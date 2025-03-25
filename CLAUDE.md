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

## Project Overview
NixMCP is a Model Context Protocol (MCP) server for NixOS resources. It provides MCP resources and tools that allow AI assistants to search and retrieve information about NixOS packages and system options. Communication happens over standard input/output streams using a JSON-based message format.

## MCP Implementation Guidelines

### Resource Definitions

When implementing MCP resources with `@mcp.resource`, follow these rules:

1. **URI Pattern Structure**:
   - Use the `nixos://` scheme for all resources
   - Follow consistent path hierarchy: `scheme://category/action/parameter`
   - Place parameters in curly braces: `nixos://package/{package_name}`

2. **Resource Function Implementation**:
   - Add type hints for all parameters and return values
   - Include a clear docstring describing the resource
   - Return structured data as a dictionary
   - Implement proper error handling with `{"error": message, "found": false}` pattern

3. **Example Resource**:
   ```python
   @mcp.resource("nixos://package/{package_name}")
   def package_resource(package_name: str) -> Dict[str, Any]:
       """Get detailed information about a NixOS package."""
       logger.info(f"Handling package resource request for {package_name}")
       return model_context.get_package(package_name)
   ```

### Tool Definitions

When implementing MCP tools with `@mcp.tool()`, follow these rules:

1. **Function Signature**:
   - Use clear, descriptive function names
   - Add type hints for all parameters and return values
   - Make return type `str` for human-readable output

2. **Documentation**:
   - Always include detailed docstrings
   - Use Google-style docstring format with Args/Returns sections
   - Document all parameters including their purpose and constraints
   - Document return format and possible error conditions

3. **Error Handling**:
   - Catch all exceptions and return user-friendly error messages
   - Include suggestions for how to fix common errors
   - For complex tools, return structured error information as formatted text

4. **Example Tool**:
   ```python
   @mcp.tool()
   def search_nixos(query: str, search_type: str = "packages", limit: int = 10) -> str:
       """
       Search for NixOS packages or options.
       
       Args:
           query: The search term
           search_type: Type of search - either "packages", "options", or "programs"
           limit: Maximum number of results to return (default: 10)
       
       Returns:
           Results formatted as text
       """
       # Implementation with proper error handling
       try:
           # Search logic here
           return formatted_results
       except Exception as e:
           logger.error(f"Error in search_nixos: {e}", exc_info=True)
           return f"Error performing search: {str(e)}\n\nTry simplifying your query."
   ```

### Context Management

1. **Lifespan Context Manager**:
   - Use the lifespan context manager for resource initialization
   - Initialize shared resources at startup and clean up on shutdown
   - Pass the context to resources and tools that need it

2. **Request Context**:
   - Use the Context parameter for tools that need request context
   - Access shared resources through the context object
   - Use context for progress reporting on long-running operations

3. **Example Lifespan Configuration**:
   ```python
   @asynccontextmanager
   async def app_lifespan(mcp_server: FastMCP):
       logger.info("Initializing NixMCP server")
       # Set up resources
       context = NixOSContext()
       
       try:
           # We yield our context that will be accessible in all handlers
           yield {"context": context}
       finally:
           # Cleanup on shutdown
           logger.info("Shutting down NixMCP server")
   ```

### Best Practices

1. **Resource vs. Tool Selection**:
   - Use resources for retrieving data
   - Use tools for actions, processing, or complex queries
   - Resources should be directly accessible by URI
   - Tools should provide user-friendly formatted output

2. **Type Annotations**:
   - Always include return type annotations
   - Use `Optional[Type]` for optional parameters
   - Use `Union[Type1, Type2]` for multiple possible types
   - Use `List[Type]`, `Dict[KeyType, ValueType]` for collections

3. **Common Patterns**:
   - For search tools, always handle empty results gracefully
   - Include pagination parameters (limit, offset) where appropriate
   - Provide clear formatting of results for human readability
   - Add wildcards or fuzzy matching for improved search experience

4. **Error Handling**:
   - Log all errors with appropriate detail
   - Return user-friendly error messages
   - Include suggestions for resolving errors when possible
   - For resources, use standard error format with "error" and "found" fields

## Resource Endpoints

The server implements the following MCP resource endpoints:

- `nixos://status`: Server status information
- `nixos://package/{package_name}`: Package information
- `nixos://search/packages/{query}`: Package search
- `nixos://search/options/{query}`: Options search
- `nixos://option/{option_name}`: Option information
- `nixos://search/programs/{program}`: Search for packages providing specific programs
- `nixos://packages/stats`: Package statistics

## Searching for NixOS Options

When searching for NixOS options, particularly for service configurations:

1. **Direct Hierarchical Paths**: Always use full hierarchical paths for precise option searching:
   - `services.postgresql` for all PostgreSQL options
   - `services.nginx.virtualHosts` for specific nginx virtual host options
   - `services.postgresql.settings` for PostgreSQL configuration settings

2. **Enhanced Service Option Handling**:
   - Special query formats are used for services.* hierarchical paths
   - Service paths get automatic helpful suggestions for common options
   - The system provides guidance on typical service option patterns
   - Related options are automatically shown to help with discoverability

3. **Elasticsearch Implementation**:
   - We connect directly to the NixOS search Elasticsearch API
   - The search utilizes the same index as packages but filters for type="option"
   - Hierarchical paths use special query handling with wildcards (services.postgresql*)
   - Specialized prefix and filter queries improve hierarchical path search accuracy
   - Queries follow the same format as the NixOS search site for maximum compatibility
   - Service paths are detected and given specialized query treatment
   - Multiple query strategies are used: exact match, prefix match, wildcard match

4. **Avoid Mocking API Responses**: 
   - Tests should use real ElasticSearch API calls where possible
   - Do not create mock responses with hardcoded data
   - The test suite is designed to be resilient to API changes by checking response structure rather than exact content

5. **Multiple Channel Support**:
   - Support searching across different NixOS channels (unstable, 24.11, etc.)
   - Channel selection is done via the channel parameter in search functions
   - Queries use the appropriate Elasticsearch index for the selected channel
   - The same query structure works across all channels

## Tool Endpoints

The server implements the following simplified MCP tools:

- `nixos_search`: Search for packages, options, or programs with automatic wildcard handling
  - Supports channel selection (`unstable`, `24.11`)
  - Optimized for hierarchical path searching (services.postgresql.*)
- `nixos_info`: Get detailed information about a specific package or option
  - Supports channel selection (`unstable`, `24.11`)
- `nixos_stats`: Get statistical information about NixOS packages

## System Requirements

### Elasticsearch API Access (Required)
The server requires access to the NixOS Elasticsearch API to function:

1. Credentials are hardcoded in server.py using the public NixOS search credentials, but can be overridden with environment variables:
```
ELASTICSEARCH_URL=https://search.nixos.org/backend  # Base URL, channel/index will be added automatically
ELASTICSEARCH_USER=aWVSALXpZv
ELASTICSEARCH_PASSWORD=X8gPHnzL52wFEekuxsfQ9cSh
```

2. The server will authenticate with the Elasticsearch API using these credentials.

3. Search indices are dynamically determined based on the selected channel:
```
latest-42-nixos-unstable   # For unstable channel
latest-42-nixos-24.11      # For 24.11 channel
```

4. Both packages and options are in the same index, but are differentiated by a "type" field.

The server requires these credentials to access the NixOS package and option data.

### Testing
The project includes a comprehensive test suite:

1. Tests are written using pytest and include code coverage reporting
2. Tests make real API calls to the Elasticsearch endpoints rather than using mocks
3. Tests are designed to be resilient to API changes and handle various response patterns
4. Current code coverage is approximately 72%

## Package Distribution

NixMCP is available on PyPI and can be installed with pip or uv. The package provides both a Python library for integration and a command-line tool for running the MCP server.

### Installation Methods

1. **With pip**:
   ```bash
   pip install nixmcp
   ```

2. **With uv**:
   ```bash
   uv pip install nixmcp
   ```

3. **Direct execution with uvx** (recommended for Claude Code integration):
   ```bash
   uvx nixmcp
   ```

### Publishing New Versions

To publish a new version:

1. Update the version in `pyproject.toml`
2. Use the publish command (if using Nix Develop):
   ```bash
   nix develop
   publish
   ```

3. Or manually publish with:
   ```bash
   # Install build tools
   pip install build twine
   
   # Build the package
   python -m build
   
   # Upload to PyPI
   twine upload --config-file ./.pypirc dist/*
   ```

### MCP Configuration

To configure Claude Code to use nixmcp, add to `~/.config/claude/config.json`:

```json
{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["nixmcp"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Build & Run Commands

### Using Nix Develop (Recommended)
- Development environment: `nix develop`
- Run server: `run [--port=PORT]`
- Run tests: `run-tests [--no-coverage]` (includes coverage report by default)
- List all commands: `menu`
- Development commands:
  - `setup`: Set up Python environment (automatically uses uv if available)
  - `setup-uv`: Install uv for faster Python package management
  - `lint`: Run Black formatter and Flake8 linter on Python code
  - `format`: Format code with Black (without linting)

### Package Management with UV (Recommended)
The project supports [uv](https://github.com/astral-sh/uv), a faster alternative to pip:

1. Install uv within the development environment:
   ```bash
   setup-uv
   ```

2. Use uv with any pip command:
   ```bash
   uv pip install <package>
   ```

3. All built-in commands (setup, run-tests, etc.) automatically use uv when available.

### Using Legacy Shell
- Legacy shell: `nix develop .#legacy`
- Run server: `python server.py`
- Install dependencies manually:
  - With pip: `pip install -r requirements.txt`
  - With uv (faster): `uv pip install -r requirements.txt`

## Project Structure Guidelines
- Keep the project structure clean and minimal
- Do not create unnecessary wrapper scripts; prefer using existing tools directly
- Use README.md to document common commands rather than creating separate scripts
- Keep all Python code in properly structured modules
- Test files should use pytest for automatic test discovery

## Code Style Guidelines
- Python 3.11+ with type hints required
- Use consistent 4-space indentation
- Line length: 120 characters maximum
- Follow PEP 8 naming conventions:
  - snake_case for functions and variables
  - CamelCase for classes
- Error handling: Use try/except with specific exceptions
- Docstrings: Use Google-style docstrings with function descriptions
- Prefer explicit error handling over bare except clauses
- Cache expensive operations where appropriate
- Types: Use static typing with Optional, Dict, List, etc.
- Code quality tools:
  - Use Black for code formatting with line-length=120
  - Use Flake8 for linting to catch issues like unused imports
  - Flake8 configuration: max-line-length=120, ignore=E402 (for test files with path manipulation)
  - Run full test suite with coverage to monitor test quality
  - Extract common logic into helper functions to reduce duplication