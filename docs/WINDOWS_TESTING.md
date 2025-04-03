# Windows Testing Guide

## Overview

This guide provides information on running and writing tests for Windows compatibility in the MCP-NixOS project.

## Running Tests on Windows

Windows requires some specific setup to run the tests successfully:

1. **Install dependencies with Windows-specific packages**:
   ```powershell
   python -m pip install ".[dev,win]"
   ```
   
   This includes the additional `pywin32` dependency needed for Windows-specific functionality.

2. **Run tests**:
   ```powershell
   python -m pytest tests/
   ```

3. **Typecheck code**:
   ```powershell
   python -m pip install pyright
   pyright
   ```

## Writing Windows-Compatible Tests

When writing tests that should run on Windows:

1. **Platform detection**:
   ```python
   import sys
   
   is_windows = sys.platform == "win32"
   ```

2. **Use platform markers**:
   ```python
   import pytest
   
   @pytest.mark.windows
   def test_windows_only_feature():
       # This test only runs on Windows
       ...
   
   @pytest.mark.skipwindows
   def test_unix_only_feature():
       # This test is skipped on Windows
       ...
   ```

3. **Path handling**:
   - Always use `pathlib.Path` or `os.path.join()` for platform-agnostic paths
   - Use `os.path.normcase()` for case-insensitive path comparisons on Windows 
   - Never use `os.path.samefile()` in tests that need to run on Windows

4. **File operations**:
   - Handle different file locking mechanisms (Windows uses msvcrt, Unix uses fcntl)
   - Be careful with file permissions as they work differently on Windows
   - Use `shutil.rmtree(path, ignore_errors=True)` for safer directory cleanup
   - Always explicitly close file handles or use context managers

5. **Environment variables**:
   - On Windows, use `LOCALAPPDATA` for cache directories instead of XDG variables
   - Provide fallbacks when environment variables aren't found

## Common Issues and Solutions

### Testing Cache Directories

Windows uses different directory structures for caches:
- Windows: `%LOCALAPPDATA%\mcp_nixos\Cache`
- macOS: `~/Library/Caches/mcp_nixos`
- Linux: `~/.cache/mcp_nixos` or `$XDG_CACHE_HOME/mcp_nixos`

Always create a test-specific cache directory to avoid polluting system directories:

```python
with tempfile.TemporaryDirectory() as temp_dir:
    with mock.patch.dict(os.environ, {"MCP_NIXOS_CACHE_DIR": temp_dir}):
        # Run your test
```

### Path Comparison

On Windows, paths are case-insensitive:

```python
# BAD (Windows-incompatible)
assert actual_path == expected_path

# GOOD (Works on Windows)
assert os.path.normcase(actual_path) == os.path.normcase(expected_path)
```

### File Locking

Different platforms use different locking mechanisms:

```python
if sys.platform == "win32":
    # Windows-specific locking (msvcrt)
    import msvcrt
    msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
else:
    # Unix-specific locking (fcntl)
    import fcntl
    fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
```

The project uses a cross-platform `lock_file()` helper that abstracts these differences.

## CI/CD for Windows Tests

The project uses GitHub Actions to run tests on Windows:
- Separate workflow for Windows tests
- Installs pywin32 and other Windows-specific dependencies
- Runs the same test suite as on Linux/macOS
- Typechecks with pyright

When fixing Windows-specific test failures:
1. Identify if the issue is a platform compatibility problem
2. Use platform-specific code with proper conditionals
3. Add appropriate tests with platform markers
4. Verify the fix works on multiple platforms