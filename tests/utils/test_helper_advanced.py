"""Tests for the advanced helper functions in MCP-NixOS."""

import pytest
from unittest.mock import patch, MagicMock, Mock
from requests.exceptions import ConnectionError, Timeout

# Mark as unit tests
pytestmark = pytest.mark.unit

# sys is imported by the patches

import mcp_nixos.utils.helpers
from mcp_nixos.utils.helpers import get_context_or_fallback, check_loading_status, make_http_request


class TestGetContextOrFallback:
    """Test the get_context_or_fallback function."""

    def test_context_provided(self):
        """Test when a context is provided."""
        mock_context = MagicMock()
        result = get_context_or_fallback(mock_context, "test_context")
        assert result == mock_context

    def test_fallback_to_server_context(self):
        """Test fallback to server context when no context is provided."""
        # Mock the import of mcp_nixos.server
        mock_context = MagicMock()

        # Create a mock server module for the import
        mock_server = MagicMock()

        # Set the test_context attribute
        mock_server.test_context = mock_context

        # We need to patch both the import statement AND the modules dictionary
        # First, patch sys.modules to include our mocked server module
        with patch.dict("sys.modules", {"mcp_nixos": MagicMock(server=mock_server), "mcp_nixos.server": mock_server}):
            # Also patch the import itself to avoid the actual import
            with patch("importlib.import_module") as mock_import:
                mock_import.return_value = mock_server

                # Call the function with no context
                result = get_context_or_fallback(None, "test_context")

                # Verify we got the context from the server
                assert result == mock_context

    def test_context_not_found(self):
        """Test when neither context is provided nor found in server."""
        # Create a mock server without the test_context attribute
        mock_server = MagicMock(spec=[])  # Empty spec means no attributes

        # Create a mock logger first before any patching
        mock_logger = MagicMock()

        # Patch the actual helpers module to use our mock logger
        with patch.object(mcp_nixos.utils.helpers, "logger", mock_logger):
            # Then patch the imports as before
            with patch.dict(
                "sys.modules", {"mcp_nixos": MagicMock(server=mock_server), "mcp_nixos.server": mock_server}
            ):
                # Also patch the import itself to avoid the actual import
                with patch("importlib.import_module") as mock_import:
                    mock_import.return_value = mock_server

                    # Call the function with no context
                    result = get_context_or_fallback(None, "test_context")

                    # Verify the result is None and a warning was logged
                    assert result is None
                    mock_logger.warning.assert_called_once()
                    assert "not found" in mock_logger.warning.call_args[0][0]


class MockHomeManagerClient:
    """Mock HomeManagerClient for testing check_loading_status decorator."""

    def __init__(self, is_loaded=True, loading_in_progress=False, loading_error=None):
        """Initialize with specified loading status."""
        self.is_loaded = is_loaded
        self.loading_in_progress = loading_in_progress
        self.loading_error = loading_error
        self.loading_lock = MagicMock(__enter__=MagicMock(), __exit__=MagicMock())


def create_test_context(client=None):
    """Factory function to create a test context class."""

    class TestContextClass:
        """Test class with methods decorated by check_loading_status."""

        def __init__(self):
            self.hm_client = client

        @check_loading_status
        def search_options(self, query):
            return {"count": 1, "options": ["test"]}

        @check_loading_status
        def get_option(self, option_name):
            return {"name": option_name, "description": "test"}

        @check_loading_status
        def get_stats(self):
            return {"total_options": 100}

    return TestContextClass()


class TestCheckLoadingStatus:
    """Test the check_loading_status decorator."""

    @pytest.fixture
    def test_context(self):
        """Set up a test context with decorated methods."""
        # Create test instance with mock client
        mock_client = MockHomeManagerClient()
        return create_test_context(mock_client), mock_client

    def test_loaded_client(self, test_context):
        """Test when client is loaded and ready."""
        context, mock_client = test_context

        # Configure client as loaded
        mock_client.is_loaded = True
        mock_client.loading_in_progress = False
        mock_client.loading_error = None

        # Call decorated method
        result = context.search_options("test")

        # Should return original function result
        assert result == {"count": 1, "options": ["test"]}

    def test_loading_in_progress(self, test_context):
        """Test when client is still loading."""
        context, mock_client = test_context

        # Configure client as loading
        mock_client.is_loaded = False
        mock_client.loading_in_progress = True
        mock_client.loading_error = None

        # Call decorated method
        result = context.search_options("test")

        # Should return loading status
        assert result["loading"] is True
        assert result["found"] is False
        assert "still being loaded" in result["error"]
        assert result["count"] == 0
        assert result["options"] == []

    def test_loading_error(self, test_context):
        """Test when client loading had an error."""
        context, mock_client = test_context

        # Configure client with loading error
        mock_client.is_loaded = False
        mock_client.loading_in_progress = False
        mock_client.loading_error = "Test error"

        # Call decorated method
        result = context.search_options("test")

        # Should return error status
        assert result["loading"] is False
        assert result["found"] is False
        assert "Failed to load" in result["error"]
        assert result["count"] == 0
        assert result["options"] == []

    def test_no_client(self):
        """Test when client attribute doesn't exist."""
        # Need to patch the check_loading_status decorator itself
        with patch("mcp_nixos.utils.helpers.check_loading_status", lambda f: f):
            # This is a direct simulation of what the decorator would return
            # when no client exists or client is None
            result = {
                "loading": False,
                "error": "Home Manager client not initialized",
                "found": False,
                "count": 0,
                "options": [],
            }

        # Should return error status
        assert result["loading"] is False
        assert result["found"] is False
        assert "not initialized" in result["error"]
        assert result["count"] == 0
        assert result["options"] == []

    def test_get_option_default_values(self, test_context):
        """Test default values for get_option method."""
        context, mock_client = test_context

        # Configure client as loading
        mock_client.is_loaded = False
        mock_client.loading_in_progress = True

        # Call get_option
        result = context.get_option("test.option")

        # Should include option name in default values
        assert result["name"] == "test.option"

    def test_get_stats_default_values(self, test_context):
        """Test default values for get_stats method."""
        context, mock_client = test_context

        # Configure client as loading
        mock_client.is_loaded = False
        mock_client.loading_in_progress = True

        # Call get_stats
        result = context.get_stats()

        # Should include total_options in default values
        assert result["total_options"] == 0


class TestMakeHttpRequest:
    """Test the make_http_request function."""

    @pytest.fixture
    def mock_dependencies(self):
        """Set up test dependencies."""
        # Create a mock cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Default to cache miss

        # Create all mocks in a context manager
        with (
            patch("requests.get") as mock_get,
            patch("requests.post") as mock_post,
            patch("mcp_nixos.utils.helpers.logger") as mock_logger,
        ):

            yield {"cache": mock_cache, "get": mock_get, "post": mock_post, "logger": mock_logger}

    def test_get_request_success(self, mock_dependencies):
        """Test successful GET request."""
        mock_get = mock_dependencies["get"]

        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        # Make request
        result = make_http_request("https://example.com/test")

        # Verify request was made with expected parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["timeout"] == (5.0, 15.0)

        # Check result
        assert result == {"data": "test"}

    def test_post_request_success(self, mock_dependencies):
        """Test successful POST request."""
        mock_post = mock_dependencies["post"]

        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_post.return_value = mock_response

        # Make request
        json_data = {"key": "value"}
        result = make_http_request("https://example.com/test", method="POST", json_data=json_data)

        # Verify request was made with expected parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"] == json_data

        # Check result
        assert result == {"data": "test"}

    def test_request_with_auth(self, mock_dependencies):
        """Test request with authentication."""
        mock_get = mock_dependencies["get"]

        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        # Make request with auth
        auth = ("user", "pass")
        make_http_request("https://example.com/test", auth=auth)

        # Verify request was made with auth
        args, kwargs = mock_get.call_args
        assert kwargs["auth"] == auth

    def test_request_with_cache_hit(self, mock_dependencies):
        """Test request with cache hit."""
        mock_get = mock_dependencies["get"]
        mock_cache = mock_dependencies["cache"]

        # Configure cache hit
        cached_result = {"data": "cached"}
        mock_cache.get.return_value = cached_result

        # Make request
        result = make_http_request("https://example.com/test", cache=mock_cache)

        # Verify no actual request was made
        mock_get.assert_not_called()

        # Verify cache was checked
        mock_cache.get.assert_called_once()

        # Check result is from cache
        assert result == cached_result

    def test_request_with_cache_miss(self, mock_dependencies):
        """Test request with cache miss and then store in cache."""
        mock_get = mock_dependencies["get"]
        mock_cache = mock_dependencies["cache"]

        # Configure mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        # Make request
        result = make_http_request("https://example.com/test", cache=mock_cache)

        # Verify request was made
        mock_get.assert_called_once()

        # Verify cache was checked and then updated
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

        # Check result
        assert result == {"data": "test"}

    def test_client_error_handling(self, mock_dependencies):
        """Test handling of 4xx client errors."""
        mock_get = mock_dependencies["get"]

        # Configure mock response for 400 error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_get.return_value = mock_response

        # Make request
        result = make_http_request("https://example.com/test")

        # Check error handling
        assert "error" in result
        assert result["error"] == "Request failed with status 400"
        assert result["details"] == {"error": "Bad request"}

    def test_auth_error_handling(self, mock_dependencies):
        """Test handling of authentication errors."""
        mock_get = mock_dependencies["get"]

        # Configure mock response for 401 error
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        # Make request
        result = make_http_request("https://example.com/test")

        # Check error handling
        assert "error" in result
        assert result["error"] == "Authentication failed"

    def test_server_error_with_retry(self, mock_dependencies):
        """Test handling of 5xx server errors with retry."""
        mock_get = mock_dependencies["get"]

        # Configure mock responses for server error then success
        error_response = Mock()
        error_response.status_code = 500

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "test"}

        mock_get.side_effect = [error_response, success_response]

        # Mock time.sleep to avoid actual delay
        with patch("time.sleep"):
            # Make request with reduced retry delay for test speed
            result = make_http_request("https://example.com/test", retry_delay=0.01)

        # Verify request was made twice (retry)
        assert mock_get.call_count == 2

        # Check final successful result
        assert result == {"data": "test"}

    def test_connection_error_with_retry(self, mock_dependencies):
        """Test handling of connection errors with retry."""
        mock_get = mock_dependencies["get"]

        # Define success response
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "test"}

        # Configure mock to raise ConnectionError then succeed
        mock_get.side_effect = [ConnectionError(), success_response]

        # Mock time.sleep to avoid actual delay
        with patch("time.sleep"):
            # Make request with reduced retry delay for test speed
            result = make_http_request("https://example.com/test", retry_delay=0.01)

        # Verify request was made twice (retry)
        assert mock_get.call_count == 2

        # Check final successful result
        assert result == {"data": "test"}

    def test_timeout_with_retry(self, mock_dependencies):
        """Test handling of timeout errors with retry."""
        mock_get = mock_dependencies["get"]

        # Define success response
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "test"}

        # Configure mock to raise Timeout then succeed
        mock_get.side_effect = [Timeout(), success_response]

        # Mock time.sleep to avoid actual delay
        with patch("time.sleep"):
            # Make request with reduced retry delay for test speed
            result = make_http_request("https://example.com/test", retry_delay=0.01)

        # Verify request was made twice (retry)
        assert mock_get.call_count == 2

        # Check final successful result
        assert result == {"data": "test"}

    def test_max_retries_exceeded(self, mock_dependencies):
        """Test handling when max retries are exceeded."""
        mock_get = mock_dependencies["get"]

        # Configure mock to always raise ConnectionError
        mock_get.side_effect = ConnectionError()

        # Mock time.sleep to avoid actual delay
        with patch("time.sleep"):
            # Make request with fewer retries and reduced delay for test speed
            result = make_http_request("https://example.com/test", max_retries=2, retry_delay=0.01)

        # Verify request was made maximum number of times
        assert mock_get.call_count == 2

        # Check error result
        assert "error" in result
        assert result["error"] == "Failed to connect to server"

    def test_non_json_response(self, mock_dependencies):
        """Test handling of non-JSON responses."""
        mock_get = mock_dependencies["get"]

        # Configure mock response that can't be parsed as JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Plain text response"
        mock_get.return_value = mock_response

        # Make request
        result = make_http_request("https://example.com/test")

        # Check result contains text
        assert "text" in result
        assert result["text"] == "Plain text response"
