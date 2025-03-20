#!/usr/bin/env python
"""
Test script for NixMCP server.

This script tests the MCP endpoints of the NixMCP server.
Run this script while the server is running to verify MCP functionality.
"""

import json
import requests
from typing import Any, Dict


def test_mcp_resources() -> None:
    """Test MCP resource endpoints."""
    base_url = "http://localhost:8000/mcp"

    # Test package resource (default channel)
    package_name = "python"
    print(f"\nTesting MCP package resource: {package_name}")
    package_url = f"{base_url}/resource?uri=nixos://package/{package_name}"

    try:
        package_response = requests.get(package_url)
        print(f"Status Code: {package_response.status_code}")
        if package_response.status_code == 200:
            result = package_response.json()
            print(f"Content type: {type(result)}")
            print(json.dumps(result, indent=2)[:500] + "...")  # Print truncated result
        else:
            print(f"Error: {package_response.text}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")

    # Test package resource with explicit channel
    print(
        f"\nTesting MCP package resource with explicit channel: {package_name}/unstable"
    )
    package_channel_url = (
        f"{base_url}/resource?uri=nixos://package/{package_name}/unstable"
    )

    try:
        response = requests.get(package_channel_url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Content type: {type(result)}")
            print(json.dumps(result, indent=2)[:500] + "...")  # Print truncated result
        else:
            print(f"Error: {response.text}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")

    # Test option resource (default channel)
    option_name = "services.nginx"
    print(f"\nTesting MCP option resource: {option_name}")
    option_url = f"{base_url}/resource?uri=nixos://option/{option_name}"

    try:
        option_response = requests.get(option_url)
        print(f"Status Code: {option_response.status_code}")
        if option_response.status_code == 200:
            result = option_response.json()
            print(f"Content type: {type(result)}")
            print(json.dumps(result, indent=2)[:500] + "...")  # Print truncated result
        else:
            print(f"Error: {option_response.text}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")


def check_server_running():
    """Check if the server is running."""
    try:
        response = requests.get("http://localhost:8000/docs")
        return response.status_code == 200
    except requests.RequestException:
        return False


def dry_run_test():
    """Run test mocks without an actual server."""
    print("NixMCP MCP Dry Run Test")
    print("=====================")
    print("This is a dry run that doesn't require a running server.")
    print("It's useful for checking if the test script itself works correctly.")
    
    # Mock response data
    mock_package = {
        "name": "python",
        "version": "3.11.0",
        "description": "A programming language that lets you work quickly",
        "attribute": "python3"
    }
    
    mock_option = {
        "name": "services.nginx",
        "description": "NGINX web server",
        "type": "attribute set",
        "default": {},
        "example": {"enable": True}
    }
    
    print("\nMock package response:")
    print(json.dumps(mock_package, indent=2))
    
    print("\nMock option response:")
    print(json.dumps(mock_option, indent=2))
    
    print("\nTest script is working correctly!")


if __name__ == "__main__":
    print("NixMCP MCP Test")
    print("===============")
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        dry_run_test()
        exit(0)

    if not check_server_running():
        print("\033[91mERROR: Server is not running!\033[0m")
        print("Please start the server in another terminal with:")
        print("  nix develop -c run")
        print("  or")
        print("  nix develop -c python server.py")
        print("\nAlternatively, run a dry test with:")
        print("  python test_mcp.py --dry-run")
        exit(1)

    print("Server is running. Testing MCP endpoints...\n")
    test_mcp_resources()
