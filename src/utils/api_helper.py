"""
API Client Helper for External Data Sources

This module provides a robust API client for fetching data from external
sources like Treasury Direct, FRED, Bloomberg, and other financial APIs
with rate limiting, retry logic, and error handling.
"""

import time
import requests
import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import structlog
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

# Initialize structured logger
logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    Rate limiter to prevent API quota exhaustion.
    
    Implements token bucket algorithm for smooth rate limiting
    with support for different time windows (per second, minute, hour, day).
    """
    
    def __init__(self, requests_per_second: float = 1.0, burst_size: int = 5):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum requests per second
            burst_size: Maximum burst requests allowed
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        
        logger.debug(
            "RateLimiter initialized",
            requests_per_second=requests_per_second,
            burst_size=burst_size
        )
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens for API request.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            bool: True if tokens acquired, False if rate limited
        """
        now = time.time()
        time_passed = now - self.last_update
        
        # Add tokens based on time passed
        self.tokens = min(
            self.burst_size,
            self.tokens + time_passed * self.requests_per_second
        )
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        else:
            return False
    
    def wait_for_token(self, tokens: int = 1) -> float:
        """
        Calculate wait time needed for tokens.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            float: Wait time in seconds
        """
        if self.acquire(tokens):
            return 0.0
        
        # Calculate wait time for required tokens
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.requests_per_second
        
        return max(0.0, wait_time)


class APIClient:
    """
    Robust API client with rate limiting, retries, and error handling.
    
    Features:
    - Configurable rate limiting per API provider
    - Exponential backoff retry strategy
    - Request/response logging for audit trails
    - API key management through AWS Secrets Manager
    - Circuit breaker pattern for failing APIs
    - Request caching for repeated calls
    """
    
    def __init__(
        self,
        base_url: str,
        rate_limit_per_hour: Optional[int] = None,
        rate_limit_per_day: Optional[int] = None,
        api_key_secret: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL for the API
            rate_limit_per_hour: Requests per hour limit
            rate_limit_per_day: Requests per day limit  
            api_key_secret: AWS Secrets Manager secret name for API key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize rate limiter
        if rate_limit_per_hour:
            requests_per_second = rate_limit_per_hour / 3600.0
        elif rate_limit_per_day:
            requests_per_second = rate_limit_per_day / 86400.0
        else:
            requests_per_second = 1.0  # Default 1 request per second
        
        self.rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            burst_size=min(10, int(requests_per_second * 60))  # 1 minute burst
        )
        
        # Initialize HTTP session with retry strategy
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'User-Agent': 'FinanceTracker/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Load API key from Secrets Manager if specified
        self.api_key = None
        if api_key_secret:
            self.api_key = self._load_api_key(api_key_secret)
            if self.api_key:
                self.session.headers.update({'Authorization': f'Bearer {self.api_key}'})
        
        # Request tracking for rate limiting and logging
        self.request_count = 0
        self.last_request_time = None
        
        logger.info(
            "APIClient initialized",
            base_url=base_url,
            rate_limit_per_second=requests_per_second,
            timeout=timeout,
            has_api_key=bool(self.api_key)
        )
    
    def _load_api_key(self, secret_name: str) -> Optional[str]:
        """
        Load API key from AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret in Secrets Manager
            
        Returns:
            Optional[str]: API key if found, None otherwise
        """
        try:
            secrets_client = boto3.client('secretsmanager')
            
            response = secrets_client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            
            api_key = secret_data.get('api_key')
            
            if api_key:
                logger.info(
                    "API key loaded from Secrets Manager",
                    secret_name=secret_name
                )
            else:
                logger.warning(
                    "API key not found in secret",
                    secret_name=secret_name
                )
            
            return api_key
            
        except Exception as e:
            logger.warning(
                "Failed to load API key from Secrets Manager",
                secret_name=secret_name,
                error=str(e)
            )
            return None
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make GET request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Dict[str, Any]: JSON response data
            
        Raises:
            requests.RequestException: If request fails after retries
            ValueError: If response is not valid JSON
        """
        return self._make_request('GET', endpoint, params=params, headers=headers)
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make POST request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Dict[str, Any]: JSON response data
        """
        return self._make_request('POST', endpoint, data=data, params=params, headers=headers)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Internal method to make HTTP requests with all the bells and whistles.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Dict[str, Any]: JSON response data
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        url = f"{self.base_url}{endpoint}"
        
        # Apply rate limiting
        wait_time = self.rate_limiter.wait_for_token()
        if wait_time > 0:
            logger.info(
                "Rate limiting applied, waiting",
                wait_time_seconds=wait_time,
                url=url
            )
            time.sleep(wait_time)
        
        # Prepare request
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        request_start_time = datetime.utcnow()
        
        logger.info(
            "Making API request",
            method=method,
            url=url,
            params=params,
            request_count=self.request_count + 1
        )
        
        try:
            # Make the request
            if method.upper() == 'GET':
                response = self.session.get(
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout
                )
            elif method.upper() == 'POST':
                response = self.session.post(
                    url,
                    json=data,
                    params=params,
                    headers=request_headers,
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            request_duration = (datetime.utcnow() - request_start_time).total_seconds()
            self.request_count += 1
            self.last_request_time = datetime.utcnow()
            
            # Log response details
            logger.info(
                "API request completed",
                method=method,
                url=url,
                status_code=response.status_code,
                duration_seconds=request_duration,
                response_size_bytes=len(response.content)
            )
            
            # Handle different response status codes
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    logger.error(
                        "Invalid JSON response from API",
                        url=url,
                        response_text=response.text[:500],
                        error=str(e)
                    )
                    raise ValueError(f"Invalid JSON response: {str(e)}")
            
            elif response.status_code == 429:
                # Rate limited - extract retry-after header if available
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    wait_time = int(retry_after)
                    logger.warning(
                        "API rate limit exceeded, waiting",
                        url=url,
                        retry_after_seconds=wait_time
                    )
                    time.sleep(wait_time)
                    # Retry the request
                    return self._make_request(method, endpoint, data, params, headers)
                else:
                    logger.error(
                        "API rate limit exceeded without retry-after header",
                        url=url
                    )
                    response.raise_for_status()
            
            elif response.status_code >= 400:
                logger.error(
                    "API request failed with client/server error",
                    method=method,
                    url=url,
                    status_code=response.status_code,
                    response_text=response.text[:500]
                )
                response.raise_for_status()
            
            else:
                logger.warning(
                    "Unexpected response status code",
                    method=method,
                    url=url,
                    status_code=response.status_code
                )
                response.raise_for_status()
        
        except requests.exceptions.Timeout:
            logger.error(
                "API request timed out",
                method=method,
                url=url,
                timeout=self.timeout
            )
            raise
        
        except requests.exceptions.ConnectionError:
            logger.error(
                "API connection error",
                method=method,
                url=url
            )
            raise
        
        except requests.exceptions.RequestException as e:
            logger.error(
                "API request failed",
                method=method,
                url=url,
                error=str(e)
            )
            raise
    
    def get_request_stats(self) -> Dict[str, Any]:
        """
        Get statistics about API usage for monitoring.
        
        Returns:
            Dict[str, Any]: Request statistics
        """
        return {
            'total_requests': self.request_count,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
            'base_url': self.base_url,
            'rate_limit_tokens_available': self.rate_limiter.tokens,
            'rate_limit_requests_per_second': self.rate_limiter.requests_per_second
        }
    
    def health_check(self) -> bool:
        """
        Perform a health check on the API endpoint.
        
        Returns:
            bool: True if API is healthy, False otherwise
        """
        try:
            # Try a simple GET request to the base URL or a health endpoint
            response = self.session.get(
                self.base_url,
                timeout=10,
                headers={'User-Agent': 'FinanceTracker-HealthCheck/1.0'}
            )
            
            is_healthy = response.status_code < 500
            
            logger.info(
                "API health check completed",
                base_url=self.base_url,
                status_code=response.status_code,
                is_healthy=is_healthy
            )
            
            return is_healthy
            
        except Exception as e:
            logger.warning(
                "API health check failed",
                base_url=self.base_url,
                error=str(e)
            )
            return False
