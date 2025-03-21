#!/usr/bin/env python
"""
NixMCP Server - A simple MCP server for NixOS resources.

This implements a minimal FastMCP server that provides resources for querying
NixOS packages and options using the Model Context Protocol (MCP).
"""

import os
import sys
import logging
import logging.handlers
import json
from typing import Dict, List, Optional, Any, Union
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

# Configure logging
def setup_logging():
    """Configure logging for the NixMCP server."""
    log_file = os.environ.get("LOG_FILE", "nixmcp-server.log")
    log_level = os.environ.get("LOG_LEVEL", "INFO")

    # Create logger
    logger = logging.getLogger("nixmcp")

    # Only configure handlers if they haven't been added yet
    # This prevents duplicate logging when code is reloaded
    if not logger.handlers:
        logger.setLevel(getattr(logging, log_level))

        # Create file handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(getattr(logging, log_level))

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        logger.info("Logging initialized")

    return logger

# Initialize logging
logger = setup_logging()

# Elasticsearch client for accessing NixOS resources
class ElasticsearchClient:
    """Client for accessing NixOS Elasticsearch API."""

    def __init__(self):
        """Initialize the Elasticsearch client."""
        # Hardcoded Elasticsearch credentials
        self.es_url = "https://search.nixos.org/backend/latest-42-nixos-unstable/_search"
        self.es_user = "aWVSALXpZv"
        self.es_password = "X8gPHnzL52wFEekuxsfQ9cSh"

        # Store the credentials for direct API access
        self.es_auth = (self.es_user, self.es_password)
        logger.info("Elasticsearch credentials hardcoded and configured")

    def search_packages(self, query: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Search for NixOS packages."""

        # Check if query contains wildcards
        if '*' in query:
            # Use wildcard query for explicit wildcard searches
            request_data = {
                "from": offset,
                "size": limit,
                "query": {
                    "query_string": {
                        "query": query,
                        "fields": ["package_attr_name^9", "package_pname^6", "package_description^2"],
                        "analyze_wildcard": True
                    }
                },
            }
        else:
            # For non-wildcard searches, use a more flexible approach
            # that can match partial terms and is more forgiving
            request_data = {
                "from": offset,
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            # Exact match with high boost
                            {"term": {"package_attr_name": {"value": query, "boost": 10}}},
                            # Prefix match for package names
                            {"prefix": {"package_attr_name": {"value": query, "boost": 5}}},
                            # Contains match for package names
                            {"wildcard": {"package_attr_name": {"value": f"*{query}*", "boost": 3}}},
                            # Exact match on package pname
                            {"term": {"package_pname": {"value": query, "boost": 7}}},
                            # Contains match for package pname
                            {"wildcard": {"package_pname": {"value": f"*{query}*", "boost": 4}}},
                            # Full-text search in description
                            {"match": {"package_description": {"query": query, "boost": 1}}}
                        ],
                        "minimum_should_match": 1
                    }
                },
            }

        try:
            response = requests.post(
                self.es_url,
                json=request_data,
                auth=self.es_auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            # Process the response
            hits = data.get("hits", {}).get("hits", [])
            total = data.get("hits", {}).get("total", {}).get("value", 0)

            packages = []
            for hit in hits:
                source = hit.get("_source", {})
                packages.append({
                    "name": source.get("package_attr_name", ""),
                    "version": source.get("package_version", ""),
                    "description": source.get("package_description", ""),
                    "channel": source.get("package_channel", ""),
                })

            return {
                "count": total,
                "packages": packages,
            }

        except Exception as e:
            logger.error(f"Error searching packages: {e}")
            return {"count": 0, "packages": [], "error": str(e)}

    def search_options(self, query: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Search for NixOS options."""

        # Check if query contains wildcards
        if '*' in query:
            # Use wildcard query for explicit wildcard searches
            request_data = {
                "from": offset,
                "size": limit,
                "query": {
                    "query_string": {
                        "query": query,
                        "fields": ["option_name^9", "option_description^3"],
                        "analyze_wildcard": True
                    }
                },
            }
        else:
            # For non-wildcard searches, use a more flexible approach
            # that can match partial terms and is more forgiving
            request_data = {
                "from": offset,
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            # Exact match with high boost
                            {"term": {"option_name": {"value": query, "boost": 10}}},
                            # Prefix match for option names
                            {"prefix": {"option_name": {"value": query, "boost": 5}}},
                            # Contains match for option names
                            {"wildcard": {"option_name": {"value": f"*{query}*", "boost": 3}}},
                            # Full-text search in description
                            {"match": {"option_description": {"query": query, "boost": 1}}}
                        ],
                        "minimum_should_match": 1
                    }
                },
            }

        try:
            response = requests.post(
                self.es_url.replace("packages", "options"),
                json=request_data,
                auth=self.es_auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            # Process the response
            hits = data.get("hits", {}).get("hits", [])
            total = data.get("hits", {}).get("total", {}).get("value", 0)

            options = []
            for hit in hits:
                source = hit.get("_source", {})
                options.append({
                    "name": source.get("option_name", ""),
                    "description": source.get("option_description", ""),
                    "type": source.get("option_type", ""),
                    "default": source.get("option_default", ""),
                })

            return {
                "count": total,
                "options": options,
            }

        except Exception as e:
            logger.error(f"Error searching options: {e}")
            return {"count": 0, "options": [], "error": str(e)}

# Model Context with app-specific data
class NixOSContext:
    """Provides NixOS resources to AI models."""

    def __init__(self):
        """Initialize the ModelContext."""
        self.es_client = ElasticsearchClient()
        logger.info("NixOSContext initialized")

    def get_status(self) -> Dict[str, Any]:
        """Get the status of the NixMCP server."""
        return {
            "status": "ok",
            "version": "1.0.0",
            "name": "NixMCP",
            "description": "NixOS Model Context Protocol Server",
        }

    def get_package(self, package_name: str) -> Dict[str, Any]:
        """Get information about a NixOS package."""
        logger.info(f"Getting detailed information for package: {package_name}")
        
        try:
            # Build a query to find the exact package by name
            request_data = {
                "size": 1,  # We only need one result
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"package_attr_name": package_name}}
                        ]
                    }
                }
            }
            
            # Make the request to Elasticsearch
            response = requests.post(
                self.es_client.es_url,
                json=request_data,
                auth=self.es_client.es_auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            
            # Process the response
            hits = data.get("hits", {}).get("hits", [])
            
            if not hits:
                logger.warning(f"Package {package_name} not found")
                return {
                    "name": package_name,
                    "error": "Package not found",
                    "found": False
                }
            
            # Extract package details from the first hit
            source = hits[0].get("_source", {})
            
            # Return comprehensive package information
            return {
                "name": source.get("package_attr_name", package_name),
                "pname": source.get("package_pname", ""),
                "version": source.get("package_version", ""),
                "description": source.get("package_description", ""),
                "longDescription": source.get("package_longDescription", ""),
                "license": source.get("package_license", ""),
                "homepage": source.get("package_homepage", ""),
                "maintainers": source.get("package_maintainers", []),
                "platforms": source.get("package_platforms", []),
                "channel": source.get("package_channel", "nixos-unstable"),
                "position": source.get("package_position", ""),
                "outputs": source.get("package_outputs", []),
                "found": True
            }
            
        except Exception as e:
            logger.error(f"Error getting package information: {e}")
            return {
                "name": package_name,
                "error": str(e),
                "found": False
            }

    def search_packages(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS packages."""
        return self.es_client.search_packages(query, limit)

    def search_options(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS options."""
        return self.es_client.search_options(query, limit)

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get information about a NixOS option."""
        logger.info(f"Getting detailed information for option: {option_name}")
        
        try:
            # Build a query to find the exact option by name
            request_data = {
                "size": 1,  # We only need one result
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"option_name": option_name}}
                        ]
                    }
                }
            }
            
            # Make the request to Elasticsearch
            response = requests.post(
                self.es_client.es_url.replace("packages", "options"),
                json=request_data,
                auth=self.es_client.es_auth,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            
            # Process the response
            hits = data.get("hits", {}).get("hits", [])
            
            if not hits:
                logger.warning(f"Option {option_name} not found")
                return {
                    "name": option_name,
                    "error": "Option not found",
                    "found": False
                }
            
            # Extract option details from the first hit
            source = hits[0].get("_source", {})
            
            # Return comprehensive option information
            return {
                "name": source.get("option_name", option_name),
                "description": source.get("option_description", ""),
                "type": source.get("option_type", ""),
                "default": source.get("option_default", ""),
                "example": source.get("option_example", ""),
                "declarations": source.get("option_declarations", []),
                "readOnly": source.get("option_readOnly", False),
                "found": True
            }
            
        except Exception as e:
            logger.error(f"Error getting option information: {e}")
            return {
                "name": option_name,
                "error": str(e),
                "found": False
            }

# Define the lifespan context manager for app initialization
@asynccontextmanager
async def app_lifespan(mcp_server: FastMCP):
    logger.info("Initializing NixMCP server")
    # Here you would typically set up database connections or other resources
    # We'll just create our context object
    context = NixOSContext()
    
    try:
        # We yield our context that will be accessible in all handlers
        yield {"context": context}
    except Exception as e:
        logger.error(f"Error in server lifespan: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down NixMCP server")
        # Close any open connections or resources
        try:
            # Add any cleanup code here if needed
            pass
        except Exception as e:
            logger.error(f"Error during server shutdown cleanup: {e}")

# Initialize the model context before creating server
model_context = NixOSContext()

# Create the MCP server with the lifespan handler
logger.info("Creating FastMCP server instance")
mcp = FastMCP(
    "NixMCP", 
    version="1.0.0",
    description="NixOS Model Context Protocol Server",
    lifespan=app_lifespan
)

# Define MCP resources
@mcp.resource("nixos://status")
def status_resource():
    """Get the status of the NixMCP server."""
    logger.info("Handling status resource request")
    return model_context.get_status()

@mcp.resource("nixos://package/{package_name}")
def package_resource(package_name: str):
    """Get information about a NixOS package."""
    logger.info(f"Handling package resource request for {package_name}")
    return model_context.get_package(package_name)

@mcp.resource("nixos://search/packages/{query}")
def search_packages_resource(query: str):
    """Search for NixOS packages."""
    logger.info(f"Handling package search request for {query}")
    return model_context.search_packages(query)

@mcp.resource("nixos://search/options/{query}")
def search_options_resource(query: str):
    """Search for NixOS options."""
    logger.info(f"Handling option search request for {query}")
    return model_context.search_options(query)

@mcp.resource("nixos://option/{option_name}")
def option_resource(option_name: str):
    """Get information about a NixOS option."""
    logger.info(f"Handling option resource request for {option_name}")
    return model_context.get_option(option_name)

# Add a search tool for NixOS packages and options
@mcp.tool()
def search_nixos(query: str, search_type: str = "packages", limit: int = 10) -> str:
    """
    Search for NixOS packages or options.
    
    Args:
        query: The search term
        search_type: Type of search - either "packages" or "options"
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        Results formatted as text
    """
    logger.info(f"Searching for {search_type} with query '{query}'")
    
    if search_type.lower() not in ["packages", "options"]:
        return f"Error: Invalid search_type. Must be 'packages' or 'options'."
    
    try:
        if search_type.lower() == "packages":
            results = model_context.search_packages(query, limit)
            packages = results.get("packages", [])
            
            if not packages:
                return f"No packages found for query: '{query}'"
            
            output = f"Found {len(packages)} packages for '{query}':\n\n"
            for pkg in packages:
                output += f"- {pkg.get('name', 'Unknown')} ({pkg.get('version', 'Unknown')})\n"
                output += f"  {pkg.get('description', 'No description')}\n"
                output += f"  Channel: {pkg.get('channel', 'Unknown')}\n\n"
            
            return output
        else:  # options
            results = model_context.search_options(query, limit)
            options = results.get("options", [])
            
            if not options:
                return f"No options found for query: '{query}'"
            
            output = f"Found {len(options)} options for '{query}':\n\n"
            for opt in options:
                output += f"- {opt.get('name', 'Unknown')}\n"
                output += f"  {opt.get('description', 'No description')}\n"
                output += f"  Type: {opt.get('type', 'Unknown')}\n"
                output += f"  Default: {opt.get('default', 'None')}\n\n"
            
            return output
    
    except Exception as e:
        logger.error(f"Error in search_nixos: {e}")
        return f"Error performing search: {str(e)}"

@mcp.tool()
def get_nixos_package(package_name: str) -> str:
    """
    Get detailed information about a NixOS package.
    
    Args:
        package_name: The name of the package
    
    Returns:
        Detailed package information formatted as text
    """
    logger.info(f"Getting detailed information for package: {package_name}")
    
    try:
        package_info = model_context.get_package(package_name)
        
        if not package_info.get("found", False):
            return f"Package '{package_name}' not found."
        
        # Format the package information
        output = f"# {package_info.get('name', package_name)}\n\n"
        
        if package_info.get('version'):
            output += f"**Version:** {package_info.get('version')}\n"
        
        if package_info.get('description'):
            output += f"\n**Description:** {package_info.get('description')}\n"
        
        if package_info.get('longDescription'):
            output += f"\n**Long Description:**\n{package_info.get('longDescription')}\n"
        
        if package_info.get('license'):
            output += f"\n**License:** {package_info.get('license')}\n"
        
        if package_info.get('homepage'):
            output += f"\n**Homepage:** {package_info.get('homepage')}\n"
        
        if package_info.get('maintainers'):
            maintainers = package_info.get('maintainers')
            if isinstance(maintainers, list) and maintainers:
                # Convert any dictionary items to strings
                maintainer_strings = []
                for m in maintainers:
                    if isinstance(m, dict):
                        if 'name' in m:
                            maintainer_strings.append(m['name'])
                        elif 'email' in m:
                            maintainer_strings.append(m['email'])
                        else:
                            maintainer_strings.append(str(m))
                    else:
                        maintainer_strings.append(str(m))
                output += f"\n**Maintainers:** {', '.join(maintainer_strings)}\n"
        
        if package_info.get('platforms'):
            platforms = package_info.get('platforms')
            if isinstance(platforms, list) and platforms:
                # Convert any dictionary or complex items to strings
                platform_strings = [str(p) for p in platforms]
                output += f"\n**Platforms:** {', '.join(platform_strings)}\n"
        
        if package_info.get('channel'):
            output += f"\n**Channel:** {package_info.get('channel')}\n"
        
        return output
    
    except Exception as e:
        logger.error(f"Error getting package information: {e}")
        return f"Error getting information for package '{package_name}': {str(e)}"

@mcp.tool()
def get_nixos_option(option_name: str) -> str:
    """
    Get detailed information about a NixOS option.
    
    Args:
        option_name: The name of the option
    
    Returns:
        Detailed option information formatted as text
    """
    logger.info(f"Getting detailed information for option: {option_name}")
    
    try:
        option_info = model_context.get_option(option_name)
        
        if not option_info.get("found", False):
            return f"Option '{option_name}' not found."
        
        # Format the option information
        output = f"# {option_info.get('name', option_name)}\n\n"
        
        if option_info.get('description'):
            output += f"**Description:** {option_info.get('description')}\n\n"
        
        if option_info.get('type'):
            output += f"**Type:** {option_info.get('type')}\n"
        
        if option_info.get('default') is not None:
            output += f"**Default:** {option_info.get('default')}\n"
        
        if option_info.get('example'):
            output += f"\n**Example:**\n```nix\n{option_info.get('example')}\n```\n"
        
        if option_info.get('declarations'):
            declarations = option_info.get('declarations')
            if isinstance(declarations, list) and declarations:
                output += f"\n**Declared in:**\n"
                for decl in declarations:
                    output += f"- {decl}\n"
        
        if option_info.get('readOnly'):
            output += f"\n**Read Only:** Yes\n"
        
        return output
    
    except Exception as e:
        logger.error(f"Error getting option information: {e}")
        return f"Error getting information for option '{option_name}': {str(e)}"

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    # Exit cleanly
    sys.exit(0)

# Run the MCP server if this script is executed directly
if __name__ == "__main__":
    import signal
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    try:
        # Run the server directly using FastMCP's method without parameters
        # FastMCP doesn't take host/port parameters in its run() method
        logger.info("Starting NixMCP server with signal handlers for graceful shutdown")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)