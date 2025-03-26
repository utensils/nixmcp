# CLAUDE.md - NixMCP Project Guidelines

## IMPORTANT: Source of Truth Rule
CLAUDE.md is the primary source of truth for coding rules and guidelines.
When updating rules:
1. Modify CLAUDE.md first
2. Run these commands to sync to other rule files:
   ```
   cp CLAUDE.md .windsurfrules
   cp CLAUDE.md .cursorrules
   cp CLAUDE.md .goosehints
   ```

## IMPORTANT: Match Existing Code Patterns
When modifying or adding to this codebase, always:
1. Follow the existing code style and patterns in each module
2. Study nearby code before making changes to understand the established approach
3. Maintain consistency with the surrounding code (naming, structure, error handling)
4. Respect the architectural boundaries between modules
5. Use the same patterns for similar functionality
6. Adhere to Python best practices while maintaining consistency with the codebase

This ensures the codebase remains cohesive and maintainable.

## Project Overview
NixMCP is a Model Context Protocol (MCP) server for NixOS resources and Home Manager configuration options. It provides MCP resources and tools that allow AI assistants to search and retrieve information about NixOS packages, system options, and Home Manager user configuration options. Communication happens over standard input/output streams using a JSON-based message format.

## Project Structure
The codebase follows a modular architecture:

- `nixmcp/__init__.py` - Package version and metadata
- `nixmcp/__main__.py` - Entry point for direct execution
- `nixmcp/cache/` - Caching components (SimpleCache)
- `nixmcp/clients/` - API clients (ElasticsearchClient, HomeManagerClient)
- `nixmcp/contexts/` - Application contexts (NixOSContext, HomeManagerContext)
- `nixmcp/resources/` - MCP resource definitions
- `nixmcp/tools/` - MCP tool implementations
- `nixmcp/utils/` - Utility functions and helpers
- `nixmcp/logging.py` - Centralized logging configuration
- `nixmcp/server.py` - FastMCP server implementation

## MCP Implementation Guidelines

### Resource Definitions
- Use `nixos://` scheme for NixOS resources, `home-manager://` for Home Manager
- Follow consistent path hierarchy: `scheme://category/action/parameter`
- Place parameters in curly braces: `nixos://package/{package_name}`
- Use type hints and clear docstrings 
- Return structured data as a dictionary
- For errors, use `{"error": message, "found": false}` pattern

### Tool Definitions
- Use clear function names with type hints (return type `str` for human-readable output)
- Include optional `context` parameter for dependency injection in tests
- Use detailed Google-style docstrings with Args/Returns sections
- Catch exceptions and return user-friendly error messages
- Use provided context or fall back to global contexts

### Context Management
- Use lifespan context manager for resource initialization
- Initialize shared resources at startup and clean up on shutdown
- Pass contexts to resources and tools that need them
- Prefer dependency injection over global state access

### Best Practices
- Use resources for retrieving data, tools for actions/processing with formatted output
- Always use proper type annotations (Optional, Union, List, Dict, etc.)
- Log all errors with appropriate detail
- Return user-friendly error messages with suggestions where possible
- For search tools, handle empty results gracefully and support wildcards

## MCP Resources

### NixOS Resources
- `nixos://status`: NixOS server status information
- `nixos://package/{package_name}`: NixOS package information
- `nixos://search/packages/{query}`: NixOS package search
- `nixos://search/options/{query}`: NixOS options search
- `nixos://option/{option_name}`: NixOS option information
- `nixos://search/programs/{program}`: Packages providing specific programs
- `nixos://packages/stats`: NixOS package statistics

### Home Manager Resources
- `home-manager://status`: Home Manager context status information
- `home-manager://search/options/{query}`: Home Manager options search
- `home-manager://option/{option_name}`: Home Manager option information
- `home-manager://options/stats`: Home Manager options statistics
- `home-manager://options/list`: Hierarchical list of all top-level options
- `home-manager://options/prefix/{option_prefix}`: Get options by prefix path
- Category-specific endpoints for various option groups:
  - `home-manager://options/programs`
  - `home-manager://options/services`
  - `home-manager://options/home`
  - And many more (accounts, fonts, gtk, xdg, etc.)

## MCP Tools

### NixOS Tools
- `nixos_search(query, type="packages", limit=20, channel="unstable", context=None)`: 
  Search for packages, options, or programs with automatic wildcard handling
- `nixos_info(name, type="package", channel="unstable", context=None)`: 
  Get detailed information about a specific package or option
- `nixos_stats(context=None)`: 
  Get statistical information about NixOS packages

### Home Manager Tools
- `home_manager_search(query, limit=20, context=None)`: 
  Search for Home Manager options with automatic wildcard handling
- `home_manager_info(name, context=None)`: 
  Get detailed information about a specific Home Manager option
- `home_manager_stats(context=None)`: 
  Get statistical information about Home Manager options
- `home_manager_list_options(context=None)`: 
  List all top-level Home Manager option categories
- `home_manager_options_by_prefix(option_prefix, context=None)`: 
  Get all Home Manager options under a specific prefix

## Searching for NixOS Options

### Best Practices
- Use full hierarchical paths for precise option searching:
  - `services.postgresql` for all PostgreSQL options
  - `services.nginx.virtualHosts` for nginx virtual hosts
  - Wildcards are automatically added where appropriate (services.postgresql*)
- Service paths get special handling with automatic suggestions
- Multiple query strategies are used: exact match, prefix match, wildcard match
- Multiple channels are supported (unstable, 24.11, etc.)

## System Requirements

### Elasticsearch API (NixOS features)
- Uses NixOS search Elasticsearch API
- Configure with environment variables (defaults provided):
  ```
  ELASTICSEARCH_URL=https://search.nixos.org/backend
  ELASTICSEARCH_USER=aWVSALXpZv
  ELASTICSEARCH_PASSWORD=X8gPHnzL52wFEekuxsfQ9cSh
  ```
- Supports multiple channels (unstable, 24.11) via different indices

### Home Manager Documentation (Home Manager features)
- Fetches and parses HTML docs from nix-community.github.io/home-manager/
- Options are indexed in memory with specialized search indices
- Background loading avoids blocking server startup
- Related options are automatically suggested based on hierarchical paths

## Configuration
- `LOG_LEVEL`: Set logging level (default: INFO)
- `LOG_FILE`: Optional log file path (default: logs to stdout/stderr)
- Environment variables for Elasticsearch API credentials (see above)

## Testing
- Use pytest with code coverage reporting (target: 80%)
- Use dependency injection for testable components:
  - Pass mock contexts directly to resource/tool functions
  - Avoid patching global state
- Mock external dependencies (Elasticsearch, Home Manager docs) 
- Test both success paths and error handling
- **IMPORTANT**: Mock test functions, not production code:
  ```python
  # GOOD: Clean production code with mocking in tests
  def production_function():
      result = make_api_request()
      return process_result(result)
  
  # In tests:
  @patch("module.make_api_request")
  def test_production_function(mock_api):
      mock_api.return_value = {"test": "data"}
      result = production_function()
      assert result == expected_result
  ```

## Installation and Usage

### Installation Methods
- pip: `pip install nixmcp`
- uv: `uv pip install nixmcp`
- uvx (for Claude Code): `uvx nixmcp`

### MCP Configuration
To configure Claude Code to use nixmcp, add to `~/.config/claude/config.json`:
```json
{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["nixmcp"],
      "env": {
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "/path/to/nixmcp.log"
      }
    }
  }
}
```

### Development Commands
- Development environment: `nix develop`
- Run server: `run [--port=PORT]`
- Run tests: `run-tests [--no-coverage]`
- List commands: `menu`
- Lint and format: `lint`, `format`
- Setup uv: `setup-uv`

## Code Style
- Python 3.11+ with type hints
- 4-space indentation, 120 characters max line length
- PEP 8 naming: snake_case for functions/variables, CamelCase for classes
- Google-style docstrings
- Specific exception handling (avoid bare except)
- Black for formatting, Flake8 for linting
- Flake8 config: max-line-length=120, ignore=E402,E203