"""
Utility functions for cache directory management across different platforms.

This module provides functions to find, create, and manage cache directories
following OS-specific conventions for Linux, macOS, and Windows.
"""

import os
import sys
import logging
import pathlib
from typing import Optional, Dict, Any


logger = logging.getLogger(__name__)


def get_default_cache_dir(app_name: str = "mcp_nixos") -> str:
    """
    Determine the appropriate OS-specific cache directory following platform conventions.

    Args:
        app_name: Application name to use for cache directory naming

    Returns:
        Path to the default cache directory for the current platform
    """
    if sys.platform.startswith("linux"):
        # Use XDG_CACHE_HOME or fallback to ~/.cache
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache:
            base_dir = pathlib.Path(xdg_cache)
        else:
            base_dir = pathlib.Path.home() / ".cache"
        cache_dir = base_dir / app_name

    elif sys.platform == "darwin":
        # macOS: ~/Library/Caches/app_name/
        cache_dir = pathlib.Path.home() / "Library" / "Caches" / app_name

    elif sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\app_name\Cache
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_dir = pathlib.Path(local_app_data)
        else:
            # Fallback if LOCALAPPDATA is not available
            base_dir = pathlib.Path.home() / "AppData" / "Local"
        cache_dir = base_dir / app_name / "Cache"

    else:
        # Fallback for other platforms: use ~/.cache/app_name
        logger.warning(f"Unsupported platform: {sys.platform}, using fallback directory")
        cache_dir = pathlib.Path.home() / ".cache" / app_name

    return str(cache_dir)


def ensure_cache_dir(cache_dir: Optional[str] = None, app_name: str = "mcp_nixos") -> str:
    """
    Ensure cache directory exists, creating it if necessary with appropriate permissions.

    Args:
        cache_dir: Path to desired cache directory, or None to use default
        app_name: Application name to use if determining default cache directory

    Returns:
        Path to the created or existing cache directory

    Raises:
        OSError: If directory creation fails
    """
    # Priority 1: Explicitly provided path
    if cache_dir:
        target_dir = pathlib.Path(cache_dir)
    else:
        # Priority 2: Environment variable
        env_cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR")
        if env_cache_dir:
            logger.info(f"Using cache directory from MCP_NIXOS_CACHE_DIR: {env_cache_dir}")
            target_dir = pathlib.Path(env_cache_dir)
        else:
            # Priority 3: OS-specific default
            default_dir = get_default_cache_dir(app_name)
            logger.info(f"Using default cache directory: {default_dir}")
            target_dir = pathlib.Path(default_dir)

    # Create directory if it doesn't exist
    if not target_dir.exists():
        logger.info(f"Creating cache directory: {target_dir}")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)

            # Set appropriate permissions on Unix-like systems
            if sys.platform != "win32":
                try:
                    os.chmod(target_dir, 0o700)  # Owner-only access
                    logger.info(f"Set permissions 0o700 on {target_dir}")
                except OSError as e:
                    logger.warning(f"Failed to set permissions on {target_dir}: {e}")
        except OSError as e:
            logger.error(f"Failed to create cache directory {target_dir}: {e}")
            raise

    return str(target_dir)


def init_cache_storage(cache_dir: Optional[str] = None, ttl: int = 86400) -> Dict[str, Any]:
    """
    Initialize cache storage system with the specified or default directory.

    Args:
        cache_dir: Path to desired cache directory, or None to use default
        ttl: Default time-to-live for cache entries in seconds

    Returns:
        Dictionary containing cache configuration information
    """
    try:
        cache_path = ensure_cache_dir(cache_dir)
        logger.info(f"Cache initialized with directory: {cache_path}")

        return {"cache_dir": cache_path, "ttl": ttl, "initialized": True}
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        # Provide fallback configuration using temporary directory
        import tempfile

        fallback_dir = tempfile.gettempdir()
        logger.warning(f"Using fallback cache directory: {fallback_dir}")
        return {"cache_dir": fallback_dir, "ttl": ttl, "initialized": False, "error": str(e)}
