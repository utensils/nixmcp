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
   import os
   
   is_windows = sys.platform == "win32" or os.name == "nt"
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
   - When comparing paths in assertions, use the `compare_paths` fixture or normalize paths:
     ```python
     # BAD (Windows-incompatible)
     assert actual_path == expected_path
     
     # GOOD (Works on Windows)
     assert os.path.normcase(actual_path) == os.path.normcase(expected_path)
     ```

4. **File operations**:
   - Handle different file locking mechanisms (Windows uses msvcrt, Unix uses fcntl)
   - Be careful with file permissions as they work differently on Windows
   - Use `shutil.rmtree(path, ignore_errors=True)` for safer directory cleanup
   - Always explicitly close file handles or use context managers

5. **Environment variables**:
   - On Windows, use `LOCALAPPDATA` for cache directories instead of XDG variables
   - Provide fallbacks when environment variables aren't found

6. **Path separators in tests**:
   - When writing tests with path assertions, make them platform-aware:
   ```python
   if os.name == "nt":
       assert os.path.normcase(path) == os.path.normcase(r"\path\with\backslash")
   else:
       assert path == "/path/with/forward/slash"
   ```

7. **Mocking Implementations**:
   - When mocking modules, patch the entire module rather than specific functions that might not exist in your test environment:
   ```python
   # BAD (might fail if running tests on Windows):
   patch("mcp_nixos.utils.cache_helpers.tempfile.NamedTemporaryFile", mock_named_temp)
   
   # GOOD (works cross-platform):
   mock_tempfile = MagicMock()
   mock_tempfile.NamedTemporaryFile.return_value = mock_temp_file
   patch("mcp_nixos.utils.cache_helpers.tempfile", mock_tempfile)
   ```

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

On Windows, paths are case-insensitive and use backslashes:

```python
# BAD (Windows-incompatible)
assert actual_path == expected_path

# GOOD (Works on Windows)
assert os.path.normcase(actual_path) == os.path.normcase(expected_path)
```

Use the `compare_paths` fixture in `conftest.py` for path comparisons:

```python
def test_example(compare_paths):
    # The fixture handles cross-platform path comparison
    assert compare_paths("/path/to/file", r"\path\to\file")
```

### File Locking

Different platforms use different locking mechanisms. Our codebase provides helpers:

```python
from mcp_nixos.utils.cache_helpers import lock_file, unlock_file

# Platform-agnostic locking
with open(file_path, "r") as f:
    if lock_file(f, exclusive=False):
        try:
            # Read from file
            content = f.read()
        finally:
            unlock_file(f)
```

## CI/CD for Windows Tests

The project uses GitHub Actions to run tests on Windows:
- Tests run on Windows, macOS, and Linux to ensure cross-platform compatibility
- Windows testing includes the Windows-specific dependencies (pywin32)
- Type checking with pyright ensures code compatibility

When fixing Windows-specific test failures:
1. Identify if the issue is a platform compatibility problem
2. Use platform-specific code with proper conditionals
3. Add appropriate tests with platform markers
4. Verify the fix works on multiple platforms by checking CI results