"""
MCP tools for Home Manager.
"""

import logging
from typing import Dict, Optional, Any

# Get logger
logger = logging.getLogger("mcp_nixos")

# Import utility functions
from mcp_nixos.utils.helpers import create_wildcard_query


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

    # Import needed modules here to avoid circular imports
    import importlib

    # Get context
    if context is None:
        # Import get_home_manager_context dynamically to avoid circular imports
        try:
            server_module = importlib.import_module("mcp_nixos.server")
            get_home_manager_context = getattr(server_module, "get_home_manager_context")
            context = get_home_manager_context()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to dynamically import get_home_manager_context: {e}")
            context = None

    try:
        # Add wildcards if not present and not a special query
        if "*" not in query and ":" not in query and not query.endswith("."):
            wildcard_query = create_wildcard_query(query)
            logger.info(f"Adding wildcards to query: {wildcard_query}")
            query = wildcard_query

        # Handle case where context is a string (from MCP tool interface)
        if isinstance(context, str):
            # Import get_home_manager_context dynamically when we have a string context
            try:
                server_module = importlib.import_module("mcp_nixos.server")
                get_home_manager_context = getattr(server_module, "get_home_manager_context")
                real_context = get_home_manager_context()
                if real_context is None:
                    return "Error: Home Manager context not available"
                results = real_context.search_options(query, limit)
            except Exception as e:
                logger.error(f"Error getting Home Manager context when called with string context: {e}")
                return f"Error: Could not search for '{query}': {str(e)}"
        else:
            # Ensure context is not None before accessing its attributes
            if context is None:
                return "Error: Home Manager context not available"

            results = context.search_options(query, limit)

        options = results.get("options", [])

        if not options:
            if "error" in results:
                return f"Error: {results['error']}"
            return f"No Home Manager options found for '{query}'."

        # Sort and prioritize results by relevance:
        # 1. Exact matches
        # 2. Name begins with query
        # 3. Path contains exact query term
        # 4. Description or other matches
        exact_matches = []
        starts_with_matches = []
        contains_matches = []
        other_matches = []

        search_term = query.replace("*", "").lower()

        for opt in options:
            name = opt.get("name", "").lower()
            # Extract last path component for more precise matching
            last_component = name.split(".")[-1] if "." in name else name

            if name == search_term or last_component == search_term:
                exact_matches.append(opt)
            elif name.startswith(search_term) or last_component.startswith(search_term):
                starts_with_matches.append(opt)
            elif search_term in name:
                contains_matches.append(opt)
            else:
                other_matches.append(opt)

        # Reassemble in priority order
        prioritized_options = exact_matches + starts_with_matches + contains_matches + other_matches

        output = f"Found {len(prioritized_options)} Home Manager options for '{query}':\n\n"

        # First, extract any program-specific options, identified by their path
        program_options = {}
        other_options = []

        for opt in prioritized_options:
            name = opt.get("name", "")
            if name.startswith("programs."):
                parts = name.split(".")
                if len(parts) > 1:
                    program = parts[1]
                    if program not in program_options:
                        program_options[program] = []
                    program_options[program].append(opt)
            else:
                other_options.append(opt)

        # First show program-specific options if the search seems to be for a program
        if program_options and (
            query.lower().startswith("program") or any(prog.lower() in query.lower() for prog in program_options.keys())
        ):
            for program, options_list in sorted(program_options.items()):
                output += f"## programs.{program}\n\n"
                for opt in options_list:
                    name = opt.get("name", "Unknown")
                    # Extract just the relevant part after programs.{program}
                    if name.startswith(f"programs.{program}."):
                        short_name = name[(len(f"programs.{program}.")) :]
                        display_name = short_name if short_name else name
                    else:
                        display_name = name

                    output += f"- {display_name}\n"
                    if opt.get("type"):
                        output += f"  Type: {opt.get('type')}\n"
                    if opt.get("description"):
                        output += f"  {opt.get('description')}\n"
                    output += "\n"

                # Add usage example for this program
                output += f"### Usage Example for {program}\n\n"
                output += "```nix\n"
                output += "# In your home configuration (e.g., ~/.config/nixpkgs/home.nix)\n"
                output += "{ config, pkgs, ... }:\n"
                output += "{\n"
                output += f"  programs.{program} = {{\n"
                output += "    enable = true;\n"
                output += "    # Add configuration options here\n"
                output += "  };\n"
                output += "}\n"
                output += "```\n\n"

        # Group remaining options by category for better organization
        if other_options:
            options_by_category = {}
            for opt in other_options:
                category = opt.get("category", "Uncategorized")
                if category not in options_by_category:
                    options_by_category[category] = []
                options_by_category[category].append(opt)

            # Print options grouped by category
            for category, category_options in sorted(options_by_category.items()):
                if len(category_options) == 0:
                    continue

                output += f"## {category}\n\n"
                for opt in category_options:
                    output += f"- {opt.get('name', 'Unknown')}\n"
                    if opt.get("type"):
                        output += f"  Type: {opt.get('type')}\n"
                    if opt.get("description"):
                        output += f"  {opt.get('description')}\n"
                    output += "\n"

        # If no specific program was identified but we have program options,
        # add a generic program usage example
        if not program_options and other_options and any("programs." in opt.get("name", "") for opt in other_options):
            all_programs = set()
            for opt in other_options:
                if "programs." in opt.get("name", ""):
                    parts = opt.get("name", "").split(".")
                    if len(parts) > 1:
                        all_programs.add(parts[1])

            if all_programs:
                primary_program = sorted(all_programs)[0]
                output += f"\n## Usage Example for {primary_program}\n\n"
                output += "```nix\n"
                output += "# In your home configuration (e.g., ~/.config/nixpkgs/home.nix)\n"
                output += "{ config, pkgs, ... }:\n"
                output += "{\n"
                output += f"  programs.{primary_program} = {{\n"
                output += "    enable = true;\n"
                output += "    # Add configuration options here\n"
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

    # Import needed modules here to avoid circular imports
    import importlib

    # Get context
    if context is None:
        # Import get_home_manager_context dynamically to avoid circular imports
        try:
            server_module = importlib.import_module("mcp_nixos.server")
            get_home_manager_context = getattr(server_module, "get_home_manager_context")
            context = get_home_manager_context()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to dynamically import get_home_manager_context: {e}")
            context = None

    try:
        # Handle case where context is a string (from MCP tool interface)
        if isinstance(context, str):
            # Import get_home_manager_context dynamically when we have a string context
            try:
                server_module = importlib.import_module("mcp_nixos.server")
                get_home_manager_context = getattr(server_module, "get_home_manager_context")
                real_context = get_home_manager_context()
                if real_context is None:
                    return f"Error: Home Manager context not available for option '{name}'"
                info = real_context.get_option(name)
            except Exception as e:
                logger.error(f"Error getting Home Manager context when called with string context: {e}")
                return f"Error: Could not obtain information for '{name}': {str(e)}"
        else:
            # Ensure context is not None before accessing its attributes
            if context is None:
                return f"Error: Home Manager context not available for option '{name}'"

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

        if option.get("introduced_version"):
            output += f"**Introduced in version:** {option.get('introduced_version')}\n"

        if option.get("deprecated_version"):
            output += f"**Deprecated in version:** {option.get('deprecated_version')}\n"

        if option.get("default") is not None:
            # Format default value nicely
            default_val = option.get("default")
            if isinstance(default_val, str) and len(default_val) > 80:
                output += f"**Default:**\n```nix\n{default_val}\n```\n"
            else:
                output += f"**Default:** {default_val}\n"

        if option.get("manual_url"):
            output += f"**Documentation:** [Home Manager Manual]({option.get('manual_url')})\n"

        if option.get("example"):
            output += f"\n**Example:**\n```nix\n{option.get('example')}\n```\n"

            # Add example in context if this is a nested option
            if "." in option.get("name", ""):
                parts = option.get("name", "").split(".")
                if len(parts) > 1:
                    # Using parts directly instead of storing in unused variable
                    leaf_name = parts[-1]

                    output += "\n**Example in context:**\n```nix\n"
                    output += "# ~/.config/nixpkgs/home.nix\n"
                    output += "{ config, pkgs, ... }:\n{\n"

                    # Build nested structure
                    current_indent = "  "
                    for i, part in enumerate(parts[:-1]):
                        output += f"{current_indent}{part} = " + ("{\n" if i < len(parts) - 2 else "{\n")
                        current_indent += "  "

                    # Add the actual example
                    example_value = option.get("example")
                    output += f"{current_indent}{leaf_name} = {example_value};\n"

                    # Close the nested structure
                    for i in range(len(parts) - 1):
                        current_indent = current_indent[:-2]
                        output += f"{current_indent}}};\n"

                    output += "}\n```\n"

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

    # Import needed modules here to avoid circular imports
    import importlib

    # Get context
    if context is None:
        # Import get_home_manager_context dynamically to avoid circular imports
        try:
            server_module = importlib.import_module("mcp_nixos.server")
            get_home_manager_context = getattr(server_module, "get_home_manager_context")
            context = get_home_manager_context()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to dynamically import get_home_manager_context: {e}")
            context = None

    try:
        # Handle case where context is a string (from MCP tool interface)
        if isinstance(context, str):
            # Import get_home_manager_context dynamically when we have a string context
            try:
                server_module = importlib.import_module("mcp_nixos.server")
                get_home_manager_context = getattr(server_module, "get_home_manager_context")
                real_context = get_home_manager_context()
                if real_context is None:
                    return "Error: Home Manager context not available"
                stats = real_context.get_stats()
            except Exception as e:
                logger.error(f"Error getting Home Manager context when called with string context: {e}")
                return f"Error: Could not obtain Home Manager statistics: {str(e)}"
        else:
            # Ensure context is not None before accessing its attributes
            if context is None:
                return "Error: Home Manager context not available"

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

    # Import needed modules here to avoid circular imports
    import importlib

    # Get context
    if context is None:
        # Import get_home_manager_context dynamically to avoid circular imports
        try:
            server_module = importlib.import_module("mcp_nixos.server")
            get_home_manager_context = getattr(server_module, "get_home_manager_context")
            context = get_home_manager_context()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to dynamically import get_home_manager_context: {e}")
            context = None

    try:
        # Handle case where context is a string (from MCP tool interface)
        if isinstance(context, str):
            # Import get_home_manager_context dynamically when we have a string context
            try:
                server_module = importlib.import_module("mcp_nixos.server")
                get_home_manager_context = getattr(server_module, "get_home_manager_context")
                real_context = get_home_manager_context()
                if real_context is None:
                    return "Error: Home Manager context not available"
                result = real_context.get_options_list()
            except Exception as e:
                logger.error(f"Error getting Home Manager context when called with string context: {e}")
                return f"Error: Could not list Home Manager options: {str(e)}"
        else:
            # Ensure context is not None before accessing its attributes
            if context is None:
                return "Error: Home Manager context not available"

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

    # Import needed modules here to avoid circular imports
    import importlib

    # Get context
    if context is None:
        # Import get_home_manager_context dynamically to avoid circular imports
        try:
            server_module = importlib.import_module("mcp_nixos.server")
            get_home_manager_context = getattr(server_module, "get_home_manager_context")
            context = get_home_manager_context()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to dynamically import get_home_manager_context: {e}")
            context = None

    try:
        # Handle case where context is a string (from MCP tool interface)
        if isinstance(context, str):
            # Import get_home_manager_context dynamically when we have a string context
            try:
                server_module = importlib.import_module("mcp_nixos.server")
                get_home_manager_context = getattr(server_module, "get_home_manager_context")
                real_context = get_home_manager_context()
                if real_context is None:
                    return f"Error: Home Manager context not available for prefix '{option_prefix}'"
                result = real_context.get_options_by_prefix(option_prefix)
            except Exception as e:
                logger.error(f"Error getting Home Manager context when called with string context: {e}")
                return f"Error: Could not get options by prefix '{option_prefix}': {str(e)}"
        else:
            # Ensure context is not None before accessing its attributes
            if context is None:
                return f"Error: Home Manager context not available for prefix '{option_prefix}'"

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
                    name = opt.get("name", "")
                    # Display the full option name but highlight the key part
                    if name.startswith(option_prefix):
                        parts = name.split(".")
                        short_name = parts[-1]
                        output += f"- **{name}** ({short_name})"
                    else:
                        output += f"- **{name}**"

                    if opt.get("type"):
                        output += f" ({opt.get('type')})"
                    output += "\n"
                    if opt.get("description"):
                        # Clean up description if it has HTML
                        desc = opt.get("description")
                        if desc.startswith("<"):
                            desc = desc.replace("<p>", "").replace("</p>", " ")
                            desc = desc.replace("<code>", "`").replace("</code>", "`")
                            # Clean up whitespace
                            desc = " ".join(desc.split())
                        output += f"  {desc}\n"
                output += "\n"

                # Remove the _direct group so it's not repeated
                del grouped_options["_direct"]

            # Then show grouped options - split into multiple sections to avoid truncation
            grouped_list = sorted(grouped_options.items())

            # Show at most 10 groups per section to avoid truncation
            group_chunks = [grouped_list[i : i + 10] for i in range(0, len(grouped_list), 10)]

            for chunk_idx, chunk in enumerate(group_chunks):
                if len(group_chunks) > 1:
                    output += f"## Option Groups (Part {chunk_idx+1} of {len(group_chunks)})\n\n"
                else:
                    output += "## Option Groups\n\n"

                for group, group_opts in chunk:
                    output += f"### {group} options ({len(group_opts)})\n\n"
                    # Add a tip to dive deeper
                    full_path = f"{option_prefix}.{group}"
                    output += "To see all options in this group, use:\n"
                    output += f'`home_manager_options_by_prefix(option_prefix="{full_path}")`\n\n'

                    # Show a sample of options from this group (up to 5)
                    for opt in group_opts[:5]:
                        name_parts = opt.get("name", "").split(".")
                        if len(name_parts) > 0:
                            short_name = name_parts[-1]
                            output += f"- **{short_name}**"
                            if opt.get("type"):
                                output += f" ({opt.get('type')})"
                            output += "\n"

                    # If there are more, indicate it
                    if len(group_opts) > 5:
                        output += f"- ...and {len(group_opts) - 5} more\n"
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

            # List groups with option counts - chunk this too to avoid truncation
            if grouped_options:
                sorted_groups = sorted(grouped_options.items())
                # Show at most 20 groups per section to avoid truncation
                group_chunks = [sorted_groups[i : i + 20] for i in range(0, len(sorted_groups), 20)]

                for chunk_idx, chunk in enumerate(group_chunks):
                    if len(group_chunks) > 1:
                        output += f"## Option Groups (Part {chunk_idx+1} of {len(group_chunks)})\n\n"
                    else:
                        output += "## Option Groups\n\n"

                    for group, group_opts in chunk:
                        if group == "_direct":
                            continue
                        output += f"- **{group}**: {len(group_opts)} options\n"
                        # Add a tip to dive deeper for groups with significant options
                        if len(group_opts) > 5:
                            full_path = f"{option_prefix}.{group}"
                            cmd = f'home_manager_options_by_prefix(option_prefix="{full_path}")'
                            output += f"  To see all options, use: `{cmd}`\n"
                    output += "\n"

        # Always include a section about examples
        output += "## Usage Examples\n\n"

        # Add usage example based on the option prefix
        parts = option_prefix.split(".")
        if len(parts) > 0:
            if parts[0] == "programs" and len(parts) > 1:
                program_name = parts[1]
                output += f"### Example Configuration for {program_name}\n\n"
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
                output += f"### Example Configuration for {service_name} service\n\n"
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
            else:
                output += "### General Home Manager Configuration\n\n"
                output += "```nix\n"
                output += "# In your home configuration (e.g., ~/.config/nixpkgs/home.nix)\n"
                output += "{ config, pkgs, ... }:\n"
                output += "{\n"
                output += f"  {option_prefix} = {{\n"
                output += "    # Add configuration options here\n"
                output += "  }};\n"
                output += "}\n"
                output += "```\n"

        return output

    except Exception as e:
        logger.error(f"Error getting Home Manager options by prefix: {e}", exc_info=True)
        return f"Error retrieving options: {str(e)}"


def check_request_ready(ctx) -> bool:
    """Check if the server is ready to handle requests.

    Args:
        ctx: The request context or context string from MCP

    Returns:
        True if ready, False if not
    """
    # Handle case where ctx is a string (from MCP tool interface)
    if isinstance(ctx, str):
        return True  # Always ready when called from MCP outside server

    # Handle case where ctx is a request context (from our server)
    if hasattr(ctx, "request_context"):
        return ctx.request_context.lifespan_context.get("is_ready", False)

    # Default to ready if we can't determine
    logger.warning("Unknown context type, assuming ready")
    return True


def check_home_manager_ready(ctx) -> Optional[Dict[str, Any]]:
    """Check if Home Manager client is ready.

    Args:
        ctx: The request context or context string from MCP

    Returns:
        Dict with error message if not ready, None if ready
    """
    # Handle case where ctx is a string (from MCP tool interface)
    if isinstance(ctx, str):
        return None  # Always ready when called from MCP outside server

    # First check if server is ready
    if not check_request_ready(ctx):
        return {"error": "The server is still initializing. Please try again in a few seconds.", "found": False}

    # Get Home Manager context and check if data is loaded
    if hasattr(ctx, "request_context"):
        home_manager_context = ctx.request_context.lifespan_context.get("home_manager_context")
        if home_manager_context and hasattr(home_manager_context, "hm_client"):
            client = home_manager_context.hm_client
            if not client.is_loaded:
                if client.loading_in_progress:
                    return {
                        "error": "Home Manager data is still loading. Please try again in a few seconds.",
                        "found": False,
                        "partial_init": True,
                    }
                elif client.loading_error:
                    return {
                        "error": f"Failed to load Home Manager data: {client.loading_error}",
                        "found": False,
                        "partial_init": True,
                    }

    # All good
    return None


def register_home_manager_tools(mcp) -> None:
    """
    Register all Home Manager tools with the MCP server.

    Args:
        mcp: The MCP server instance
    """

    @mcp.tool()
    async def home_manager_search(ctx, query: str, limit: int = 20) -> str:
        """Search for Home Manager options.

        Args:
            query: The search term
            limit: Maximum number of results to return (default: 20)

        Returns:
            Results formatted as text
        """
        logger.info(f"Home Manager search request: query='{query}', limit={limit}")

        # Check if Home Manager is ready
        ready_check = check_home_manager_ready(ctx)
        if ready_check:
            logger.warning(f"Home Manager search blocked: {ready_check['error']}")
            return ready_check["error"]

        # Get context
        try:
            # Handle string context from MCP
            if isinstance(ctx, str):
                # Access the correct function (not this decorated function)
                from mcp_nixos.tools.home_manager_tools import home_manager_search as search_func

                result = search_func(query, limit, ctx)
                return result

            # Regular request context from server
            home_ctx = ctx.request_context.lifespan_context.get("home_manager_context")
            # Access the correct function (not this decorated function)
            from mcp_nixos.tools.home_manager_tools import home_manager_search as search_func

            result = search_func(query, limit, home_ctx)
            return result
        except Exception as e:
            error_msg = f"Error during Home Manager search: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @mcp.tool()
    async def home_manager_info(ctx, name: str) -> str:
        """Get detailed information about a Home Manager option.

        Args:
            name: The name of the option

        Returns:
            Detailed information formatted as text
        """
        logger.info(f"Home Manager info request: name='{name}'")

        # Check if Home Manager is ready
        ready_check = check_home_manager_ready(ctx)
        if ready_check:
            logger.warning(f"Home Manager info blocked: {ready_check['error']}")
            return ready_check["error"]

        # Get context
        try:
            # Handle string context from MCP
            if isinstance(ctx, str):
                # Access the correct function (not this decorated function)
                from mcp_nixos.tools.home_manager_tools import home_manager_info as info_func

                result = info_func(name, ctx)
                return result

            # Regular request context from server
            home_ctx = ctx.request_context.lifespan_context.get("home_manager_context")
            from mcp_nixos.tools.home_manager_tools import home_manager_info as info_func

            result = info_func(name, home_ctx)
            return result
        except Exception as e:
            error_msg = f"Error during Home Manager info: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @mcp.tool()
    async def home_manager_stats(ctx) -> str:
        """Get statistics about Home Manager options.

        Returns:
            Statistics about Home Manager options
        """
        logger.info("Home Manager stats request")

        # Check if Home Manager is ready
        ready_check = check_home_manager_ready(ctx)
        if ready_check:
            logger.warning(f"Home Manager stats blocked: {ready_check['error']}")
            return ready_check["error"]

        # Get context
        try:
            # Handle string context from MCP
            if isinstance(ctx, str):
                # Access the correct function (not this decorated function)
                from mcp_nixos.tools.home_manager_tools import home_manager_stats as stats_func

                result = stats_func(ctx)
                return result

            # Regular request context from server
            home_ctx = ctx.request_context.lifespan_context.get("home_manager_context")
            from mcp_nixos.tools.home_manager_tools import home_manager_stats as stats_func

            result = stats_func(home_ctx)
            return result
        except Exception as e:
            error_msg = f"Error during Home Manager stats: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @mcp.tool()
    async def home_manager_list_options(ctx) -> str:
        """List all top-level Home Manager option categories.

        Returns:
            Formatted list of top-level option categories and their statistics
        """
        logger.info("Home Manager list options request")

        # Check if Home Manager is ready
        ready_check = check_home_manager_ready(ctx)
        if ready_check:
            logger.warning(f"Home Manager list options blocked: {ready_check['error']}")
            return ready_check["error"]

        # Get context
        try:
            # Handle string context from MCP
            if isinstance(ctx, str):
                # Access the correct function (not this decorated function)
                from mcp_nixos.tools.home_manager_tools import home_manager_list_options as list_options_func

                result = list_options_func(ctx)
                return result

            # Regular request context from server
            home_ctx = ctx.request_context.lifespan_context.get("home_manager_context")
            from mcp_nixos.tools.home_manager_tools import home_manager_list_options as list_options_func

            result = list_options_func(home_ctx)
            return result
        except Exception as e:
            error_msg = f"Error during Home Manager list options: {str(e)}"
            logger.error(error_msg)
            return error_msg

    @mcp.tool()
    async def home_manager_options_by_prefix(ctx, option_prefix: str) -> str:
        """Get all Home Manager options under a specific prefix.

        Args:
            option_prefix: The option prefix to search for (e.g., "programs", "programs.git")

        Returns:
            Formatted list of options under the given prefix
        """
        logger.info(f"Home Manager options by prefix request: option_prefix='{option_prefix}'")

        # Check if Home Manager is ready
        ready_check = check_home_manager_ready(ctx)
        if ready_check:
            logger.warning(f"Home Manager options by prefix blocked: {ready_check['error']}")
            return ready_check["error"]

        # Get context
        try:
            # Handle string context from MCP
            if isinstance(ctx, str):
                # Access the correct function (not this decorated function)
                from mcp_nixos.tools.home_manager_tools import home_manager_options_by_prefix as options_by_prefix_func

                result = options_by_prefix_func(option_prefix, ctx)
                return result

            # Regular request context from server
            home_ctx = ctx.request_context.lifespan_context.get("home_manager_context")
            from mcp_nixos.tools.home_manager_tools import home_manager_options_by_prefix as options_by_prefix_func

            result = options_by_prefix_func(option_prefix, home_ctx)
            return result
        except Exception as e:
            error_msg = f"Error during Home Manager options by prefix: {str(e)}"
            logger.error(error_msg)
            return error_msg

    logger.info("Home Manager MCP tools registered with request gating.")
