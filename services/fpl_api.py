import aiohttp
import asyncio
import logging
import time
from typing import Optional
from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import FPL_BASE_URL
from utils.security import log_api_call, log_authentication_attempt

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
                    await browser.close()

                for cookie in cookies:
                    if cookie['name'] == 'sessionid':
                        self.session_id = cookie['value']
                    if cookie['name'] == 'csrftoken':
                        self.csrf_token = cookie['value']

                if self.session_id and self.csrf_token:
                    logger.info("Successfully retrieved session cookies")
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
                    log_authentication_attempt(True, "traditional")
                    return True
                else:
                    logger.error("Failed to retrieve session cookies")
                    log_authentication_attempt(False, "traditional")
                    return False
            
            logger.warning("No authentication credentials provided")
            log_authentication_attempt(False, "none")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            log_authentication_attempt(False, "error")
            return False
    
    async def _ensure_authenticated(self) -> bool:
        """Ensure we have a valid authenticated session, refreshing if necessary"""
        # Check if we have an authenticated session
        if not self.authenticated_session:
            logger.info("No authenticated session found, creating new one")
            return await self._authenticate()
        
        # Check if session is about to expire or is invalid
        if await self._is_session_expired() or not await self._is_session_valid():
            logger.info("Session expired or invalid, refreshing")
            return await self._authenticate()
        
        return True
    
    async def get_bootstrap_data(self):
        """Get static bootstrap data from FPL"""
        try:
            url = f"{FPL_BASE_URL}/bootstrap-static/"
            # Bootstrap data is cacheable since it doesn't change frequently
            return await self._make_request_with_retry(url, cacheable=True)
        except Exception as e:
            logger.error(f"Error fetching bootstrap data: {str(e)}")
            return None
    
    async def get_player_data(self, player_id):
        """Get detailed data for a specific player"""
        try:
            url = f"{FPL_BASE_URL}/element-summary/{player_id}/"
            return await self._make_request_with_retry(url)
        except Exception as e:
            logger.error(f"Error fetching player data for ID {player_id}: {str(e)}")
            return None
    
    async def get_fixtures(self):
        """Get upcoming fixtures"""
        try:
            url = f"{FPL_BASE_URL}/fixtures/"
            # Fixtures can be cached for a short period
            return await self._make_request_with_retry(url, cacheable=True)
        except Exception as e:
            logger.error(f"Error fetching fixtures: {str(e)}")
            return None
    
    async def get_team_data(self):
        """Get team data for the configured team ID"""
        if not self.team_id:
            logger.error("No TEAM_ID configured")
            return None
            
        try:
            url = f"{FPL_BASE_URL}/entry/{self.team_id}/"
            return await self._make_request_with_retry(url, authenticated=True)
        except Exception as e:
            logger.error(f"Error fetching team data for ID {self.team_id}: {str(e)}")
            return None
    
    async def get_team_picks(self, gameweek=None):
        """Get team picks for a specific gameweek (defaults to current)"""
        if not self.team_id:
            logger.error("No TEAM_ID configured")
            return None
            
        try:
            # If no gameweek specified, try to get current gameweek
            if gameweek is None:
                bootstrap_data = await self.get_bootstrap_data()
                if bootstrap_data:
                    events = bootstrap_data.get('events', [])
                    for event in events:
                        if event.get('is_current'):
                            gameweek = event.get('id')
                            break
                        elif event.get('is_next'):
                            gameweek = event.get('id')
                            break
            
            if gameweek is None:
                logger.error("Could not determine current gameweek")
                return None
                
            url = f"{FPL_BASE_URL}/entry/{self.team_id}/event/{gameweek}/picks/"
            return await self._make_request_with_retry(url)
        except Exception as e:
            logger.error(f"Error fetching team picks for ID {self.team_id}, GW {gameweek}: {str(e)}")
            return None
    
    async def get_player_info(self, player_id):
        """Get detailed player information"""
        try:
            bootstrap_data = await self.get_bootstrap_data()
            if not bootstrap_data:
                return None
                
            players = bootstrap_data.get('elements', [])
            for player in players:
                if player.get('id') == player_id:
                    return player
            return None
        except Exception as e:
            logger.error(f"Error fetching player info for ID {player_id}: {str(e)}")
            return None
    
    async def get_fixture_difficulty(self, team_id, gameweek):
        """Get fixture difficulty for a team in a specific gameweek"""
        try:
            fixtures = await self.get_fixtures()
            if not fixtures:
                return 3  # Default medium difficulty
            
            for fixture in fixtures:
                if fixture.get('event') == gameweek:
                    if fixture.get('team_h') == team_id:
                        return fixture.get('team_h_difficulty', 3)
                    elif fixture.get('team_a') == team_id:
                        return fixture.get('team_a_difficulty', 3)
            
            return 3  # Default medium difficulty
        except Exception as e:
            logger.error(f"Error fetching fixture difficulty for team {team_id}, GW {gameweek}: {str(e)}")
            return 3
    
    async def get_player_injury_status(self, player_id):
        """Get injury/suspension status for a player"""
        try:
            player_info = await self.get_player_info(player_id)
            if not player_info:
                return {'status': 'a', 'news': '', 'chance_of_playing_next_round': 100, 'chance_of_playing_this_round': 100}
            
            status = player_info.get('status', 'a')
            news = player_info.get('news', '')
            
            # Handle None values for chance of playing
            chance_next = player_info.get('chance_of_playing_next_round')
            chance_this = player_info.get('chance_of_playing_this_round')
            
            # Convert None to default values
            chance_next = chance_next if chance_next is not None else 100
            chance_this = chance_this if chance_this is not None else 100
            
            return {
                'status': status,
                'news': news,
                'chance_of_playing_next_round': chance_next,
                'chance_of_playing_this_round': chance_this
            }
        except Exception as e:
            logger.error(f"Error fetching injury status for player {player_id}: {str(e)}")
            return {'status': 'a', 'news': '', 'chance_of_playing_next_round': 100, 'chance_of_playing_this_round': 100}
    
    async def execute_transfers(self, transfers):
        """Execute transfers in FPL with proper error handling and retry mechanisms"""
        if not self.team_id:
            logger.error("No TEAM_ID configured")
            return False
            
        try:
            # Ensure we're authenticated
            if not await self._ensure_authenticated():
                logger.error("Failed to authenticate for transfer execution")
                return False
            
            # Validate transfers
            if not transfers or not isinstance(transfers, list):
                logger.error("Invalid transfers data provided")
                return False
            
            # Prepare transfer payload
            transfer_payload = {
                'confirmed': True,
                'entry': int(self.team_id),
                'wildcard': False,
                'freehit': False,
                'benchboost': False,
                'triple_captain': False,
                'transfers': transfers
            }
            
            url = f"{FPL_BASE_URL}/transfers/"
            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://fantasy.premierleague.com/transfers'
            }
            
            # Try to execute transfers with authenticated session
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if self.authenticated_session:
                        async with self.authenticated_session.post(url, json=transfer_payload, headers=headers) as response:
                            if response.status == 200:
                                result = await response.json()
                                logger.info(f"Transfers executed successfully: {result}")
                                # Log transfer execution
                                for transfer in transfers:
                                    # Import here to avoid circular imports
                                    from utils.security import log_transfer_execution
                                    log_transfer_execution(
                                        transfer.get('element_out', 0),
                                        transfer.get('element_in', 0),
                                        True
                                    )
                                return True
                            elif response.status == 401:  # Unauthorized
                                logger.warning("Unauthorized during transfer execution, re-authenticating...")
                                if await self._authenticate():
                                    if attempt < max_retries - 1:
                                        continue  # Retry after re-authentication
                                else:
                                    logger.error("Failed to re-authenticate for transfer execution")
                                    # Log failed transfer execution
                                    for transfer in transfers:
                                        # Import here to avoid circular imports
                                        from utils.security import log_transfer_execution
                                        log_transfer_execution(
                                            transfer.get('element_out', 0),
                                            transfer.get('element_in', 0),
                                            False
                                        )
                                    return False
                            else:
                                error_text = await response.text()
                                logger.error(f"Failed to execute transfers. Status: {response.status}, Error: {error_text}")
                                # Log failed transfer execution
                                for transfer in transfers:
                                    # Import here to avoid circular imports
                                    from utils.security import log_transfer_execution
                                    log_transfer_execution(
                                        transfer.get('element_out', 0),
                                        transfer.get('element_in', 0),
                                        False
                                    )
                                if attempt < max_retries - 1:
                                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                    continue
                                return False
                    else:
                        logger.error("No authenticated session available for transfer execution")
                        # Log failed transfer execution
                        for transfer in transfers:
                            # Import here to avoid circular imports
                            from utils.security import log_transfer_execution
                            log_transfer_execution(
                                transfer.get('element_out', 0),
                                transfer.get('element_in', 0),
                                False
                            )
                        return False
                except Exception as e:
                    logger.error(f"Error executing transfers (attempt {attempt + 1}): {str(e)}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    # Log failed transfer execution due to exception
                    for transfer in transfers:
                        # Import here to avoid circular imports
                        from utils.security import log_transfer_execution
                        log_transfer_execution(
                            transfer.get('element_out', 0),
                            transfer.get('element_in', 0),
                            False
                        )
                    return False
            
            return False  # All retries exhausted
                
        except Exception as e:
            logger.error(f"Error executing transfers: {str(e)}")
            # Log failed transfer execution due to exception
            for transfer in transfers:
                # Import here to avoid circular imports
                from utils.security import log_transfer_execution
                log_transfer_execution(
                    transfer.get('element_out', 0),
                    transfer.get('element_in', 0),
                    False
                )
            return False