"""Common fixtures for server-related tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_home_manager_context():
    """Create a mock Home Manager context for testing."""
    mock = MagicMock()
    mock.hm_client = MagicMock()
    mock.hm_client.load_in_background = MagicMock()
    mock.hm_client.is_loaded = True
    mock.hm_client.loading_error = None

    # Set up loading lock context manager
    mock_lock = MagicMock()
    mock_lock.__enter__ = MagicMock()
    mock_lock.__exit__ = MagicMock()
    mock.hm_client.loading_lock = mock_lock

    return mock


@pytest.fixture
def mock_darwin_context():
    """Create a mock Darwin context for testing."""
    mock = MagicMock()
    mock.startup = AsyncMock()
    mock.shutdown = AsyncMock()
    mock.status = "ready"
    return mock


@pytest.fixture
def mock_nixos_context():
    """Create a mock NixOS context for testing."""
    mock = MagicMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
def mock_state_persistence():
    """Create a mock state persistence object for testing."""
    mock = MagicMock()
    mock.set_state = MagicMock()
    mock.get_state = MagicMock(return_value=None)
    mock.save_state = MagicMock()
    return mock


@pytest.fixture
def mock_psutil():
    """Create a mock psutil module for testing."""
    mock = MagicMock()

    # Create a mock process
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.ppid.return_value = 54321
    mock_process.name.return_value = "python"
    mock_process.cmdline.return_value = ["python", "-m", "mcp_nixos"]

    # Create a mock parent process
    mock_parent = MagicMock()
    mock_parent.pid = 54321
    mock_parent.name.return_value = "bash"
    mock_parent.cmdline.return_value = ["bash"]

    # Set up Process constructor to return our mocks
    def mock_process_constructor(pid=None):
        if pid is None or pid == 12345:
            return mock_process
        elif pid == 54321:
            return mock_parent
        else:
            raise mock.NoSuchProcess(pid=pid)

    mock.Process = mock_process_constructor
    mock.NoSuchProcess = type("NoSuchProcess", (Exception,), {"pid": None})
    mock.AccessDenied = type("AccessDenied", (Exception,), {})

    return mock


@pytest.fixture
def server_mock_modules():
    """Create all necessary mocks for server module testing, to be used with patch_dict.

    This function creates only the mocks for the modules that actually exist and
    are needed for our tests.
    """
    # Create mocks directly here to avoid circular dependencies
    mock_home_manager_context = MagicMock()
    mock_home_manager_context.hm_client = MagicMock()
    mock_home_manager_context.hm_client.load_in_background = MagicMock()
    mock_home_manager_context.hm_client.is_loaded = True
    mock_home_manager_context.hm_client.loading_error = None

    # Set up loading lock context manager
    mock_lock = MagicMock()
    mock_lock.__enter__ = MagicMock()
    mock_lock.__exit__ = MagicMock()
    mock_home_manager_context.hm_client.loading_lock = mock_lock

    mock_darwin_context = MagicMock()
    mock_darwin_context.startup = AsyncMock()
    mock_darwin_context.shutdown = AsyncMock()
    mock_darwin_context.status = "ready"

    mock_nixos_context = MagicMock()
    mock_nixos_context.shutdown = AsyncMock()

    # Create a mock psutil module
    mock_psutil = MagicMock()
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.ppid.return_value = 54321
    mock_process.name.return_value = "python"
    mock_process.cmdline.return_value = ["python", "-m", "mcp_nixos"]

    # Create a mock parent process
    mock_parent = MagicMock()
    mock_parent.pid = 54321
    mock_parent.name.return_value = "bash"
    mock_parent.cmdline.return_value = ["bash"]

    # Set up Process constructor to return our mocks
    def mock_process_constructor(pid=None):
        if pid is None or pid == 12345:
            return mock_process
        elif pid == 54321:
            return mock_parent
        else:
            raise mock_psutil.NoSuchProcess(pid=pid)

    mock_psutil.Process = mock_process_constructor
    mock_psutil.NoSuchProcess = type("NoSuchProcess", (Exception,), {"pid": None})
    mock_psutil.AccessDenied = type("AccessDenied", (Exception,), {})

    mods = {
        "mcp_nixos.server.home_manager_context": mock_home_manager_context,
        "mcp_nixos.server.darwin_context": mock_darwin_context,
        "mcp_nixos.server.nixos_context": mock_nixos_context,
        "mcp_nixos.server.logger": MagicMock(),
        "mcp_nixos.server.mcp": MagicMock(),
        "mcp_nixos.server.async_with_timeout": AsyncMock(return_value=True),
        "mcp_nixos.server.psutil": mock_psutil,
        # Add a minimal set of mocks that definitely exist in the server module
    }

    # Since the mcp_nixos_prompt function is not exposed at the module level,
    # we don't include it in the mocks. It's only used as a method within server.py
    # and is not imported by other modules.

    return mods


@pytest.fixture
def patch_server_modules(server_mock_modules):
    """Patch all server module dependencies using the provided mocks."""
    patches = [patch(mod, val) for mod, val in server_mock_modules.items()]

    # Start all patches
    for p in patches:
        p.start()

    # Return control to the test
    yield

    # Stop all patches
    for p in patches:
        p.stop()
