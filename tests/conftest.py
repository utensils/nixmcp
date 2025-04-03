"""Common test fixtures for MCP-NixOS tests."""

import os
import tempfile
import shutil
import pathlib
import glob
import pytest


def get_test_type():
    """Determine the test type (unit or integration) based on test collection."""
    # Type annotation workaround for pyright
    pytest_obj = pytest  # type: ignore

    if hasattr(pytest_obj, "current_test_type"):
        return getattr(pytest_obj, "current_test_type", "mixed")

    # Default to 'mixed' if we can't determine the specific type
    return "mixed"


def create_structured_cache_dir(base_dir=None):
    """Create a structured cache directory for tests.

    This creates a directory structure with separate subdirectories for
    unit and integration tests to prevent cross-contamination.
    """
    # If base directory is specified, use it; otherwise use project root
    if not base_dir:
        # Get project root (base dir of the tests directory)
        root_dir = pathlib.Path(__file__).parent.parent
        base_dir = os.path.join(root_dir, "mcp_nixos_test_cache")

    # Create base directory if it doesn't exist
    try:
        os.makedirs(base_dir, exist_ok=True)
    except (PermissionError, OSError) as e:
        # Fallback to temp directory if we can't use the project root
        import tempfile
        import uuid

        temp_base = os.path.join(tempfile.gettempdir(), f"mcp_nixos_test_cache_{uuid.uuid4().hex}")
        print(f"⚠️ Could not create cache in {base_dir}: {e}")
        print(f"⚠️ Using fallback temp directory: {temp_base}")
        os.makedirs(temp_base, exist_ok=True)
        base_dir = temp_base

    # Determine test type for this session
    test_type = get_test_type()

    # Create a subdirectory for the specific test type
    cache_dir = os.path.join(base_dir, test_type)
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except (PermissionError, OSError) as e:
        # Final fallback - use a different directory in the same base
        alt_cache_dir = os.path.join(base_dir, f"{test_type}_{uuid.uuid4().hex[:8]}")
        print(f"⚠️ Could not create cache in {cache_dir}: {e}")
        print(f"⚠️ Using alternative cache directory: {alt_cache_dir}")
        os.makedirs(alt_cache_dir, exist_ok=True)
        cache_dir = alt_cache_dir

    return cache_dir


@pytest.fixture(scope="session", autouse=True)  # Make this autouse to ensure it's always active
def temp_cache_dir():
    """Create a temporary cache directory for the entire test session.

    This creates a structured cache directory with separate areas for
    unit and integration tests, preventing cache conflicts.

    This fixture is auto-used to ensure NO tests ever use the system cache directory.
    """
    import uuid

    # Store original cache dir to restore later
    old_cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR")

    # ALWAYS force a test-specific cache dir, even if one was provided via environment
    # This ensures we never accidently use a system cache during tests

    # Create a structured cache directory
    temp_dir = None
    try:
        temp_dir = create_structured_cache_dir()
    except Exception as e:
        # Ultimate fallback if even our fallbacks fail
        fallback_dir = os.path.join(tempfile.gettempdir(), f"mcp_nixos_emergency_cache_{uuid.uuid4().hex}")
        print(f"⚠️ Error creating test cache directory: {e}")
        print(f"⚠️ Using emergency fallback directory: {fallback_dir}")
        os.makedirs(fallback_dir, exist_ok=True)
        temp_dir = fallback_dir

    # Update environment variable for the test session
    os.environ["MCP_NIXOS_CACHE_DIR"] = temp_dir

    # Log the cache directory being used
    print(f"\n⚠️ Test cache directory: {temp_dir}")

    yield temp_dir

    # Clean up if cleanup is not disabled
    if os.environ.get("KEEP_TEST_CACHE") != "true":
        try:
            # Use safe directory removal with forced timeout
            # Don't hang indefinitely if there's a lock or similar issue
            import time
            from pathlib import Path

            # First try normal cleanup
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                # If that fails, try more aggressive cleanup
                for attempt in range(3):
                    try:
                        # Try to clear individual files first
                        path = Path(temp_dir)
                        if path.exists():
                            for item in path.glob("**/*"):
                                if item.is_file():
                                    try:
                                        item.unlink(missing_ok=True)
                                    except Exception:
                                        pass

                            # Then try to remove directories
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            break
                    except Exception:
                        if attempt < 2:
                            time.sleep(0.5)  # Brief pause before retry

            print(f"✅ Cleaned test cache directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️ Error cleaning test cache (tests completed successfully): {e}")

    # Restore the original environment
    if old_cache_dir is not None:
        os.environ["MCP_NIXOS_CACHE_DIR"] = old_cache_dir
    else:
        os.environ.pop("MCP_NIXOS_CACHE_DIR", None)


# The clear_module_cache fixture was removed to improve performance.
# Test isolation should use mocking or dependency injection instead.


# Add custom CLI options for pytest
def pytest_addoption(parser):
    """Add MCP-NixOS specific command line options to pytest."""
    parser.addoption("--unit", action="store_true", default=False, help="Run unit tests only (non-integration tests)")
    parser.addoption("--integration", action="store_true", default=False, help="Run integration tests only")


# Add a pytest plugin to detect test type (unit vs integration) and register markers
def pytest_configure(config):
    """Configure pytest with custom attributes and markers.

    This plugin:
    1. Detects if we're running unit or integration tests
       based on the marker expression or command-line options.
    2. Registers custom markers used by our test suite
    """
    # Register markers to avoid warnings
    config.addinivalue_line("markers", "timeout(seconds): mark test to timeout after given seconds")
    config.addinivalue_line("markers", "skipwindows: mark test to be skipped on Windows platforms")
    config.addinivalue_line("markers", "windows: mark test that should only run on Windows")

    # Add the current_test_type attribute to pytest module if it doesn't exist
    if not hasattr(pytest, "current_test_type"):
        # Add attribute using setattr to avoid variable reassignment
        setattr(pytest, "current_test_type", "mixed")

    # Type annotation workaround for pyright
    pytest_obj = pytest  # type: ignore

    # First check for our custom CLI options
    if config.getoption("--unit"):
        pytest_obj.current_test_type = "unit"  # type: ignore
        # Add the appropriate marker expression
        config.option.markexpr = "not integration"
    elif config.getoption("--integration"):
        pytest_obj.current_test_type = "integration"  # type: ignore
        # Add the appropriate marker expression
        config.option.markexpr = "integration"
    else:
        # Check if markers are being used
        marker_expr = config.getoption("-m", "")
        keyword_expr = config.getoption("-k", "")

        # Set type based on marker/keyword expressions
        if marker_expr == "integration":
            pytest_obj.current_test_type = "integration"  # type: ignore
        elif "not integration" in keyword_expr:
            pytest_obj.current_test_type = "unit"  # type: ignore

    # Get current test type safely
    current_type = getattr(pytest_obj, "current_test_type", "mixed")

    # Log the test type to stdout
    print(
        f"\nRunning {current_type} tests with cache directory: "
        + f"{os.environ.get('MCP_NIXOS_CACHE_DIR', 'default')}\n"
    )


@pytest.fixture(scope="session", autouse=True)
def clean_system_cache_dirs():
    """Clean up system cache directories to prevent tests from using them.

    This explicitly targets the system cache locations to prevent any test from
    accidentally using the real system cache. It's a safety net on top of the
    temp_cache_dir fixture.
    """
    import sys
    import uuid

    # Determine default cache directory based on platform
    if sys.platform == "darwin":
        default_cache_dir = os.path.expanduser("~/Library/Caches/mcp_nixos")
    elif sys.platform.startswith("linux"):
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        default_cache_dir = (
            os.path.join(xdg_cache, "mcp_nixos") if xdg_cache else os.path.expanduser("~/.cache/mcp_nixos")
        )
    elif sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\mcp_nixos\Cache
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            default_cache_dir = os.path.join(local_app_data, "mcp_nixos", "Cache")
        else:
            # Fallback if LOCALAPPDATA is not available
            default_cache_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "mcp_nixos", "Cache")
    else:
        default_cache_dir = os.path.expanduser("~/.cache/mcp_nixos")

    backup_dir = None

    # Only clean system caches before the test run, not during/after
    # This ensures no tests have access to real cache data
    if os.path.exists(default_cache_dir):
        print(f"\n🧹 Cleaning system cache directory: {default_cache_dir}")
        try:
            # Instead of removing the system cache, we can rename it temporarily
            # This preserves the original cache while ensuring tests can't use it
            backup_dir = f"{default_cache_dir}_backup_during_tests_{uuid.uuid4().hex[:8]}"

            # Remove any existing backup dir first
            old_backups = glob.glob(f"{default_cache_dir}_backup_during_tests_*")
            for old_backup in old_backups:
                try:
                    if os.path.exists(old_backup):
                        shutil.rmtree(old_backup, ignore_errors=True)
                except Exception:
                    pass

            # Try to move the directory but handle errors robustly
            try:
                # Rename the system cache dir to backup
                os.rename(default_cache_dir, backup_dir)
            except (PermissionError, OSError):
                # If rename fails, try to make the system dir inaccessible
                # by creating our own test marker file in it
                marker_file = os.path.join(default_cache_dir, ".TEST_IN_PROGRESS")
                try:
                    with open(marker_file, "w") as f:
                        f.write(f"Test in progress: {uuid.uuid4().hex}")
                except Exception:
                    # If all else fails, just continue - the temp_cache_dir should still protect us
                    pass
        except Exception as e:
            print(f"⚠️ Error managing system cache: {e}")

    # After tests complete, restore the original cache
    yield

    try:
        # Cleanup any test-created system cache
        if os.path.exists(default_cache_dir):
            # If a marker file exists, this is the original cache that we couldn't move
            marker_file = os.path.join(default_cache_dir, ".TEST_IN_PROGRESS")
            if os.path.exists(marker_file):
                # Just remove our marker file
                try:
                    os.unlink(marker_file)
                except Exception:
                    pass
            else:
                # This is a test-created directory, so remove it
                shutil.rmtree(default_cache_dir, ignore_errors=True)

        # Restore original cache if we were able to back it up
        if backup_dir and os.path.exists(backup_dir):
            if not os.path.exists(default_cache_dir):
                try:
                    os.rename(backup_dir, default_cache_dir)
                    print(f"✅ Restored original system cache: {default_cache_dir}")
                except Exception as e:
                    print(f"⚠️ Error restoring system cache: {e}")
                    # If we can't restore the cache directory, try to manually move the files
                    try:
                        if not os.path.exists(default_cache_dir):
                            os.makedirs(default_cache_dir, exist_ok=True)
                        # Copy files instead of moving
                        from pathlib import Path

                        backup_path = Path(backup_dir)
                        for item in backup_path.glob("**/*"):
                            if item.is_file():
                                rel_path = item.relative_to(backup_path)
                                target = Path(default_cache_dir) / rel_path
                                target.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(item, target)
                    except Exception:
                        pass
            else:
                # Backup directory exists but original was also recreated
                # Just clean up the backup
                shutil.rmtree(backup_dir, ignore_errors=True)
    except Exception as e:
        print(f"⚠️ Error in cache cleanup: {e}")

    # Clean any stray temporary test cache directories
    try:
        tmp_caches = glob.glob(os.path.join(tempfile.gettempdir(), "mcp_nixos_*cache*"))
        if tmp_caches:
            print(f"🧹 Cleaning {len(tmp_caches)} stray test cache directories")
            for tmp_cache in tmp_caches:
                try:
                    if os.path.isdir(tmp_cache):
                        shutil.rmtree(tmp_cache, ignore_errors=True)
                except Exception:
                    pass
    except Exception:
        pass


def pytest_runtest_setup(item):
    """
    Handle platform-specific test markers:
    - Skip tests marked with 'skipwindows' on Windows platforms
    - Skip tests marked with 'windows' on non-Windows platforms
    """
    import sys

    if sys.platform == "win32" and item.get_closest_marker("skipwindows"):
        pytest.skip("Test not supported on Windows")

    if sys.platform != "win32" and item.get_closest_marker("windows"):
        pytest.skip("Test only supported on Windows")


@pytest.fixture(scope="session")
def is_windows():
    """Return True if running on Windows."""
    import sys

    return sys.platform == "win32"


@pytest.fixture
def compare_paths():
    """Return a function to safely compare paths across platforms.

    This handles Windows case-insensitivity and path separator differences.
    """
    import os
    import pathlib

    def _compare(path1, path2):
        """Compare two paths in a platform-agnostic way."""
        # Convert to string if paths are Path objects
        if isinstance(path1, pathlib.Path):
            path1 = str(path1)
        if isinstance(path2, pathlib.Path):
            path2 = str(path2)

        # Normalize path separators
        path1 = os.path.normpath(path1)
        path2 = os.path.normpath(path2)

        # Use normcase for case-insensitive comparison on Windows
        return os.path.normcase(path1) == os.path.normcase(path2)

    return _compare
