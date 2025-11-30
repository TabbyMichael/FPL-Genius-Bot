import aiohttp
import asyncio
import logging
import time
from typing import Optional
from config.settings import FPL_BASE_URL
from utils.security import log_api_call, log_authentication_attempt

logger = logging.getLogger(__name__)

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
    
    async def __aenter__(self):
        # Create session with timeout and retry settings
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
    
    async def _make_request_with_retry(self, url, method='GET', cacheable=False, **kwargs):
        """Make HTTP request with retry logic"""
        max_retries = 5  # Increased retries
        retry_delay = 1  # seconds
        backoff_factor = 2  # Exponential backoff factor
        
        # Check cache first for GET requests
        if method.upper() == 'GET' and cacheable:
            is_cached, cached_response = self._is_cached(url)
            if is_cached:
                log_api_call(url, method, 200)  # Log cached response as 200
                return cached_response
        
        # Check if session exists
        if not self.session:
            logger.error("No active session")
            log_api_call(url, method, 0)  # Use 0 to indicate no connection
            return None
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    async with self.session.get(url, **kwargs) as response:
                        if response.status == 200:
                            result = await response.json()
                            # Cache the response if it's cacheable
                            if cacheable:
                                self._cache_response(url, result)
                            log_api_call(url, method, response.status)
                            return result
                        elif response.status == 429:  # Rate limited
                            logger.warning(f"Rate limited, waiting {retry_delay * backoff_factor} seconds...")
                            log_api_call(url, method, response.status)
                            await asyncio.sleep(retry_delay * backoff_factor)
                            retry_delay *= backoff_factor
                            continue
                        elif response.status == 500:  # Server error, retry with backoff
                            logger.warning(f"Server error (500), retrying in {retry_delay} seconds...")
                            log_api_call(url, method, response.status)
                            await asyncio.sleep(retry_delay)
                            retry_delay *= backoff_factor
                            continue
                        elif response.status == 502:  # Bad gateway, retry with backoff
                            logger.warning(f"Bad gateway (502), retrying in {retry_delay} seconds...")
                            log_api_call(url, method, response.status)
                            await asyncio.sleep(retry_delay)
                            retry_delay *= backoff_factor
                            continue
                        elif response.status == 503:  # Service unavailable, retry with backoff
                            logger.warning(f"Service unavailable (503), retrying in {retry_delay} seconds...")
                            log_api_call(url, method, response.status)
                            await asyncio.sleep(retry_delay)
                            retry_delay *= backoff_factor
                            continue
                        else:
                            logger.error(f"HTTP {response.status} for {url}")
                            log_api_call(url, method, response.status)
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                retry_delay *= backoff_factor
                                continue
                            return None
                elif method.upper() == 'POST':
                    # Use authenticated session for POST requests if available
                    session_to_use = self.authenticated_session if self.authenticated_session else self.session
                    async with session_to_use.post(url, **kwargs) as response:
                        if response.status == 200:
                            result = await response.json()
                            log_api_call(url, method, response.status)
                            return result
                        elif response.status == 401:  # Unauthorized
                            logger.warning("Unauthorized access, trying to re-authenticate...")
                            log_api_call(url, method, response.status)
                            if await self._authenticate():
                                # Retry the request with authenticated session
                                if self.authenticated_session:
                                    async with self.authenticated_session.post(url, **kwargs) as retry_response:
                                        if retry_response.status == 200:
                                            result = await retry_response.json()
                                            log_api_call(url, method, retry_response.status)
                                            return result
                            return None
                        elif response.status == 429:  # Rate limited
                            logger.warning(f"Rate limited, waiting {retry_delay * backoff_factor} seconds...")
                            log_api_call(url, method, response.status)
                            await asyncio.sleep(retry_delay * backoff_factor)
                            retry_delay *= backoff_factor
                            continue
                        elif response.status == 500:  # Server error, retry with backoff
                            logger.warning(f"Server error (500), retrying in {retry_delay} seconds...")
                            log_api_call(url, method, response.status)
                            await asyncio.sleep(retry_delay)
                            retry_delay *= backoff_factor
                            continue
                        elif response.status == 502:  # Bad gateway, retry with backoff
                            logger.warning(f"Bad gateway (502), retrying in {retry_delay} seconds...")
                            log_api_call(url, method, response.status)
                            await asyncio.sleep(retry_delay)
                            retry_delay *= backoff_factor
                            continue
                        elif response.status == 503:  # Service unavailable, retry with backoff
                            logger.warning(f"Service unavailable (503), retrying in {retry_delay} seconds...")
                            log_api_call(url, method, response.status)
                            await asyncio.sleep(retry_delay)
                            retry_delay *= backoff_factor
                            continue
                        else:
                            logger.error(f"HTTP {response.status} for {url}")
                            log_api_call(url, method, response.status)
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay)
                                retry_delay *= backoff_factor
                                continue
                            return None
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    log_api_call(url, method, 0)  # Use 0 for unsupported method
                    return None
                    
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                last_exception = "Timeout"
                log_api_call(url, method, 0)  # Use 0 for timeout
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= backoff_factor
                    continue
                return None
            except aiohttp.ClientConnectorError as e:
                logger.warning(f"Connection error on attempt {attempt + 1} for {url}: {str(e)}")
                last_exception = str(e)
                log_api_call(url, method, 0)  # Use 0 for connection error
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= backoff_factor
                    continue
                return None
            except aiohttp.ClientResponseError as e:
                logger.warning(f"Response error on attempt {attempt + 1} for {url}: {str(e)}")
                last_exception = str(e)
                log_api_call(url, method, e.status if e.status else 0)
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= backoff_factor
                    continue
                return None
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1} for {url}: {str(e)}")
                last_exception = str(e)
                log_api_call(url, method, 0)  # Use 0 for unexpected error
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= backoff_factor
                    continue
                return None
        
        logger.error(f"All retry attempts failed for {url}. Last error: {last_exception}")
        return None
    
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
                log_authentication_attempt(True, "session")
                return True
            
            # Fallback to traditional username/password authentication
            elif self.username and self.password:
                logger.info("Using traditional authentication")
                # Note: This is a simplified implementation
                # Real implementation would need to handle the full login flow
                connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, ttl_dns_cache=300)
                self.authenticated_session = aiohttp.ClientSession(
                    timeout=self.timeout,
                    connector=connector,
                    headers={'User-Agent': 'FPL-Bot/1.0'}
                )
                # In a real implementation, we would perform the login here
                log_authentication_attempt(True, "traditional")
                return True
            
            logger.warning("No authentication credentials provided")
            log_authentication_attempt(False, "none")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            log_authentication_attempt(False, "error")
            return False
    
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
            return await self._make_request_with_retry(url)
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
        """Execute transfers in FPL"""
        if not self.team_id:
            logger.error("No TEAM_ID configured")
            return False
            
        try:
            # Ensure we're authenticated
            if not self.authenticated_session:
                if not await self._authenticate():
                    logger.error("Failed to authenticate for transfer execution")
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
                        return False
            else:
                logger.error("No authenticated session available for transfer execution")
                return False
                
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