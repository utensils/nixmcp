#!/usr/bin/env python
"""
Command-line interface for NixMCP.
"""

import argparse
import json
import sys
from typing import Any, Dict, Optional

from rich.console import Console
from rich.markdown import Markdown

from .model_context import ModelContext


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="NixMCP - Model Context Protocol for NixOS resources")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Package command
    pkg_parser = subparsers.add_parser("package", help="Query NixOS package information")
    pkg_parser.add_argument("name", help="Package name to query (can be name or attribute path)")
    pkg_parser.add_argument("--channel", default="unstable", help="NixOS channel (default: unstable)")
    pkg_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    pkg_parser.add_argument("--markdown", action="store_true", help="Output in Markdown format")
    
    # Option command
    opt_parser = subparsers.add_parser("option", help="Query NixOS option information")
    opt_parser.add_argument("name", help="Option name to query (e.g., services.nginx.enable)")
    opt_parser.add_argument("--channel", default="unstable", help="NixOS channel (default: unstable)")
    opt_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    opt_parser.add_argument("--markdown", action="store_true", help="Output in Markdown format")
    
    # Context command
    ctx_parser = subparsers.add_parser("context", help="Generate context for AI models")
    ctx_parser.add_argument("--packages", nargs="+", help="Package names to include in context")
    ctx_parser.add_argument("--options", nargs="+", help="Option names to include in context")
    ctx_parser.add_argument("--channel", default="unstable", help="NixOS channel (default: unstable)")
    ctx_parser.add_argument("--max-entries", type=int, default=10, help="Maximum entries per category")
    ctx_parser.add_argument("--format", choices=["text", "json", "markdown"], default="text",
                          help="Output format (default: text)")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for NixOS packages or options")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--type", choices=["package", "option"], default="package",
                             help="Type of resource to search (default: package)")
    search_parser.add_argument("--channel", default="unstable", help="NixOS channel (default: unstable)")
    search_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    search_parser.add_argument("--markdown", action="store_true", help="Output in Markdown format")
    search_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results (default: 10)")
    
    return parser.parse_args()


def get_format_type(args) -> str:
    """Determine the output format type based on args."""
    if hasattr(args, "format") and args.format:
        return args.format
    elif getattr(args, "json", False):
        return "json"
    elif getattr(args, "markdown", False):
        return "markdown"
    else:
        return "text"


def print_formatted_output(data: Any, format_type: str) -> None:
    """Print data in the specified format."""
    console = Console()
    
    if format_type == "json":
        if isinstance(data, str):
            print(data)  # Already formatted as JSON string
        else:
            print(json.dumps(data, indent=2))
    elif format_type == "markdown":
        if isinstance(data, str):
            console.print(Markdown(data))
        else:
            # Convert dict to markdown
            md = ["# Nix Resource Information", ""]
            for key, value in data.items():
                if key != "name" and value:  # Skip name as it's used in the title
                    if isinstance(value, (dict, list)):
                        md.append(f"**{key}**: `{json.dumps(value)}`")
                    else:
                        md.append(f"**{key}**: {value}")
            console.print(Markdown("\n".join(md)))
    else:
        # Plain text
        if isinstance(data, str):
            print(data)
        elif isinstance(data, dict):
            for key, value in data.items():
                if value:  # Only print non-empty values
                    if isinstance(value, (dict, list)):
                        print(f"{key}: {json.dumps(value, indent=2)}")
                    else:
                        print(f"{key}: {value}")
        else:
            print(data)


def main():
    """Main CLI entrypoint."""
    args = parse_args()
    context = ModelContext()
    
    if args.command == "package":
        package = context.query_package(args.name, channel=args.channel)
        if not package:
            print(f"Package '{args.name}' not found in channel '{args.channel}'")
            return 1
            
        format_type = get_format_type(args)
        if format_type == "json":
            print_formatted_output(package, format_type)
        else:
            # For text or markdown, create a formatted context with just this package
            context_str = context.format_context(
                packages=[args.name],
                format_type=format_type
            )
            print_formatted_output(context_str, format_type)
            
    elif args.command == "option":
        option = context.query_option(args.name, channel=args.channel)
        if not option:
            print(f"Option '{args.name}' not found in channel '{args.channel}'")
            return 1
            
        format_type = get_format_type(args)
        if format_type == "json":
            print_formatted_output(option, format_type)
        else:
            # For text or markdown, create a formatted context with just this option
            context_str = context.format_context(
                options=[args.name],
                format_type=format_type
            )
            print_formatted_output(context_str, format_type)
            
    elif args.command == "context":
        if not args.packages and not args.options:
            print("Error: At least one of --packages or --options must be provided")
            return 1
            
        format_type = get_format_type(args)
        context_str = context.format_context(
            packages=args.packages,
            options=args.options,
            max_entries=args.max_entries,
            format_type=format_type
        )
        print_formatted_output(context_str, format_type)
        
    elif args.command == "search":
        format_type = get_format_type(args)
        
        if args.type == "package":
            results = context.api.search_packages(args.query, channel=args.channel)
            if not results:
                print(f"No packages found matching '{args.query}' in channel '{args.channel}'")
                return 1
                
            # Limit results
            results = results[:args.limit]
                
            if format_type == "json":
                print_formatted_output({"results": results}, format_type)
            elif format_type == "markdown":
                md = ["# Search Results", ""]
                for pkg in results:
                    md.append(f"## {pkg.get('name')}")
                    md.append("")
                    md.append(f"**Description**: {pkg.get('description', 'No description')}")
                    md.append(f"**Attribute**: `{pkg.get('attribute_path')}`")
                    md.append(f"**Version**: `{pkg.get('version', 'Unknown')}`")
                    md.append("")
                print_formatted_output("\n".join(md), format_type)
            else:
                for pkg in results:
                    print(f"{pkg.get('name')} ({pkg.get('version', 'Unknown')})")
                    print(f"  Attribute: {pkg.get('attribute_path')}")
                    print(f"  {pkg.get('description', 'No description')}")
                    print("")
                    
        elif args.type == "option":
            results = context.api.search_options(args.query, channel=args.channel)
            if not results:
                print(f"No options found matching '{args.query}' in channel '{args.channel}'")
                return 1
                
            # Limit results
            results = results[:args.limit]
                
            if format_type == "json":
                print_formatted_output({"results": results}, format_type)
            elif format_type == "markdown":
                md = ["# Search Results", ""]
                for opt in results:
                    md.append(f"## {opt.get('name')}")
                    md.append("")
                    md.append(f"**Description**: {opt.get('description', 'No description')}")
                    md.append(f"**Type**: `{opt.get('type', 'Unknown')}`")
                    md.append(f"**Default**: `{opt.get('default', 'None')}`")
                    md.append("")
                print_formatted_output("\n".join(md), format_type)
            else:
                for opt in results:
                    print(f"{opt.get('name')}")
                    print(f"  Type: {opt.get('type', 'Unknown')}")
                    print(f"  {opt.get('description', 'No description')}")
                    print("")
        
    else:
        print("Error: No command specified. Use --help for usage information.")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())