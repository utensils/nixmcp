"""Test for the context handling behavior."""

import unittest
from unittest.mock import patch, Mock

# Import the function we're testing
from mcp_nixos.tools.nixos_tools import _setup_context_and_channel


class TestMinimalContextHandling(unittest.TestCase):
    """Basic tests for context handling behavior."""

    def test_direct_context_handling(self):
        """Test handling of direct context object."""
        # Create a mock ES client
        es_client = Mock()

        # Create a direct context with the ES client
        context = Mock()
        context.es_client = es_client

        # Call the function
        result = _setup_context_and_channel(context, "test-channel")

        # Verify set_channel was called correctly
        es_client.set_channel.assert_called_once_with("test-channel")

        # Verify context is returned
        self.assertEqual(result, context)

    @patch("importlib.import_module")
    def test_none_context_handling(self, mock_import):
        """Test handling of None context."""
        # Create a mock ES client
        es_client = Mock()

        # Create a context with the ES client
        context = Mock()
        context.es_client = es_client

        # Set up mock server module
        mock_server = Mock()
        mock_server.get_nixos_context = Mock(return_value=context)
        mock_import.return_value = mock_server

        # Call the function with None context
        result = _setup_context_and_channel(None, "test-channel")

        # Verify import was called correctly
        mock_import.assert_called_once_with("mcp_nixos.server")

        # Verify get_nixos_context was called
        mock_server.get_nixos_context.assert_called_once()

        # Verify set_channel was called correctly
        es_client.set_channel.assert_called_once_with("test-channel")

        # Verify context is returned
        self.assertEqual(result, context)


if __name__ == "__main__":
    unittest.main()
