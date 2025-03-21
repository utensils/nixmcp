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

## MCP Endpoint Implementation
The server implements standard MCP endpoints for accessing NixOS resources:

MCP resource endpoints:
- `/mcp/resource?uri=nixos://status`: Server status information
- `/mcp/resource?uri=nixos://package/{package_name}`: Package information
- `/mcp/resource?uri=nixos://package/{package_name}/{channel}`: Package information from specific channel
- `/mcp/resource?uri=nixos://search/packages/{query}`: Package search
- `/mcp/resource?uri=nixos://search/packages/{query}/{channel}`: Package search in specific channel
- `/mcp/resource?uri=nixos://search/options/{query}`: Options search
- `/mcp/resource?uri=nixos://option/{option_name}`: Option information

The MCP implementation uses the FastMCP library from the Model Context Protocol (MCP) project. Resources are registered using decorators:

```python
# Define the resource handler with decorator
@mcp.resource("nixos://package/{package_name}")
def package_resource(package_name: str) -> Dict[str, Any]:
    """Get information about a NixOS package"""
    return model_context.get_package(package_name)
```

The server also includes a custom `/mcp/resource` endpoint that manually dispatches to the appropriate handler based on the URI pattern, which ensures compatibility with various MCP client implementations.

## System Requirements

### Elasticsearch API Access (Required)
The server requires access to the NixOS Elasticsearch API to function:

1. Create a `.env` file with your NixOS Elasticsearch credentials:
```
ELASTICSEARCH_URL=https://search.nixos.org/backend/latest-42-nixos-unstable/_search
ELASTICSEARCH_USER=your_username
ELASTICSEARCH_PASSWORD=your_password
```

2. Test the connection:
```bash
python nixmcp_util.py elasticsearch
```

Without valid Elasticsearch credentials, the server will start but will not be able to search packages or provide metadata.

## Build & Run Commands

### Using Nix Develop (Recommended)
- Development environment: `nix develop`
- Run server: `run [--port=PORT]`
  - Run with hot reloading for development: `run-dev [--port=PORT]`
- Run tests (automatically manages server): `run-tests`
  - Run tests with existing server: `run-tests-with-server`
  - Run test mocks (no server needed): `run-tests-dry`
  - Run tests in debug mode: `run-tests-debug`
- List all commands: `menu`
- Development commands:
  - `setup`: Set up Python environment
  - `lint`: Run Black formatter on Python code
  - `typecheck`: Run mypy type checker on Python code

### Using Legacy Shell
- Legacy shell: `nix develop .#legacy`
- Run server: `python server.py`
- Install dependencies manually: `pip install -r requirements.txt`

## Project Structure Guidelines
- Keep the project structure clean and minimal
- Do not create unnecessary wrapper scripts; prefer using existing tools directly
- Use README.md to document common commands rather than creating separate scripts
- Keep all Python code in properly structured modules
- Test files can use pytest for automatic test discovery
- The main test_mcp.py file uses pytest fixtures for server management
- Tests are designed to work in any environment, with or without Nix packages
- Server is started/stopped automatically during tests

## Code Style Guidelines
- Python 3.11+ with type hints required
- Use consistent 4-space indentation
- Follow PEP 8 naming conventions:
  - snake_case for functions and variables
  - CamelCase for classes
- Error handling: Use try/except with specific exceptions
- Docstrings: Use triple-quoted strings with function descriptions
- Prefer explicit error handling over bare except clauses
- Cache expensive operations where appropriate
- Types: Use static typing with Optional, Dict, List, etc.
- New components should follow FastAPI patterns