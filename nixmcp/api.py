"""
API module for querying NixOS packages and options using Nix CLI tools.
"""

import json
import subprocess
from typing import Dict, List, Optional, Any


class NixosAPI:
    """API client for NixOS packages and options using local Nix installation."""
    
    def __init__(self):
        """Initialize the NixOS API client."""
        self._check_nix_installation()
    
    def _check_nix_installation(self) -> None:
        """Verify that Nix is installed and available."""
        try:
            subprocess.run(["nix", "--version"], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise RuntimeError("Nix installation not found. Please install Nix to use this tool.")
    
    def search_packages(self, query: str, channel: str = "unstable") -> List[Dict[str, Any]]:
        """
        Search for NixOS packages using nix search.
        
        Args:
            query: Search query string
            channel: NixOS channel (default: unstable)
            
        Returns:
            List of package information dictionaries
        """
        # Use nix search with JSON output
        cmd = ["nix", "search", f"nixpkgs/{channel}", query, "--json"]
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Parse the JSON output
            packages_data = json.loads(result.stdout)
            
            # Transform into our standardized format
            packages = []
            for pkg_attr, pkg_data in packages_data.items():
                # Extract attribute path and package name
                attr_path = pkg_attr
                name = pkg_data.get("pname", attr_path.split(".")[-1])
                
                package = {
                    "name": name,
                    "attribute_path": attr_path,
                    "version": pkg_data.get("version", ""),
                    "description": pkg_data.get("description", ""),
                    "homepage": pkg_data.get("meta", {}).get("homepage", ""),
                    "license": pkg_data.get("meta", {}).get("license", {}).get("fullName", ""),
                    "platforms": pkg_data.get("meta", {}).get("platforms", []),
                    "position": pkg_data.get("meta", {}).get("position", "")
                }
                packages.append(package)
                
            return packages
            
        except subprocess.CalledProcessError as e:
            print(f"Error searching packages: {e.stderr}")
            return []
    
    def get_package_metadata(self, attr_path: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metadata for a specific package.
        
        Args:
            attr_path: Attribute path of the package (e.g., "nixpkgs.python3")
            
        Returns:
            Dictionary with package metadata or None if not found
        """
        # Use nix-env to get detailed package info
        cmd = ["nix", "eval", "--json", f"{attr_path}.meta"]
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Parse the JSON output
            meta = json.loads(result.stdout)
            
            # Get basic package info
            basic_cmd = ["nix", "eval", "--json", 
                        f"{{ pname = {attr_path}.pname or \"\"; version = {attr_path}.version or \"\"; }}"]
            basic_result = subprocess.run(
                basic_cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            basic_info = json.loads(basic_result.stdout)
            
            # Combine the information
            return {
                "name": basic_info.get("pname", attr_path.split(".")[-1]),
                "attribute_path": attr_path,
                "version": basic_info.get("version", ""),
                "description": meta.get("description", ""),
                "homepage": meta.get("homepage", ""),
                "license": meta.get("license", {}).get("fullName", ""),
                "platforms": meta.get("platforms", []),
                "maintainers": meta.get("maintainers", []),
                "position": meta.get("position", "")
            }
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting package metadata: {e.stderr}")
            return None
    
    def search_options(self, query: str, channel: str = "unstable") -> List[Dict[str, Any]]:
        """
        Search for NixOS options.
        
        Args:
            query: Search query string
            channel: NixOS channel (default: unstable)
            
        Returns:
            List of option information dictionaries
        """
        # This requires NixOS options database or nixos-option tool
        # For now, we'll implement a simplified version using nixos-option if available
        
        try:
            # Check if nixos-option is available
            subprocess.run(
                ["which", "nixos-option"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Use nixos-option to search for the option
            cmd = ["nixos-option", query, "--xml"]
            result = subprocess.run(
                cmd,
                check=False,  # Don't check for success as it might return non-zero if option doesn't exist
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # This is a simplified approach - a real implementation would parse the XML output
            # and extract detailed option information
            
            if "not found" in result.stderr:
                return []
                
            # Basic parsing of the output to extract option info
            option = {
                "name": query,
                "description": "Option description unavailable",  # Would be extracted from XML
                "type": "unknown",  # Would be extracted from XML
                "default": "unknown"  # Would be extracted from XML
            }
            
            return [option]
            
        except (subprocess.SubprocessError, FileNotFoundError):
            print("nixos-option tool not available, options search is limited")
            # Fall back to a minimal implementation or return empty list
            return []
            
    def get_option_metadata(self, option_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metadata for a specific NixOS option.
        
        Args:
            option_name: Full name of the option (e.g., "services.nginx.enable")
            
        Returns:
            Dictionary with option metadata or None if not found
        """
        # Similar to search_options, but focused on a single option
        # A more complete implementation would parse the option definition from the Nix sources
        
        try:
            # Try using nixos-option if available
            subprocess.run(
                ["which", "nixos-option"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Use nixos-option to get option info
            cmd = ["nixos-option", option_name]
            result = subprocess.run(
                cmd,
                check=False,  # Don't check for success as it might return non-zero if option doesn't exist
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if "not found" in result.stderr:
                return None
                
            # Parse the output to extract option info
            lines = result.stdout.strip().split("\n")
            metadata = {}
            
            for line in lines:
                if ": " in line:
                    key, value = line.split(": ", 1)
                    metadata[key.strip()] = value.strip()
            
            # Format the result
            return {
                "name": option_name,
                "description": metadata.get("description", "No description available"),
                "type": metadata.get("type", "unknown"),
                "default": metadata.get("default value", "No default"),
                "example": metadata.get("example", "No example"),
                "declared_by": metadata.get("declared by", "Unknown")
            }
            
        except (subprocess.SubprocessError, FileNotFoundError):
            print("nixos-option tool not available, option metadata is limited")
            return None