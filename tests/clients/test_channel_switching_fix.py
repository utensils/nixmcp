"""Test for the fix to ensure cache is only cleared when channel actually changes."""

import unittest
import pytest
from unittest.mock import patch, Mock, MagicMock

# Import the ElasticsearchClient class that we fixed
from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient


class TestChannelSwitchingFix(unittest.TestCase):
    """Test the fix for channel switching behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a client for testing
        self.client = ElasticsearchClient()
        
        # Track cache clearing
        self.original_clear = self.client.cache.clear
        self.cache_clear_count = 0
        
        def mock_clear():
            self.cache_clear_count += 1
            return self.original_clear()
            
        self.client.cache.clear = mock_clear
    
    def tearDown(self):
        """Tear down test fixtures."""
        if hasattr(self, 'client') and hasattr(self.client, 'cache'):
            self.client.cache.clear = self.original_clear
    
    def test_cache_cleared_only_on_actual_change(self):
        """Test that cache is only cleared when channel actually changes."""
        # Reset counter
        self.cache_clear_count = 0
        
        # First set channel to current value (unstable) - should not clear cache
        current_channel = self.client._current_channel_id
        current_channel_name = next(name for name, cid in self.client.available_channels.items() 
                                   if cid == current_channel)
        
        # Call set_channel with same channel multiple times
        self.client.set_channel(current_channel_name)
        self.client.set_channel(current_channel_name)
        self.client.set_channel(current_channel_name)
        
        # Cache should not be cleared if channel didn't change
        self.assertEqual(self.cache_clear_count, 0, 
                         "Cache was cleared despite channel not changing")
        
        # Now set to a different channel - should clear cache
        different_channel = "24.11" if current_channel_name != "24.11" else "unstable"
        self.client.set_channel(different_channel)
        
        # Verify cache was cleared exactly once
        self.assertEqual(self.cache_clear_count, 1,
                         "Cache should be cleared exactly once when changing channel")
        
        # Try setting to the same new channel multiple times - should not clear again
        self.client.set_channel(different_channel)
        self.client.set_channel(different_channel)
        
        # Cache should still only be cleared once
        self.assertEqual(self.cache_clear_count, 1,
                         "Cache was incorrectly cleared when setting to same channel")
    
    def test_urls_always_updated(self):
        """Test that URLs are always updated regardless of channel changes."""
        # Get initial URLs
        initial_packages_url = self.client.es_packages_url
        initial_options_url = self.client.es_options_url
        
        # Call set_channel with current channel
        current_channel = self.client._current_channel_id
        current_channel_name = next(name for name, cid in self.client.available_channels.items() 
                                   if cid == current_channel)
        self.client.set_channel(current_channel_name)
        
        # URLs should be set even if channel didn't change
        self.assertEqual(initial_packages_url, self.client.es_packages_url)
        self.assertEqual(initial_options_url, self.client.es_options_url)
        
        # Now change to different channel
        different_channel = "24.11" if current_channel_name != "24.11" else "unstable"
        self.client.set_channel(different_channel)
        
        # URLs should be different
        self.assertNotEqual(initial_packages_url, self.client.es_packages_url)
        self.assertNotEqual(initial_options_url, self.client.es_options_url)
    
    def test_channel_state_always_updated(self):
        """Test that internal channel state is always updated."""
        # Get current channel
        original_channel_id = self.client._current_channel_id
        
        # Set to different channel
        different_channel = "24.11" if "unstable" in original_channel_id else "unstable"
        self.client.set_channel(different_channel)
        
        # Internal state should be updated
        different_channel_id = self.client.available_channels[different_channel]
        self.assertEqual(self.client._current_channel_id, different_channel_id)
        self.assertNotEqual(original_channel_id, self.client._current_channel_id)


if __name__ == "__main__":
    unittest.main()