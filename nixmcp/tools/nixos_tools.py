"""
MCP tools for NixOS.
"""

import logging

# Get logger
logger = logging.getLogger("nixmcp")

# Import utility functions
from nixmcp.utils.helpers import (
    create_wildcard_query,
    get_context_or_fallback,
    parse_multi_word_query,
)


# Define channel constants to make updates easier in the future
CHANNEL_UNSTABLE = "unstable"
CHANNEL_STABLE = "stable"  # Currently maps to 24.11, but using stable makes it easier to update


def nixos_search(
    query: str, type: str = "packages", limit: int = 20, channel: str = CHANNEL_UNSTABLE, context=None
) -> str:
    """
    Search for NixOS packages, options, or programs.

    Args:
        query: The search term
        type: What to search for - "packages", "options", or "programs"
        limit: Maximum number of results to return (default: 20)
        channel: NixOS channel to search (default: "unstable", can also be "stable")
        context: Optional context object for dependency injection in tests

    Returns:
        Results formatted as text
    """
    logger.info(f"Searching for {type} with query '{query}' in channel '{channel}'")

    valid_types = ["packages", "options", "programs"]
    if type.lower() not in valid_types:
        return f"Error: Invalid type. Must be one of: {', '.join(valid_types)}"

    # Get context using the helper function
    context = get_context_or_fallback(context, "nixos_context")

    # Set the channel for the search
    context.es_client.set_channel(channel)
    logger.info(f"Using channel: {channel}")

    try:
        # Enhanced multi-word query handling for options
        if type.lower() == "options":
            # Parse the query if it's a multi-word query
            if " " in query:
                query_components = parse_multi_word_query(query)
                logger.info(f"Parsed multi-word query: {query_components}")

                # If we have a hierarchical path (dot notation) in a multi-word query
                if query_components["main_path"]:
                    main_path = query_components["main_path"]
                    terms = query_components["terms"]
                    quoted_terms = query_components["quoted_terms"]

                    logger.info(
                        f"Multi-word hierarchical query detected: path={main_path}, "
                        f"terms={terms}, quoted={quoted_terms}"
                    )

                    # Use the main hierarchical path for searching, and use terms for additional filtering
                    # Pass the structured query to the search_options method
                    results = context.search_options(
                        main_path, limit=limit, additional_terms=terms, quoted_terms=quoted_terms
                    )

                    # Handle the results
                    options = results.get("options", [])

                    if not options:
                        # Check if this is a service path for better suggestions
                        is_service_path = main_path.startswith("services.")
                        service_name = ""
                        if is_service_path:
                            service_parts = main_path.split(".", 2)
                            service_name = service_parts[1] if len(service_parts) > 1 else ""

                            # Provide suggestions based on parsed components
                            original_parts = " ".join([main_path] + terms + quoted_terms)
                            suggestion_msg = f"\nYour search '{original_parts}' returned no results.\n\n"
                            suggestion_msg += "Try these approaches instead:\n"

                            if service_name:
                                suggestion_msg += (
                                    f"1. Search for the exact option: "
                                    f'`nixos_info(name="{main_path}.{terms[0] if terms else "acceptTerms"}", '
                                    f'type="option")`\n'
                                )
                                suggestion_msg += (
                                    f"2. Search for all options in this path: "
                                    f'`nixos_search(query="{main_path}", type="options")`\n'
                                )
                                if terms:
                                    suggestion_msg += (
                                        f'3. Search for "{terms[0]}" within the service: '
                                        f'`nixos_search(query="services.{service_name} {terms[0]}", type="options")`\n'
                                    )

                            return f"No options found for '{query}'.\n{suggestion_msg}"

                        return f"No options found for '{query}'."

                    # Custom formatting of results for multi-word hierarchical queries
                    output = f"Found {len(options)} options for '{query}':\n\n"
                    for opt in options:
                        output += f"- {opt.get('name', 'Unknown')}\n"
                        if opt.get("description"):
                            output += f"  {opt.get('description')}\n"
                        if opt.get("type"):
                            output += f"  Type: {opt.get('type')}\n"
                        output += "\n"

                    return output

            # Handle simple hierarchical paths (no spaces)
            elif "." in query and "*" not in query:
                # Don't add wildcards yet - the search_options method will handle it
                logger.info(f"Detected hierarchical path in options search: {query}")

            # Add wildcards if not present and not a special query
            elif "*" not in query and ":" not in query:
                wildcard_query = create_wildcard_query(query)
                logger.info(f"Adding wildcards to query: {wildcard_query}")
                query = wildcard_query

        # For non-options searches (packages, programs), use standard wildcard handling
        elif "*" not in query and ":" not in query:
            wildcard_query = create_wildcard_query(query)
            logger.info(f"Adding wildcards to query: {wildcard_query}")
            query = wildcard_query

        if type.lower() == "packages":
            results = context.search_packages(query, limit)
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
            # Special handling for service module paths
            is_service_path = query.startswith("services.") if not query.startswith("*") else False
            service_name = ""
            if is_service_path:
                service_parts = query.split(".", 2)
                service_name = service_parts[1] if len(service_parts) > 1 else ""
                logger.info(f"Detected services module path, service name: {service_name}")

            results = context.search_options(query, limit)
            options = results.get("options", [])

            if not options:
                if is_service_path:
                    suggestion_msg = f"\nTo find options for the '{service_name}' service, try these searches:\n"
                    suggestion_msg += f'- `nixos_search(query="services.{service_name}.enable", type="options")`\n'
                    suggestion_msg += f'- `nixos_search(query="services.{service_name}.package", type="options")`\n'

                    # Add common option patterns for services
                    common_options = [
                        "enable",
                        "package",
                        "settings",
                        "port",
                        "user",
                        "group",
                        "dataDir",
                        "configFile",
                    ]
                    sample_options = [f"services.{service_name}.{opt}" for opt in common_options[:3]]
                    suggestion_msg += f"\nOr try a more specific option path like: {', '.join(sample_options)}"

                    return f"No options found for '{query}'.\n{suggestion_msg}"
                return f"No options found for '{query}'."

            output = f"Found {len(options)} options for '{query}':\n\n"
            for opt in options:
                output += f"- {opt.get('name', 'Unknown')}\n"
                if opt.get("description"):
                    output += f"  {opt.get('description')}\n"
                if opt.get("type"):
                    output += f"  Type: {opt.get('type')}\n"
                output += "\n"

            # For service modules, provide extra help
            if is_service_path and service_name:
                output += f"\n## Common option patterns for '{service_name}' service:\n\n"
                output += "Services typically include these standard options:\n"
                output += "- `enable`: Boolean to enable/disable the service\n"
                output += "- `package`: The package to use for the service\n"
                output += "- `settings`: Configuration settings for the service\n"
                output += "- `user`/`group`: User/group the service runs as\n"
                output += "- `dataDir`: Data directory for the service\n"

            return output

        else:  # programs
            results = context.search_programs(query, limit)
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


def nixos_info(name: str, type: str = "package", channel: str = CHANNEL_UNSTABLE, context=None) -> str:
    """
    Get detailed information about a NixOS package or option.

    Args:
        name: The name of the package or option
        type: Either "package" or "option"
        channel: NixOS channel to search (default: "unstable", can also be "stable")
        context: Optional context object for dependency injection in tests

    Returns:
        Detailed information formatted as text
    """
    logger.info(f"Getting {type} information for: {name} from channel '{channel}'")

    if type.lower() not in ["package", "option"]:
        return "Error: 'type' must be 'package' or 'option'"

    # Get context using the helper function
    context = get_context_or_fallback(context, "nixos_context")

    # Set the channel for the search
    context.es_client.set_channel(channel)
    logger.info(f"Using channel: {channel}")

    try:
        if type.lower() == "package":
            info = context.get_package(name)

            if not info.get("found", False):
                return f"Package '{name}' not found."

            output = f"# {info.get('name', name)}\n\n"

            # Always show version information, even if it's not available
            # Force version to be explicitly displayed in the output
            version = info.get("version", "")
            output += f"**Version:** {version if version else 'Not available'}\n"

            if info.get("description"):
                output += f"\n**Description:** {info.get('description')}\n"

            if info.get("longDescription"):
                output += f"\n**Long Description:**\n{info.get('longDescription')}\n"

            if info.get("homepage"):
                homepage = info.get("homepage")
                if isinstance(homepage, list):
                    if len(homepage) == 1:
                        output += f"\n**Homepage:** {homepage[0]}\n"
                    else:
                        output += "\n**Homepages:**\n"
                        for url in homepage:
                            output += f"- {url}\n"
                else:
                    output += f"\n**Homepage:** {homepage}\n"

            if info.get("license"):
                # Handle both string and list/dict formats for license
                license_info = info.get("license")
                if isinstance(license_info, list) and license_info:
                    if isinstance(license_info[0], dict) and "fullName" in license_info[0]:
                        # Extract license names
                        license_names = [lic.get("fullName", "") for lic in license_info if lic.get("fullName")]
                        output += f"\n**License:** {', '.join(license_names)}\n"
                    else:
                        output += f"\n**License:** {license_info}\n"
                else:
                    output += f"\n**License:** {license_info}\n"

            # Add source code position information
            if info.get("position"):
                position = info.get("position")
                # Create a link to the NixOS packages GitHub repository
                if ":" in position:
                    # If position has format "path:line"
                    file_path, line_num = position.rsplit(":", 1)
                    github_url = f"https://github.com/NixOS/nixpkgs/blob/master/{file_path}#L{line_num}"
                    output += f"\n**Source:** [{position}]({github_url})\n"
                else:
                    github_url = f"https://github.com/NixOS/nixpkgs/blob/master/{position}"
                    output += f"\n**Source:** [{position}]({github_url})\n"

            # Add maintainers
            if info.get("maintainers") and isinstance(info.get("maintainers"), list):
                maintainers = info.get("maintainers")
                if maintainers:
                    maintainer_names = []
                    for maintainer in maintainers:
                        if isinstance(maintainer, dict):
                            name = maintainer.get("name", "")
                            if name:
                                maintainer_names.append(name)
                        elif maintainer:
                            maintainer_names.append(str(maintainer))

                    if maintainer_names:
                        output += f"\n**Maintainers:** {', '.join(maintainer_names)}\n"

            # Add platforms
            if info.get("platforms") and isinstance(info.get("platforms"), list):
                platforms = info.get("platforms")
                if platforms:
                    output += f"\n**Platforms:** {', '.join(platforms)}\n"

            if info.get("programs") and isinstance(info.get("programs"), list):
                programs = info.get("programs")
                if programs:
                    output += f"\n**Provided Programs:** {', '.join(programs)}\n"

            return output

        else:  # option
            info = context.get_option(name)

            if not info.get("found", False):
                if info.get("is_service_path", False):
                    # Special handling for service paths that weren't found
                    service_name = info.get("service_name", "")
                    output = f"# Option '{name}' not found\n\n"
                    output += f"The option '{name}' doesn't exist or couldn't be found in the {channel} channel.\n\n"

                    output += "## Common Options for Services\n\n"
                    output += f"For service '{service_name}', try these common options:\n\n"
                    output += f"- `services.{service_name}.enable` - Enable the service (boolean)\n"
                    output += f"- `services.{service_name}.package` - The package to use for the service\n"
                    output += f"- `services.{service_name}.user` - The user account to run the service\n"
                    output += f"- `services.{service_name}.group` - The group to run the service\n"
                    output += f"- `services.{service_name}.settings` - Configuration settings for the service\n\n"

                    output += "## Example NixOS Configuration\n\n"
                    output += "```nix\n"
                    output += "# /etc/nixos/configuration.nix\n"
                    output += "{ config, pkgs, ... }:\n"
                    output += "{\n"
                    output += f"  # Enable {service_name} service\n"
                    output += f"  services.{service_name} = {{\n"
                    output += "    enable = true;\n"
                    output += "    # Add other configuration options here\n"
                    output += "  };\n"
                    output += "}\n"
                    output += "```\n"

                    output += "\nTry searching for all options related to this service with:\n"
                    output += f'`nixos_search(query="services.{service_name}", type="options", channel="{channel}")`'

                    return output
                return f"Option '{name}' not found."

            output = f"# {info.get('name', name)}\n\n"

            if info.get("description"):
                output += f"**Description:** {info.get('description')}\n\n"

            if info.get("type"):
                output += f"**Type:** {info.get('type')}\n"

            if info.get("introduced_version"):
                output += f"**Introduced in:** NixOS {info.get('introduced_version')}\n"

            if info.get("deprecated_version"):
                output += f"**Deprecated in:** NixOS {info.get('deprecated_version')}\n"

            if info.get("default") is not None:
                # Format default value nicely
                default_val = info.get("default")
                if isinstance(default_val, str) and len(default_val) > 80:
                    output += f"**Default:**\n```nix\n{default_val}\n```\n"
                else:
                    output += f"**Default:** {default_val}\n"

            if info.get("manual_url"):
                output += f"**Manual:** [{info.get('manual_url')}]({info.get('manual_url')})\n"

            if info.get("example"):
                output += f"\n**Example:**\n```nix\n{info.get('example')}\n```\n"

                # Add example in context if this is a nested option
                if "." in info.get("name", ""):
                    parts = info.get("name", "").split(".")
                    if len(parts) > 1:
                        # Using parts directly instead of storing in unused variable
                        leaf_name = parts[-1]

                        output += "\n**Example in context:**\n```nix\n"
                        output += "# /etc/nixos/configuration.nix\n"
                        output += "{ config, pkgs, ... }:\n{\n"

                        # Build nested structure
                        current_indent = "  "
                        for i, part in enumerate(parts[:-1]):
                            output += f"{current_indent}{part} = " + ("{\n" if i < len(parts) - 2 else "{\n")
                            current_indent += "  "

                        # Add the actual example
                        example_value = info.get("example")
                        output += f"{current_indent}{leaf_name} = {example_value};\n"

                        # Close the nested structure
                        for i in range(len(parts) - 1):
                            current_indent = current_indent[:-2]
                            output += f"{current_indent}}};\n"

                        output += "}\n```\n"

            # Add information about related options for service paths
            if info.get("is_service_path", False) and info.get("related_options", []):
                service_name = info.get("service_name", "")
                related_options = info.get("related_options", [])

                output += f"\n## Related Options for {service_name} Service\n\n"
                for opt in related_options:
                    output += f"- `{opt.get('name', '')}`"
                    if opt.get("type"):
                        output += f" ({opt.get('type')})"
                    output += "\n"
                    if opt.get("description"):
                        output += f"  {opt.get('description')}\n"

                # Add example NixOS configuration
                output += "\n## Example NixOS Configuration\n\n"
                output += "```nix\n"
                output += "# /etc/nixos/configuration.nix\n"
                output += "{ config, pkgs, ... }:\n"
                output += "{\n"
                output += f"  # Enable {service_name} service with options\n"
                output += f"  services.{service_name} = {{\n"
                output += "    enable = true;\n"
                if "services.{service_name}.package" in [opt.get("name", "") for opt in related_options]:
                    output += f"    package = pkgs.{service_name};\n"
                # Add current option to the example
                current_name = info.get("name", name)
                option_leaf = current_name.split(".")[-1]

                if info.get("type") == "boolean":
                    output += f"    {option_leaf} = true;\n"
                elif info.get("type") == "string":
                    output += f'    {option_leaf} = "value";\n'
                elif info.get("type") == "int" or info.get("type") == "integer":
                    output += f"    {option_leaf} = 1234;\n"
                else:
                    output += f"    # Configure {option_leaf} here\n"

                output += "  };\n"
                output += "}\n"
                output += "```\n"

            return output

    except Exception as e:
        logger.error(f"Error getting {type} information: {e}", exc_info=True)
        return f"Error retrieving information: {str(e)}"


def nixos_stats(context=None) -> str:
    """
    Get statistics about available NixOS packages.

    Args:
        context: Optional context object for dependency injection in tests

    Returns:
        Statistics about NixOS packages
    """
    logger.info("Getting package statistics")

    # Get context using the helper function
    context = get_context_or_fallback(context, "nixos_context")

    try:
        results = context.get_package_stats()

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


def register_nixos_tools(mcp) -> None:
    """
    Register all NixOS tools with the MCP server.

    Args:
        mcp: The MCP server instance
    """
    # Explicitly register tools with function handle to ensure proper serialization
    mcp.tool()(nixos_search)
    mcp.tool()(nixos_info)
    mcp.tool()(nixos_stats)
