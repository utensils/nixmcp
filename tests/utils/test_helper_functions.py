"""Tests for helper functions in the MCP-NixOS server."""

import unittest
import pytest

# Mark as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.server import create_wildcard_query


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions in the server module."""

    def test_create_wildcard_query_single_word(self):
        """Test create_wildcard_query with a single word."""
        # Test simple single word query
        result = create_wildcard_query("python")
        self.assertEqual(result, "*python*")

        # Test empty query
        result = create_wildcard_query("")
        self.assertEqual(result, "**")

        # Test with special characters
        result = create_wildcard_query("c++")
        self.assertEqual(result, "*c++*")

        # Test with numbers
        result = create_wildcard_query("python3")
        self.assertEqual(result, "*python3*")

    def test_create_wildcard_query_multiple_words(self):
        """Test create_wildcard_query with multiple words."""
        # Test with two words
        result = create_wildcard_query("web server")
        self.assertEqual(result, "*web* *server*")

        # Test with three words
        result = create_wildcard_query("python web framework")
        self.assertEqual(result, "*python* *web* *framework*")

        # Test with extra spaces
        result = create_wildcard_query("  multiple   spaces   ")
        self.assertEqual(result, "*multiple* *spaces*")

        # Test with mixed case
        result = create_wildcard_query("Python Package")
        self.assertEqual(result, "*Python* *Package*")

    def test_create_wildcard_query_already_has_wildcards(self):
        """Test create_wildcard_query when input already has wildcards."""
        # This function doesn't detect existing wildcards, it just adds them
        result = create_wildcard_query("*python*")
        self.assertEqual(result, "**python**")

        # With multiple words
        result = create_wildcard_query("*python* *package*")
        self.assertEqual(result, "**python** **package**")


if __name__ == "__main__":
    unittest.main()
