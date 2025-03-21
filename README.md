# NixMCP - Model Context Protocol for NixOS Resources

[![CI](https://github.com/utensils/nixmcp/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/nixmcp/actions/workflows/ci.yml)

> **⚠️ UNDER DEVELOPMENT**: NixMCP is currently under active development. Some features may be incomplete or subject to change.

NixMCP is a Model Context Protocol (MCP) server that exposes NixOS packages and options to AI models. This server helps AI models access up-to-date information about NixOS resources, reducing hallucinations and outdated information.

Using the MCP framework, the server provides direct access to the NixOS Elasticsearch API to deliver accurate, up-to-date information about packages and options. It implements standard MCP resource endpoints and tools that can be consumed by any MCP-compatible client.

## Features

- MCP server implementation for NixOS resources
- Access NixOS packages and options through a standardized MCP interface
- Get detailed package and option metadata using direct Elasticsearch API access
- Connect seamlessly with Claude and other MCP-compatible AI models
- Comprehensive MCP-compatible resource endpoints and tools
- Rich search capabilities with automatic fallback to wildcard matching

## MCP Implementation

The server implements both MCP resources and tools for accessing NixOS information:

### MCP Resources

- `nixos://status`: Server status information
- `nixos://package/{package_name}`: Package information
- `nixos://search/packages/{query}`: Package search
- `nixos://search/options/{query}`: Options search
- `nixos://option/{option_name}`: Option information

### MCP Tools

- `search_nixos`: Search for packages or options with smart fallback to wildcard matching
- `get_nixos_package`: Get detailed information about a specific package
- `get_nixos_option`: Get detailed information about a specific NixOS option
- `advanced_search`: Perform complex queries using Elasticsearch query syntax
- `package_statistics`: Get statistical information about NixOS packages
- `version_search`: Search for packages with specific version patterns

## Quick Start

### Using Nix Develop (Recommended)

NixMCP uses the [devshell](https://github.com/numtide/devshell) project to provide a rich, interactive development environment with convenient commands:

```bash
# Enter the development shell (now the default)
nix develop

# List all available commands
menu

# Run the server (default port is 9421)
run

# Run on specific port
run --port=8080

# Run tests (automatically handles server startup/shutdown)
run-tests

# Format code
lint

# Set up with uv for faster dependency management (recommended)
setup-uv  # Install uv fast Python package installer
setup     # Will automatically use uv if installed
```

The project supports [uv](https://github.com/astral-sh/uv), a much faster alternative to pip, for Python dependency management. When uv is installed, all package installation commands will automatically use it for improved performance.

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
# Using pytest with server management
python -m pytest -xvs test_mcp.py
# OR using the test script directly which works even without pytest
python test_mcp.py
```

### Manual Setup

```bash
# Install required Python dependencies (using pip)
pip install -r requirements.txt

# OR install with uv (faster alternative to pip)
uv pip install -r requirements.txt

# Run the server
python server.py
```

### Testing the MCP Server

The server can be tested in several ways:

1. **Basic Testing:**
   ```bash
   # Inside the Nix development environment
   run-tests
   ```
   This runs basic tests for the server functionality.

2. **Manual Testing with curl:**
   ```bash
   # Test MCP resource endpoints
   curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://package/python"
   curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://search/packages/python"
   curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://search/options/postgresql"
   curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://option/services.nginx"
   curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://status"
   
   # Test MCP tools endpoint
   curl -X POST "http://localhost:9421/mcp/tool" \
     -H "Content-Type: application/json" \
     -d '{"name": "search_nixos", "arguments": {"query": "python", "search_type": "packages", "limit": 5}}'
   ```

### Prerequisites

The server can operate in two modes:

#### Elasticsearch API Mode (Recommended)

For optimal performance and up-to-date results, the server can directly access the NixOS Elasticsearch API:

1. **Elasticsearch Credentials**: Create a `.env` file in the project root with the following configuration:
   ```
   ELASTICSEARCH_URL=https://search.nixos.org/backend/latest-42-nixos-unstable/_search
   ELASTICSEARCH_USER=your_username
   ELASTICSEARCH_PASSWORD=your_password
   ```

2. The server will attempt to authenticate with these credentials on startup.

#### Local Nix Fallback Mode

If Elasticsearch credentials are not available or the connection fails, the server will fallback to the local Nix installation:

1. **Nix Package Manager**: The server will use your local Nix installation to query package data.
   - Install from: https://nixos.org/download.html

2. **Required Nix Channels**: The server expects the following channels to be available:
   - `nixpkgs` (pointing to nixpkgs-unstable)
   - `nixpkgs-unstable`

   If these channels are not present, you'll see a warning on startup. Add them with:
   ```bash
   nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs
   nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs-unstable
   nix-channel --update
   ```

### Available Resources

The server provides access to NixOS resources through the Model Context Protocol (MCP):

#### MCP Resources

These resources can be accessed by AI models using the MCP protocol:

- `nixos://status` - Get server status information
- `nixos://package/{package_name}` - Get information about a specific package
- `nixos://package/{package_name}/{channel}` - Get information about a specific package from a specific channel
- `nixos://search/packages/{query}` - Search for packages matching the query
- `nixos://search/packages/{query}/{channel}` - Search for packages matching the query in a specific channel
- `nixos://option/{option_name}` - Get information about a specific NixOS option
- `nixos://search/options/{query}` - Search for options matching the query

Example MCP resource URLs:
- `nixos://status` - Check server health and version information
- `nixos://package/python` - Get information about the python package
- `nixos://package/python/unstable` - Get information about the python package in the unstable channel
- `nixos://search/packages/python` - Search for packages containing "python"
- `nixos://search/options/postgresql` - Search for options related to PostgreSQL
- `nixos://option/services.postgresql.enable` - Get specific option details

#### MCP Endpoint

All MCP resources are accessed through the standard MCP endpoint:

- `GET /mcp/resource?uri={resource_uri}` - Access any MCP resource

#### Health & Debug Endpoints

- `GET /health` - Server health status
- `GET /debug/mcp-registered` - List of registered MCP resources

Example MCP resource calls:
```bash
# Get server status
curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://status"

# Get package information
curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://package/python"

# Search for packages
curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://search/packages/python"

# Search for options related to PostgreSQL
curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://search/options/postgresql"

# Get option information
curl -X GET "http://localhost:9421/mcp/resource?uri=nixos://option/services.nginx"

# Check registered MCP resources
curl -X GET "http://localhost:9421/debug/mcp-registered"
```

### Implementation Details

The server implements standard MCP resource endpoints for NixOS packages and options using the FastMCP library. It's designed to be used with any MCP-compatible client to provide AI models with up-to-date information about NixOS.

The server uses the NixOS Elasticsearch API when properly configured to provide rich, detailed information about packages and options. Without valid Elasticsearch credentials, the server will return simplified responses.

### Using with Claude

Once the server is running, you can use it with Claude by referencing NixOS resources in your prompts:

```
Please provide information about the Python package in NixOS.
~nixos://package/python

What configuration options are available for NGINX in NixOS?
~nixos://option/services.nginx

How do I set up PostgreSQL in NixOS?
~nixos://search/options/postgresql
```

Claude will automatically fetch the requested information through the MCP server.

## What is Model Context Protocol?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. MCP servers can expose:

- **Resources**: Data that can be loaded into an LLM's context
- **Tools**: Functions that the LLM can call to perform actions
- **Prompts**: Reusable templates for LLM interactions

## Development Guidelines

This project includes a `CLAUDE.md` file which serves as the source of truth for all development guidelines. The file contains:

- **MCP Implementation Guidelines**: Best practices for implementing MCP resources and tools
- **Code Style Rules**: Python styling, naming conventions, and typing requirements
- **Build & Run Commands**: Documentation of all available development commands
- **Project Structure Guidelines**: Rules for organizing code and resources

The CLAUDE.md file is synchronized with tool-specific files (`.windsurfrules`, `.cursorrules`, and `.goosehints`) to ensure consistent guidance across all development environments and AI assistants.

When contributing to this project, please follow the guidelines specified in `CLAUDE.md`.

## License

MIT