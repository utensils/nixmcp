"""
MCP tools for Home Manager.
"""

import logging

# Get logger
logger = logging.getLogger("nixmcp")

# Import utility functions
from nixmcp.utils.helpers import create_wildcard_query


def home_manager_search(query: str, limit: int = 20, context=None) -> str:
    """
    Search for Home Manager options.

    Args:
        query: The search term
        limit: Maximum number of results to return (default: 20)
        context: Optional context object for dependency injection in tests

    Returns:
        Results formatted as text
    """
    logger.info(f"Searching for Home Manager options with query '{query}'")

    # Use provided context or fallback to global context
    if context is None:
        # Import here to avoid circular imports
        import nixmcp.server

        context = nixmcp.server.home_manager_context

    try:
        # Add wildcards if not present and not a special query
        if "*" not in query and ":" not in query and not query.endswith("."):
            wildcard_query = create_wildcard_query(query)
            logger.info(f"Adding wildcards to query: {wildcard_query}")
            query = wildcard_query

        results = context.search_options(query, limit)
        options = results.get("options", [])

        if not options:
            if "error" in results:
                return f"Error: {results['error']}"
            return f"No Home Manager options found for '{query}'."

        output = f"Found {len(options)} Home Manager options for '{query}':\n\n"

        # Group options by category for better organization
        options_by_category = {}
        for opt in options:
            category = opt.get("category", "Uncategorized")
            if category not in options_by_category:
                options_by_category[category] = []
            options_by_category[category].append(opt)

        # Print options grouped by category
        for category, category_options in options_by_category.items():
            output += f"## {category}\n\n"
            for opt in category_options:
                output += f"- {opt.get('name', 'Unknown')}\n"
                if opt.get("type"):
                    output += f"  Type: {opt.get('type')}\n"
                if opt.get("description"):
                    output += f"  {opt.get('description')}\n"
                output += "\n"

        # Add usage hint if results contain program options
        program_options = [opt for opt in options if "programs." in opt.get("name", "")]
        if program_options:
            program_name = program_options[0].get("name", "").split(".")[1] if len(program_options) > 0 else ""
            if program_name:
                output += f"\n## Usage Example for {program_name}\n\n"
                output += "```nix\n"
                output += "# In your home configuration (e.g., ~/.config/nixpkgs/home.nix)\n"
                output += "{ config, pkgs, ... }:\n"
                output += "{\n"
                output += f"  programs.{program_name} = {{\n"
                output += "    enable = true;\n"
                output += "    # Add more configuration options here\n"
                output += "  };\n"
                output += "}\n"
                output += "```\n"

        return output

    except Exception as e:
        logger.error(f"Error in home_manager_search: {e}", exc_info=True)
        return f"Error performing search: {str(e)}"


def home_manager_info(name: str, context=None) -> str:
    """
    Get detailed information about a Home Manager option.

    Args:
        name: The name of the option
        context: Optional context object for dependency injection in tests

    Returns:
        Detailed information formatted as text
    """
    logger.info(f"Getting Home Manager option information for: {name}")

    # Use provided context or fallback to global context
    if context is None:
        # Import here to avoid circular imports
        import nixmcp.server

        context = nixmcp.server.home_manager_context

    try:
        info = context.get_option(name)

        if not info.get("found", False):
            output = f"# Option '{name}' not found\n\n"

            if "suggestions" in info:
                output += "Did you mean one of these options?\n\n"
                for suggestion in info.get("suggestions", []):
                    output += f"- {suggestion}\n"

                # Get the first suggestion's parent path if it's a hierarchical path
                if "." in name and len(info.get("suggestions", [])) > 0:
                    suggested_name = info.get("suggestions", [])[0]
                    parts = suggested_name.split(".")
                    if len(parts) > 1:
                        parent_path = ".".join(parts[:-1])
                        output += "\nTry searching for all options under this path:\n"
                        output += f'`home_manager_search(query="{parent_path}")`'
            else:
                # If name contains dots, suggest searching for parent path
                if "." in name:
                    parts = name.split(".")
                    if len(parts) > 1:
                        parent_path = ".".join(parts[:-1])
                        output += "Try searching for all options under this path:\n"
                        output += f'`home_manager_search(query="{parent_path}")`'

            return output

        option = info

        output = f"# {option.get('name', name)}\n\n"

        if option.get("description"):
            output += f"**Description:** {option.get('description')}\n\n"

        if option.get("type"):
            output += f"**Type:** {option.get('type')}\n"

        if option.get("default") is not None:
            # Format default value nicely
            default_val = option.get("default")
            if isinstance(default_val, str) and len(default_val) > 80:
                output += f"**Default:**\n```nix\n{default_val}\n```\n"
            else:
                output += f"**Default:** {default_val}\n"

        if option.get("example"):
            output += f"\n**Example:**\n```nix\n{option.get('example')}\n```\n"

        if option.get("category"):
            output += f"\n**Category:** {option.get('category')}\n"

        if option.get("source"):
            output += f"**Source:** {option.get('source')}\n"

        # Add information about related options
        if "related_options" in option and option["related_options"]:
            related_options = option["related_options"]

            output += "\n## Related Options\n\n"
            for opt in related_options:
                output += f"- `{opt.get('name', '')}`"
                if opt.get("type"):
                    output += f" ({opt.get('type')})"
                output += "\n"
                if opt.get("description"):
                    output += f"  {opt.get('description')}\n"

        # Add example Home Manager configuration if this is a program option
        if "programs." in name:
            parts = name.split(".")
            if len(parts) > 1:
                program_name = parts[1]

                output += "\n## Example Home Manager Configuration\n\n"
                output += "```nix\n"
                output += "# In your home configuration (e.g., ~/.config/nixpkgs/home.nix)\n"
                output += "{ config, pkgs, ... }:\n"
                output += "{\n"
                output += f"  programs.{program_name} = {{\n"
                output += "    enable = true;\n"

                # Specific configuration for this option if it's not the enable option
                if not name.endswith(".enable"):
                    option_leaf = parts[-1]

                    if option.get("type") == "boolean":
                        output += f"    {option_leaf} = true;\n"
                    elif option.get("type") == "string":
                        output += f'    {option_leaf} = "value";\n'
                    elif option.get("type") == "int" or option.get("type") == "integer":
                        output += f"    {option_leaf} = 1234;\n"
                    else:
                        output += f"    # Configure {option_leaf} here\n"

                output += "  };\n"
                output += "}\n"
                output += "```\n"

        return output

    except Exception as e:
        logger.error(f"Error getting Home Manager option information: {e}", exc_info=True)
        return f"Error retrieving information: {str(e)}"


def home_manager_stats(context=None) -> str:
    """
    Get statistics about Home Manager options.

    Args:
        context: Optional context object for dependency injection in tests

    Returns:
        Statistics about Home Manager options
    """
    logger.info("Getting Home Manager option statistics")

    # Use provided context or fallback to global context
    if context is None:
        # Import here to avoid circular imports
        import nixmcp.server

        context = nixmcp.server.home_manager_context

    try:
        stats = context.get_stats()

        if "error" in stats:
            return f"Error getting statistics: {stats['error']}"

        output = "# Home Manager Option Statistics\n\n"

        # Overall statistics
        output += f"Total options: {stats.get('total_options', 0)}\n"
        output += f"Categories: {stats.get('total_categories', 0)}\n"
        output += f"Option types: {stats.get('total_types', 0)}\n\n"

        # Distribution by source
        by_source = stats.get("by_source", {})
        if by_source:
            output += "## Distribution by Source\n\n"
            for source, count in by_source.items():
                output += f"- {source}: {count} options\n"
            output += "\n"

        # Top categories by option count
        by_category = stats.get("by_category", {})
        if by_category:
            output += "## Top Categories\n\n"

            # Sort categories by option count (descending)
            sorted_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)

            # Show top 10 categories
            for category, count in sorted_categories[:10]:
                output += f"- {category}: {count} options\n"
            output += "\n"

        # Distribution by type
        by_type = stats.get("by_type", {})
        if by_type:
            output += "## Distribution by Type\n\n"

            # Sort types by option count (descending)
            sorted_types = sorted(by_type.items(), key=lambda x: x[1], reverse=True)

            # Show top 10 types
            for type_name, count in sorted_types[:10]:
                output += f"- {type_name}: {count} options\n"
            output += "\n"

        # Indexing statistics
        index_stats = stats.get("index_stats", {})
        if index_stats:
            output += "## Index Statistics\n\n"
            output += f"- Words indexed: {index_stats.get('words', 0)}\n"
            output += f"- Prefix paths: {index_stats.get('prefixes', 0)}\n"
            output += f"- Hierarchical parts: {index_stats.get('hierarchical_parts', 0)}\n"

        return output

    except Exception as e:
        logger.error(f"Error getting Home Manager statistics: {e}", exc_info=True)
        return f"Error retrieving statistics: {str(e)}"


def home_manager_list_options(context=None) -> str:
    """
    List all top-level Home Manager option categories.

    Args:
        context: Optional context object for dependency injection in tests

    Returns:
        Formatted list of top-level option categories and their statistics
    """
    logger.info("Listing all top-level Home Manager option categories")

    # Use provided context or fallback to global context
    if context is None:
        # Import here to avoid circular imports
        import nixmcp.server

        context = nixmcp.server.home_manager_context

    try:
        result = context.get_options_list()

        if not result.get("found", False):
            if "error" in result:
                return f"Error: {result['error']}"
            return "No Home Manager options were found."

        options = result.get("options", {})

        if not options:
            return "No top-level Home Manager option categories were found."

        output = "# Home Manager Top-Level Option Categories\n\n"

        # Calculate totals for summary
        total_options = sum(opt.get("count", 0) for opt in options.values())
        # total_enable_options calculation removed - was unused

        output += f"Total categories: {len(options)}\n"
        output += f"Total options: {total_options}\n\n"

        # Sort options by count (descending)
        sorted_options = sorted(options.items(), key=lambda x: x[1].get("count", 0), reverse=True)

        for name, data in sorted_options:
            option_count = data.get("count", 0)
            if option_count == 0:
                continue  # Skip empty categories

            output += f"## {name}\n\n"
            output += f"- **Options count**: {option_count}\n"

            # Show type distribution if available
            types = data.get("types", {})
            if types:
                output += "- **Option types**:\n"
                sorted_types = sorted(types.items(), key=lambda x: x[1], reverse=True)
                for type_name, count in sorted_types[:5]:  # Show top 5 types
                    output += f"  - {type_name}: {count}\n"

            # Show enable options if available
            enable_options = data.get("enable_options", [])
            if enable_options:
                output += f"- **Enable options**: {len(enable_options)}\n"
                # Show a few examples of enable options
                for i, enable_opt in enumerate(enable_options[:3]):  # Show up to 3 examples
                    parent = enable_opt.get("parent", "")
                    desc = enable_opt.get("description", "").split(". ")[0] + "."  # First sentence
                    output += f"  - {parent}: {desc}\n"
                if len(enable_options) > 3:
                    output += f"  - ...and {len(enable_options) - 3} more\n"

            # Add usage example for this category
            output += f"\n**Usage example for {name}:**\n"
            output += "```nix\n"
            output += "# In your home configuration (e.g., ~/.config/nixpkgs/home.nix)\n"
            output += "{ config, pkgs, ... }:\n"
            output += "{\n"

            # Different example syntax based on category
            if name == "programs":
                output += "  programs.<name> = {\n"
                output += "    enable = true;\n"
                output += "    # Additional configuration options\n"
                output += "  };\n"
            elif name == "services":
                output += "  services.<name> = {\n"
                output += "    enable = true;\n"
                output += "    # Service-specific configuration\n"
                output += "  };\n"
            else:
                output += f"  {name}.<option> = <value>;\n"

            output += "}\n"
            output += "```\n\n"

            # Add a tip to search for more detailed information
            output += "**Tip**: To see all options in this category, use:\n"
            output += f'`home_manager_options_by_prefix(option_prefix="{name}")`\n\n'

        return output

    except Exception as e:
        logger.error(f"Error listing Home Manager options: {e}", exc_info=True)
        return f"Error retrieving options list: {str(e)}"


def home_manager_options_by_prefix(option_prefix: str, context=None) -> str:
    """
    Get all Home Manager options under a specific prefix.

    Args:
        option_prefix: The option prefix to search for (e.g., "programs", "programs.git")
        context: Optional context object for dependency injection in tests

    Returns:
        Formatted list of options under the given prefix
    """
    logger.info(f"Getting Home Manager options by prefix '{option_prefix}'")

    # Use provided context or fallback to global context
    if context is None:
        # Import here to avoid circular imports
        import nixmcp.server

        context = nixmcp.server.home_manager_context

    try:
        result = context.get_options_by_prefix(option_prefix)

        if not result.get("found", False):
            if "error" in result:
                return f"Error: {result['error']}"
            return f"No Home Manager options found with prefix '{option_prefix}'."

        options = result.get("options", [])

        if not options:
            return f"No Home Manager options found with prefix '{option_prefix}'."

        output = f"# Home Manager Options: {option_prefix}\n\n"
        output += f"Found {len(options)} options\n\n"

        # Organize options by next hierarchical level
        if "." in option_prefix:
            # This is a deeper level, sort options alphabetically
            options.sort(key=lambda x: x.get("name", ""))

            # Group options by their immediate parent
            grouped_options = {}
            for opt in options:
                name = opt.get("name", "")
                if name.startswith(option_prefix):
                    # Get the next path component after the prefix
                    remainder = name[len(option_prefix) + 1 :]  # +1 for the dot
                    if "." in remainder:
                        group = remainder.split(".")[0]
                        if group not in grouped_options:
                            grouped_options[group] = []
                        grouped_options[group].append(opt)
                    else:
                        # This is a direct child option
                        if "_direct" not in grouped_options:
                            grouped_options["_direct"] = []
                        grouped_options["_direct"].append(opt)

            # First show direct options if any
            if "_direct" in grouped_options:
                output += "## Direct Options\n\n"
                for opt in grouped_options["_direct"]:
                    output += f"- **{opt.get('name', '')}**"
                    if opt.get("type"):
                        output += f" ({opt.get('type')})"
                    output += "\n"
                    if opt.get("description"):
                        output += f"  {opt.get('description')}\n"
                output += "\n"

                # Remove the _direct group so it's not repeated
                del grouped_options["_direct"]

            # Then show grouped options
            for group, group_opts in sorted(grouped_options.items()):
                output += f"## {group}\n\n"
                output += f"**{len(group_opts)}** options - "
                # Add a tip to dive deeper
                full_path = f"{option_prefix}.{group}"
                output += "To see all options in this group, use:\n"
                output += f'`home_manager_options_by_prefix(option_prefix="{full_path}")`\n\n'

                # Show a sample of options from this group (up to 3)
                for opt in group_opts[:3]:
                    name_parts = opt.get("name", "").split(".")
                    if len(name_parts) > 0:
                        short_name = name_parts[-1]
                        output += f"- **{short_name}**"
                        if opt.get("type"):
                            output += f" ({opt.get('type')})"
                        output += "\n"
                output += "\n"
        else:
            # This is a top-level option, show enable options first if available
            enable_options = result.get("enable_options", [])
            if enable_options:
                output += "## Enable Options\n\n"
                for enable_opt in enable_options:
                    parent = enable_opt.get("parent", "")
                    name = enable_opt.get("name", "")
                    desc = enable_opt.get("description", "")
                    output += f"- **{parent}**: {desc}\n"
                output += "\n"

            # Group other options by their second-level component
            grouped_options = {}
            for opt in options:
                name = opt.get("name", "")
                parts = name.split(".")
                if len(parts) > 1 and parts[0] == option_prefix:
                    group = parts[1] if len(parts) > 1 else "_direct"
                    if group not in grouped_options:
                        grouped_options[group] = []
                    grouped_options[group].append(opt)

            # List groups with option counts
            if grouped_options:
                output += "## Option Groups\n\n"
                for group, group_opts in sorted(grouped_options.items()):
                    if group == "_direct":
                        continue
                    output += f"- **{group}**: {len(group_opts)} options\n"
                    # Add a tip to dive deeper for groups with significant options
                    if len(group_opts) > 5:
                        full_path = f"{option_prefix}.{group}"
                        output += f'  To see all options, use: `home_manager_options_by_prefix("{full_path}")`\n'
                output += "\n"

        # Add usage example based on the option prefix
        parts = option_prefix.split(".")
        if len(parts) > 0:
            if parts[0] == "programs" and len(parts) > 1:
                program_name = parts[1]
                output += f"## Example Configuration for {program_name}\n\n"
                output += "```nix\n"
                output += "# In your home configuration (e.g., ~/.config/nixpkgs/home.nix)\n"
                output += "{ config, pkgs, ... }:\n"
                output += "{\n"
                output += f"  programs.{program_name} = {{\n"
                output += "    enable = true;\n"
                output += "    # Add configuration options here\n"
                output += "  };\n"
                output += "}\n"
                output += "```\n"
            elif parts[0] == "services" and len(parts) > 1:
                service_name = parts[1]
                output += f"## Example Configuration for {service_name} service\n\n"
                output += "```nix\n"
                output += "# In your home configuration (e.g., ~/.config/nixpkgs/home.nix)\n"
                output += "{ config, pkgs, ... }:\n"
                output += "{\n"
                output += f"  services.{service_name} = {{\n"
                output += "    enable = true;\n"
                output += "    # Add service configuration options here\n"
                output += "  };\n"
                output += "}\n"
                output += "```\n"

        return output

    except Exception as e:
        logger.error(f"Error getting Home Manager options by prefix: {e}", exc_info=True)
        return f"Error retrieving options: {str(e)}"


def register_home_manager_tools(mcp) -> None:
    """
    Register all Home Manager tools with the MCP server.

    Args:
        mcp: The MCP server instance
    """
    mcp.tool()(home_manager_search)
    mcp.tool()(home_manager_info)
    mcp.tool()(home_manager_stats)
    mcp.tool()(home_manager_list_options)
    mcp.tool()(home_manager_options_by_prefix)
