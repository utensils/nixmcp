"""
HTML client for fetching and caching web content.

This module provides a client for fetching HTML content from the web
with persistent caching support to improve performance.
"""

import logging
import requests
from typing import Optional, Dict, Any, Tuple

from ..cache.html_cache import HTMLCache


logger = logging.getLogger(__name__)


class HTMLClient:
    """
    Client for fetching and caching HTML content.

    This client provides methods to fetch HTML content from web URLs
    with automatic caching to improve performance and reduce network requests.
    """

    def __init__(self, cache_dir: Optional[str] = None, ttl: int = 86400, timeout: int = 30, use_cache: bool = True):
        """
        Initialize the HTML client.

        Args:
            cache_dir: Optional custom cache directory path
            ttl: Time-to-live for cache entries in seconds (default: 1 day)
            timeout: HTTP request timeout in seconds
            use_cache: Whether to use caching (can be disabled for testing)
        """
        self.timeout = timeout
        self.use_cache = use_cache

        if use_cache:
            self.cache = HTMLCache(cache_dir=cache_dir, ttl=ttl)
            logger.info(f"HTMLClient initialized with cache directory: {self.cache.cache_dir}")
        else:
            self.cache = None
            logger.info("HTMLClient initialized with caching disabled")

    def fetch(self, url: str, force_refresh: bool = False) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Fetch HTML content from a URL with caching support.

        Args:
            url: URL to fetch content from
            force_refresh: Whether to ignore cache and force a fresh request

        Returns:
            Tuple of (content, metadata) where content is the HTML content
            and metadata contains information about the request/cache operation
        """
        metadata = {
            "url": url,
            "from_cache": False,
            "success": False,
        }

        # Try to get content from cache if caching is enabled and not forcing refresh
        if self.use_cache and not force_refresh and self.cache is not None:
            cache_result = self.cache.get(url)
            if cache_result and len(cache_result) == 2:
                cached_content, cache_metadata = cache_result
                if cache_metadata and isinstance(cache_metadata, dict):
                    metadata.update(cache_metadata)

                if cached_content is not None:
                    logger.debug(f"Fetched content from cache for URL: {url}")
                    metadata["from_cache"] = True
                    metadata["success"] = True
                    return cached_content, metadata

        # Fetch content from the web
        logger.debug(f"Fetching content from web for URL: {url}")
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            content = response.text

            metadata["status_code"] = response.status_code
            metadata["success"] = True

            # Store in cache if caching is enabled
            if self.use_cache and self.cache is not None:
                cache_result = self.cache.set(url, content)
                metadata["cache_result"] = cache_result

            return content, metadata

        except requests.RequestException as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            metadata["error"] = str(e)
            if hasattr(e, "response") and e.response is not None:
                metadata["status_code"] = e.response.status_code

            return None, metadata

    def clear_cache(self) -> Dict[str, Any]:
        """
        Clear all cached content.

        Returns:
            Metadata about the cache clear operation
        """
        if not self.use_cache or self.cache is None:
            return {"cache_enabled": False}

        return self.cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache usage statistics
        """
        if not self.use_cache or self.cache is None:
            return {"cache_enabled": False}

        return self.cache.get_stats()
