"""State persistence across MCP server reconnections.

This module provides a way to persist critical state across MCP server reconnections,
which is particularly important for the stdio transport where each reconnection
starts a new server process.
"""

import os
import json
import time
import logging
import threading
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

# Get logger
logger = logging.getLogger("mcp_nixos")


class StatePersistence:
    """Persistent state storage for MCP server.

    This class provides a way to persist critical state between server restarts,
    which is useful for maintaining connection counts, metrics, and other
    stateful information that would otherwise be lost when the server restarts
    due to connection refresh or other events.
    """

    def __init__(self):
        """Initialize the state persistence with the state file path."""
        self._state: Dict[str, Any] = {}
        self._lock = threading.RLock()

        # Get state file path from environment or use default
        state_file = os.environ.get("MCP_NIXOS_STATE_FILE")

        # If no explicit state file, use the cache directory
        if not state_file:
            cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR")
            if not cache_dir:
                # Default to a system-appropriate temp location
                cache_dir = os.path.join(tempfile.gettempdir(), "mcp_nixos_cache")

            # Ensure directory exists
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            state_file = os.path.join(cache_dir, "mcp_state.json")

        self._state_file = state_file
        logger.debug(f"State persistence initialized with state file: {self._state_file}")

        # Create empty file if it doesn't exist
        if not os.path.exists(self._state_file):
            try:
                with open(self._state_file, "w") as f:
                    json.dump({}, f)
            except Exception as e:
                logger.warning(f"Could not create state file: {e}")

    def set_state(self, key: str, value: Any) -> None:
        """Set a state value by key.

        Args:
            key: The state key
            value: The value to store
        """
        with self._lock:
            self._state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value by key.

        Args:
            key: The state key
            default: Default value if key not found

        Returns:
            The stored value or default
        """
        with self._lock:
            return self._state.get(key, default)

    def delete_state(self, key: str) -> None:
        """Delete a state value by key.

        Args:
            key: The state key to delete
        """
        with self._lock:
            if key in self._state:
                del self._state[key]

    def increment_counter(self, key: str, increment: int = 1) -> int:
        """Increment a counter value.

        Args:
            key: The counter key
            increment: Amount to increment by

        Returns:
            The new counter value
        """
        with self._lock:
            current = self._state.get(key, 0)
            if not isinstance(current, (int, float)):
                current = 0
            new_value = current + increment
            self._state[key] = new_value
            return int(new_value)

    def load_state(self) -> bool:
        """Load state from disk.

        Returns:
            True if state was loaded successfully, False otherwise
        """
        with self._lock:
            try:
                if os.path.exists(self._state_file):
                    with open(self._state_file, "r") as f:
                        loaded_state = json.load(f)
                        self._state.update(loaded_state)
                    logger.debug(f"Loaded state from {self._state_file}")
                    return True
                else:
                    logger.debug(f"State file not found at {self._state_file}")
                    return False
            except Exception as e:
                logger.error(f"Error loading state: {e}")
                return False

    def save_state(self) -> bool:
        """Save state to disk.

        Returns:
            True if state was saved successfully, False otherwise
        """
        with self._lock:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self._state_file), exist_ok=True)

                # Add timestamp to state
                state_to_save = self._state.copy()
                state_to_save["_last_saved"] = time.time()

                # Write to temp file first
                temp_file = f"{self._state_file}.tmp"
                with open(temp_file, "w") as f:
                    json.dump(state_to_save, f)

                # Rename to actual file (atomic operation)
                os.replace(temp_file, self._state_file)

                logger.debug(f"Saved state to {self._state_file}")
                return True
            except Exception as e:
                logger.error(f"Error saving state: {e}")
                return False


# Global instance for easy access
_state_persistence: Optional[StatePersistence] = None


def get_state_persistence() -> StatePersistence:
    """Get the global state persistence instance.

    Returns:
        The global StatePersistence instance
    """
    global _state_persistence
    if _state_persistence is None:
        _state_persistence = StatePersistence()
    return _state_persistence
