# NixMCP - Model Context Protocol for NixOS resources

**Note: This project is under active development and is not yet ready for production use.**

NixMCP is a Model Context Protocol (MCP) server that exposes NixOS packages and options to AI models. This server helps AI models access up-to-date information about NixOS resources, reducing hallucinations and outdated information.

The server uses the local Nix installation to provide accurate, up-to-date information directly from the Nix package repository, rather than relying on web scraping or potentially outdated API sources.

## Features

- Access NixOS packages and options directly through a standardized MCP interface
- Get detailed package and option metadata from your local Nix installation
- Cache results to improve performance
- Connect directly with Claude and other MCP-compatible AI models
- MCP-compatible resource endpoints for packages and options

## Quick Start

### Using Nix Develop (Recommended)

NixMCP uses the [devshell](https://github.com/numtide/devshell) project to provide a rich, interactive development environment with convenient commands:

```bash
# Enter the development shell (now the default)
nix develop

# List all available commands
menu

# Run the server
run

# Run tests (automatically handles server startup/shutdown)
test

# Format and check code
lint
typecheck
```

### Using direnv with Nix

If you have [direnv](https://direnv.net/) installed, the included `.envrc` file will automatically activate the Nix development environment when you enter the directory:

```bash
# Allow direnv the first time (only needed once)
direnv allow

# Run the server (direnv automatically loads the Nix environment)
python server.py
```

### Using Legacy Shell

```bash
# If you need the legacy shell without the menu system
nix develop .#legacy

# Run the server
python server.py

# Run tests (automatically handles server startup/shutdown)
python test_mcp.py
```

### Manual Setup

```bash
# Install required Python dependencies
pip install mcp>=1.4.0 fastapi uvicorn requests

# Run the server
python server.py
```

### Testing the MCP Server

The project includes comprehensive test coverage that can be run in several ways. These tests are designed to work in all environments, including those without Nix packages available:

1. **Automated Testing with Server Management:**
   ```bash
   # Inside the Nix development environment
   test
   
   # Or using Python directly (works even without pytest installed)
   python test_mcp.py
   ```
   This automatically starts the server, runs all tests, and shuts down the server. The test runner has a fallback mechanism that works even if pytest isn't installed.

2. **Dry Run Testing (No Server Required):**
   ```bash
   # Inside the Nix development environment
   test-dry
   
   # Or using Python directly
   python test_mcp.py --dry-run
   ```
   This runs mock tests without requiring a server.

3. **Testing with an Existing Server:**
   ```bash
   # Inside the Nix development environment (requires server running)
   test-with-server
   
   # Or using pytest directly
   python -m pytest -xvs test_mcp.py
   ```
   This runs tests against an already-running server.

4. **Manual Testing with curl:**
   ```bash
   # Test MCP package resource
   curl -X GET "http://localhost:8000/mcp/resource?uri=nixos://package/python"

   # Test MCP option resource
   curl -X GET "http://localhost:8000/mcp/resource?uri=nixos://option/services.nginx"
   ```

5. **Debug Testing:**
   ```bash
   # Inside the Nix development environment
   test-debug
   
   # Or using Python directly
   python test_mcp.py --debug
   ```
   This runs tests in debug mode with detailed output for troubleshooting.

6. **Exploring with the MCP UI:**
   - Open your browser to: http://localhost:8000/mcp
   - This provides a UI to explore MCP resources and tools

### Available Resources

The MCP server exposes the following resources that can be accessed by AI models:

- `nixos://package/{package_name}` - Get information about a specific package (using default unstable channel)
- `nixos://package/{package_name}/{channel}` - Get information about a specific package in a specific channel
- `nixos://option/{option_name}` - Get information about a specific NixOS option (using default unstable channel)
- `nixos://option/{option_name}/{channel}` - Get information about a specific NixOS option in a specific channel

Example resource URLs:
- `nixos://package/python` (uses default channel)
- `nixos://package/python/unstable` (explicitly specifies channel)

### Available Tools

The MCP server provides the following tools for AI models:

- `search_packages(query, channel, limit)` - Search for NixOS packages
- `search_options(query, channel, limit)` - Search for NixOS options
- `get_resource_context(packages, options, max_entries, format_type)` - Generate formatted context

Note: Currently only package and option resource endpoints are implemented. Tools will be added in future updates.

### Using with Claude

Once the server is running, you can use it with Claude by referencing NixOS resources in your prompts:

```
Please provide information about the Python package in NixOS.
~nixos://package/python

What configuration options are available for NGINX in NixOS?
~nixos://option/services.nginx
```

Claude will automatically fetch the requested information through the MCP server.

## What is Model Context Protocol?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. MCP servers can expose:

- **Resources**: Data that can be loaded into an LLM's context
- **Tools**: Functions that the LLM can call to perform actions
- **Prompts**: Reusable templates for LLM interactions

## Development Guidelines

This project includes a `CLAUDE.md` file which contains build commands, code style guidelines, and other development best practices. This file serves as the source of truth for project conventions and is synchronized with other tool-specific files (`.windsurfrules`, `.cursorrules`, and `.goosehints`).

When contributing to this project, please follow the guidelines specified in `CLAUDE.md`.

## License

MIT