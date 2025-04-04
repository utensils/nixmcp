"""
Tests for the Home Manager tools module.
"""

import unittest
from unittest.mock import patch, MagicMock, call
import logging
import importlib

# Import the module to test
from mcp_nixos.tools.home_manager_tools import (
    home_manager_search,
    home_manager_info,
    home_manager_stats,
    home_manager_list_options,
    home_manager_options_by_prefix,
    check_request_ready,
    check_home_manager_ready,
    register_home_manager_tools,
)


class TestHomeManagerTools(unittest.TestCase):
    """Test the Home Manager tools functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock context
        self.mock_context = MagicMock()
        self.mock_context.search_options.return_value = {
            "options": [
                {
                    "name": "programs.git",
                    "description": "Git configuration",
                    "type": "attribute set",
                }
            ]
        }
        self.mock_context.get_option_info.return_value = {
            "name": "programs.git",
            "description": "Git configuration",
            "type": "attribute set",
            "default": {},
            "example": {"enable": True},
            "declared_by": ["home-manager/git.nix"],
        }
        self.mock_context.get_stats.return_value = {
            "total_options": 1000,
            "categories": {"programs": 200, "services": 150},
        }
        self.mock_context.get_options_by_prefix.return_value = {
            "options": [
                {
                    "name": "programs.git.enable",
                    "description": "Whether to enable Git",
                    "type": "boolean",
                }
            ]
        }

    def test_home_manager_search_with_context(self):
        """Test home_manager_search with provided context."""
        # Setup the mock context to return search results
        self.mock_context.search_options.return_value = {
            "options": [
                {
                    "name": "programs.git",
                    "description": "Git configuration",
                    "type": "attribute set"
                }
            ]
        }
        
        result = home_manager_search("git", 10, self.mock_context)
        
        # Verify the context's search_options method was called correctly
        self.mock_context.search_options.assert_called_once_with("*git*", 10)
        self.assertIn("programs.git", result)
        self.assertIn("Git configuration", result)

    @patch("importlib.import_module")
    def test_home_manager_search_with_dynamic_context(self, mock_importlib):
        """Test home_manager_search with dynamically imported context."""
        # Setup the mock server module
        mock_server = MagicMock()
        mock_server.get_home_manager_context.return_value = self.mock_context
        mock_importlib.return_value = mock_server
        
        # Setup the mock context to return search results
        self.mock_context.search_options.return_value = {
            "options": [
                {
                    "name": "programs.git",
                    "description": "Git configuration",
                    "type": "attribute set"
                }
            ]
        }
        
        # Call the function without providing a context
        result = home_manager_search("git", 10)
        
        # Verify importlib.import_module was called correctly
        mock_importlib.assert_called_with("mcp_nixos.server")
        self.assertIn("programs.git", result)

    def test_home_manager_search_with_string_context(self):
        """Test home_manager_search with string context (from MCP)."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = self.mock_context
            mock_importlib.return_value = mock_server
            
            # Setup the mock context to return search results
            self.mock_context.search_options.return_value = {
                "options": [
                    {
                        "name": "programs.git",
                        "description": "Git configuration",
                        "type": "attribute set"
                    }
                ]
            }

            # Call the function with a string context
            result = home_manager_search("git", 10, "mcp_context_string")

            # Verify importlib.import_module was called correctly
            mock_importlib.assert_called_with("mcp_nixos.server")
            # Verify the context's search_options method was called with wildcard query
            self.mock_context.search_options.assert_called_once_with("*git*", 10)
            self.assertIn("programs.git", result)

    def test_home_manager_search_with_none_context(self):
        """Test home_manager_search with None context."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to return None
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = None
            mock_importlib.return_value = mock_server

            # Call the function without providing a context
            result = home_manager_search("git", 10)

            # Verify error message is returned
            self.assertEqual(result, "Error: Home Manager context not available")

    def test_home_manager_search_with_string_context_error(self):
        """Test home_manager_search with string context when an error occurs."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to raise an exception
            mock_server = MagicMock()
            mock_server.get_home_manager_context.side_effect = Exception("Test error")
            mock_importlib.return_value = mock_server

            # Call the function with a string context
            result = home_manager_search("git", 10, "mcp_context_string")

            # Verify error message is returned
            self.assertIn("Error: Could not search for '*git*': Test error", result)

    def test_home_manager_search_no_results(self):
        """Test home_manager_search when no results are found."""
        # Modify the mock to return no options
        self.mock_context.search_options.return_value = {"options": []}
        
        # Call the function
        result = home_manager_search("nonexistent", 10, self.mock_context)
        
        # Verify the context's search_options method was called with wildcard query
        self.mock_context.search_options.assert_called_once_with("*nonexistent*", 10)
        # Verify the result contains the expected message
        self.assertIn("No Home Manager options found for '*nonexistent*'", result)

    def test_home_manager_search_with_error(self):
        """Test home_manager_search when an error is returned."""
        # Modify the mock to return an error
        self.mock_context.search_options.return_value = {"error": "Test error", "options": []}
        
        # Call the function
        result = home_manager_search("git", 10, self.mock_context)
        
        # Verify the result contains the error message
        self.assertEqual(result, "Error: Test error")

    def test_home_manager_info_with_context(self):
        """Test home_manager_info with provided context."""
        # Set up the mock to return a proper option object
        self.mock_context.get_option.return_value = {
            "found": True,
            "name": "programs.git",
            "description": "Git configuration",
            "type": "attribute set"
        }

        result = home_manager_info("programs.git", self.mock_context)
        
        # Verify the context's get_option method was called correctly
        self.mock_context.get_option.assert_called_once_with("programs.git")
        self.assertIn("programs.git", result)
        self.assertIn("Git configuration", result)

    @patch("importlib.import_module")
    def test_home_manager_info_with_dynamic_context(self, mock_importlib):
        """Test home_manager_info with dynamically imported context."""
        # Setup the mock server module
        mock_server = MagicMock()
        mock_server.get_home_manager_context.return_value = self.mock_context
        mock_importlib.return_value = mock_server
        
        # Call the function without providing a context
        result = home_manager_info("programs.git")
        
        # Verify importlib.import_module was called correctly
        mock_importlib.assert_called_with("mcp_nixos.server")
        self.assertIn("programs.git", result)

    def test_home_manager_info_with_string_context(self):
        """Test home_manager_info with string context (from MCP)."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = self.mock_context
            mock_importlib.return_value = mock_server

            # Call the function with a string context
            result = home_manager_info("programs.git", "mcp_context_string")

            # Verify importlib.import_module was called correctly
            mock_importlib.assert_called_with("mcp_nixos.server")
            # Verify the context's search_options method was called with wildcard query
            self.mock_context.search_options.assert_called_once_with("*git*", 10)
            self.assertIn("programs.git", result)

    def test_home_manager_info_with_none_context(self):
        """Test home_manager_info with None context."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to return None
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = None
            mock_importlib.return_value = mock_server

            # Call the function without providing a context
            result = home_manager_info("programs.git")

            # Verify error message is returned
            self.assertEqual(result, "Error: Home Manager context not available for option 'programs.git'")

    def test_home_manager_info_with_string_context_error(self):
        """Test home_manager_info with string context when an error occurs."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to raise an exception
            mock_server = MagicMock()
            mock_server.get_home_manager_context.side_effect = Exception("Test error")
            mock_importlib.return_value = mock_server

            # Call the function with a string context
            result = home_manager_info("programs.git", "mcp_context_string")

            # Verify error message is returned
            self.assertIn("Error: Could not obtain information for 'programs.git': Test error", result)

    def test_home_manager_info_not_found(self):
        """Test home_manager_info when option is not found."""
        # Modify the mock to return not found
        self.mock_context.get_option.return_value = {"found": False}
        
        # Call the function
        result = home_manager_info("nonexistent", self.mock_context)
        
        # Verify the result contains the expected message
        self.assertIn("# Option 'nonexistent' not found", result)

    def test_home_manager_stats_with_context(self):
        """Test home_manager_stats with provided context."""
        # Setup the mock context to return stats
        self.mock_context.get_stats.return_value = {
            "found": True,
            "total": 1000,
            "categories": {
                "programs": 200,
                "services": 150,
                "users": 50,
                "other": 600
            }
        }
        
        result = home_manager_stats(self.mock_context)
        
        # Verify the context's get_stats method was called correctly
        self.mock_context.get_stats.assert_called_once()
        self.assertIn("1000", result)  # Total options
        self.assertIn("programs", result)
        self.assertIn("200", result)  # Programs count

    @patch("importlib.import_module")
    def test_home_manager_stats_with_dynamic_context(self, mock_importlib):
        """Test home_manager_stats with dynamically imported context."""
        # Setup the mock server module
        mock_server = MagicMock()
        mock_server.get_home_manager_context.return_value = self.mock_context
        mock_importlib.return_value = mock_server
        
        # Setup the mock context to return stats
        self.mock_context.get_stats.return_value = {
            "found": True,
            "total": 1000,
            "categories": {
                "programs": 200,
                "services": 150,
                "users": 50,
                "other": 600
            }
        }
        
        # Call the function without providing a context
        result = home_manager_stats()
        
        # Verify importlib.import_module was called correctly
        mock_importlib.assert_called_with("mcp_nixos.server")
        self.assertIn("1000", result)  # Total options

    def test_home_manager_stats_with_string_context(self):
        """Test home_manager_stats with string context (from MCP)."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = self.mock_context
            mock_importlib.return_value = mock_server
            
            # Setup the mock context to return stats
            self.mock_context.get_stats.return_value = {
                "found": True,
                "total": 1000,
                "categories": {
                    "programs": 200,
                    "services": 150,
                    "users": 50,
                    "other": 600
                }
            }

            # Call the function with a string context
            result = home_manager_stats("mcp_context_string")

            # Verify importlib.import_module was called correctly
            mock_importlib.assert_called_with("mcp_nixos.server")
            self.assertIn("1000", result)  # Total options

    def test_home_manager_stats_with_none_context(self):
        """Test home_manager_stats with None context."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to return None
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = None
            mock_importlib.return_value = mock_server

            # Call the function without providing a context
            result = home_manager_stats()

            # Verify error message is returned
            self.assertEqual(result, "Error: Home Manager context not available")

    def test_home_manager_stats_with_string_context_error(self):
        """Test home_manager_stats with string context when an error occurs."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to raise an exception
            mock_server = MagicMock()
            mock_server.get_home_manager_context.side_effect = Exception("Test error")
            mock_importlib.return_value = mock_server

            # Call the function with a string context
            result = home_manager_stats("mcp_context_string")

            # Verify error message is returned
            self.assertIn("Error: Could not obtain Home Manager statistics", result)

    def test_home_manager_list_options_with_context(self):
        """Test home_manager_list_options with provided context."""
        # Set up the mock to return a proper options list
        self.mock_context.get_options_list.return_value = {
            "found": True,
            "options": {
                "programs": {
                    "count": 200,
                    "types": {"boolean": 50, "string": 30},
                    "enable_options": [{"parent": "programs.git"}]
                }
            }
        }

        result = home_manager_list_options(self.mock_context)
        
        # Verify the context's get_options_list method was called correctly
        self.mock_context.get_options_list.assert_called_once()
        self.assertIn("programs", result)
        self.assertIn("200", result)  # Programs count

    @patch("importlib.import_module")
    def test_home_manager_list_options_with_dynamic_context(self, mock_importlib):
        """Test home_manager_list_options with dynamically imported context."""
        # Setup the mock server module
        mock_server = MagicMock()
        mock_server.get_home_manager_context.return_value = self.mock_context
        mock_importlib.return_value = mock_server
        
        # Setup the mock context to return a proper options list
        self.mock_context.get_options_list.return_value = {
            "found": True,
            "options": {
                "programs": {
                    "count": 200,
                    "types": {"boolean": 50, "string": 30},
                    "enable_options": [{"parent": "programs.git"}]
                }
            }
        }
        
        # Call the function without providing a context
        result = home_manager_list_options()
        
        # Verify importlib.import_module was called correctly
        mock_importlib.assert_called_with("mcp_nixos.server")
        self.assertIn("programs", result)

    def test_home_manager_list_options_with_string_context(self):
        """Test home_manager_list_options with string context (from MCP)."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = self.mock_context
            mock_importlib.return_value = mock_server
            
            # Setup the mock context to return a proper options list
            self.mock_context.get_options_list.return_value = {
                "found": True,
                "options": {
                    "programs": {
                        "count": 200,
                        "types": {"boolean": 50, "string": 30},
                        "enable_options": [{"parent": "programs.git"}]
                    }
                }
            }

            # Call the function with a string context
            result = home_manager_list_options("mcp_context_string")

            # Verify importlib.import_module was called correctly
            mock_importlib.assert_called_with("mcp_nixos.server")
            self.assertIn("programs", result)

    def test_home_manager_list_options_with_none_context(self):
        """Test home_manager_list_options with None context."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to return None
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = None
            mock_importlib.return_value = mock_server

            # Call the function without providing a context
            result = home_manager_list_options()

            # Verify error message is returned
            self.assertEqual(result, "Error: Home Manager context not available")

    def test_home_manager_list_options_with_string_context_error(self):
        """Test home_manager_list_options with string context when an error occurs."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to raise an exception
            mock_server = MagicMock()
            mock_server.get_home_manager_context.side_effect = Exception("Test error")
            mock_importlib.return_value = mock_server

            # Call the function with a string context
            result = home_manager_list_options("mcp_context_string")

            # Verify error message is returned
            self.assertIn("Error: Could not list Home Manager options", result)

    def test_home_manager_options_by_prefix_with_context(self):
        """Test home_manager_options_by_prefix with provided context."""
        # Setup the mock context to return a proper options list
        self.mock_context.get_options_by_prefix.return_value = {
            "found": True,
            "options": {
                "programs.git.enable": {
                    "description": "Whether to enable Git",
                    "type": "boolean",
                    "default": "false"
                }
            }
        }
        
        result = home_manager_options_by_prefix("programs.git", self.mock_context)
        
        # Verify the context's get_options_by_prefix method was called correctly
        self.mock_context.get_options_by_prefix.assert_called_once_with("programs.git")
        self.assertIn("programs.git.enable", result)
        self.assertIn("Whether to enable Git", result)

    @patch("importlib.import_module")
    def test_home_manager_options_by_prefix_with_dynamic_context(self, mock_importlib):
        """Test home_manager_options_by_prefix with dynamically imported context."""
        # Setup the mock server module
        mock_server = MagicMock()
        mock_server.get_home_manager_context.return_value = self.mock_context
        mock_importlib.return_value = mock_server
        
        # Setup the mock context to return a proper options list
        self.mock_context.get_options_by_prefix.return_value = {
            "found": True,
            "options": {
                "programs.git.enable": {
                    "description": "Whether to enable Git",
                    "type": "boolean",
                    "default": "false"
                }
            }
        }
        
        # Call the function without providing a context
        result = home_manager_options_by_prefix("programs.git")
        
        # Verify importlib.import_module was called correctly
        mock_importlib.assert_called_with("mcp_nixos.server")
        self.assertIn("programs.git.enable", result)

    def test_home_manager_options_by_prefix_with_string_context(self):
        """Test home_manager_options_by_prefix with string context (from MCP)."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = self.mock_context
            mock_importlib.return_value = mock_server
            
            # Setup the mock context to return a proper options list
            self.mock_context.get_options_by_prefix.return_value = {
                "found": True,
                "options": {
                    "programs.git.enable": {
                        "description": "Whether to enable Git",
                        "type": "boolean",
                        "default": "false"
                    }
                }
            }

            # Call the function with a string context
            result = home_manager_options_by_prefix("programs.git", "mcp_context_string")

            # Verify importlib.import_module was called correctly
            mock_importlib.assert_called_with("mcp_nixos.server")
            self.assertIn("programs.git.enable", result)

    def test_home_manager_options_by_prefix_with_none_context(self):
        """Test home_manager_options_by_prefix with None context."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to return None
            mock_server = MagicMock()
            mock_server.get_home_manager_context.return_value = None
            mock_importlib.return_value = mock_server

            # Call the function without providing a context
            result = home_manager_options_by_prefix("programs.git")

            # Verify error message is returned
            self.assertEqual(result, "Error: Home Manager context not available")

    def test_home_manager_options_by_prefix_with_string_context_error(self):
        """Test home_manager_options_by_prefix with string context when an error occurs."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to raise an exception
            mock_server = MagicMock()
            mock_server.get_home_manager_context.side_effect = Exception("Test error")
            mock_importlib.return_value = mock_server

            # Call the function with a string context
            result = home_manager_options_by_prefix("programs.git", "mcp_context_string")

            # Verify error message is returned
            self.assertIn("Error: Could not get options for prefix 'programs.git'", result)

    def test_home_manager_options_by_prefix_no_results(self):
        """Test home_manager_options_by_prefix when no results are found."""
        # Modify the mock to return no options
        self.mock_context.get_options_by_prefix.return_value = {"options": []}
        
        # Call the function
        result = home_manager_options_by_prefix("nonexistent", self.mock_context)
        
        # Verify the result contains the expected message
        self.assertIn("No options found under prefix 'nonexistent'", result)

    def test_check_request_ready(self):
        """Test check_request_ready function."""
        # Test with string context
        self.assertTrue(check_request_ready("string_context"))
        
        # Test with object context that has request_context attribute
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.get.return_value = True
        self.assertTrue(check_request_ready(mock_ctx))
        
        # Test with object context that returns False for is_ready
        mock_ctx.request_context.lifespan_context.get.return_value = False
        self.assertFalse(check_request_ready(mock_ctx))

    def test_check_home_manager_ready(self):
        """Test check_home_manager_ready function."""
        # Test with string context
        self.assertIsNone(check_home_manager_ready("string_context"))
        
        # Test with object context that has request_context attribute and is ready
        mock_ctx = MagicMock()
        mock_hm_client = MagicMock(is_loaded=True)
        mock_hm_context = MagicMock(hm_client=mock_hm_client)
        mock_ctx.request_context.lifespan_context.get.return_value = mock_hm_context
        self.assertIsNone(check_home_manager_ready(mock_ctx))
        
        # Test with object context that returns None for home_manager_context
        mock_ctx.request_context.lifespan_context.get.return_value = None
        result = check_home_manager_ready(mock_ctx)
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)
        
        # Test with object context that returns not loaded for home_manager_context
        mock_hm_client = MagicMock(is_loaded=False, loading_in_progress=True)
        mock_hm_context = MagicMock(hm_client=mock_hm_client)
        mock_ctx.request_context.lifespan_context.get.return_value = mock_hm_context
        result = check_home_manager_ready(mock_ctx)
        self.assertIsInstance(result, dict)
        self.assertIn("error", result)

    def test_register_home_manager_tools(self):
        """Test register_home_manager_tools function."""
        # Create a mock MCP server
        mock_mcp = MagicMock()
        
        # Call the function
        register_home_manager_tools(mock_mcp)
        
        # Verify that tool was called for each tool function
        self.assertEqual(mock_mcp.tool.call_count, 5)


if __name__ == "__main__":
    unittest.main()
