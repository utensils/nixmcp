#!/usr/bin/env python
"""
NixMCP Utility - A combined tool for testing, diagnostics, and MCP client functionality.

This utility combines the functionality of the previous mcp_test_client.py and 
mcp_diagnose.py tools into a single, comprehensive tool for working with NixMCP.

Usage examples:
  # Check server status and available MCP resources
  python nixmcp_util.py status
  
  # Test a specific MCP resource
  python nixmcp_util.py resource nixos://package/python
  
  # Run diagnostics on all endpoints
  python nixmcp_util.py diagnose
  
  # Check only Elasticsearch connectivity
  python nixmcp_util.py elasticsearch
  
  # Analyze server logs
  python nixmcp_util.py logs
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import quote
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Standard MCP routes to test
MCP_ROUTES = [
    # Standard MCP endpoints
    "/mcp/resource?uri=nixos://status",
    "/mcp/resource?uri=nixos://package/python",
    "/mcp/resource?uri=nixos://package/python/unstable",
    "/mcp/resource?uri=nixos://search/packages/python",
    "/mcp/resource?uri=nixos://search/packages/python/unstable",
    "/mcp/resource?uri=nixos://search/options/postgresql",
    "/mcp/resource?uri=nixos://option/services.nginx",
    
    # Debug and utility endpoints
    "/debug/mcp-registered",
    
    # Server info endpoints
    "/health",
]

class NixMCPUtil:
    """NixMCP utility for testing, diagnostics, and MCP client functionality."""

    def __init__(self, base_url: str = "http://localhost:9421"):
        """Initialize with the server base URL."""
        self.base_url = base_url
        self.mcp_url = f"{base_url}/mcp"
        
        # Configure styling for output
        self.styles = {
            "header": "\033[1;36m",  # Bold cyan
            "success": "\033[1;32m",  # Bold green
            "error": "\033[1;31m",    # Bold red
            "warning": "\033[1;33m",  # Bold yellow
            "info": "\033[1;34m",     # Bold blue
            "reset": "\033[0m",       # Reset
        }

    def styled_print(self, text: str, style: str = "info", add_newline: bool = False):
        """Print text with the specified style."""
        if style in self.styles:
            prefix = self.styles[style]
            suffix = self.styles["reset"]
            print(f"{prefix}{text}{suffix}")
        else:
            print(text)
            
        if add_newline:
            print()

    def print_header(self, text: str):
        """Print a section header."""
        print()
        self.styled_print("=" * 60, "header")
        self.styled_print(f" {text}", "header")
        self.styled_print("=" * 60, "header")
        print()

    def print_subheader(self, text: str):
        """Print a subsection header."""
        print()
        self.styled_print(f"--- {text} ---", "info")
        print()

    def check_server_status(self) -> Dict[str, Any]:
        """Check the health and debug endpoints to get server status."""
        self.print_header("NixMCP Server Status")
        
        # Check health endpoint
        health_data = self.test_endpoint("/health")
        
        # Check debug endpoint for registered resources
        debug_data = self.test_endpoint("/debug/mcp-registered")
        
        return {
            "health": health_data,
            "debug": debug_data
        }

    def test_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Test a specific endpoint and return its data."""
        url = f"{self.base_url}{endpoint}"
        self.styled_print(f"Testing: {url}")
        
        try:
            response = requests.get(url)
            status = response.status_code
            
            if status == 200:
                self.styled_print(f"Status: {status} ✅", "success")
                data = response.json()
                print(json.dumps(data, indent=2))
                return data
            else:
                self.styled_print(f"Status: {status} ❌", "error")
                print(f"Response: {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            self.styled_print(f"Error: {e}", "error")
            return {"error": str(e)}

    def test_mcp_resource(self, uri: str) -> Dict[str, Any]:
        """Test a MCP resource using standard MCP protocol."""
        self.print_header(f"Testing MCP Resource: {uri}")
        
        encoded_uri = quote(uri)
        endpoint = f"/mcp/resource?uri={encoded_uri}"
        
        return self.test_endpoint(endpoint)

    def get_registered_resources(self) -> List[str]:
        """Get a list of registered MCP resources."""
        try:
            debug_data = self.test_endpoint("/debug/mcp-registered")
            resources = debug_data.get("registered_resources", [])
            
            self.print_subheader("Registered MCP Resources")
            for resource in resources:
                print(f"- {resource}")
                
            return resources
            
        except Exception as e:
            self.styled_print(f"Error getting registered resources: {e}", "error")
            return []

    def run_diagnostics(self) -> Dict[str, Any]:
        """Run diagnostics on all available endpoints."""
        self.print_header("NixMCP Server Diagnostics")
        
        results = []
        
        # Test all standard endpoints
        for route in MCP_ROUTES:
            url = f"{self.base_url}{route}"
            self.styled_print(f"Testing: {url}")
            
            try:
                response = requests.get(url)
                status = response.status_code
                
                if status == 200:
                    result = "✅ OK"
                    self.styled_print(f"  Result: {result}", "success")
                    data = response.json()
                    
                    # For successful responses, show a brief summary
                    if isinstance(data, dict):
                        if "error" in data:
                            self.styled_print(f"  Response: {data['error']}", "warning")
                        elif "results" in data and isinstance(data["results"], list):
                            self.styled_print(f"  Found: {len(data['results'])} results", "info")
                        else:
                            keys = list(data.keys())[:3]
                            self.styled_print(f"  Keys: {', '.join(keys)}...", "info")
                else:
                    result = f"❌ ERROR ({status})"
                    self.styled_print(f"  Result: {result}", "error")
                    
                results.append({
                    "url": url,
                    "status": status,
                    "result": result
                })
                
            except Exception as e:
                self.styled_print(f"  Error: {e}", "error")
                results.append({
                    "url": url,
                    "status": None,
                    "result": f"❌ EXCEPTION: {str(e)}"
                })
                
            print()
        
        # Print summary
        self.print_subheader("Endpoint Status Summary")
        
        working = [r for r in results if r["status"] == 200]
        failing = [r for r in results if r["status"] != 200]
        
        self.styled_print(f"Working endpoints: {len(working)}/{len(results)}", "success")
        self.styled_print(f"Failing endpoints: {len(failing)}/{len(results)}", 
                         "success" if len(failing) == 0 else "error")
        
        if failing:
            self.print_subheader("Failing Endpoints")
            for r in failing:
                self.styled_print(f"- {r['url']}: {r['result']}", "error")
        else:
            self.styled_print("\n🎉 All MCP endpoints are working correctly!", "success")
            
        return {
            "working": len(working),
            "failing": len(failing),
            "total": len(results),
            "results": results
        }

    def check_elasticsearch(self) -> bool:
        """Check Elasticsearch connection and do a test search."""
        self.print_header("Elasticsearch Connectivity Check")
        
        es_url = os.getenv("ELASTICSEARCH_URL", "https://search.nixos.org/backend/latest-42-nixos-unstable/_search")
        es_user = os.getenv("ELASTICSEARCH_USER")
        es_password = os.getenv("ELASTICSEARCH_PASSWORD")
        
        self.styled_print(f"Elasticsearch URL: {es_url}")
        self.styled_print(f"Elasticsearch credentials configured: {'Yes' if es_user and es_password else 'No'}")
        
        if not es_user or not es_password:
            self.styled_print("\n❌ ERROR: Elasticsearch credentials not set in .env file", "error")
            self.styled_print("Create a .env file with ELASTICSEARCH_USER and ELASTICSEARCH_PASSWORD", "info")
            return False
        
        # Make a direct test request to Elasticsearch
        self.print_subheader("Testing Direct Elasticsearch Connection")
        
        try:
            # Basic search query for packages
            search_body = {
                "size": 2,
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"package_pname": "python"}},
                        ],
                        "filter": [
                            {"term": {"type": "package"}}
                        ]
                    }
                }
            }
            
            response = requests.post(
                es_url,
                auth=(es_user, es_password),
                json=search_body,
                headers={"Content-Type": "application/json"},
                verify=False  # Disabling verification for testing
            )
            
            if response.status_code == 200:
                data = response.json()
                total_hits = data.get("hits", {}).get("total", {}).get("value", 0)
                self.styled_print(f"✅ SUCCESS: Elasticsearch connection successful", "success")
                self.styled_print(f"Found {total_hits} hits for 'python' query", "info")
                
                # Show first result as sample
                if total_hits > 0:
                    first_hit = data.get("hits", {}).get("hits", [])[0]
                    source = first_hit.get("_source", {})
                    self.print_subheader("Sample Result")
                    self.styled_print(f"  Name: {source.get('package_pname')}")
                    self.styled_print(f"  Version: {source.get('package_version')}")
                    self.styled_print(f"  Attribute: {source.get('package_attr_name')}")
                
                return True
            else:
                self.styled_print(f"❌ ERROR: Elasticsearch returned status code {response.status_code}", "error")
                self.styled_print(f"Response: {response.text}", "error")
                return False
                
        except Exception as e:
            self.styled_print(f"❌ ERROR: Failed to connect to Elasticsearch: {e}", "error")
            return False

    def analyze_logs(self, log_file: str = "nixmcp-server.log") -> Dict[str, Any]:
        """Analyze the server log file for MCP issues."""
        self.print_header(f"Log File Analysis: {log_file}")
        
        if not os.path.exists(log_file):
            self.styled_print(f"Log file not found: {log_file}", "error")
            return {"error": "Log file not found"}
        
        # Patterns to look for
        patterns = {
            "error": ["error", "exception", "failed", "failure", "cannot"],
            "warning": ["warning", "warn"],
            "mcp": ["mcp", "resource", "mount", "fastmcp"],
            "elasticsearch": ["elasticsearch", "es_client", "search"]
        }
        
        # Counters
        counts = {"error": 0, "warning": 0, "mcp": 0, "elasticsearch": 0}
        last_errors = []
        last_warnings = []
        
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line_lower = line.lower()
                    
                    # Check for patterns
                    for category, terms in patterns.items():
                        if any(term in line_lower for term in terms):
                            counts[category] += 1
                            
                    # Store recent errors and warnings
                    if any(term in line_lower for term in patterns["error"]):
                        last_errors.append(line.strip())
                        if len(last_errors) > 5:  # Keep only the most recent 5
                            last_errors.pop(0)
                            
                    if any(term in line_lower for term in patterns["warning"]):
                        last_warnings.append(line.strip())
                        if len(last_warnings) > 5:  # Keep only the most recent 5
                            last_warnings.pop(0)
            
            # Print summary
            self.print_subheader("Log Analysis Summary")
            
            for category, count in counts.items():
                style = "error" if category == "error" and count > 0 else "warning" if category == "warning" and count > 0 else "info"
                self.styled_print(f"{category.capitalize()}: {count} occurrences", style)
                
            if last_errors:
                self.print_subheader("Recent Errors")
                for err in last_errors:
                    self.styled_print(f"  {err}", "error")
                    
            if last_warnings:
                self.print_subheader("Recent Warnings")
                for warn in last_warnings:
                    self.styled_print(f"  {warn}", "warning")
            
            return {
                "counts": counts,
                "last_errors": last_errors,
                "last_warnings": last_warnings
            }
                    
        except Exception as e:
            self.styled_print(f"Error analyzing log file: {e}", "error")
            return {"error": str(e)}

    def run_comprehensive_test(self):
        """Run a comprehensive test of the server with all diagnostics."""
        self.print_header("NixMCP Comprehensive Test")
        
        # Check server status
        self.check_server_status()
        
        # Run diagnostics
        diag_results = self.run_diagnostics()
        
        # Check Elasticsearch
        es_success = self.check_elasticsearch()
        
        # Overall status
        self.print_header("Overall Test Results")
        
        failing_count = diag_results['failing']
        self.styled_print(f"MCP Endpoints: {'✅ OK' if failing_count == 0 else f'❌ {failing_count} failing'}", 
                         "success" if failing_count == 0 else "error")
        
        self.styled_print(f"Elasticsearch: {'✅ OK' if es_success else '❌ Not working'}", 
                         "success" if es_success else "error")
        
        if diag_results['failing'] == 0 and es_success:
            self.styled_print("\n✨ NixMCP Server is running correctly with all core functionality!", "success")
            self.styled_print("Ready for integration with any MCP-compatible client.", "success")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="NixMCP utility for testing, diagnostics, and MCP client functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check server status and available MCP resources
  python nixmcp_util.py status
  
  # Test a specific MCP resource
  python nixmcp_util.py resource nixos://package/python
  
  # Run diagnostics on all endpoints
  python nixmcp_util.py diagnose
  
  # Check only Elasticsearch connectivity
  python nixmcp_util.py elasticsearch
  
  # Analyze server logs
  python nixmcp_util.py logs
"""
    )
    
    # Base URL argument
    parser.add_argument("--url", default="http://localhost:9421", 
                        help="Base URL of the NixMCP server (default: http://localhost:9421)")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check server status and available MCP resources")
    
    # Resource command
    resource_parser = subparsers.add_parser("resource", help="Test a specific MCP resource")
    resource_parser.add_argument("uri", help="MCP resource URI (e.g., nixos://package/python)")
    
    # Diagnose command
    diagnose_parser = subparsers.add_parser("diagnose", help="Run diagnostics on all endpoints")
    
    # Elasticsearch command
    es_parser = subparsers.add_parser("elasticsearch", help="Check Elasticsearch connectivity")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Analyze server logs")
    logs_parser.add_argument("--logfile", default="nixmcp-server.log", 
                            help="Path to the log file (default: nixmcp-server.log)")
    
    # Comprehensive test command
    test_parser = subparsers.add_parser("test", help="Run a comprehensive test of the server")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create the utility
    util = NixMCPUtil(args.url)
    
    # Execute the requested command
    if args.command == "status":
        util.check_server_status()
        util.get_registered_resources()
    elif args.command == "resource":
        util.test_mcp_resource(args.uri)
    elif args.command == "diagnose":
        util.run_diagnostics()
    elif args.command == "elasticsearch":
        util.check_elasticsearch()
    elif args.command == "logs":
        util.analyze_logs(args.logfile)
    elif args.command == "test":
        util.run_comprehensive_test()
    else:
        # If no command provided, show help
        parser.print_help()
        print("\nPlease specify a command to execute.")


if __name__ == "__main__":
    main()