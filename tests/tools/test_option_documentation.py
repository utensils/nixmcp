"""
Tests for NixOS and Home Manager option documentation integration.
"""

import unittest
import pytest
from unittest.mock import MagicMock

# Mark as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.tools.nixos_tools import nixos_info
from mcp_nixos.tools.home_manager_tools import home_manager_info


class TestNixOSOptionDocumentation(unittest.TestCase):
    """Test the NixOS option documentation integration."""

    def test_nixos_option_with_docs(self):
        """Test that NixOS options display documentation links and version information."""
        # Create a simpler direct test that doesn't depend on mocking get_context_or_fallback
        mock_option_data = {
            "name": "services.nginx.enable",
            "description": "Whether to enable nginx web server.",
            "type": "boolean",
            "default": "false",
            "example": "true",
            "declarations": ["/nix/store/..."],
            "readOnly": False,
            "manual_url": "https://nixos.org/manual/nixos/stable/options.html#opt-services.nginx.enable",
            "introduced_version": "14.12",
            "deprecated_version": "",
            "found": True,
        }

        # Create a mock context with the required methods
        mock_context = MagicMock()
        # Make sure it returns our option data when get_option is called
        mock_context.get_option.return_value = mock_option_data
        # Add an empty get_package method to avoid fallback
        mock_context.get_package.return_value = {}

        result = nixos_info("services.nginx.enable", type="option", context=mock_context)

        # Check for manual link and version info in the output
        self.assertIn(
            "**Manual:** [https://nixos.org/manual/nixos/stable/options.html#opt-services.nginx.enable]", result
        )
        self.assertIn("**Introduced in:** NixOS 14.12", result)
        self.assertNotIn("**Deprecated in:**", result)

        # Check for contextual example
        self.assertIn("**Example in context:**", result)
        self.assertIn("services = {", result)
        self.assertIn("nginx = {", result)
        self.assertIn("enable = true;", result)


class TestHomeManagerOptionDocumentation(unittest.TestCase):
    """Test the Home Manager option documentation integration."""

    def test_home_manager_option_with_docs(self):
        """Test that Home Manager options display documentation links and version information."""
        # Create a simpler direct test
        mock_option_data = {
            "name": "programs.git.enable",
            "description": "Whether to enable Git.",
            "type": "boolean",
            "default": "false",
            "example": "true",
            "category": "Programs",
            "source": "options",
            "introduced_version": "21.11",
            "deprecated_version": "",
            "manual_url": "https://nix-community.github.io/home-manager/options.html#opt-programs.git.enable",
            "found": True,
        }

        # Create a mock context with the required methods
        mock_context = MagicMock()
        # Make sure it returns our option data when get_option is called
        mock_context.get_option.return_value = mock_option_data

        result = home_manager_info("programs.git.enable", context=mock_context)

        # Check for manual link and version info in the output
        manual_url = "https://nix-community.github.io/home-manager/options.html#opt-programs.git.enable"
        self.assertIn(f"**Documentation:** [Home Manager Manual]({manual_url})", result)
        self.assertIn("**Introduced in version:** 21.11", result)
        self.assertNotIn("**Deprecated in version:**", result)

        # Check for contextual example
        self.assertIn("**Example in context:**", result)
        self.assertIn("programs = {", result)
        self.assertIn("git = {", result)
        self.assertIn("enable = true;", result)
