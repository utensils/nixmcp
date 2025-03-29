# MCP-NixOS - Model Context Protocol for NixOS Resources

[![CI](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml/badge.svg)](https://github.com/utensils/mcp-nixos/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/utensils/mcp-nixos/graph/badge.svg?token=kdcbgvq4Bh)](https://codecov.io/gh/utensils/mcp-nixos)
[![PyPI](https://img.shields.io/pypi/v/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mcp-nixos.svg)](https://pypi.org/project/mcp-nixos/)

> **⚠️ ACTIVE DEVELOPMENT**: This package is actively maintained and improved.
>
> **📢 RENAMED**: This package was renamed from `nixmcp` to `mcp-nixos` in version 0.2.0. Update your references accordingly.

MCP-NixOS is a Model Context Protocol server that stops your AI assistant from hallucinating about NixOS. It provides real-time access to NixOS packages, system options, Home Manager configuration, and nix-darwin macOS settings.

## Quick Start: For the Impatient Nixer

Look, we both know you're just going to skim this README and then complain when things don't work. Here's the bare minimum MCP configuration to get started:

```json
{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["mcp-nixos"]
    }
  }
}
```

There. Now your AI assistant can actually give you correct information about NixOS instead of hallucinating package names from 2019.

### Environment Variables

| Variable              | Description                                 | Default                          |
| --------------------- | ------------------------------------------- | -------------------------------- |
| `LOG_LEVEL`           | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO                             |
| `LOG_FILE`            | Path to log file (empty = console only)     | (none)                           |
| `MCP_NIXOS_CACHE_DIR` | Custom cache directory                      | OS-specific\*                    |
| `MCP_NIXOS_CACHE_TTL` | Cache time-to-live in seconds               | 86400 (24h)                      |
| `ELASTICSEARCH_URL`   | NixOS Elasticsearch API URL                 | https://search.nixos.org/backend |

\*Default cache locations: Linux: `~/.cache/mcp_nixos/`, macOS: `~/Library/Caches/mcp_nixos/`, Windows: `%LOCALAPPDATA%\mcp_nixos\Cache\`

## Features

- **NixOS Resources**: Packages and system options via Elasticsearch API
  - Multiple channels: unstable, stable (24.11), and specific versions
  - Detailed package metadata and system option information
- **Home Manager**: User configuration options via parsed documentation
  - Programs, services, and user environment settings
  - Hierarchical paths (e.g., programs.git.userName)
- **nix-darwin**: macOS configuration options via parsed documentation
  - System defaults, services, and macOS-specific settings
- **Smart Caching**: Cross-platform filesystem caching with TTL
  - Reduces network requests and improves startup time
  - Works offline once cached
- **Rich Search**: Automatic wildcard matching and hierarchical paths
  - Fast in-memory search engine for options
  - Related options and contextual suggestions

## MCP Resources & Tools

### NixOS

**Resources:**

- `nixos://package/{name}` - Package info
- `nixos://search/packages/{query}` - Search packages
- `nixos://search/options/{query}` - Search system options
- `nixos://option/{name}` - System option info
- `nixos://search/programs/{name}` - Find packages providing programs
- `nixos://packages/stats` - Package statistics

**Tools:**

- `nixos_search(query, type, channel)` - Search packages, options, or programs
- `nixos_info(name, type, channel)` - Get package or option details
- `nixos_stats(channel)` - Get NixOS statistics

**Channels:** `unstable` (default), `stable` (24.11), or specific version

### Home Manager

**Resources:**

- `home-manager://search/options/{query}` - Search user config options
- `home-manager://option/{name}` - Option details
- `home-manager://options/prefix/{prefix}` - All options under prefix
- `home-manager://options/{category}` - Category options (programs, services, etc.)

**Tools:**

- `home_manager_search(query)` - Search configuration options
- `home_manager_info(name)` - Get option details
- `home_manager_options_by_prefix(option_prefix)` - Get options by prefix
- `home_manager_list_options()` - List all option categories

### nix-darwin

**Resources:**

- `darwin://search/options/{query}` - Search macOS options
- `darwin://option/{name}` - Option details
- `darwin://options/prefix/{prefix}` - All options under prefix
- `darwin://options/{category}` - Category options (system, services, etc.)

**Tools:**

- `darwin_search(query)` - Search macOS configuration options
- `darwin_info(name)` - Get option details
- `darwin_options_by_prefix(option_prefix)` - Get options by prefix
- `darwin_list_options()` - List all option categories

### Tool Usage Examples

```python
# NixOS examples
nixos_search(query="firefox", type="packages", channel="unstable")
nixos_search(query="postgresql", type="options", channel="stable")
nixos_info(name="firefox", type="package")
nixos_info(name="services.postgresql.enable", type="option")

# Home Manager examples
home_manager_search(query="programs.git")
home_manager_info(name="programs.firefox.enable")
home_manager_options_by_prefix(option_prefix="programs.git")

# nix-darwin examples
darwin_search(query="system.defaults.dock")
darwin_info(name="services.yabai.enable")
darwin_options_by_prefix(option_prefix="system.defaults")
```

## Installation & Configuration

### Install It

```bash
# Option 1: Install with pip
pip install mcp-nixos

# Option 2: Install with uv
uv pip install mcp-nixos

# Option 3: Run directly with uvx (recommended)
uvx --install-deps mcp-nixos
```

### Configure It

Add to your MCP configuration file (e.g., `~/.config/claude/config.json`):

```json
{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["mcp-nixos"]
    }
  }
}
```

For development with the source code:

```json
{
  "mcpServers": {
    "nixos": {
      "command": "uv",
      "args": ["run", "-m", "mcp_nixos.__main__"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

### Cache & Channels

**Cache System:**

- Default locations: Linux: `~/.cache/mcp_nixos/`, macOS: `~/Library/Caches/mcp_nixos/`
- Stores HTML content, serialized data, and search indices
- Works offline once cached

**NixOS Channels:**

- `unstable`: Latest NixOS unstable (default)
- `stable`: Current stable release (24.11)
- `24.11`: Specific version reference

## Development

### Dependencies

This project uses `pyproject.toml`

```bash
# Install development dependencies
pip install -e ".[dev]"

# Or with uv (recommended)
uv pip install -e ".[dev]"
```

### Using Nix

```bash
# Enter dev shell and see available commands
nix develop && menu

# Common commands
run         # Start the server
run-tests   # Run tests with coverage
lint        # Format and lint code
publish     # Build and publish to PyPI
```

### Testing

Tests use real Elasticsearch API calls instead of mocks for better reliability:

```bash
# Run tests with coverage (default)
run-tests

# Run tests without coverage
run-tests --no-coverage
```

Code coverage is tracked on [Codecov](https://codecov.io/gh/utensils/mcp-nixos).

## Using with LLMs

Once configured, use MCP-NixOS in your prompts with MCP-compatible models:

```
# NixOS resources
~nixos://package/python
~nixos://option/services.nginx
~nixos://search/packages/firefox

# Home Manager resources
~home-manager://search/options/programs.git
~home-manager://option/programs.firefox.profiles

# nix-darwin resources
~darwin://search/options/system.defaults.dock

# NixOS tools
~nixos_search(query="postgresql", type="options")
~nixos_info(name="firefox", type="package", channel="unstable")

# Home Manager tools
~home_manager_search(query="programs.zsh")
~home_manager_info(name="programs.git.userName")

# nix-darwin tools
~darwin_search(query="services.yabai")
~darwin_info(name="system.defaults.dock.autohide")
```

The LLM will fetch information through the MCP server and use the appropriate tools based on whether you're asking about NixOS system configuration, Home Manager user configuration, or nix-darwin macOS configuration.

## Implementation Details

### Code Architecture

MCP-NixOS is organized into a modular structure that somehow manages to work:

- `mcp_nixos/cache/` - Caching components that save your bandwidth
- `mcp_nixos/clients/` - API clients that talk to Elasticsearch and parse HTML docs
- `mcp_nixos/contexts/` - Context objects that keep everything from falling apart
- `mcp_nixos/resources/` - MCP resource definitions for all platforms
- `mcp_nixos/tools/` - MCP tool implementations that do the actual work
- `mcp_nixos/utils/` - Utility functions because we're not animals
- `mcp_nixos/server.py` - The glue that holds this house of cards together

### NixOS API Integration

Connects to the NixOS Elasticsearch API with:

- Multiple channel support (unstable, stable/24.11)
- Field-specific search boosts for better relevance
- Error handling that expects the worst but hopes for the best

### HTML Documentation Parsers

For Home Manager and nix-darwin options, we've committed crimes against HTML parsing:

1. **Documentation Parsers**: Extracts structured data through a combination of BeautifulSoup incantations, regex black magic, and the kind of determination that only comes from staring at malformed HTML for 72 hours straight.

2. **Search Engines**: Cobbled together with:

   - Inverted index for fast text search (when it doesn't fall over)
   - Prefix tree for hierarchical lookups (seemed like a good idea at 3 AM)
   - Result scoring based on an algorithm best described as "vibes-based sorting"

3. **Caching System**: Because parsing that HTML once was traumatic enough:
   - Stores HTML content, processed data structures, and search indices
   - Uses platform-specific cache locations so you don't have to think about it
   - Implements TTL-based expiration to refresh content when needed
   - Falls back gracefully when things inevitably go wrong

## What is Model Context Protocol?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open protocol that connects LLMs to external data and tools using JSON messages over stdin/stdout. This project implements MCP to give AI assistants access to NixOS, Home Manager, and nix-darwin resources.

## License

MIT
