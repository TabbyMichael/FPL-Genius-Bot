import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from services.fpl_api import FPLAPI

@pytest.mark.asyncio
async def test_api_response_caching():
    """Test that API responses are cached and retrieved."""
    async with FPLAPI() as api:
        with patch.object(api.session, 'request', new_callable=Mock) as mock_request:
            # Correctly mock the async context manager
            mock_context_manager = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": "test"})
            mock_context_manager.__aenter__.return_value = mock_response
            mock_request.return_value = mock_context_manager

            # First call should hit the API
            result1 = await api._make_request_with_retry("http://test.com/cacheable", cacheable=True)
            assert result1 == {"data": "test"}
            mock_request.assert_called_once()

            # Second call should be cached
            result2 = await api._make_request_with_retry("http://test.com/cacheable", cacheable=True)
            assert result2 == {"data": "test"}
            mock_request.assert_called_once()  # Should not be called again
