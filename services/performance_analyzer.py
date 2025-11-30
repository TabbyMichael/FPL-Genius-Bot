import logging
from typing import List, Dict, Any
from services.fpl_api import FPLAPI

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Analyzes top performing teams and players in FPL"""
    
    def __init__(self, api: FPLAPI):
        self.api = api
    
    async def get_top_players_by_position(self, players: List[Dict], position: int, limit: int = 5) -> List[Dict]:
        """Get top players by position based on current form/value"""
        try:
            # Filter players by position
            position_players = [p for p in players if p.get('element_type') == position]
            
            # Calculate value for each player (form points per million)
            player_values = []
            for player in position_players:
                form = float(player.get('form', 0))
                price = player.get('now_cost', 1)
                if price > 0:
                    value = form / (price / 10)  # Points per million
                    player_values.append({
                        'player': player,
                        'value': value,
                        'form': form,
                        'price': price
                    })
            
            # Sort by value and return top players
            player_values.sort(key=lambda x: x['value'], reverse=True)
            return [item['player'] for item in player_values[:limit]]
        except Exception as e:
            logger.error(f"Error getting top players by position {position}: {str(e)}")
            return []
    
    async def get_top_teams_by_points(self, limit: int = 5) -> List[Dict]:
        """Get top teams by total points"""
        try:
            bootstrap_data = await self.api.get_bootstrap_data()
            if not bootstrap_data:
                return []
            
            teams = bootstrap_data.get('teams', [])
            # Sort teams by strength overall (as proxy for performance)
            teams.sort(key=lambda x: x.get('strength', 0), reverse=True)
            return teams[:limit]
        except Exception as e:
            logger.error(f"Error getting top teams: {str(e)}")
            return []
    
    async def get_gameweek_performance_stats(self, gameweek: int) -> Dict[str, Any]:
        """Get performance statistics for a specific gameweek"""
        try:
            bootstrap_data = await self.api.get_bootstrap_data()
            if not bootstrap_data:
                return {}
            
            # Get player data for the gameweek
            players = bootstrap_data.get('elements', [])
            
            # Calculate stats
            total_players = len(players)
            players_with_points = [p for p in players if p.get('event_points', 0) > 0]
            total_points = sum(p.get('event_points', 0) for p in players)
            
            # Find highest scoring players
            players_sorted = sorted(players, key=lambda x: x.get('event_points', 0), reverse=True)
            top_scorers = players_sorted[:5]
            
            return {
                'total_players': total_players,
                'players_with_points': len(players_with_points),
                'total_points': total_points,
                'average_points': total_points / total_players if total_players > 0 else 0,
                'top_scorers': top_scorers
            }
        except Exception as e:
            logger.error(f"Error getting gameweek performance stats: {str(e)}")
            return {}
    
    async def analyze_player_performance_trends(self, player_id: int) -> Dict[str, Any]:
        """Analyze performance trends for a specific player"""
        try:
            player_data = await self.api.get_player_data(player_id)
            if not player_data:
                return {}
            
            history = player_data.get('history', [])
            if not history:
                return {}
            
            # Calculate recent form (last 3 games)
            recent_games = history[-3:] if len(history) >= 3 else history
            recent_points = [game.get('total_points', 0) for game in recent_games]
            recent_average = sum(recent_points) / len(recent_points) if recent_points else 0
            
            # Calculate overall average
            all_points = [game.get('total_points', 0) for game in history]
            overall_average = sum(all_points) / len(all_points) if all_points else 0
            
            # Calculate consistency (standard deviation)
            import statistics
            consistency = 1 / (statistics.stdev(all_points) + 1) if len(all_points) > 1 else 1
            
            return {
                'recent_form': recent_average,
                'overall_average': overall_average,
                'consistency': consistency,
                'total_games': len(history),
                'recent_games': recent_games
            }
        except Exception as e:
            logger.error(f"Error analyzing player performance trends for player {player_id}: {str(e)}")
            return {}
    
    async def get_differential_players(self, players: List[Dict], threshold: float = 5.0) -> List[Dict]:
        """Get differential players (selected by less than threshold % of managers)"""
        try:
            # Filter players selected by less than threshold %
            differential_players = [
                p for p in players 
                if float(p.get('selected_by_percent', 100)) < threshold
            ]
            
            # Sort by form/value
            differential_players.sort(
                key=lambda x: float(x.get('form', 0)) / (x.get('now_cost', 1) / 10), 
                reverse=True
            )
            
            return differential_players[:10]
        except Exception as e:
            logger.error(f"Error getting differential players: {str(e)}")
            return []