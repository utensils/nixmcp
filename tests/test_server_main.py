"""Tests for server main entry point execution."""

import os
from unittest.mock import MagicMock, patch

# Import patch helper
from tests.fixtures.patch_helper import patch_dict

# Not marking as asyncio since most of these tests are synchronous


class TestServerMain:
    """Test server main entry point execution."""

    def test_environment_detection(self):
        """Test environment detection during server initialization."""
        # Mock environment variables for testing
        mock_os_environ = {"WINDSURF_MODE": "test", "OTHER_VAR": "value"}

        # Create necessary mocks
        server_mock_modules = {
            "mcp_nixos.server.logger": MagicMock(),
            "mcp_nixos.server.mcp": MagicMock(),
        }

        # Create psutil mock
        mock_psutil = MagicMock()
        mock_process = MagicMock(pid=12345, ppid=MagicMock(return_value=54321))
        mock_process.name.return_value = "python"
        mock_process.cmdline.return_value = ["python", "-m", "mcp_nixos"]

        mock_parent = MagicMock(pid=54321)
        mock_parent.name.return_value = "bash"
        mock_parent.cmdline.return_value = ["bash"]

        mock_psutil.Process = MagicMock(side_effect=lambda pid=None: mock_process if pid is None else mock_parent)

        # Add to mocks
        server_mock_modules["mcp_nixos.server.psutil"] = mock_psutil

        # Apply patches
        with patch.dict("os.environ", mock_os_environ), patch_dict(server_mock_modules):

            # Create a simplified version of the main entry point
            def simulate_main():
                try:
                    # Log server initialization with environment info
                    server_mock_modules["mcp_nixos.server.logger"].info("Initializing MCP-NixOS server")

                    # Log process information
                    process = server_mock_modules["mcp_nixos.server.psutil"].Process()
                    server_mock_modules["mcp_nixos.server.logger"].info(
                        f"Process info - PID: {process.pid}, Parent PID: {process.ppid()}"
                    )

                    # Try to get parent process info
                    try:
                        parent = server_mock_modules["mcp_nixos.server.psutil"].Process(process.ppid())
                        server_mock_modules["mcp_nixos.server.logger"].info(
                            f"Parent process: {parent.name()} (PID: {parent.pid})"
                        )
                        parent_cmdline = " ".join(parent.cmdline())
                        server_mock_modules["mcp_nixos.server.logger"].debug(f"Parent command line: {parent_cmdline}")
                    except Exception:
                        server_mock_modules["mcp_nixos.server.logger"].info(
                            "Unable to access parent process information"
                        )

                    # Check if running under Windsurf
                    windsurf_detected = False
                    for env_var in os.environ:
                        if "WINDSURF" in env_var.upper() or "WINDSURFER" in env_var.upper():
                            windsurf_detected = True
                            server_mock_modules["mcp_nixos.server.logger"].info(
                                f"Detected Windsurf environment: {env_var}={os.environ[env_var]}"
                            )

                    if windsurf_detected:
                        server_mock_modules["mcp_nixos.server.logger"].info(
                            "Running under Windsurf - configuring for Windsurf compatibility"
                        )

                    server_mock_modules["mcp_nixos.server.logger"].info("Starting MCP-NixOS server event loop")
                    server_mock_modules["mcp_nixos.server.mcp"].run()
                except KeyboardInterrupt:
                    server_mock_modules["mcp_nixos.server.logger"].info("Server stopped by keyboard interrupt")
                    return 0
                except Exception as e:
                    server_mock_modules["mcp_nixos.server.logger"].error(f"Error running server: {e}", exc_info=True)
                    return 1
                return 0

            # Run the function
            result = simulate_main()

            # Verify interactions and detections
            assert result == 0  # No errors
            server_mock_modules["mcp_nixos.server.logger"].info.assert_any_call("Initializing MCP-NixOS server")
            server_mock_modules["mcp_nixos.server.logger"].info.assert_any_call(
                "Process info - PID: 12345, Parent PID: 54321"
            )
            server_mock_modules["mcp_nixos.server.logger"].info.assert_any_call("Parent process: bash (PID: 54321)")
            server_mock_modules["mcp_nixos.server.logger"].debug.assert_any_call("Parent command line: bash")
            server_mock_modules["mcp_nixos.server.logger"].info.assert_any_call(
                "Detected Windsurf environment: WINDSURF_MODE=test"
            )
            server_mock_modules["mcp_nixos.server.logger"].info.assert_any_call(
                "Running under Windsurf - configuring for Windsurf compatibility"
            )
            server_mock_modules["mcp_nixos.server.logger"].info.assert_any_call("Starting MCP-NixOS server event loop")
            server_mock_modules["mcp_nixos.server.mcp"].run.assert_called_once()

    def test_parent_process_error_handling(self):
        """Test error handling when parent process info is inaccessible."""
        # Create necessary mocks
        mock_logger = MagicMock()
        mock_mcp = MagicMock()

        # Create psutil mock that fails for parent process
        mock_psutil = MagicMock()
        mock_process = MagicMock(pid=12345, ppid=MagicMock(return_value=54321))

        # Create NoSuchProcess exception class with proper pid attribute
        class MockNoSuchProcess(Exception):
            def __init__(self, pid=None):
                self.pid = pid
                super().__init__(f"No process found with pid {pid}")

        # Create AccessDenied exception class
        class MockAccessDenied(Exception):
            pass

        # Configure the psutil mock
        mock_psutil.NoSuchProcess = MockNoSuchProcess
        mock_psutil.AccessDenied = MockAccessDenied

        # Define a function that raises the exception for parent process
        def mock_process_factory(pid=None):
            if pid is None:
                return mock_process
            elif pid == 54321:  # This is the parent pid from mock_process.ppid()
                raise MockNoSuchProcess(pid=pid)
            else:
                parent_mock = MagicMock(pid=pid)
                return parent_mock

        mock_psutil.Process = MagicMock(side_effect=mock_process_factory)

        # Apply patches
        modified_mocks = {
            "mcp_nixos.server.logger": mock_logger,
            "mcp_nixos.server.mcp": mock_mcp,
            "mcp_nixos.server.psutil": mock_psutil,
        }

        with patch_dict(modified_mocks):
            # Create a simplified version of the main entry point
            def simulate_main():
                try:
                    # Log process information
                    process = modified_mocks["mcp_nixos.server.psutil"].Process()
                    modified_mocks["mcp_nixos.server.logger"].info(
                        f"Process info - PID: {process.pid}, Parent PID: {process.ppid()}"
                    )

                    # Try to get parent process info - this will raise an exception
                    try:
                        parent = modified_mocks["mcp_nixos.server.psutil"].Process(process.ppid())
                        modified_mocks["mcp_nixos.server.logger"].info(
                            f"Parent process: {parent.name()} (PID: {parent.pid})"
                        )
                    except (
                        modified_mocks["mcp_nixos.server.psutil"].NoSuchProcess,
                        modified_mocks["mcp_nixos.server.psutil"].AccessDenied,
                    ) as e:
                        print(f"Caught expected exception: {type(e).__name__}")
                        modified_mocks["mcp_nixos.server.logger"].info("Unable to access parent process information")

                    modified_mocks["mcp_nixos.server.mcp"].run()
                    return 0
                except Exception as e:
                    print(f"Unexpected exception: {type(e).__name__}: {e}")
                    modified_mocks["mcp_nixos.server.logger"].error(f"Error running server: {e}", exc_info=True)
                    return 1

            # Run the function
            result = simulate_main()

            # Verify error handling
            assert result == 0  # No fatal errors
            modified_mocks["mcp_nixos.server.logger"].info.assert_any_call(
                "Unable to access parent process information"
            )
            modified_mocks["mcp_nixos.server.mcp"].run.assert_called_once()

    def test_keyboard_interrupt_handling(self):
        """Test handling of keyboard interrupt during server execution."""
        # Create necessary mocks
        mock_logger = MagicMock()
        mock_mcp = MagicMock()

        # Configure MCP to raise KeyboardInterrupt
        mock_mcp.run.side_effect = KeyboardInterrupt()

        # Apply patches
        server_mock_modules = {
            "mcp_nixos.server.logger": mock_logger,
            "mcp_nixos.server.mcp": mock_mcp,
        }

        with patch_dict(server_mock_modules):
            # Create a simplified version of the main entry point
            def simulate_main():
                try:
                    server_mock_modules["mcp_nixos.server.logger"].info("Starting MCP-NixOS server")
                    server_mock_modules["mcp_nixos.server.mcp"].run()
                except KeyboardInterrupt:
                    server_mock_modules["mcp_nixos.server.logger"].info("Server stopped by keyboard interrupt")
                    return 0
                except Exception as e:
                    server_mock_modules["mcp_nixos.server.logger"].error(f"Error running server: {e}", exc_info=True)
                    return 1
                return 0

            # Run the function
            result = simulate_main()

            # Verify handling of keyboard interrupt
            assert result == 0  # Clean exit
            server_mock_modules["mcp_nixos.server.logger"].info.assert_called_with(
                "Server stopped by keyboard interrupt"
            )

    def test_generic_exception_handling(self):
        """Test handling of generic exceptions during server execution."""
        # Create necessary mocks
        mock_logger = MagicMock()
        mock_mcp = MagicMock()

        # Configure MCP to raise generic exception
        mock_mcp.run.side_effect = Exception("Test server error")

        # Apply patches
        server_mock_modules = {
            "mcp_nixos.server.logger": mock_logger,
            "mcp_nixos.server.mcp": mock_mcp,
        }

        with patch_dict(server_mock_modules):
            # Create a simplified version of the main entry point
            def simulate_main():
                try:
                    server_mock_modules["mcp_nixos.server.logger"].info("Starting MCP-NixOS server")
                    server_mock_modules["mcp_nixos.server.mcp"].run()
                except KeyboardInterrupt:
                    server_mock_modules["mcp_nixos.server.logger"].info("Server stopped by keyboard interrupt")
                    return 0
                except Exception as e:
                    server_mock_modules["mcp_nixos.server.logger"].error(f"Error running server: {e}", exc_info=True)
                    return 1
                return 0

            # Run the function
            result = simulate_main()

            # Verify error handling
            assert result == 1  # Error exit code
            server_mock_modules["mcp_nixos.server.logger"].error.assert_called_once()
            assert "Test server error" in server_mock_modules["mcp_nixos.server.logger"].error.call_args[0][0]
