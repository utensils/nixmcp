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
        self.es_url = os.getenv(
            "ELASTICSEARCH_URL",
            "https://search.nixos.org/backend/latest-42-nixos-unstable/_search",
        )
        self.es_user = os.getenv("ELASTICSEARCH_USER")
        self.es_password = os.getenv("ELASTICSEARCH_PASSWORD")

        # Store the credentials for direct API access
        self.es_auth = None
        if self.es_user and self.es_password:
            self.es_auth = (self.es_user, self.es_password)
            logger.info("Elasticsearch credentials configured")
        else:
            logger.warning("No Elasticsearch credentials found. Using mock data.")

    def search_packages(self, query: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Search for NixOS packages."""
        if not self.es_auth:
            # Return mock data if no credentials
            return {
                "count": 1,
                "packages": [
                    {
                        "name": "python3",
                        "version": "3.11.0",
                        "description": "A high-level dynamically-typed programming language",
                        "channel": "nixos-unstable",
                    }
                ],
            }

        # Build the search request
        request_data = {
            "from": offset,
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["package_attr_name^9", "package_pname^6", "package_description^2"],
                    "type": "best_fields",
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
        if not self.es_auth:
            # Return mock data if no credentials
            return {
                "count": 1,
                "options": [
                    {
                        "name": "services.nginx.enable",
                        "description": "Whether to enable the nginx web server",
                        "type": "boolean",
                        "default": "false",
                    }
                ],
            }

        # Build the search request
        request_data = {
            "from": offset,
            "size": limit,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["option_name^9", "option_description^3"],
                    "type": "best_fields",
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
        # For now, just return a mock response
        # In a real implementation, we would query the package database
        return {
            "name": package_name,
            "version": "1.0.0",
            "description": f"Information about {package_name}",
            "channel": "nixos-unstable",
        }

    def search_packages(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS packages."""
        return self.es_client.search_packages(query, limit)

    def search_options(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS options."""
        return self.es_client.search_options(query, limit)

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get information about a NixOS option."""
        # For now, just return a mock response
        # In a real implementation, we would query the options database
        return {
            "name": option_name,
            "description": f"Information about {option_name}",
            "type": "string",
            "default": "",
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
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down NixMCP server")

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

# Add a simple addition tool for testing
@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers together and return the result."""
    logger.info(f"Adding {a} and {b}")
    return a + b

# Run the MCP server if this script is executed directly
if __name__ == "__main__":
    # Run the server directly using FastMCP's method without parameters
    # FastMCP doesn't take host/port parameters in its run() method
    mcp.run()