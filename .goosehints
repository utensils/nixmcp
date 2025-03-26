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
NixMCP is a Model Context Protocol (MCP) server for NixOS resources and Home Manager configuration options. It provides MCP resources and tools that allow AI assistants to search and retrieve information about NixOS packages, system options, and Home Manager user configuration options. Communication happens over standard input/output streams using a JSON-based message format.

## Project Structure
The codebase follows a modular architecture:

- `nixmcp/cache/` - Caching components (SimpleCache)
- `nixmcp/clients/` - API clients (ElasticsearchClient, HomeManagerClient)
- `nixmcp/contexts/` - Application contexts (NixOSContext, HomeManagerContext)
- `nixmcp/resources/` - MCP resource definitions 
- `nixmcp/tools/` - MCP tool implementations
- `nixmcp/utils/` - Utility functions and helpers
- `nixmcp/logging.py` - Centralized logging configuration
- `nixmcp/server.py` - Main entry point and FastMCP server implementation

This modular approach allows for better:
- Organization of code by responsibility
- Isolation during testing
- Separation of concerns
- Maintainability and extensibility

## MCP Implementation Guidelines

### Resource Definitions

When implementing MCP resources with `@mcp.resource`, follow these rules:

1. **URI Pattern Structure**:
   - Use the `nixos://` scheme for NixOS resources
   - Use the `home-manager://` scheme for Home Manager resources
   - Follow consistent path hierarchy: `scheme://category/action/parameter`
   - Place parameters in curly braces: `nixos://package/{package_name}`

2. **Resource Function Implementation**:
   - Add type hints for all parameters and return values
   - Include a clear docstring describing the resource
   - Return structured data as a dictionary
   - Implement proper error handling with `{"error": message, "found": false}` pattern

3. **Example Resource**:
   ```python
   # Resource function in nixmcp/resources/nixos_resources.py
   def package_resource(package_name: str, nixos_context) -> Dict[str, Any]:
       """Get detailed information about a NixOS package."""
       logger.info(f"Handling package resource request for {package_name}")
       return nixos_context.get_package(package_name)
   
   # Registration in register_nixos_resources function
   @mcp.resource("nixos://package/{package_name}")
   def package_resource_handler(package_name: str):
       return package_resource(package_name, get_nixos_context())
   ```

### Tool Definitions

When implementing MCP tools with `@mcp.tool()`, follow these rules:

1. **Function Signature**:
   - Use clear, descriptive function names
   - Add type hints for all parameters and return values
   - Make return type `str` for human-readable output
   - Include optional `context` parameter for dependency injection in tests

2. **Documentation**:
   - Always include detailed docstrings
   - Use Google-style docstring format with Args/Returns sections
   - Document all parameters including their purpose and constraints
   - Document return format and possible error conditions

3. **Error Handling**:
   - Catch all exceptions and return user-friendly error messages
   - Include suggestions for how to fix common errors
   - For complex tools, return structured error information as formatted text

4. **Dependency Injection**:
   - All tool functions should accept an optional context parameter
   - Fall back to global contexts only when no context is provided
   - This allows for clean testing without patching global state

5. **Example Tool**:
   ```python
   def nixos_search(query: str, type: str = "packages", limit: int = 20, channel: str = "unstable", context=None) -> str:
       """
       Search for NixOS packages, options, or programs.
       
       Args:
           query: The search term
           type: What to search for - "packages", "options", or "programs"
           limit: Maximum number of results to return (default: 20)
           channel: NixOS channel to search (default: "unstable", can also be "24.11")
           context: Optional context object for dependency injection in tests
       
       Returns:
           Results formatted as text
       """
       logger.info(f"Searching for {type} with query '{query}' in channel '{channel}'")

       # Validate parameters
       valid_types = ["packages", "options", "programs"]
       if type.lower() not in valid_types:
           return f"Error: Invalid type. Must be one of: {', '.join(valid_types)}"

       # Use provided context or fallback to global context
       if context is None:
           # Import here to avoid circular imports
           import nixmcp.server
           context = nixmcp.server.nixos_context
           
       # Implementation with proper error handling
       try:
           # Set the channel for search
           context.es_client.set_channel(channel)
           
           # Search logic using the context
           if type.lower() == "packages":
               result = context.search_packages(query, limit=limit)
               return format_packages_result(result)
           elif type.lower() == "options":
               result = context.search_options(query, limit=limit)
               return format_options_result(result)
           else:  # programs
               result = context.search_programs(query, limit=limit)
               return format_programs_result(result)
       except Exception as e:
           logger.error(f"Error in nixos_search: {e}", exc_info=True)
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
       nixos_context = NixOSContext()
       home_manager_context = HomeManagerContext()
       
       try:
           # We yield our contexts that will be accessible in all handlers
           yield {"nixos_context": nixos_context, "home_manager_context": home_manager_context}
       except Exception as e:
           logger.error(f"Error in server lifespan: {e}")
           raise
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

3. **Dependency Injection**:
   - Avoid direct use of global state in function implementations
   - Always accept context parameters in resource functions
   - Use optional context parameters in tool functions with fallback to globals
   - This pattern improves testability and reduces coupling between components
   - Resource function example:
     ```python
     def resource_function(param: str, context) -> Dict[str, Any]:
         """Resource function that requires a context."""
         # Context is required parameter, no fallback to global
         return context.get_something(param)
     ```
   - Tool function example:
     ```python
     def tool_function(param1: str, param2: int, context=None) -> str:
         """Tool function with optional context parameter."""
         # Use provided context or fall back to global
         if context is None:
             # Import here to avoid circular imports
             import nixmcp.server
             context = nixmcp.server.global_context
         # Use context instead of global state
         return context.do_something(param1, param2)
     ```

4. **Common Patterns**:
   - For search tools, always handle empty results gracefully
   - Include pagination parameters (limit, offset) where appropriate
   - Provide clear formatting of results for human readability
   - Add wildcards or fuzzy matching for improved search experience

5. **Error Handling**:
   - Log all errors with appropriate detail
   - Return user-friendly error messages
   - Include suggestions for resolving errors when possible
   - For resources, use standard error format with "error" and "found" fields

## Resource Endpoints

The server implements the following MCP resource endpoints:

### NixOS Resource Endpoints

- `nixos://status`: NixOS server status information
- `nixos://package/{package_name}`: NixOS package information
- `nixos://search/packages/{query}`: NixOS package search
- `nixos://search/options/{query}`: NixOS options search
- `nixos://option/{option_name}`: NixOS option information
- `nixos://search/programs/{program}`: Search for packages providing specific programs
- `nixos://packages/stats`: NixOS package statistics

### Home Manager Resource Endpoints

- `home-manager://status`: Home Manager context status information
- `home-manager://search/options/{query}`: Home Manager options search
- `home-manager://option/{option_name}`: Home Manager option information
- `home-manager://options/stats`: Home Manager options statistics

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

### NixOS Tools

- `nixos_search`: Search for packages, options, or programs with automatic wildcard handling
  - Supports channel selection (`unstable`, `24.11`)
  - Optimized for hierarchical path searching (services.postgresql.*)
- `nixos_info`: Get detailed information about a specific package or option
  - Supports channel selection (`unstable`, `24.11`)
- `nixos_stats`: Get statistical information about NixOS packages

### Home Manager Tools

- `home_manager_search`: Search for Home Manager options with automatic wildcard handling
  - Optimized for hierarchical path searching (programs.git.*)
  - Categorizes results by source and option groups
- `home_manager_info`: Get detailed information about a specific Home Manager option
  - Provides related options and usage examples
- `home_manager_stats`: Get statistical information about Home Manager options

## System Requirements

### Elasticsearch API Access (Required for NixOS features)
The server requires access to the NixOS Elasticsearch API to provide NixOS package and system option data:

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

### Home Manager Documentation Access (Required for Home Manager features)
The server requires internet access to fetch Home Manager documentation at startup:

1. The server fetches documentation from these URLs:
```
https://nix-community.github.io/home-manager/options.xhtml
https://nix-community.github.io/home-manager/nixos-options.xhtml
https://nix-community.github.io/home-manager/nix-darwin-options.xhtml
```

2. HTML documentation is parsed and indexed in memory for fast searching:
   - Parses options from `<div class="variablelist">` elements containing `<dl>/<dt>/<dd>` elements
   - Extracts option names, types, descriptions, defaults, and examples
   - Automatically categorizes options based on document structure and headings

3. Multiple specialized indexes for search:
   - Inverted index for text search across option names and descriptions
   - Prefix index for hierarchical path matches (e.g., programs.git.*)
   - Hierarchical index for path component matching

4. Background loading is used to avoid blocking server startup.

5. Results include option metadata such as type, description, default values and examples.

6. Related options are automatically suggested based on hierarchical paths.

7. Data is automatically refreshed when the server restarts to ensure current documentation.

### Testing
The project includes a comprehensive test suite:

1. Tests are written using pytest and include code coverage reporting
2. Use a balanced approach to testing:
   - Use mocks for external service dependencies (like Elasticsearch and Home Manager docs)  
   - Create integration tests with real API calls for critical paths
3. Test structure recommendations:
   - Create dedicated test files for each major component (e.g., ElasticsearchClient, HomeManagerClient)
   - Test both success paths and error handling
   - Test caching behavior where applicable
   - Use parameterized tests for different input variations
4. Test dependency injection:
   - For resource functions: create mock contexts and pass them directly to the resource functions
   - For tool functions: pass mock contexts directly using the `context` parameter
   - Avoid patching global state whenever possible
   - Validate mocks are called with the correct arguments
   - This approach isolates tests and prevents interference between test cases
   - Example:
     ```python
     def test_resource_function():
         # Create a mock context
         mock_context = Mock()
         mock_context.get_something.return_value = {"key": "value"}
         
         # Call the resource function with the mock context
         result = resource_function("param", mock_context)
         
         # Verify the result and that mock was called correctly
         assert result["key"] == "value"
         mock_context.get_something.assert_called_once_with("param")
     ```
5. Test async components:
   - Use pytest-asyncio for testing async code
   - Properly wrap async tests with `async_to_sync` decorator for compatibility
   - Be careful with exception handling tests in async context managers
6. The test suite is designed to be resilient to API changes by checking response structure rather than exact content
7. Current target code coverage is approximately 80%

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

#### Automatic Publishing with GitHub Actions

The repository is configured to automatically publish to PyPI when a new tag is pushed:

1. Update the version in `pyproject.toml`
2. Commit the changes
3. Create and push a new tag:
   ```bash
   git tag v0.1.1  # Use semantic versioning
   git push origin v0.1.1
   ```

GitHub Actions will run tests and then publish to PyPI automatically using trusted publishing.

#### Manual Publishing

You can also publish manually:

1. Use the publish command (if using Nix Develop):
   ```bash
   nix develop
   publish
   ```

2. Or manually publish with:
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

By default, nixmcp logs only to the console (stdout/stderr), which is captured by Claude Code. If you need file logging, add `"NIX_MCP_LOG": "/path/to/log/file.log"` to the env object.

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
  - Flake8 configuration: max-line-length=120, ignore=E402,E203 (E402 for imports not at top of file, E203 for whitespace before ':' which conflicts with Black's formatting)
  - Run full test suite with coverage to monitor test quality
  - Extract common logic into helper functions to reduce duplication