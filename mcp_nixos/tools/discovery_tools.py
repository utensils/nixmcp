"""
Discovery tools for MCP-NixOS.

These tools provide dynamic discovery and introspection capabilities for the MCP tools,
following the MCP best practices of allowing tools to be self-documenting.
"""

import logging
from typing import Dict, Any

# Get logger
logger = logging.getLogger("mcp_nixos")


def get_tool_list() -> Dict[str, str]:
    """List all available MCP tools with brief descriptions.

    Returns:
        Dictionary mapping tool names to descriptions.
    """
    return {
        "nixos_search": "Search NixOS packages and options",
        "nixos_info": "Get detailed info about specific packages/options",
        "nixos_stats": "View statistics and available channels",
        "home_manager_search": "Search Home Manager options",
        "home_manager_info": "Get details about Home Manager options",
        "home_manager_stats": "Get statistics about Home Manager options",
        "home_manager_list_options": "List all Home Manager categories",
        "home_manager_options_by_prefix": "List Home Manager options by prefix",
        "darwin_search": "Search Darwin options for macOS",
        "darwin_info": "Get details about Darwin options",
        "darwin_stats": "Get statistics about Darwin options",
        "darwin_list_options": "List Darwin option categories",
        "darwin_options_by_prefix": "List Darwin options by prefix",
        "discover_tools": "List all available MCP tools",
        "get_tool_usage": "Get detailed usage information for a specific tool",
    }


def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """Get parameter schema for a specific tool.

    Args:
        tool_name: Name of the tool to get schema for

    Returns:
        Dictionary with parameter information
    """
    # Tool parameter schemas
    schemas = {
        "nixos_search": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "query": {
                "type": "string",
                "description": "Search term like 'firefox' or 'services.postgresql'",
                "required": True,
            },
            "type": {
                "type": "string",
                "description": "Type of search: 'packages', 'options', or 'programs'",
                "default": "packages",
            },
            "limit": {"type": "integer", "description": "Maximum number of results to return", "default": 20},
            "channel": {
                "type": "string",
                "description": "NixOS channel ('unstable', 'stable', or '24.11')",
                "default": "unstable",
            },
        },
        "nixos_info": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "name": {"type": "string", "description": "Name of package or option", "required": True},
            "type": {"type": "string", "description": "Type of info: 'package' or 'option'", "default": "package"},
            "channel": {
                "type": "string",
                "description": "NixOS channel ('unstable', 'stable', or '24.11')",
                "default": "unstable",
            },
        },
        "nixos_stats": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "channel": {
                "type": "string",
                "description": "NixOS channel ('unstable', 'stable', or '24.11')",
                "default": "unstable",
            },
        },
        "home_manager_search": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "query": {
                "type": "string",
                "description": "Search term like 'programs.git' or 'browsers'",
                "required": True,
            },
            "limit": {"type": "integer", "description": "Maximum number of results to return", "default": 20},
        },
        "home_manager_info": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "name": {"type": "string", "description": "Name of the Home Manager option", "required": True},
        },
        "home_manager_stats": {"ctx": {"type": "string", "description": "MCP context parameter", "required": True}},
        "home_manager_list_options": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True}
        },
        "home_manager_options_by_prefix": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "option_prefix": {
                "type": "string",
                "description": "The option prefix path (e.g., 'programs', 'services')",
                "required": True,
            },
        },
        "darwin_search": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "query": {
                "type": "string",
                "description": "Search term like 'services.yabai' or 'system'",
                "required": True,
            },
            "limit": {"type": "integer", "description": "Maximum number of results to return", "default": 20},
        },
        "darwin_info": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "name": {"type": "string", "description": "Name of the nix-darwin option", "required": True},
        },
        "darwin_stats": {"ctx": {"type": "string", "description": "MCP context parameter", "required": True}},
        "darwin_list_options": {"ctx": {"type": "string", "description": "MCP context parameter", "required": True}},
        "darwin_options_by_prefix": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "option_prefix": {
                "type": "string",
                "description": "The option prefix path (e.g., 'services', 'system.defaults')",
                "required": True,
            },
        },
        "discover_tools": {"ctx": {"type": "string", "description": "MCP context parameter", "required": True}},
        "get_tool_usage": {
            "ctx": {"type": "string", "description": "MCP context parameter", "required": True},
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to get usage information for",
                "required": True,
            },
        },
    }

    return schemas.get(tool_name, {"error": "Tool not found"})


def get_tool_examples(tool_name: str) -> Dict[str, str]:
    """Get usage examples for a specific tool.

    Args:
        tool_name: Name of the tool to get examples for

    Returns:
        Dictionary with example name and code
    """
    examples = {
        "nixos_search": {
            "Search packages": 'nixos_search(ctx, query="python", type="packages")',
            "Search options": 'nixos_search(ctx, query="services.postgresql", type="options")',
            "Search programs": 'nixos_search(ctx, query="firefox", type="programs", channel="stable")',
            "Search virtual hosts": 'nixos_search(ctx, query="services.nginx.virtualHosts", type="options")',
        },
        "nixos_info": {
            "Package info": 'nixos_info(ctx, name="firefox", type="package")',
            "Option info": 'nixos_info(ctx, name="services.postgresql.enable", type="option")',
            "Stable channel info": 'nixos_info(ctx, name="git", type="package", channel="stable")',
        },
        "nixos_stats": {
            "Default stats": "nixos_stats(ctx)",
            "Stable channel stats": 'nixos_stats(ctx, channel="stable")',
        },
        "home_manager_search": {
            "Search git options": 'home_manager_search(ctx, query="git")',
            "Search program options": 'home_manager_search(ctx, query="programs.alacritty")',
            "Search firefox options": 'home_manager_search(ctx, query="firefox")',
        },
        "home_manager_info": {
            "Option details": 'home_manager_info(ctx, name="programs.git.enable")',
            "Program details": 'home_manager_info(ctx, name="programs.vscode")',
        },
        "home_manager_stats": {"Get stats": "home_manager_stats(ctx)"},
        "home_manager_list_options": {"List categories": "home_manager_list_options(ctx)"},
        "home_manager_options_by_prefix": {
            "List program options": 'home_manager_options_by_prefix(ctx, option_prefix="programs")',
            "List service options": 'home_manager_options_by_prefix(ctx, option_prefix="services")',
        },
        "darwin_search": {
            "Search yabai": 'darwin_search(ctx, query="yabai")',
            "Search keyboard": 'darwin_search(ctx, query="system.keyboard")',
            "Search services": 'darwin_search(ctx, query="services")',
        },
        "darwin_info": {
            "Service option": 'darwin_info(ctx, name="services.yabai.enable")',
            "System defaults": 'darwin_info(ctx, name="system.defaults.dock")',
        },
        "darwin_stats": {"Get stats": "darwin_stats(ctx)"},
        "darwin_list_options": {"List categories": "darwin_list_options(ctx)"},
        "darwin_options_by_prefix": {
            "List services": 'darwin_options_by_prefix(ctx, option_prefix="services")',
            "List system defaults": 'darwin_options_by_prefix(ctx, option_prefix="system.defaults")',
        },
        "discover_tools": {"List all tools": "discover_tools(ctx)"},
        "get_tool_usage": {"Get usage info": 'get_tool_usage(ctx, tool_name="nixos_search")'},
    }

    return examples.get(tool_name, {"error": "No examples found for this tool"})


def get_tool_tips(tool_name: str) -> Dict[str, str]:
    """Get best practices and tips for using a specific tool.

    Args:
        tool_name: Name of the tool to get tips for

    Returns:
        Dictionary with tips and best practices
    """
    tips = {
        "nixos_search": {
            "use_wildcards": "Wildcards (*) are automatically added to most queries",
            "path_search": "For service options, use paths like 'services.postgresql'",
            "channels": "Use channel='stable' or channel='24.11' for the current stable release",
            "type_param": "Set type='packages', 'options', or 'programs' for different searches",
        },
        "nixos_info": {
            "verify_first": "First use nixos_search to find the exact name before using this tool",
            "option_paths": "For options, use the full path like 'services.postgresql.enable'",
            "package_names": "For packages, use the exact attribute name, not the package name",
        },
        "nixos_stats": {
            "channels": "Compare different channels using channel='unstable', channel='stable', or channel='24.11'"
        },
        "home_manager_search": {
            "program_configs": "For application configs, try 'programs.NAME'",
            "wildcards": "Use explicit wildcards for more specific searches",
        },
        "home_manager_info": {"option_paths": "Use the full path like 'programs.git.userName'"},
        "home_manager_stats": {"usage": "Use this for an overview of available options by category"},
        "home_manager_list_options": {"exploration": "Use this for exploring available option categories"},
        "home_manager_options_by_prefix": {"common_prefixes": "Common prefixes include 'programs', 'services', 'xdg'"},
        "darwin_search": {
            "system_options": "For system settings, try 'system.defaults'",
            "service_options": "For services, try 'services.NAME'",
        },
        "darwin_info": {"verify_first": "First use darwin_search to find the exact option path"},
        "darwin_stats": {"usage": "Use this for an overview of available options by category"},
        "darwin_list_options": {"exploration": "Use this to explore top-level option categories"},
        "darwin_options_by_prefix": {
            "common_prefixes": "Common prefixes include 'services', 'system.defaults', 'system.keyboard'"
        },
        "discover_tools": {"usage": "Use this when you need to know what tools are available"},
        "get_tool_usage": {"tool_exploration": "Use this to understand how to use a specific tool"},
    }

    return tips.get(tool_name, {"error": "No tips found for this tool"})


def get_tool_usage(tool_name: str) -> Dict[str, Any]:
    """Get detailed usage information for a specific tool.

    Args:
        tool_name: Name of the tool to get usage information for

    Returns:
        Dictionary with tool usage information
    """
    logger.info(f"Getting usage information for tool: {tool_name}")

    tools = get_tool_list()
    if tool_name not in tools:
        return {"error": f"Tool '{tool_name}' not found", "available_tools": list(tools.keys())}

    return {
        "name": tool_name,
        "description": tools.get(tool_name, ""),
        "parameters": get_tool_schema(tool_name),
        "examples": get_tool_examples(tool_name),
        "best_practices": get_tool_tips(tool_name),
    }


def register_discovery_tools(mcp):
    """Register all discovery tools with the MCP server.

    Args:
        mcp: The MCP server instance
    """
    logger.info("Registering discovery tools")

    @mcp.tool()
    def discover_tools(ctx):
        """List all available MCP tools with brief descriptions.

        Args:
            ctx: MCP context parameter

        Returns:
            Dictionary mapping tool names to descriptions
        """
        return get_tool_list()

    @mcp.tool()
    def get_tool_usage(ctx, tool_name: str):
        """Get detailed usage information for a specific tool.

        Args:
            ctx: MCP context parameter
            tool_name: Name of the tool to get usage information for

        Returns:
            Dictionary with tool usage information
        """
        # Directly use the module-level functions to avoid recursion
        tools = get_tool_list()
        if tool_name not in tools:
            return {"error": f"Tool '{tool_name}' not found", "available_tools": list(tools.keys())}

        return {
            "name": tool_name,
            "description": tools.get(tool_name, ""),
            "parameters": get_tool_schema(tool_name),
            "examples": get_tool_examples(tool_name),
            "best_practices": get_tool_tips(tool_name),
        }
