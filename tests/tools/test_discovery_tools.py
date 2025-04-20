"""Tests for the discovery tools in the MCP-NixOS server."""

import unittest
import pytest
from unittest.mock import MagicMock, patch

# Mark as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.tools.discovery_tools import (
    get_tool_list,
    get_tool_schema,
    get_tool_examples,
    get_tool_tips,
    get_tool_usage,
)


class TestDiscoveryTools(unittest.TestCase):
    """Test the Discovery MCP tools."""

    def test_get_tool_list(self):
        """Test that get_tool_list returns all expected tools."""
        tools = get_tool_list()

        # Check type
        self.assertIsInstance(tools, dict)

        # Check if it contains expected tools
        expected_tools = [
            "nixos_search",
            "nixos_info",
            "nixos_stats",
            "home_manager_search",
            "home_manager_info",
            "home_manager_stats",
            "home_manager_list_options",
            "home_manager_options_by_prefix",
            "darwin_search",
            "darwin_info",
            "darwin_stats",
            "darwin_list_options",
            "darwin_options_by_prefix",
            "discover_tools",
            "get_tool_usage",
        ]

        for tool in expected_tools:
            self.assertIn(tool, tools)
            self.assertIsInstance(tools[tool], str)
            self.assertTrue(len(tools[tool]) > 0)

    def test_get_tool_schema(self):
        """Test that get_tool_schema returns the correct schema for tools."""
        # Test schema for nixos_search
        nixos_search_schema = get_tool_schema("nixos_search")
        self.assertIsInstance(nixos_search_schema, dict)

        # Check ctx parameter is included
        self.assertIn("ctx", nixos_search_schema)
        self.assertEqual(nixos_search_schema["ctx"]["type"], "string")
        self.assertTrue(nixos_search_schema["ctx"]["required"])
        self.assertIn("MCP context parameter", nixos_search_schema["ctx"]["description"])

        # Check required parameters
        self.assertIn("query", nixos_search_schema)
        self.assertEqual(nixos_search_schema["query"]["type"], "string")
        self.assertTrue(nixos_search_schema["query"]["required"])

        # Check optional parameters
        self.assertIn("type", nixos_search_schema)
        self.assertEqual(nixos_search_schema["type"]["default"], "packages")

        self.assertIn("limit", nixos_search_schema)
        self.assertEqual(nixos_search_schema["limit"]["default"], 20)

        self.assertIn("channel", nixos_search_schema)
        self.assertEqual(nixos_search_schema["channel"]["default"], "unstable")

        # Test schema for a tool with fewer parameters
        home_manager_stats_schema = get_tool_schema("home_manager_stats")
        self.assertIsInstance(home_manager_stats_schema, dict)
        self.assertGreaterEqual(len(home_manager_stats_schema), 1)  # At least ctx parameter
        self.assertIn("ctx", home_manager_stats_schema)

        # Test schema for a non-existent tool
        non_existent_schema = get_tool_schema("non_existent_tool")
        self.assertIn("error", non_existent_schema)

    def test_all_schemas_include_ctx(self):
        """Test that all schemas include the ctx parameter."""
        tools = get_tool_list()

        for tool_name in tools:
            schema = get_tool_schema(tool_name)

            # Skip tools that return error schemas
            if "error" in schema:
                continue

            self.assertIn("ctx", schema, f"Tool {tool_name} missing ctx parameter in schema")
            self.assertEqual(schema["ctx"]["type"], "string")
            self.assertTrue(schema["ctx"]["required"])
            self.assertIn("MCP context parameter", schema["ctx"]["description"])

    def test_get_tool_examples(self):
        """Test that get_tool_examples returns examples for tools."""
        # Test examples for nixos_search
        nixos_search_examples = get_tool_examples("nixos_search")
        self.assertIsInstance(nixos_search_examples, dict)
        self.assertGreater(len(nixos_search_examples), 0)

        # Check expected example keys
        self.assertIn("Search packages", nixos_search_examples)
        self.assertIn("Search options", nixos_search_examples)

        # Verify example content
        self.assertIn("nixos_search", nixos_search_examples["Search packages"])
        self.assertIn("ctx", nixos_search_examples["Search packages"])
        self.assertIn("query=", nixos_search_examples["Search packages"])

        # Test examples for a non-existent tool
        non_existent_examples = get_tool_examples("non_existent_tool")
        self.assertIn("error", non_existent_examples)

    def test_examples_include_ctx_parameter(self):
        """Test that all examples include the ctx parameter."""
        # Get all tools
        tools = get_tool_list()

        # Check each tool's examples for ctx parameter
        for tool_name in tools.keys():
            examples = get_tool_examples(tool_name)

            # Skip tools that return error examples
            if "error" in examples:
                continue

            # Check each example for the tool
            for example_name, example_text in examples.items():
                self.assertIn(
                    "ctx", example_text, f"Example '{example_name}' for tool '{tool_name}' is missing ctx parameter"
                )

    def test_get_tool_tips(self):
        """Test that get_tool_tips returns best practices for tools."""
        # Test tips for nixos_search
        nixos_search_tips = get_tool_tips("nixos_search")
        self.assertIsInstance(nixos_search_tips, dict)
        self.assertGreater(len(nixos_search_tips), 0)

        # Check expected tip keys
        self.assertIn("use_wildcards", nixos_search_tips)
        self.assertIn("channels", nixos_search_tips)

        # Test tips for a non-existent tool
        non_existent_tips = get_tool_tips("non_existent_tool")
        self.assertIn("error", non_existent_tips)

    def test_get_tool_usage(self):
        """Test that get_tool_usage returns comprehensive usage info."""
        # Test usage for nixos_search
        with patch("mcp_nixos.tools.discovery_tools.logger") as mock_logger:
            nixos_search_usage = get_tool_usage("nixos_search")

            # Check that logging happened
            mock_logger.info.assert_called_once()

            # Check return structure
            self.assertIsInstance(nixos_search_usage, dict)
            self.assertEqual(nixos_search_usage["name"], "nixos_search")
            self.assertIn("description", nixos_search_usage)
            self.assertIn("parameters", nixos_search_usage)
            self.assertIn("examples", nixos_search_usage)
            self.assertIn("best_practices", nixos_search_usage)

            # Check parameters
            self.assertIn("query", nixos_search_usage["parameters"])

            # Check examples
            self.assertIn("Search packages", nixos_search_usage["examples"])

            # Check best practices
            self.assertIn("use_wildcards", nixos_search_usage["best_practices"])

        # Test usage for a non-existent tool
        with patch("mcp_nixos.tools.discovery_tools.logger") as mock_logger:
            non_existent_usage = get_tool_usage("non_existent_tool")

            # Check that logging happened
            mock_logger.info.assert_called_once()

            # Check error response
            self.assertIn("error", non_existent_usage)
            self.assertIn("available_tools", non_existent_usage)
            self.assertIsInstance(non_existent_usage["available_tools"], list)
            self.assertGreater(len(non_existent_usage["available_tools"]), 0)


class TestDiscoveryToolsRegistration(unittest.TestCase):
    """Test the registration of discovery tools."""

    def test_register_discovery_tools(self):
        """Test that register_discovery_tools correctly registers tools."""
        # Import here to avoid circular import
        from mcp_nixos.tools.discovery_tools import register_discovery_tools

        # Create a mock MCP server
        mock_mcp = MagicMock()
        mock_decorator = MagicMock()
        mock_mcp.tool = MagicMock(return_value=mock_decorator)

        # Call register_discovery_tools
        register_discovery_tools(mock_mcp)

        # Verify that tool registration methods were called
        # When a decorator is used, it creates two calls in the mock:
        # 1. The decorator itself (which returns a wrapper function)
        # 2. The wrapper function being called with the function to decorate
        # Since we have 2 tools (discover_tools and get_tool_usage), we expect at least 2 calls
        self.assertGreaterEqual(mock_mcp.tool.call_count, 2)

        # Inspect the functions that were decorated to ensure they have ctx parameter
        decorator_calls = mock_decorator.mock_calls
        decorated_functions = []
        for call in decorator_calls:
            if len(call.args) > 0:
                decorated_functions.append(call.args[0])

        # Verify at least some functions were found
        self.assertGreaterEqual(len(decorated_functions), 1)

        # Check that the functions have ctx parameter
        for func in decorated_functions:
            import inspect

            params = list(inspect.signature(func).parameters.keys())
            self.assertIn("ctx", params, f"Function {func.__name__} is missing ctx parameter")
            # Check ctx is the first parameter
            self.assertEqual(params[0], "ctx", f"Function {func.__name__} should have ctx as first parameter")


if __name__ == "__main__":
    unittest.main()
