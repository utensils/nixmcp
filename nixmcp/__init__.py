"""
NixMCP - Model Context Protocol server for NixOS and Home Manager resources.

This package provides MCP resources and tools for interacting with NixOS packages,
system options, and Home Manager configuration options.
"""

try:
    from importlib.metadata import version, PackageNotFoundError

    try:
        __version__ = version("nixmcp")
    except PackageNotFoundError:
        # Package is not installed, use a default version
        __version__ = "0.0.0"
except ImportError:
    # Fallback for Python < 3.8
    try:
        import pkg_resources

        __version__ = pkg_resources.get_distribution("nixmcp").version
    except Exception:
        __version__ = "0.0.0"
