"""
Simple in-memory cache implementation for NixMCP.
"""

import time
import logging

# Get logger
logger = logging.getLogger("nixmcp")


class SimpleCache:
    """A simple in-memory cache with TTL expiration."""

    def __init__(self, max_size=1000, ttl=300):  # ttl in seconds
        """Initialize the cache with maximum size and TTL."""
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
        logger.info(f"Initialized cache with max_size={max_size}, ttl={ttl}s")

    def get(self, key):
        """Retrieve a value from the cache if it exists and is not expired."""
        if key not in self.cache:
            self.misses += 1
            return None

        timestamp, value = self.cache[key]
        if time.time() - timestamp > self.ttl:
            # Expired
            del self.cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return value

    def set(self, key, value):
        """Store a value in the cache with the current timestamp."""
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Simple eviction: remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]

        self.cache[key] = (time.time(), value)

    def clear(self):
        """Clear all cache entries."""
        self.cache = {}

    def get_stats(self):
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": (self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0),
        }
