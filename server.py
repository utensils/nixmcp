#!/usr/bin/env python
"""
NixMCP Server - An API server for NixOS resources.

This implements a FastAPI server that provides endpoints for querying
NixOS packages and options using the Model Context Protocol (MCP).
"""

import json
import os
import subprocess
import time
from typing import Dict, List, Optional, Any, Union

try:
    from fastapi import FastAPI
    import uvicorn
    from mcp.server import FastMCP
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import ApiError
    from dotenv import load_dotenv
except ImportError:
    raise ImportError(
        "Required packages not found. Please install them with: pip install mcp>=1.4.0 fastapi uvicorn elasticsearch python-dotenv"
        "\nOr run 'nix develop' to enter the development environment."
    )

# Load environment variables from .env file
load_dotenv()


# Elasticsearch client for NixOS search
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
        
        # Create Elasticsearch client if credentials are available
        self.es = None
        if self.es_user and self.es_password:
            try:
                # Initialize Elasticsearch client with basic auth
                # Set verify_certs=False and timeout to handle NixOS search API better
                self.es = Elasticsearch(
                    self.es_url, 
                    basic_auth=(self.es_user, self.es_password),
                    verify_certs=False,
                    request_timeout=30,
                    max_retries=3,
                    retry_on_timeout=True,
                    # Set this to ignore version verification since NixOS search has a custom API
                    meta_header=False
                )
                print("Elasticsearch client initialized with Python client")
            except Exception as e:
                print(f"Failed to initialize Elasticsearch client: {e}")
                self.es = None
                
        # Test the connection with direct API access if the client fails
        if self.es is None and self.es_auth:
            print("Trying direct API access instead...")
            try:
                import requests
                response = requests.get(
                    self.es_url,
                    auth=self.es_auth,
                    verify=False,
                    timeout=10
                )
                if response.status_code == 200:
                    print("Direct API access to Elasticsearch works")
                    # We'll implement the search with direct requests
                else:
                    print(f"Direct API access failed with status: {response.status_code}")
            except Exception as e:
                print(f"Direct API access error: {e}")

    def search_packages(
        self, query: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search for NixOS packages using Elasticsearch.

        Args:
            query: The search query string
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            List of package dictionaries
        """
        if not self.es:
            print("Elasticsearch client not available, cannot search packages")
            return []

        try:
            # Create a search query for packages
            search_body = {
                "from": offset,
                "size": limit,
                "sort": [{"package_attr_name.raw": {"order": "asc"}}],
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "package_attr_name": {"query": query, "boost": 10}
                                }
                            },
                            {"match": {"package_pname": {"query": query, "boost": 8}}},
                            {
                                "match": {
                                    "package_attr_name_reverse": {
                                        "query": query,
                                        "boost": 5,
                                    }
                                }
                            },
                            {
                                "match": {
                                    "package_description": {"query": query, "boost": 2}
                                }
                            },
                            {
                                "match": {
                                    "package_description_normalized": {"query": query}
                                }
                            },
                            {
                                "match": {
                                    "package_maintainers_names": {
                                        "query": query,
                                        "boost": 3,
                                    }
                                }
                            },
                            {"match": {"package_all": query}},
                        ],
                        "filter": [{"term": {"type": "package"}}],
                    }
                },
            }

            # Execute the search
            result = self.es.search(body=search_body)

            # Process results into a consistent format
            packages = []
            for hit in result["hits"]["hits"]:
                source = hit["_source"]
                packages.append(
                    {
                        "attribute": source.get("package_attr_name", ""),
                        "name": source.get("package_pname", ""),
                        "version": source.get("package_version", ""),
                        "description": source.get("package_description", ""),
                        "homepage": source.get("package_homepage", [None])[0],
                        "license": source.get("package_license", []),
                        "maintainers": source.get("package_maintainers", []),
                        "platforms": source.get("package_platforms", []),
                        "score": hit.get("_score", 0),
                    }
                )

            return packages

        except ApiError as e:
            print(f"Elasticsearch API error: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in Elasticsearch search: {e}")
            return []

    def search_options(
        self, query: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search for NixOS options using Elasticsearch.

        Args:
            query: The search query string
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            List of option dictionaries
        """
        try:
            import requests
            
            # Create search body based on the curl example
            search_body = {
                "size": limit,
                "from": offset,
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"type": {"value": "option", "_name": "filter_options"}}}
                        ],
                        "must": [
                            {"dis_max": {
                                "tie_breaker": 0.7,
                                "queries": [
                                    {"multi_match": {
                                        "type": "cross_fields",
                                        "query": query,
                                        "analyzer": "whitespace",
                                        "auto_generate_synonyms_phrase_query": False,
                                        "operator": "and",
                                        "fields": [
                                            "option_name^6",
                                            "option_name.*^3.6",
                                            "option_description^1",
                                            "option_description.*^0.6",
                                            "flake_name^0.5",
                                            "flake_name.*^0.3"
                                        ]
                                    }},
                                    {"wildcard": {
                                        "option_name": {
                                            "value": f"*{query}*",
                                            "case_insensitive": True
                                        }
                                    }}
                                ]
                            }}
                        ]
                    }
                }
            }
            
            # For queries like services.postgresql, also add some specific queries
            if '.' in query:
                # Add a prefix search for child options
                search_body["query"]["bool"]["must"][0]["dis_max"]["queries"].append({
                    "prefix": {
                        "option_name.raw": {
                            "value": query + ".",
                            "boost": 5.0
                        }
                    }
                })
                
                # Get the last part (e.g., "postgresql" from "services.postgresql")
                service_name = query.split(".")[-1]
                search_body["query"]["bool"]["must"][0]["dis_max"]["queries"].append({
                    "wildcard": {
                        "option_name": {
                            "value": f"*{service_name}*",
                            "case_insensitive": True
                        }
                    }
                })
            
            # Make the request with proper auth - using the curl example approach
            print(f"Making direct API request for options with query: {query}")
            response = requests.post(
                self.es_url,
                json=search_body,
                auth=self.es_auth if self.es_auth else None,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                total_hits = result.get("hits", {}).get("total", {}).get("value", 0)
                print(f"Direct API search successful, got {total_hits} option results")
                
                # Process results into a consistent format
                options = []
                for hit in result.get("hits", {}).get("hits", []):
                    source = hit.get("_source", {})
                    options.append({
                        "name": source.get("option_name", ""),
                        "description": source.get("option_description", ""),
                        "type": source.get("option_type", ""),
                        "default": source.get("option_default", None),
                        "example": source.get("option_example", None),
                        "declared_by": source.get("option_declarations", []),
                        "score": hit.get("_score", 0),
                    })
                
                return options
            else:
                print(f"Direct API search failed with status {response.status_code}: {response.text}")
        
        except Exception as e:
            print(f"Error searching options: {e}")
        
        return []

    def get_package_by_attr(self, attr_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific package by its attribute name.

        Args:
            attr_name: The package attribute name

        Returns:
            Package dictionary or None if not found
        """
        if not self.es:
            print("Elasticsearch client not available, cannot get package")
            return None

        try:
            # Create an exact match query for the attribute name
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"package_attr_name.raw": attr_name}},
                            {"term": {"type": "package"}},
                        ]
                    }
                }
            }

            # Execute the search
            result = self.es.search(body=search_body, size=1)

            # If we found a match, return it
            if result["hits"]["total"]["value"] > 0:
                source = result["hits"]["hits"][0]["_source"]
                return {
                    "attribute": source.get("package_attr_name", ""),
                    "name": source.get("package_pname", ""),
                    "version": source.get("package_version", ""),
                    "description": source.get("package_description", ""),
                    "homepage": source.get("package_homepage", [None])[0],
                    "license": source.get("package_license", []),
                    "maintainers": source.get("package_maintainers", []),
                    "platforms": source.get("package_platforms", []),
                }

            return None

        except ApiError as e:
            print(f"Elasticsearch API error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in Elasticsearch get_package: {e}")
            return None


# NixOS API Implementation
class NixosAPI:
    """API client for NixOS packages and options using local Nix installation."""

    def __init__(self):
        """Initialize the NixOS API client."""
        self._check_nix_installation()
        # Initialize Elasticsearch client for direct API access
        self.es_client = ElasticsearchClient()

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
        self, query: str, channel: str = "unstable", limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search for NixOS packages using Elasticsearch API.

        Args:
            query: Search query string
            channel: NixOS channel to search
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            List of package dictionaries
        """
        packages = []

        # Skip empty queries
        if not query or query.strip() == "":
            return packages

        # Use Elasticsearch direct API
        if self.es_client.es:
            print(f"Searching packages with Elasticsearch: {query}")
            packages = self.es_client.search_packages(query, limit=limit, offset=offset)
            print(f"Found {len(packages)} packages using Elasticsearch")
        else:
            print("Elasticsearch client not available")

        return packages

    def get_package_metadata(self, attribute: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a specific package by attribute path."""
        # Use Elasticsearch for direct lookup
        if self.es_client.es:
            print(f"Getting package metadata with Elasticsearch: {attribute}")
            package = self.es_client.get_package_by_attr(attribute)
            if package:
                return package
            else:
                print("Package not found with Elasticsearch")

        return None

    def query_option(self, option_path: str) -> Optional[Dict[str, Any]]:
        """Query a NixOS option by path using Elasticsearch API.

        This will use Elasticsearch API to get NixOS option information.
        For option paths like services.postgresql, this will also return related options.
        """
        is_prefix_query = '.' in option_path
        
        try:
            import requests
            
            # First, try to get an exact match
            search_body = {
                "size": 1,
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"type": {"value": "option"}}}
                        ],
                        "must": [
                            {"term": {"option_name.raw": option_path}}
                        ]
                    }
                }
            }
            
            # Make the request with proper auth - using the curl example approach
            print(f"Making direct API request for exact option match: {option_path}")
            response = requests.post(
                self.es_client.es_url,
                json=search_body,
                auth=self.es_client.es_auth if self.es_client.es_auth else None,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                total_hits = result.get("hits", {}).get("total", {}).get("value", 0)
                
                # If we found an exact match, return it
                if total_hits > 0:
                    source = result["hits"]["hits"][0]["_source"]
                    return {
                        "name": source.get("option_name", ""),
                        "description": source.get("option_description", ""),
                        "type": source.get("option_type", ""),
                        "default": source.get("option_default", None),
                        "example": source.get("option_example", None),
                        "declared_by": source.get("option_declarations", []),
                    }
            
            # If we didn't find an exact match but it's a prefix query like services.postgresql,
            # search for all related options
            if is_prefix_query:
                print(f"No exact match found, searching for options related to: {option_path}")
                # Get all related options (using the search_options function)
                related_options = self.search_options(option_path, limit=50)
                
                if related_options:
                    # Format the response for an LLM with useful context
                    return {
                        "name": option_path,
                        "message": f"No exact match found for '{option_path}', but found {len(related_options)} related options.",
                        "related_options": related_options,
                        "note": "These are the available configuration options related to your query."
                    }
        
        except Exception as e:
            print(f"Error querying option: {e}")
        
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

        # Check if Nix is installed
        try:
            self.api._check_nix_installation()
        except RuntimeError:
            # Nix is not installed, return helpful information
            return {
                "error": "Nix is not installed on this system.",
                "name": package_name,
                "channel": channel,
                "message": "To use this endpoint, please install Nix: https://nixos.org/download.html",
            }

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

        # No results found, include helpful message
        if package_name == "python":
            return {
                "error": f"Package '{package_name}' not found in channel '{channel}'",
                "suggestions": [
                    "Try 'python3' instead of 'python'",
                    "Check that the channel is correctly specified",
                    "Use search to find similar packages",
                ],
            }

        return {
            "error": f"Package '{package_name}' not found in channel '{channel}'",
            "suggestions": [
                "Check the spelling of the package name",
                "Try searching with a partial name",
                "Verify the channel name is correct",
            ],
        }

    def search_packages(
        self, query: str, channel: str = "unstable", limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        """Search for NixOS packages matching a query string with pagination."""
        cache_key = f"search:{channel}:{query}:{limit}:{offset}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Check if Nix is installed
        try:
            self.api._check_nix_installation()
        except RuntimeError:
            # Nix is not installed, return helpful information
            return {
                "error": "Nix is not installed on this system.",
                "query": query,
                "channel": channel,
                "total": 0,
                "offset": offset,
                "limit": limit,
                "results": [],
                "message": "To use this endpoint, please install Nix: https://nixos.org/download.html",
            }

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

        # If no results, add helpful suggestions
        if not results:
            suggestions = [
                "Try using more general search terms",
                "Check the spelling of your search query",
                "Try searching in a different channel (e.g., unstable, 23.11)",
                "If you know the exact package name, try querying it directly",
            ]

            # Add specific suggestions for common searches
            if query.lower() == "python":
                suggestions.insert(0, "Try searching for 'python3' instead")
            elif query.lower() == "node" or query.lower() == "nodejs":
                suggestions.insert(0, "Try searching for 'nodejs' or 'nodejs_20'")

            search_result["suggestions"] = suggestions
            search_result["error"] = f"No packages found matching '{query}'"

        self.cache[cache_key] = search_result
        return search_result

    def query_option(
        self, option_name: str, channel: str = "unstable"
    ) -> Optional[Dict[str, Any]]:
        """Query details about a specific NixOS option."""
        cache_key = f"option:{channel}:{option_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Check if Nix is installed
        try:
            self.api._check_nix_installation()
        except RuntimeError:
            # Nix is not installed, return helpful information
            return {
                "error": "Nix is not installed on this system.",
                "name": option_name,
                "channel": channel,
                "message": "To use this endpoint, please install Nix: https://nixos.org/download.html",
            }

        option = self.api.query_option(option_name)
        if option:
            self.cache[cache_key] = option
            return option

        # Special case for service options like services.postgresql
        if option_name.startswith("services."):
            service_name = option_name.split(".", 1)[1]
            
            # Try to get related options for this service
            related_options = self.api.es_client.search_options(service_name, limit=10)
            
            # Check if we have an exact match in the related options
            exact_match = next((opt for opt in related_options if opt["name"] == option_name), None)
            # If we found an exact match, return it immediately
            if exact_match:
                return exact_match
                
            # Otherwise, filter to keep options that match the service name prefix
            matching_options = [opt for opt in related_options if opt["name"].startswith(option_name)]
            
            response = {
                "error": f"Option '{option_name}' not found",
                "name": option_name,
                "message": f"This appears to be a NixOS service configuration for '{service_name}'.",
                "hint": f"Try searching for specific configuration options like '{option_name}.enable' or '{option_name}.settings'",
                "try_search": f"To see all related options, try a search for '{service_name}' in NixOS options."
            }
            
            # If we found related options, include them in the response
            if matching_options:
                response["related_options"] = matching_options
                response["note"] = f"Found {len(matching_options)} related options for {option_name}."
            else:
                response["note"] = "The Elasticsearch API may not be properly configured, or this service might not be indexed."
                
            return response
            
        elif "." in option_name:
            # Other dotted option paths
            return {
                "error": f"Option '{option_name}' not found",
                "name": option_name,
                "hint": "This appears to be a NixOS option path, but no exact match was found.",
                "suggestion": "Try searching for related options by using a more general query.",
            }
        else:
            # Generic case
            return {
                "error": f"Option '{option_name}' not found",
                "suggestions": [
                    "Check the spelling of the option name",
                    "Verify that the option exists in the specified NixOS version",
                    "Try a more general search term to find related options",
                ],
            }


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


@app.get("/api/search/options/{query}")
async def search_options_direct(
    query: str, channel: str = "unstable", limit: int = 50, offset: int = 0
):
    """Direct endpoint for options search."""
    if not context.api.es_client.es:
        return {
            "error": "Elasticsearch client not available",
            "message": "The Elasticsearch API is required for option searching."
        }
    
    # Use the ElasticsearchClient.search_options method directly
    options = context.api.es_client.search_options(query, limit=limit, offset=offset)
    
    return {
        "query": query,
        "channel": channel,
        "total": len(options),
        "offset": offset,
        "limit": limit,
        "results": options,
    }


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

    # Check Elasticsearch status
    es_status = "unavailable"
    es_info = {}
    try:
        if context.api.es_client.es:
            es_info = context.api.es_client.es.info()
            if es_info:
                es_status = "connected"
    except Exception as e:
        es_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "timestamp": time.time(),
        "server": "NixMCP",
        "version": "0.1.0",
        "nix_installed": nix_installed,
        "elasticsearch": {
            "status": es_status,
            "url": os.getenv("ELASTICSEARCH_URL", "not configured"),
            "auth": (
                "configured" if os.getenv("ELASTICSEARCH_USER") else "not configured"
            ),
            "info": es_info,
        },
        "endpoints": {
            "mcp_resources": [
                "nixos://package/{package_name}",
                "nixos://package/{package_name}/{channel}",
                "nixos://option/{option_name}",
                "nixos://option/{option_name}/{channel}",
                "nixos://search/packages/{query}",
                "nixos://search/packages/{query}/{channel}",
                "nixos://search/options/{query}",
                "nixos://search/options/{query}/{channel}",
            ],
            "direct_api": [
                "/api/package/{package_name}[?channel={channel}]",
                "/api/search/packages/{query}[?channel={channel}&limit={limit}&offset={offset}]",
                "/api/search/options/{query}[?channel={channel}&limit={limit}&offset={offset}]",
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


# Register option search resource
@mcp.resource("nixos://search/options/{query}")
async def mcp_search_options(query: str):
    """MCP resource handler for searching NixOS options."""
    print(f"MCP: Searching options with query: {query}")
    
    if not context.api.es_client.es:
        return {
            "error": "Elasticsearch client not available",
            "message": "The Elasticsearch API is required for option searching."
        }
    
    # Search for options
    options = context.api.es_client.search_options(query, limit=50)
    
    return {
        "query": query,
        "total": len(options),
        "results": options,
    }


@mcp.resource("nixos://search/options/{query}/{channel}")
async def mcp_search_options_with_channel(query: str, channel: str):
    """MCP resource handler for searching NixOS options with specific channel."""
    print(f"MCP: Searching options with query: {query} in channel: {channel}")
    
    # Channel parameter is included for API consistency, but currently not used
    # for options search since the Elasticsearch index doesn't separate by channel
    return await mcp_search_options(query)


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

    # We've removed the direct-mcp endpoint to just use the standard MCP implementation

    # Let's implement a custom MCP resource endpoint that manually dispatches to our resource handlers
    @app.get("/mcp/resource")
    async def mcp_resource_endpoint(uri: str):
        """Standard MCP resource endpoint that manually dispatches to our resource handlers."""
        print(f"MCP resource endpoint access: {uri}")
        try:
            # Parse the URI and call the appropriate handler
            if uri.startswith("nixos://package/"):
                parts = uri.replace("nixos://package/", "").split("/")
                if len(parts) == 1:
                    return await get_package_resource(parts[0])
                elif len(parts) == 2:
                    return await get_package_resource_with_channel(parts[0], parts[1])
                
            elif uri.startswith("nixos://search/packages/"):
                parts = uri.replace("nixos://search/packages/", "").split("/")
                if len(parts) == 1:
                    return await search_packages_resource(parts[0])
                elif len(parts) == 2:
                    return await search_packages_resource_with_channel(parts[0], parts[1])
                
            elif uri.startswith("nixos://search/options/"):
                parts = uri.replace("nixos://search/options/", "").split("/")
                if len(parts) == 1:
                    return await mcp_search_options(parts[0])
                elif len(parts) == 2:
                    return await mcp_search_options_with_channel(parts[0], parts[1])
                
            elif uri.startswith("nixos://option/"):
                parts = uri.replace("nixos://option/", "").split("/")
                if len(parts) == 1:
                    return await get_option_resource(parts[0])
                elif len(parts) == 2:
                    return await get_option_resource_with_channel(parts[0], parts[1])
                
            return {"error": f"Unsupported URI format: {uri}"}
        except Exception as e:
            print(f"Error in MCP resource endpoint: {e}")
            return {"error": f"Error processing resource: {str(e)}"}

    # Configure and mount the MCP server
    try:
        # Make sure the resources actually got registered
        resource_count = len(mcp._resource_manager._resources)
        print(f"\nFound {resource_count} registered MCP resources")

        # Mount the FastMCP instance at /mcp (standard MCP path)
        app.mount("/mcp", mcp)

        print("Mounted MCP at /mcp")
        print("Added custom MCP endpoint at /mcp/resource")
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
        f"  - MCP URL: http://localhost:{port}/mcp/resource?uri=nixos://package/python"
    )
    print(
        f"  - MCP Package Search URL: http://localhost:{port}/mcp/resource?uri=nixos://search/packages/python"
    )
    print(
        f"  - MCP Option Search URL: http://localhost:{port}/mcp/resource?uri=nixos://search/options/postgresql"
    )
    print(f"  - REST API Package URL: http://localhost:{port}/api/package/python")
    print(f"  - REST API Option Search URL: http://localhost:{port}/api/search/options/postgresql")

    print(f"\nStarting NixMCP server on port {port}...")
    print(f"Access FastAPI docs at http://localhost:{port}/docs")
    print(f"Access MCP endpoints at http://localhost:{port}/mcp")

    uvicorn.run(
        "server:app", host="0.0.0.0", port=port, log_level="debug", reload=args.reload
    )
