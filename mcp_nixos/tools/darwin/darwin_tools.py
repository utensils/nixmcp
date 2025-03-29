"""Darwin tools for MCP."""

import logging
from typing import Optional

from mcp_nixos.contexts.darwin.darwin_context import DarwinContext
from mcp_nixos.utils.helpers import get_context_or_fallback

logger = logging.getLogger(__name__)

# Global context instance
darwin_context: Optional[DarwinContext] = None


def register_darwin_tools(context: Optional[DarwinContext] = None, mcp=None) -> None:
    """Register Darwin tools with MCP.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.
        mcp: The MCP server instance to register tools with.
    """
    global darwin_context
    darwin_context = context

    # Register tools through MCP server instance
    if mcp:
        from mcp_nixos.tools.darwin.darwin_tools import (
            darwin_search,
            darwin_info,
            darwin_stats,
            darwin_list_options,
            darwin_options_by_prefix,
        )

        @mcp.tool("darwin_search")
        async def darwin_search_handler(query: str, limit: int = 20):
            return await darwin_search(query, limit, context)

        @mcp.tool("darwin_info")
        async def darwin_info_handler(name: str):
            return await darwin_info(name, context)

        @mcp.tool("darwin_stats")
        async def darwin_stats_handler():
            return await darwin_stats(context)

        @mcp.tool("darwin_list_options")
        async def darwin_list_options_handler():
            return await darwin_list_options(context)

        @mcp.tool("darwin_options_by_prefix")
        async def darwin_options_by_prefix_handler(option_prefix: str):
            return await darwin_options_by_prefix(option_prefix, context)


async def darwin_search(query: str, limit: int = 20, context: Optional[DarwinContext] = None) -> str:
    """
    Search for nix-darwin options.

    Args:
        query: The search term
        limit: Maximum number of results to return (default: 20)
        context: Optional context object for dependency injection in tests

    Returns:
        Results formatted as text
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return "Error: no Darwin context available"

        results = await ctx.search_options(query, limit=limit)

        if not results:
            return f"No nix-darwin options found matching '{query}'."

        output = [f"## Search results for '{query}' in nix-darwin options\n"]

        for option in results:
            name = option.get("name", "")
            desc = option.get("description", "")
            # Truncate description if it's too long
            if len(desc) > 100:
                desc = desc[:97] + "..."

            output.append(f"### {name}")
            output.append(f"{desc}\n")

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error searching Darwin options: {e}")
        return f"Error searching nix-darwin options: {e}"


async def darwin_info(name: str, context: Optional[DarwinContext] = None) -> str:
    """
    Get detailed information about a nix-darwin option.

    Args:
        name: The name of the option
        context: Optional context object for dependency injection in tests

    Returns:
        Detailed information formatted as text
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return "Error: no Darwin context available"

        option = await ctx.get_option(name)

        if not option:
            return f"Option '{name}' not found in nix-darwin."

        option_type = option.get("type", "")
        default = option.get("default", "")
        example = option.get("example", "")
        declared_by = option.get("declared_by", "")
        description = option.get("description", "")

        output = [f"## {name}"]

        output.append(description)
        output.append("")

        if option_type:
            output.append(f"**Type:** `{option_type}`")

        if default:
            output.append(f"**Default:** `{default}`")

        if example:
            output.append("**Example:**")
            output.append("```nix")
            output.append(example)
            output.append("```")

        if declared_by:
            output.append(f"**Declared by:** {declared_by}")

        # Add sub-options if any
        sub_options = option.get("sub_options", [])
        if sub_options:
            output.append("\n### Sub-options")
            for sub in sub_options:
                sub_name = sub.get("name", "")
                sub_desc = sub.get("description", "")
                if sub_desc and len(sub_desc) > 100:
                    sub_desc = sub_desc[:97] + "..."
                output.append(f"- **{sub_name}**: {sub_desc}")

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error getting Darwin option {name}: {e}")
        return f"Error getting nix-darwin option '{name}': {e}"


async def darwin_stats(context: Optional[DarwinContext] = None) -> str:
    """
    Get statistics about available nix-darwin options.

    Args:
        context: Optional context object for dependency injection in tests

    Returns:
        Statistics about nix-darwin options
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return "Error: no Darwin context available"

        stats = await ctx.get_statistics()

        if "error" in stats:
            return f"Error retrieving nix-darwin statistics: {stats['error']}"

        total_options = stats.get("total_options", 0)
        total_categories = stats.get("total_categories", 0)
        last_updated = stats.get("last_updated", "unknown")
        categories = stats.get("categories", [])

        output = ["## nix-darwin Options Statistics"]
        output.append(f"- **Total options:** {total_options}")
        output.append(f"- **Total categories:** {total_categories}")
        output.append(f"- **Last updated:** {last_updated}")

        if categories:
            output.append("\n### Top-level Categories")
            for cat in sorted(categories, key=lambda x: x.get("name", "")):
                name = cat.get("name", "")
                count = cat.get("option_count", 0)
                output.append(f"- **{name}**: {count} options")

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error getting Darwin statistics: {e}")
        return f"Error retrieving nix-darwin statistics: {e}"


async def darwin_list_options(context: Optional[DarwinContext] = None) -> str:
    """
    List all top-level nix-darwin option categories.

    Args:
        context: Optional context object for dependency injection in tests

    Returns:
        Formatted list of top-level option categories and their statistics
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return "Error: no Darwin context available"

        categories = await ctx.get_categories()

        if not categories:
            return "No nix-darwin option categories found."

        output = ["## nix-darwin Option Categories"]

        for category in sorted(categories, key=lambda x: x.get("name", "")):
            name = category.get("name", "")
            count = category.get("option_count", 0)
            output.append(f"### {name}")
            output.append(f"- **Options count:** {count}")
            output.append(f"- **Usage:** `darwin.{name}`")
            output.append("")

        output.append(
            "To view options in a specific category, use the `darwin_options_by_prefix` tool with the category name."
        )

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error listing Darwin options: {e}")
        return f"Error listing nix-darwin option categories: {e}"


async def darwin_options_by_prefix(option_prefix: str, context: Optional[DarwinContext] = None) -> str:
    """
    Get all nix-darwin options under a specific prefix.

    Args:
        option_prefix: The option prefix to search for (e.g., "programs", "services")
        context: Optional context object for dependency injection in tests

    Returns:
        Formatted list of options under the given prefix
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return "Error: no Darwin context available"

        options = await ctx.get_options_by_prefix(option_prefix)

        if not options:
            return f"No nix-darwin options found with prefix '{option_prefix}'."

        output = [f"## nix-darwin options with prefix '{option_prefix}'"]
        output.append(f"Found {len(options)} options.")
        output.append("")

        for option in sorted(options, key=lambda x: x.get("name", "")):
            name = option.get("name", "")
            desc = option.get("description", "")
            option_type = option.get("type", "")

            # Truncate description if it's too long
            if desc and len(desc) > 100:
                desc = desc[:97] + "..."

            output.append(f"### {name}")
            output.append(desc)

            if option_type:
                output.append(f"**Type:** `{option_type}`")

            output.append("")
            output.append(f'For more details, use `darwin_info("{name}")`')
            output.append("")

        return "\n".join(output)
    except Exception as e:
        logger.error(f"Error getting Darwin options by prefix {option_prefix}: {e}")
        return f"Error retrieving nix-darwin options with prefix '{option_prefix}': {e}"
