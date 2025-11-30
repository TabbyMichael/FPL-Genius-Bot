import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
from services.fpl_api import FPLAPI

@pytest.mark.asyncio
async def test_session_expiration_with_buffer():
    """Test session expiration checking with buffer time"""
    # Create FPLAPI with session credentials
    api = FPLAPI(session_id='test_session_id', csrf_token='test_csrf_token')
    
    # Initially, session should be expired (no auth time)
    assert await api._is_session_expired() is True
    
    # Set auth time to now
    api.last_auth_time = time.time()
    # Session should not be expired
    assert await api._is_session_expired() is False
    
    # Set auth time to just before buffer time (should be expired)
    api.last_auth_time = time.time() - (api.session_expires_in - api.min_session_time + 1)
    # Session should be expired
    assert await api._is_session_expired() is True

@pytest.mark.asyncio
async def test_session_validity_check():
    """Test session validity checking"""
    async with FPLAPI(session_id='test_session_id', csrf_token='test_csrf_token') as api:
        # Without authenticated session, should return False
        assert await api._is_session_valid() is False
        
        # Create mock authenticated session
        mock_session = AsyncMock()
        api.authenticated_session = mock_session
        
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        
        # Mock context manager properly
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_context)
        
        # Should return True for valid session
        result = await api._is_session_valid()
        assert result is True
        
        # Test with failed response
        mock_response.status = 401
        result = await api._is_session_valid()
        assert result is False

@pytest.mark.asyncio
async def test_ensure_authenticated():
    """Test ensure authenticated functionality"""
    async with FPLAPI(session_id='test_session_id', csrf_token='test_csrf_token') as api:
        # Test when no authenticated session exists
        with patch.object(api, '_authenticate', return_value=True) as mock_auth:
            result = await api._ensure_authenticated()
            assert result is True
            assert mock_auth.called
        
        # Test when session exists and is valid
        api.authenticated_session = AsyncMock()
        api.last_auth_time = time.time()
        
        with patch.object(api, '_is_session_valid', return_value=True) as mock_valid:
            with patch.object(api, '_authenticate', return_value=True) as mock_auth:
                result = await api._ensure_authenticated()
                assert result is True
                assert mock_valid.called
                assert not mock_auth.called  # Should not re-authenticate

@pytest.mark.asyncio
async def test_ensure_authenticated_with_expired_session():
    """Test ensure authenticated with expired session"""
    async with FPLAPI(session_id='test_session_id', csrf_token='test_csrf_token') as api:
        # Set up expired session
        api.authenticated_session = AsyncMock()
        api.last_auth_time = time.time() - (api.session_expires_in + 1)
        
        # Mock session validity check to return False
        with patch.object(api, '_is_session_valid', return_value=False):
            with patch.object(api, '_authenticate', return_value=True) as mock_auth:
                result = await api._ensure_authenticated()
                assert result is True
                assert mock_auth.called

@pytest.mark.asyncio
async def test_ensure_authenticated_with_invalid_session():
    """Test ensure authenticated with invalid session"""
    async with FPLAPI(session_id='test_session_id', csrf_token='test_csrf_token') as api:
        # Set up valid but invalid session
        api.authenticated_session = AsyncMock()
        api.last_auth_time = time.time()
        
        # Mock session validity check to return False
        with patch.object(api, '_is_session_valid', return_value=False):
            with patch.object(api, '_authenticate', return_value=True) as mock_auth:
                result = await api._ensure_authenticated()
                assert result is True
                assert mock_auth.called

@pytest.mark.asyncio
async def test_fallback_authentication():
    """Test fallback to traditional authentication"""
    async with FPLAPI(username='test_user', password='test_pass') as api:
        # Mock the session creation
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session
            
            result = await api._authenticate()
            assert result is True
            # Should have been called with traditional auth
            mock_session_class.assert_called()

@pytest.mark.asyncio
async def test_no_credentials_authentication():
    """Test authentication with no credentials"""
    async with FPLAPI() as api:
        result = await api._authenticate()
        assert result is False

@pytest.mark.asyncio
async def test_team_data_with_auth_check():
    """Test team data fetching with authentication check"""
    async with FPLAPI(team_id='123456', session_id='test_session_id', csrf_token='test_csrf_token') as api:
        # Mock ensure_authenticated to return True
        with patch.object(api, '_ensure_authenticated', return_value=True):
            # Mock the request
            with patch.object(api, '_make_request_with_retry', return_value={'data': 'test'}):
                result = await api.get_team_data()
                assert result == {'data': 'test'}

@pytest.mark.asyncio
async def test_team_picks_with_auth_check():
    """Test team picks fetching with authentication check"""
    async with FPLAPI(team_id='123456', session_id='test_session_id', csrf_token='test_csrf_token') as api:
        # Mock ensure_authenticated to return True
        with patch.object(api, '_ensure_authenticated', return_value=True):
            # Mock the request
            with patch.object(api, '_make_request_with_retry', return_value={'picks': []}):
                result = await api.get_team_picks(1)
                assert result == {'picks': []}