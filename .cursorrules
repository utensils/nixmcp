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

## Build & Run Commands
- Development environment: `nix develop` or use direnv
- Run server: `python server.py`
- Install dependencies manually: `pip install -r requirements.txt`
- Lint: `black server.py` (recommended, not yet set up)
- Type checking: `mypy server.py` (recommended, not yet set up)

## Code Style Guidelines
- Python 3.9+ with type hints required
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