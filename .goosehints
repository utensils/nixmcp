# MCP-NixOS Project Guidelines

## Source of Truth & Code Patterns

- CLAUDE.md is the primary source of truth for coding rules
- Sync changes to other rule files: `.windsurfrules`, `.cursorrules`, `.goosehints`
- Always follow existing code patterns and module structure
- Maintain architectural boundaries and consistency

## Project Overview

MCP-NixOS provides MCP resources and tools for NixOS packages, system options, Home Manager configuration, and nix-darwin macOS configuration. Communication uses JSON-based messages over standard I/O.

## Architecture

### Core Components
- **Cache**: Simple in-memory and filesystem HTML caching
- **Clients**: Elasticsearch, Home Manager, nix-darwin, HTML
- **Contexts**: Application state management for each platform
- **Resources**: MCP resource definitions using URL schemes
- **Tools**: Search, info, and statistics tools
- **Utils**: Cross-platform helpers and cache management
- **Server**: FastMCP server implementation

### Implementation Guidelines

**Resources**
- Use consistent URL schemes: `nixos://`, `home-manager://`, `darwin://`
- Follow path hierarchy: `scheme://category/action/parameter`
- Parameters in curly braces: `nixos://package/{package_name}`
- Return structured data as dictionaries
- Errors: `{"error": message, "found": false}`

**Tools**
- Functions with type hints (return `str` for human-readable output)
- Include `context` parameter for dependency injection
- Detailed Google-style docstrings
- Catch exceptions for user-friendly error messages

**Context Management**
- Lifespan management for initialization/cleanup
- Eager loading with fallbacks and timeouts
- Prefer dependency injection over global state

**Best Practices**
- Type annotations (Optional, Union, List, Dict)
- Strict null safety with defensive programming
- Detailed error logging and user-friendly messages
- Support wildcard searches and handle empty results

## API Reference

### NixOS Resources & Tools
- Status, package info/search, option info/search, program search
- `nixos_search()`, `nixos_info()`, `nixos_stats()`
- Multiple channels: unstable (default), stable (24.11)

### Home Manager Resources & Tools
- Status, option info/search, hierarchical lists, prefix paths
- `home_manager_search()`, `home_manager_info()`, `home_manager_options_by_prefix()`

### nix-darwin Resources & Tools
- Status, option info/search, category lists, prefix paths
- `darwin_search()`, `darwin_info()`, `darwin_options_by_prefix()`

## System Requirements

### APIs & Configuration
- Elasticsearch API for NixOS features
- HTML parsing for Home Manager and nix-darwin
- Multi-level caching with filesystem persistence
- Environment configuration via ENV variables

### Configuration
- `LOG_LEVEL`, `LOG_FILE`
- `MCP_NIXOS_CACHE_DIR`, `MCP_NIXOS_CACHE_TTL`
- `ELASTICSEARCH_URL`, `ELASTICSEARCH_USER`, `ELASTICSEARCH_PASSWORD`

## Development

### Testing
- 80%+ code coverage with pytest
- Static type checking (zero-tolerance policy)
- Linting with Black and Flake8
- Test organization mirrors module structure
- Use dependency injection for testable components

### Installation & Usage
- Install: `pip install mcp-nixos`, `uv pip install mcp-nixos`, `uvx mcp-nixos`
- Claude Code configuration: Add to `~/.config/claude/config.json`
- Development: `nix develop`, `run`, `run-tests`, `lint`, `format`

### Code Style
- Python 3.11+ with strict type hints
- PEP 8 naming conventions
- Google-style docstrings
- Black formatting, 120 char line limit
- Strict null safety practices
- Zero-tolerance for type errors