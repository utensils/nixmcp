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

## System Requirements

### Elasticsearch API Access (Recommended)
The server can directly access the NixOS Elasticsearch API for optimal performance:

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

### Nix Channels (Fallback)
As a fallback, the server can use local Nix channels:
- `nixpkgs` (pointing to nixpkgs-unstable)
- `nixpkgs-unstable`

Add them with:
```bash
nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs
nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs-unstable
nix-channel --update
```

These channels allow the server to access package information when Elasticsearch is unavailable. The server will verify these channels on startup and warn if any are missing.

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