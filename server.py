#!/usr/bin/env python
"""
NixMCP Server - An API server for NixOS resources.

This implements a FastAPI server that provides endpoints for querying
NixOS packages and options using the Model Context Protocol (MCP).
"""

import json
import subprocess
import time
from typing import Dict, List, Optional, Any, Union

try:
    from fastapi import FastAPI
    import uvicorn
    from mcp.server import FastMCP
except ImportError:
    raise ImportError(
        "Required packages not found. Please install them with: pip install mcp>=1.4.0 fastapi uvicorn"
        "\nOr run 'nix develop' to enter the development environment."
    )


# NixOS API Implementation
class NixosAPI:
    """API client for NixOS packages and options using local Nix installation."""

    def __init__(self):
        """Initialize the NixOS API client."""
        self._check_nix_installation()

    def _check_nix_installation(self) -> None:
        """Verify that Nix is installed and available."""
        try:
            subprocess.run(
                ["nix", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            raise RuntimeError(
                "Nix installation not found. Please install Nix to use this tool."
            )

    def search_packages(
        self, query: str, channel: str = "unstable"
    ) -> List[Dict[str, Any]]:
        """Search for NixOS packages using nix search."""
        cmd = ["nix", "search", f"nixpkgs/{channel}", query, "--json"]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            packages_data = json.loads(result.stdout)
            packages = []

            for pkg_attr, pkg_info in packages_data.items():
                name = pkg_attr.split(".")[-1]
                packages.append(
                    {
                        "attribute": pkg_attr,
                        "name": name,
                        "version": pkg_info.get("version", ""),
                        "description": pkg_info.get("description", ""),
                    }
                )

            return packages
        except subprocess.CalledProcessError:
            return []
        except json.JSONDecodeError:
            return []

    def get_package_metadata(self, attribute: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a specific package by attribute path."""
        cmd = ["nix", "eval", "--json", f"nixpkgs#{attribute}"]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            pkg_data = json.loads(result.stdout)

            name = attribute.split(".")[-1]
            metadata = {
                "attribute": attribute,
                "name": name,
                "version": pkg_data.get("version", ""),
                "description": pkg_data.get("meta", {}).get("description", ""),
                "homepage": pkg_data.get("meta", {}).get("homepage", ""),
                "license": pkg_data.get("meta", {}).get("license", {}),
                "maintainers": pkg_data.get("meta", {}).get("maintainers", []),
            }

            return metadata
        except subprocess.CalledProcessError:
            return None
        except json.JSONDecodeError:
            return None

    def query_option(self, option_path: str) -> Optional[Dict[str, Any]]:
        """Query a NixOS option by path using nixos-option."""
        cmd = [
            "nixos-option",
            "-I",
            "nixpkgs=channel:nixos-unstable",
            "--json",
            option_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            option_data = json.loads(result.stdout)

            option = {
                "name": option_path,
                "description": option_data.get("description", ""),
                "type": option_data.get("type", ""),
                "default": option_data.get("default", None),
                "example": option_data.get("example", None),
                "declared_by": option_data.get("declarations", []),
            }

            return option
        except subprocess.CalledProcessError:
            return None
        except json.JSONDecodeError:
            return None


# Model Context
class ModelContext:
    """ModelContext class for providing NixOS resources to AI models."""

    def __init__(self):
        """Initialize the ModelContext with a NixosAPI instance."""
        self.api = NixosAPI()
        self.cache = {}  # Simple in-memory cache

    def query_package(
        self, package_name: str, channel: str = "unstable"
    ) -> Optional[Dict[str, Any]]:
        """Query details about a specific NixOS package."""
        cache_key = f"package:{channel}:{package_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # First try exact attribute path
        if "." in package_name:  # Likely an attribute path
            pkg_metadata = self.api.get_package_metadata(package_name)
            if pkg_metadata:
                self.cache[cache_key] = pkg_metadata
                return pkg_metadata

        # Otherwise search by name
        results = self.api.search_packages(package_name, channel=channel)
        if results:
            # Find exact match or return first result
            for pkg in results:
                if pkg["name"] == package_name:
                    self.cache[cache_key] = pkg
                    return pkg

            # No exact match, return first result
            self.cache[cache_key] = results[0]
            return results[0]

        return None

    def search_packages(
        self, query: str, channel: str = "unstable", limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        """Search for NixOS packages matching a query string with pagination."""
        cache_key = f"search:{channel}:{query}:{limit}:{offset}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        results = self.api.search_packages(query, channel=channel)

        # Apply pagination
        total = len(results)
        paginated_results = results[offset : offset + limit] if results else []

        search_result = {
            "query": query,
            "channel": channel,
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": paginated_results,
        }

        self.cache[cache_key] = search_result
        return search_result

    def query_option(
        self, option_name: str, channel: str = "unstable"
    ) -> Optional[Dict[str, Any]]:
        """Query details about a specific NixOS option."""
        cache_key = f"option:{channel}:{option_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        option = self.api.query_option(option_name)
        if option:
            self.cache[cache_key] = option
            return option

        return None


# Create the FastAPI server
app = FastAPI(title="NixMCP", description="NixOS Model Context Protocol server")
# Initialize context
context = ModelContext()

# Create the FastMCP server
mcp = FastMCP(
    name="NixMCP",
    instructions="A Model Context Protocol server that provides access to NixOS packages and options.",
)

# Debug info about MCP
print("\nMCP server created:")
print(f"Type: {type(mcp)}")
print(f"Attributes: {dir(mcp)}")

# Direct API endpoints
# These endpoints provide the same functionality as the MCP resources
# but in a more traditional REST API format. They're useful for clients
# that don't support MCP or for simpler integration scenarios.


@app.get("/api/package/{package_name}")
async def get_package_direct(package_name: str, channel: str = "unstable"):
    """Direct endpoint for package data."""
    package = context.query_package(package_name, channel)
    if not package:
        return {"error": f"Package '{package_name}' not found"}
    return package


@app.get("/api/search/packages/{query}")
async def search_packages_direct(
    query: str, channel: str = "unstable", limit: int = 10, offset: int = 0
):
    """Direct endpoint for package search."""
    search_results = context.search_packages(query, channel, limit, offset)
    if not search_results["results"]:
        return {"error": f"No packages found matching '{query}'"}
    return search_results


@app.get("/api/option/{option_name}")
async def get_option_direct(option_name: str, channel: str = "unstable"):
    """Direct endpoint for NixOS option data."""
    option = context.query_option(option_name, channel)
    if not option:
        return {"error": f"Option '{option_name}' not found"}
    return option


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint that doesn't require Nix."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "server": "NixMCP",
        "version": "0.1.0",
    }


# Status endpoint with more detailed information
@app.get("/status")
def server_status():
    """Status endpoint with detailed server information."""
    nix_installed = True
    try:
        subprocess.run(
            ["nix", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        nix_installed = False

    return {
        "status": "ok",
        "timestamp": time.time(),
        "server": "NixMCP",
        "version": "0.1.0",
        "nix_installed": nix_installed,
        "endpoints": {
            "mcp_resources": [
                "nixos://package/{package_name}",
                "nixos://package/{package_name}/{channel}",
                "nixos://option/{option_name}",
                "nixos://option/{option_name}/{channel}",
                "nixos://search/packages/{query}",
                "nixos://search/packages/{query}/{channel}",
            ],
            "direct_api": [
                "/api/package/{package_name}[?channel={channel}]",
                "/api/search/packages/{query}[?channel={channel}&limit={limit}&offset={offset}]",
                "/api/option/{option_name}[?channel={channel}]",
            ],
        },
    }


# MCP is the focus of this project, legacy REST endpoints removed


# Define MCP Resource Handlers first, then register them
async def get_package_resource(package_name: str):
    """MCP resource handler for NixOS packages."""
    print(f"MCP: Fetching package {package_name}")
    # Default channel is used (unstable)
    package = context.query_package(package_name)
    if not package:
        return {"error": f"Package '{package_name}' not found"}
    return package


async def get_package_resource_with_channel(package_name: str, channel: str):
    """MCP resource handler for NixOS packages with specific channel."""
    package = context.query_package(package_name, channel)
    if not package:
        return {"error": f"Package '{package_name}' not found in channel '{channel}'"}
    return package


async def search_packages_resource(query: str):
    """MCP resource handler for searching NixOS packages."""
    print(f"MCP: Searching packages with query: {query}")
    # Default channel and pagination
    search_results = context.search_packages(query)
    if not search_results["results"]:
        return {"error": f"No packages found matching '{query}'"}
    return search_results


async def search_packages_resource_with_channel(query: str, channel: str):
    """MCP resource handler for searching NixOS packages with specific channel."""
    print(f"MCP: Searching packages with query: {query} in channel: {channel}")
    search_results = context.search_packages(query, channel)
    if not search_results["results"]:
        return {"error": f"No packages found matching '{query}' in channel '{channel}'"}
    return search_results


async def get_option_resource(option_name: str):
    """MCP resource handler for NixOS options."""
    # Default channel is used (unstable)
    option = context.query_option(option_name)
    if not option:
        return {"error": f"Option '{option_name}' not found"}
    return option


async def get_option_resource_with_channel(option_name: str, channel: str):
    """MCP resource handler for NixOS options with specific channel."""
    option = context.query_option(option_name, channel)
    if not option:
        return {"error": f"Option '{option_name}' not found in channel '{channel}'"}
    return option


# Explicitly register all resources using the decorator pattern
print("\nRegistering MCP resources...")


# Register package resources
@mcp.resource("nixos://package/{package_name}")
async def mcp_package(package_name: str):
    return await get_package_resource(package_name)


@mcp.resource("nixos://package/{package_name}/{channel}")
async def mcp_package_with_channel(package_name: str, channel: str):
    return await get_package_resource_with_channel(package_name, channel)


# Register search resources
@mcp.resource("nixos://search/packages/{query}")
async def mcp_search_packages(query: str):
    return await search_packages_resource(query)


@mcp.resource("nixos://search/packages/{query}/{channel}")
async def mcp_search_packages_with_channel(query: str, channel: str):
    return await search_packages_resource_with_channel(query, channel)


# Register option resources
@mcp.resource("nixos://option/{option_name}")
async def mcp_option(option_name: str):
    return await get_option_resource(option_name)


@mcp.resource("nixos://option/{option_name}/{channel}")
async def mcp_option_with_channel(option_name: str, channel: str):
    return await get_option_resource_with_channel(option_name, channel)


print("Registration complete")


if __name__ == "__main__":
    import uvicorn
    import logging
    import argparse
    from fastapi.middleware.cors import CORSMiddleware

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="NixMCP Server")
    parser.add_argument(
        "--reload", action="store_true", help="Enable hot reloading for development"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9421,
        help="Port to run the server on (default: 9421)",
    )
    args = parser.parse_args()

    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG)

    # Configure CORS for the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For development only, restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add specific route for easy testing
    @app.get("/debug/mcp-registered")
    def debug_mcp_registered():
        """Debug endpoint to show registered MCP resources."""
        registered = []
        for resource in mcp._resource_manager._resources.values():
            registered.append(str(resource.uri_template))
        return {"registered_resources": registered}

    # Add a debug endpoint to test direct resources
    @app.get("/debug/resource/{resource_type}/{query}")
    async def debug_resource(resource_type: str, query: str, channel: str = "unstable"):
        """Debug endpoint for direct resource access."""
        print(f"Debug resource request: {resource_type}/{query}")

        try:
            if resource_type == "package":
                return await get_package_resource(query)
            elif resource_type == "search":
                return await search_packages_resource(query)
            elif resource_type == "option":
                return await get_option_resource(query)
            else:
                return {"error": f"Unknown resource type: {resource_type}"}
        except Exception as e:
            return {"error": f"Error processing resource: {str(e)}"}

    # Mount the MCP server
    try:
        # Make sure the resources actually got registered
        resource_count = len(mcp._resource_manager._resources)
        print(f"\nFound {resource_count} registered MCP resources")

        # Now mount the MCP server to FastAPI
        app.mount("/mcp", mcp)
        print("Mounted MCP at /mcp")
    except Exception as e:
        print(f"\nError mounting MCP: {e}")

    # Debug info about registered resources
    print("\nRegistered MCP resources:")
    try:
        for resource in mcp._resource_manager._resources.values():
            print(f"  - {resource.uri_template}")
    except Exception as e:
        print(f"Error accessing resources: {e}")
        print(f"MCP object dir: {dir(mcp)}")

    port = args.port
    print("\nDebug access URLs:")
    print(
        f"  - Package URL: http://localhost:{port}/mcp/resource?uri=nixos://package/python"
    )
    print(
        f"  - Search URL: http://localhost:{port}/mcp/resource?uri=nixos://search/packages/python"
    )

    print(f"\nStarting NixMCP server on port {port}...")
    print(f"Access FastAPI docs at http://localhost:{port}/docs")
    print(f"Access MCP endpoints at http://localhost:{port}/mcp")

    uvicorn.run(
        "server:app", host="0.0.0.0", port=port, log_level="debug", reload=args.reload
    )
