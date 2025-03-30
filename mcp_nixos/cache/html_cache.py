"""
HTML content caching implementation using filesystem storage.

This module provides a persistent caching mechanism for HTML content
with support for cross-platform cache directory management, atomic file operations,
and resilience against time shifts.
"""

import hashlib
import time
import logging
import pathlib
import json
import pickle
import os
import threading
from typing import Optional, Dict, Any, Tuple, cast

from ..utils.cache_helpers import (
    init_cache_storage,
    atomic_write,
    write_with_metadata,
    read_with_metadata,
    lock_file,
    unlock_file,
)


logger = logging.getLogger(__name__)


class HTMLCache:
    """
    Filesystem-based cache for HTML content with cross-platform support.

    This cache stores HTML content on disk in an OS-appropriate location,
    providing persistence across application restarts and reducing the need
    for frequent network requests. File operations are atomic and thread-safe.
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
        self.instance_id = self.config.get("instance_id", "")
        self.ttl = ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "writes": 0,
            "data_hits": 0,
            "data_misses": 0,
            "data_writes": 0,
        }
        # Lock for thread-safe stats updates
        self.stats_lock = threading.RLock()
        logger.info(f"HTMLCache initialized with directory: {self.cache_dir}, instance: {self.instance_id}")

    def __del__(self):
        """Destructor with cleanup logic for non-session scoped test caches."""
        try:
            # Only perform cleanup if path includes specific marker for non-session test dirs
            # Skip cleanup for session-scoped fixtures managed by pytest
            if (
                self.cache_dir
                and "mcp_nixos_test_cache_" in str(self.cache_dir)
                and not os.environ.get("MCP_NIXOS_CACHE_DIR") == str(self.cache_dir)
            ):
                self.clear()
                logger.debug(f"HTMLCache cleaned up temporary directory: {self.cache_dir}")
        except Exception:
            pass

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

    def _get_data_cache_path(self, key: str) -> pathlib.Path:
        """
        Generate a cache file path for serialized data.

        Args:
            key: The key to identify the data cache

        Returns:
            Path object pointing to the data cache file location
        """
        # Create a hash of the key to use as the filename
        key_hash = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key_hash}.data.json"

    def _get_binary_data_cache_path(self, key: str) -> pathlib.Path:
        """
        Generate a cache file path for binary serialized data.

        Args:
            key: The key to identify the data cache

        Returns:
            Path object pointing to the binary data cache file location
        """
        key_hash = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key_hash}.data.pickle"

    def _is_expired(self, file_path: pathlib.Path, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a cache entry has expired using both file mtime and embedded creation timestamp.

        This function uses a hybrid approach for greater reliability against time shifts:
        - File modification time (traditional, but vulnerable to time shifts)
        - Embedded creation timestamp (more robust against time shifts)

        The entry is considered expired only if BOTH methods indicate expiration,
        providing maximum resilience against time shifts in either direction.

        Args:
            file_path: Path to the cache file
            metadata: Optional metadata containing creation_timestamp if available

        Returns:
            True if the entry has expired according to both methods, False if still valid by either
        """
        if not file_path.exists():
            return True

        current_time = time.time()

        # Method 1: Check file modification time (traditional)
        try:
            mod_time = file_path.stat().st_mtime
            file_age = current_time - mod_time

            # Handle backward time shifts where file_age could be negative
            if file_age < 0:
                logger.debug(f"Detected backward time shift for {file_path}. Using 0 for file age.")
                file_age = 0

            file_expired = file_age > self.ttl
        except (OSError, IOError) as e:
            # If we can't check mod time, assume expired
            logger.warning(f"Failed to get file modification time for {file_path}: {e}")
            file_expired = True

        # Method 2: Check embedded creation timestamp if available
        timestamp_expired = False  # Default to valid if no timestamp (rely on file mtime)
        if metadata and "creation_timestamp" in metadata:
            try:
                creation_time = float(metadata["creation_timestamp"])
                timestamp_age = current_time - creation_time

                # Handle backward time shifts where timestamp_age could be negative
                if timestamp_age < 0:
                    logger.debug(
                        f"Detected backward time shift for timestamp in {file_path}. Using 0 for timestamp age."
                    )
                    timestamp_age = 0

                timestamp_expired = timestamp_age > self.ttl
            except (ValueError, TypeError) as e:
                # If timestamp is invalid, fall back to file expiration only
                logger.warning(f"Invalid creation_timestamp format in metadata for {file_path}: {e}")
                timestamp_expired = False  # Default to valid, let file mtime decide

        # Entry is expired only if BOTH methods indicate it's expired
        # This provides maximum resilience against time shifts
        has_timestamp = metadata is not None and "creation_timestamp" in metadata
        expired = file_expired and (timestamp_expired or not has_timestamp)

        if expired:
            logger.debug(
                f"Cache entry {file_path} is expired: file_expired={file_expired}, "
                f"timestamp_expired={timestamp_expired}"
            )

        return expired

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
            # Use read_with_metadata to handle file locking and metadata reading
            content, file_metadata = read_with_metadata(cache_path)

            # Update our metadata with file metadata
            metadata.update(file_metadata)

            # Check for errors from read_with_metadata
            if "error" in file_metadata:
                with self.stats_lock:
                    self.stats["errors"] += 1
                logger.error(f"Error reading cache file for {url}: {file_metadata['error']}")
                return None, metadata

            if content is None:
                # If file doesn't exist or couldn't be read
                with self.stats_lock:
                    self.stats["misses"] += 1
                logger.debug(f"Cache miss for URL: {url}")
                return None, metadata

            # Check if content is expired using the hybrid approach
            expired = self._is_expired(cache_path, file_metadata)
            metadata["expired"] = expired

            if expired:
                with self.stats_lock:
                    self.stats["misses"] += 1
                logger.debug(f"Cache expired for URL: {url}")
                return None, metadata

            # Content is valid
            with self.stats_lock:
                self.stats["hits"] += 1
            metadata["cache_hit"] = True
            logger.debug(f"Cache hit for URL: {url}")

            return content, metadata

        except Exception as e:
            with self.stats_lock:
                self.stats["errors"] += 1
            logger.error(f"Error retrieving from cache for {url}: {str(e)}")
            metadata["error"] = str(e)
            return None, metadata

    def get_data(self, key: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieve serialized data from cache if available and not expired.

        Args:
            key: Key to identify the cached data

        Returns:
            Tuple of (data, metadata) where data is the cached structured data
            or None if not found, and metadata contains cache status info
        """
        cache_path = self._get_data_cache_path(key)
        metadata = {
            "key": key,
            "cache_hit": False,
            "cache_path": str(cache_path),
            "expired": False,
        }

        try:
            # Check if file exists first
            if not cache_path.exists():
                with self.stats_lock:
                    self.stats["data_misses"] += 1
                logger.debug(f"Data cache miss for key: {key}")
                return None, metadata

            # Read with file locking to prevent race conditions
            with open(cache_path, "r") as f:
                if lock_file(f, exclusive=False, blocking=False):
                    try:
                        content = f.read()
                        data = json.loads(content)

                        # Check if content is expired using both methods
                        expired = self._is_expired(cache_path, data)
                        metadata["expired"] = expired

                        if expired:
                            with self.stats_lock:
                                self.stats["data_misses"] += 1
                            logger.debug(f"Data cache expired for key: {key}")
                            return None, metadata

                        # Data is valid
                        with self.stats_lock:
                            self.stats["data_hits"] += 1
                        metadata["cache_hit"] = True
                        logger.debug(f"Data cache hit for key: {key}")

                        # Return the embedded creation timestamp in metadata
                        if "creation_timestamp" in data:
                            metadata["creation_timestamp"] = data["creation_timestamp"]

                        return data, metadata
                    finally:
                        unlock_file(f)
                else:
                    # Could not acquire lock, file might be being written
                    logger.warning(f"Could not acquire lock to read data for {key}")
                    metadata["lock_error"] = True
                    with self.stats_lock:
                        self.stats["data_misses"] += 1
                    return None, metadata

        except Exception as e:
            with self.stats_lock:
                self.stats["errors"] += 1
            logger.error(f"Error retrieving data from cache for {key}: {str(e)}")
            metadata["error"] = str(e)
            return None, metadata

    def get_binary_data(self, key: str) -> Tuple[Optional[Any], Dict[str, Any]]:
        """
        Retrieve binary serialized data from cache if available and not expired.

        Args:
            key: Key to identify the cached data

        Returns:
            Tuple of (data, metadata) where data is the cached binary data
            or None if not found, and metadata contains cache status info
        """
        cache_path = self._get_binary_data_cache_path(key)
        metadata = {
            "key": key,
            "cache_hit": False,
            "cache_path": str(cache_path),
            "expired": False,
        }

        # Check if the metadata file exists for timestamp validation
        meta_path = pathlib.Path(f"{cache_path}.meta")
        meta_data = {}

        try:
            # Check if file exists first
            if not cache_path.exists():
                with self.stats_lock:
                    self.stats["data_misses"] += 1
                logger.debug(f"Binary data cache miss for key: {key}")
                return None, metadata

            # Try to read metadata file first if it exists
            if meta_path.exists():
                try:
                    with open(meta_path, "r") as f:
                        if lock_file(f, exclusive=False, blocking=False):
                            try:
                                meta_content = f.read()
                                meta_data = json.loads(meta_content)
                            finally:
                                unlock_file(f)
                except Exception as e:
                    logger.warning(f"Error reading metadata for binary cache {key}: {e}")

            # Check if content is expired using both methods
            expired = self._is_expired(cache_path, meta_data)
            metadata["expired"] = expired

            if expired:
                with self.stats_lock:
                    self.stats["data_misses"] += 1
                logger.debug(f"Binary data cache expired for key: {key}")
                return None, metadata

            # Read with file locking to prevent race conditions
            with open(cache_path, "rb") as f:
                if lock_file(f, exclusive=False, blocking=False):
                    try:
                        # Read the binary data
                        data = pickle.load(f)

                        # If data is wrapped in a dict with _cache_metadata, extract it
                        if isinstance(data, dict) and "_cache_metadata" in data:
                            metadata.update(data["_cache_metadata"])
                            actual_data = data.get("_data")
                        else:
                            actual_data = data

                        with self.stats_lock:
                            self.stats["data_hits"] += 1
                        metadata["cache_hit"] = True
                        logger.debug(f"Binary data cache hit for key: {key}")

                        return actual_data, metadata
                    finally:
                        unlock_file(f)
                else:
                    # Could not acquire lock, file might be being written
                    logger.warning(f"Could not acquire lock to read binary data for {key}")
                    metadata["lock_error"] = True
                    with self.stats_lock:
                        self.stats["data_misses"] += 1
                    return None, metadata

        except Exception as e:
            with self.stats_lock:
                self.stats["errors"] += 1
            logger.error(f"Error retrieving binary data from cache for {key}: {str(e)}")
            metadata["error"] = str(e)
            return None, metadata

    def set(self, url: str, content: str) -> Dict[str, Any]:
        """
        Store HTML content in the cache using atomic file operations.

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
            "creation_timestamp": time.time(),
            "instance_id": self.instance_id,
        }

        try:
            # Use atomic write with file locking and separate metadata
            success = write_with_metadata(cache_path, content, metadata)

            if success:
                with self.stats_lock:
                    self.stats["writes"] += 1
                metadata["stored"] = True
                logger.debug(f"Cached content for URL: {url}")
            else:
                metadata["error"] = "Atomic write failed"
                logger.error(f"Failed to atomically write cache for URL: {url}")

            return metadata

        except Exception as e:
            with self.stats_lock:
                self.stats["errors"] += 1
            logger.error(f"Error storing in cache for {url}: {str(e)}")
            metadata["error"] = str(e)
            return metadata

    def set_data(self, key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store structured data in the cache using atomic file operations.

        Args:
            key: Key to identify the cached data
            data: Structured data to cache (must be JSON serializable)

        Returns:
            Metadata dictionary with cache operation information
        """
        cache_path = self._get_data_cache_path(key)
        metadata = {
            "key": key,
            "cache_path": str(cache_path),
            "stored": False,
            "instance_id": self.instance_id,
        }

        try:
            # Ensure data is mutable if it's a dict
            if isinstance(data, dict):
                # Create a copy to avoid modifying the original
                data_copy = dict(data)
                # Embed creation timestamp if not already present
                if "creation_timestamp" not in data_copy:
                    data_copy["creation_timestamp"] = time.time()
                # Add instance ID for debugging
                data_copy["_cache_instance"] = self.instance_id
            else:
                # For non-dict data, we can't embed timestamps
                data_copy = data
                # But we can create a metadata file
                meta_data = {
                    "creation_timestamp": time.time(),
                    "instance_id": self.instance_id,
                }
                meta_path = pathlib.Path(f"{cache_path}.meta")
                try:
                    atomic_write(meta_path, lambda f: f.write(json.dumps(meta_data, indent=2)))
                except Exception as e:
                    logger.warning(f"Failed to write metadata for {key}: {e}")

            # Write data atomically
            def write_data(f):
                content = json.dumps(data_copy, indent=2)
                f.write(content)

            success = atomic_write(cache_path, write_data)

            if success:
                with self.stats_lock:
                    self.stats["data_writes"] += 1
                metadata["stored"] = True
                logger.debug(f"Cached data for key: {key}")
            else:
                metadata["error"] = "Atomic write failed"
                logger.error(f"Failed to atomically write data cache for key: {key}")

            return metadata

        except Exception as e:
            with self.stats_lock:
                self.stats["errors"] += 1
            logger.error(f"Error storing data in cache for {key}: {str(e)}")
            metadata["error"] = str(e)
            return metadata

    def set_binary_data(self, key: str, data: Any) -> Dict[str, Any]:
        """
        Store binary data in the cache using pickle and atomic file operations.

        This implementation wraps the data in a dictionary with metadata to ensure
        we can track creation time even for binary data.

        Args:
            key: Key to identify the cached data
            data: Data to cache (must be pickle serializable)

        Returns:
            Metadata dictionary with cache operation information
        """
        cache_path = self._get_binary_data_cache_path(key)
        metadata = {
            "key": key,
            "cache_path": str(cache_path),
            "stored": False,
            "instance_id": self.instance_id,
        }

        try:
            # Create metadata for separate storage and for embedding
            cache_metadata = {
                "creation_timestamp": time.time(),
                "instance_id": self.instance_id,
                "key": key,
            }

            # Wrap data with metadata for resilience against time shifts
            wrapped_data = {"_data": data, "_cache_metadata": cache_metadata}

            # Write metadata file separately too (belt and suspenders)
            meta_path = pathlib.Path(f"{cache_path}.meta")
            try:
                # Cast is needed because write returns an int but atomic_write expects None return type
                atomic_write(meta_path, lambda f: cast(None, f.write(json.dumps(cache_metadata, indent=2))))
            except Exception as e:
                logger.warning(f"Failed to write metadata for binary data {key}: {e}")

            # Write data atomically
            def write_binary_data(f):
                pickle.dump(wrapped_data, f)

            # Set the mode attribute so atomic_write knows to open in binary mode
            write_binary_data.mode = "wb"  # type: ignore

            success = atomic_write(cache_path, write_binary_data)

            if success:
                with self.stats_lock:
                    self.stats["data_writes"] += 1
                metadata["stored"] = True
                logger.debug(f"Cached binary data for key: {key}")
            else:
                metadata["error"] = "Atomic write failed"
                logger.error(f"Failed to atomically write binary data cache for key: {key}")

            return metadata

        except Exception as e:
            with self.stats_lock:
                self.stats["errors"] += 1
            logger.error(f"Error storing binary data in cache for {key}: {str(e)}")
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
        meta_path = pathlib.Path(f"{cache_path}.meta")
        metadata = {
            "url": url,
            "cache_path": str(cache_path),
            "invalidated": False,
            "meta_invalidated": False,
        }

        try:
            if cache_path.exists():
                cache_path.unlink()
                metadata["invalidated"] = True
                logger.debug(f"Invalidated cache for URL: {url}")
            else:
                logger.debug(f"No cache to invalidate for URL: {url}")

            # Also remove metadata file if it exists
            if meta_path.exists():
                meta_path.unlink()
                metadata["meta_invalidated"] = True
                logger.debug(f"Invalidated metadata for URL: {url}")

            return metadata

        except Exception as e:
            with self.stats_lock:
                self.stats["errors"] += 1
            logger.error(f"Error invalidating cache for {url}: {str(e)}")
            metadata["error"] = str(e)
            return metadata

    def invalidate_data(self, key: str) -> Dict[str, Any]:
        """
        Remove specific data from the cache.

        Args:
            key: Key of the data to remove

        Returns:
            Metadata dictionary with invalidation operation information
        """
        cache_path = self._get_data_cache_path(key)
        binary_cache_path = self._get_binary_data_cache_path(key)

        # Also check for metadata files
        data_meta_path = pathlib.Path(f"{cache_path}.meta")
        binary_meta_path = pathlib.Path(f"{binary_cache_path}.meta")

        metadata = {
            "key": key,
            "cache_path": str(cache_path),
            "binary_cache_path": str(binary_cache_path),
            "invalidated": False,
            "binary_invalidated": False,
            "meta_invalidated": False,
            "binary_meta_invalidated": False,
        }

        try:
            if cache_path.exists():
                cache_path.unlink()
                metadata["invalidated"] = True
                logger.debug(f"Invalidated data cache for key: {key}")
            else:
                logger.debug(f"No data cache to invalidate for key: {key}")

            if data_meta_path.exists():
                data_meta_path.unlink()
                metadata["meta_invalidated"] = True
                logger.debug(f"Invalidated data metadata for key: {key}")

            if binary_cache_path.exists():
                binary_cache_path.unlink()
                metadata["binary_invalidated"] = True
                logger.debug(f"Invalidated binary data cache for key: {key}")
            else:
                logger.debug(f"No binary data cache to invalidate for key: {key}")

            if binary_meta_path.exists():
                binary_meta_path.unlink()
                metadata["binary_meta_invalidated"] = True
                logger.debug(f"Invalidated binary data metadata for key: {key}")

            return metadata

        except Exception as e:
            with self.stats_lock:
                self.stats["errors"] += 1
            logger.error(f"Error invalidating data cache for {key}: {str(e)}")
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
            # Remove all files recursively, including hidden files and those without extensions
            for file_path in self.cache_dir.glob("**/*"):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove cache file {file_path}: {e}")

            # Reset stats since we've cleared everything
            with self.stats_lock:
                self.stats = {
                    "hits": 0,
                    "misses": 0,
                    "errors": 0,
                    "writes": 0,
                    "data_hits": 0,
                    "data_misses": 0,
                    "data_writes": 0,
                }

            metadata["cleared"] = True
            metadata["files_removed"] = count
            logger.info(f"Cleared {count} files from cache directory: {self.cache_dir}")

            return metadata

        except Exception as e:
            with self.stats_lock:
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
        with self.stats_lock:
            stats_copy = dict(self.stats)

            total_requests = stats_copy["hits"] + stats_copy["misses"]
            hit_ratio = stats_copy["hits"] / total_requests if total_requests > 0 else 0

            total_data_requests = stats_copy["data_hits"] + stats_copy["data_misses"]
            data_hit_ratio = stats_copy["data_hits"] / total_data_requests if total_data_requests > 0 else 0

        # Get cache size information
        cache_size = 0
        file_count = 0
        html_count = 0
        data_count = 0
        binary_data_count = 0
        meta_count = 0

        try:
            if self.cache_dir.exists():
                for file_path in self.cache_dir.glob("*.*"):
                    try:
                        cache_size += file_path.stat().st_size
                        file_count += 1
                        if file_path.suffix == ".html":
                            html_count += 1
                        elif file_path.suffix == ".json":
                            data_count += 1
                        elif file_path.suffix == ".pickle":
                            binary_data_count += 1
                        elif file_path.suffix == ".meta":
                            meta_count += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Error calculating cache size: {e}")

        return {
            "hits": stats_copy["hits"],
            "misses": stats_copy["misses"],
            "hit_ratio": hit_ratio,
            "data_hits": stats_copy["data_hits"],
            "data_misses": stats_copy["data_misses"],
            "data_hit_ratio": data_hit_ratio,
            "errors": stats_copy["errors"],
            "writes": stats_copy["writes"],
            "data_writes": stats_copy["data_writes"],
            "cache_dir": str(self.cache_dir),
            "ttl": self.ttl,
            "instance_id": self.instance_id,
            "file_count": file_count,
            "html_count": html_count,
            "data_count": data_count,
            "binary_data_count": binary_data_count,
            "meta_count": meta_count,
            "cache_size_bytes": cache_size,
            "cache_size_mb": round(cache_size / (1024 * 1024), 2) if cache_size > 0 else 0,
        }
