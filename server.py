#!/usr/bin/env python
"""
NixMCP Server - An API server for NixOS resources.

This implements a FastAPI server that provides endpoints for querying
NixOS packages and options using the Model Context Protocol (MCP).
"""

import os
import logging
import logging.handlers
import json
import subprocess
import time
from typing import Dict, List, Optional, Any, Union

try:
    import uvicorn
    import requests
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from mcp.server.fastmcp import FastMCP, __version__ as mcp_version
    from dotenv import load_dotenv
    
    # Check if MCP version supports the features we need
    print(f"MCP version: {mcp_version}")
    mcp_version_parts = mcp_version.split('.')
    mcp_major_version = int(mcp_version_parts[0])
    mcp_minor_version = int(mcp_version_parts[1]) if len(mcp_version_parts) > 1 else 0
    MCP_MODERN_API = mcp_major_version >= 1 and mcp_minor_version >= 4
    print(f"Using modern API: {MCP_MODERN_API}")
    
except ImportError:
    raise ImportError(
        "Required packages not found. Please install them with: pip install mcp>=1.4.0 fastapi uvicorn python-dotenv requests"
        "\nOr run 'nix develop' to enter the development environment."
    )

# Load environment variables from .env file
load_dotenv()

# Configure logging
def setup_logging():
    """Configure logging for the NixMCP server."""
    log_file = os.environ.get("LOG_FILE", "nixmcp-server.log")
    log_level = os.environ.get("LOG_LEVEL", "DEBUG")
    
    # Create logger
    logger = logging.getLogger("nixmcp")
    logger.setLevel(getattr(logging, log_level))
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(getattr(logging, log_level))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("Logging initialized")
    return logger

# Initialize logging
logger = setup_logging()

# Create the MCP server
mcp = FastMCP(
    "NixMCP-Minimal", 
    version="1.0",
    dependencies=["fastapi", "uvicorn"]
)

# Elasticsearch client for NixOS search (simplified)
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

    def search_packages(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Search for NixOS packages."""
        if not query or query.strip() == "":
            return []
            
        if not self.es_auth:
            logger.warning("No Elasticsearch credentials configured")
            return []

        try:
            # Create a search query for packages
            search_body = {
                "from": offset,
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"package_attr_name": {"query": query, "boost": 10}}},
                            {"match": {"package_pname": {"query": query, "boost": 8}}},
                            {"match": {"package_description": {"query": query, "boost": 2}}},
                            {"match": {"package_all": query}},
                        ],
                        "filter": [{"term": {"type": "package"}}],
                    }
                },
            }
            
            logger.debug(f"Search packages query: {json.dumps(search_body)}")
            
            # Execute the search with direct HTTP request
            response = requests.post(
                self.es_url,
                json=search_body,
                auth=self.es_auth,
                headers={"Content-Type": "application/json"},
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Elasticsearch API error: {response.status_code}, {response.text}")
                return []
                
            result = response.json()
            
            # Process results
            packages = []
            if "hits" in result and "hits" in result["hits"]:
                for hit in result["hits"]["hits"]:
                    source = hit["_source"]
                    packages.append({
                        "attribute": source.get("package_attr_name", ""),
                        "name": source.get("package_pname", ""),
                        "version": source.get("package_version", ""),
                        "description": source.get("package_description", ""),
                        "homepage": source.get("package_homepage", [None])[0],
                        "license": source.get("package_license", []),
                        "maintainers": source.get("package_maintainers", []),
                        "score": hit.get("_score", 0),
                    })

            logger.info(f"Found {len(packages)} packages matching '{query}'")
            return packages

        except Exception as e:
            logger.error(f"Error searching packages: {e}")
            return []

    def search_options(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Search for NixOS options."""
        if not query or query.strip() == "":
            return []
            
        if not self.es_auth:
            logger.warning("No Elasticsearch credentials configured")
            return []

        try:
            # Create search query for options
            search_body = {
                "size": limit,
                "from": offset,
                "query": {
                    "bool": {
                        "filter": [{"term": {"type": "option"}}],
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "option_name^10",
                                        "option_description^2",
                                        "option_all"
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
            
            logger.debug(f"Search options query: {json.dumps(search_body)}")
            
            # Execute search
            response = requests.post(
                self.es_url,
                json=search_body,
                auth=self.es_auth,
                headers={"Content-Type": "application/json"},
                verify=False,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Elasticsearch API error: {response.status_code}, {response.text}")
                return []
            
            result = response.json()
            
            # Process results
            options = []
            if "hits" in result and "hits" in result["hits"]:
                for hit in result["hits"]["hits"]:
                    source = hit["_source"]
                    options.append({
                        "name": source.get("option_name", ""),
                        "description": source.get("option_description", ""),
                        "type": source.get("option_type", ""),
                        "default": source.get("option_default", None),
                        "example": source.get("option_example", None),
                        "declared_by": source.get("option_declarations", []),
                        "score": hit.get("_score", 0),
                    })
                    
            logger.info(f"Found {len(options)} options matching '{query}'")
            return options
            
        except Exception as e:
            logger.error(f"Error searching options: {e}")
            return []


# Model Context for MCP Resources
class ModelContext:
    """Provides NixOS resources to AI models via MCP."""

    def __init__(self):
        """Initialize the ModelContext."""
        self.es_client = ElasticsearchClient()
        logger.info("ModelContext initialized")

    def get_package(self, package_name: str) -> Dict[str, Any]:
        """Get information about a NixOS package."""
        logger.info(f"Getting package info: {package_name}")
        return {
            "name": package_name,
            "message": "This is a simplified implementation. For full package details, configure Elasticsearch credentials."
        }
    
    def search_packages(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS packages."""
        logger.info(f"Searching packages: {query}")
        results = self.es_client.search_packages(query, limit=limit)
        return {
            "query": query,
            "count": len(results),
            "results": results
        }
        
    def search_options(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS options."""
        logger.info(f"Searching options: {query}")
        results = self.es_client.search_options(query, limit=limit)
        return {
            "query": query,
            "count": len(results),
            "results": results
        }


# Initialize the model context
model_context = ModelContext()

# Register all MCP resources using decorators
logger.info("Defining MCP resource handlers")

# Status resource handler
@mcp.resource("nixos://status")
def status_resource() -> Dict[str, Any]:
    """Get the status of the NixMCP server"""
    logger.info("Resource handler: status")
    return {
        "status": "ok",
        "name": "NixMCP",
        "version": "1.0",
        "mcp_version": mcp_version,
    }

# The separate registrations below were causing issues
# Let's try an alternative approach to force all resources to be registered

# Create resource URI templates and print them for debugging
status_uri = "nixos://status"
package_uri = "nixos://package/{package_name}"
package_search_uri = "nixos://search/packages/{query}"
option_search_uri = "nixos://search/options/{query}"
option_uri = "nixos://option/{option_name}"

# Package resource handler
@mcp.resource(package_uri)
def package_resource(package_name: str) -> Dict[str, Any]:
    """Get information about a NixOS package"""
    logger.info(f"Resource handler: package: {package_name}")
    return model_context.get_package(package_name)

# Package search resource handler
@mcp.resource(package_search_uri)
def search_packages_resource(query: str) -> Dict[str, Any]:
    """Search for NixOS packages"""
    logger.info(f"Resource handler: search packages: {query}")
    return model_context.search_packages(query)

# Option search resource handler
@mcp.resource(option_search_uri)
def search_options_resource(query: str) -> Dict[str, Any]:
    """Search for NixOS options"""
    logger.info(f"Resource handler: search options: {query}")
    return model_context.search_options(query)

# Option resource handler
@mcp.resource(option_uri)
def option_resource(option_name: str) -> Dict[str, Any]:
    """Get information about a NixOS option"""
    logger.info(f"Resource handler: option: {option_name}")
    return {
        "name": option_name,
        "message": "This is a simplified implementation. For option details, configure Elasticsearch credentials."
    }

# Log registered resources
logger.info(f"Registered resources: {status_uri}, {package_uri}, {package_search_uri}, {option_search_uri}, {option_uri}")

# Main FastAPI app for direct API endpoints
app = FastAPI(title="NixMCP-Minimal", description="NixOS Model Context Protocol server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "name": "NixMCP-Minimal",
        "version": "1.0",
    }

# MCP resource endpoint
@app.get("/mcp/resource")
async def mcp_resource(uri: str, request: Request):
    """Get a resource from the MCP server."""
    logger.info(f"MCP resource request: {uri}")
    
    # Log available resources
    logger.info(f"Registered resources: {status_uri}, {package_uri}, {package_search_uri}, {option_search_uri}, {option_uri}")
    
    try:
        # Try manual dispatch based on URI pattern
        if uri == status_uri:
            logger.info("Dispatching to status_resource handler")
            return status_resource()
        elif uri.startswith("nixos://package/"):
            package_name = uri.replace("nixos://package/", "")
            logger.info(f"Dispatching to package_resource handler with {package_name}")
            return package_resource(package_name)
        elif uri.startswith("nixos://search/packages/"):
            query = uri.replace("nixos://search/packages/", "")
            logger.info(f"Dispatching to search_packages_resource handler with {query}")
            return search_packages_resource(query)
        elif uri.startswith("nixos://search/options/"):
            query = uri.replace("nixos://search/options/", "")
            logger.info(f"Dispatching to search_options_resource handler with {query}")
            return search_options_resource(query)
        elif uri.startswith("nixos://option/"):
            option_name = uri.replace("nixos://option/", "")
            logger.info(f"Dispatching to option_resource handler with {option_name}")
            return option_resource(option_name)
            
        # If no direct match, fall back to MCP library
        logger.info(f"No direct handler match, falling back to mcp.read_resource({uri})")
        resource = await mcp.read_resource(uri)
        return resource
    except Exception as e:
        logger.error(f"Error handling MCP resource request: {e}")
        return {"error": str(e), "uri": uri}

# Debug endpoint to show registered MCP resources
@app.get("/debug/mcp-registered")
def debug_mcp_registered():
    """Debug endpoint to show registered MCP resources."""
    registered = []
    mcp_info = {}
    try:
        # Enhanced diagnostic info
        mcp_info = {
            "version": mcp_version,
            "modern_api": MCP_MODERN_API,
            "attributes": [attr for attr in dir(mcp) if not attr.startswith('__')],
        }
        
        # This version of MCP seems to have issues reporting the resources
        # So we'll use our known list of registered URIs
        registered = [
            status_uri,
            package_uri,
            package_search_uri,
            option_search_uri,
            option_uri
        ]
        
        # Add information about the handlers too
        mcp_info["handlers"] = {
            "status": str(status_resource),
            "package": str(package_resource),
            "search_packages": str(search_packages_resource),
            "search_options": str(search_options_resource),
            "option": str(option_resource)
        }
        
        # Safely get information about list_resources if available
        if hasattr(mcp, 'list_resources'):
            try:
                # For async methods, we can't call them directly in sync code
                mcp_info["has_list_resources"] = True
            except Exception as e:
                logger.info(f"mcp.list_resources access error: {e}")
        
        # Safely get information about list_resource_templates if available
        if hasattr(mcp, 'list_resource_templates'):
            try:
                # For async methods, we can't call them directly in sync code
                mcp_info["has_list_resource_templates"] = True
            except Exception as e:
                logger.info(f"mcp.list_resource_templates access error: {e}")
                
    except Exception as e:
        logger.error(f"Error in debug_mcp_registered: {e}")
        return {"error": str(e), "registered_resources": registered, "mcp_info": mcp_info}
        
    return {"registered_resources": registered, "mcp_info": mcp_info}

# Run the server
if __name__ == "__main__":
    import argparse
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="NixMCP-Minimal Server")
    parser.add_argument(
        "--reload", action="store_true", help="Enable hot reloading for development"
    )
    parser.add_argument(
        "--port", type=int, default=9421, help="Port to run the server on (default: 9421)"
    )
    args = parser.parse_args()
    
    logger.info("Starting NixMCP-Minimal server")
    
    # Create the Starlette app using SSE
    try:
        if hasattr(mcp, 'sse_app'):
            # For modern versions of MCP
            logger.info("Using modern MCP API with sse_app()")
            starlette_app = mcp.sse_app()
            
            # Mount the FastAPI app on the starlette app
            from starlette.middleware.wsgi import WSGIMiddleware
            mcp_app = starlette_app
            
            # Add the FastAPI app as a mounted application
            from fastapi.middleware.wsgi import WSGIMiddleware
            app.mount("/api", app)
            
            # Mount the FastAPI app to the starlette app
            original_routes = mcp_app.routes.copy()
            mcp_app.routes = []
            for route in original_routes:
                mcp_app.routes.append(route)
            
            mcp_app.mount("/api", app)
            
            # Run with the configured Starlette app
            uvicorn.run(
                mcp_app,
                host="0.0.0.0",
                port=args.port,
                reload=args.reload
            )
        else:
            # For older versions without sse_app
            logger.info("Using legacy MCP API without sse_app()")
            # Create our own route configuration
            from mcp.server.sse import SseServerTransport
            
            # Mount the FastAPI app
            app.mount("/api", app)
            
            # Create an SSE transport
            sse = SseServerTransport("/mcp/messages/")
            
            # Create an SSE handler
            async def handle_sse(request: Request):
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await mcp._mcp_server.run(
                        streams[0], 
                        streams[1], 
                        mcp._mcp_server.create_initialization_options()
                    )
            
            # Create the Starlette app with SSE routes
            starlette_app = Starlette(
                debug=True,
                routes=[
                    Route("/mcp/sse", endpoint=handle_sse),
                    Mount("/mcp/messages/", app=sse.handle_post_message),
                    Mount("/", app=app)
                ],
            )
            
            # Run the server
            uvicorn.run(
                starlette_app,
                host="0.0.0.0",
                port=args.port,
                reload=args.reload
            )
    except Exception as e:
        logger.error(f"Error starting MCP server: {e}")
        # Fall back to running just the FastAPI server
        logger.info("Falling back to FastAPI server without MCP")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=args.port,
            reload=args.reload
        )
