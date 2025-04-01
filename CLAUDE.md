# MCP-NixOS Project Guidelines

## Source of Truth & Code Patterns

- CLAUDE.md is the primary source of truth for coding rules
- Sync changes to other rule files using: `nix develop -c sync-rules` 
  - This syncs CLAUDE.md to `.windsurfrules`, `.cursorrules`, `.goosehints`
- Always follow existing code patterns and module structure
- Maintain architectural boundaries and consistency

## Project Overview

MCP-NixOS provides MCP resources and tools for NixOS packages, system options, Home Manager configuration, and nix-darwin macOS configuration. Communication uses JSON-based messages over standard I/O. An interactive shell (`mcp_shell.py`) is included for manual testing and exploration.

Official repository: [https://github.com/utensils/mcp-nixos](https://github.com/utensils/mcp-nixos)

## Architecture

### Core Components
- **Cache**: Simple in-memory and filesystem HTML caching
- **Clients**: Elasticsearch, Home Manager, nix-darwin, HTML
- **Contexts**: Application state management for each platform
- **Resources**: MCP resource definitions using URL schemes
- **Tools**: Search, info, and statistics tools
- **Utils**: Cross-platform helpers and cache management
- **Server**: FastMCP server implementation
- **Pre-Cache**: Command-line option to populate cache data during setup/build

### Implementation Guidelines

**Resources**
- Use consistent URL schemes: `nixos://`, `home-manager://`, `darwin://`
- Follow path hierarchy: `scheme://category/action/parameter`
- Parameters in curly braces: `nixos://package/{package_name}`
- Return structured data as dictionaries
- Errors: `{"error": message, "found": false}`

**Tools**
- Functions with type hints (return `str` for human-readable output)
- Include `context` parameter for dependency injection
- Detailed Google-style docstrings
- Catch exceptions for user-friendly error messages

**Context Management**
- Lifespan management for initialization/cleanup
- Eager loading with fallbacks and timeouts
- Prefer dependency injection over global state

**Best Practices**
- Type annotations (Optional, Union, List, Dict)
- Strict null safety with defensive programming
- Detailed error logging and user-friendly messages
- Support wildcard searches and handle empty results
- Cross-platform compatibility:
  - Use pathlib.Path for platform-agnostic path handling
  - Check sys.platform before using platform-specific features
  - Handle file operations with appropriate platform-specific adjustments
  - Use os.path.join() instead of string concatenation for paths
  - Ensure tests work consistently across Windows, macOS, and Linux

## API Reference

### NixOS Resources & Tools
- Status, package info/search, option info/search, program search
- `nixos_search()`, `nixos_info()`, `nixos_stats()`
- Multiple channels: unstable (default), stable (24.11)

### Home Manager Resources & Tools
- Status, option info/search, hierarchical lists, prefix paths
- `home_manager_search()`, `home_manager_info()`, `home_manager_options_by_prefix()`

### nix-darwin Resources & Tools
- Status, option info/search, category lists, prefix paths
- `darwin_search()`, `darwin_info()`, `darwin_options_by_prefix()`

## System Requirements

### APIs & Configuration
- Elasticsearch API for NixOS features
- HTML parsing for Home Manager and nix-darwin
- Multi-level caching with filesystem persistence
- Environment configuration via ENV variables

### Configuration
- `MCP_NIXOS_LOG_LEVEL`, `MCP_NIXOS_LOG_FILE`, `LOG_FORMAT`
- `MCP_NIXOS_CACHE_DIR`, `MCP_NIXOS_CACHE_TTL`
- `MCP_NIXOS_CLEANUP_ORPHANS`, `KEEP_TEST_CACHE` (development)
- `ELASTICSEARCH_URL`, `ELASTICSEARCH_USER`, `ELASTICSEARCH_PASSWORD`

## Development

### C Extension Compilation Support
- Fully supports building C extensions via native libffi support
- Environment setup managed by flake.nix for build tools and headers

### Testing
- 80%+ code coverage with pytest
- Static type checking (zero-tolerance policy)
- Linting with Black and Flake8
- Test organization mirrors module structure
- Use dependency injection for testable components
- Tests categorized with markers:
  - Integration tests: `@pytest.mark.integration`
  - Slow tests: `@pytest.mark.slow`
  - Async tests: `@pytest.mark.asyncio`
- Cross-platform testing:
  - CI runs tests on Linux, macOS, and Windows
  - Linux and macOS tests use flake.nix for development environment
  - Windows tests use Python's venv with special dependencies (pywin32)
  - All tests must be platform-agnostic or include platform-specific handling
- Run specific test categories:
  - Unit tests only: `nix run .#run-tests -- --unit`
  - Integration tests only: `nix run .#run-tests -- --integration`
  - All tests: `nix run .#run-tests`
- Test Cache Configuration:
  - Tests use structured cache directory with separate areas for unit and integration tests
  - Automatic subdirectory: `./mcp_nixos_test_cache/{unit|integration|mixed}`
  - Cache is automatically cleaned up after tests unless `KEEP_TEST_CACHE=true`
  - Override with `MCP_NIXOS_CACHE_DIR=/custom/path nix run .#run-tests`
  - Designed for parallel test runs without cache conflicts
  - Testing strictly maintains cache directory isolation from system directories
  - All tests must check for both default OS cache paths and test-specific paths
  - The gitignore file excludes `mcp_nixos_test_cache/` and `*test_cache*/` patterns

### Logging Tests
- Prefer direct behavior verification over implementation details
- When testing log level filtering:
  - Use `isEnabledFor()` assertions for level checks (platform-independent)
  - Use mock handlers with explicit level settings
  - Test both logger configuration and actual handler behavior
  - Avoid patching internal logging methods (`_log`) which vary by platform
  - Add clear error messages to assertions
- Prevent test flakiness by avoiding sleep/timing dependencies
- Use clean logger fixtures to prevent test interaction

### Dependency Management
- Project uses `pyproject.toml` for dependency specification (PEP 621)
- Core dependencies:
  - `mcp>=1.5.0`: Base MCP framework
  - `requests>=2.32.3`: HTTP client for API interactions
  - `python-dotenv>=1.1.0`: Environment variable management
  - `beautifulsoup4>=4.13.3`: HTML parsing for documentation
  - `psutil>=5.9.8`: Process and system utilities for orphan cleanup
- Dev dependencies defined in `[project.optional-dependencies]`
- Setup script ensures all dependencies are properly installed

### Installation & Usage
- Install: `pip install mcp-nixos`, `uv pip install mcp-nixos`, `uvx mcp-nixos`
- Claude Code configuration: Add to `~/.config/claude/config.json`
- Interactive shell: `python mcp_shell.py` (manual testing and tool exploration)
- Docker deployment:
  - Standard use: `docker run --rm ghcr.io/utensils/mcp-nixos`
  - Docker image includes pre-cached data for immediate startup
  - Build with pre-cache: `docker build -t mcp-nixos .`
  - Deployed on Smithery.ai as a hosted service
- Development:
  - Environment: `nix develop`
  - Run server: `run`
  - Pre-cache data: `python -m mcp_nixos --pre-cache`
  - Tests: `run-tests`, `run-tests --unit`, `run-tests --integration`
  - Code quality: `lint`, `typecheck`, `format`
  - Stats: `loc`
  - Package: `build`, `publish`
  - GitHub operations: Use `gh` tool for repository management and troubleshooting

### Code Style
- Python 3.11+ with strict type hints
- PEP 8 naming conventions
- Google-style docstrings
- Black formatting, 120 char line limit
- Strict null safety practices
- Zero-tolerance for type errors