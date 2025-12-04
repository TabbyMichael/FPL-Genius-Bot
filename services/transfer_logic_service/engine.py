import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import httpx # For making HTTP requests to other services

# This is a temporary solution for the database connection.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fpl_bot.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import necessary models from config.database (once moved to shared library or each service has its own models)
from config.database import TransferHistory # Placeholder for now

logger = logging.getLogger(__name__)

class TransferEngine:
    """Handles transfer decisions for the FPL bot"""
    
    def __init__(self, db: Session, ml_service_url: str, fpl_api_service_url: str):
        self.budget_buffer = 0.5  # Keep some money in reserve
        self.db = db
        self.ml_service_url = ml_service_url
        self.fpl_api_service_url = fpl_api_service_url
    
    async def calculate_expected_points(self, player_data: Dict[str, Any], fixture_difficulty: int = 3) -> float:
        """Calculate expected points for a player by calling the ML Prediction Service."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ml_service_url}/predict",
                    json={"stats": player_data, "opponent_difficulty": fixture_difficulty}
                )
                response.raise_for_status()
                return response.json().get("predicted_points", 0.0)
        except httpx.HTTPStatusError as e:
            logger.error(f"Error calling ML Prediction Service: {e.response.status_code} - {e.response.text}")
            # Fallback to simple calculation if ML service is unavailable or errors
            history = player_data.get('history', [])
            if not history:
                return 0
            recent_points = [game['total_points'] for game in history[-3:] if 'total_points' in game]
            avg_points = sum(recent_points) / len(recent_points) if recent_points else 0
            difficulty_multiplier = 1.2 - (fixture_difficulty - 3) * 0.1
            return avg_points * difficulty_multiplier
        except Exception as e:
            logger.error(f"Unexpected error in calculate_expected_points: {str(e)}")
            return 0
    
    def is_player_available(self, player: Dict[str, Any]) -> bool:
        """Check if player is available (not injured or suspended)"""
        try:
            status = player.get('status')
            if status is None:
                status = 'a'
            
            if status != 'a':
                logger.debug(f"Player {player.get('web_name', 'Unknown')} is not available (status: {status})")
                return False
            
            chance_next = player.get('chance_of_playing_next_round')
            if chance_next is not None and chance_next < 75:
                logger.debug(f"Player {player.get('web_name', 'Unknown')} has low chance of playing ({chance_next}%)")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error checking player availability: {str(e)}")
            return True
    
    def calculate_player_value(self, player: Dict[str, Any], fixture_difficulty: int = 3) -> float:
        """Calculate value score for a player (points per million)"""
        try:
            price = player.get('now_cost', 1)
            if price <= 0:
                return 0
            
            # This will need to be an async call in an async context
            # For now, it will be called in identify_transfer_targets which is async
            # In a real microservice, this might be handled via message passing or a direct call
            expected_points = player.get('expected_points_from_ml', 0) # Assumed to be pre-calculated
            value = expected_points / (price / 10)
            
            return value
        except Exception as e:
            logger.error(f"Error calculating player value: {str(e)}")
            return 0
    
    async def identify_transfer_targets(self, current_squad: List[Dict], 
                                available_players: List[Dict], 
                                budget: float) -> List[Dict]:
        """Identify potential transfer targets with sophisticated analysis"""
        try:
            logger.info("Starting transfer target identification...")
            
            # Fetch bootstrap data from FPL API Service
            async with httpx.AsyncClient() as client:
                bootstrap_response = await client.get(f"{self.fpl_api_service_url}/bootstrap")
                bootstrap_response.raise_for_status()
                bootstrap_data = bootstrap_response.json()
            
            events = bootstrap_data.get('events', [])
            current_gw = None
            for event in events:
                if event.get('is_current'):
                    current_gw = event.get('id')
                    break
            if not current_gw:
                for event in events:
                    if event.get('is_next'):
                        current_gw = event.get('id')
                        break
            if not current_gw:
                current_gw = 1 # Fallback
            
            # Calculate value and expected points for each player
            logger.info(f"Analyzing {len(available_players)} available players...")
            player_values = []
            
            for player in available_players:
                if not self.is_player_available(player):
                    continue
                
                # Get fixture difficulty from FPL API Service
                team_id = player.get('team', 0)
                async with httpx.AsyncClient() as client:
                    difficulty_response = await client.get(f"{self.fpl_api_service_url}/fixture-difficulty/{team_id}/{current_gw}")
                    difficulty_response.raise_for_status()
                    fixture_difficulty = difficulty_response.json().get("difficulty", 3)
                
                # Call ML Prediction Service for expected points
                expected_points = await self.calculate_expected_points(player, fixture_difficulty)
                player['expected_points_from_ml'] = expected_points # Attach for value calculation
                
                value = self.calculate_player_value(player, fixture_difficulty)
                
                player_values.append({
                    'player': player,
                    'expected_points': expected_points,
                    'value': value,
                    'fixture_difficulty': fixture_difficulty
                })
            
            logger.info(f"Found {len(player_values)} available players after filtering")
            
            # Sort by value
            player_values.sort(key=lambda x: x['value'], reverse=True)
            
            # Find weakest players in current squad
            logger.info(f"Analyzing {len(current_squad)} squad players...")
            squad_analysis = []
            for player in current_squad:
                # Need to get fixture difficulty and expected points for current squad players too
                team_id = player.get('team', 0)
                async with httpx.AsyncClient() as client:
                    difficulty_response = await client.get(f"{self.fpl_api_service_url}/fixture-difficulty/{team_id}/{current_gw}")
                    difficulty_response.raise_for_status()
                    fixture_difficulty = difficulty_response.json().get("difficulty", 3)

                expected_points = await self.calculate_expected_points(player, fixture_difficulty)
                player['expected_points_from_ml'] = expected_points

                value = self.calculate_player_value(player, fixture_difficulty)
                
                squad_analysis.append({
                    'player': player,
                    'expected_points': expected_points,
                    'value': value,
                    'fixture_difficulty': fixture_difficulty
                })
            
            squad_analysis.sort(key=lambda x: x['value'])
            
            # Suggest transfers (sophisticated logic)
            transfers = []
            for i in range(min(2, len(squad_analysis))):  # Max 2 transfers
                weakest = squad_analysis[i]
                weakest_player = weakest['player']
                weakest_value = weakest['value']
                
                position = weakest_player.get('element_type')
                player_price = weakest_player.get('now_cost', 0)
                available_budget = budget + player_price - self.budget_buffer * 10
                
                better_players = [
                    pv for pv in player_values 
                    if (pv['player'].get('element_type') == position and 
                        pv['player'].get('now_cost', 0) <= available_budget and
                        pv['value'] > weakest_value and
                        self.is_player_available(pv['player']))
                ]
                
                if better_players:
                    better_players.sort(key=lambda x: x['value'] - weakest_value, reverse=True)
                    best_target = better_players[0]
                    
                    transfers.append({
                        'out': weakest_player,
                        'in': best_target['player'],
                        'gain': best_target['value'] - weakest_value,
                        'expected_point_gain': best_target['expected_points'] - weakest['expected_points'],
                        'reason': f"Better value ({best_target['value']:.2f} vs {weakest_value:.2f}), Difficulty: {best_target['fixture_difficulty']} vs {weakest['fixture_difficulty']}"
                    })
            
            transfers.sort(key=lambda x: x['gain'], reverse=True)
            logger.info(f"Identified {len(transfers)} potential transfers")
            return transfers[:2]
        except Exception as e:
            logger.error(f"Error identifying transfer targets: {str(e)}", exc_info=True)
            return []
    
    def record_transfer(self, transfer_data: Dict):
        """Record transfer in database for performance tracking"""
        try:
            # Need to get PlayerPerformance from a shared model or data service
            from config.database import TransferHistory # Placeholder for now
            transfer_record = TransferHistory(
                player_out_id=transfer_data['out']['id'],
                player_in_id=transfer_data['in']['id'],
                gameweek=transfer_data.get('gameweek', 0),
                transfer_gain=transfer_data.get('gain', 0),
                cost=transfer_data.get('cost', 0)
            )
            self.db.add(transfer_record)
            self.db.commit()
            logger.info(f"Recorded transfer: {transfer_data['out']['web_name']} -> {transfer_data['in']['web_name']}")
        except Exception as e:
            logger.error(f"Error recording transfer: {str(e)}")
            self.db.rollback()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
