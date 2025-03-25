#!/usr/bin/env python
"""
NixMCP Server - A MCP server for NixOS resources.

This implements a comprehensive FastMCP server that provides MCP resources and tools
for querying NixOS packages and options using the Model Context Protocol (MCP).
The server communicates via standard input/output streams using a JSON-based
message format, allowing seamless integration with MCP-compatible AI models.
"""

import os
import logging
import logging.handlers
import json
import time
from typing import Dict, Any
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

    # Add prompt to guide assistants on using the MCP tools
    mcp_server.prompt = """
    # NixOS MCP Guide
    
    This MCP provides tools to search and retrieve information about NixOS packages and system options.
    
    ## Available Tools
    
    - `nixos_search`: Search for packages, options, or programs
      - Example: `nixos_search(query="python", type="packages")`
      
    - `nixos_info`: Get detailed information about a package or option
      - Example: `nixos_info(name="firefox", type="package")`
      - Example: `nixos_info(name="services.postgresql.enable", type="option")`
      
    - `nixos_stats`: Get statistics about available NixOS packages
      - Example: `nixos_stats()`
    
    ## Search Tips
    
    - Wildcards are automatically added to search terms
    - For more specific searches, use explicit wildcards: `*term*`, `term*`, etc.
    - When searching for options related to a service, try patterns like `services.*name*`
    """

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


# Helper functions
def create_wildcard_query(query: str) -> str:
    """Create a wildcard query from a regular query string.

    Args:
        query: The original query string

    Returns:
        A query string with wildcards added
    """
    if " " in query:
        # For multi-word queries, add wildcards around each word
        words = query.split()
        wildcard_terms = [f"*{word}*" for word in words]
        return " ".join(wildcard_terms)
    else:
        # For single word queries, just wrap with wildcards
        return f"*{query}*"


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
def nixos_search(query: str, type: str = "packages", limit: int = 20) -> str:
    """
    Search for NixOS packages, options, or programs.

    Args:
        query: The search term
        type: What to search for - "packages", "options", or "programs"
        limit: Maximum number of results to return (default: 20)

    Returns:
        Results formatted as text
    """
    logger.info(f"Searching for {type} with query '{query}'")

    valid_types = ["packages", "options", "programs"]
    if type.lower() not in valid_types:
        return f"Error: Invalid type. Must be one of: {', '.join(valid_types)}"

    try:
        # Add wildcards if not present and not a special query
        if "*" not in query and ":" not in query:
            wildcard_query = create_wildcard_query(query)
            logger.info(f"Adding wildcards to query: {wildcard_query}")
            query = wildcard_query

        if type.lower() == "packages":
            results = model_context.search_packages(query, limit)
            packages = results.get("packages", [])

            if not packages:
                return f"No packages found for '{query}'."

            output = f"Found {len(packages)} packages for '{query}':\n\n"
            for pkg in packages:
                output += f"- {pkg.get('name', 'Unknown')}"
                if pkg.get("version"):
                    output += f" ({pkg.get('version')})"
                output += "\n"
                if pkg.get("description"):
                    output += f"  {pkg.get('description')}\n"
                output += "\n"

            return output

        elif type.lower() == "options":
            results = model_context.search_options(query, limit)
            options = results.get("options", [])

            if not options:
                return f"No options found for '{query}'."

            output = f"Found {len(options)} options for '{query}':\n\n"
            for opt in options:
                output += f"- {opt.get('name', 'Unknown')}\n"
                if opt.get("description"):
                    output += f"  {opt.get('description')}\n"
                if opt.get("type"):
                    output += f"  Type: {opt.get('type')}\n"
                output += "\n"

            return output

        else:  # programs
            results = model_context.search_programs(query, limit)
            packages = results.get("packages", [])

            if not packages:
                return f"No packages found providing programs matching '{query}'."

            output = f"Found {len(packages)} packages providing programs matching '{query}':\n\n"
            for pkg in packages:
                output += f"- {pkg.get('name', 'Unknown')}"
                if pkg.get("version"):
                    output += f" ({pkg.get('version')})"
                output += "\n"

                programs = pkg.get("programs", [])
                if programs:
                    output += f"  Programs: {', '.join(programs)}\n"

                if pkg.get("description"):
                    output += f"  {pkg.get('description')}\n"
                output += "\n"

            return output

    except Exception as e:
        logger.error(f"Error in nixos_search: {e}", exc_info=True)
        return f"Error performing search: {str(e)}"


@mcp.tool()
def nixos_info(name: str, type: str = "package") -> str:
    """
    Get detailed information about a NixOS package or option.

    Args:
        name: The name of the package or option
        type: Either "package" or "option"

    Returns:
        Detailed information formatted as text
    """
    logger.info(f"Getting {type} information for: {name}")

    if type.lower() not in ["package", "option"]:
        return "Error: 'type' must be 'package' or 'option'"

    try:
        if type.lower() == "package":
            info = model_context.get_package(name)

            if not info.get("found", False):
                return f"Package '{name}' not found."

            output = f"# {info.get('name', name)}\n\n"

            if info.get("version"):
                output += f"**Version:** {info.get('version')}\n"

            if info.get("description"):
                output += f"\n**Description:** {info.get('description')}\n"

            if info.get("longDescription"):
                output += f"\n**Long Description:**\n{info.get('longDescription')}\n"

            if info.get("homepage"):
                output += f"\n**Homepage:** {info.get('homepage')}\n"

            if info.get("license"):
                output += f"\n**License:** {info.get('license')}\n"

            if info.get("programs") and isinstance(info.get("programs"), list):
                programs = info.get("programs")
                if programs:
                    output += f"\n**Provided Programs:** {', '.join(programs)}\n"

            return output

        else:  # option
            info = model_context.get_option(name)

            if not info.get("found", False):
                return f"Option '{name}' not found."

            output = f"# {info.get('name', name)}\n\n"

            if info.get("description"):
                output += f"**Description:** {info.get('description')}\n\n"

            if info.get("type"):
                output += f"**Type:** {info.get('type')}\n"

            if info.get("default") is not None:
                output += f"**Default:** {info.get('default')}\n"

            if info.get("example"):
                output += f"\n**Example:**\n```nix\n{info.get('example')}\n```\n"

            return output

    except Exception as e:
        logger.error(f"Error getting {type} information: {e}", exc_info=True)
        return f"Error retrieving information: {str(e)}"


@mcp.tool()
def nixos_stats() -> str:
    """
    Get statistics about available NixOS packages.

    Returns:
        Statistics about NixOS packages
    """
    logger.info("Getting package statistics")

    try:
        results = model_context.get_package_stats()

        if "error" in results:
            return f"Error getting statistics: {results['error']}"

        aggregations = results.get("aggregations", {})

        if not aggregations:
            return "No statistics available"

        output = "# NixOS Package Statistics\n\n"

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
            output += "## Top 10 Licenses\n\n"
            for license in licenses:
                output += f"- {license.get('key', 'Unknown')}: {license.get('doc_count', 0)} packages\n"
            output += "\n"

        # Platform distribution
        platforms = aggregations.get("platforms", {}).get("buckets", [])
        if platforms:
            output += "## Top 10 Platforms\n\n"
            for platform in platforms:
                output += f"- {platform.get('key', 'Unknown')}: {platform.get('doc_count', 0)} packages\n"

        return output

    except Exception as e:
        logger.error(f"Error getting package statistics: {e}", exc_info=True)
        return f"Error retrieving statistics: {str(e)}"


if __name__ == "__main__":
    # This will start the server and keep it running
    try:
        logger.info("Starting NixMCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}", exc_info=True)
