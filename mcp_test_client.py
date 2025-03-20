#!/usr/bin/env python
"""
Simple MCP client to test NixMCP server resources.
"""

import argparse
import asyncio
import json
import requests
import sys
from typing import Dict, Any, List
from urllib.parse import quote


class MCPTestClient:
    """Simple client to test MCP resource endpoints."""

    def __init__(self, base_url: str = "http://localhost:9421"):
        """Initialize with the server base URL."""
        self.base_url = base_url
        self.mcp_url = f"{base_url}/mcp"
        self.direct_mcp_url = f"{base_url}/direct-mcp"
        self.api_url = f"{base_url}"

    def test_health(self) -> Dict[str, Any]:
        """Test the health endpoint."""
        print("\n=== Testing Health Endpoint ===")
        response = requests.get(f"{self.base_url}/health")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))
        return data

    def test_status(self) -> Dict[str, Any]:
        """Test the status endpoint."""
        print("\n=== Testing Status Endpoint ===")
        response = requests.get(f"{self.base_url}/status")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))
        return data

    def get_mcp_resources(self) -> List[str]:
        """Get list of registered MCP resources."""
        try:
            response = requests.get(f"{self.base_url}/debug/mcp-registered")
            if response.status_code == 200:
                return response.json().get("registered_resources", [])
            return []
        except Exception:
            return []

    def test_mcp_resource(self, uri: str) -> Dict[str, Any]:
        """Test a MCP resource using standard MCP protocol."""
        print(f"\n=== Testing MCP Resource: {uri} ===")
        encoded_uri = quote(uri)
        standard_url = f"{self.mcp_url}/resource?uri={encoded_uri}"
        
        print(f"URL: {standard_url}")
        response = requests.get(standard_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"Error: {response.text}")
            return {"error": response.text}

    def test_direct_mcp_resource(self, uri: str) -> Dict[str, Any]:
        """Test a MCP resource using our direct endpoint."""
        print(f"\n=== Testing Direct MCP Resource: {uri} ===")
        encoded_uri = quote(uri)
        direct_url = f"{self.direct_mcp_url}/resource?uri={encoded_uri}"
        
        print(f"URL: {direct_url}")
        response = requests.get(direct_url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"Error: {response.text}")
            return {"error": response.text}

    def test_direct_api(self, resource_type: str, name: str) -> Dict[str, Any]:
        """Test a direct API endpoint."""
        print(f"\n=== Testing Direct API: {resource_type}/{name} ===")
        
        if resource_type == "package":
            url = f"{self.api_url}/api/package/{name}"
        elif resource_type == "search":
            url = f"{self.api_url}/api/search/packages/{name}"
        elif resource_type == "search-options":
            url = f"{self.api_url}/api/search/options/{name}"
        elif resource_type == "option":
            url = f"{self.api_url}/api/option/{name}"
        else:
            return {"error": f"Unknown resource type: {resource_type}"}
        
        print(f"URL: {url}")
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"Error: {response.text}")
            return {"error": response.text}

    def test_all_endpoints(self):
        """Test all endpoints with sample data."""
        self.test_health()
        self.test_status()
        
        # Get registered resources
        resources = self.get_mcp_resources()
        print(f"\nRegistered MCP resources: {resources}")
        
        # Test MCP package resource
        self.test_mcp_resource("nixos://package/python")
        
        # Test direct MCP resource endpoint
        self.test_direct_mcp_resource("nixos://package/python")
        
        # Test MCP search resource
        self.test_mcp_resource("nixos://search/packages/python")
        
        # Test direct MCP search resource
        self.test_direct_mcp_resource("nixos://search/packages/python")
        
        # Test direct API endpoints
        self.test_direct_api("package", "python")
        self.test_direct_api("search", "python")
        self.test_direct_api("option", "services.nginx")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Test MCP resources.")
    parser.add_argument(
        "--url", 
        default="http://localhost:9421", 
        help="Base URL of the NixMCP server"
    )
    parser.add_argument(
        "--resource", 
        help="Specific MCP resource to test (e.g., nixos://package/python)"
    )
    parser.add_argument(
        "--api", 
        help="Test direct API endpoint (format: resource_type/name, e.g., package/python)"
    )
    parser.add_argument(
        "--all", 
        action="store_true", 
        help="Test all endpoints with sample data"
    )
    parser.add_argument(
        "--direct-only", 
        action="store_true", 
        help="Only test direct MCP endpoint"
    )
    parser.add_argument(
        "--mcp-only", 
        action="store_true", 
        help="Only test standard MCP endpoint"
    )
    
    args = parser.parse_args()
    client = MCPTestClient(args.url)
    
    if args.all:
        client.test_all_endpoints()
    elif args.resource:
        if args.mcp_only:
            client.test_mcp_resource(args.resource)
        elif args.direct_only:
            client.test_direct_mcp_resource(args.resource)
        else:
            # Default to test both
            client.test_mcp_resource(args.resource)
            client.test_direct_mcp_resource(args.resource)
    elif args.api:
        if "/" in args.api:
            resource_type, name = args.api.split("/", 1)
            client.test_direct_api(resource_type, name)
        else:
            print("Error: API format should be resource_type/name (e.g., package/python)")
    else:
        client.test_health()
        client.test_status()


if __name__ == "__main__":
    main()