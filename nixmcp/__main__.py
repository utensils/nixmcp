#!/usr/bin/env python
"""
CLI entry point for NixMCP server.
"""

from nixmcp.server import mcp

if __name__ == "__main__":
    mcp.run()
