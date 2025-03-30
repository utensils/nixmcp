"""Tests for the SimpleCache class in the MCP-NixOS server."""

import threading
import time
import unittest
import pytest

# Mark as unit tests (not integration)
pytestmark = [pytest.mark.unit, pytest.mark.not_integration]

from mcp_nixos.server import SimpleCache


class TestSimpleCache(unittest.TestCase):
    """Test the SimpleCache implementation."""

    def test_basic_set_get(self):
        """Test basic setting and getting values."""
        cache = SimpleCache(max_size=10, ttl=60)

        # Set a value
        cache.set("test_key", "test_value")

        # Get the value
        value = cache.get("test_key")

        # Verify value was retrieved
        self.assertEqual(value, "test_value")

    def test_ttl_expiration(self):
        """Test that values expire after TTL."""
        cache = SimpleCache(max_size=10, ttl=1)  # 1 second TTL

        # Set a value
        cache.set("expiring_key", "test_value")

        # Verify value is available immediately
        self.assertEqual(cache.get("expiring_key"), "test_value")

        # Wait for expiration
        time.sleep(1.1)

        # Value should be gone now
        self.assertIsNone(cache.get("expiring_key"))

    def test_max_size_eviction(self):
        """Test that old items are evicted when max size is reached."""
        cache = SimpleCache(max_size=3, ttl=60)

        # Fill the cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # All values should be present
        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key3"), "value3")

        # Add one more value, which should evict the oldest
        cache.set("key4", "value4")

        # The oldest key should be gone, but others remain
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key2"), "value2")
        self.assertEqual(cache.get("key3"), "value3")
        self.assertEqual(cache.get("key4"), "value4")

    def test_hit_miss_tracking(self):
        """Test that cache hit/miss tracking works correctly."""
        cache = SimpleCache(max_size=10, ttl=60)

        # Initial stats should have 0 hits and misses
        self.assertEqual(cache.hits, 0)
        self.assertEqual(cache.misses, 0)

        # Miss
        cache.get("missing_key")
        self.assertEqual(cache.hits, 0)
        self.assertEqual(cache.misses, 1)

        # Set a key
        cache.set("test_key", "test_value")

        # Hit
        cache.get("test_key")
        self.assertEqual(cache.hits, 1)
        self.assertEqual(cache.misses, 1)

        # Another miss
        cache.get("another_missing_key")
        self.assertEqual(cache.hits, 1)
        self.assertEqual(cache.misses, 2)

        # Verify hit ratio
        stats = cache.get_stats()
        self.assertEqual(stats["hit_ratio"], 1 / 3)

    def test_clear_cache(self):
        """Test that cache can be cleared."""
        cache = SimpleCache(max_size=10, ttl=60)

        # Add some values
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # Values should be present
        self.assertEqual(cache.get("key1"), "value1")
        self.assertEqual(cache.get("key2"), "value2")

        # Clear the cache
        cache.clear()

        # Values should be gone
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))

        # Cache should be empty
        stats = cache.get_stats()
        self.assertEqual(stats["size"], 0)

    def test_get_stats(self):
        """Test that cache statistics are correct."""
        cache = SimpleCache(max_size=10, ttl=30)

        # Check initial stats
        stats = cache.get_stats()
        self.assertEqual(stats["size"], 0)
        self.assertEqual(stats["max_size"], 10)
        self.assertEqual(stats["ttl"], 30)
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)
        self.assertEqual(stats["hit_ratio"], 0)

        # Add some data and get hits/misses
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss

        # Check updated stats
        stats = cache.get_stats()
        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_ratio"], 0.5)

    def test_concurrent_access(self):
        """Test cache behavior with concurrent access patterns."""
        cache = SimpleCache(max_size=100, ttl=60)

        # Define a function that hammers the cache
        def cache_worker(worker_id, iterations):
            for i in range(iterations):
                key = f"worker_{worker_id}_key_{i}"
                cache.set(key, f"value_{i}")
                cache.get(key)

        # Create and start threads
        threads = []
        for i in range(5):  # 5 concurrent workers
            t = threading.Thread(target=cache_worker, args=(i, 20))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify cache state
        stats = cache.get_stats()
        self.assertGreater(stats["hits"], 0)
        self.assertLessEqual(stats["size"], cache.max_size)
        # Size should be at most 100 items (the max_size)
        self.assertLessEqual(stats["size"], 100)
        # We expect 5 workers * 20 iterations = 100 items total created
        self.assertEqual(stats["hits"], 100)  # Each worker gets its own items once

    def test_update_existing_key(self):
        """Test updating an existing key in the cache."""
        cache = SimpleCache(max_size=10, ttl=60)

        # Set initial value
        cache.set("key", "value1")
        self.assertEqual(cache.get("key"), "value1")

        # Update the value
        cache.set("key", "value2")
        self.assertEqual(cache.get("key"), "value2")

        # Verify only one entry exists
        stats = cache.get_stats()
        self.assertEqual(stats["size"], 1)


if __name__ == "__main__":
    unittest.main()
