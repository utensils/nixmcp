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
NixMCP is a Model Context Protocol (MCP) server for NixOS resources. It provides MCP-compatible endpoints that allow AI assistants to search and retrieve information about NixOS packages and system options.

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

## Tool Endpoints

The server implements the following MCP tools:

- `search_nixos`: Search for packages, options, or programs with automatic wildcard fallback
- `get_nixos_package`: Get detailed information about a specific package
- `get_nixos_option`: Get detailed information about a specific NixOS option
- `advanced_search`: Perform complex queries using Elasticsearch query syntax
- `package_statistics`: Get statistical information about NixOS packages
- `version_search`: Search for packages with specific version patterns

## System Requirements

### Elasticsearch API Access (Required)
The server requires access to the NixOS Elasticsearch API to function:

1. Create a `.env` file with your NixOS Elasticsearch credentials:
```
ELASTICSEARCH_URL=https://search.nixos.org/backend/latest-42-nixos-unstable/_search
ELASTICSEARCH_USER=your_username
ELASTICSEARCH_PASSWORD=your_password
```

2. The server will authenticate with the Elasticsearch API using these credentials.

The server requires these credentials to access the NixOS package and option data.

## Build & Run Commands

### Using Nix Develop (Recommended)
- Development environment: `nix develop`
- Run server: `run [--port=PORT]`
- Run tests: `run-tests`
- List all commands: `menu`
- Development commands:
  - `setup`: Set up Python environment (automatically uses uv if available)
  - `setup-uv`: Install uv for faster Python package management
  - `lint`: Run Black formatter on Python code

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
- Follow PEP 8 naming conventions:
  - snake_case for functions and variables
  - CamelCase for classes
- Error handling: Use try/except with specific exceptions
- Docstrings: Use Google-style docstrings with function descriptions
- Prefer explicit error handling over bare except clauses
- Cache expensive operations where appropriate
- Types: Use static typing with Optional, Dict, List, etc.