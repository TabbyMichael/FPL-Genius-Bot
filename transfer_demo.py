#!/usr/bin/env python3
"""
Demo script to show transfer execution capability
"""

import asyncio
import logging
from config.settings import TEAM_ID
from services.fpl_api import FPLAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FPLTransferExecutor:
    """Handles execution of transfers in FPL"""
    
    def __init__(self, api: FPLAPI):
        self.api = api
        self.team_id = TEAM_ID
    
    async def authenticate(self):
        """Authenticate with FPL (placeholder)"""
        logger.info("Authenticating with FPL...")
        # In a real implementation, this would handle authentication
        # For Google Sign-In accounts, this would use session cookies
        logger.info("Authentication simulated - in real implementation, this would use session cookies")
        return True
    
    async def get_current_transfers_made(self, gameweek: int) -> int:
        """Get number of transfers already made this gameweek"""
        # Placeholder - in real implementation, this would fetch from API
        return 0
    
    async def calculate_transfer_cost(self, transfers_made: int, new_transfers: int) -> int:
        """Calculate cost of transfers"""
        free_transfers = 1 + max(0, transfers_made - 1)  # 1 free transfer, +1 for every 2 used previously
        transfers_needed = new_transfers - free_transfers
        cost = max(0, transfers_needed) * 4  # £4 per transfer beyond free allowance
        return cost
    
    async def execute_transfer(self, player_out_id: int, player_in_id: int, gameweek: int):
        """Execute a single transfer"""
        try:
            logger.info(f"Executing transfer: Player {player_out_id} -> Player {player_in_id}")
            
            # Get current transfers made
            transfers_made = await self.get_current_transfers_made(gameweek)
            
            # Calculate cost
            cost = await self.calculate_transfer_cost(transfers_made, 1)
            logger.info(f"Transfer cost: £{cost}m")
            
            # In a real implementation, this would make the actual API call:
            # POST to https://fantasy.premierleague.com/api/transfers/
            # With proper authentication headers and transfer payload
            
            logger.info("Transfer executed successfully (simulated)")
            return True
        except Exception as e:
            logger.error(f"Error executing transfer: {str(e)}")
            return False
    
    async def execute_transfers(self, transfers: list, gameweek: int):
        """Execute multiple transfers"""
        try:
            if not transfers:
                logger.info("No transfers to execute")
                return True
            
            logger.info(f"Executing {len(transfers)} transfers...")
            
            # Authenticate first
            if not await self.authenticate():
                logger.error("Failed to authenticate")
                return False
            
            success_count = 0
            for i, transfer in enumerate(transfers, 1):
                logger.info(f"Transfer {i}/{len(transfers)}:")
                out_player = transfer.get('out', {})
                in_player = transfer.get('in', {})
                
                logger.info(f"  Out: {out_player.get('web_name', 'Unknown')} (£{out_player.get('now_cost', 0)/10:.1f}m)")
                logger.info(f"  In:  {in_player.get('web_name', 'Unknown')} (£{in_player.get('now_cost', 0)/10:.1f}m)")
                logger.info(f"  Reason: {transfer.get('reason', 'No reason provided')}")
                
                # Execute the transfer
                success = await self.execute_transfer(
                    out_player.get('id'), 
                    in_player.get('id'), 
                    gameweek
                )
                
                if success:
                    success_count += 1
                else:
                    logger.error(f"Failed to execute transfer {i}")
            
            logger.info(f"Transfer execution completed: {success_count}/{len(transfers)} successful")
            return success_count == len(transfers)
        except Exception as e:
            logger.error(f"Error executing transfers: {str(e)}")
            return False

async def demo_transfer_execution():
    """Demo transfer execution"""
    logger.info("=" * 50)
    logger.info("FPL Transfer Execution Demo")
    logger.info("=" * 50)
    
    # Sample transfer data (this would come from the transfer engine in reality)
    sample_transfers = [
        {
            'out': {'id': 1, 'web_name': 'Raya', 'now_cost': 59},
            'in': {'id': 2, 'web_name': 'Henderson', 'now_cost': 50},
            'reason': 'Better value goalkeeper with easier upcoming fixtures'
        },
        {
            'out': {'id': 3, 'web_name': 'Guéhi', 'now_cost': 51},
            'in': {'id': 4, 'web_name': 'Keane', 'now_cost': 46},
            'reason': 'Higher value defender with better recent form'
        }
    ]
    
    async with FPLAPI() as api:
        executor = FPLTransferExecutor(api)
        success = await executor.execute_transfers(sample_transfers, 13)
        
        if success:
            logger.info("All transfers executed successfully!")
        else:
            logger.error("Some transfers failed to execute")

if __name__ == "__main__":
    asyncio.run(demo_transfer_execution())