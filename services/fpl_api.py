import aiohttp
import asyncio
import logging
from config.settings import FPL_BASE_URL, FPL_USERNAME, FPL_PASSWORD, TEAM_ID

logger = logging.getLogger(__name__)

class FPLAPI:
    """Handles communication with the FPL API"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_bootstrap_data(self):
        """Get static bootstrap data from FPL"""
        try:
            async with self.session.get(f"{FPL_BASE_URL}/bootstrap-static/") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch bootstrap data: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching bootstrap data: {str(e)}")
            return None
    
    async def get_player_data(self, player_id):
        """Get detailed data for a specific player"""
        try:
            async with self.session.get(f"{FPL_BASE_URL}/element-summary/{player_id}/") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch player data for ID {player_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching player data for ID {player_id}: {str(e)}")
            return None
    
    async def get_fixtures(self):
        """Get upcoming fixtures"""
        try:
            async with self.session.get(f"{FPL_BASE_URL}/fixtures/") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch fixtures: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching fixtures: {str(e)}")
            return None
    
    async def get_team_data(self):
        """Get team data for the configured team ID"""
        if not TEAM_ID:
            logger.error("No TEAM_ID configured")
            return None
            
        try:
            url = f"{FPL_BASE_URL}/entry/{TEAM_ID}/"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch team data for ID {TEAM_ID}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching team data for ID {TEAM_ID}: {str(e)}")
            return None
    
    async def get_team_picks(self, gameweek=None):
        """Get team picks for a specific gameweek (defaults to current)"""
        if not TEAM_ID:
            logger.error("No TEAM_ID configured")
            return None
            
        try:
            # If no gameweek specified, try to get current gameweek
            if gameweek is None:
                bootstrap_data = await self.get_bootstrap_data()
                if bootstrap_data:
                    events = bootstrap_data.get('events', [])
                    for event in events:
                        if event.get('is_current'):
                            gameweek = event.get('id')
                            break
                        elif event.get('is_next'):
                            gameweek = event.get('id')
                            break
            
            if gameweek is None:
                logger.error("Could not determine current gameweek")
                return None
                
            url = f"{FPL_BASE_URL}/entry/{TEAM_ID}/event/{gameweek}/picks/"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch team picks for ID {TEAM_ID}, GW {gameweek}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching team picks for ID {TEAM_ID}, GW {gameweek}: {str(e)}")
            return None
    
    async def get_player_info(self, player_id):
        """Get detailed player information"""
        try:
            bootstrap_data = await self.get_bootstrap_data()
            if not bootstrap_data:
                return None
                
            players = bootstrap_data.get('elements', [])
            for player in players:
                if player.get('id') == player_id:
                    return player
            return None
        except Exception as e:
            logger.error(f"Error fetching player info for ID {player_id}: {str(e)}")
            return None
    
    async def get_fixture_difficulty(self, team_id, gameweek):
        """Get fixture difficulty for a team in a specific gameweek"""
        try:
            fixtures = await self.get_fixtures()
            if not fixtures:
                return 3  # Default medium difficulty
            
            for fixture in fixtures:
                if fixture.get('event') == gameweek:
                    if fixture.get('team_h') == team_id:
                        return fixture.get('team_h_difficulty', 3)
                    elif fixture.get('team_a') == team_id:
                        return fixture.get('team_a_difficulty', 3)
            
            return 3  # Default medium difficulty
        except Exception as e:
            logger.error(f"Error fetching fixture difficulty for team {team_id}, GW {gameweek}: {str(e)}")
            return 3
    
    async def get_player_injury_status(self, player_id):
        """Get injury/suspension status for a player"""
        try:
            player_info = await self.get_player_info(player_id)
            if not player_info:
                return "a"  # Default to available
            
            status = player_info.get('status', 'a')
            news = player_info.get('news', '')
            
            return {
                'status': status,
                'news': news,
                'chance_of_playing_next_round': player_info.get('chance_of_playing_next_round', 100),
                'chance_of_playing_this_round': player_info.get('chance_of_playing_this_round', 100)
            }
        except Exception as e:
            logger.error(f"Error fetching injury status for player {player_id}: {str(e)}")
            return {'status': 'a', 'news': '', 'chance_of_playing_next_round': 100, 'chance_of_playing_this_round': 100}