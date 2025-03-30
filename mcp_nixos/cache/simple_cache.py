"""
Simple in-memory cache implementation for MCP-NixOS with thread safety.
"""

import logging
import time
import threading
import uuid
from typing import Any, Dict

# Get logger
logger = logging.getLogger("mcp_nixos")


class SimpleCache:
    """
    A simple in-memory cache with TTL expiration and thread safety.

    This class provides a thread-safe in-memory cache with automatic expiration
    of entries based on time-to-live (TTL). It also includes features to
    handle system time shifts gracefully.
    """

    def __init__(self, max_size=1000, ttl=300):  # ttl in seconds
        """Initialize the cache with maximum size and TTL."""
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
        self.instance_id = str(uuid.uuid4())[:8]

        # Add lock for thread safety
        self.lock = threading.RLock()

        # Store initialization time to detect significant time shifts
        self.init_time = time.time()

        logger.info(f"Initialized SimpleCache with max_size={max_size}, ttl={ttl}s, instance={self.instance_id}")

    def __del__(self):
        """Destructor to ensure proper cleanup when the cache is garbage collected."""
        try:
            self.clear()
        except Exception:
            # Ignore exceptions during garbage collection
            pass

    def get(self, key: Any) -> Any:
        """
        Retrieve a value from the cache if it exists and is not expired.

        This method uses a dual timestamp approach for maximum resilience against time shifts:
        1. Timestamp: Updated whenever the entry is accessed (sliding window)
        2. Creation time: Fixed when the entry was first created (absolute window)

        The entry is only considered expired if BOTH timestamps indicate expiration,
        providing resilience against both forward and backward time shifts.

        Args:
            key: The key to retrieve from the cache

        Returns:
            The cached value, or None if not found or expired
        """
        current_time = time.time()

        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None

            entry = self.cache[key]
            if len(entry) == 2:
                # Legacy format (timestamp, value)
                timestamp, value = entry
                creation_time = timestamp  # For older entries, creation time = timestamp
            else:
                # New format with separate creation time
                timestamp, creation_time, value = entry

            # Check if the value has expired using two methods:
            # 1. Traditional: compare current time to timestamp
            time_diff = current_time - timestamp

            # Handle backward time shifts - if time_diff is negative,
            # the system clock has moved backward
            if time_diff < 0:
                logger.debug(
                    f"Detected backward time shift for key {key}. "
                    f"Current time: {current_time}, Timestamp: {timestamp}, "
                    f"Diff: {time_diff}. Refreshing timestamps."
                )
                # Refresh the timestamp to the current time
                timestamp = current_time
                time_diff = 0
                # Update entry with new timestamp but keep original creation time
                self.cache[key] = (timestamp, creation_time, value)

            # 2. Creation-based: compare elapsed time since creation
            creation_diff = current_time - creation_time

            # Handle backward time shifts for creation time too
            if creation_diff < 0:
                logger.debug(
                    f"Detected extreme backward time shift beyond creation time "
                    f"for key {key}. Current time: {current_time}, Creation time: {creation_time}, "
                    f"Diff: {creation_diff}. Using 0 for creation_diff."
                )
                creation_diff = 0

            # Value is expired only if BOTH methods indicate it's expired
            # This provides maximum resilience against time shifts
            if time_diff > self.ttl and creation_diff > self.ttl:
                logger.debug(
                    f"Cache entry for key {key} is expired: "
                    f"time_diff={time_diff}, creation_diff={creation_diff}, ttl={self.ttl}"
                )
                del self.cache[key]
                self.misses += 1
                return None

            # For sliding window behavior, update the timestamp on every access
            # but preserve the original creation time
            self.cache[key] = (current_time, creation_time, value)

            self.hits += 1
            return value

    def set(self, key: Any, value: Any) -> None:
        """
        Store a value in the cache with the current timestamp.

        This method stores both the timestamp and creation time to ensure
        resilience against system time changes.

        Args:
            key: The key to store the value under
            value: The value to cache
        """
        current_time = time.time()

        with self.lock:
            if len(self.cache) >= self.max_size and key not in self.cache:
                # Simple eviction: remove oldest entry
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
                del self.cache[oldest_key]

            # Store as (timestamp, creation_time, value) tuple
            self.cache[key] = (current_time, current_time, value)

    def update_timestamp(self, key: Any) -> bool:
        """
        Update the timestamp for an existing cache entry.

        This is useful for implementing a cache access pattern where
        accessing an item extends its lifetime.

        Args:
            key: The key whose timestamp should be updated

        Returns:
            True if the key exists and was updated, False otherwise
        """
        current_time = time.time()

        with self.lock:
            if key not in self.cache:
                return False

            entry = self.cache[key]
            if len(entry) == 2:
                # Legacy format (timestamp, value)
                _, value = entry
                creation_time = current_time  # For legacy entries being updated
            else:
                # New format with separate creation time
                _, creation_time, value = entry

            # Update timestamp but preserve creation time
            self.cache[key] = (current_time, creation_time, value)
            return True

    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache = {}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache usage statistics
        """
        with self.lock:
            total_requests = self.hits + self.misses
            hit_ratio = self.hits / total_requests if total_requests > 0 else 0

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": hit_ratio,
                "instance_id": self.instance_id,
                "uptime": time.time() - self.init_time,
            }

    def remove_expired_entries(self) -> int:
        """
        Explicitly remove all expired entries from the cache.

        This can be called periodically to clean up the cache instead of
        relying solely on lazy expiration during get() operations.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        removed = 0

        with self.lock:
            expired_keys = []

            for key, entry in self.cache.items():
                if len(entry) == 2:
                    # Legacy format (timestamp, value)
                    timestamp, _ = entry
                    creation_time = timestamp
                else:
                    # New format with separate creation time
                    timestamp, creation_time, _ = entry

                # Check expiration using both methods
                time_diff = current_time - timestamp
                creation_diff = current_time - creation_time

                # Expired only if both indicate it's expired
                if time_diff > self.ttl and creation_diff > self.ttl:
                    expired_keys.append(key)

            # Now remove the expired keys
            for key in expired_keys:
                del self.cache[key]
                removed += 1

        return removed
