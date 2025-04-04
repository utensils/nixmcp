# MCP-NixOS Project Guidelines

## ⚠️ CRITICAL: Testing and Implementation Changes ⚠️

**NEVER MODIFY IMPLEMENTATION CODE WITHOUT VALIDATING YOUR APPROACH**

- **TEST BEHAVIOR, NOT IMPLEMENTATION**: Ensure tests validate expected behaviors, not internal details
- **UNDERSTAND BEFORE CHANGING**: Thoroughly understand existing patterns and architecture before modifying
- **ROOT CAUSES, NOT SYMPTOMS**: Address fundamental issues instead of adding workarounds
- **VERIFY ALL CONTEXTS**: Test in all usage contexts (direct code, API calls, MCP interface, CLI)
- **IMPLEMENTATION CHANGES REQUIRE EVIDENCE**: Provide clear evidence that implementation changes are correct
- **CHANGES MUST BE REVERSIBLE**: Ensure you can roll back if a change causes regressions

Implementing quick fixes without understanding the architecture can completely break functionality, especially with context-sensitive code. Always validate your approach with robust tests that cover all usage scenarios.

## Source of Truth & Code Patterns

- CLAUDE.md is the primary source of truth for coding rules
- Sync changes to other rule files using: `nix develop -c sync-rules` 
  - This syncs CLAUDE.md to `.windsurfrules`, `.cursorrules`, `.goosehints`
- Always follow existing code patterns and module structure
- Maintain architectural boundaries and consistency

## Project Overview

MCP-NixOS provides MCP resources and tools for NixOS packages, system options, Home Manager configuration, and nix-darwin macOS configuration. Communication uses JSON-based messages over standard I/O. An interactive shell (`mcp_shell.py`) is included for manual testing and exploration.

Official repository: [https://github.com/utensils/mcp-nixos](https://github.com/utensils/mcp-nixos)

## Branch Management

- Default development branch is `develop`
- Main release branch is `main`
- Branch protection rules are enforced:
  - `main`: Requires PR review (1 approval), admin enforcement, no deletion, no force push
  - `develop`: Protected from deletion but allows force push
- PRs follow the pattern: commit to `develop` → open PR to `main` → merge once approved
- Branch deletion on merge is disabled to preserve branch history

## CI/CD Configuration

- **IMPORTANT**: Only use the single `.github/workflows/ci.yml` file for all CI/CD workflows
- Never create additional workflow files as it leads to duplicate/conflicting CI runs
- The main workflow already includes cross-platform testing (Linux, macOS, Windows)
- Update the existing ci.yml file when adding new CI steps instead of creating new files
- Includes Codecov integration for both coverage reporting and test analytics:
  - Generates coverage reports in XML format for Codecov upload
  - Creates JUnit XML test results for Codecov Test Analytics
  - Uses `continue-on-error` and `if: always()` to ensure reports are uploaded even when tests fail
  - Configured with appropriate flags to categorize different test types
- Website deployment to AWS S3/CloudFront:
  - Automatic deployment only when changes are detected in the website directory
  - Only runs on pushes to `main` branch (not on PRs)
  - Uses AWS environment credentials for S3 sync and CloudFront cache invalidation
  - Independent of other jobs like testing or type checking
  - Configured to skip deployment entirely if no website files have changed
- PyPI package deployment:
  - Only runs on version tag pushes (v*)
  - Depends on successful completion of all test and quality jobs
  - Uses the PyPI trusted publishing workflow
- When working with PRs:
  - The CI workflow is configured to run only on:
    - Pushes to `main` branch
    - Pull requests targeting the `main` branch
    - Version tag pushes
  - Pushes to `develop` branch will not trigger CI unless there's an open PR to `main`
  - CI may run twice for PR updates - this is controlled by the concurrency settings
  - The `cancel-in-progress: true` setting ensures older runs are cancelled when new commits are pushed

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
  - For Windows compatibility:
    - Use os.path.normcase() for case-insensitive path comparisons
    - Never use os.path.samefile() in Windows tests (use normcase comparison instead)
    - Provide robust fallbacks for environment variables like LOCALAPPDATA
    - Properly clean up file handles with explicit close or context managers
  - Use platform-specific test markers (@pytest.mark.windows, @pytest.mark.skipwindows)
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

### Website 
- The website is built with Next.js 15.2 and Tailwind CSS in the `/website` directory
- Uses TypeScript, App Router, and static export for AWS S3/CloudFront hosting
- NixOS color scheme is used throughout: primary #5277C3, secondary #7EBAE4
- Directory structure:
  - `/app` - Next.js App Router pages
  - `/components` - React components with client/server separation
  - `/public` - Static assets including favicon and images
  - `/public/favicon` - Website favicon files
  - `/public/images` - Logo images and attribution information
- Deployment:
  - Hosted on AWS S3 bucket `urandom-mcp-nixos` with CloudFront CDN distribution ID `E1QS1G7FYYJ6TL`
  - Automatically deployed via GitHub Actions when changes are detected in the website directory
  - Only deploys on pushes to the `main` branch, not on PRs or feature branches
  - Configured to skip deployment entirely if no website files have changed
  - Uses AWS credentials stored in the AWS environment in GitHub repository
- Nested shell architecture:
  - Main shell has single command: `web-dev` - Launch website development shell
  - Website shell (`nix develop .#web`) provides dedicated commands:
    - `install` - Install dependencies 
    - `dev` - Start development server
    - `build` - Build for production
    - `lint` - Lint code
    - `lint:fix` - Fix linting issues
    - `type-check` - Run TypeScript type checking
- Code quality tools:
  - ESLint for code linting with TypeScript and React plugins
  - Prettier for code formatting with tailwind plugin
  - TypeScript for type checking
- Follows responsive design principles and accessibility guidelines (WCAG 2.1 AA)

### C Extension Compilation Support
- Fully supports building C extensions via native libffi support
- Environment setup managed by flake.nix for build tools and headers

### Testing
- 80%+ code coverage with pytest
- Codecov Test Analytics integration:
  - JUnit XML reports generated during all test runs
  - Uploaded to Codecov for insights on test performance and failures
  - Configured to upload results even when tests fail
  - Results displayed in PR comments with failure details
- Static type checking (zero-tolerance policy)
- Linting with Black and Flake8
- Test organization mirrors module structure
- Use dependency injection for testable components
- Tests categorized with markers:
  - Integration tests: `@pytest.mark.integration`
  - Slow tests: `@pytest.mark.slow`
  - Async tests: `@pytest.mark.asyncio`
  - Platform-specific tests:
    - Windows-only tests: `@pytest.mark.windows`
    - Skip on Windows: `@pytest.mark.skipwindows`
- Cross-platform testing:
  - CI runs tests on Linux, macOS, and Windows
  - Linux and macOS tests use flake.nix for development environment
  - Windows tests use Python's venv with special dependencies (pywin32)
  - All tests must be platform-agnostic or include platform-specific handling
  - Enhance error messages with platform-specific diagnostic information
  - Use platform-aware assertions (e.g., normcase for Windows paths)
  - Never let platform-specific test failures cascade to other test jobs
  - See detailed guide in `docs/WINDOWS_TESTING.md`
  - IMPORTANT: When comparing file paths in tests, use `os.path.normcase()` or the `compare_paths` fixture
  - When mocking modules like `tempfile`, mock the entire module rather than specific functions
  - For assertions involving paths, use platform-specific expectations:
    ```python
    if os.name == "nt":  # Windows
        assert os.path.normcase(path) == os.path.normcase(r"\windows\style\path")
    else:  # Unix
        assert path == "/unix/style/path"
    ```
- Run specific test categories:
  - Unit tests only: `nix run .#run-tests -- --unit`
  - Integration tests only: `nix run .#run-tests -- --integration`
  - All tests: `nix run .#run-tests`
  - With JUnit XML (for local test analytics): `python -m pytest --junitxml=junit.xml -o junit_family=legacy`
- Test Cache Configuration:
  - Tests use structured cache directory with separate areas for unit and integration tests
  - Automatic subdirectory: `./mcp_nixos_test_cache/{unit|integration|mixed}`
  - Cache is automatically cleaned up after tests unless `KEEP_TEST_CACHE=true`
  - Override with `MCP_NIXOS_CACHE_DIR=/custom/path nix run .#run-tests`
  - Designed for parallel test runs without cache conflicts
  - Testing strictly maintains cache directory isolation from system directories
  - All tests must check for both default OS cache paths and test-specific paths
  - The gitignore file excludes `mcp_nixos_test_cache/` and `*test_cache*/` patterns

### Code Complexity Analysis
- Uses wily to track and report on code complexity metrics
- Available locally via `nix develop -c complexity` command:
  - Build cache: `complexity build`
  - View report: `complexity report <file> <metric>`
  - Generate graph: `complexity graph <file> <metric>`
  - Rank files: `complexity rank [path] [metric]`
  - Compare changes: `complexity diff [git_ref]`
- Pre-commit hook to check complexity on every commit
- Continuous Integration:
  - Separate GitHub workflow for complexity analysis
  - Runs on all PRs targeting main branch
  - Posts complexity report as PR comment
  - Archives detailed reports as artifacts
- Key metrics tracked:
  - Cyclomatic complexity
  - Maintainability index
  - Lines of code
  - Comments and documentation
- Code complexity thresholds:
  - Functions should maintain cyclomatic complexity < 10
  - Files should maintain maintainability index > 65
  - Keep module sizes reasonable (< 500 lines preferred)

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

### Development Shells
- Project uses a nested shell architecture for development environments:
  - `devShells.default`: Main Python development shell
  - `devShells.web`: Dedicated Node.js shell for website development
- Separation prevents dependency conflicts between Python and Node.js
- Each shell has purpose-specific commands via `pkgs.devshell.mkShell`
- Shell navigation:
  - From host system: `nix develop` (main) or `nix develop .#web` (website)
  - From main shell: `web-dev` launches website shell
  - Each shell shows commands via menu interface

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
- Docker deployment:
  - Standard use: `docker run --rm ghcr.io/utensils/mcp-nixos`
  - Docker image includes pre-cached data for immediate startup
  - Build with pre-cache: `docker build -t mcp-nixos .`
  - Deployed on Smithery.ai as a hosted service
- Interactive CLI (deprecated from v0.3.0):
  - For manual testing, use a JSON-capable HTTP client like HTTPie or curl
  - Example: `echo '{"type":"call","tool":"nixos_search","params":{"query":"python"}}' | nc localhost 8080`
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

### Licensing and Attribution
- Project code is licensed under MIT License
- The NixOS snowflake logo is used with attribution to the NixOS project
- Project assets include:
  - `nixos-flake.svg`: NixOS snowflake logo in blue (monochrome)
  - `nixos-snowflake-colour.svg`: NixOS snowflake logo with gradient colors
  - `mcp-nixos.png`: Project logo incorporating the NixOS snowflake design
  - Favicon files derived from the project logo
- Logo attribution must be maintained in:
  - README.md attribution section
  - Website footer with link to attribution details
  - Attribution document in website/public/images/attribution.md
- Attribution document must specify both "NixOS" and "NixOS snowflake logo"
- When adding or modifying logo files, update all attribution locations