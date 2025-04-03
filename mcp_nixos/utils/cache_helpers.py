"""
Utility functions for cache directory management across different platforms.

This module provides functions to find, create, and manage cache directories
following OS-specific conventions for Linux, macOS, and Windows.
It also provides cross-platform file locking utilities for concurrent access.
"""

import os
import sys
import logging
import pathlib
import uuid
import time
import json
import random
import errno
from typing import Optional, Dict, Any, Tuple, Callable, IO, Union, cast

# Define file locking imports conditionally based on platform
if sys.platform != "win32":
    import fcntl
else:
    # For Windows, we'll use a simpler locking mechanism
    import msvcrt

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
        if local_app_data and os.path.exists(local_app_data):
            base_dir = pathlib.Path(local_app_data)
        else:
            # More robust fallback if LOCALAPPDATA is not available/valid
            try:
                # First try using the home directory
                home = pathlib.Path.home()
                # Ensure the path exists and construct AppData path
                if home.exists():
                    base_dir = home / "AppData" / "Local"
                    # Create it if it doesn't exist
                    if not base_dir.exists() and home.exists():
                        base_dir.mkdir(parents=True, exist_ok=True)
                else:
                    # Ultimate fallback - use temp directory
                    import tempfile

                    base_dir = pathlib.Path(tempfile.gettempdir()) / "AppData" / "Local"
                    base_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                # If all else fails, use the temp directory
                logger.warning(f"Error finding Windows cache dir: {e}, using temp directory")
                import tempfile

                base_dir = pathlib.Path(tempfile.gettempdir())

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
        # Detect test environment
        if "pytest" in sys.modules:
            # For testing, we want to ensure the cache NEVER uses system locations
            # If we're in a test but no cache_dir was specified, use a temp directory
            # This avoids polluting system cache directories during tests
            if not cache_dir and "MCP_NIXOS_CACHE_DIR" not in os.environ:
                import tempfile as tmp_module

                # Create a test-specific cache directory
                test_dir = tmp_module.mkdtemp(prefix="mcp_nixos_test_cache_")
                logger.warning(f"Test environment detected, using isolated cache: {test_dir}")
                # Set it in the environment so any child processes will use it too
                os.environ["MCP_NIXOS_CACHE_DIR"] = test_dir
                cache_dir = test_dir

        cache_path = ensure_cache_dir(cache_dir)
        instance_id = str(uuid.uuid4())[:8]  # Generate a unique instance ID
        logger.info(f"Cache initialized with directory: {cache_path}, instance: {instance_id}")

        return {
            "cache_dir": cache_path,
            "ttl": ttl,
            "initialized": True,
            "instance_id": instance_id,
            "creation_time": time.time(),
            "is_test_dir": "mcp_nixos_test_cache" in cache_path,
        }
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")
        # Provide fallback configuration using temporary directory
        import tempfile as tmp_module

        fallback_dir = tmp_module.mkdtemp(prefix="mcp_nixos_temp_cache_")
        instance_id = str(uuid.uuid4())[:8]
        logger.warning(f"Using fallback cache directory: {fallback_dir}, instance: {instance_id}")
        return {
            "cache_dir": fallback_dir,
            "ttl": ttl,
            "initialized": False,
            "error": str(e),
            "instance_id": instance_id,
            "creation_time": time.time(),
            "is_test_dir": True,  # Mark as test/temp dir so it gets cleaned up
        }


def lock_file(
    file_handle: IO, exclusive: bool = True, blocking: bool = True, timeout: float = 5.0, retry_interval: float = 0.1
) -> bool:
    """
    Acquire a lock on a file handle in a cross-platform manner with timeout and retry support.

    Args:
        file_handle: An open file handle
        exclusive: Whether to request an exclusive (write) lock
        blocking: Whether to block until the lock is acquired
        timeout: Maximum time to wait for lock in seconds (only used if blocking=True)
        retry_interval: Time between retries in seconds

    Returns:
        True if lock was acquired, False otherwise
    """
    # Validate file handle
    if file_handle.closed:
        logger.error("Attempted to lock a closed file handle")
        return False

    start_time = time.time()
    # No need to track last error in this implementation

    # Use exponential backoff with jitter for retries
    current_interval = retry_interval

    while True:
        try:
            if sys.platform != "win32":
                # Unix platforms: use fcntl
                lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH

                if not blocking:
                    # Non-blocking attempt
                    try:
                        fcntl.flock(file_handle.fileno(), lock_type | fcntl.LOCK_NB)
                        return True
                    except (IOError, OSError) as e:
                        if e.errno in (errno.EACCES, errno.EAGAIN):
                            # Resource temporarily unavailable
                            return False
                        # Re-raise other errors
                        raise
                else:
                    # Blocking with timeout implementation
                    if timeout <= 0:
                        # Infinite blocking
                        fcntl.flock(file_handle.fileno(), lock_type)
                        return True
                    else:
                        # Try non-blocking first
                        try:
                            fcntl.flock(file_handle.fileno(), lock_type | fcntl.LOCK_NB)
                            return True
                        except (IOError, OSError) as e:
                            if e.errno not in (errno.EACCES, errno.EAGAIN):
                                # Unexpected error
                                raise

                            # Check if we've exceeded timeout
                            elapsed = time.time() - start_time
                            if elapsed >= timeout:
                                logger.warning(f"Lock acquisition timed out after {elapsed:.2f}s")
                                return False

                            # Wait and retry
                            time.sleep(current_interval)
                            # Increase backoff interval with jitter
                            current_interval = min(current_interval * 1.5, 0.5) * (0.9 + 0.2 * random.random())
                            continue
            else:
                # Windows: use msvcrt
                # Note: Windows doesn't support shared locks, so exclusive is ignored
                if not blocking:
                    # Try once and return immediately
                    try:
                        msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                        return True
                    except IOError:
                        return False
                else:
                    # Implement timeout for Windows too
                    if timeout <= 0:
                        # Standard blocking call
                        msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
                        return True
                    else:
                        # Loop with timeout
                        while time.time() - start_time < timeout:
                            try:
                                msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                                return True
                            except IOError:
                                # Wait and retry
                                time.sleep(current_interval)
                                # Increase backoff interval with jitter
                                current_interval = min(current_interval * 1.5, 0.5) * (0.9 + 0.2 * random.random())

                        logger.warning(f"Windows lock acquisition timed out after {time.time()-start_time:.2f}s")
                        return False
        except (IOError, OSError) as e:
            # Log error but don't need to store it
            logger.debug(f"Lock acquisition error: {e}")
            elapsed = time.time() - start_time

            if not blocking or elapsed >= timeout:
                if blocking:
                    # Only log as error for blocking calls that time out
                    logger.error(f"Failed to acquire file lock after {elapsed:.2f}s: {e}")
                return False

            # Wait and retry
            time.sleep(current_interval)
            # Increase backoff interval with jitter
            current_interval = min(current_interval * 1.5, 0.5) * (0.9 + 0.2 * random.random())

    # We should never reach here, but return False just in case
    return False


def unlock_file(file_handle: IO) -> bool:
    """
    Release a lock on a file handle in a cross-platform manner.

    Args:
        file_handle: An open file handle with an active lock

    Returns:
        True if unlock was successful, False otherwise
    """
    try:
        if sys.platform != "win32":
            # Unix platforms
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        else:
            # Windows
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        return True
    except (IOError, OSError) as e:
        logger.error(f"Failed to release file lock: {e}")
        return False


def atomic_write(
    file_path: Union[str, pathlib.Path],
    write_func: Callable[[IO], Any],  # Allow any return type, but we ignore it
    max_retries: int = 3,
    retry_delay: float = 0.1,
) -> bool:
    """
    Perform an atomic write operation to a file using a temporary file and rename.

    This implementation includes retry logic for high-contention scenarios and
    ensures proper cleanup of temporary files.

    Args:
        file_path: Path to the target file
        write_func: Function that takes a file object and writes data to it
        max_retries: Maximum number of retry attempts on failure
        retry_delay: Delay between retries in seconds

    Returns:
        True if the operation was successful, False otherwise
    """
    path = pathlib.Path(file_path)
    # Use a unique instance identifier in the temp filename to avoid conflicts
    instance_id = getattr(write_func, "instance_id", str(uuid.uuid4())[:8])
    temp_path = path.parent / f".{path.name}.{instance_id}.{uuid.uuid4()}.tmp"

    # Determine if we're writing in binary or text mode
    is_binary = "b" in getattr(write_func, "mode", "w")
    mode = "w+b" if is_binary else "w+"

    for attempt in range(max_retries + 1):
        try:
            # Ensure the parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first
            with open(temp_path, mode) as f:
                # Lock the temp file during write - use blocking with timeout
                start_time = time.time()
                max_lock_wait = 1.0  # Maximum seconds to wait for lock

                # Try to acquire lock with exponential backoff
                lock_acquired = False
                backoff_time = 0.01

                while time.time() - start_time < max_lock_wait:
                    if lock_file(f, exclusive=True, blocking=False):
                        lock_acquired = True
                        break

                    # Exponential backoff to reduce contention
                    time.sleep(backoff_time)
                    backoff_time = min(backoff_time * 2, 0.1)  # Cap at 100ms

                if not lock_acquired:
                    # Try one more time with blocking
                    lock_acquired = lock_file(f, exclusive=True, blocking=True)

                if lock_acquired:
                    try:
                        # Call the write function to write the data
                        write_func(f)
                        f.flush()
                        os.fsync(f.fileno())  # Ensure data is written to disk
                    finally:
                        unlock_file(f)
                else:
                    logger.warning(f"Failed to lock temporary file for atomic write (attempt {attempt+1}): {temp_path}")
                    if attempt < max_retries:
                        time.sleep(retry_delay * (attempt + 1))  # Progressive backoff
                        continue
                    else:
                        return False

            # Use a different approach based on platform for maximum atomicity
            target_exists = path.exists()

            if sys.platform == "win32" and target_exists:
                # On Windows, rename might fail if target exists, so we need a different approach
                # First get a lock on the target file if it exists
                try:
                    with open(path, "r+b" if is_binary else "r+") as target_file:
                        if lock_file(target_file, exclusive=True, blocking=True):
                            try:
                                # Now we can safely replace the file
                                os.replace(temp_path, path)
                            finally:
                                unlock_file(target_file)
                        else:
                            logger.error(f"Failed to lock target file for replacement: {path}")
                            return False
                except Exception as e:
                    logger.warning(f"Error while trying to lock existing target for replacement: {e}")
                    # Fall back to direct replacement
                    os.replace(temp_path, path)
            else:
                # On Unix, rename is atomic if the target is on the same filesystem
                os.replace(temp_path, path)

            logger.debug(f"Atomic write completed for {path} (attempt {attempt+1})")
            return True

        except Exception as e:
            logger.warning(f"Atomic write attempt {attempt+1} failed for {path}: {e}")

            # Clean up temp file if it exists
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass

            # Retry with backoff if not the last attempt
            if attempt < max_retries:
                retry_delay_with_jitter = retry_delay * (attempt + 1) * (0.9 + 0.2 * random.random())
                logger.debug(f"Retrying atomic write for {path} in {retry_delay_with_jitter:.2f}s")
                time.sleep(retry_delay_with_jitter)
            else:
                logger.error(f"All atomic write attempts failed for {path}")
                return False

    # Should never reach here, but return False just in case
    return False


def write_with_metadata(
    file_path: Union[str, pathlib.Path], content: str, metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Write content to a file with associated metadata in a separate metadata file.

    Args:
        file_path: Path to the target file
        content: Content string to write
        metadata: Optional metadata dictionary to write alongside the content

    Returns:
        True if both content and metadata were written successfully
    """
    path = pathlib.Path(file_path)
    meta_path = path.parent / f"{path.name}.meta"

    # Ensure metadata includes creation timestamp
    if metadata is None:
        metadata = {}

    if "creation_timestamp" not in metadata:
        metadata["creation_timestamp"] = time.time()

    # Write main content file
    content_written = atomic_write(path, lambda f: cast(None, f.write(content)))

    # Write metadata file
    metadata_written = atomic_write(meta_path, lambda f: cast(None, f.write(json.dumps(metadata, indent=2))))

    return content_written and metadata_written


def read_with_metadata(file_path: Union[str, pathlib.Path]) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Read content from a file along with its associated metadata file if it exists.

    Args:
        file_path: Path to the file to read

    Returns:
        Tuple of (content, metadata) where content is the file content and
        metadata is a dictionary of metadata (empty if no metadata file exists)
    """
    path = pathlib.Path(file_path)
    meta_path = path.parent / f"{path.name}.meta"
    metadata = {"file_path": str(path), "metadata_exists": False}
    content = None

    try:
        # Read main content with file locking to prevent reading during writes
        if path.exists():
            with open(path, "r") as f:
                if lock_file(f, exclusive=False, blocking=False):
                    try:
                        content = f.read()
                        metadata["file_mtime"] = path.stat().st_mtime
                    finally:
                        unlock_file(f)
                else:
                    logger.warning(f"Could not acquire lock to read {path}, file may be in use")
                    metadata["lock_error"] = True
                    return None, metadata

        # Read metadata file if it exists
        if meta_path.exists():
            with open(meta_path, "r") as f:
                if lock_file(f, exclusive=False, blocking=False):
                    try:
                        meta_content = f.read()
                        meta_data = json.loads(meta_content)
                        metadata.update(meta_data)
                        metadata["metadata_exists"] = True
                    finally:
                        unlock_file(f)
                else:
                    logger.warning(f"Could not acquire lock to read metadata for {path}")

        return content, metadata

    except Exception as e:
        logger.error(f"Error reading file with metadata {file_path}: {e}")
        metadata["error"] = str(e)
        return None, metadata
