"""
HTML content caching implementation using filesystem storage.

This module provides a persistent caching mechanism for HTML content
with support for cross-platform cache directory management.
"""

import hashlib
import time
import logging
import pathlib
from typing import Optional, Dict, Any, Tuple

from ..utils.cache_helpers import init_cache_storage


logger = logging.getLogger(__name__)


class HTMLCache:
    """
    Filesystem-based cache for HTML content with cross-platform support.

    This cache stores HTML content on disk in an OS-appropriate location,
    providing persistence across application restarts and reducing the need
    for frequent network requests.
    """

    def __init__(self, cache_dir: Optional[str] = None, ttl: int = 86400):
        """
        Initialize the HTML cache.

        Args:
            cache_dir: Optional custom cache directory path
            ttl: Time-to-live for cache entries in seconds (default: 1 day)
        """
        self.config = init_cache_storage(cache_dir, ttl)
        self.cache_dir = pathlib.Path(self.config["cache_dir"])
        self.ttl = ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "writes": 0,
        }
        logger.info(f"HTMLCache initialized with directory: {self.cache_dir}")

    def _get_cache_path(self, url: str) -> pathlib.Path:
        """
        Generate a cache file path for a given URL.

        Args:
            url: The URL for which to generate a cache path

        Returns:
            Path object pointing to the cache file location
        """
        # Create a hash of the URL to use as the filename
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{url_hash}.html"

    def _is_expired(self, file_path: pathlib.Path) -> bool:
        """
        Check if a cache file has expired based on its modification time.

        Args:
            file_path: Path to the cache file

        Returns:
            True if the file has expired, False otherwise
        """
        if not file_path.exists():
            return True

        mod_time = file_path.stat().st_mtime
        age = time.time() - mod_time
        return age > self.ttl

    def get(self, url: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Retrieve HTML content from cache if available and not expired.

        Args:
            url: URL to retrieve from cache

        Returns:
            Tuple of (content, metadata) where content is the cached HTML
            or None if not found, and metadata contains cache status info
        """
        cache_path = self._get_cache_path(url)
        metadata = {
            "url": url,
            "cache_hit": False,
            "cache_path": str(cache_path),
            "expired": False,
        }

        try:
            if not cache_path.exists():
                self.stats["misses"] += 1
                logger.debug(f"Cache miss for URL: {url}")
                return None, metadata

            expired = self._is_expired(cache_path)
            metadata["expired"] = expired

            if expired:
                self.stats["misses"] += 1
                logger.debug(f"Cache expired for URL: {url}")
                return None, metadata

            content = cache_path.read_text(encoding="utf-8")
            self.stats["hits"] += 1
            metadata["cache_hit"] = True
            logger.debug(f"Cache hit for URL: {url}")

            return content, metadata

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error retrieving from cache for {url}: {str(e)}")
            metadata["error"] = str(e)
            return None, metadata

    def set(self, url: str, content: str) -> Dict[str, Any]:
        """
        Store HTML content in the cache.

        Args:
            url: URL associated with the content
            content: HTML content to cache

        Returns:
            Metadata dictionary with cache operation information
        """
        cache_path = self._get_cache_path(url)
        metadata = {
            "url": url,
            "cache_path": str(cache_path),
            "stored": False,
        }

        try:
            # Ensure parent directories exist
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            cache_path.write_text(content, encoding="utf-8")

            self.stats["writes"] += 1
            metadata["stored"] = True
            logger.debug(f"Cached content for URL: {url}")

            return metadata

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error storing in cache for {url}: {str(e)}")
            metadata["error"] = str(e)
            return metadata

    def invalidate(self, url: str) -> Dict[str, Any]:
        """
        Remove a specific URL from the cache.

        Args:
            url: URL to remove from cache

        Returns:
            Metadata dictionary with invalidation operation information
        """
        cache_path = self._get_cache_path(url)
        metadata = {
            "url": url,
            "cache_path": str(cache_path),
            "invalidated": False,
        }

        try:
            if cache_path.exists():
                cache_path.unlink()
                metadata["invalidated"] = True
                logger.debug(f"Invalidated cache for URL: {url}")
            else:
                logger.debug(f"No cache to invalidate for URL: {url}")

            return metadata

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error invalidating cache for {url}: {str(e)}")
            metadata["error"] = str(e)
            return metadata

    def clear(self) -> Dict[str, Any]:
        """
        Clear all cached HTML content.

        Returns:
            Metadata dictionary with clear operation information
        """
        metadata = {
            "cache_dir": str(self.cache_dir),
            "cleared": False,
            "files_removed": 0,
        }

        try:
            if not self.cache_dir.exists():
                logger.debug(f"Cache directory does not exist: {self.cache_dir}")
                return metadata

            count = 0
            for file_path in self.cache_dir.glob("*.html"):
                try:
                    file_path.unlink()
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove cache file {file_path}: {e}")

            metadata["cleared"] = True
            metadata["files_removed"] = count
            logger.info(f"Cleared {count} files from cache directory: {self.cache_dir}")

            return metadata

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error clearing cache: {str(e)}")
            metadata["error"] = str(e)
            return metadata

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache usage statistics
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_ratio = self.stats["hits"] / total_requests if total_requests > 0 else 0

        # Get cache size information
        cache_size = 0
        file_count = 0

        try:
            if self.cache_dir.exists():
                for file_path in self.cache_dir.glob("*.html"):
                    try:
                        cache_size += file_path.stat().st_size
                        file_count += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Error calculating cache size: {e}")

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_ratio": hit_ratio,
            "errors": self.stats["errors"],
            "writes": self.stats["writes"],
            "cache_dir": str(self.cache_dir),
            "ttl": self.ttl,
            "file_count": file_count,
            "cache_size_bytes": cache_size,
            "cache_size_mb": round(cache_size / (1024 * 1024), 2) if cache_size > 0 else 0,
        }
