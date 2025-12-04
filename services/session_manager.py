import asyncio
import logging
import time
from typing import Dict, Optional
from cryptography.fernet import Fernet
import os
from config.settings import TEAM_ID
from utils.security import log_authentication_attempt, log_security_event

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages authentication sessions with proactive refresh capabilities"""
    
    def __init__(self):
        # Generate or load encryption key for securing refresh tokens
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Session storage (in production, this should be in a secure database)
        self.sessions = {}  # team_id -> session_data
        
        # Refresh configuration
        self.refresh_window = 300  # 5 minutes before expiry
        self.max_refresh_attempts = 3
        self.refresh_interval = 60  # Check every minute
        
        # Track refresh failures
        self.refresh_failures = {}  # team_id -> failure_count
        
        # Scheduler task
        self.scheduler_task = None
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for securing refresh tokens"""
        key_file = ".session_key"
        
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt_token(self, token: str) -> bytes:
        """Encrypt a token for secure storage"""
        return self.cipher_suite.encrypt(token.encode())
    
    def decrypt_token(self, encrypted_token: bytes) -> str:
        """Decrypt a token for use"""
        return self.cipher_suite.decrypt(encrypted_token).decode()
    
    def store_session(self, team_id: str, session_data: Dict):
        """Store session data securely"""
        # Encrypt sensitive tokens
        if 'session_id' in session_data:
            session_data['session_id_encrypted'] = self.encrypt_token(session_data['session_id'])
            del session_data['session_id']
            
        if 'csrf_token' in session_data:
            session_data['csrf_token_encrypted'] = self.encrypt_token(session_data['csrf_token'])
            del session_data['csrf_token']
            
        if 'refresh_token' in session_data:
            session_data['refresh_token_encrypted'] = self.encrypt_token(session_data['refresh_token'])
            del session_data['refresh_token']
        
        # Store session data
        self.sessions[team_id] = {
            'data': session_data,
            'last_updated': time.time(),
            'expires_at': session_data.get('expires_at', time.time() + 3600)  # Default 1 hour
        }
        
        logger.info(f"Stored session for team {team_id}")
        log_security_event(f"Session stored for team {team_id}")
    
    def get_session(self, team_id: str) -> Optional[Dict]:
        """Retrieve session data"""
        if team_id not in self.sessions:
            return None
            
        session_entry = self.sessions[team_id]
        session_data = session_entry['data'].copy()
        
        # Decrypt sensitive tokens
        if 'session_id_encrypted' in session_data:
            session_data['session_id'] = self.decrypt_token(session_data['session_id_encrypted'])
            del session_data['session_id_encrypted']
            
        if 'csrf_token_encrypted' in session_data:
            session_data['csrf_token'] = self.decrypt_token(session_data['csrf_token_encrypted'])
            del session_data['csrf_token_encrypted']
            
        if 'refresh_token_encrypted' in session_data:
            session_data['refresh_token'] = self.decrypt_token(session_data['refresh_token_encrypted'])
            del session_data['refresh_token_encrypted']
        
        return session_data
    
    def is_session_expiring_soon(self, team_id: str) -> bool:
        """Check if session is expiring soon"""
        if team_id not in self.sessions:
            return True  # No session, needs refresh
            
        session_entry = self.sessions[team_id]
        expires_at = session_entry['expires_at']
        return time.time() > (expires_at - self.refresh_window)
    
    def is_session_valid(self, team_id: str) -> bool:
        """Check if session is still valid"""
        if team_id not in self.sessions:
            return False
            
        session_entry = self.sessions[team_id]
        expires_at = session_entry['expires_at']
        return time.time() < expires_at
    
    async def refresh_session(self, team_id: str, fpl_api_instance) -> bool:
        """Refresh session for a specific team"""
        try:
            logger.info(f"Attempting to refresh session for team {team_id}")
            
            # Increment failure counter
            if team_id not in self.refresh_failures:
                self.refresh_failures[team_id] = 0
            
            # Attempt authentication
            success = await fpl_api_instance._authenticate()
            
            if success:
                # Reset failure counter on success
                self.refresh_failures[team_id] = 0
                
                # Update session data
                session_data = {
                    'session_id': fpl_api_instance.session_id,
                    'csrf_token': fpl_api_instance.csrf_token,
                    'username': fpl_api_instance.username,
                    'team_id': fpl_api_instance.team_id,
                    'expires_at': time.time() + fpl_api_instance.session_expires_in
                }
                
                self.store_session(team_id, session_data)
                logger.info(f"Successfully refreshed session for team {team_id}")
                log_authentication_attempt(True, "refresh")
                return True
            else:
                # Increment failure counter
                self.refresh_failures[team_id] += 1
                logger.error(f"Failed to refresh session for team {team_id} (attempt {self.refresh_failures[team_id]})")
                log_authentication_attempt(False, "refresh")
                
                # Disable account if too many failures
                if self.refresh_failures[team_id] >= self.max_refresh_attempts:
                    logger.error(f"Disabling account {team_id} after {self.max_refresh_attempts} consecutive failures")
                    log_security_event(f"Account {team_id} disabled due to repeated refresh failures")
                    # Mark account as disabled (implementation depends on account manager)
                
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing session for team {team_id}: {str(e)}")
            self.refresh_failures[team_id] = self.refresh_failures.get(team_id, 0) + 1
            log_authentication_attempt(False, "refresh_error")
            return False
    
    async def _scheduler_loop(self, fpl_api_instances: Dict[str, object]):
        """Background scheduler loop to check and refresh sessions"""
        while True:
            try:
                for team_id, api_instance in fpl_api_instances.items():
                    # Check if session needs refresh
                    if self.is_session_expiring_soon(team_id):
                        logger.info(f"Session for team {team_id} expiring soon, refreshing...")
                        await self.refresh_session(team_id, api_instance)
                
                # Wait before next check
                await asyncio.sleep(self.refresh_interval)
                
            except Exception as e:
                logger.error(f"Error in session scheduler loop: {str(e)}")
                await asyncio.sleep(self.refresh_interval)
    
    def start_scheduler(self, fpl_api_instances: Dict[str, object]):
        """Start the background scheduler"""
        if self.scheduler_task is None:
            logger.info("Starting session refresh scheduler")
            self.scheduler_task = asyncio.create_task(self._scheduler_loop(fpl_api_instances))
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        if self.scheduler_task:
            logger.info("Stopping session refresh scheduler")
            self.scheduler_task.cancel()
            self.scheduler_task = None
    
    def get_session_status(self, team_id: str) -> Dict:
        """Get session status for monitoring"""
        if team_id not in self.sessions:
            return {
                'status': 'no_session',
                'valid': False,
                'expiring_soon': True,
                'failure_count': self.refresh_failures.get(team_id, 0)
            }
        
        session_entry = self.sessions[team_id]
        expiring_soon = self.is_session_expiring_soon(team_id)
        valid = self.is_session_valid(team_id)
        
        return {
            'status': 'valid' if valid else 'expired',
            'valid': valid,
            'expiring_soon': expiring_soon,
            'expires_at': session_entry['expires_at'],
            'last_updated': session_entry['last_updated'],
            'failure_count': self.refresh_failures.get(team_id, 0)
        }

# Global session manager instance
session_manager = SessionManager()