import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# FPL Credentials
FPL_USERNAME = os.getenv('FPL_USERNAME')
FPL_PASSWORD = os.getenv('FPL_PASSWORD')
TEAM_ID = os.getenv('TEAM_ID')

# API Settings
FPL_BASE_URL = "https://fantasy.premierleague.com/api"
MAX_TRANSFERS = 2
FREE_TRANSFERS = 1
TRANSFER_COST = 4

# Bot Settings
BUDGET_BUFFER = 0.5  # Keep some money in reserve
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')