#!/usr/bin/env python
"""
NixMCP Server - A MCP server for NixOS resources.

This implements a comprehensive FastMCP server that provides MCP resources and tools
for querying NixOS packages and options using the Model Context Protocol (MCP).
The server communicates via standard input/output streams using a JSON-based
message format, allowing seamless integration with MCP-compatible AI models.
"""

import os
import sys
import logging
import logging.handlers
import json
import time
import functools
from typing import Dict, List, Optional, Any, Union, Tuple
import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
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


# Simple in-memory cache implementation
class SimpleCache:
    """A simple in-memory cache with TTL expiration."""

    def __init__(self, max_size=1000, ttl=300):  # ttl in seconds
        """Initialize the cache with maximum size and TTL."""
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
        logger.info(f"Initialized cache with max_size={max_size}, ttl={ttl}s")

    def get(self, key):
        """Retrieve a value from the cache if it exists and is not expired."""
        if key not in self.cache:
            self.misses += 1
            return None

        timestamp, value = self.cache[key]
        if time.time() - timestamp > self.ttl:
            # Expired
            del self.cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return value

    def set(self, key, value):
        """Store a value in the cache with the current timestamp."""
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Simple eviction: remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][0])
            del self.cache[oldest_key]

        self.cache[key] = (time.time(), value)

    def clear(self):
        """Clear all cache entries."""
        self.cache = {}

    def get_stats(self):
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": (
                self.hits / (self.hits + self.misses)
                if (self.hits + self.misses) > 0
                else 0
            ),
        }


# Elasticsearch client for accessing NixOS resources
class ElasticsearchClient:
    """Enhanced client for accessing NixOS Elasticsearch API."""

    def __init__(self):
        """Initialize the Elasticsearch client with caching."""
        # Elasticsearch endpoints
        self.es_packages_url = (
            "https://search.nixos.org/backend/latest-42-nixos-unstable/_search"
        )
        self.es_options_url = (
            "https://search.nixos.org/backend/latest-42-nixos-unstable-options/_search"
        )

        # Authentication
        self.es_user = "aWVSALXpZv"
        self.es_password = "X8gPHnzL52wFEekuxsfQ9cSh"
        self.es_auth = (self.es_user, self.es_password)

        # AWS Elasticsearch endpoint (for reference)
        self.es_aws_endpoint = (
            "https://nixos-search-5886075189.us-east-1.bonsaisearch.net:443"
        )

        # Initialize cache
        self.cache = SimpleCache(max_size=500, ttl=600)  # 10 minutes TTL

        # Request timeout settings
        self.connect_timeout = 3.0  # seconds
        self.read_timeout = 10.0  # seconds

        # Retry settings
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

        logger.info("Elasticsearch client initialized with caching")

    def safe_elasticsearch_query(
        self, endpoint: str, query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an Elasticsearch query with robust error handling and retries."""
        cache_key = f"{endpoint}:{json.dumps(query_data)}"
        cached_result = self.cache.get(cache_key)

        if cached_result:
            logger.debug(f"Cache hit for query: {cache_key[:100]}...")
            return cached_result

        logger.debug(f"Cache miss for query: {cache_key[:100]}...")

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    endpoint,
                    json=query_data,
                    auth=self.es_auth,
                    headers={"Content-Type": "application/json"},
                    timeout=(self.connect_timeout, self.read_timeout),
                )

                # Handle different status codes
                if response.status_code == 400:
                    logger.warning(f"Bad query: {query_data}")
                    return {"error": "Invalid query syntax", "details": response.json()}
                elif response.status_code == 401 or response.status_code == 403:
                    logger.error("Authentication failure")
                    return {"error": "Authentication failed"}
                elif response.status_code >= 500:
                    logger.error(f"Elasticsearch server error: {response.status_code}")
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (
                            2**attempt
                        )  # Exponential backoff
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    return {"error": "Elasticsearch server error"}

                response.raise_for_status()
                result = response.json()

                # Cache successful result
                self.cache.set(cache_key, result)
                return result

            except requests.exceptions.ConnectionError:
                logger.error("Connection error")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return {"error": "Failed to connect to Elasticsearch"}
            except requests.exceptions.Timeout:
                logger.error("Request timeout")
                return {"error": "Request timed out"}
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                return {"error": f"Query error: {str(e)}"}

    def search_packages(
        self, query: str, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for NixOS packages with enhanced query handling and field boosting.

        Args:
            query: Search term
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            Dict containing search results and metadata
        """
        # Check if query contains wildcards
        if "*" in query:
            # Use wildcard query for explicit wildcard searches
            logger.info(f"Using wildcard query for package search: {query}")

            # Handle special case for queries like *term*
            if query.startswith("*") and query.endswith("*") and query.count("*") == 2:
                term = query.strip("*")
                logger.info(f"Optimizing *term* query to search for: {term}")

                request_data = {
                    "from": offset,
                    "size": limit,
                    "query": {
                        "bool": {
                            "should": [
                                # Contains match with high boost
                                {
                                    "wildcard": {
                                        "package_attr_name": {
                                            "value": f"*{term}*",
                                            "boost": 9,
                                        }
                                    }
                                },
                                {
                                    "wildcard": {
                                        "package_pname": {
                                            "value": f"*{term}*",
                                            "boost": 7,
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "package_description": {
                                            "query": term,
                                            "boost": 3,
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "package_programs": {"query": term, "boost": 6}
                                    }
                                },
                            ],
                            "minimum_should_match": 1,
                        }
                    },
                }
            else:
                # Standard wildcard query
                request_data = {
                    "from": offset,
                    "size": limit,
                    "query": {
                        "query_string": {
                            "query": query,
                            "fields": [
                                "package_attr_name^9",
                                "package_pname^7",
                                "package_description^3",
                                "package_programs^6",
                            ],
                            "analyze_wildcard": True,
                        }
                    },
                }
        else:
            # For non-wildcard searches, use a more refined approach with field boosting
            request_data = {
                "from": offset,
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            # Exact match with highest boost
                            {
                                "term": {
                                    "package_attr_name": {"value": query, "boost": 10}
                                }
                            },
                            {"term": {"package_pname": {"value": query, "boost": 8}}},
                            # Prefix match (starts with)
                            {
                                "prefix": {
                                    "package_attr_name": {"value": query, "boost": 7}
                                }
                            },
                            {"prefix": {"package_pname": {"value": query, "boost": 6}}},
                            # Contains match
                            {
                                "wildcard": {
                                    "package_attr_name": {
                                        "value": f"*{query}*",
                                        "boost": 5,
                                    }
                                }
                            },
                            {
                                "wildcard": {
                                    "package_pname": {"value": f"*{query}*", "boost": 4}
                                }
                            },
                            # Full-text search in description fields
                            {
                                "match": {
                                    "package_description": {"query": query, "boost": 3}
                                }
                            },
                            {
                                "match": {
                                    "package_longDescription": {
                                        "query": query,
                                        "boost": 1,
                                    }
                                }
                            },
                            # Program search
                            {
                                "match": {
                                    "package_programs": {"query": query, "boost": 6}
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                },
            }

        # Execute the query
        data = self.safe_elasticsearch_query(self.es_packages_url, request_data)

        # Check for errors
        if "error" in data:
            return data

        # Process the response
        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)

        packages = []
        for hit in hits:
            source = hit.get("_source", {})
            packages.append(
                {
                    "name": source.get("package_attr_name", ""),
                    "pname": source.get("package_pname", ""),
                    "version": source.get("package_version", ""),
                    "description": source.get("package_description", ""),
                    "channel": source.get("package_channel", ""),
                    "score": hit.get("_score", 0),
                    "programs": source.get("package_programs", []),
                }
            )

        return {
            "count": total,
            "packages": packages,
        }

    def search_options(
        self, query: str, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for NixOS options with enhanced query handling.

        Args:
            query: Search term
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            Dict containing search results and metadata
        """
        # Check if query contains wildcards
        if "*" in query:
            # Use wildcard query for explicit wildcard searches
            logger.info(f"Using wildcard query for option search: {query}")

            # Handle special case for queries like *term*
            if query.startswith("*") and query.endswith("*") and query.count("*") == 2:
                term = query.strip("*")
                logger.info(f"Optimizing *term* query to search for: {term}")

                request_data = {
                    "from": offset,
                    "size": limit,
                    "query": {
                        "bool": {
                            "should": [
                                # Contains match with high boost
                                {
                                    "wildcard": {
                                        "option_name": {
                                            "value": f"*{term}*",
                                            "boost": 9,
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "option_description": {
                                            "query": term,
                                            "boost": 3,
                                        }
                                    }
                                },
                            ],
                            "minimum_should_match": 1,
                        }
                    },
                }
            else:
                # Standard wildcard query
                request_data = {
                    "from": offset,
                    "size": limit,
                    "query": {
                        "query_string": {
                            "query": query,
                            "fields": ["option_name^9", "option_description^3"],
                            "analyze_wildcard": True,
                        }
                    },
                }
        else:
            # For non-wildcard searches, use a more refined approach with field boosting
            request_data = {
                "from": offset,
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            # Exact match with high boost
                            {"term": {"option_name": {"value": query, "boost": 10}}},
                            # Prefix match for option names
                            {"prefix": {"option_name": {"value": query, "boost": 6}}},
                            # Contains match for option names
                            {
                                "wildcard": {
                                    "option_name": {"value": f"*{query}*", "boost": 4}
                                }
                            },
                            # Full-text search in description
                            {
                                "match": {
                                    "option_description": {"query": query, "boost": 2}
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                },
            }

        # Execute the query
        data = self.safe_elasticsearch_query(self.es_options_url, request_data)

        # Check for errors
        if "error" in data:
            return data

        # Process the response
        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)

        options = []
        for hit in hits:
            source = hit.get("_source", {})
            options.append(
                {
                    "name": source.get("option_name", ""),
                    "description": source.get("option_description", ""),
                    "type": source.get("option_type", ""),
                    "default": source.get("option_default", ""),
                    "score": hit.get("_score", 0),
                }
            )

        return {
            "count": total,
            "options": options,
        }

    def search_programs(
        self, program: str, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for packages that provide specific programs.

        Args:
            program: Program name to search for
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            Dict containing search results and metadata
        """
        logger.info(f"Searching for packages providing program: {program}")

        # Check if program contains wildcards
        if "*" in program:
            request_data = {
                "from": offset,
                "size": limit,
                "query": {"wildcard": {"package_programs": {"value": program}}},
            }
        else:
            request_data = {
                "from": offset,
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "term": {
                                    "package_programs": {"value": program, "boost": 10}
                                }
                            },
                            {
                                "prefix": {
                                    "package_programs": {"value": program, "boost": 5}
                                }
                            },
                            {
                                "wildcard": {
                                    "package_programs": {
                                        "value": f"*{program}*",
                                        "boost": 3,
                                    }
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                },
            }

        # Execute the query
        data = self.safe_elasticsearch_query(self.es_packages_url, request_data)

        # Check for errors
        if "error" in data:
            return data

        # Process the response
        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)

        packages = []
        for hit in hits:
            source = hit.get("_source", {})
            programs = source.get("package_programs", [])

            # Filter to only include matching programs in the result
            matching_programs = []
            if isinstance(programs, list):
                if "*" in program:
                    # For wildcard searches, use simple string matching
                    wild_pattern = program.replace("*", "")
                    matching_programs = [p for p in programs if wild_pattern in p]
                else:
                    # For exact searches, look for exact/partial matches
                    matching_programs = [
                        p for p in programs if program == p or program in p
                    ]

            packages.append(
                {
                    "name": source.get("package_attr_name", ""),
                    "version": source.get("package_version", ""),
                    "description": source.get("package_description", ""),
                    "programs": matching_programs,
                    "all_programs": programs,
                    "score": hit.get("_score", 0),
                }
            )

        return {
            "count": total,
            "packages": packages,
        }

    def search_packages_with_version(
        self, query: str, version_pattern: str, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for packages with a specific version pattern.

        Args:
            query: Package search term
            version_pattern: Version pattern to filter by (e.g., "1.*")
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            Dict containing search results and metadata
        """
        logger.info(
            f"Searching for packages matching '{query}' with version '{version_pattern}'"
        )

        request_data = {
            "from": offset,
            "size": limit,
            "query": {
                "bool": {
                    "must": [
                        # Basic package search
                        {
                            "bool": {
                                "should": [
                                    {
                                        "term": {
                                            "package_attr_name": {
                                                "value": query,
                                                "boost": 10,
                                            }
                                        }
                                    },
                                    {
                                        "wildcard": {
                                            "package_attr_name": {
                                                "value": f"*{query}*",
                                                "boost": 5,
                                            }
                                        }
                                    },
                                    {
                                        "match": {
                                            "package_description": {
                                                "query": query,
                                                "boost": 2,
                                            }
                                        }
                                    },
                                ],
                                "minimum_should_match": 1,
                            }
                        },
                        # Version filter
                        {"wildcard": {"package_version": version_pattern}},
                    ]
                }
            },
        }

        # Execute the query
        data = self.safe_elasticsearch_query(self.es_packages_url, request_data)

        # Check for errors
        if "error" in data:
            return data

        # Process the response
        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)

        packages = []
        for hit in hits:
            source = hit.get("_source", {})
            packages.append(
                {
                    "name": source.get("package_attr_name", ""),
                    "version": source.get("package_version", ""),
                    "description": source.get("package_description", ""),
                    "channel": source.get("package_channel", ""),
                    "score": hit.get("_score", 0),
                }
            )

        return {
            "count": total,
            "packages": packages,
        }

    def advanced_query(
        self, index_type: str, query_string: str, limit: int = 50, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Execute an advanced query using Elasticsearch's query string syntax.

        Args:
            index_type: Either "packages" or "options"
            query_string: Elasticsearch query string syntax
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            Dict containing search results and metadata
        """
        logger.info(f"Executing advanced query on {index_type}: {query_string}")

        # Determine the endpoint
        if index_type.lower() == "options":
            endpoint = self.es_options_url
        else:
            endpoint = self.es_packages_url

        request_data = {
            "from": offset,
            "size": limit,
            "query": {
                "query_string": {"query": query_string, "default_operator": "AND"}
            },
        }

        # Execute the query
        return self.safe_elasticsearch_query(endpoint, request_data)

    def get_package_stats(self, query: str = "*") -> Dict[str, Any]:
        """
        Get statistics about NixOS packages.

        Args:
            query: Optional query to filter packages

        Returns:
            Dict containing aggregation statistics
        """
        logger.info(f"Getting package statistics for query: {query}")

        request_data = {
            "size": 0,  # We only need aggregations, not actual hits
            "query": {"query_string": {"query": query}},
            "aggs": {
                "channels": {"terms": {"field": "package_channel", "size": 10}},
                "licenses": {"terms": {"field": "package_license", "size": 10}},
                "platforms": {"terms": {"field": "package_platforms", "size": 10}},
            },
        }

        # Execute the query
        return self.safe_elasticsearch_query(self.es_packages_url, request_data)

    def get_package(self, package_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific package.

        Args:
            package_name: Name of the package

        Returns:
            Dict containing package details
        """
        logger.info(f"Getting detailed information for package: {package_name}")

        # Build a query to find the exact package by name
        request_data = {
            "size": 1,  # We only need one result
            "query": {
                "bool": {"must": [{"term": {"package_attr_name": package_name}}]}
            },
        }

        # Execute the query
        data = self.safe_elasticsearch_query(self.es_packages_url, request_data)

        # Check for errors
        if "error" in data:
            return {"name": package_name, "error": data["error"], "found": False}

        # Process the response
        hits = data.get("hits", {}).get("hits", [])

        if not hits:
            logger.warning(f"Package {package_name} not found")
            return {"name": package_name, "error": "Package not found", "found": False}

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
            "programs": source.get("package_programs", []),
            "found": True,
        }

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific NixOS option.

        Args:
            option_name: Name of the option

        Returns:
            Dict containing option details
        """
        logger.info(f"Getting detailed information for option: {option_name}")

        # Build a query to find the exact option by name
        request_data = {
            "size": 1,  # We only need one result
            "query": {"bool": {"must": [{"term": {"option_name": option_name}}]}},
        }

        # Execute the query
        data = self.safe_elasticsearch_query(self.es_options_url, request_data)

        # Check for errors
        if "error" in data:
            return {"name": option_name, "error": data["error"], "found": False}

        # Process the response
        hits = data.get("hits", {}).get("hits", [])

        if not hits:
            logger.warning(f"Option {option_name} not found")
            return {"name": option_name, "error": "Option not found", "found": False}

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
            "found": True,
        }


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
            "description": "NixOS HTTP-based Model Context Protocol Server",
            "server_type": "http",
            "cache_stats": self.es_client.cache.get_stats(),
        }

    def get_package(self, package_name: str) -> Dict[str, Any]:
        """Get information about a NixOS package."""
        return self.es_client.get_package(package_name)

    def search_packages(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS packages."""
        return self.es_client.search_packages(query, limit)

    def search_options(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS options."""
        return self.es_client.search_options(query, limit)

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get information about a NixOS option."""
        return self.es_client.get_option(option_name)

    def search_programs(self, program: str, limit: int = 10) -> Dict[str, Any]:
        """Search for packages that provide specific programs."""
        return self.es_client.search_programs(program, limit)

    def search_packages_with_version(
        self, query: str, version_pattern: str, limit: int = 10
    ) -> Dict[str, Any]:
        """Search for packages with a specific version pattern."""
        return self.es_client.search_packages_with_version(
            query, version_pattern, limit
        )

    def advanced_query(
        self, index_type: str, query_string: str, limit: int = 10
    ) -> Dict[str, Any]:
        """Execute an advanced query using Elasticsearch's query string syntax."""
        return self.es_client.advanced_query(index_type, query_string, limit)

    def get_package_stats(self, query: str = "*") -> Dict[str, Any]:
        """Get statistics about NixOS packages."""
        return self.es_client.get_package_stats(query)


# Define the lifespan context manager for app initialization
@asynccontextmanager
async def app_lifespan(mcp_server: FastMCP):
    logger.info("Initializing NixMCP server")
    # Set up resources
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
    description="NixOS HTTP-based Model Context Protocol Server",
    lifespan=app_lifespan,
)

# No need for a get_tool method as we're importing tools directly


# Define MCP resources for packages
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


@mcp.resource("nixos://search/programs/{program}")
def search_programs_resource(program: str):
    """Search for packages that provide specific programs."""
    logger.info(f"Handling program search request for {program}")
    return model_context.search_programs(program)


@mcp.resource("nixos://packages/stats")
def package_stats_resource():
    """Get statistics about NixOS packages."""
    logger.info("Handling package statistics resource request")
    return model_context.get_package_stats()


# Add MCP tools for searching and retrieving information
@mcp.tool()
def search_nixos(query: str, search_type: str = "packages", limit: int = 10) -> str:
    """
    Search for NixOS packages or options.

    Args:
        query: The search term
        search_type: Type of search - either "packages", "options", or "programs"
        limit: Maximum number of results to return (default: 10)

    Returns:
        Results formatted as text
    """
    logger.info(f"Searching for {search_type} with query '{query}'")

    valid_types = ["packages", "options", "programs"]
    if search_type.lower() not in valid_types:
        return f"Error: Invalid search_type. Must be one of: {', '.join(valid_types)}"

    try:
        # First try the original query as-is
        if search_type.lower() == "packages":
            logger.info(f"Trying original query first: {query}")
            results = model_context.search_packages(query, limit)
            packages = results.get("packages", [])

            # If no results with original query and it doesn't already have wildcards,
            # try with wildcards
            if not packages and "*" not in query:
                # Create wildcard query
                if " " in query:
                    # For multi-word queries, add wildcards around each word
                    words = query.split()
                    wildcard_terms = [f"*{word}*" for word in words]
                    wildcard_query = " ".join(wildcard_terms)
                else:
                    # For single word queries, just wrap with wildcards
                    wildcard_query = f"*{query}*"

                logger.info(
                    f"No results with original query, trying wildcard search: {wildcard_query}"
                )
                results = model_context.search_packages(wildcard_query, limit)
                packages = results.get("packages", [])

                # If we got results with wildcards, note this in the output
                if packages:
                    logger.info(f"Found {len(packages)} results using wildcard search")

            if not packages:
                return f"No packages found for query: '{query}'\n\nTry using wildcards like *{query}* for broader results."

            # Create a flag to track if wildcards were automatically used
            used_wildcards = False
            if packages and "*" not in query and "wildcard_query" in locals():
                used_wildcards = True

            # Indicate if wildcards were used to find results
            if "*" in query:
                output = (
                    f"Found {len(packages)} packages for wildcard query '{query}':\n\n"
                )
            elif used_wildcards:
                output = f"Found {len(packages)} packages using automatic wildcard search for '{query}':\n\nNote: No exact matches were found, so wildcards were automatically added.\n\n"
            else:
                output = f"Found {len(packages)} packages for '{query}':\n\n"
            for pkg in packages:
                output += f"- {pkg.get('name', 'Unknown')}"
                if pkg.get("version"):
                    output += f" ({pkg.get('version')})"
                output += "\n"
                if pkg.get("description"):
                    output += f"  {pkg.get('description')}\n"
                if pkg.get("channel"):
                    output += f"  Channel: {pkg.get('channel')}\n"
                output += "\n"

            return output

        elif search_type.lower() == "options":
            # First try the original query as-is
            logger.info(f"Trying original query first: {query}")
            results = model_context.search_options(query, limit)
            options = results.get("options", [])

            # If no results with original query and it doesn't already have wildcards,
            # try with wildcards
            if not options and "*" not in query:
                # Create wildcard query
                if " " in query:
                    # For multi-word queries, add wildcards around each word
                    words = query.split()
                    wildcard_terms = [f"*{word}*" for word in words]
                    wildcard_query = " ".join(wildcard_terms)
                else:
                    # For single word queries, just wrap with wildcards
                    wildcard_query = f"*{query}*"

                logger.info(
                    f"No results with original query, trying wildcard search: {wildcard_query}"
                )
                results = model_context.search_options(wildcard_query, limit)
                options = results.get("options", [])

                # If we got results with wildcards, note this in the output
                if options:
                    logger.info(f"Found {len(options)} results using wildcard search")

            if not options:
                return f"No options found for query: '{query}'\n\nTry using wildcards like *{query}* for broader results."

            # Create a flag to track if wildcards were automatically used
            used_wildcards = False
            if options and "*" not in query and "wildcard_query" in locals():
                used_wildcards = True

            # Indicate if wildcards were used to find results
            if "*" in query:
                output = (
                    f"Found {len(options)} options for wildcard query '{query}':\n\n"
                )
            elif used_wildcards:
                output = f"Found {len(options)} options using automatic wildcard search for '{query}':\n\nNote: No exact matches were found, so wildcards were automatically added.\n\n"
            else:
                output = f"Found {len(options)} options for '{query}':\n\n"
            for opt in options:
                output += f"- {opt.get('name', 'Unknown')}\n"
                if opt.get("description"):
                    output += f"  {opt.get('description')}\n"
                if opt.get("type"):
                    output += f"  Type: {opt.get('type')}\n"
                if "default" in opt:
                    output += f"  Default: {opt.get('default')}\n"
                output += "\n"

            return output

        else:  # programs
            results = model_context.search_programs(query, limit)
            packages = results.get("packages", [])

            if not packages:
                return f"No packages found providing programs matching: '{query}'\n\nTry using wildcards like *{query}* for broader results."

            output = f"Found {len(packages)} packages providing programs matching '{query}':\n\n"

            for pkg in packages:
                output += f"- {pkg.get('name', 'Unknown')}"
                if pkg.get("version"):
                    output += f" ({pkg.get('version')})"
                output += "\n"

                # List matching programs
                matching_programs = pkg.get("programs", [])
                if matching_programs:
                    output += f"  Programs: {', '.join(matching_programs)}\n"

                if pkg.get("description"):
                    output += f"  {pkg.get('description')}\n"
                output += "\n"

            return output

    except Exception as e:
        logger.error(f"Error in search_nixos: {e}", exc_info=True)
        error_message = f"Error performing search for '{query}': {str(e)}"

        # Add helpful suggestions based on the error
        if "ConnectionError" in str(e) or "ConnectionTimeout" in str(e):
            error_message += "\n\nThere seems to be a connection issue with the Elasticsearch server. Please try again later."
        elif "AuthenticationException" in str(e):
            error_message += "\n\nAuthentication failed. Please check your Elasticsearch credentials."
        else:
            error_message += "\n\nTry simplifying your query or using wildcards like *term* for broader results."

        return error_message


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

        if package_info.get("version"):
            output += f"**Version:** {package_info.get('version')}\n"

        if package_info.get("description"):
            output += f"\n**Description:** {package_info.get('description')}\n"

        if package_info.get("longDescription"):
            output += (
                f"\n**Long Description:**\n{package_info.get('longDescription')}\n"
            )

        if package_info.get("license"):
            output += f"\n**License:** {package_info.get('license')}\n"

        if package_info.get("homepage"):
            output += f"\n**Homepage:** {package_info.get('homepage')}\n"

        if package_info.get("maintainers"):
            maintainers = package_info.get("maintainers")
            if isinstance(maintainers, list) and maintainers:
                # Convert any dictionary items to strings
                maintainer_strings = []
                for m in maintainers:
                    if isinstance(m, dict):
                        if "name" in m:
                            maintainer_strings.append(m["name"])
                        elif "email" in m:
                            maintainer_strings.append(m["email"])
                        else:
                            maintainer_strings.append(str(m))
                    else:
                        maintainer_strings.append(str(m))
                output += f"\n**Maintainers:** {', '.join(maintainer_strings)}\n"

        if package_info.get("platforms"):
            platforms = package_info.get("platforms")
            if isinstance(platforms, list) and platforms:
                # Convert any dictionary or complex items to strings
                platform_strings = [str(p) for p in platforms]
                output += f"\n**Platforms:** {', '.join(platform_strings)}\n"

        if package_info.get("channel"):
            output += f"\n**Channel:** {package_info.get('channel')}\n"

        # Add programs if available
        if package_info.get("programs"):
            programs = package_info.get("programs")
            if isinstance(programs, list) and programs:
                output += f"\n**Provided Programs:** {', '.join(programs)}\n"

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

        if option_info.get("description"):
            output += f"**Description:** {option_info.get('description')}\n\n"

        if option_info.get("type"):
            output += f"**Type:** {option_info.get('type')}\n"

        if option_info.get("default") is not None:
            output += f"**Default:** {option_info.get('default')}\n"

        if option_info.get("example"):
            output += f"\n**Example:**\n```nix\n{option_info.get('example')}\n```\n"

        if option_info.get("declarations"):
            declarations = option_info.get("declarations")
            if isinstance(declarations, list) and declarations:
                output += f"\n**Declared in:**\n"
                for decl in declarations:
                    output += f"- {decl}\n"

        if option_info.get("readOnly"):
            output += f"\n**Read Only:** Yes\n"

        return output

    except Exception as e:
        logger.error(f"Error getting option information: {e}")
        return f"Error getting information for option '{option_name}': {str(e)}"


@mcp.tool()
def advanced_search(
    query_string: str, index_type: str = "packages", limit: int = 20
) -> str:
    """
    Perform an advanced search using Elasticsearch's query string syntax.

    Args:
        query_string: Elasticsearch query string (e.g. "package_programs:(python OR ruby)")
        index_type: Type of index to search ("packages" or "options")
        limit: Maximum number of results to return

    Returns:
        Search results formatted as text
    """
    logger.info(f"Performing advanced query string search: {query_string}")

    if index_type.lower() not in ["packages", "options"]:
        return f"Error: Invalid index_type. Must be 'packages' or 'options'."

    try:
        results = model_context.advanced_query(index_type, query_string, limit)

        # Check for errors
        if "error" in results:
            return f"Error executing query: {results['error']}"

        hits = results.get("hits", {}).get("hits", [])
        total = results.get("hits", {}).get("total", {}).get("value", 0)

        if not hits:
            return f"No results found for query: '{query_string}'"

        output = f"Found {total} results for query '{query_string}' (showing top {len(hits)}):\n\n"

        for hit in hits:
            source = hit.get("_source", {})
            score = hit.get("_score", 0)

            if index_type.lower() == "packages":
                # Format package result
                name = source.get("package_attr_name", "Unknown")
                version = source.get("package_version", "")
                description = source.get("package_description", "")

                output += f"- {name}"
                if version:
                    output += f" ({version})"
                output += f" [score: {score:.2f}]\n"
                if description:
                    output += f"  {description}\n"
            else:
                # Format option result
                name = source.get("option_name", "Unknown")
                description = source.get("option_description", "")

                output += f"- {name} [score: {score:.2f}]\n"
                if description:
                    output += f"  {description}\n"

            output += "\n"

        return output

    except Exception as e:
        logger.error(f"Error in advanced_search: {e}", exc_info=True)
        return f"Error performing advanced search: {str(e)}"


@mcp.tool()
def package_statistics(query: str = "*") -> str:
    """
    Get statistics about NixOS packages matching the query.

    Args:
        query: Search query (default: all packages)

    Returns:
        Statistics about matching packages
    """
    logger.info(f"Getting package statistics for query: {query}")

    try:
        results = model_context.get_package_stats(query)

        # Check for errors
        if "error" in results:
            return f"Error getting statistics: {results['error']}"

        # Extract aggregations
        aggregations = results.get("aggregations", {})

        if not aggregations:
            return "No statistics available"

        output = f"# NixOS Package Statistics\n\n"

        # Channel distribution
        channels = aggregations.get("channels", {}).get("buckets", [])
        if channels:
            output += "## Distribution by Channel\n\n"
            for channel in channels:
                output += f"- {channel.get('key', 'Unknown')}: {channel.get('doc_count', 0)} packages\n"
            output += "\n"

        # License distribution
        licenses = aggregations.get("licenses", {}).get("buckets", [])
        if licenses:
            output += "## Distribution by License\n\n"
            for license in licenses:
                output += f"- {license.get('key', 'Unknown')}: {license.get('doc_count', 0)} packages\n"
            output += "\n"

        # Platform distribution
        platforms = aggregations.get("platforms", {}).get("buckets", [])
        if platforms:
            output += "## Distribution by Platform\n\n"
            for platform in platforms:
                output += f"- {platform.get('key', 'Unknown')}: {platform.get('doc_count', 0)} packages\n"
            output += "\n"

        # Add cache statistics
        cache_stats = model_context.es_client.cache.get_stats()
        output += "## Cache Statistics\n\n"
        output += (
            f"- Cache size: {cache_stats['size']}/{cache_stats['max_size']} entries\n"
        )
        output += f"- Hit ratio: {cache_stats['hit_ratio']*100:.1f}% ({cache_stats['hits']} hits, {cache_stats['misses']} misses)\n"

        return output

    except Exception as e:
        logger.error(f"Error getting package statistics: {e}", exc_info=True)
        return f"Error getting package statistics: {str(e)}"


@mcp.tool()
def version_search(package_query: str, version_pattern: str, limit: int = 10) -> str:
    """
    Search for packages matching a specific version pattern.

    Args:
        package_query: Package search term
        version_pattern: Version pattern to filter by (e.g., "1.*")
        limit: Maximum number of results to return

    Returns:
        Search results formatted as text
    """
    logger.info(
        f"Searching for packages matching '{package_query}' with version '{version_pattern}'"
    )

    try:
        results = model_context.search_packages_with_version(
            package_query, version_pattern, limit
        )

        # Check for errors
        if "error" in results:
            return f"Error searching packages: {results['error']}"

        packages = results.get("packages", [])
        total = results.get("count", 0)

        if not packages:
            return f"No packages found matching '{package_query}' with version pattern '{version_pattern}'"

        output = f"Found {total} packages matching '{package_query}' with version pattern '{version_pattern}' (showing top {len(packages)}):\n\n"

        for pkg in packages:
            output += (
                f"- {pkg.get('name', 'Unknown')} ({pkg.get('version', 'Unknown')})\n"
            )
            if pkg.get("description"):
                output += f"  {pkg.get('description')}\n"
            if pkg.get("channel"):
                output += f"  Channel: {pkg.get('channel')}\n"
            output += "\n"

        return output

    except Exception as e:
        logger.error(f"Error in version_search: {e}", exc_info=True)
        return f"Error searching packages with version pattern: {str(e)}"


if __name__ == "__main__":
    # This will start the server and keep it running
    try:
        logger.info("Starting NixMCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}", exc_info=True)
