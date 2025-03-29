"""Common test fixtures for MCP-NixOS tests."""

import os
import tempfile
import shutil
import pytest


@pytest.fixture(scope="session")
def temp_cache_dir():
    """Create a temporary cache directory for the entire test session."""
    temp_dir = tempfile.mkdtemp(prefix="mcp_nixos_test_cache_")
    old_cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR")
    os.environ["MCP_NIXOS_CACHE_DIR"] = temp_dir
    
    yield temp_dir
    
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
    
    if old_cache_dir is not None:
        os.environ["MCP_NIXOS_CACHE_DIR"] = old_cache_dir
    else:
        os.environ.pop("MCP_NIXOS_CACHE_DIR", None)


# The clear_module_cache fixture was removed to improve performance.
# Test isolation should use mocking or dependency injection instead.
                
                
@pytest.fixture(scope="session", autouse=True)
def clean_cache_dirs():
    """Clean up all cache directories before and after the test session."""
    import sys
    import glob
    from pathlib import Path
    
    # Determine default cache directory based on platform
    if sys.platform == "darwin":
        default_cache_dir = os.path.expanduser("~/Library/Caches/mcp_nixos")
    elif sys.platform.startswith("linux"):
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        default_cache_dir = os.path.join(xdg_cache, "mcp_nixos") if xdg_cache else os.path.expanduser("~/.cache/mcp_nixos")
    else:
        default_cache_dir = os.path.expanduser("~/.cache/mcp_nixos")
    
    cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR", default_cache_dir)
    
    def clean_caches():
        # Clean main cache directory
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
            except Exception as e:
                print(f"Error cleaning cache directory: {e}")
        
        # Clean any stray temporary test cache directories
        tmp_caches = glob.glob(os.path.join(tempfile.gettempdir(), "mcp_nixos_test_cache_*"))
        for tmp_cache in tmp_caches:
            try:
                shutil.rmtree(tmp_cache)
            except Exception:
                pass
    
    clean_caches()
    yield
    clean_caches()