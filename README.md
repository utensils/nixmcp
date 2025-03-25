# NixMCP - Model Context Protocol for NixOS Resources

[![CI](https://github.com/utensils/nixmcp/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/nixmcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/nixmcp/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/nixmcp)
[![PyPI](https://img.shields.io/pypi/v/nixmcp.svg)](https://pypi.org/project/nixmcp/)
[![Python Versions](https://img.shields.io/pypi/pyversions/nixmcp.svg)](https://pypi.org/project/nixmcp/)

> **⚠️ UNDER ACTIVE DEVELOPMENT**: NixMCP is being actively maintained and improved. I'm just a fool fumbling through the codebase like a raccoon in a dumpster, but having fun along the way!

NixMCP is a Model Context Protocol (MCP) server that exposes NixOS packages and options to AI models. It provides AI models with up-to-date information about NixOS resources, reducing hallucinations and outdated information.

Using the FastMCP framework, the server provides MCP endpoints for accessing the NixOS Elasticsearch API to deliver accurate information about packages and options.

## Features

- MCP server implementation for NixOS resources
- Access to NixOS packages and options through a standardized MCP interface
- Get detailed package and option metadata using direct Elasticsearch API access
- Connect seamlessly with Claude and other MCP-compatible AI models
- Rich search capabilities with automatic wildcard matching
- JSON-based responses for easy integration with MCP clients

## MCP Implementation

The server implements both MCP resources and tools for accessing NixOS information:

### MCP Resources

- `nixos://status` - Get server status information
- `nixos://package/{package_name}` - Get information about a specific package
- `nixos://search/packages/{query}` - Search for packages matching the query
- `nixos://search/options/{query}` - Search for options matching the query
- `nixos://option/{option_name}` - Get information about a specific NixOS option
- `nixos://search/programs/{program}` - Search for packages that provide specific programs
- `nixos://packages/stats` - Get statistics about NixOS packages

### MCP Tools

- `nixos_search` - Search for packages, options, or programs with automatic wildcard handling
- `nixos_info` - Get detailed information about a specific package or option
- `nixos_stats` - Get statistical information about NixOS packages

#### Tool Usage Examples

```python
# Search for packages
nixos_search(query="firefox", type="packages", limit=10, channel="unstable")

# Search for system options
nixos_search(query="postgresql", type="options", channel="24.11")

# Search for programs
nixos_search(query="python", type="programs")

# Get package details
nixos_info(name="nixos.firefox", type="package", channel="unstable")

# Get option details
nixos_info(name="services.postgresql.enable", type="option", channel="24.11")

# Get package statistics
nixos_stats()
```

## Installation

### Using pip or uv

```bash
# Install with pip
pip install nixmcp

# Or install with uv
uv pip install nixmcp
```

### Using uvx (Recommended)

To use the package with uvx (uv execute), which runs Python packages directly without installing:

```bash
uvx nixmcp
```

## MCP Configuration

Add the following to your MCP configuration file:

```json
{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["nixmcp"],
      "env": {
        "LOG_LEVEL": "INFO"
        // Optionally add NIX_MCP_LOG if you want file logging:
        // "NIX_MCP_LOG": "/path/to/nixmcp.log"
      }
    }
  }
}
```

With this configuration:
- Logs are written to stdout/stderr only (captured by the Claude Code interface)
- No log files are created by default
- You can enable file logging by adding the NIX_MCP_LOG environment variable

### Environment Variables

You can customize the server behavior with these environment variables:

```
LOG_LEVEL=INFO        # Log level (DEBUG, INFO, WARNING, ERROR)
NIX_MCP_LOG=/path/log # Optional: If set to a non-empty value, logs to this file; otherwise logs only to console
```

### Releasing New Versions

To release a new version:

1. Update the version in `pyproject.toml`
2. Commit the changes
3. Tag the release:
   ```bash
   git tag v0.1.1  # Use semantic versioning
   git push origin v0.1.1
   ```

The GitHub Actions workflow will automatically test and publish the new version to PyPI.

## Elasticsearch Credentials

The server requires access to the NixOS Elasticsearch API. By default, the credentials are hardcoded in the server implementation for simplicity, but you can override them with environment variables:

```
ELASTICSEARCH_URL=https://search.nixos.org/backend  # Base URL, channel/index will be added automatically
ELASTICSEARCH_USER=your_username
ELASTICSEARCH_PASSWORD=your_password
```

## Development

### Using Nix Develop (Recommended)

```bash
# Enter the development shell
nix develop

# List all available commands
menu

# Run the server
run

# Run tests
run-tests

# Format code
lint

# Build and publish to PyPI
publish
```

## Testing Approach

The tests use real Elasticsearch API calls instead of mocks to ensure actual API compatibility. This approach:

- Tests actual API behavior rather than simplified mocks
- Validates error handling with real-world responses
- Detects changes in the API endpoints or structure
- Remains resilient to API changes by testing response structure

The project provides Nix-based development commands:
```bash
# Enter the development environment
nix develop

# Run tests with coverage report (default)
run-tests

# Run tests without coverage
run-tests --no-coverage

# Lint and format code
lint

# Format code only
format

# Show all available commands
menu
```

Current code coverage is tracked on [Codecov](https://codecov.io/gh/utensils/nixmcp).

## Using with Claude

### Setting up Claude Code with Nixmcp

1. Install the package globally or use uvx:
   ```bash
   pip install nixmcp
   # or
   uv pip install nixmcp
   ```

2. Configure Claude Code to use the nixmcp server by adding to your `~/.config/claude/config.json`:
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

3. If you prefer using pip-installed version:
   ```json
   {
     "mcpServers": {
       "nixos": {
         "command": "nixmcp"
       }
     }
   }
   ```

### Using Nixmcp with Claude

Once the server is configured, you can use it with Claude by referencing NixOS resources in your prompts:

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

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. MCP uses a JSON-based message format exchanged over various transport mechanisms (typically standard input/output streams).

This project implements the MCP specification using the FastMCP library, providing a bridge between AI models and NixOS resources.

## License

MIT