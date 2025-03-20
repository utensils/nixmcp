# NixMCP - Model Context Protocol for NixOS resources

**Note: This project is under active development and is not yet ready for production use.**

NixMCP is a Python library and CLI tool that exposes NixOS packages and options to AI models via a Model Context Protocol. This tool helps AI models access up-to-date information about NixOS resources, reducing hallucinations and outdated information.

The tool uses the local Nix installation to provide accurate, up-to-date information directly from the Nix package repository, rather than relying on web scraping or potentially outdated API sources.

## Features

- Query NixOS packages and options directly using the Nix CLI tools
- Get detailed package and option metadata from your local Nix installation
- Cache results to improve performance
- Generate formatted context for AI models in various formats (text, Markdown, JSON)
- CLI tool for easy integration with AI workflows

## Installation

### Using Nix

```bash
# Enter development shell
nix develop

# Or, to use the flake directly
nix run github:username/nixmcp
```

### From source

```bash
pip install .
```

## Usage

### CLI

```bash
# Query package information
nixmcp package python --channel unstable

# Query package information with JSON output
nixmcp package python --json

# Query package information with Markdown output
nixmcp package python --markdown

# Query option information
nixmcp option services.nginx.enable --channel unstable

# Search for packages
nixmcp search python --type package --limit 5

# Search for options
nixmcp search nginx --type option

# Generate context for AI models (plain text format)
nixmcp context --packages python nodejs --options services.nginx.enable

# Generate context in JSON format
nixmcp context --packages python nodejs --options services.nginx.enable --format json

# Generate context in Markdown format
nixmcp context --packages python nodejs --options services.nginx.enable --format markdown
```

### Python API

```python
from nixmcp.model_context import ModelContext

# Create a ModelContext instance
context = ModelContext()

# Query package information
python_pkg = context.query_package("python")
print(python_pkg)

# Generate context for AI models
context_str = context.format_context(
    packages=["python", "nodejs"],
    options=["services.nginx.enable"]
)
print(context_str)
```

## Development

```bash
# Enter development shell
nix develop

# Run tests
pytest

# Format code
black nixmcp tests
isort nixmcp tests

# Type checking
mypy nixmcp
```

## License

MIT