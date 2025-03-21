# NixMCP - Model Context Protocol for NixOS Resources

[![CI](https://github.com/utensils/nixmcp/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/nixmcp/actions/workflows/ci.yml)

> **⚠️ UNDER DEVELOPMENT**: NixMCP is currently under active development. Some features may be incomplete or subject to change.

NixMCP is a Model Context Protocol (MCP) HTTP server that exposes NixOS packages and options to AI models. This server helps AI models access up-to-date information about NixOS resources, reducing hallucinations and outdated information.

Using the FastMCP framework, the server provides a REST API for accessing the NixOS Elasticsearch API to deliver accurate, up-to-date information about packages and options. It implements standard MCP resource endpoints and tools over HTTP that can be consumed by any MCP-compatible client.

## Features

- HTTP-based MCP server implementation for NixOS resources
- RESTful API to access NixOS packages and options through a standardized MCP interface
- Get detailed package and option metadata using direct Elasticsearch API access
- Connect seamlessly with Claude and other MCP-compatible AI models via HTTP
- Comprehensive MCP-compatible resource endpoints and tools exposed via REST API
- Rich search capabilities with automatic fallback to wildcard matching
- JSON-based responses for easy integration with any HTTP client

## MCP Implementation over HTTP

The server implements both MCP resources and tools for accessing NixOS information through a RESTful HTTP interface:

### MCP Resources (Accessed via HTTP GET)

- `nixos://status`: Server status information
- `nixos://package/{package_name}`: Package information
- `nixos://search/packages/{query}`: Package search
- `nixos://search/options/{query}`: Options search
- `nixos://option/{option_name}`: Option information

### MCP Tools (Accessed via HTTP POST)

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

# Run the server on the default HTTP port
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

To run the test suite:

```bash
# Inside the Nix development environment
run-tests
```

This runs basic tests for the server functionality.

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

### Available Resources and Tools

The server provides the following resources and tools via the HTTP-based Model Context Protocol:

#### MCP Resources

- `nixos://status` - Get server status information
- `nixos://package/{package_name}` - Get information about a specific package
- `nixos://search/packages/{query}` - Search for packages matching the query
- `nixos://search/options/{query}` - Search for options matching the query
- `nixos://option/{option_name}` - Get information about a specific NixOS option
- `nixos://search/programs/{program}` - Search for packages that provide specific programs
- `nixos://packages/stats` - Get statistics about NixOS packages

#### MCP Tools

- `search_nixos` - Search for packages, options, or programs with automatic wildcard fallback
- `get_nixos_package` - Get detailed information about a specific package
- `get_nixos_option` - Get detailed information about a specific NixOS option
- `advanced_search` - Perform complex queries using Elasticsearch query syntax
- `package_statistics` - Get statistical information about NixOS packages
- `version_search` - Search for packages with specific version patterns

### Implementation Details

The server implements standard MCP resource endpoints for NixOS packages and options using the FastMCP library, which provides a RESTful HTTP interface. The server exposes MCP resources and tools as HTTP endpoints that can be accessed by any HTTP client, including MCP-compatible AI models.

Resources are accessed via GET requests to `/mcp/resource?uri=...`, while tools are invoked via POST requests to `/mcp/tool` with a JSON payload. All responses are returned as JSON.

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

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. MCP is typically implemented over HTTP as a RESTful API, making it easy to integrate with any HTTP client or server.

MCP servers can expose:

- **Resources**: Data that can be loaded into an LLM's context (accessed via HTTP GET)
- **Tools**: Functions that the LLM can call to perform actions (accessed via HTTP POST)
- **Prompts**: Reusable templates for LLM interactions

This project implements the MCP specification using the FastMCP library, which provides a robust HTTP server implementation of the protocol.

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