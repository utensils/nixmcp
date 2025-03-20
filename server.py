#!/usr/bin/env python
"""
NixMCP Server - An API server for NixOS resources.

This implements a FastAPI server that provides endpoints for querying
NixOS packages and options.
"""

import json
import subprocess
from typing import Dict, List, Optional, Any, Union

try:
    from fastapi import FastAPI
    import uvicorn
except ImportError:
    raise ImportError(
        "FastAPI or Uvicorn not found. Please install them with: pip install fastapi uvicorn"
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
            subprocess.run(["nix", "--version"], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise RuntimeError("Nix installation not found. Please install Nix to use this tool.")
    
    def search_packages(self, query: str, channel: str = "unstable") -> List[Dict[str, Any]]:
        """Search for NixOS packages using nix search."""
        cmd = ["nix", "search", f"nixpkgs/{channel}", query, "--json"]
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            packages_data = json.loads(result.stdout)
            packages = []
            
            for pkg_attr, pkg_info in packages_data.items():
                name = pkg_attr.split(".")[-1]
                packages.append({
                    "attribute": pkg_attr,
                    "name": name,
                    "version": pkg_info.get("version", ""),
                    "description": pkg_info.get("description", "")
                })
            
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
                text=True
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
                "maintainers": pkg_data.get("meta", {}).get("maintainers", [])
            }
            
            return metadata
        except subprocess.CalledProcessError:
            return None
        except json.JSONDecodeError:
            return None
    
    def query_option(self, option_path: str) -> Optional[Dict[str, Any]]:
        """Query a NixOS option by path using nixos-option."""
        cmd = ["nixos-option", "-I", "nixpkgs=channel:nixos-unstable", "--json", option_path]
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            option_data = json.loads(result.stdout)
            
            option = {
                "name": option_path,
                "description": option_data.get("description", ""),
                "type": option_data.get("type", ""),
                "default": option_data.get("default", None),
                "example": option_data.get("example", None),
                "declared_by": option_data.get("declarations", [])
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

    def query_package(self, package_name: str, channel: str = "unstable") -> Optional[Dict[str, Any]]:
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

    def query_option(self, option_name: str, channel: str = "unstable") -> Optional[Dict[str, Any]]:
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

# Resources
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
def search_packages(query: str, channel: str = "unstable", limit: int = 10) -> Dict[str, Any]:
    """Search for NixOS packages."""
    packages = context.api.search_packages(query, channel)
    if not packages:
        return {"results": [], "count": 0}
    
    limited_results = packages[:limit]
    return {
        "results": limited_results,
        "count": len(limited_results)
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting NixMCP server on port 8000...")
    print("Access MCP Inspector at http://localhost:8000/docs")
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
