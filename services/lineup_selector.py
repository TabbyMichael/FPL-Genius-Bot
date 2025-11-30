import logging
from typing import List, Dict, Any
from services.ml_predictor import MLPredictor

logger = logging.getLogger(__name__)

class LineupSelector:
    """Handles lineup selection and captain choice"""
    
    def __init__(self, db_session=None):
        # Formation constraints
        self.positions = {
            1: {'name': 'Goalkeeper', 'min': 1, 'max': 1},
            2: {'name': 'Defender', 'min': 3, 'max': 5},
            3: {'name': 'Midfielder', 'min': 3, 'max': 5},
            4: {'name': 'Forward', 'min': 1, 'max': 3}
        }
        self.db_session = db_session
        self.ml_predictor = MLPredictor()
        if db_session:
            self.ml_predictor.train_model(db_session)
    
    def select_captain(self, squad: List[Dict]) -> Dict:
        """Select captain based on expected points"""
        try:
            best_player = None
            max_points = -1
            
            for player in squad:
                # Use ML prediction if available
                if self.ml_predictor.is_trained:
                    opponent_difficulty = player.get('opponent_difficulty', 3)
                    expected_points = self.ml_predictor.predict_performance(player, opponent_difficulty)
                else:
                    # Fallback to simplified expected points calculation
                    expected_points = self._calculate_player_points(player)
                
                if expected_points > max_points:
                    max_points = expected_points
                    best_player = player
                    
            return best_player
        except Exception as e:
            logger.error(f"Error selecting captain: {str(e)}")
            return squad[0] if squad else None
    
    def select_lineup(self, squad: List[Dict]) -> List[Dict]:
        """Select starting XI from squad"""
        try:
            # Sort players by expected points (using ML if available)
            def sort_key(player):
                if self.ml_predictor.is_trained:
                    opponent_difficulty = player.get('opponent_difficulty', 3)
                    return self.ml_predictor.predict_performance(player, opponent_difficulty)
                else:
                    return self._calculate_player_points(player)
            
            sorted_players = sorted(squad, key=sort_key, reverse=True)
            
            # Select lineup based on positions
            lineup = []
            position_count = {1: 0, 2: 0, 3: 0, 4: 0}
            
            # First pass - fill minimum requirements
            for player in sorted_players:
                position = player['element_type']
                if position_count[position] < self.positions[position]['min']:
                    lineup.append(player)
                    position_count[position] += 1
            
            # Second pass - fill remaining spots
            for player in sorted_players:
                if len(lineup) >= 11:
                    break
                if player not in lineup:
                    position = player['element_type']
                    if position_count[position] < self.positions[position]['max']:
                        lineup.append(player)
                        position_count[position] += 1
            
            return lineup
        except Exception as e:
            logger.error(f"Error selecting lineup: {str(e)}")
            return squad[:11] if len(squad) >= 11 else squad
    
    def _calculate_player_points(self, player: Dict) -> float:
        """Calculate expected points for a player"""
        # Simplified calculation - can be enhanced
        try:
            # Use form, minutes, goals, assists, etc.
            form = float(player.get('form', 0))
            points_per_game = float(player.get('points_per_game', 0))
            minutes = player.get('minutes', 0)
            
            # Weighted score
            score = form * 0.6 + points_per_game * 0.4
            
            # Bonus for regular playing time
            if minutes > 900:  # Played more than 10 games
                score *= 1.1
                
            return score
        except:
            return 0