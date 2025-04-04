"""Tests for error handling in the Home Manager context."""

import pytest
from unittest import mock

from mcp_nixos.contexts.home_manager_context import HomeManagerContext
from mcp_nixos.clients.home_manager_client import HomeManagerClient


# Mark as unit tests
pytestmark = pytest.mark.unit


class TestHomeManagerErrorHandling:
    """Tests for error handling in the Home Manager context."""

    def test_search_options_with_loading_in_progress(self):
        """Test search_options when client is still loading."""
        # Create a context with loading in progress
        context = HomeManagerContext()

        # Mock the client to show loading in progress
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = True
        mock_client.loading_error = None
        context.hm_client = mock_client

        # Search should return loading information
        results = context.search_options("test")
        assert results["found"] is False
        assert results["loading"] is True
        assert "loading" in results["error"].lower()

    def test_search_options_with_loading_error(self):
        """Test search_options when client has a loading error."""
        # Create a context with a loading error
        context = HomeManagerContext()

        # Mock the client to have a loading error
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = False
        mock_client.loading_error = "Test loading error"
        context.hm_client = mock_client

        # Search should return error information
        results = context.search_options("test")
        assert results["found"] is False
        assert "error" in results["error"].lower()

    def test_search_options_with_client_exception(self):
        """Test search_options when client raises an exception."""
        # Create a mock client that raises an exception during search
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = False
        mock_client.loading_error = None
        mock_client.search_options.side_effect = Exception("Test search error")

        # Create context with our mock client
        context = HomeManagerContext()
        context.hm_client = mock_client

        # Search should handle the exception and return error info
        results = context.search_options("test")
        assert results["found"] is False
        assert "error" in results["error"].lower()

    def test_get_option_with_loading_in_progress(self):
        """Test get_option when client is still loading."""
        # Create a context with loading in progress
        context = HomeManagerContext()

        # Mock the client to show loading in progress
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = True
        mock_client.loading_error = None
        context.hm_client = mock_client

        # get_option should return loading information
        result = context.get_option("programs.git.enable")
        assert result["found"] is False
        assert result["loading"] is True
        assert "loading" in result["error"].lower()

    def test_get_option_with_loading_error(self):
        """Test get_option when client has a loading error."""
        # Create a context with a loading error
        context = HomeManagerContext()

        # Mock the client to have a loading error
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = False
        mock_client.loading_error = "Test loading error"
        context.hm_client = mock_client

        # get_option should return error information
        result = context.get_option("programs.git.enable")
        assert result["found"] is False
        assert "error" in result["error"].lower()

    def test_get_option_with_client_exception(self):
        """Test get_option when client raises an exception."""
        # Create a mock client that raises an exception during get_option
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = False
        mock_client.loading_error = None
        mock_client.get_option.side_effect = Exception("Test get_option error")

        # Create context with our mock client
        context = HomeManagerContext()
        context.hm_client = mock_client

        # get_option should handle the exception and return error info
        result = context.get_option("programs.git.enable")
        assert result["found"] is False
        assert "error" in result["error"].lower()

    def test_get_option_not_found(self):
        """Test get_option when option is not found."""
        # Create a mock client that returns "not found" for get_option
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = False
        mock_client.loading_error = None
        mock_client.get_option.return_value = {
            "name": "nonexistent.option",
            "found": False,
            "error": "Option not found",
        }

        # Create context with our mock client
        context = HomeManagerContext()
        context.hm_client = mock_client

        # get_option should return not found
        result = context.get_option("programs.nonexistent.option")
        assert result["found"] is False
        assert "not found" in result["error"].lower()

    def test_get_options_by_prefix_with_loading_in_progress(self):
        """Test get_options_by_prefix when client is still loading."""
        # Create a context with loading in progress
        context = HomeManagerContext()

        # Mock the client to show loading in progress
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = True
        mock_client.loading_error = None
        context.hm_client = mock_client

        # get_options_by_prefix should return loading information
        result = context.get_options_by_prefix("programs")
        assert result["found"] is False
        assert result["loading"] is True
        assert "loading" in result["error"].lower()

    def test_get_options_by_prefix_with_loading_error(self):
        """Test get_options_by_prefix when client has a loading error."""
        # Create a context with a loading error
        context = HomeManagerContext()

        # Mock the client to have a loading error
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = False
        mock_client.loading_error = "Test loading error"
        context.hm_client = mock_client

        # get_options_by_prefix should return error information
        result = context.get_options_by_prefix("programs")
        assert result["found"] is False
        assert "error" in result["error"].lower()

    def test_get_options_list_with_loading_in_progress(self):
        """Test get_options_list when client is still loading."""
        # Create a context with loading in progress
        context = HomeManagerContext()

        # Mock the client to show loading in progress
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = True
        mock_client.loading_error = None
        context.hm_client = mock_client

        # get_options_list should return loading information
        result = context.get_options_list()
        assert result["found"] is False
        assert result["loading"] is True
        assert "loading" in result["error"].lower()

    def test_get_stats_with_loading_in_progress(self):
        """Test get_stats when client is still loading."""
        # Create a context with loading in progress
        context = HomeManagerContext()

        # Mock the client to show loading in progress
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = True
        mock_client.loading_error = None
        context.hm_client = mock_client

        # get_stats should return loading information
        result = context.get_stats()
        assert result["found"] is False
        assert result["loading"] is True
        assert "loading" in result["error"].lower()

    def test_get_stats_with_loading_error(self):
        """Test get_stats when client has a loading error."""
        # Create a context with a loading error
        context = HomeManagerContext()

        # Mock the client to have a loading error
        mock_client = mock.MagicMock(spec=HomeManagerClient)
        mock_client.loading_in_progress = False
        mock_client.loading_error = "Test loading error"
        context.hm_client = mock_client

        # get_stats should return error information
        result = context.get_stats()
        assert result["found"] is False
        assert "error" in result["error"].lower()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
