import os
import json
import logging
from typing import Dict, List, Optional
from services.fpl_api import FPLAPI
from config.settings import FPL_USERNAME, FPL_PASSWORD, TEAM_ID, SESSION_ID, CSRF_TOKEN

logger = logging.getLogger(__name__)

class AccountManager:
    """Manages multiple FPL accounts"""
    
    def __init__(self, accounts_file: str = "accounts.json"):
        self.accounts_file = accounts_file
        self.accounts = self._load_accounts()
        self.active_account = None
        
    def _load_accounts(self) -> Dict[str, Dict]:
        """Load accounts from file or environment variables"""
        accounts = {}
        
        # Check if accounts file exists
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, 'r') as f:
                    accounts = json.load(f)
                logger.info(f"Loaded {len(accounts)} accounts from {self.accounts_file}")
            except Exception as e:
                logger.error(f"Error loading accounts from file: {str(e)}")
        
        # Add default account from environment variables if not already present
        default_account_id = "default"
        if default_account_id not in accounts:
            # Check if we have the required environment variables
            if FPL_USERNAME or (SESSION_ID and CSRF_TOKEN and TEAM_ID):
                accounts[default_account_id] = {
                    "username": FPL_USERNAME,
                    "password": FPL_PASSWORD,
                    "session_id": SESSION_ID,
                    "csrf_token": CSRF_TOKEN,
                    "team_id": TEAM_ID,
                    "name": "Default Account"
                }
                logger.info("Added default account from environment variables")
        
        return accounts
    
    def save_accounts(self):
        """Save accounts to file"""
        try:
            with open(self.accounts_file, 'w') as f:
                json.dump(self.accounts, f, indent=2)
            logger.info(f"Saved {len(self.accounts)} accounts to {self.accounts_file}")
        except Exception as e:
            logger.error(f"Error saving accounts to file: {str(e)}")
    
    def add_account(self, account_id: str, username: str = None, password: str = None, 
                   session_id: str = None, csrf_token: str = None, team_id: str = None,
                   name: str = None):
        """Add a new account"""
        self.accounts[account_id] = {
            "username": username,
            "password": password,
            "session_id": session_id,
            "csrf_token": csrf_token,
            "team_id": team_id,
            "name": name or account_id
        }
        self.save_accounts()
        logger.info(f"Added account {account_id}")
    
    def remove_account(self, account_id: str):
        """Remove an account"""
        if account_id in self.accounts:
            del self.accounts[account_id]
            if self.active_account == account_id:
                self.active_account = None
            self.save_accounts()
            logger.info(f"Removed account {account_id}")
    
    def get_account(self, account_id: str) -> Optional[Dict]:
        """Get account details"""
        return self.accounts.get(account_id)
    
    def list_accounts(self) -> List[str]:
        """List all account IDs"""
        return list(self.accounts.keys())
    
    def set_active_account(self, account_id: str) -> bool:
        """Set the active account"""
        if account_id in self.accounts:
            self.active_account = account_id
            logger.info(f"Set active account to {account_id}")
            return True
        else:
            logger.error(f"Account {account_id} not found")
            return False
    
    def get_active_account(self) -> Optional[Dict]:
        """Get the active account details"""
        if self.active_account:
            return self.accounts.get(self.active_account)
        return None
    
    def get_fpl_api_for_account(self, account_id: str = None) -> Optional[FPLAPI]:
        """Get FPLAPI instance for a specific account"""
        # Use active account if none specified
        if not account_id:
            account_id = self.active_account
        
        if not account_id:
            logger.error("No account specified and no active account set")
            return None
        
        account = self.accounts.get(account_id)
        if not account:
            logger.error(f"Account {account_id} not found")
            return None
        
        # Create FPLAPI instance with account credentials
        api = FPLAPI()
        
        # We'll need to modify FPLAPI to accept credentials
        # For now, we'll set environment variables temporarily
        return api
    
    async def validate_account(self, account_id: str) -> bool:
        """Validate that an account can connect to FPL"""
        account = self.accounts.get(account_id)
        if not account:
            return False
        
        try:
            async with FPLAPI() as api:
                # Temporarily set account credentials
                # This is a simplified validation
                team_id = account.get("team_id")
                if team_id:
                    team_data = await api.get_team_data()
                    return team_data is not None
                else:
                    # Just check if we can get bootstrap data
                    bootstrap_data = await api.get_bootstrap_data()
                    return bootstrap_data is not None
        except Exception as e:
            logger.error(f"Error validating account {account_id}: {str(e)}")
            return False

# Global account manager instance
account_manager = AccountManager()