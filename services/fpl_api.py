import aiohttp  
import asyncio
import logging
import time
from typing import Optional
from playwright.async_api import async_playwright  
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type  
from config.settings import FPL_BASE_URL
from utils.security import log_api_call, log_authentication_attempt, log_transfer_execution

logger = logging.getLogger(__name__)

# Define custom exception for retryable HTTP errors
class RetryableAPIError(Exception):
    pass

class FPLAPI:
    """Handles communication with the FPL API"""
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, 
                 session_id: Optional[str] = None, csrf_token: Optional[str] = None, team_id: Optional[str] = None):
        self.session = None
        self.authenticated_session = None
        # Set default timeout
        self.timeout = aiohttp.ClientTimeout(total=30)
        # Cache for storing API responses
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        # Account credentials
        self.username = username
        self.password = password
        self.session_id = session_id
        self.csrf_token = csrf_token
        self.team_id = team_id
        
        # Session management
        self.last_auth_time = None
        self.session_expires_in = 3600  # 1 hour default
        self.min_session_time = 300  # 5 minutes minimum before expiration check
        
    async def __aenter__(self):
        # Create session with timeout settings
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector,
            headers={'User-Agent': 'FPL-Bot/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.authenticated_session:
            await self.authenticated_session.close()
        # Clear cache
        self._cache.clear()
    
    def _is_cached(self, url):
        """Check if URL response is cached and not expired"""
        if url in self._cache:
            cached_data, timestamp = self._cache[url]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"Cache hit for {url}")
                return True, cached_data
            else:
                # Remove expired cache entry
                del self._cache[url]
        return False, None
    
    def _cache_response(self, url, response):
        """Cache API response"""
        self._cache[url] = (response, time.time())
        logger.debug(f"Cached response for {url}")
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((RetryableAPIError, asyncio.TimeoutError, aiohttp.ClientConnectorError)),
        reraise=True  # Reraise the exception after all retries fail
    )
    async def _make_request_with_retry(self, url, method='GET', cacheable=False, authenticated=False, **kwargs):
        """Make HTTP request with tenacity retry logic"""
        # Check cache first for GET requests
        if method.upper() == 'GET' and cacheable:
            is_cached, cached_response = self._is_cached(url)
            if is_cached:
                log_api_call(url, method, 200)  # Log cached response as 200
                return cached_response

        # Determine which session to use
        if authenticated:
            if not await self._ensure_authenticated():
                logger.error("Authentication required but failed.")
                log_api_call(url, method, 401)
                return None
            session_to_use = self.authenticated_session
        else:
            session_to_use = self.session

        if not session_to_use:
            logger.error("No active session available.")
            log_api_call(url, method, 0)
            return None

        try:
            async with session_to_use.request(method, url, **kwargs) as response:
                log_api_call(url, method, response.status)

                if response.status == 200:
                    result = await response.json()
                    if method.upper() == 'GET' and cacheable:
                        self._cache_response(url, result)
                    return result
                elif response.status == 401:  # Unauthorized
                    logger.warning("Unauthorized access, attempting to re-authenticate...")
                    if await self._authenticate():
                        # After re-authentication, retry the request
                        raise RetryableAPIError("Re-authentication successful, retrying request.")
                    else:
                        logger.error("Re-authentication failed.")
                        return None
                elif response.status in [429, 500, 502, 503]:  # Retryable server errors
                    logger.warning(f"Received status {response.status}, retrying...")
                    raise RetryableAPIError(f"HTTP {response.status}")
                else:
                    logger.error(f"HTTP {response.status} for {url}")
                    return None
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError) as e:
            logger.warning(f"Connection error for {url}: {e}")
            log_api_call(url, method, 0)
            raise  # Re-raise to be caught by tenacity for retry
        except RetryableAPIError:
            # Let tenacity handle this specific error for retries
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            log_api_call(url, method, 0)
            return None
    
    async def _is_session_expired(self) -> bool:
        """Check if the current session has expired or is about to expire"""
        if not self.last_auth_time:
            return True
            
        # Check if session has expired or will expire soon
        time_since_auth = time.time() - self.last_auth_time
        return time_since_auth > (self.session_expires_in - self.min_session_time)
    
    async def _is_session_valid(self) -> bool:
        """Check if the current session is still valid by making a test request"""
        if not self.authenticated_session:
            return False
            
        try:
            # Make a simple request to check session validity
            url = f"{FPL_BASE_URL}/entry/{self.team_id}/" if self.team_id else f"{FPL_BASE_URL}/bootstrap-static/"
            async with self.authenticated_session.get(url) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def _authenticate(self):
        """Authenticate with FPL using either traditional login or session cookies"""
        try:
            # Close existing authenticated session if it exists
            if self.authenticated_session:
                await self.authenticated_session.close()
            
            # Prefer session-based authentication if available (for Google Sign-In)
            if self.session_id and self.csrf_token:
                logger.info("Using session-based authentication")
                connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
                self.authenticated_session = aiohttp.ClientSession(
                    timeout=self.timeout,
                    connector=connector,
                    headers={
                        'User-Agent': 'FPL-Bot/1.0',
                        'Cookie': f'sessionid={self.session_id}; csrftoken={self.csrf_token}',
                        'X-CSRFToken': self.csrf_token,
                        'Referer': 'https://fantasy.premierleague.com/'
                    }
                )
                self.last_auth_time = time.time()
                log_authentication_attempt(True, "session")
                return True
            
            # Fallback to traditional username/password authentication
            elif self.username and self.password:
                logger.info("Using traditional authentication")
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(f"{FPL_BASE_URL}/")
                    await page.fill('input[name="login"]', self.username)
                    await page.fill('input[name="password"]', self.password)
                    await page.click('button[type="submit"]')
                    await page.wait_for_load_state('networkidle')
                    cookies = await page.context.cookies()
                    
                    # Extract session cookie
                    session_cookie = next((cookie for cookie in cookies if cookie['name'] == 'sessionid'), None)
                    csrf_cookie = next((cookie for cookie in cookies if cookie['name'] == 'csrftoken'), None)
                    
                    if session_cookie and csrf_cookie:
                        # Update session with authenticated client
                        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
                        self.authenticated_session = aiohttp.ClientSession(
                            timeout=self.timeout,
                            connector=connector,
                            headers={
                                'User-Agent': 'FPL-Bot/1.0',
                                'Cookie': f"sessionid={session_cookie['value']}; csrftoken={csrf_cookie['value']}",
                                'X-CSRFToken': csrf_cookie['value'],
                                'Referer': 'https://fantasy.premierleague.com/'
                            }
                        )
                        self.session_id = session_cookie['value']
                        self.csrf_token = csrf_cookie['value']
                        self.last_auth_time = time.time()
                        log_authentication_attempt(True, "traditional")
                        return True
                    else:
                        logger.error("Failed to extract authentication cookies")
                        log_authentication_attempt(False, "traditional")
                        return False
                        
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            log_authentication_attempt(False, "traditional")
            return False
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid authenticated session"""
        # If we don't have an authenticated session, authenticate
        if not self.authenticated_session:
            return await self._authenticate()
        
        # Check if session is still valid
        if await self._is_session_expired() or not await self._is_session_valid():
            logger.info("Session expired or invalid, re-authenticating...")
            return await self._authenticate()
        
        return True
    
    async def get_bootstrap_data(self):
        """Get FPL bootstrap data (players, teams, etc.)"""
        url = f"{FPL_BASE_URL}/bootstrap-static/"
        return await self._make_request_with_retry(url, cacheable=True)
    
    async def get_player_info(self, player_id: int):
        """Get detailed information for a specific player"""
        url = f"{FPL_BASE_URL}/element-summary/{player_id}/"
        return await self._make_request_with_retry(url, cacheable=True)
    
    async def get_team_info(self, team_id: int):
        """Get information for a specific team"""
        url = f"{FPL_BASE_URL}/entry/{team_id}/"
        return await self._make_request_with_retry(url, authenticated=True)
    
    async def get_team_picks(self, team_id: int, gameweek: int):
        """Get team picks for a specific gameweek"""
        url = f"{FPL_BASE_URL}/entry/{team_id}/event/{gameweek}/picks/"
        return await self._make_request_with_retry(url, authenticated=True)
    
    async def get_gameweek_data(self, gameweek: int):
        """Get data for a specific gameweek"""
        url = f"{FPL_BASE_URL}/event/{gameweek}/live/"
        return await self._make_request_with_retry(url, cacheable=True)
    
    async def make_transfer(self, transfer_data: dict):
        """Make a transfer in the FPL team"""
        if not await self._ensure_authenticated():
            logger.error("Cannot make transfer without authentication")
            return None
            
        url = f"{FPL_BASE_URL}/transfers/"
        try:
            if self.authenticated_session:
                async with self.authenticated_session.post(url, json=transfer_data) as response:
                    # For now, we'll use dummy player IDs for logging
                    log_transfer_execution(0, 0, response.status == 200)
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 400:
                        error_data = await response.json()
                        logger.error(f"Transfer validation error: {error_data}")
                        return error_data
                    else:
                        logger.error(f"Transfer failed with status {response.status}")
                        return None
            else:
                logger.error("No authenticated session available for transfer")
                log_transfer_execution(0, 0, False)
                return None
        except Exception as e:
            logger.error(f"Transfer error: {e}")
            log_transfer_execution(0, 0, False)
            return None
    
    async def get_transfers_status(self):
        """Get the status of transfers"""
        if not await self._ensure_authenticated():
            logger.error("Cannot get transfers status without authentication")
            return None
            
        url = f"{FPL_BASE_URL}/transfers/"
        return await self._make_request_with_retry(url, method='GET', authenticated=True)