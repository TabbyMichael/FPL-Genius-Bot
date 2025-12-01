import logging
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

# Get team ID and hash it for logging
TEAM_ID = os.getenv("FPL_TEAM_ID", "unknown")
TEAM_ID_HASH = hashlib.sha256(TEAM_ID.encode()).hexdigest()[:16] if TEAM_ID else "unknown"

# --- Audit Logger Setup ---
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)

# Create a file handler for the audit log if it doesn't have one
if not audit_logger.handlers:
    # Make sure the logs directory exists
    if not os.path.exists('logs'):
        os.makedirs('logs')
    audit_handler = logging.FileHandler('logs/audit.log')
    audit_handler.setLevel(logging.INFO)

    # Create a formatter and set it for the handler
    audit_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    audit_handler.setFormatter(audit_formatter)

    # Add the handler to the logger
    audit_logger.addHandler(audit_handler)

# --- Security Logging Functions ---

def log_authentication_attempt(success: bool, method: str):
    """Logs an authentication attempt."""
    status = "SUCCESS" if success else "FAILURE"
    audit_logger.info(f"Authentication Attempt - Method: {method}, Status: {status}, Team: {TEAM_ID_HASH}")

def log_transfer_execution(player_out_id: int, player_in_id: int, success: bool):
    """Logs a transfer execution."""
    status = "SUCCESS" if success else "FAILURE"
    audit_logger.info(f"Transfer Execution - Player Out: {player_out_id}, Player In: {player_in_id}, Status: {status}, Team: {TEAM_ID_HASH}")

def log_api_call(endpoint: str, method: str, status: int):
    """Logs an API call."""
    audit_logger.info(f"API Call - Endpoint: {endpoint}, Method: {method}, Team: {TEAM_ID_HASH}, Status: {status}")

def log_database_operation(operation: str, success: bool):
    """Logs a database operation."""
    status = "SUCCESS" if success else "FAILURE"
    audit_logger.info(f"Database Operation - Operation: {operation}, Status: {status}, Team: {TEAM_ID_HASH}")

def log_security_event(message: str):
    """Logs a generic security event."""
    audit_logger.info(f"Security Event - Message: {message}, Team: {TEAM_ID_HASH}")
