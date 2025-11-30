import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def format_currency(value: int) -> str:
    """Convert pence to pounds format"""
    return f"£{value/10:.1f}m"

def calculate_squad_value(squad: List[Dict]) -> int:
    """Calculate total value of squad"""
    return sum(player.get('now_cost', 0) for player in squad)

def get_position_name(position_id: int) -> str:
    """Convert position ID to name"""
    positions = {1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'}
    return positions.get(position_id, 'Unknown')

def is_player_available(player: Dict) -> bool:
    """Check if player is available for selection"""
    # Check status, injuries, etc.
    status = player.get('status', 'a')
    return status == 'a'  # 'a' means available