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
    os.makedirs(base_dir, exist_ok=True)

    # Determine test type for this session
    test_type = get_test_type()

    # Create a subdirectory for the specific test type
    cache_dir = os.path.join(base_dir, test_type)
    os.makedirs(cache_dir, exist_ok=True)

    return cache_dir


@pytest.fixture(scope="session", autouse=True)  # Make this autouse to ensure it's always active
def temp_cache_dir():
    """Create a temporary cache directory for the entire test session.

    This creates a structured cache directory with separate areas for
    unit and integration tests, preventing cache conflicts.

    This fixture is auto-used to ensure NO tests ever use the system cache directory.
    """
    # Store original cache dir to restore later
    old_cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR")

    # ALWAYS force a test-specific cache dir, even if one was provided via environment
    # This ensures we never accidently use a system cache during tests

    # Create a structured cache directory
    temp_dir = create_structured_cache_dir()

    # Update environment variable for the test session
    os.environ["MCP_NIXOS_CACHE_DIR"] = temp_dir

    # Log the cache directory being used
    print(f"\n⚠️ Test cache directory: {temp_dir}")

    yield temp_dir

    # Clean up if cleanup is not disabled
    if os.environ.get("KEEP_TEST_CACHE") != "true":
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"✅ Cleaned test cache directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️ Error cleaning test cache: {e}")

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

    # Only clean system caches before the test run, not during/after
    # This ensures no tests have access to real cache data
    if os.path.exists(default_cache_dir):
        print(f"\n🧹 Cleaning system cache directory: {default_cache_dir}")
        try:
            # Instead of removing the system cache, we can rename it temporarily
            # This preserves the original cache while ensuring tests can't use it
            backup_dir = f"{default_cache_dir}_backup_during_tests"

            # Remove any existing backup dir first
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)

            # Rename the system cache dir to backup
            os.rename(default_cache_dir, backup_dir)

            # After tests complete, restore the original cache
            yield

            # Cleanup any test-created system cache
            if os.path.exists(default_cache_dir):
                shutil.rmtree(default_cache_dir)

            # Restore original cache
            if os.path.exists(backup_dir):
                os.rename(backup_dir, default_cache_dir)
                print(f"✅ Restored original system cache: {default_cache_dir}")
        except Exception as e:
            print(f"⚠️ Error managing system cache: {e}")
            yield
    else:
        # No system cache to preserve
        yield

    # Clean any stray temporary test cache directories
    tmp_caches = glob.glob(os.path.join(tempfile.gettempdir(), "mcp_nixos_test_cache_*"))
    if tmp_caches:
        print(f"🧹 Cleaning {len(tmp_caches)} stray test cache directories")
        for tmp_cache in tmp_caches:
            try:
                shutil.rmtree(tmp_cache)
            except Exception as e:
                print(f"⚠️ Error cleaning temp cache {tmp_cache}: {e}")

    # Make one final check to ensure the system cache dir doesn't exist
    # after tests (except for the original that we restored)
    unexpected_dirs = []
    if sys.platform == "darwin":
        cache_parent = os.path.expanduser("~/Library/Caches")
        unexpected_pattern = os.path.join(cache_parent, "mcp_nixos*")
        unexpected_dirs = [
            d for d in glob.glob(unexpected_pattern) if d != default_cache_dir and "_backup_during_tests" not in d
        ]

    if unexpected_dirs:
        print(f"⚠️ Found unexpected cache directories after tests: {unexpected_dirs}")


def pytest_runtest_setup(item):
    """Skip tests marked with 'skipwindows' on Windows platforms."""
    import sys
    
    if sys.platform == "win32" and item.get_closest_marker("skipwindows"):
        pytest.skip("Test not supported on Windows")
        
        
@pytest.fixture(scope="session")
def is_windows():
    """Return True if running on Windows."""
    import sys
    return sys.platform == "win32"
