import pytest
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
from services.fpl_api import FPLAPI
from config.database import cached_query, clear_query_cache, _query_cache

@pytest.mark.asyncio
async def test_fpl_api_caching():
    """Test FPL API caching functionality"""
    async with FPLAPI() as api:
        # Test cache miss
        url = "https://fantasy.premierleague.com/api/test"
        
        # Mock session and response
        mock_session = AsyncMock()
        api.session = mock_session
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'data': 'test'})
        
        mock_get_context = AsyncMock()
        mock_get_context.__aenter__.return_value = mock_response
        mock_session.get.return_value = mock_get_context
        
        # First call should not be cached
        result1 = await api._make_request_with_retry(url, cacheable=True)
        assert result1 == {'data': 'test'}
        assert mock_session.get.call_count == 1
        
        # Second call with same URL should be cached
        result2 = await api._make_request_with_retry(url, cacheable=True)
        assert result2 == {'data': 'test'}
        # Session get should still only be called once
        assert mock_session.get.call_count == 1

@pytest.mark.asyncio
async def test_fpl_api_retry_mechanisms():
    """Test FPL API retry mechanisms with different error codes"""
    async with FPLAPI() as api:
        # Mock session
        mock_session = AsyncMock()
        api.session = mock_session
        
        # Mock responses: first two fail with 500, third succeeds
        mock_response_fail1 = AsyncMock()
        mock_response_fail1.status = 500
        
        mock_response_fail2 = AsyncMock()
        mock_response_fail2.status = 500
        
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value={'data': 'success'})
        
        # Set up the mock to return failures then success
        mock_get_context1 = AsyncMock()
        mock_get_context1.__aenter__.return_value = mock_response_fail1
        
        mock_get_context2 = AsyncMock()
        mock_get_context2.__aenter__.return_value = mock_response_fail2
        
        mock_get_context3 = AsyncMock()
        mock_get_context3.__aenter__.return_value = mock_response_success
        
        mock_session.get.side_effect = [
            mock_get_context1,
            mock_get_context2,
            mock_get_context3
        ]
        
        # Test that it retries and eventually succeeds
        result = await api._make_request_with_retry("https://test.com/api", method='GET')
        assert result == {'data': 'success'}
        # Should have been called 3 times
        assert mock_session.get.call_count == 3

def test_database_query_caching():
    """Test database query caching decorator"""
    # Clear cache before test
    _query_cache.clear()
    
    call_count = 0
    
    @cached_query(ttl=1)  # 1 second TTL for testing
    def mock_query_function(param):
        nonlocal call_count
        call_count += 1
        return f"result_{param}_{call_count}"
    
    # First call should execute the function
    result1 = mock_query_function("test")
    assert result1 == "result_test_1"
    assert call_count == 1
    
    # Second call with same param should use cache
    result2 = mock_query_function("test")
    assert result2 == "result_test_1"  # Same result from cache
    assert call_count == 1  # Function not called again
    
    # Call with different param should execute function
    result3 = mock_query_function("test2")
    assert result3 == "result_test2_2"
    assert call_count == 2
    
    # Wait for cache to expire and test again
    time.sleep(1.1)  # Sleep longer than TTL
    
    # Call with original param should execute function again
    result4 = mock_query_function("test")
    assert result4 == "result_test_3"
    assert call_count == 3

def test_database_cache_clear():
    """Test clearing the database query cache"""
    # Clear cache before test
    _query_cache.clear()
    
    call_count = 0
    
    @cached_query(ttl=10)  # Long TTL
    def mock_query_function(param):
        nonlocal call_count
        call_count += 1
        return f"result_{param}_{call_count}"
    
    # First call
    result1 = mock_query_function("test")
    assert result1 == "result_test_1"
    assert call_count == 1
    
    # Second call should use cache
    result2 = mock_query_function("test")
    assert result2 == "result_test_1"
    assert call_count == 1
    
    # Clear cache
    clear_query_cache()
    
    # Third call should execute function again
    result3 = mock_query_function("test")
    assert result3 == "result_test_2"
    assert call_count == 2

@pytest.mark.asyncio
async def test_fpl_api_rate_limiting():
    """Test FPL API rate limiting handling"""
    async with FPLAPI() as api:
        # Mock session
        mock_session = AsyncMock()
        api.session = mock_session
        
        # Mock responses: first fails with 429, second succeeds
        mock_response_rate_limited = AsyncMock()
        mock_response_rate_limited.status = 429
        
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value={'data': 'success'})
        
        mock_get_context1 = AsyncMock()
        mock_get_context1.__aenter__.return_value = mock_response_rate_limited
        
        mock_get_context2 = AsyncMock()
        mock_get_context2.__aenter__.return_value = mock_response_success
        
        mock_session.get.side_effect = [
            mock_get_context1,
            mock_get_context2
        ]
        
        # Test that it handles rate limiting and retries
        with patch('asyncio.sleep', new_callable=AsyncMock):  # Mock sleep to avoid waiting
            result = await api._make_request_with_retry("https://test.com/api", method='GET')
            assert result == {'data': 'success'}

@pytest.mark.asyncio
async def test_fpl_api_connection_errors():
    """Test FPL API handling of connection errors"""
    async with FPLAPI() as api:
        # Mock session to raise connection error
        mock_session = AsyncMock()
        api.session = mock_session
        mock_session.get.side_effect = Exception("Connection error")
        
        # Test that it handles connection errors gracefully
        result = await api._make_request_with_retry("https://test.com/api", method='GET')
        assert result is None  # Should return None after retries exhausted