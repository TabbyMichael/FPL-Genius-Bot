import pytest
from unittest.mock import AsyncMock, Mock, patch
from services.fpl_api import FPLAPI, RetryableAPIError

@pytest.mark.asyncio
async def test_authenticate_with_credentials_success():
    """Test successful authentication with username and password."""
    api = FPLAPI(username="testuser", password="testpassword")

    with patch('services.fpl_api.async_playwright') as mock_playwright:
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_context = AsyncMock()

        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.context.cookies.return_value = [
            {'name': 'sessionid', 'value': 'testsessionid'},
            {'name': 'csrftoken', 'value': 'testcsrftoken'}
        ]

        authenticated = await api._authenticate()

        assert authenticated is True
        assert api.session_id == 'testsessionid'
        assert api.csrf_token == 'testcsrftoken'
        assert api.authenticated_session is not None

@pytest.mark.asyncio
async def test_authenticate_with_session_success():
    """Test successful authentication with session ID and CSRF token."""
    api = FPLAPI(session_id="testsessionid", csrf_token="testcsrftoken")

    authenticated = await api._authenticate()

    assert authenticated is True
    assert api.authenticated_session is not None

@pytest.mark.asyncio
async def test_authenticate_failure():
    """Test failed authentication."""
    api = FPLAPI()

    authenticated = await api._authenticate()

    assert authenticated is False
    assert api.authenticated_session is None

@pytest.mark.asyncio
async def test_make_request_with_retry_success():
    """Test _make_request_with_retry succeeds on the first attempt."""
    async with FPLAPI() as api:
        with patch.object(api.session, 'request', new_callable=Mock) as mock_request:
            # Correctly mock the async context manager
            mock_context_manager = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"success": True})
            mock_context_manager.__aenter__.return_value = mock_response
            mock_request.return_value = mock_context_manager

            result = await api._make_request_with_retry("http://test.com")

            assert result == {"success": True}
            mock_request.assert_called_once()

@pytest.mark.asyncio
async def test_make_request_with_retry_and_reattempt():
    """Test _make_request_with_retry fails and then succeeds."""
    async with FPLAPI() as api:
        with patch.object(api.session, 'request', new_callable=Mock) as mock_request:
            # Mock the failed response
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            mock_context_manager_fail = AsyncMock()
            mock_context_manager_fail.__aenter__.return_value = mock_response_fail

            # Mock the successful response
            mock_response_success = AsyncMock()
            mock_response_success.status = 200
            mock_response_success.json = AsyncMock(return_value={"success": True})
            mock_context_manager_success = AsyncMock()
            mock_context_manager_success.__aenter__.return_value = mock_response_success

            # The request method should return the failed context manager, then the successful one
            mock_request.side_effect = [
                mock_context_manager_fail,
                mock_context_manager_success
            ]

            # Call the function once, tenacity will handle the retry
            result = await api._make_request_with_retry("http://test.com")

            assert result == {"success": True}
            assert mock_request.call_count == 2
