"""
Tests for the Home Manager hierarchical options support.
"""

import unittest
from unittest.mock import patch, MagicMock
import pytest

# Import the tools to test
from mcp_nixos.tools.home_manager_tools import (
    home_manager_search,
    home_manager_options_by_prefix,
)

# Mark as unit tests
pytestmark = pytest.mark.unit


class TestHomeManagerHierarchy(unittest.TestCase):
    """Test the Home Manager hierarchical option functionality."""

    def setUp(self):
        """Set up a mock context with hierarchical options."""
        self.mock_context = MagicMock()
        
        # Mock search_options to return hierarchical results
        self.mock_search_results = {
            "count": 5,
            "options": [
                {
                    "name": "programs.git.enable",
                    "description": "Whether to enable Git.",
                    "type": "boolean",
                    "default": "false",
                },
                {
                    "name": "programs.git.userName",
                    "description": "Your Git username.",
                    "type": "string",
                    "default": "null",
                },
                {
                    "name": "programs.git.userEmail",
                    "description": "Your Git email.",
                    "type": "string",
                    "default": "null",
                },
                {
                    "name": "programs.git.signing.key",
                    "description": "Git signing key.",
                    "type": "string",
                    "default": "null",
                },
                {
                    "name": "programs.git.signing.signByDefault",
                    "description": "Whether to sign commits by default.",
                    "type": "boolean",
                    "default": "false",
                },
            ],
            "found": True,
        }
        self.mock_context.search_options.return_value = self.mock_search_results
        
        # Mock get_options_by_prefix
        self.mock_prefix_results = {
            "prefix": "programs.git",
            "options": self.mock_search_results["options"],
            "count": 5,
            "types": {"boolean": 2, "string": 3},
            "enable_options": [
                {
                    "name": "programs.git.enable",
                    "parent": "git",
                    "description": "Whether to enable Git."
                }
            ],
            "found": True,
        }
        self.mock_context.get_options_by_prefix.return_value = self.mock_prefix_results

    def test_wildcard_search_behavior(self):
        """Test that search adds wildcards correctly."""
        # Test case 1: Simple query without wildcards
        result = home_manager_search("git", context=self.mock_context)
        # Verify wildcards were added to the query
        self.mock_context.search_options.assert_called_with("*git*", 20)
        self.assertIn("git", result)  # Should find git in the results
        
        # Test case 2: Query with existing wildcards
        self.mock_context.search_options.reset_mock()
        result = home_manager_search("*git*", context=self.mock_context)
        # Verify wildcards were NOT added again
        self.mock_context.search_options.assert_called_with("*git*", 20)
        
        # Test case 3: Query with dot suffix (hierarchical path)
        self.mock_context.search_options.reset_mock()
        result = home_manager_search("programs.git.", context=self.mock_context)
        # Verify wildcards were NOT added to hierarchical path with trailing dot
        self.mock_context.search_options.assert_called_with("programs.git.", 20)

    def test_options_by_prefix(self):
        """Test getting options by hierarchical prefix."""
        # Mock the output to include expected text in the result
        # This is needed because the actual output is formatted by the function
        # and may not match our exact expectations
        def side_effect_get_options_by_prefix(prefix):
            result = self.mock_prefix_results
            # Adding an actual enable option description that should appear in output
            if prefix == "programs.git":
                result["enable_options"][0]["description"] = "Whether to enable Git."
            return result
            
        self.mock_context.get_options_by_prefix.side_effect = side_effect_get_options_by_prefix
        
        result = home_manager_options_by_prefix("programs.git", context=self.mock_context)
        
        # Verify the correct prefix was used
        self.mock_context.get_options_by_prefix.assert_called_with("programs.git")
        
        # Check basic output formatting (key elements should be present)
        self.assertIn("programs.git", result)
        self.assertIn("options", result)
        self.assertIn("enable", result)
        self.assertIn("userName", result)
        
        # Verify option types were included
        self.assertIn("boolean", result)
        self.assertIn("string", result)
        
        # Verify enable option is present (though formatting may vary)
        self.assertIn("Whether to enable Git", result)

    def test_hierarchical_navigation(self):
        """Test navigating through hierarchical paths."""
        # First level
        first_level_mock = {
            "options": [
                {"name": "programs", "count": 50},
                {"name": "services", "count": 30},
            ],
            "found": True,
        }
        self.mock_context.get_options_list.return_value = first_level_mock
        
        # Second level - create more detailed results for navigation tests
        second_level_mock = {
            "prefix": "programs",
            "options": [
                {"name": "programs.git.enable", "description": "Git description"},
                {"name": "programs.firefox.enable", "description": "Firefox description"},
            ],
            "count": 2,
            "types": {"boolean": 2},
            "enable_options": [],
            "found": True,
        }
        
        # Simulate different responses based on prefix
        def mock_get_options_by_prefix(prefix):
            if prefix == "programs":
                return second_level_mock
            elif prefix == "programs.git":
                return self.mock_prefix_results
            return {"error": "Prefix not found", "found": False}
                
        self.mock_context.get_options_by_prefix.side_effect = mock_get_options_by_prefix
        
        # Test first level navigation
        result = home_manager_options_by_prefix("programs", context=self.mock_context)
        
        # Check basic expected elements in result - not specific formatting
        self.assertIn("programs", result)
        self.assertIn("options", result)  # Should mention options
        self.assertTrue("firefox" in result or "Firefox" in result)  # Some mention of Firefox
        self.assertTrue("git" in result or "Git" in result)  # Some mention of Git


class TestHomeManagerSpecialQueries(unittest.TestCase):
    """Test special query handling in Home Manager search."""

    def setUp(self):
        """Set up a mock context."""
        self.mock_context = MagicMock()
        
        # Set up different response scenarios
        self.standard_results = {
            "options": [
                {"name": "programs.git.enable", "description": "Git description"},
            ],
            "count": 1,
            "found": True,
        }
        
        self.empty_results = {
            "options": [],
            "count": 0,
            "found": False,
        }
        
        self.error_results = {
            "options": [],
            "count": 0,
            "error": "Something went wrong",
            "found": False,
        }

    def test_search_with_colon_query(self):
        """Test search with a query containing a colon (special query)."""
        # Set up mock to return special results for colon queries
        def mock_search(query, limit):
            if ":" in query:
                return self.standard_results
            return self.empty_results
            
        self.mock_context.search_options.side_effect = mock_search
        
        # Test with colon query
        result = home_manager_search("type:boolean", context=self.mock_context)
        
        # Verify wildcards were NOT added to special queries
        self.mock_context.search_options.assert_called_with("type:boolean", 20)
        # The output transformation happens in the function being tested
        # so we can't guarantee specific content, but certain elements should be present
        self.assertIn("found", result.lower())  # Should mention "found"
        self.assertIn("1", result)  # Should mention the count

    def test_search_with_error(self):
        """Test search handling when an error occurs."""
        self.mock_context.search_options.return_value = self.error_results
        
        result = home_manager_search("query", context=self.mock_context)
        
        # Check that error message is included
        self.assertIn("Error:", result)
        self.assertIn("Something went wrong", result)
    
    def test_search_no_results(self):
        """Test search when no results are found."""
        self.mock_context.search_options.return_value = self.empty_results
        
        result = home_manager_search("nonexistent", context=self.mock_context)
        
        # Check that no results message is included
        self.assertIn("No Home Manager options found", result)
        self.assertIn("nonexistent", result)

    def test_multi_word_query(self):
        """Test search with multi-word queries."""
        def mock_search(query, limit):
            # The actual implementation adds spaces between words in wildcards
            if "*git* *user*" in query:
                return {
                    "options": [
                        {"name": "programs.git.userName", "description": "Git username"},
                        {"name": "programs.git.userEmail", "description": "Git user email"},
                    ],
                    "count": 2,
                    "found": True,
                }
            return self.empty_results
            
        self.mock_context.search_options.side_effect = mock_search
        
        # Test with multi-word query
        result = home_manager_search("git user", context=self.mock_context)
        
        # Verify wildcards were added correctly - with space preserved
        self.mock_context.search_options.assert_called_with("*git* *user*", 20)
        # Check that results contain both words
        self.assertIn("userName", result)
        self.assertIn("userEmail", result)


if __name__ == "__main__":
    unittest.main()