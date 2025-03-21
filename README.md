# NixMCP - Model Context Protocol for NixOS Resources

[![CI](https://github.com/utensils/nixmcp/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/nixmcp/actions/workflows/ci.yml)

> **⚠️ UNDER DEVELOPMENT**: NixMCP is currently under active development. Some features may be incomplete or subject to change.

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

- `search_nixos` - Search for packages, options, or programs with automatic wildcard fallback
- `get_nixos_package` - Get detailed information about a specific package
- `get_nixos_option` - Get detailed information about a specific NixOS option
- `advanced_search` - Perform complex queries using Elasticsearch query syntax
- `package_statistics` - Get statistical information about NixOS packages
- `version_search` - Search for packages with specific version patterns

## Quick Start

### Using Nix Develop (Recommended)

```bash
# Enter the development shell
nix develop

# List all available commands
menu

# Run the server
run

# Run with a specific port for debugging
run --port=8080

# Run tests
run-tests

# Format code
lint
```

### Prerequisites

The server requires access to the NixOS Elasticsearch API:

Create a `.env` file in the project root with the following configuration:
```
ELASTICSEARCH_URL=https://search.nixos.org/backend/latest-42-nixos-unstable/_search
ELASTICSEARCH_USER=your_username
ELASTICSEARCH_PASSWORD=your_password
```

## Using with Claude

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

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. MCP uses a JSON-based message format exchanged over various transport mechanisms (typically standard input/output streams).

This project implements the MCP specification using the FastMCP library, providing a bridge between AI models and NixOS resources.

## License

MIT