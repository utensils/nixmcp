"""Tests for state persistence across reconnections."""

import os
import json
import pytest
import tempfile
from unittest.mock import patch

# Mark as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def state_file_path():
    """Create a temporary state file for tests."""
    tmp_dir = tempfile.mkdtemp()
    state_file = os.path.join(tmp_dir, "mcp_state.json")
    yield state_file
    # Cleanup
    if os.path.exists(state_file):
        os.remove(state_file)
    os.rmdir(tmp_dir)


class TestStatePersistence:
    """Test state persistence across server reconnections."""

    def test_state_persistence_across_restarts(self, state_file_path):
        """Test that critical state persists across server restarts."""
        # Import module after patching environment
        with patch.dict(os.environ, {"MCP_NIXOS_STATE_FILE": state_file_path}):
            from mcp_nixos.utils.state_persistence import StatePersistence

            # Create first instance and set state
            persistence = StatePersistence()
            persistence.set_state("connection_count", 5)
            persistence.set_state("last_query", "nixos_search")
            persistence.save_state()

            # Create second instance (simulates restart)
            persistence2 = StatePersistence()
            persistence2.load_state()

            # Verify state was preserved
            assert persistence2.get_state("connection_count") == 5
            assert persistence2.get_state("last_query") == "nixos_search"

    def test_state_file_created_if_missing(self, state_file_path):
        """Test that state file is created if not found."""
        # Ensure file doesn't exist
        if os.path.exists(state_file_path):
            os.remove(state_file_path)

        with patch.dict(os.environ, {"MCP_NIXOS_STATE_FILE": state_file_path}):
            from mcp_nixos.utils.state_persistence import StatePersistence

            # Create instance
            persistence = StatePersistence()
            persistence.set_state("test_key", "test_value")
            persistence.save_state()

            # Verify file was created
            assert os.path.exists(state_file_path)

            # Verify content
            with open(state_file_path, "r") as f:
                data = json.load(f)
                assert data.get("test_key") == "test_value"

    def test_connection_counter_persistence(self, state_file_path):
        """Test that connection counter persists across restarts."""
        with patch.dict(os.environ, {"MCP_NIXOS_STATE_FILE": state_file_path}):
            from mcp_nixos.utils.state_persistence import StatePersistence

            # First "server instance"
            persistence1 = StatePersistence()
            # Simulate loading state in first run (will be empty)
            persistence1.load_state()

            # Get and increment counter
            current = persistence1.get_state("connection_count", 0)
            assert current == 0  # Initial value
            persistence1.set_state("connection_count", current + 1)
            persistence1.save_state()

            # Second "server instance"
            persistence2 = StatePersistence()
            persistence2.load_state()

            # Counter should be persisted
            assert persistence2.get_state("connection_count") == 1

            # Increment again
            current = persistence2.get_state("connection_count")
            persistence2.set_state("connection_count", current + 1)
            persistence2.save_state()

            # Third "server instance"
            persistence3 = StatePersistence()
            persistence3.load_state()

            # Verify counter was properly preserved
            assert persistence3.get_state("connection_count") == 2
