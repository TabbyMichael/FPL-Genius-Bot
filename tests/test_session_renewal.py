import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
from services.fpl_api import FPLAPI

@pytest.mark.asyncio
async def test_session_expiration_check():
    """Test session expiration checking"""
    # Create FPLAPI with session credentials
    api = FPLAPI(session_id='test_session_id', csrf_token='test_csrf_token')
    
    # Initially, session should be expired (no auth time)
    assert await api._is_session_expired() is True
    
    # Set auth time to now
    api.last_auth_time = time.time()
    # Session should not be expired
    assert await api._is_session_expired() is False
    
    # Set auth time to 2 hours ago
    api.last_auth_time = time.time() - 7200  # 2 hours ago
    # Session should be expired
    assert await api._is_session_expired() is True

@pytest.mark.asyncio
async def test_session_renewal_on_expired_session():
    """Test that session is renewed when expired"""
    with patch('aiohttp.ClientSession') as mock_session_class:
        # Mock the session
        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # Create FPLAPI with session credentials
        async with FPLAPI(session_id='test_session_id', csrf_token='test_csrf_token', team_id='123456') as api:
            # Set session to expired
            api.last_auth_time = time.time() - 7200  # 2 hours ago
            
            # Mock authentication to return True
            with patch.object(api, '_authenticate', return_value=True) as mock_auth:
                # Try to get team data (should trigger re-auth)
                result = await api.get_team_data()
                # Authentication should have been called
                assert mock_auth.called

@pytest.mark.asyncio
async def test_transfer_execution_with_session_renewal():
    """Test transfer execution with session renewal"""
    async with FPLAPI(team_id='123456') as api:
        # Set session to expired
        api.last_auth_time = time.time() - 7200  # 2 hours ago
        
        # Mock authentication to return True
        with patch.object(api, '_authenticate', return_value=True) as mock_auth:
            # Create a mock authenticated session
            mock_authenticated_session = AsyncMock()
            api.authenticated_session = mock_authenticated_session
            
            # Mock successful transfer response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={'status': 'success'})
            
            # Properly mock the context manager for the POST request
            mock_post_context = AsyncMock()
            mock_post_context.__aenter__.return_value = mock_response
            mock_authenticated_session.post.return_value = mock_post_context
            
            # Test transfer execution
            transfers = [{
                "element_in": 1,
                "element_out": 2,
                "purchase_price": 50,
                "selling_price": 45
            }]
            
            result = await api.execute_transfers(transfers)
            # Authentication should have been called for session renewal
            assert mock_auth.called
            assert isinstance(result, bool)