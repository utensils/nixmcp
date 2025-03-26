"""
MCP completion package for NixMCP.

This package provides MCP completion implementations for various resource types
and tools in NixMCP, enabling IDE-like code suggestions and tab completion.
"""

import logging
import re
from typing import Dict, List, Any

# Get logger
logger = logging.getLogger("nixmcp")

# Import completion implementations
from nixmcp.completions.utils import create_completion_item
from nixmcp.completions.nixos import (
    complete_nixos_package_name,
    complete_nixos_option_name,
    complete_nixos_program_name,
    complete_nixos_search_arguments,
    complete_nixos_info_arguments,
)

from nixmcp.completions.home_manager import (
    complete_home_manager_option_name,
    complete_home_manager_search_arguments,
    complete_home_manager_info_arguments,
    complete_home_manager_prefix_arguments,
)


async def handle_completion(
    params: Dict[str, Any], nixos_context: Any, home_manager_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Handle MCP completion requests by dispatching to appropriate completion handlers.

    Args:
        params: Parameters from the completion request
        nixos_context: NixOS context for accessing package/option data
        home_manager_context: Home Manager context for accessing option data

    Returns:
        Dictionary with completion items
    """
    logger.info("Handling completion request")
    logger.debug(f"Completion request params: {params}")

    try:
        # Extract reference type and parameters
        ref = params.get("ref", {})
        ref_type = ref.get("type")

        # Extract argument information
        argument = params.get("argument", {})
        arg_name = argument.get("name", "")
        arg_value = argument.get("value", "")

        logger.info(f"Completion request: type={ref_type}, argument={arg_name}, value={arg_value}")

        # Dispatch based on reference type
        if ref_type == "ref/resource":
            # Handle resource URI completion
            uri = ref.get("uri", "")
            return await complete_resource_uri(uri, nixos_context, home_manager_context)

        elif ref_type == "ref/prompt":
            # Handle prompt argument completion
            prompt_name = ref.get("name", "")
            return await complete_prompt_argument(prompt_name, arg_name, arg_value, nixos_context, home_manager_context)

        elif ref_type == "ref/tool":
            # Handle tool argument completion
            tool_name = ref.get("name", "")
            return await complete_tool_argument(tool_name, arg_name, arg_value, nixos_context, home_manager_context)

        else:
            logger.warning(f"Unsupported reference type: {ref_type}")
            return {"items": []}

    except Exception as e:
        logger.error(f"Error handling completion request: {e}", exc_info=True)
        # Return empty completion results on error
        return {"items": []}


async def complete_resource_uri(
    uri: str, nixos_context: Any, home_manager_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete a resource URI based on its path structure.

    Args:
        uri: The partial resource URI to complete
        nixos_context: NixOS context for accessing package/option data
        home_manager_context: Home Manager context for accessing option data

    Returns:
        Dictionary with completion items
    """
    logger.info(f"Completing resource URI: {uri}")
    logger.debug(
        f"Completion context - NixOS: {nixos_context is not None}, Home Manager: {home_manager_context is not None}"
    )

    # Get elasticsearch client
    es_client = nixos_context.get_es_client()

    # Get Home Manager client
    hm_client = home_manager_context.get_home_manager_client()

    # Define patterns for various resource types
    NIXOS_PACKAGE_PATTERN = r"^nixos://package/(.*)$"
    NIXOS_OPTION_PATTERN = r"^nixos://option/(.*)$"
    NIXOS_SEARCH_PACKAGES_PATTERN = r"^nixos://search/packages/(.*)$"
    NIXOS_SEARCH_OPTIONS_PATTERN = r"^nixos://search/options/(.*)$"
    NIXOS_SEARCH_PROGRAMS_PATTERN = r"^nixos://search/programs/(.*)$"
    HOME_MANAGER_OPTION_PATTERN = r"^home-manager://option/(.*)$"
    HOME_MANAGER_SEARCH_PATTERN = r"^home-manager://search/options/(.*)$"

    # Match patterns and dispatch to appropriate handlers

    # NixOS package completions
    if re.match(NIXOS_PACKAGE_PATTERN, uri):
        partial_name = re.match(NIXOS_PACKAGE_PATTERN, uri).group(1)
        result = await complete_nixos_package_name(partial_name, es_client)
        logger.debug(f"Package completion result for '{partial_name}': {len(result.get('items', []))} items")
        return result

    # NixOS option completions
    elif re.match(NIXOS_OPTION_PATTERN, uri):
        partial_name = re.match(NIXOS_OPTION_PATTERN, uri).group(1)
        result = await complete_nixos_option_name(partial_name, es_client)
        logger.debug(f"Option completion result for '{partial_name}': {len(result.get('items', []))} items")
        return result

    # NixOS search/packages completions
    elif re.match(NIXOS_SEARCH_PACKAGES_PATTERN, uri):
        partial_query = re.match(NIXOS_SEARCH_PACKAGES_PATTERN, uri).group(1)
        result = await complete_nixos_package_name(partial_query, es_client, is_search=True)
        logger.debug(f"Package search completion result for '{partial_query}': {len(result.get('items', []))} items")
        return result

    # NixOS search/options completions
    elif re.match(NIXOS_SEARCH_OPTIONS_PATTERN, uri):
        partial_query = re.match(NIXOS_SEARCH_OPTIONS_PATTERN, uri).group(1)
        result = await complete_nixos_option_name(partial_query, es_client, is_search=True)
        logger.debug(f"Option search completion result for '{partial_query}': {len(result.get('items', []))} items")
        return result

    # NixOS search/programs completions
    elif re.match(NIXOS_SEARCH_PROGRAMS_PATTERN, uri):
        partial_program = re.match(NIXOS_SEARCH_PROGRAMS_PATTERN, uri).group(1)
        result = await complete_nixos_program_name(partial_program, es_client)
        logger.debug(f"Program search completion result for '{partial_program}': {len(result.get('items', []))} items")
        return result

    # Home Manager option completions
    elif re.match(HOME_MANAGER_OPTION_PATTERN, uri):
        partial_name = re.match(HOME_MANAGER_OPTION_PATTERN, uri).group(1)
        result = await complete_home_manager_option_name(partial_name, hm_client)
        logger.debug(
            f"Home Manager option completion result for '{partial_name}': {len(result.get('items', []))} items"
        )
        return result

    # Home Manager search completions
    elif re.match(HOME_MANAGER_SEARCH_PATTERN, uri):
        partial_query = re.match(HOME_MANAGER_SEARCH_PATTERN, uri).group(1)
        result = await complete_home_manager_option_name(partial_query, hm_client, is_search=True)
        logger.debug(
            f"Home Manager search completion result for '{partial_query}': {len(result.get('items', []))} items"
        )
        return result

    # Base resource URI completion (first level paths)
    elif uri in ["nixos://", "nixos:", "nixos"]:
        # Provide top-level NixOS resource paths
        items = [
            create_completion_item("nixos://package/{name}", "nixos://package/", "NixOS package by name"),
            create_completion_item("nixos://option/{name}", "nixos://option/", "NixOS option by name"),
            create_completion_item(
                "nixos://search/packages/{query}", "nixos://search/packages/", "Search NixOS packages"
            ),
            create_completion_item("nixos://search/options/{query}", "nixos://search/options/", "Search NixOS options"),
            create_completion_item(
                "nixos://search/programs/{program}", "nixos://search/programs/", "Search NixOS programs"
            ),
            create_completion_item("nixos://packages/stats", "nixos://packages/stats", "NixOS package statistics"),
            create_completion_item("nixos://status", "nixos://status", "NixOS context status"),
        ]
        logger.debug(f"Returning {len(items)} top-level NixOS resource completions")
        return {"items": items}

    elif uri in ["home-manager://", "home-manager:", "home-manager"]:
        # Provide top-level Home Manager resource paths
        items = [
            create_completion_item(
                "home-manager://option/{name}", "home-manager://option/", "Home Manager option by name"
            ),
            create_completion_item(
                "home-manager://search/options/{query}", "home-manager://search/options/", "Search Home Manager options"
            ),
            create_completion_item(
                "home-manager://options/stats", "home-manager://options/stats", "Home Manager options statistics"
            ),
            create_completion_item(
                "home-manager://options/list", "home-manager://options/list", "List Home Manager option categories"
            ),
            create_completion_item(
                "home-manager://options/prefix/{prefix}", "home-manager://options/prefix/", "Get options by prefix"
            ),
            create_completion_item("home-manager://status", "home-manager://status", "Home Manager context status"),
        ]
        logger.debug(f"Returning {len(items)} top-level Home Manager resource completions")
        return {"items": items}

    # Fallback - no completions
    logger.info(f"No completion handler for URI: {uri}")
    return {"items": []}


async def complete_tool_argument(
    tool_name: str, arg_name: str, arg_value: str, nixos_context: Any, home_manager_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete arguments for tools based on the tool name and argument.

    Args:
        tool_name: Name of the tool
        arg_name: Name of the argument being completed
        arg_value: Current value of the argument
        nixos_context: NixOS context for accessing package/option data
        home_manager_context: Home Manager context for accessing option data

    Returns:
        Dictionary with completion items
    """
    logger.info(f"Completing tool argument: {tool_name}.{arg_name}={arg_value}")
    logger.debug(
        "Tool argument completion context - NixOS: "
        f"{nixos_context is not None}, Home Manager: {home_manager_context is not None}"
    )

    result = {"items": []}

    # NixOS search tool completions
    if tool_name == "nixos_search":
        result = await complete_nixos_search_arguments(arg_name, arg_value, nixos_context)
        logger.debug(
            f"NixOS search tool completion result for '{arg_name}={arg_value}': {len(result.get('items', []))} items"
        )

    # NixOS info tool completions
    elif tool_name == "nixos_info":
        result = await complete_nixos_info_arguments(arg_name, arg_value, nixos_context)
        logger.debug(
            f"NixOS info tool completion result for '{arg_name}={arg_value}': {len(result.get('items', []))} items"
        )

    # Home Manager search tool completions
    elif tool_name == "home_manager_search":
        result = await complete_home_manager_search_arguments(arg_name, arg_value, home_manager_context)
        logger.debug(
            "Home Manager search tool completion result for "
            f"'{arg_name}={arg_value}': {len(result.get('items', []))} items"
        )

    # Home Manager info tool completions
    elif tool_name == "home_manager_info":
        result = await complete_home_manager_info_arguments(arg_name, arg_value, home_manager_context)
        logger.debug(
            "Home Manager info tool completion result for "
            f"'{arg_name}={arg_value}': {len(result.get('items', []))} items"
        )

    # Home Manager options by prefix tool completions
    elif tool_name == "home_manager_options_by_prefix":
        result = await complete_home_manager_prefix_arguments(arg_name, arg_value, home_manager_context)
        logger.debug(
            "Home Manager prefix tool completion result for "
            f"'{arg_name}={arg_value}': {len(result.get('items', []))} items"
        )

    # Fallback for unknown tools
    elif tool_name:
        logger.debug(f"No completion handler for tool: {tool_name}")

    return result


async def complete_prompt_argument(
    prompt_name: str, arg_name: str, arg_value: str, nixos_context: Any, home_manager_context: Any
) -> Dict[str, List[Dict[str, str]]]:
    """
    Complete arguments for prompts based on the prompt name and argument.

    Args:
        prompt_name: Name of the prompt
        arg_name: Name of the argument being completed
        arg_value: Current value of the argument
        nixos_context: NixOS context for accessing package/option data
        home_manager_context: Home Manager context for accessing option data

    Returns:
        Dictionary with completion items
    """
    logger.info(f"Prompt argument completion request: {prompt_name}.{arg_name}={arg_value}")
    logger.debug("Currently no prompt completion support in NixMCP")
    # Currently no prompt support in NixMCP
    return {"items": []}
