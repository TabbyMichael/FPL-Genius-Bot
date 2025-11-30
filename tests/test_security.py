import pytest
import os
import tempfile
from utils.security import hash_sensitive_data, log_authentication_attempt, log_transfer_execution, log_api_call, log_database_operation, log_security_event

def test_hash_sensitive_data():
    """Test hashing of sensitive data"""
    # Test with string data
    result = hash_sensitive_data("sensitive_data")
    assert isinstance(result, str)
    assert len(result) == 16  # Should be 16 characters long
    
    # Test with numeric data
    result = hash_sensitive_data(12345)
    assert isinstance(result, str)
    assert len(result) == 16
    
    # Test with None
    result = hash_sensitive_data(None)
    assert result is None

def test_log_authentication_attempt():
    """Test authentication attempt logging"""
    # Create a temporary log file for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Redirect audit logger to temporary file
        import logging
        audit_logger = logging.getLogger('audit')
        
        # Clear existing handlers
        audit_logger.handlers.clear()
        
        # Add temporary file handler
        temp_log_file = os.path.join(temp_dir, 'audit.log')
        handler = logging.FileHandler(temp_log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)
        
        # Test logging
        log_authentication_attempt(True, "session")
        log_authentication_attempt(False, "traditional")
        
        # Check that log entries were written
        handler.flush()
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
            assert "Authentication attempt" in log_content
            assert "Success: True" in log_content
            assert "Success: False" in log_content
            assert "Method: session" in log_content
            assert "Method: traditional" in log_content

def test_log_transfer_execution():
    """Test transfer execution logging"""
    # Create a temporary log file for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Redirect audit logger to temporary file
        import logging
        audit_logger = logging.getLogger('audit')
        
        # Clear existing handlers
        audit_logger.handlers.clear()
        
        # Add temporary file handler
        temp_log_file = os.path.join(temp_dir, 'audit.log')
        handler = logging.FileHandler(temp_log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)
        
        # Test logging
        log_transfer_execution(123, 456, True)
        log_transfer_execution(789, 101, False)
        
        # Check that log entries were written
        handler.flush()
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
            assert "Transfer execution" in log_content
            assert "Out: 123" in log_content
            assert "In: 456" in log_content
            assert "Success: True" in log_content
            assert "Out: 789" in log_content
            assert "In: 101" in log_content
            assert "Success: False" in log_content

def test_log_api_call():
    """Test API call logging"""
    # Create a temporary log file for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Redirect audit logger to temporary file
        import logging
        audit_logger = logging.getLogger('audit')
        
        # Clear existing handlers
        audit_logger.handlers.clear()
        
        # Add temporary file handler
        temp_log_file = os.path.join(temp_dir, 'audit.log')
        handler = logging.FileHandler(temp_log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)
        
        # Test logging
        log_api_call("/api/test", "GET", 200)
        log_api_call("/api/test", "POST", 500)
        log_api_call("/api/test", "GET", None)
        
        # Check that log entries were written
        handler.flush()
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
            assert "API Call" in log_content
            assert "Endpoint: /api/test" in log_content
            assert "Method: GET" in log_content
            assert "Method: POST" in log_content
            assert "Status: 200" in log_content
            assert "Status: 500" in log_content
            assert "Status: None" in log_content

def test_log_database_operation():
    """Test database operation logging"""
    # Create a temporary log file for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Redirect audit logger to temporary file
        import logging
        audit_logger = logging.getLogger('audit')
        
        # Clear existing handlers
        audit_logger.handlers.clear()
        
        # Add temporary file handler
        temp_log_file = os.path.join(temp_dir, 'audit.log')
        handler = logging.FileHandler(temp_log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)
        
        # Test logging
        log_database_operation("INSERT", "players", 123)
        log_database_operation("UPDATE", "transfers", None)
        
        # Check that log entries were written
        handler.flush()
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
            assert "Database Operation" in log_content
            assert "Type: INSERT" in log_content
            assert "Table: players" in log_content
            assert "Record ID: 123" in log_content
            assert "Type: UPDATE" in log_content
            assert "Table: transfers" in log_content
            assert "Record ID: None" in log_content

def test_log_security_event():
    """Test security event logging"""
    # Create a temporary log file for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Redirect audit logger to temporary file
        import logging
        audit_logger = logging.getLogger('audit')
        
        # Clear existing handlers
        audit_logger.handlers.clear()
        
        # Add temporary file handler
        temp_log_file = os.path.join(temp_dir, 'audit.log')
        handler = logging.FileHandler(temp_log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)
        
        # Test logging
        log_security_event("AUTH_FAILURE", "Failed login attempt", "WARNING")
        log_security_event("DATA_ACCESS", "Sensitive data accessed", "INFO")
        
        # Check that log entries were written
        handler.flush()
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
            assert "Security Event" in log_content
            assert "Type: AUTH_FAILURE" in log_content
            assert "Description: Failed login attempt" in log_content
            assert "Severity: WARNING" in log_content
            assert "Type: DATA_ACCESS" in log_content
            assert "Description: Sensitive data accessed" in log_content
            assert "Severity: INFO" in log_content