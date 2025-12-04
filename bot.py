import asyncio
import os
import logging
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# Conditional imports for aio_pika to avoid linter errors
import importlib

# Initialize variables for conditional imports
aio_pika = None
ExchangeType = None
Message = None

try:
    aio_pika = importlib.import_module('aio_pika')
    ExchangeType = importlib.import_module('aio_pika').ExchangeType
    Message = importlib.import_module('aio_pika').Message
except ImportError as e:
    logging.error(f"Failed to import aio_pika: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# RabbitMQ configuration
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


class RabbitMQClient:
    def __init__(self, amqp_url: str):
        self.connection = None
        self.channel = None
        self.amqp_url = amqp_url

    async def connect(self):
        if aio_pika is None:
            logger.error("aio_pika not available")
            return
            
        logger.info(f"Connecting to RabbitMQ at {self.amqp_url}")
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        if self.connection is not None:
            self.channel = await self.connection.channel()
            if self.channel is not None:
                await self.channel.set_qos(prefetch_count=1)
        logger.info("Connected to RabbitMQ")

    async def disconnect(self):
        if self.connection:
            logger.info("Disconnecting from RabbitMQ")
            await self.connection.close()
            self.connection = None
            self.channel = None
            logger.info("Disconnected from RabbitMQ")

    async def call(self, queue_name: str, payload: Dict) -> Dict:
        if aio_pika is None or Message is None:
            logger.error("aio_pika not available")
            return {"error": "aio_pika not available"}
            
        if not self.channel:
            await self.connect()

        correlation_id = str(uuid.uuid4())
        
        # Declare a temporary, exclusive, auto-delete queue for RPC response
        if self.channel is not None:
            callback_queue = await self.channel.declare_queue(exclusive=True, auto_delete=True)
        else:
            return {"error": "Channel not available"}

        message_body = json.dumps(payload).encode()
        
        if self.channel is not None and Message is not None:
            await self.channel.default_exchange.publish(
                Message(
                    message_body,
                    content_type="application/json",
                    correlation_id=correlation_id,
                    reply_to=callback_queue.name,
                ),
                routing_key=queue_name,
            )

        logger.debug(f"RPC call to {queue_name} with correlation_id {correlation_id}")

        response_future = asyncio.Future()

        async with callback_queue.iterator() as queue_iter:
            async for message in queue_iter:
                if message.correlation_id == correlation_id:
                    response_future.set_result(json.loads(message.body.decode()))
                    await message.ack()
                    break
        
        return await response_future

    async def publish(self, exchange_name: str, routing_key: str, payload: Dict):
        if aio_pika is None or ExchangeType is None or Message is None:
            logger.error("aio_pika not available")
            return
            
        if not self.channel:
            await self.connect()
        
        if self.channel is not None and ExchangeType is not None:
            exchange = await self.channel.declare_exchange(exchange_name, ExchangeType.FANOUT, durable=True)
            message_body = json.dumps(payload).encode()
            if Message is not None:
                await exchange.publish(
                    Message(message_body, content_type="application/json"),
                    routing_key=routing_key
                )
            logger.debug(f"Published message to exchange {exchange_name} with routing_key {routing_key}")


async def run_weekly_process():
    """Run the weekly FPL process, orchestrated via RabbitMQ."""
    logger.info("Starting weekly FPL process (Orchestrator)")
    
    rabbitmq_client = RabbitMQClient(RABBITMQ_URL)
    try:
        await rabbitmq_client.connect()

        # 1. Trigger FPL Data Fetch
        logger.info("Requesting FPL Bootstrap Data...")
        bootstrap_data_response = await rabbitmq_client.call(
            "fpl_api_rpc_queue", {"action": "get_bootstrap_data"}
        )
        bootstrap_data = bootstrap_data_response.get("data")
        if not bootstrap_data:
            logger.error("Failed to fetch bootstrap data from FPL API Service.")
            return False
        logger.info("FPL Bootstrap Data received.")

        players = bootstrap_data.get('elements', [])
        teams = bootstrap_data.get('teams', [])
        events = bootstrap_data.get('events', [])
        
        # 2. Determine current gameweek
        current_gw = None
        for event in events:
            if event.get('is_current'):
                current_gw = event
                break
        if not current_gw:
            for event in events:
                if event.get('is_next'):
                    current_gw = event
                    break
        if not current_gw:
            logger.warning("Could not determine current gameweek")
            return False
        gameweek_id = current_gw.get('id')
        logger.info(f"Processing gameweek {gameweek_id}")

        # 3. Request current squad
        logger.info("Requesting current squad...")
        team_picks_response = await rabbitmq_client.call(
            "fpl_api_rpc_queue", {"action": "get_team_picks", "gameweek": gameweek_id}
        )
        picks_data = team_picks_response.get("data")
        if not picks_data:
            logger.warning("Could not fetch team picks, trying previous gameweek...")
            # Try previous gameweek if current fails
            if gameweek_id > 1:
                team_picks_response = await rabbitmq_client.call(
                    "fpl_api_rpc_queue", {"action": "get_team_picks", "gameweek": gameweek_id - 1}
                )
                picks_data = team_picks_response.get("data")
                if picks_data:
                    gameweek_id -= 1
                    logger.info(f"Successfully loaded squad from gameweek {gameweek_id}")
            if not picks_data:
                logger.error("Failed to fetch team picks from FPL API Service.")
                return False

        picks = picks_data.get('picks', [])
        entry_history = picks_data.get('entry_history', {})
        bank = entry_history.get('bank', 1000)

        # Build current_squad (simplified for orchestrator)
        current_squad = []
        player_dict = {player['id']: player for player in players}
        for pick in picks:
            player_id = pick.get('element')
            if player_id in player_dict:
                player_info = player_dict[player_id].copy()
                player_info['pick_data'] = pick
                current_squad.append(player_info)
        
        logger.info(f"Loaded squad with {len(current_squad)} players")
        # Assuming format_currency is moved to a utility service or orchestrator maintains simple utilities
        logger.info(f"Available budget: {bank / 10.0:.1f}m")

        # 4. Trigger ML Model Training (if needed)
        logger.info("Triggering ML Model Training...")
        train_model_response = await rabbitmq_client.call(
            "ml_prediction_rpc_queue", {"action": "train_model"}
        )
        if not train_model_response.get("success"):
            logger.warning(f"ML Model training not successful: {train_model_response.get('detail', 'Unknown error')}")
        else:
            logger.info("ML Model training process initiated/completed.")

        # 5. Request Transfer Recommendations
        logger.info("Requesting Transfer Recommendations...")
        transfer_recommendations_response = await rabbitmq_client.call(
            "transfer_logic_rpc_queue", 
            {
                "action": "identify_transfer_targets",
                "current_squad": current_squad,
                "available_players": players, # Pass all available players for the service to filter
                "budget": bank
            }
        )
        transfer_targets = transfer_recommendations_response.get("data", [])
        if not transfer_targets:
            logger.info("No transfer recommendations received.")
        else:
            logger.info(f"Received {len(transfer_targets)} transfer recommendations.")
            # 6. Execute Transfers (via FPL API Service)
            logger.info("Initiating Transfer Execution...")
            execute_transfers_response = await rabbitmq_client.call(
                "fpl_api_rpc_queue", {"action": "execute_transfers", "transfers": transfer_targets}
            )
            if execute_transfers_response.get("success"):
                logger.info("Transfers executed successfully.")
            else:
                logger.error(f"Transfer execution failed: {execute_transfers_response.get('detail', 'Unknown error')}")
        
        logger.info("Weekly process completed successfully")
        return True

    except Exception as e:
        logger.error(f"Orchestrator error during weekly process: {str(e)}", exc_info=True)
        return False
    finally:
        await rabbitmq_client.disconnect()


async def main():
    """Main entry point for the Orchestrator."""
    logger.info("=" * 50)
    logger.info("FPL Orchestrator Starting")
    logger.info("=" * 50)
    
    try:
        success = await run_weekly_process()
        if success:
            logger.info("FPL Orchestrator completed successfully")
        else:
            logger.error("FPL Orchestrator encountered errors")
            return 1
            
    except Exception as e:
        logger.error(f"Error running FPL Orchestrator: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)