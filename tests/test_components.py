#!/usr/bin/env python3
"""
Test script to verify all FPL Bot components work together
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test imports
try:
    from config.settings import FPL_USERNAME, FPL_PASSWORD
    print("✓ Settings module imported successfully")
except Exception as e:
    print(f"✗ Error importing settings: {e}")

try:
    from config.database import Base, engine, get_db
    print("✓ Database module imported successfully")
except Exception as e:
    print(f"✗ Error importing database: {e}")

try:
    from services.fpl_api import FPLAPI
    print("✓ FPL API module imported successfully")
except Exception as e:
    print(f"✗ Error importing FPL API: {e}")

try:
    from services.ml_predictor import MLPredictor
    print("✓ ML Predictor module imported successfully")
except Exception as e:
    print(f"✗ Error importing ML Predictor: {e}")

try:
    from services.transfer_engine import TransferEngine
    print("✓ Transfer Engine module imported successfully")
except Exception as e:
    print(f"✗ Error importing Transfer Engine: {e}")

try:
    from services.lineup_selector import LineupSelector
    print("✓ Lineup Selector module imported successfully")
except Exception as e:
    print(f"✗ Error importing Lineup Selector: {e}")

try:
    from utils.helpers import format_currency, calculate_squad_value
    print("✓ Helpers module imported successfully")
except Exception as e:
    print(f"✗ Error importing Helpers: {e}")

# Test database connection
try:
    db_gen = get_db()
    db = next(db_gen)
    print("✓ Database connection established successfully")
    # Close the connection
    db.close()
except Exception as e:
    print(f"✗ Error establishing database connection: {e}")

print("\nAll components checked!")