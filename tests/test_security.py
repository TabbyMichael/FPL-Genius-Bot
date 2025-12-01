import pytest
from unittest.mock import patch, mock_open
from utils import security

@patch('utils.security.audit_logger.info')
def test_log_authentication_attempt(mock_log):
    """Test logging of authentication attempts."""
    security.log_authentication_attempt(True, "test_method")
    mock_log.assert_called_once_with("Authentication Attempt - Method: test_method, Status: SUCCESS, Team: b23a6a8439c0dde5")

    security.log_authentication_attempt(False, "test_method")
    mock_log.assert_called_with("Authentication Attempt - Method: test_method, Status: FAILURE, Team: b23a6a8439c0dde5")

@patch('utils.security.audit_logger.info')
def test_log_transfer_execution(mock_log):
    """Test logging of transfer executions."""
    security.log_transfer_execution(1, 2, True)
    mock_log.assert_called_once_with("Transfer Execution - Player Out: 1, Player In: 2, Status: SUCCESS, Team: b23a6a8439c0dde5")

    security.log_transfer_execution(3, 4, False)
    mock_log.assert_called_with("Transfer Execution - Player Out: 3, Player In: 4, Status: FAILURE, Team: b23a6a8439c0dde5")

@patch('utils.security.audit_logger.info')
def test_log_api_call(mock_log):
    """Test logging of API calls."""
    security.log_api_call("http://test.com", "GET", 200)
    mock_log.assert_called_once_with("API Call - Endpoint: http://test.com, Method: GET, Team: b23a6a8439c0dde5, Status: 200")
