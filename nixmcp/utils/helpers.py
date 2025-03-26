"""
Helper functions for NixMCP.
"""

import time
import logging
import requests
from typing import Optional, Callable, TypeVar, Dict, Any, Tuple

# Import version for user agent
from nixmcp import __version__

# Get logger
logger = logging.getLogger("nixmcp")

# Type variables for better type annotations
T = TypeVar("T")


def create_wildcard_query(query: str) -> str:
    """Create a wildcard query from a regular query string.

    Args:
        query: The original query string

    Returns:
        A query string with wildcards added
    """
    if " " in query:
        # For multi-word queries, add wildcards around each word
        words = query.split()
        wildcard_terms = [f"*{word}*" for word in words]
        return " ".join(wildcard_terms)
    else:
        # For single word queries, just wrap with wildcards
        return f"*{query}*"


def get_context_or_fallback(context: Optional[T], context_name: str) -> T:
    """Get the provided context or fall back to global context.

    Args:
        context: The context passed to the function, potentially None
        context_name: The name of the context to retrieve from server if not provided

    Returns:
        The provided context or the global context from the server
    """
    if context is None:
        # Import here to avoid circular imports
        import nixmcp.server

        return getattr(nixmcp.server, context_name)

    return context


def check_loading_status(func: Callable) -> Callable:
    """Decorator that checks if Home Manager client is loaded before executing a method.

    This decorator is intended for HomeManagerContext methods to avoid duplicating the
    loading status check code across multiple methods.

    Args:
        func: The function to decorate

    Returns:
        A wrapped function that checks loading status before executing
    """

    def wrapper(self, *args, **kwargs):
        # Get the default response values based on the method name
        method_name = func.__name__
        default_values = {}

        # Add method-specific default values
        if method_name == "search_options":
            default_values = {"count": 0, "options": []}
        elif method_name == "get_option" and args:
            default_values = {"name": args[0]}  # First arg should be option_name
        elif method_name == "get_stats":
            default_values = {"total_options": 0}

        # Check if data is still being loaded
        with self.hm_client.loading_lock:
            if not self.hm_client.is_loaded and self.hm_client.loading_in_progress:
                # Return a loading status instead of waiting indefinitely
                response = {
                    "loading": True,
                    "error": "Home Manager data is still being loaded. Please try again in a moment.",
                    "found": False,
                }
                response.update(default_values)
                return response

            # If loading failed, report the error
            if self.hm_client.loading_error:
                response = {
                    "loading": False,
                    "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                    "found": False,
                }
                response.update(default_values)
                return response

        # Ensure we have the client and it's not loading
        if not hasattr(self, "hm_client") or not self.hm_client:
            response = {
                "loading": False,
                "error": "Home Manager client not initialized",
                "found": False,
            }
            response.update(default_values)
            return response

        # If we get here, the client is loaded and ready, so call the original function
        return func(self, *args, **kwargs)

    return wrapper


def make_http_request(
    url: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    auth: Optional[Tuple[str, str]] = None,
    timeout: Tuple[float, float] = (5.0, 15.0),
    max_retries: int = 3,
    retry_delay: float = 1.0,
    cache: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Make an HTTP request with robust error handling and retries.

    This is a common utility function to standardize HTTP requests across the codebase.
    It handles retries with exponential backoff, caching, error handling, and logging.

    Args:
        url: The URL to request
        method: HTTP method (GET or POST)
        json_data: JSON data to send (for POST requests)
        auth: Optional authentication tuple (username, password)
        timeout: Tuple of (connect_timeout, read_timeout) in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        cache: Optional cache instance (must have get/set methods)
        headers: Optional custom headers to include in the request

    Returns:
        Dict containing either the JSON response or an error message
    """
    # Check if result is in cache
    cache_key = None
    if cache is not None:
        method_key = method.lower()
        data_key = "" if json_data is None else f":{str(json_data)}"
        cache_key = f"{method_key}:{url}{data_key}"
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for request: {cache_key[:100]}...")
            return cached_result
        logger.debug(f"Cache miss for request: {cache_key[:100]}...")

    # Common headers
    default_headers = {
        "User-Agent": f"NixMCP/{__version__}",
        "Accept-Encoding": "gzip, deflate",
    }

    # Add content-type for JSON requests
    if json_data is not None:
        default_headers["Content-Type"] = "application/json"

    # Merge default headers with custom headers if provided
    request_headers = headers if headers is not None else {}
    for key, value in default_headers.items():
        if key not in request_headers:
            request_headers[key] = value

    for attempt in range(max_retries):
        try:
            # Make the request
            if method.upper() == "POST":
                response = requests.post(url, json=json_data, auth=auth, headers=request_headers, timeout=timeout)
            else:  # Default to GET
                response = requests.get(url, auth=auth, headers=request_headers, timeout=timeout)

            # Handle 4xx client errors
            if 400 <= response.status_code < 500:
                logger.warning(f"Client error ({response.status_code}) for URL: {url}")
                error_result = {"error": f"Request failed with status {response.status_code}"}

                # For 401/403, provide authentication error
                if response.status_code in (401, 403):
                    error_result["error"] = "Authentication failed"

                # For 400 bad request, try to include response body for more details
                if response.status_code == 400:
                    try:
                        error_result["details"] = response.json()
                    except Exception:
                        pass

                return error_result

            # Handle 5xx server errors with retry
            if response.status_code >= 500:
                logger.error(f"Server error ({response.status_code}) for URL: {url}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                return {"error": f"Server error ({response.status_code})"}

            # Handle successful responses
            response.raise_for_status()  # Raise for any other error codes

            # Try to parse JSON response
            try:
                result = response.json()
                # Cache successful result if cache is available
                if cache is not None and cache_key is not None:
                    cache.set(cache_key, result)
                return result
            except (ValueError, AttributeError):
                # If not JSON, return text content
                return {"text": response.text}

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for URL: {url}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)  # Exponential backoff
                time.sleep(wait_time)
                continue
            return {"error": "Failed to connect to server"}

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for URL: {url}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)  # Exponential backoff
                time.sleep(wait_time)
                continue
            return {"error": "Request timed out"}

        except Exception as e:
            logger.error(f"Error making request to {url}: {str(e)}")
            return {"error": f"Request error: {str(e)}"}

    # We should never reach here, but just in case
    return {"error": f"Request failed after {max_retries} attempts"}
