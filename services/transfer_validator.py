import logging
from typing import List, Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

class TransferValidator:
    """Validates transfers before execution according to FPL rules"""
    
    def __init__(self):
        # FPL squad constraints
        self.SQUAD_SIZE = 15
        self.POSITION_LIMITS = {
            1: {'name': 'Goalkeeper', 'min': 1, 'max': 1},      # GK
            2: {'name': 'Defender', 'min': 3, 'max': 5},         # DEF
            3: {'name': 'Midfielder', 'min': 3, 'max': 5},       # MID
            4: {'name': 'Forward', 'min': 1, 'max': 3}           # FWD
        }
        self.MAX_PLAYERS_PER_CLUB = 3
        self.ALLOWED_FORMATIONS = [
            [1, 3, 4, 3],  # 1 GK, 3 DEF, 4 MID, 3 FWD
            [1, 3, 5, 2],  # 1 GK, 3 DEF, 5 MID, 2 FWD
            [1, 4, 3, 3],  # 1 GK, 4 DEF, 3 MID, 3 FWD
            [1, 4, 4, 2],  # 1 GK, 4 DEF, 4 MID, 2 FWD
            [1, 4, 5, 1],  # 1 GK, 4 DEF, 5 MID, 1 FWD
            [1, 5, 3, 2],  # 1 GK, 5 DEF, 3 MID, 2 FWD
            [1, 5, 4, 1]   # 1 GK, 5 DEF, 4 MID, 1 FWD
        ]
        self.TRANSFERS_PER_GW = 2
        self.TRANSFER_COST = 4  # Points deducted per extra transfer
    
    def validate_transfers(self, transfers: List[Dict], current_squad: List[Dict], 
                          budget: float, gameweek: int = 0, chips: Optional[Dict] = None,
                          override: bool = False) -> Dict[str, Any]:
        """
        Validate transfers before execution
        
        Args:
            transfers: List of transfer dictionaries
            current_squad: Current squad composition
            budget: Available budget
            gameweek: Current gameweek
            chips: Active chips (wildcard, freehit, etc.)
            override: Whether to allow execution despite validation failures
        
        Returns:
            Dict with validation status and messages
        """
        validation_result = {
            'status': 'pass',
            'messages': [],
            'override_required': False
        }
        
        try:
            # Validate each transfer individually
            for i, transfer in enumerate(transfers):
                self._validate_single_transfer(transfer, validation_result, i)
            
            # Validate squad constraints after all transfers
            self._validate_squad_constraints(transfers, current_squad, validation_result)
            
            # Validate budget
            self._validate_budget(transfers, current_squad, budget, validation_result)
            
            # Validate formation
            self._validate_formation(transfers, current_squad, validation_result)
            
            # Validate chips and transfer rules
            self._validate_chips_and_transfers(transfers, gameweek, chips, validation_result)
            
            # Validate player availability
            self._validate_player_availability(transfers, validation_result)
            
            # Check for override requirement
            if validation_result['status'] == 'fail':
                validation_result['override_required'] = not override
                if override:
                    validation_result['messages'].append({
                        'code': 'OVERRIDE_USED',
                        'level': 'warn',
                        'message': 'Override flag used to bypass validation failures',
                        'details': 'Transfer execution proceeding despite validation failures due to override flag'
                    })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during transfer validation: {str(e)}")
            return {
                'status': 'fail',
                'messages': [{
                    'code': 'VALIDATION_ERROR',
                    'level': 'error',
                    'message': 'Internal validation error occurred',
                    'details': str(e)
                }],
                'override_required': False
            }
    
    def _validate_single_transfer(self, transfer: Dict, result: Dict, index: int):
        """Validate a single transfer"""
        try:
            player_out = transfer.get('element_out') or transfer.get('out')
            player_in = transfer.get('element_in') or transfer.get('in')
            
            if not player_out or not player_in:
                result['status'] = 'fail'
                result['messages'].append({
                    'code': 'INVALID_TRANSFER_FORMAT',
                    'level': 'fail',
                    'message': f'Transfer {index+1} has invalid format',
                    'details': 'Missing player_out or player_in fields'
                })
                return
            
            # Check if players exist (basic validation)
            if not isinstance(player_out, dict) or not isinstance(player_in, dict):
                result['status'] = 'fail'
                result['messages'].append({
                    'code': 'INVALID_PLAYER_DATA',
                    'level': 'fail',
                    'message': f'Transfer {index+1} has invalid player data',
                    'details': 'Player data must be dictionary objects'
                })
            
        except Exception as e:
            result['status'] = 'fail'
            result['messages'].append({
                'code': 'TRANSFER_VALIDATION_ERROR',
                'level': 'error',
                'message': f'Error validating transfer {index+1}',
                'details': str(e)
            })
    
    def _validate_squad_constraints(self, transfers: List[Dict], current_squad: List[Dict], result: Dict):
        """Validate squad size and position constraints"""
        try:
            # Simulate the final squad after transfers
            final_squad = list(current_squad)  # Copy current squad
            
            # Apply transfers
            for transfer in transfers:
                player_out = transfer.get('element_out') or transfer.get('out')
                player_in = transfer.get('element_in') or transfer.get('in')
                
                # Remove player_out
                if player_out and isinstance(player_out, dict):
                    final_squad = [p for p in final_squad if p.get('id') != player_out.get('id')]
                
                # Add player_in
                if player_in and isinstance(player_in, dict):
                    final_squad.append(player_in)
            
            # Check squad size
            if len(final_squad) != self.SQUAD_SIZE:
                result['status'] = 'fail'
                result['messages'].append({
                    'code': 'INVALID_SQUAD_SIZE',
                    'level': 'fail',
                    'message': f'Invalid squad size: {len(final_squad)}',
                    'details': f'Squad must contain exactly {self.SQUAD_SIZE} players'
                })
            
            # Check position constraints
            position_counts = {1: 0, 2: 0, 3: 0, 4: 0}  # GK, DEF, MID, FWD
            for player in final_squad:
                if isinstance(player, dict):
                    pos_type = player.get('element_type', 0)
                    if pos_type in position_counts:
                        position_counts[pos_type] += 1
            
            for pos_type, count in position_counts.items():
                limits = self.POSITION_LIMITS[pos_type]
                if count < limits['min'] or count > limits['max']:
                    result['status'] = 'fail'
                    result['messages'].append({
                        'code': 'INVALID_POSITION_COUNT',
                        'level': 'fail',
                        'message': f'Invalid {limits["name"]} count: {count}',
                        'details': f'Must have {limits["min"]}-{limits["max"]} {limits["name"]}s, got {count}'
                    })
            
            # Check club limits
            club_counts = {}
            for player in final_squad:
                if isinstance(player, dict):
                    club_id = player.get('team', player.get('team_code', 0))
                    club_counts[club_id] = club_counts.get(club_id, 0) + 1
            
            for club_id, count in club_counts.items():
                if count > self.MAX_PLAYERS_PER_CLUB:
                    result['status'] = 'fail'
                    result['messages'].append({
                        'code': 'CLUB_LIMIT_EXCEEDED',
                        'level': 'fail',
                        'message': f'Too many players from club {club_id}: {count}',
                        'details': f'Maximum {self.MAX_PLAYERS_PER_CLUB} players per club allowed, got {count}'
                    })
                    
        except Exception as e:
            result['status'] = 'fail'
            result['messages'].append({
                'code': 'SQUAD_CONSTRAINT_ERROR',
                'level': 'error',
                'message': 'Error validating squad constraints',
                'details': str(e)
            })
    
    def _validate_budget(self, transfers: List[Dict], current_squad: List[Dict], budget: float, result: Dict):
        """Validate budget constraints"""
        try:
            total_cost = 0
            total_sold = 0
            
            # Calculate total cost of transfers
            for transfer in transfers:
                player_out = transfer.get('element_out') or transfer.get('out')
                player_in = transfer.get('element_in') or transfer.get('in')
                
                # Get player prices
                sold_price = 0
                bought_price = 0
                
                if player_out and isinstance(player_out, dict):
                    sold_price = player_out.get('now_cost', player_out.get('selling_price', 0))
                
                if player_in and isinstance(player_in, dict):
                    bought_price = player_in.get('now_cost', player_in.get('selling_price', 0))
                
                total_sold += sold_price
                total_cost += bought_price
            
            # Calculate final budget
            final_budget = budget + total_sold - total_cost
            
            if final_budget < 0:
                result['status'] = 'fail'
                result['messages'].append({
                    'code': 'INSUFFICIENT_BUDGET',
                    'level': 'fail',
                    'message': f'Insufficient budget: {final_budget / 10:.1f}m needed',
                    'details': f'Budget would be negative after transfers. Available: {budget / 10:.1f}m, Cost: {(total_cost - total_sold) / 10:.1f}m'
                })
                
        except Exception as e:
            result['status'] = 'fail'
            result['messages'].append({
                'code': 'BUDGET_VALIDATION_ERROR',
                'level': 'error',
                'message': 'Error validating budget',
                'details': str(e)
            })
    
    def _validate_formation(self, transfers: List[Dict], current_squad: List[Dict], result: Dict):
        """Validate formation validity"""
        try:
            # Simulate the final squad after transfers
            final_squad = list(current_squad)  # Copy current squad
            
            # Apply transfers
            for transfer in transfers:
                player_out = transfer.get('element_out') or transfer.get('out')
                player_in = transfer.get('element_in') or transfer.get('in')
                
                # Remove player_out
                if player_out and isinstance(player_out, dict):
                    final_squad = [p for p in final_squad if p.get('id') != player_out.get('id')]
                
                # Add player_in
                if player_in and isinstance(player_in, dict):
                    final_squad.append(player_in)
            
            # Get starting XI (first 11 players)
            starting_xi = final_squad[:11]  # Simplified - in reality would depend on user selection
            
            # Count positions in starting XI
            position_counts = {1: 0, 2: 0, 3: 0, 4: 0}  # GK, DEF, MID, FWD
            for player in starting_xi:
                if isinstance(player, dict):
                    pos_type = player.get('element_type', 0)
                    if pos_type in position_counts:
                        position_counts[pos_type] += 1
            
            # Create formation array [GK, DEF, MID, FWD]
            formation = [position_counts[1], position_counts[2], position_counts[3], position_counts[4]]
            
            # Check if formation is allowed
            if formation not in self.ALLOWED_FORMATIONS:
                # Try to find closest valid formation
                valid_formations_str = [f"{f[1]}-{f[2]}-{f[3]}" for f in self.ALLOWED_FORMATIONS if f[1] > 0]
                result['messages'].append({
                    'code': 'INVALID_FORMATION',
                    'level': 'warn',
                    'message': f'Formation {formation[1]}-{formation[2]}-{formation[3]} may be invalid',
                    'details': f'Valid formations: {", ".join(valid_formations_str)}'
                })
                
        except Exception as e:
            result['messages'].append({
                'code': 'FORMATION_VALIDATION_ERROR',
                'level': 'error',
                'message': 'Error validating formation',
                'details': str(e)
            })
    
    def _validate_chips_and_transfers(self, transfers: List[Dict], gameweek: int, chips: Optional[Dict], result: Dict):
        """Validate chip usage and transfer rules"""
        try:
            # Check if wildcard or freehit is active
            wildcard_active = chips and chips.get('wildcard', False)
            freehit_active = chips and chips.get('freehit', False)
            
            # Normal transfer limit check (unless wildcard/freehit active)
            if not wildcard_active and not freehit_active:
                if len(transfers) > self.TRANSFERS_PER_GW:
                    result['messages'].append({
                        'code': 'TRANSFER_LIMIT_EXCEEDED',
                        'level': 'warn',
                        'message': f'Too many transfers: {len(transfers)}',
                        'details': f'Max {self.TRANSFERS_PER_GW} transfers per gameweek (unless using wildcard/freehit)'
                    })
            
            # Chip conflict checks would go here if we had more chip information
            
        except Exception as e:
            result['messages'].append({
                'code': 'CHIP_VALIDATION_ERROR',
                'level': 'error',
                'message': 'Error validating chips and transfers',
                'details': str(e)
            })
    
    def _validate_player_availability(self, transfers: List[Dict], result: Dict):
        """Validate player availability (injury, suspension, etc.)"""
        try:
            for i, transfer in enumerate(transfers):
                player_in = transfer.get('element_in') or transfer.get('in')
                
                if not player_in or not isinstance(player_in, dict):
                    continue
                
                # Check player status
                status = player_in.get('status', 'a')  # 'a' = available
                news = player_in.get('news', '')
                
                # Check if player is unavailable
                if status != 'a':
                    result['messages'].append({
                        'code': 'PLAYER_UNAVAILABLE',
                        'level': 'warn',
                        'message': f'Player {player_in.get("web_name", "Unknown")} is {status}',
                        'details': f'Player status: {status}. News: {news}'
                    })
                
                # Check chance of playing
                chance_next = player_in.get('chance_of_playing_next_round')
                if chance_next is not None and chance_next < 75:
                    level = 'fail' if chance_next < 25 else 'warn'
                    if level == 'fail':
                        result['status'] = 'fail'
                    result['messages'].append({
                        'code': 'LOW_CHANCE_OF_PLAYING',
                        'level': level,
                        'message': f'Player {player_in.get("web_name", "Unknown")} chance of playing: {chance_next}%',
                        'details': f'Player has only {chance_next}% chance of playing next round'
                    })
                
        except Exception as e:
            result['messages'].append({
                'code': 'AVAILABILITY_VALIDATION_ERROR',
                'level': 'error',
                'message': 'Error validating player availability',
                'details': str(e)
            })

# Global transfer validator instance
transfer_validator = TransferValidator()