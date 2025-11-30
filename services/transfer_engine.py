import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from config.database import PlayerPerformance, TransferHistory
from services.ml_predictor import MLPredictor
from services.fpl_api import FPLAPI

logger = logging.getLogger(__name__)

class TransferEngine:
    """Handles transfer decisions for the FPL bot"""
    
    def __init__(self, db: Session):
        self.budget_buffer = 0.5  # Keep some money in reserve
        self.db = db
        self.ml_predictor = MLPredictor()
        self.ml_predictor.train_model(db)
    
    def calculate_expected_points(self, player_data: Dict[str, Any], fixture_difficulty: int = 3) -> float:
        """Calculate expected points for a player based on recent performance and fixtures"""
        try:
            # Try to use ML prediction first
            if self.ml_predictor.is_trained:
                predicted_points = self.ml_predictor.predict_performance(player_data, fixture_difficulty)
                return predicted_points
            
            # Fallback to simple calculation if ML not available
            # Get recent points (last 3 games)
            history = player_data.get('history', [])
            if not history:
                return 0
            
            recent_points = [game['total_points'] for game in history[-3:] if 'total_points' in game]
            if not recent_points:
                return 0
                
            avg_points = sum(recent_points) / len(recent_points)
            
            # Adjust based on fixture difficulty
            # 1 = easiest, 5 = hardest
            difficulty_multiplier = 1.2 - (fixture_difficulty - 3) * 0.1  # Scale from 0.8 to 1.2
            expected_points = avg_points * difficulty_multiplier
            
            return expected_points
        except Exception as e:
            logger.error(f"Error calculating expected points: {str(e)}")
            return 0
    
    def is_player_available(self, player: Dict[str, Any]) -> bool:
        """Check if player is available (not injured or suspended) - simplified version"""
        try:
            status = player.get('status', 'a')
            
            # 'a' = available, 'i' = injured, 's' = suspended, 'u' = unavailable
            if status != 'a':
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error checking player availability: {str(e)}")
            return True  # Assume available if error
    
    def calculate_player_value(self, player: Dict[str, Any], fixture_difficulty: int = 3) -> float:
        """Calculate value score for a player (points per million)"""
        try:
            price = player.get('now_cost', 1)
            if price <= 0:
                return 0
            
            expected_points = self.calculate_expected_points(player, fixture_difficulty)
            value = expected_points / (price / 10)  # Points per million
            
            return value
        except Exception as e:
            logger.error(f"Error calculating player value: {str(e)}")
            return 0
    
    async def identify_transfer_targets(self, current_squad: List[Dict], 
                                available_players: List[Dict], 
                                budget: float, 
                                api: Optional[FPLAPI] = None) -> List[Dict]:
        """Identify potential transfer targets with sophisticated analysis"""
        try:
            # Get current gameweek for fixture analysis
            current_gw = 13  # Default, would normally get from API
            if api:
                bootstrap_data = await api.get_bootstrap_data()
                if bootstrap_data:
                    events = bootstrap_data.get('events', [])
                    for event in events:
                        if event.get('is_current'):
                            current_gw = event.get('id')
                            break
            
            # Calculate value and expected points for each player
            player_values = []
            for player in available_players:
                # Skip injured/suspended players
                if not self.is_player_available(player):
                    continue
                
                # Get fixture difficulty for player's team
                team_id = player.get('team', 0)
                fixture_difficulty = 3  # Default
                if api and team_id:
                    fixture_difficulty = await api.get_fixture_difficulty(team_id, current_gw)
                
                expected_points = self.calculate_expected_points(player, fixture_difficulty)
                value = self.calculate_player_value(player, fixture_difficulty)
                
                player_values.append({
                    'player': player,
                    'expected_points': expected_points,
                    'value': value,
                    'fixture_difficulty': fixture_difficulty
                })
            
            # Sort by value
            player_values.sort(key=lambda x: x['value'], reverse=True)
            
            # Find weakest players in current squad
            squad_analysis = []
            for player in current_squad:
                team_id = player.get('team', 0)
                fixture_difficulty = 3  # Default
                if api and team_id:
                    fixture_difficulty = await api.get_fixture_difficulty(team_id, current_gw)
                
                expected_points = self.calculate_expected_points(player, fixture_difficulty)
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
                
                # Find better valued players of the same position within budget
                better_players = [
                    pv for pv in player_values 
                    if (pv['player'].get('element_type') == position and 
                        pv['player'].get('now_cost', 0) <= available_budget and
                        pv['value'] > weakest_value and
                        self.is_player_available(pv['player']))
                ]
                
                if better_players:
                    # Sort by value improvement
                    better_players.sort(key=lambda x: x['value'] - weakest_value, reverse=True)
                    best_target = better_players[0]
                    
                    transfers.append({
                        'out': weakest_player,
                        'in': best_target['player'],
                        'gain': best_target['value'] - weakest_value,
                        'expected_point_gain': best_target['expected_points'] - weakest['expected_points'],
                        'reason': f"Better value ({best_target['value']:.2f} vs {weakest_value:.2f}), Difficulty: {best_target['fixture_difficulty']} vs {weakest['fixture_difficulty']}"
                    })
            
            # Sort by gain
            transfers.sort(key=lambda x: x['gain'], reverse=True)
            return transfers[:2]  # Return top 2 transfers
        except Exception as e:
            logger.error(f"Error identifying transfer targets: {str(e)}")
            return []
    
    def record_transfer(self, transfer_data: Dict):
        """Record transfer in database for performance tracking"""
        try:
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