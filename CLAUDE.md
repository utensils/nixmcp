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
The server implements two types of endpoints for accessing NixOS resources:

1. REST API endpoints:
   - `/api/package/{package_name}`: Direct package info
   - `/api/search/packages/{query}`: Package search
   - `/api/search/options/{query}`: Options search
   - `/api/option/{option_name}`: Option info

2. MCP endpoints:
   - `/mcp/resource?uri=nixos://package/{package_name}`: MCP-compatible package endpoint
   - `/mcp/resource?uri=nixos://search/packages/{query}`: MCP-compatible package search
   - `/mcp/resource?uri=nixos://search/options/{query}`: MCP-compatible options search
   - `/mcp/resource?uri=nixos://option/{option_name}`: MCP-compatible option info

The MCP implementation uses the FastMCP library from the Model Context Protocol (MCP) project. To properly register MCP resources, use:

```python
# Define the resource handler
async def get_resource(resource_id: str):
    # Implement handler logic
    return {"data": "result"}

# Register with the MCP server
@mcp.resource("nixos://resource/{resource_id}")
async def mcp_resource_handler(resource_id: str):
    return await get_resource(resource_id)
```

When implementing a custom MCP endpoint like we do with `/mcp/resource`, the implementation manually dispatches to the appropriate handler based on the URI.

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
python mcp_diagnose.py --es-only
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