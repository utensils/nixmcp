# NixMCP - Model Context Protocol for NixOS resources

**Note: This project is under active development and is not yet ready for production use.**

NixMCP is a Model Context Protocol (MCP) server that exposes NixOS packages and options to AI models. This server helps AI models access up-to-date information about NixOS resources, reducing hallucinations and outdated information.

The server uses the local Nix installation to provide accurate, up-to-date information directly from the Nix package repository, rather than relying on web scraping or potentially outdated API sources.

## Features

- Access NixOS packages and options directly through a standardized MCP interface
- Get detailed package and option metadata from your local Nix installation
- Cache results to improve performance
- Connect directly with Claude and other MCP-compatible AI models

## Quick Start

### Using direnv with Nix (Recommended)

If you have [direnv](https://direnv.net/) installed, the included `.envrc` file will automatically activate the Nix development environment when you enter the directory:

```bash
# Allow direnv the first time (only needed once)
direnv allow

# Run the server (direnv automatically loads the Nix environment)
python server.py
```

### Using Nix Directly

```bash
# Enter development shell which automatically sets up everything
nix develop

# Run the server
python server.py
```

### Manual Setup

```bash
# Install required Python dependencies
pip install mcp>=1.4.0 fastapi uvicorn

# Run the server
python server.py
```

### Available Resources

The MCP server exposes the following resources that can be accessed by AI models:

- `nixos://package/{package_name}?channel={channel}` - Get information about a specific package
- `nixos://option/{option_name}?channel={channel}` - Get information about a specific NixOS option

### Available Tools

The MCP server provides the following tools for AI models:

- `search_packages(query, channel, limit)` - Search for NixOS packages
- `search_options(query, channel, limit)` - Search for NixOS options
- `get_resource_context(packages, options, max_entries, format_type)` - Generate formatted context

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