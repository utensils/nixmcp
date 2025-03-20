"""
Model Context Protocol (MCP) implementation for NixOS resources.

This module provides functionality to expose NixOS packages and options 
to AI models in a structured format.
"""

import json
from typing import Dict, List, Optional, Any, Union

from .api import NixosAPI


class ModelContext:
    """
    ModelContext class for providing NixOS resources to AI models.
    
    This class allows AI models to access up-to-date information about
    NixOS packages and options.
    """

    def __init__(self):
        """Initialize the ModelContext with a NixosAPI instance."""
        self.api = NixosAPI()
        self.cache: Dict[str, Any] = {}  # Simple in-memory cache

    def query_package(self, package_name: str, channel: str = "unstable") -> Optional[Dict[str, Any]]:
        """
        Query details about a specific NixOS package.
        
        Args:
            package_name: Name of the package to query
            channel: NixOS channel to query (default: unstable)
            
        Returns:
            Dictionary with package details or None if not found
        """
        cache_key = f"package:{channel}:{package_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        # First try exact attribute path
        if "." in package_name:  # Likely an attribute path
            pkg_metadata = self.api.get_package_metadata(package_name)
            if pkg_metadata:
                self.cache[cache_key] = pkg_metadata
                return pkg_metadata
        
        # Otherwise search by name
        results = self.api.search_packages(package_name, channel=channel)
        
        # Filter for exact or close match
        package = next((p for p in results if p.get("name") == package_name), None)
        if not package and results:
            # Take first result if no exact match
            package = results[0]
        
        if package:
            # If we found it by search, get detailed metadata
            attr_path = package.get("attribute_path")
            if attr_path:
                detailed = self.api.get_package_metadata(attr_path)
                if detailed:
                    package = detailed
            
            self.cache[cache_key] = package
            
        return package

    def query_option(self, option_name: str, channel: str = "unstable") -> Optional[Dict[str, Any]]:
        """
        Query details about a specific NixOS option.
        
        Args:
            option_name: Name of the option to query
            channel: NixOS channel to query (default: unstable)
            
        Returns:
            Dictionary with option details or None if not found
        """
        cache_key = f"option:{channel}:{option_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Try direct metadata query first
        option = self.api.get_option_metadata(option_name)
        
        if not option:
            # Fall back to search
            results = self.api.search_options(option_name, channel=channel)
            option = next((o for o in results if o.get("name") == option_name), None)
        
        if option:
            self.cache[cache_key] = option
            
        return option

    def format_context(
        self, 
        packages: Optional[List[str]] = None, 
        options: Optional[List[str]] = None, 
        max_entries: int = 10,
        format_type: str = "text"
    ) -> str:
        """
        Format NixOS resources as context for an AI model.
        
        Args:
            packages: List of package names to include
            options: List of option names to include
            max_entries: Maximum number of entries per category
            format_type: Output format ("text", "json", or "markdown")
            
        Returns:
            Formatted context string with package and option information
        """
        if format_type == "json":
            return self._format_json_context(packages, options, max_entries)
        elif format_type == "markdown":
            return self._format_markdown_context(packages, options, max_entries)
        else:
            return self._format_text_context(packages, options, max_entries)
    
    def _format_text_context(
        self, 
        packages: Optional[List[str]] = None, 
        options: Optional[List[str]] = None, 
        max_entries: int = 10
    ) -> str:
        """Format context as plain text."""
        context = []
        
        if packages:
            context.append("NixOS Packages:")
            for i, pkg_name in enumerate(packages[:max_entries]):
                pkg = self.query_package(pkg_name)
                if pkg:
                    context.append(f"- {pkg.get('name')}: {pkg.get('description', 'No description')}")
                    context.append(f"  Version: {pkg.get('version', 'Unknown')}")
                    context.append(f"  Attribute: {pkg.get('attribute_path', 'Unknown')}")
                    context.append(f"  Homepage: {pkg.get('homepage', 'N/A')}")
            context.append("")
            
        if options:
            context.append("NixOS Options:")
            for i, opt_name in enumerate(options[:max_entries]):
                opt = self.query_option(opt_name)
                if opt:
                    context.append(f"- {opt.get('name')}: {opt.get('description', 'No description')}")
                    context.append(f"  Type: {opt.get('type', 'Unknown')}")
                    context.append(f"  Default: {opt.get('default', 'None')}")
                    if opt.get('example'):
                        context.append(f"  Example: {opt.get('example')}")
            context.append("")
            
        return "\n".join(context)
    
    def _format_markdown_context(
        self, 
        packages: Optional[List[str]] = None, 
        options: Optional[List[str]] = None, 
        max_entries: int = 10
    ) -> str:
        """Format context as Markdown."""
        context = []
        
        if packages:
            context.append("## NixOS Packages")
            context.append("")
            
            for i, pkg_name in enumerate(packages[:max_entries]):
                pkg = self.query_package(pkg_name)
                if pkg:
                    context.append(f"### {pkg.get('name')}")
                    context.append("")
                    context.append(f"**Description**: {pkg.get('description', 'No description')}")
                    context.append("")
                    context.append(f"**Version**: `{pkg.get('version', 'Unknown')}`")
                    context.append(f"**Attribute**: `{pkg.get('attribute_path', 'Unknown')}`")
                    if pkg.get('homepage'):
                        context.append(f"**Homepage**: [{pkg.get('homepage')}]({pkg.get('homepage')})")
                    if pkg.get('license'):
                        context.append(f"**License**: {pkg.get('license')}")
                    context.append("")
            
        if options:
            context.append("## NixOS Options")
            context.append("")
            
            for i, opt_name in enumerate(options[:max_entries]):
                opt = self.query_option(opt_name)
                if opt:
                    context.append(f"### {opt.get('name')}")
                    context.append("")
                    context.append(f"**Description**: {opt.get('description', 'No description')}")
                    context.append("")
                    context.append(f"**Type**: `{opt.get('type', 'Unknown')}`")
                    context.append(f"**Default**: `{opt.get('default', 'None')}`")
                    if opt.get('example'):
                        context.append(f"**Example**: `{opt.get('example')}`")
                    if opt.get('declared_by'):
                        context.append(f"**Declared by**: {opt.get('declared_by')}")
                    context.append("")
            
        return "\n".join(context)
    
    def _format_json_context(
        self, 
        packages: Optional[List[str]] = None, 
        options: Optional[List[str]] = None, 
        max_entries: int = 10
    ) -> str:
        """Format context as JSON."""
        result = {
            "nixos_resources": {
                "packages": [],
                "options": []
            }
        }
        
        if packages:
            for i, pkg_name in enumerate(packages[:max_entries]):
                pkg = self.query_package(pkg_name)
                if pkg:
                    result["nixos_resources"]["packages"].append(pkg)
            
        if options:
            for i, opt_name in enumerate(options[:max_entries]):
                opt = self.query_option(opt_name)
                if opt:
                    result["nixos_resources"]["options"].append(opt)
            
        return json.dumps(result, indent=2)