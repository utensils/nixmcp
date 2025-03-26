"""
Test multi-word query handling in NixMCP.
"""

import unittest
from unittest.mock import patch, MagicMock

from nixmcp.utils.helpers import create_wildcard_query, extract_hierarchical_paths, parse_multi_word_query
from nixmcp.tools.nixos_tools import nixos_search


class TestMultiWordQueryParsing(unittest.TestCase):
    """Test the multi-word query parsing functionality."""

    def test_create_wildcard_query(self):
        """Test basic wildcard query creation."""
        self.assertEqual(create_wildcard_query("term"), "*term*")
        self.assertEqual(create_wildcard_query("multi word"), "*multi* *word*")

    def test_extract_hierarchical_paths(self):
        """Test extraction of hierarchical paths from queries."""
        # Test with hierarchical path
        hierarchical, non_hierarchical = extract_hierarchical_paths("services.nginx port")
        self.assertEqual(hierarchical, ["services.nginx"])
        self.assertEqual(non_hierarchical, ["port"])

        # Test with multiple hierarchical paths
        hierarchical, non_hierarchical = extract_hierarchical_paths("services.nginx boot.loader.grub enable")
        self.assertEqual(hierarchical, ["services.nginx", "boot.loader.grub"])
        self.assertEqual(non_hierarchical, ["enable"])

        # Test with no hierarchical paths
        hierarchical, non_hierarchical = extract_hierarchical_paths("nginx enable port")
        self.assertEqual(hierarchical, [])
        self.assertEqual(non_hierarchical, ["nginx", "enable", "port"])

    def test_parse_multi_word_query(self):
        """Test parsing of multi-word queries with hierarchical paths and quotes."""
        # Test basic case
        result = parse_multi_word_query("services.acme acceptTerms")
        self.assertEqual(result["main_path"], "services.acme")
        self.assertEqual(result["terms"], ["acceptTerms"])
        self.assertEqual(result["quoted_terms"], [])

        # Test with quoted term
        result = parse_multi_word_query('services.nginx "access log"')
        self.assertEqual(result["main_path"], "services.nginx")
        self.assertEqual(result["terms"], [])
        self.assertEqual(result["quoted_terms"], ["access log"])

        # Test with multiple paths and terms
        result = parse_multi_word_query("services.nginx boot.loader enable ssl")
        self.assertEqual(result["main_path"], "services.nginx")
        self.assertEqual(result["additional_paths"], ["boot.loader"])
        self.assertEqual(result["terms"], ["enable", "ssl"])


@patch("nixmcp.tools.nixos_tools.get_context_or_fallback")
class TestNixOSSearchWithMultiWord(unittest.TestCase):
    """Test the nixos_search function with multi-word queries."""

    def setUp(self):
        """Set up the test environment."""
        self.mock_context = MagicMock()
        self.mock_es_client = MagicMock()
        self.mock_context.es_client = self.mock_es_client
        self.mock_context.search_options.return_value = {"options": [], "count": 0}

    def test_acme_search_issue(self, mock_get_context):
        """Test the issue from TODO.md: security.acme acceptTerms."""
        # Mock the context to return empty results
        mock_get_context.return_value = self.mock_context

        # Define a successful result for the search_options call
        self.mock_context.search_options.return_value = {
            "options": [
                {
                    "name": "security.acme.acceptTerms",
                    "description": "Accept the CA's terms of service.",
                    "type": "boolean",
                    "default": "false",
                }
            ],
            "count": 1,
        }

        # Test the improved multi-word query
        nixos_search(query="security.acme acceptTerms", type="options")

        # Verify that search_options was called with the correct parameters
        self.mock_context.search_options.assert_called_once()
        args, kwargs = self.mock_context.search_options.call_args

        # Check that we passed the main path as the query
        self.assertEqual(args[0], "security.acme")

        # Check that additional_terms contains "acceptTerms"
        self.assertIn("additional_terms", kwargs)
        self.assertEqual(kwargs["additional_terms"], ["acceptTerms"])

    def test_multi_word_with_quoted_terms(self, mock_get_context):
        """Test multi-word query with quoted terms."""
        # Mock the context to return empty results
        mock_get_context.return_value = self.mock_context

        # Define a successful result for the search_options call
        self.mock_context.search_options.return_value = {
            "options": [
                {
                    "name": "services.nginx.logFormat",
                    "description": "Format for the access log.",
                    "type": "string",
                    "default": "combined",
                }
            ],
            "count": 1,
        }

        # Test the multi-word query with quotes
        nixos_search(query='services.nginx "access log"', type="options")

        # Verify that search_options was called with the correct parameters
        self.mock_context.search_options.assert_called_once()
        args, kwargs = self.mock_context.search_options.call_args

        # Check that we passed the main path as the query
        self.assertEqual(args[0], "services.nginx")

        # Check that quoted_terms contains "access log"
        self.assertIn("quoted_terms", kwargs)
        self.assertEqual(kwargs["quoted_terms"], ["access log"])


if __name__ == "__main__":
    unittest.main()
