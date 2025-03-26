"""
Home Manager-specific completion implementations.

This module provides completion handlers for Home Manager options and tools.
"""

import logging
from typing import Dict, List, Any

from nixmcp.completions.utils import create_completion_item

# Get logger
logger = logging.getLogger("nixmcp")


async def complete_home_manager_option_name(
    partial_name: str, hm_client: Any, is_search: bool = False
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete Home Manager option names based on partial input.

    Args:
        partial_name: Partial option name to complete
        hm_client: Home Manager client for querying option data
        is_search: Whether this is a search query parameter (affects return format)

    Returns:
        Dictionary with completion items
    """
    logger.info(f"Completing Home Manager option name: {partial_name}")

    if not partial_name:
        # For empty prefix, return some common Home Manager option categories
        common_categories = [
            "programs",
            "services",
            "home",
            "accounts",
            "fonts",
            "gtk",
            "xdg",
            "wayland",
            "xsession",
            "targets",
        ]
        items = [create_completion_item(cat, cat, f"Home Manager {cat} options") for cat in common_categories]
        return {"items": items}

    # For hierarchical paths, we should use the prefix index
    if "." in partial_name:
        # Extract the hierarchical path components
        parts = partial_name.split(".")
        parent_path = ".".join(parts[:-1])
        last_part = parts[-1]

        # Use the hierarchical index directly for better performance
        if parent_path in hm_client.hierarchical_index:
            matching_options = []
            for component, options in hm_client.hierarchical_index[parent_path].items():
                if component.startswith(last_part):
                    for option in options:
                        matching_options.append((option, component))

            # Sort by component match quality
            matching_options.sort(key=lambda x: (0 if x[1] == last_part else 1, len(x[1])))

            # Convert to completion items
            items = []
            for option, component in matching_options[:10]:
                option_info = hm_client.options_data.get(option, {})
                description = option_info.get("description", "")
                option_type = option_info.get("type", "")

                items.append(
                    create_completion_item(option, option, f"{option_type}: {description[:80] if description else ''}")
                )

            return {"items": items}

    # Use the prefix index for better performance
    matching_options = []

    # Try to find matches in the prefix index
    if partial_name in hm_client.prefix_index:
        # Exact prefix match
        options = hm_client.prefix_index[partial_name]
        for option in options:
            matching_options.append(option)

    # Try prefix matches
    for prefix, options in hm_client.prefix_index.items():
        if prefix.startswith(partial_name) and prefix != partial_name:
            for option in options:
                matching_options.append(option)

    # Deduplicate and limit results
    matching_options = list(set(matching_options))[:10]

    # Convert to completion items
    items = []
    for option in matching_options:
        option_info = hm_client.options_data.get(option, {})
        description = option_info.get("description", "")
        option_type = option_info.get("type", "")

        items.append(
            create_completion_item(option, option, f"{option_type}: {description[:80] if description else ''}")
        )

    return {"items": items}


async def complete_home_manager_search_arguments(
    arg_name: str, arg_value: str, home_manager_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete arguments for the home_manager_search tool.

    Args:
        arg_name: Name of the argument being completed
        arg_value: Current value of the argument
        home_manager_context: Home Manager context for accessing option data

    Returns:
        Dictionary with completion items
    """
    # Get Home Manager client
    hm_client = home_manager_context.get_home_manager_client()

    if arg_name == "query":
        # For query argument, provide Home Manager option completion
        if not arg_value:
            # Suggest common Home Manager search patterns
            items = [
                create_completion_item("programs.git", "programs.git", "Search for Git configuration options"),
                create_completion_item(
                    "programs.firefox", "programs.firefox", "Search for Firefox configuration options"
                ),
                create_completion_item("services", "services", "Search for user services"),
                create_completion_item("programs.bash", "programs.bash", "Search for Bash shell configuration options"),
            ]
            return {"items": items}
        else:
            # Use Home Manager option completion
            return await complete_home_manager_option_name(arg_value, hm_client, is_search=True)

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


async def complete_home_manager_info_arguments(
    arg_name: str, arg_value: str, home_manager_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete arguments for the home_manager_info tool.

    Args:
        arg_name: Name of the argument being completed
        arg_value: Current value of the argument
        home_manager_context: Home Manager context for accessing option data

    Returns:
        Dictionary with completion items
    """
    # Get Home Manager client
    hm_client = home_manager_context.get_home_manager_client()

    if arg_name == "name":
        # For name argument, provide Home Manager option completion
        if not arg_value:
            return {"items": []}

        return await complete_home_manager_option_name(arg_value, hm_client)

    # Fallback for unknown arguments
    return {"items": []}


async def complete_home_manager_prefix_arguments(
    arg_name: str, arg_value: str, home_manager_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete arguments for the home_manager_options_by_prefix tool.

    Args:
        arg_name: Name of the argument being completed
        arg_value: Current value of the argument
        home_manager_context: Home Manager context for accessing option data

    Returns:
        Dictionary with completion items
    """
    # Get Home Manager client
    hm_client = home_manager_context.get_home_manager_client()

    if arg_name == "option_prefix":
        # For option_prefix argument, provide hierarchical path completion
        if not arg_value:
            # Suggest top-level prefixes
            prefixes = ["programs", "services", "home", "xdg", "accounts", "fonts", "gtk"]
            items = [create_completion_item(p, p, f"Home Manager {p} options") for p in prefixes]
            return {"items": items}

        # For partial hierarchical paths, get completions
        return await complete_home_manager_option_name(arg_value, hm_client)

    # Fallback for unknown arguments
    return {"items": []}
