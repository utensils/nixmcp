# NixMCP - Model Context Protocol for NixOS Resources

[![CI](https://github.com/utensils/nixmcp/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/nixmcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/nixmcp/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/nixmcp)
[![PyPI](https://img.shields.io/pypi/v/nixmcp.svg)](https://pypi.org/project/nixmcp/)
[![Python Versions](https://img.shields.io/pypi/pyversions/nixmcp.svg)](https://pypi.org/project/nixmcp/)

> **⚠️ UNDER ACTIVE DEVELOPMENT**: NixMCP is being actively maintained and improved.

NixMCP is a Model Context Protocol (MCP) server that exposes NixOS packages, system options, and Home Manager configuration options to AI models. It provides up-to-date information about both NixOS and Home Manager resources, reducing hallucinations and outdated information.

> **NOTE:** MCP completions support is temporarily disabled as it's specified in the MCP protocol but not yet fully implemented in the MCP SDK. Completion support will be added once the upstream SDK implementation is available.

## Quick Start: For the Impatient Nixer

Look, we both know you're just going to skim this README and then complain when things don't work. So here's the bare minimum you need to add to your MCP configuration file to get started. Copy, paste, and get back to your regularly scheduled yak shaving:

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

There. Was that so hard? Now your AI assistant can actually give you correct information about NixOS instead of hallucinating package names from 2019.

## Features

- Complete MCP server implementation for NixOS and Home Manager resources
- Access to NixOS packages and system options through the NixOS Elasticsearch API
- Access to Home Manager configuration options through in-memory parsed documentation
- Get detailed package, system option, and Home Manager option metadata
- Connect seamlessly with Claude and other MCP-compatible AI models
- Rich search capabilities with automatic wildcard matching and hierarchical path support
- Intelligent context-based tool selection for different resource types
- JSON-based responses for easy integration with MCP clients
- Modular architecture with dedicated components for caching, API clients, contexts, resources, and tools
- In-memory search engine for fast option lookups
- Support for hierarchical paths like programs.git.* and services.postgresql.*
- Related options and contextual suggestions for better discoverability
- Background fetching and caching of documentation

> **Future Feature:** IDE-style completions (MCP completion/complete protocol) will be added once the MCP SDK implementation is ready.

## MCP Implementation

The server implements both MCP resources and tools for accessing NixOS and Home Manager information:

### MCP Resources

#### NixOS Resources
- `nixos://status` - Get NixOS server status information
- `nixos://package/{package_name}` - Get information about a specific package
- `nixos://search/packages/{query}` - Search for packages matching the query
- `nixos://search/options/{query}` - Search for NixOS options matching the query
- `nixos://option/{option_name}` - Get information about a specific NixOS option
- `nixos://search/programs/{program}` - Search for packages that provide specific programs
- `nixos://packages/stats` - Get statistics about NixOS packages

#### Home Manager Resources
- `home-manager://status` - "Is this thing on?" Check if the Home Manager context is alive and kicking
- `home-manager://search/options/{query}` - For when you can't remember that one option you saw that one time
- `home-manager://option/{option_name}` - Deep dive into a specific option (yes, it goes deeper than you think)
- `home-manager://options/stats` - For the data nerds who need to know how many options exist
- `home-manager://options/list` - The 10,000-foot view of Home Manager's option categories
- `home-manager://options/programs` - "How do I configure ALL THE THINGS?" All your favorite software options
- `home-manager://options/services` - Because running services manually is so 2010
- `home-manager://options/home` - Configure your $HOME directory without actually touching it
- `home-manager://options/accounts` - User account settings that won't lock you out (hopefully)
- `home-manager://options/fonts` - For people who judge others by their font choices
- `home-manager://options/gtk` - Make your GTK apps look less like they're from 2005
- `home-manager://options/qt` - For when you need your Qt apps to match your GTK apps
- `home-manager://options/xdg` - Because everyone loves the XDG specification, right? Right??
- `home-manager://options/wayland` - The future is now, old X11 man
- `home-manager://options/i18n` - For polyglots and those pretending to be
- `home-manager://options/manual` - RTFM, but make it declarative
- `home-manager://options/news` - Stay updated without doomscrolling social media
- `home-manager://options/nix` - Nix options for your Nix inside your Nix (we heard you like Nix)
- `home-manager://options/nixpkgs` - Control your packages before they control you
- `home-manager://options/systemd` - For those who've embraced the systemd overlords
- `home-manager://options/targets` - Set your targets, then hit them with configuration
- `home-manager://options/dconf` - GNOME settings that won't make you pull your hair out
- `home-manager://options/editorconfig` - End the tabs vs. spaces war once and for all
- `home-manager://options/lib` - Library options for the truly hardcore Nixer
- `home-manager://options/launchd` - macOS services that actually work as expected
- `home-manager://options/pam` - Authentication modules that won't lock you out of your own system
- `home-manager://options/sops` - Secrets management that's actually secret
- `home-manager://options/windowManager` - Configure your window manager without editing 15 different config files
- `home-manager://options/xresources` - X11 resources for those still living in 1999
- `home-manager://options/xsession` - X session configuration for the X11 diehards
- `home-manager://options/prefix/{option_prefix}` - Choose your own adventure with any option prefix

### MCP Tools

#### NixOS Tools
- `nixos_search` - Search for packages, options, or programs with automatic wildcard handling
- `nixos_info` - Get detailed information about a specific package or option
- `nixos_stats` - Get statistical information about NixOS packages

#### Home Manager Tools
- `home_manager_search` - Search for Home Manager configuration options
- `home_manager_info` - Get detailed information about a specific Home Manager option
- `home_manager_stats` - Get statistics about Home Manager options

#### Tool Usage Examples

```python
# NixOS examples
# Search for packages
nixos_search(query="firefox", type="packages", limit=10, channel="unstable")

# Search for system options using the stable channel (currently 24.11)
nixos_search(query="postgresql", type="options", channel="stable")

# Search for programs
nixos_search(query="python", type="programs")

# Get package details
nixos_info(name="nixos.firefox", type="package", channel="unstable")

# Get option details
nixos_info(name="services.postgresql.enable", type="option", channel="stable")

# Get package statistics
nixos_stats()

# Home Manager examples
# Search for Home Manager options
home_manager_search(query="programs.git")

# Get Home Manager option details
home_manager_info(name="programs.firefox.enable")

# Get Home Manager statistics
home_manager_stats()
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
# Make sure to install dependencies explicitly with --install-deps
uvx --install-deps nixmcp

# Or with a specific Python version
uvx --python=3.11 --install-deps nixmcp
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
      }
    }
  }
}
```

With this configuration:
- Logs are written to stdout/stderr only (captured by the Claude Code interface)
- No log files are created by default
- To enable file logging, add `"NIX_MCP_LOG": "/path/to/log/file.log"` to the env object

### Environment Variables

You can customize the server behavior with these environment variables:

```
LOG_LEVEL=INFO        # Log level (DEBUG, INFO, WARNING, ERROR)
NIX_MCP_LOG=/path/log # Optional: If set to a non-empty value, logs to this file; otherwise logs only to console
```

### NixOS Channel Support

The server supports multiple NixOS channels for package and option searches:

- `unstable`: Latest NixOS unstable channel (default)
- `stable`: Current stable NixOS release (synonym for 24.11 currently)
- `24.11`: Specific version reference

These can be used with the `channel` parameter in `nixos_search` and `nixos_info` tools.

### Releasing New Versions

To release a new version:

1. Update the version in `pyproject.toml`
2. Commit the changes
3. Tag the release with semantic versioning

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

### Development with Claude Desktop

For local development and testing with Claude Desktop, add this configuration to your `~/.config/claude/config.json`:

```json
{
  "mcpServers": {
    "nixos": {
      "command": "uv",
      "args": [
        "run",
        "--isolated",
        "--with-requirements",
        "<path-to-cloned-repo>/requirements.txt",
        "-m",
        "nixmcp.__main__"
      ],
      "cwd": "<path-to-cloned-repo>",
      "env": {
        "LOG_LEVEL": "DEBUG",
        "LOG_FILE": "<path-to-cloned-repo>/nixmcp-server.log",
        "PYTHONPATH": "<path-to-cloned-repo>"
      }
    }
  }
}
```

This configuration:
- Uses `uv run` with the `--isolated` flag to create a clean environment
- Explicitly specifies requirements with `--with-requirements`
- Uses the `-m nixmcp.__main__` module entry point
- Sets the working directory to your repo location
- Adds the project directory to PYTHONPATH for module resolution
- Enables debug logging for development purposes

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

## Using with LLMs

Once configured, you can use NixMCP in your prompts with MCP-compatible models:

```
# Direct resource references for NixOS
Please provide information about the Python package in NixOS.
~nixos://package/python

What configuration options are available for NGINX in NixOS?
~nixos://option/services.nginx

# Direct resource references for Home Manager
What options are available for configuring Git in Home Manager?
~home-manager://search/options/programs.git

Tell me about the Firefox profiles option in Home Manager.
~home-manager://option/programs.firefox.profiles

# Tool usage for NixOS
Search for PostgreSQL options in NixOS:
~nixos_search(query="postgresql", type="options")

Get details about the Firefox package:
~nixos_info(name="firefox", type="package")

# Tool usage for Home Manager
Search for shell configuration options:
~home_manager_search(query="programs.zsh")

Get details about Git username configuration:
~home_manager_info(name="programs.git.userName")
```

The LLM will automatically fetch the requested information through the MCP server and use the appropriate tools based on whether you're asking about NixOS system-level configuration or Home Manager user-level configuration.

## Implementation Details

### Code Architecture

NixMCP is organized into a modular structure for better maintainability and testing:

- `nixmcp/cache/` - Caching components for better performance
- `nixmcp/clients/` - API clients for Elasticsearch and Home Manager documentation
- `nixmcp/contexts/` - Context objects that manage application state
- `nixmcp/resources/` - MCP resource definitions for NixOS and Home Manager
- `nixmcp/tools/` - MCP tool implementations for searching and retrieving data
- `nixmcp/utils/` - Utility functions and helpers
- `nixmcp/logging.py` - Centralized logging configuration
- `nixmcp/server.py` - Main entry point and server initialization

### NixOS API Integration

For NixOS packages and system options, NixMCP connects directly to the NixOS Elasticsearch API to provide real-time access to the latest package and system configuration data.

### Home Manager Documentation Parser

For Home Manager options, NixMCP implements what can only be described as a crime against HTML parsing:

1. An HTML documentation parser that somehow manages to extract structured data from Home Manager's documentation pages through a combination of BeautifulSoup incantations, regex black magic, and the kind of determination that only comes from staring at malformed HTML for 72 hours straight:
   - https://nix-community.github.io/home-manager/options.xhtml
   - https://nix-community.github.io/home-manager/nixos-options.xhtml
   - https://nix-community.github.io/home-manager/nix-darwin-options.xhtml

2. An in-memory search engine cobbled together with duct tape and wishful thinking:
   - Inverted index for fast text search (when it doesn't fall over)
   - Prefix tree for hierarchical path lookups (a data structure that seemed like a good idea at 3 AM)
   - Option categorization by source and type (more accurate than a coin flip, usually)
   - Result scoring and relevance ranking (based on an algorithm best described as "vibes-based sorting")

3. Background loading to avoid blocking server startup (because waiting for this monstrosity to initialize would test anyone's patience)

## What is Model Context Protocol?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that enables seamless integration between LLM applications and external data sources and tools. MCP uses a JSON-based message format exchanged over various transport mechanisms (typically standard input/output streams).

This project implements the MCP specification using the FastMCP library, providing a bridge between AI models and both NixOS and Home Manager resources.

## License

MIT