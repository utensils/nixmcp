"""Tests for hierarchical path handling in MCP-NixOS."""

import json
import logging
import unittest
import pytest
from unittest.mock import patch

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import the server module
from mcp_nixos.server import ElasticsearchClient, create_wildcard_query

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestHierarchicalPathQueries(unittest.TestCase):
    """Test the construction of Elasticsearch queries for hierarchical paths."""

    def setUp(self):
        """Set up the test environment."""
        self.client = ElasticsearchClient()

        # Patch the safe_elasticsearch_query method to avoid real API calls
        patcher = patch.object(ElasticsearchClient, "safe_elasticsearch_query")
        self.mock_es_query = patcher.start()
        self.addCleanup(patcher.stop)

        # Set up default response that mimics empty results
        self.mock_es_query.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

    def test_service_path_query_structure(self):
        """Test the structure of queries generated for service paths."""
        # Call search_options with a service path
        self.client.search_options("services.postgresql")

        # Get the query that was generated
        args, kwargs = self.mock_es_query.call_args
        query_data = kwargs.get("query_data", args[1] if len(args) > 1 else None)

        # Verify the query follows the expected structure for service paths
        self.assertIsNotNone(query_data)
        self.assertIn("query", query_data)

        # For hierarchical paths we should have a boolean query
        query = query_data["query"]
        self.assertIn("bool", query)

        # Should have a filter for type=option
        bool_query = query["bool"]
        self.assertIn("filter", bool_query)

        # Check that we're adding wildcards for hierarchical paths
        self.assertIn("must", bool_query)

        # This is where we check for special service path handling
        if hasattr(bool_query["must"][0], "get") and bool_query["must"][0].get("bool"):
            # This is the enhanced structure with special service handling
            service_query = bool_query["must"][0]["bool"]
            self.assertIn("should", service_query)

            # Check for presence of prefix and wildcard queries
            should_clauses = service_query["should"]
            has_prefix = any("prefix" in clause for clause in should_clauses)
            has_wildcard = any("wildcard" in clause for clause in should_clauses)

            self.assertTrue(
                has_prefix or has_wildcard,
                "Service path query should include prefix or wildcard queries",
            )

    def test_hierarchical_path_wildcards(self):
        """Test wildcard handling for hierarchical paths."""
        # Test with a service path that doesn't end with a wildcard
        self.client.search_options("services.postgresql")

        # Get the query that was generated
        args, kwargs = self.mock_es_query.call_args
        query_data = kwargs.get("query_data", args[1] if len(args) > 1 else None)

        # Verify wildcards were added (services.postgresql*)
        query = query_data["query"]

        # Find any wildcards in the query
        query_str = json.dumps(query)
        self.assertIn("services.postgresql*", query_str)

    def test_regular_option_query_structure(self):
        """Test query structure for non-hierarchical option searches."""
        # Call search_options with a non-hierarchical path
        self.client.search_options("enable")

        # Get the query that was generated
        args, kwargs = self.mock_es_query.call_args
        query_data = kwargs.get("query_data", args[1] if len(args) > 1 else None)

        # Verify the query follows the expected structure for regular searches
        self.assertIsNotNone(query_data)
        self.assertIn("query", query_data)

        # Should still have a boolean query with a filter for type=option
        query = query_data["query"]
        self.assertIn("bool", query)
        bool_query = query["bool"]
        self.assertIn("filter", bool_query)

        # For regular searches, we expect a different structure than service paths
        self.assertIn("must", bool_query)

        # Check for standard search components
        first_must = bool_query["must"][0]
        self.assertTrue(
            "dis_max" in first_must or "multi_match" in first_must or "wildcard" in first_must,
            "Regular option query should use standard search components",
        )

    def test_explicit_wildcard_handling(self):
        """Test handling of explicit wildcards in queries."""
        # Call search_options with an explicit wildcard
        self.client.search_options("services.postgresql.*")

        # Get the query that was generated
        args, kwargs = self.mock_es_query.call_args
        query_data = kwargs.get("query_data", args[1] if len(args) > 1 else None)

        # Verify the wildcard was preserved exactly as provided
        query = query_data["query"]
        query_str = json.dumps(query)
        self.assertIn("services.postgresql.*", query_str)


class TestWildcardQueryGeneration(unittest.TestCase):
    """Test the create_wildcard_query helper function."""

    def test_single_term_wildcards(self):
        """Test wildcard generation for single term queries."""
        result = create_wildcard_query("postgresql")
        self.assertEqual(result, "*postgresql*")

    def test_multi_term_wildcards(self):
        """Test wildcard generation for multi-term queries."""
        result = create_wildcard_query("postgresql server")
        self.assertEqual(result, "*postgresql* *server*")

    def test_with_existing_wildcards(self):
        """Test that existing wildcards are preserved."""
        # Our function shouldn't be called directly in this case,
        # but let's test it anyway for completeness
        result = create_wildcard_query("postgresql*")
        self.assertEqual(result, "*postgresql**")


class TestChannelHandling(unittest.TestCase):
    """Test channel handling for hierarchical paths."""

    def setUp(self):
        """Set up the test environment."""
        self.client = ElasticsearchClient()

    def test_channel_url_construction(self):
        """Test that the correct URL is constructed for different channels."""
        # Test unstable channel
        self.client.set_channel("unstable")
        self.assertIn("unstable", self.client.es_packages_url)
        self.assertIn("unstable", self.client.es_options_url)

        # Test stable channel
        self.client.set_channel("24.11")
        self.assertIn("24.11", self.client.es_packages_url)
        self.assertIn("24.11", self.client.es_options_url)

    def test_fallback_to_unstable(self):
        """Test fallback to unstable for unknown channels."""
        # Set a known channel first
        self.client.set_channel("24.11")

        # Then try an invalid channel
        self.client.set_channel("invalid-channel")

        # Should fallback to unstable
        self.assertIn("unstable", self.client.es_packages_url)


class TestQueryBoostingValues(unittest.TestCase):
    """Test that query boosting is applied correctly."""

    def setUp(self):
        """Set up the test environment."""
        self.client = ElasticsearchClient()

        # Patch the safe_elasticsearch_query method to avoid real API calls
        patcher = patch.object(ElasticsearchClient, "safe_elasticsearch_query")
        self.mock_es_query = patcher.start()
        self.addCleanup(patcher.stop)

        # Set up default response
        self.mock_es_query.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

    def test_service_path_boost_values(self):
        """Test that service paths have appropriate boost values."""
        # Call search_options with a service path
        self.client.search_options("services.postgresql")

        # Get the query that was generated
        args, kwargs = self.mock_es_query.call_args
        query_data = kwargs.get("query_data", args[1] if len(args) > 1 else None)

        # Convert to string to check for boost values
        query_str = json.dumps(query_data)

        # Check for presence of boost values
        self.assertIn("boost", query_str)

        # For service paths, our boosted queries should be in this order (highest to lowest):
        # 1. Prefix matches (exact beginning matches)
        # 2. Wildcard matches (contains)
        # 3. Description matches

        # Rather than trying to parse the JSON structure, just check
        # that we have appropriate boost values in the query
        import re

        boost_pattern = r'"boost":\s*([\d.]+)'
        boost_values = [float(m) for m in re.findall(boost_pattern, query_str)]

        # We should have at least 2 boost values
        self.assertGreaterEqual(len(boost_values), 2, "Query should contain at least 2 boost values")

        # Check that we have a range of boost values (some should be higher than others)
        self.assertGreater(
            max(boost_values),
            min(boost_values),
            "Query should have a range of boost values to prioritize matches",
        )


if __name__ == "__main__":
    unittest.main()
