"""
NixOS-specific completion implementations.

This module provides completion handlers for NixOS packages, options, and tools.
"""

import logging
import re
from typing import Dict, List, Any

from nixmcp.completions.utils import create_completion_item

# Get logger
logger = logging.getLogger("nixmcp")


async def complete_nixos_package_name(
    partial_name: str, es_client: Any, is_search: bool = False
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete NixOS package names based on partial input.

    Args:
        partial_name: Partial package name to complete
        es_client: Elasticsearch client for querying package data
        is_search: Whether this is a search query parameter (affects return format)

    Returns:
        Dictionary with completion items
    """
    logger.info(f"Completing NixOS package name: {partial_name}")

    if not partial_name:
        # For empty prefix, return some popular packages as examples
        popular_packages = ["firefox", "python", "vscode", "git", "nodejs", "nginx", "postgresql"]
        if is_search:
            items = [create_completion_item(pkg, pkg, f"Search for {pkg} packages") for pkg in popular_packages]
            return {"items": items}
        else:
            items = [create_completion_item(pkg, pkg, f"The {pkg} package") for pkg in popular_packages]
            return {"items": items}

    # Create a special completion query with prefix boost and a small result limit
    request_data = {
        "size": 10,  # Limit results for faster response
        "query": {
            "bool": {
                "should": [
                    # Exact match with highest boost
                    {"term": {"package_attr_name": {"value": partial_name, "boost": 15}}},
                    # Prefix match with high boost
                    {"prefix": {"package_attr_name": {"value": partial_name, "boost": 10}}},
                    # Prefix match on package name
                    {"prefix": {"package_pname": {"value": partial_name, "boost": 8}}},
                    # Contains match with lower boost
                    {"wildcard": {"package_attr_name": {"value": f"*{partial_name}*", "boost": 5}}},
                    {"wildcard": {"package_pname": {"value": f"*{partial_name}*", "boost": 3}}},
                ],
                "minimum_should_match": 1,
            }
        },
    }

    # Execute the query using the safe_elasticsearch_query method from the Elasticsearch client
    endpoint = es_client.es_packages_url
    result = es_client.safe_elasticsearch_query(endpoint, request_data)

    # Extract hits from the response
    hits = result.get("hits", {}).get("hits", [])

    # Convert hits to completion items
    items = []
    for hit in hits[:10]:  # Limit to 10 items max
        source = hit.get("_source", {})
        name = source.get("package_attr_name", "")
        description = source.get("package_description", "")

        if is_search:
            # For search completions, keep the URI format
            items.append(create_completion_item(name, name, description[:100] if description else ""))
        else:
            # For package resource completions, use the full name
            items.append(create_completion_item(name, name, description[:100] if description else ""))

    return {"items": items}


async def complete_nixos_option_name(
    partial_name: str, es_client: Any, is_search: bool = False
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete NixOS option names based on partial input.

    Args:
        partial_name: Partial option name to complete
        es_client: Elasticsearch client for querying option data
        is_search: Whether this is a search query parameter (affects return format)

    Returns:
        Dictionary with completion items
    """
    logger.info(f"Completing NixOS option name: {partial_name}")

    if not partial_name:
        # For empty prefix, return some common option categories
        common_options = [
            "services",
            "networking",
            "boot",
            "users",
            "environment",
            "hardware",
            "systemd",
            "security",
            "virtualisation",
            "fonts",
        ]
        items = [create_completion_item(opt, opt, f"NixOS {opt} options") for opt in common_options]
        return {"items": items}

    # Special handling for hierarchical paths
    if "." in partial_name:
        # For service paths, provide specialized completion
        if partial_name.startswith("services."):
            parts = partial_name.split(".")
            service_base = ".".join(parts[:2])  # services.servicename

            # Create a query that finds options with this service prefix
            request_data = {
                "size": 10,
                "query": {
                    "bool": {
                        "filter": [{"term": {"type": {"value": "option"}}}],
                        "must": [{"prefix": {"option_name": {"value": service_base}}}],
                    }
                },
            }
        else:
            # For other hierarchical paths, use a general prefix query
            request_data = {
                "size": 10,
                "query": {
                    "bool": {
                        "filter": [{"term": {"type": {"value": "option"}}}],
                        "must": [{"prefix": {"option_name": {"value": partial_name}}}],
                    }
                },
            }
    else:
        # For non-hierarchical paths, use a more flexible query
        request_data = {
            "size": 10,
            "query": {
                "bool": {
                    "filter": [{"term": {"type": {"value": "option"}}}],
                    "should": [
                        # Exact match
                        {"term": {"option_name": {"value": partial_name, "boost": 10}}},
                        # Prefix match
                        {"prefix": {"option_name": {"value": partial_name, "boost": 8}}},
                        # Contains match
                        {"wildcard": {"option_name": {"value": f"*{partial_name}*", "boost": 5}}},
                    ],
                    "minimum_should_match": 1,
                }
            },
        }

    # Execute the query
    endpoint = es_client.es_options_url
    result = es_client.safe_elasticsearch_query(endpoint, request_data)

    # Extract hits from the response
    hits = result.get("hits", {}).get("hits", [])

    # Convert hits to completion items
    items = []
    for hit in hits[:10]:  # Limit to 10 items max
        source = hit.get("_source", {})
        name = source.get("option_name", "")
        description = source.get("option_description", "")
        option_type = source.get("option_type", "")

        if is_search:
            # For search completions, keep the URI format
            items.append(
                create_completion_item(name, name, f"{option_type}: {description[:80] if description else ''}")
            )
        else:
            # For option resource completions, use the full name
            items.append(
                create_completion_item(name, name, f"{option_type}: {description[:80] if description else ''}")
            )

    return {"items": items}


async def complete_nixos_program_name(partial_name: str, es_client: Any) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete program names for NixOS program search.

    Args:
        partial_name: Partial program name to complete
        es_client: Elasticsearch client for querying package data

    Returns:
        Dictionary with completion items
    """
    logger.info(f"Completing NixOS program name: {partial_name}")

    if not partial_name:
        # For empty prefix, return some common executable names
        common_programs = ["python", "git", "npm", "cargo", "docker", "firefox", "code"]
        items = [
            create_completion_item(prog, prog, f"Search for packages providing '{prog}'") for prog in common_programs
        ]
        return {"items": items}

    # Query for programs that match the partial name
    request_data = {
        "size": 10,
        "query": {
            "bool": {
                "should": [
                    # Exact match
                    {"term": {"package_programs": {"value": partial_name, "boost": 10}}},
                    # Prefix match
                    {"prefix": {"package_programs": {"value": partial_name, "boost": 8}}},
                    # Contains match
                    {"wildcard": {"package_programs": {"value": f"*{partial_name}*", "boost": 5}}},
                ],
                "minimum_should_match": 1,
            }
        },
        "aggs": {
            "unique_programs": {
                "terms": {"field": "package_programs", "include": f".*{re.escape(partial_name)}.*", "size": 10}
            }
        },
    }

    # Execute the query
    endpoint = es_client.es_packages_url
    result = es_client.safe_elasticsearch_query(endpoint, request_data)

    # Extract aggregation results for unique programs
    buckets = result.get("aggregations", {}).get("unique_programs", {}).get("buckets", [])

    # Extract the matching programs from the query result
    items = []
    # First use aggregation results
    if buckets:
        for bucket in buckets[:10]:
            program = bucket.get("key", "")
            count = bucket.get("doc_count", 0)
            if program and program.startswith(partial_name):
                items.append(create_completion_item(program, program, f"Found in {count} packages"))

    # If no results from aggregation, try extracting programs from hits
    if not items:
        hits = result.get("hits", {}).get("hits", [])
        all_programs = set()
        for hit in hits:
            source = hit.get("_source", {})
            programs = source.get("package_programs", [])
            if programs:
                for prog in programs:
                    if partial_name.lower() in prog.lower():
                        all_programs.add((prog, source.get("package_attr_name", "")))

        for prog, pkg in list(all_programs)[:10]:
            items.append(create_completion_item(prog, prog, f"Found in {pkg}"))

    return {"items": items}


async def complete_nixos_search_arguments(
    arg_name: str, arg_value: str, nixos_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete arguments for the nixos_search tool.

    Args:
        arg_name: Name of the argument being completed
        arg_value: Current value of the argument
        nixos_context: NixOS context for accessing package/option data

    Returns:
        Dictionary with completion items
    """
    logger.info(f"Completing argument for nixos_search: {arg_name}={arg_value}")

    # Get elasticsearch client
    es_client = nixos_context.get_es_client()

    if arg_name == "query":
        # For query argument, provide completion based on the type
        if not arg_value:
            # Suggest common search patterns
            items = [
                create_completion_item("firefox", "firefox", "Search for Firefox packages"),
                create_completion_item(
                    "services.postgresql", "services.postgresql", "Search for PostgreSQL service options"
                ),
                create_completion_item("networking", "networking", "Search for networking options"),
                create_completion_item("python", "python", "Search for Python-related packages"),
            ]
            return {"items": items}
        else:
            # Use existing completion functions based on the type
            # We'll need to determine if this is a package, option, or program search
            # For now, default to package search
            return await complete_nixos_package_name(arg_value, es_client, is_search=True)

    elif arg_name == "type":
        # Type is an enum
        types = [
            ("packages", "Search for NixOS packages"),
            ("options", "Search for NixOS configuration options"),
            ("programs", "Search for executables provided by packages"),
        ]

        # Filter based on current value
        matching_types = [(t, d) for t, d in types if arg_value.lower() in t.lower()]

        items = [create_completion_item(t, t, d) for t, d in matching_types]
        return {"items": items}

    elif arg_name == "channel":
        # Channel is an enum of available channels
        channels = [
            ("unstable", "Latest development branch"),
            ("24.11", "Latest stable release"),
        ]

        # Filter based on current value
        matching_channels = [(c, d) for c, d in channels if arg_value.lower() in c.lower()]

        items = [create_completion_item(c, c, d) for c, d in matching_channels]
        return {"items": items}

    elif arg_name == "limit":
        # Provide some reasonable limit values
        limits = [10, 20, 50, 100]

        # Try to convert current value to int for filtering
        try:
            current = int(arg_value) if arg_value else 0
            items = [
                create_completion_item(str(limit), str(limit), f"Return up to {limit} results")
                for limit in limits
                if limit >= current
            ]
        except ValueError:
            # If conversion fails, just return all options
            items = [
                create_completion_item(str(limit), str(limit), f"Return up to {limit} results") for limit in limits
            ]

        return {"items": items}

    # Fallback for unknown arguments
    return {"items": []}


async def complete_nixos_info_arguments(
    arg_name: str, arg_value: str, nixos_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete arguments for the nixos_info tool.

    Args:
        arg_name: Name of the argument being completed
        arg_value: Current value of the argument
        nixos_context: NixOS context for accessing package/option data

    Returns:
        Dictionary with completion items
    """
    # Get elasticsearch client
    es_client = nixos_context.get_es_client()

    if arg_name == "name":
        # For name argument, provide completions based on type
        if not arg_value:
            return {"items": []}

        # Default to package completion
        return await complete_nixos_package_name(arg_value, es_client)

    elif arg_name == "type":
        # Type is an enum with two values
        types = [("package", "Get detailed package information"), ("option", "Get detailed option information")]

        # Filter based on current value
        matching_types = [(t, d) for t, d in types if arg_value.lower() in t.lower()]

        items = [create_completion_item(t, t, d) for t, d in matching_types]
        return {"items": items}

    elif arg_name == "channel":
        # Channel is an enum of available channels
        channels = [
            ("unstable", "Latest development branch"),
            ("24.11", "Latest stable release"),
        ]

        # Filter based on current value
        matching_channels = [(c, d) for c, d in channels if arg_value.lower() in c.lower()]

        items = [create_completion_item(c, c, d) for c, d in matching_channels]
        return {"items": items}

    # Fallback for unknown arguments
    return {"items": []}
