import logging
import hashlib
import os
from datetime import datetime
from config.settings import FPL_USERNAME, TEAM_ID

# Configure audit logging
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)

# Create audit log file handler if it doesn't exist
if not audit_logger.handlers:
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Create file handler for audit logs
    audit_handler = logging.FileHandler('logs/audit.log')
    audit_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    audit_handler.setFormatter(formatter)
    
    # Add handler to logger
    audit_logger.addHandler(audit_handler)

def hash_sensitive_data(data):
    """Hash sensitive data for logging"""
    if data is None:
        return None
    return hashlib.sha256(str(data).encode()).hexdigest()[:16]

def log_authentication_attempt(success: bool, method: str = "unknown"):
    """Log authentication attempts"""
    audit_logger.info(f"Authentication attempt - Success: {success}, Method: {method}")

def log_transfer_execution(player_out_id: int, player_in_id: int, success: bool):
    """Log transfer execution attempts"""
    audit_logger.info(f"Transfer execution - Out: {player_out_id}, In: {player_in_id}, Success: {success}")

def log_api_call(endpoint: str, method: str, status_code: int = None):
    """Log API calls for monitoring"""
    masked_team_id = hash_sensitive_data(TEAM_ID) if TEAM_ID else "UNKNOWN"
    audit_logger.info(f"API Call - Endpoint: {endpoint}, Method: {method}, Team: {masked_team_id}, Status: {status_code}")

def log_database_operation(operation: str, table: str, record_id: int = None):
    """Log database operations"""
    audit_logger.info(f"Database Operation - Type: {operation}, Table: {table}, Record ID: {record_id}")

def log_security_event(event_type: str, description: str, severity: str = "INFO"):
    """Log security-related events"""
    audit_logger.info(f"Security Event - Type: {event_type}, Description: {description}, Severity: {severity}")