#!/usr/bin/env python
"""
NixMCP Server - An API server for NixOS resources.

This implements a FastAPI server that provides endpoints for querying
NixOS packages and options using the Model Context Protocol (MCP).
"""

import json
import subprocess
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


# Legacy REST API Resources (keeping for backward compatibility)
@app.get("/packages/{package_name}")
def get_package(package_name: str, channel: str = "unstable") -> Dict[str, Any]:
    """Get information about a NixOS package."""
    package = context.query_package(package_name, channel)
    if not package:
        return {"error": f"Package '{package_name}' not found"}
    return package


@app.get("/options/{option_name}")
def get_option(option_name: str, channel: str = "unstable") -> Dict[str, Any]:
    """Get information about a NixOS option."""
    option = context.query_option(option_name, channel)
    if not option:
        return {"error": f"Option '{option_name}' not found"}
    return option


@app.get("/search/packages")
def search_packages(
    query: str, channel: str = "unstable", limit: int = 10
) -> Dict[str, Any]:
    """Search for NixOS packages."""
    packages = context.api.search_packages(query, channel)
    if not packages:
        return {"results": [], "count": 0}

    limited_results = packages[:limit]
    return {"results": limited_results, "count": len(limited_results)}


# MCP Resource Handlers
@mcp.resource("nixos://package/{package_name}")
async def get_package_resource(package_name: str):
    """MCP resource handler for NixOS packages."""
    print(f"MCP: Fetching package {package_name}")
    # Default channel is used (unstable)
    package = context.query_package(package_name)
    if not package:
        return {"error": f"Package '{package_name}' not found"}
    return package


@mcp.resource("nixos://package/{package_name}/{channel}")
async def get_package_resource_with_channel(package_name: str, channel: str):
    """MCP resource handler for NixOS packages with specific channel."""
    package = context.query_package(package_name, channel)
    if not package:
        return {"error": f"Package '{package_name}' not found in channel '{channel}'"}
    return package


@mcp.resource("nixos://option/{option_name}")
async def get_option_resource(option_name: str):
    """MCP resource handler for NixOS options."""
    # Default channel is used (unstable)
    option = context.query_option(option_name)
    if not option:
        return {"error": f"Option '{option_name}' not found"}
    return option


@mcp.resource("nixos://option/{option_name}/{channel}")
async def get_option_resource_with_channel(option_name: str, channel: str):
    """MCP resource handler for NixOS options with specific channel."""
    option = context.query_option(option_name, channel)
    if not option:
        return {"error": f"Option '{option_name}' not found in channel '{channel}'"}
    return option


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

    # Add MCP routes to the FastAPI app
    app.mount("/mcp", mcp)

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
        f"  - Test URL: http://localhost:{port}/mcp/resource?uri=nixos://package/python"
    )
    print(f"  - Direct FastAPI: http://localhost:{port}/packages/python")

    print(f"\nStarting NixMCP server on port {port}...")
    print(f"Access FastAPI docs at http://localhost:{port}/docs")
    print(f"Access MCP endpoints at http://localhost:{port}/mcp")

    uvicorn.run(
        "server:app", host="0.0.0.0", port=port, log_level="debug", reload=args.reload
    )
