import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.transfer_validator import TransferValidator

class TestTransferValidator(unittest.TestCase):
    """Test cases for the enhanced transfer validator"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.validator = TransferValidator()
    
    def test_validate_single_valid_transfer(self):
        """Test validation of a single valid transfer"""
        transfers = [{
            'element_out': {'id': 1, 'web_name': 'Player A'},
            'element_in': {'id': 2, 'web_name': 'Player B'}
        }]
        current_squad = [
            {'id': 1, 'element_type': 1, 'team': 1},  # GK
            {'id': 3, 'element_type': 2, 'team': 2},  # DEF
            {'id': 4, 'element_type': 2, 'team': 3},  # DEF
            {'id': 5, 'element_type': 2, 'team': 4},  # DEF
            {'id': 6, 'element_type': 2, 'team': 5},  # DEF
            {'id': 7, 'element_type': 3, 'team': 6},  # MID
            {'id': 8, 'element_type': 3, 'team': 7},  # MID
            {'id': 9, 'element_type': 3, 'team': 8},  # MID
            {'id': 10, 'element_type': 3, 'team': 9}, # MID
            {'id': 11, 'element_type': 3, 'team': 10},# MID
            {'id': 12, 'element_type': 4, 'team': 11},# FWD
            {'id': 13, 'element_type': 4, 'team': 12},# FWD
            {'id': 14, 'element_type': 4, 'team': 13},# FWD
            {'id': 15, 'element_type': 1, 'team': 14},# GK
            {'id': 16, 'element_type': 2, 'team': 15},# DEF
        ]
        budget = 1000  # 100.0m
        
        result = self.validator.validate_transfers(transfers, current_squad, budget)
        
        # Should pass with no critical errors
        self.assertIn(result['status'], ['pass', 'warn'])
    
    def test_validate_invalid_squad_size(self):
        """Test validation fails with invalid squad size"""
        transfers = [{
            'element_out': {'id': 1, 'web_name': 'Player A'},
            'element_in': {'id': 2, 'web_name': 'Player B'}
        }]
        # Invalid squad size (too small)
        current_squad = [
            {'id': 1, 'element_type': 1, 'team': 1},  # GK
            {'id': 3, 'element_type': 2, 'team': 2},  # DEF
        ]
        budget = 1000
        
        result = self.validator.validate_transfers(transfers, current_squad, budget)
        
        # Should fail due to invalid squad size
        self.assertEqual(result['status'], 'fail')
        messages = [msg['code'] for msg in result['messages']]
        self.assertIn('INVALID_SQUAD_SIZE', messages)
    
    def test_validate_insufficient_budget(self):
        """Test validation fails with insufficient budget"""
        transfers = [{
            'element_out': {'id': 1, 'web_name': 'Player A', 'now_cost': 50},  # 5.0m
            'element_in': {'id': 2, 'web_name': 'Player B', 'now_cost': 200}   # 20.0m
        }]
        current_squad = [
            {'id': 1, 'element_type': 1, 'team': 1},  # GK
            {'id': 3, 'element_type': 2, 'team': 2},  # DEF
            {'id': 4, 'element_type': 2, 'team': 3},  # DEF
            {'id': 5, 'element_type': 2, 'team': 4},  # DEF
            {'id': 6, 'element_type': 2, 'team': 5},  # DEF
            {'id': 7, 'element_type': 3, 'team': 6},  # MID
            {'id': 8, 'element_type': 3, 'team': 7},  # MID
            {'id': 9, 'element_type': 3, 'team': 8},  # MID
            {'id': 10, 'element_type': 3, 'team': 9}, # MID
            {'id': 11, 'element_type': 3, 'team': 10},# MID
            {'id': 12, 'element_type': 4, 'team': 11},# FWD
            {'id': 13, 'element_type': 4, 'team': 12},# FWD
            {'id': 14, 'element_type': 4, 'team': 13},# FWD
            {'id': 15, 'element_type': 1, 'team': 14},# GK
            {'id': 16, 'element_type': 2, 'team': 15},# DEF
        ]
        budget = 50  # 5.0m - not enough for the transfer
        
        result = self.validator.validate_transfers(transfers, current_squad, budget)
        
        # Should fail due to insufficient budget
        self.assertEqual(result['status'], 'fail')
        messages = [msg['code'] for msg in result['messages']]
        self.assertIn('INSUFFICIENT_BUDGET', messages)
    
    def test_validate_too_many_transfers(self):
        """Test validation warns with too many transfers"""
        # Create 5 transfers (more than the normal limit of 2)
        transfers = []
        for i in range(5):
            transfers.append({
                'element_out': {'id': i+1, 'web_name': f'Player Out {i+1}'},
                'element_in': {'id': i+10, 'web_name': f'Player In {i+1}'}
            })
        
        current_squad = [
            {'id': 1, 'element_type': 1, 'team': 1},  # GK
            {'id': 3, 'element_type': 2, 'team': 2},  # DEF
            {'id': 4, 'element_type': 2, 'team': 3},  # DEF
            {'id': 5, 'element_type': 2, 'team': 4},  # DEF
            {'id': 6, 'element_type': 2, 'team': 5},  # DEF
            {'id': 7, 'element_type': 3, 'team': 6},  # MID
            {'id': 8, 'element_type': 3, 'team': 7},  # MID
            {'id': 9, 'element_type': 3, 'team': 8},  # MID
            {'id': 10, 'element_type': 3, 'team': 9}, # MID
            {'id': 11, 'element_type': 3, 'team': 10},# MID
            {'id': 12, 'element_type': 4, 'team': 11},# FWD
            {'id': 13, 'element_type': 4, 'team': 12},# FWD
            {'id': 14, 'element_type': 4, 'team': 13},# FWD
            {'id': 15, 'element_type': 1, 'team': 14},# GK
            {'id': 16, 'element_type': 2, 'team': 15},# DEF
        ]
        budget = 1000
        
        result = self.validator.validate_transfers(transfers, current_squad, budget)
        
        # Should warn (not fail) about too many transfers
        messages = [msg['code'] for msg in result['messages']]
        self.assertIn('TRANSFER_LIMIT_EXCEEDED', messages)
    
    def test_validate_player_unavailability(self):
        """Test validation warns with unavailable players"""
        transfers = [{
            'element_out': {'id': 1, 'web_name': 'Player A'},
            'element_in': {'id': 2, 'web_name': 'Player B', 'status': 'i', 'news': 'Injured'}
        }]
        current_squad = [
            {'id': 1, 'element_type': 1, 'team': 1},  # GK
            {'id': 3, 'element_type': 2, 'team': 2},  # DEF
            {'id': 4, 'element_type': 2, 'team': 3},  # DEF
            {'id': 5, 'element_type': 2, 'team': 4},  # DEF
            {'id': 6, 'element_type': 2, 'team': 5},  # DEF
            {'id': 7, 'element_type': 3, 'team': 6},  # MID
            {'id': 8, 'element_type': 3, 'team': 7},  # MID
            {'id': 9, 'element_type': 3, 'team': 8},  # MID
            {'id': 10, 'element_type': 3, 'team': 9}, # MID
            {'id': 11, 'element_type': 3, 'team': 10},# MID
            {'id': 12, 'element_type': 4, 'team': 11},# FWD
            {'id': 13, 'element_type': 4, 'team': 12},# FWD
            {'id': 14, 'element_type': 4, 'team': 13},# FWD
            {'id': 15, 'element_type': 1, 'team': 14},# GK
            {'id': 16, 'element_type': 2, 'team': 15},# DEF
        ]
        budget = 1000
        
        result = self.validator.validate_transfers(transfers, current_squad, budget)
        
        # Should warn about unavailable player
        messages = [msg['code'] for msg in result['messages']]
        self.assertIn('PLAYER_UNAVAILABLE', messages)

if __name__ == '__main__':
    unittest.main()