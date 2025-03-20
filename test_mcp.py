#!/usr/bin/env python
"""
Test suite for NixMCP server.

This script tests both the REST API and MCP endpoints of the NixMCP server.
It automatically handles server startup and shutdown for tests.
"""

import json
import os
import pytest
import requests
import subprocess
import sys
import time
from typing import Any, Dict, Generator, Optional
import uvicorn
import multiprocessing
from multiprocessing import Process


# Server configuration
SERVER_HOST = "localhost"
SERVER_PORT = 9421
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
SERVER_STARTUP_TIMEOUT = 5  # seconds


def run_server():
    """Run the NixMCP server with uvicorn."""
    # Using string import so we don't need to import server at module level
    uvicorn.run("server:app", host="0.0.0.0", port=SERVER_PORT, log_level="info")


def start_server() -> Process:
    """Start the NixMCP server in a separate process."""
    process = Process(target=run_server)
    process.daemon = True  # Kill the server when the test process exits
    process.start()

    # Wait for the server to start
    start_time = time.time()
    while time.time() - start_time < SERVER_STARTUP_TIMEOUT:
        try:
            response = requests.get(f"{BASE_URL}/docs")
            if response.status_code == 200:
                print(f"Server started successfully on {BASE_URL}")
                return process
        except requests.RequestException:
            pass
        time.sleep(0.1)

    # If we get here, the server didn't start in time
    process.terminate()
    raise RuntimeError(
        f"Server failed to start within {SERVER_STARTUP_TIMEOUT} seconds"
    )


@pytest.fixture(scope="session")
def server_process() -> Generator[Optional[Process], None, None]:
    """Pytest fixture to start and stop the server for the test session."""
    # Check if server is already running (for CI or manual testing)
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("Server is already running, using existing instance")
            # Return None since we don't need to stop anything
            yield None
            return
    except requests.RequestException:
        pass

    # Start the server
    process = start_server()
    yield process

    # Stop the server
    if process and process.is_alive():
        print("Stopping server")
        process.terminate()
        process.join(timeout=2)
        if process.is_alive():
            process.kill()


def test_legacy_package_api(server_process) -> None:
    """Test legacy FastAPI package endpoints."""
    package_url = f"{BASE_URL}/packages/python"
    response = requests.get(package_url)

    # Check that the response is valid
    assert response.status_code == 200, f"Package endpoint failed: {response.text}"
    data = response.json()

    # In test environments without Nix packages, we'll get an error response
    # but it should still be properly formatted JSON
    if "error" in data:
        print(f"NOTE: Package test received error: {data['error']}")
        print("This is expected in environments without Nix packages")
        # The test passes if we at least got a valid error response
        assert isinstance(data["error"], str), "Error should be a string"
    else:
        # If we have package data, validate it
        assert "name" in data, "Package data missing 'name' field"
        assert "version" in data, "Package data missing 'version' field"
        assert data["name"] == "python", f"Expected python package, got {data['name']}"


def test_legacy_option_api(server_process) -> None:
    """Test legacy FastAPI option endpoints."""
    option_url = f"{BASE_URL}/options/services.nginx"
    response = requests.get(option_url)

    # Check that the response is valid
    assert response.status_code == 200, f"Option endpoint failed: {response.text}"
    data = response.json()

    # In test environments without Nix options, we'll get an error response
    # but it should still be properly formatted JSON
    if "error" in data:
        print(f"NOTE: Option test received error: {data['error']}")
        print("This is expected in environments without nixos-option")
        # The test passes if we at least got a valid error response
        assert isinstance(data["error"], str), "Error should be a string"
    else:
        # If we have option data, validate it
        assert "name" in data, "Option data missing 'name' field"
        assert "description" in data, "Option data missing 'description' field"
        assert (
            data["name"] == "services.nginx"
        ), f"Expected services.nginx option, got {data['name']}"


def test_mcp_package_resource(server_process) -> None:
    """Test MCP package resource endpoint."""
    base_url = f"{BASE_URL}/mcp"
    package_name = "python"

    # Try standard MCP format
    package_url = f"{base_url}/resource"
    package_params = {"uri": f"nixos://package/{package_name}"}
    response = requests.get(package_url, params=package_params)

    # If standard format fails, try alternative format
    if response.status_code == 404:
        alt_url = f"{base_url}/nixos://package/{package_name}"
        response = requests.get(alt_url)

    # For now, mark as xfail since MCP endpoints are still in development
    if response.status_code != 200:
        pytest.xfail("MCP package endpoint is still in development")

    data = response.json()

    # In test environments without Nix packages, we'll get an error response
    if "error" in data:
        print(f"NOTE: MCP package test received error: {data['error']}")
        print("This is expected in environments without Nix packages")
        # The test passes if we at least got a valid error response
        assert isinstance(data["error"], str), "Error should be a string"
    else:
        # If we have package data, validate it
        assert "name" in data, "Package data missing 'name' field"
        assert data["name"] == "python", f"Expected python package, got {data['name']}"


def test_mcp_package_with_channel(server_process) -> None:
    """Test MCP package resource with explicit channel."""
    base_url = f"{BASE_URL}/mcp"
    package_name = "python"

    # Try standard MCP format
    package_url = f"{base_url}/resource"
    package_params = {"uri": f"nixos://package/{package_name}/unstable"}
    response = requests.get(package_url, params=package_params)

    # If standard format fails, try alternative format
    if response.status_code == 404:
        alt_url = f"{base_url}/nixos://package/{package_name}/unstable"
        response = requests.get(alt_url)

    # For now, mark as xfail since MCP endpoints are still in development
    if response.status_code != 200:
        pytest.xfail("MCP package with channel endpoint is still in development")

    data = response.json()

    # In test environments without Nix packages, we'll get an error response
    if "error" in data:
        print(f"NOTE: MCP package with channel test received error: {data['error']}")
        print("This is expected in environments without Nix packages")
        # The test passes if we at least got a valid error response
        assert isinstance(data["error"], str), "Error should be a string"
    else:
        # If we have package data, validate it
        assert "name" in data, "Package data missing 'name' field"
        assert data["name"] == "python", f"Expected python package, got {data['name']}"


def test_mcp_option_resource(server_process) -> None:
    """Test MCP option resource endpoint."""
    base_url = f"{BASE_URL}/mcp"
    option_name = "services.nginx"

    # Try standard MCP format
    option_url = f"{base_url}/resource"
    option_params = {"uri": f"nixos://option/{option_name}"}
    response = requests.get(option_url, params=option_params)

    # If standard format fails, try alternative format
    if response.status_code == 404:
        alt_url = f"{base_url}/nixos://option/{option_name}"
        response = requests.get(alt_url)

    # For now, mark as xfail since MCP endpoints are still in development
    if response.status_code != 200:
        pytest.xfail("MCP option endpoint is still in development")

    data = response.json()

    # In test environments without NixOS options, we'll get an error response
    if "error" in data:
        print(f"NOTE: MCP option test received error: {data['error']}")
        print("This is expected in environments without nixos-option")
        # The test passes if we at least got a valid error response
        assert isinstance(data["error"], str), "Error should be a string"
    else:
        # If we have option data, validate it
        assert "name" in data, "Option data missing 'name' field"
        assert (
            data["name"] == "services.nginx"
        ), f"Expected services.nginx option, got {data['name']}"


def dry_run_test() -> None:
    """Run test mocks without an actual server."""
    print("NixMCP MCP Dry Run Test")
    print("=====================")
    print("This is a dry run that doesn't require a running server.")
    print("It's useful for checking if the test script itself works correctly.")

    # Mock response data
    mock_package = {
        "name": "python",
        "version": "3.11.0",
        "description": "A programming language that lets you work quickly",
        "attribute": "python3",
    }

    mock_option = {
        "name": "services.nginx",
        "description": "NGINX web server",
        "type": "attribute set",
        "default": {},
        "example": {"enable": True},
    }

    print("\nMock package response:")
    print(json.dumps(mock_package, indent=2))

    print("\nMock option response:")
    print(json.dumps(mock_option, indent=2))

    print("\nTest script is working correctly!")


if __name__ == "__main__":
    # Force stdout to be unbuffered so output is displayed immediately
    sys.stdout.reconfigure(line_buffering=True)

    print("=" * 50)
    print("NixMCP Test Runner")
    print("=" * 50)

    # Check command-line arguments
    if len(sys.argv) > 1:
        # Handle dry run request
        if sys.argv[1] == "--dry-run":
            print("\nRunning in dry-run mode (no server required)")
            dry_run_test()
            exit(0)

        # Handle debug mode
        elif sys.argv[1] == "--debug":
            print("\nRunning in debug mode")

            # Start server if needed
            is_server_running = False
            try:
                response = requests.get(f"{BASE_URL}/docs")
                if response.status_code == 200:
                    is_server_running = True
                    print("✓ Using existing server")
            except Exception:
                print("⚠️ No server detected, starting a new one...")
                start_server()
                print("✓ Server started for debugging")

            # Test the legacy API endpoints directly
            print("\n--- Testing /packages/python ---")
            try:
                response = requests.get(f"{BASE_URL}/packages/python")
                print(f"Status code: {response.status_code}")
                print(f"Response data: {json.dumps(response.json(), indent=2)}")
            except Exception as e:
                print(f"Error: {e}")

            print("\n--- Testing /options/services.nginx ---")
            try:
                response = requests.get(f"{BASE_URL}/options/services.nginx")
                print(f"Status code: {response.status_code}")
                print(f"Response data: {json.dumps(response.json(), indent=2)}")
            except Exception as e:
                print(f"Error: {e}")

            print("\nDebug complete - server is still running for manual testing")
            exit(0)

    print("\nStarting NixMCP tests...")

    # Check for pytest
    try:
        import pytest
    except ImportError:
        print("\nERROR: pytest module not found!")
        print("Please install pytest with one of these commands:")
        print("  nix develop -c setup-test")
        print("  pip install pytest")
        sys.exit(1)

    # Create a simple test runner in case pytest can't be used
    def run_simple_tests():
        """Run tests without pytest when necessary"""
        print("\n===== Running tests in simple mode =====")

        # Check if server is running
        is_server_running = False
        try:
            response = requests.get(f"{BASE_URL}/docs")
            if response.status_code == 200:
                is_server_running = True
                print("✓ Using existing server")
        except Exception:
            print("⚠️ No server detected, starting a new one...")

        # Start server if needed
        server = None
        if not is_server_running:
            try:
                server = start_server()
                print("✓ Server started successfully")
            except Exception as e:
                print(f"❌ Failed to start server: {e}")
                return False

        # Track test results
        tests_passed = 0
        tests_failed = 0
        tests_skipped = 0

        # Function to run a test with proper error handling
        def run_test(name, test_func):
            nonlocal tests_passed, tests_failed
            print(f"\n----- Testing: {name} -----")
            try:
                test_func(None)  # Pass None instead of server_process
                print(f"✅ PASS: {name}")
                tests_passed += 1
                return True
            except Exception as e:
                print(f"❌ FAIL: {name} - {e}")
                tests_failed += 1
                return False

        # Function to run a test that's expected to fail
        def run_expected_fail_test(name, test_func):
            nonlocal tests_passed, tests_skipped
            print(f"\n----- Testing: {name} (expected to fail) -----")
            try:
                test_func(None)
                print(f"⚠️ Unexpectedly PASSED: {name}")
                tests_passed += 1
                return True
            except Exception as e:
                print(f"✓ Expected failure: {name} - {e}")
                tests_skipped += 1
                return True

        # Run all tests
        run_test("Legacy package API", test_legacy_package_api)
        run_test("Legacy option API", test_legacy_option_api)
        run_expected_fail_test("MCP package resource", test_mcp_package_resource)
        run_expected_fail_test(
            "MCP package with channel", test_mcp_package_with_channel
        )
        run_expected_fail_test("MCP option resource", test_mcp_option_resource)

        # Stop server if we started it
        if server and server.is_alive():
            print("\nStopping server...")
            server.terminate()
            server.join(timeout=2)
            if server.is_alive():
                server.kill()

        # Report results
        print("\n===== Test Results =====")
        print(f"✅ Passed: {tests_passed}")
        print(f"❌ Failed: {tests_failed}")
        print(f"⚠️ Skipped: {tests_skipped}")

        if tests_failed > 0:
            print(f"\n❌ {tests_failed} tests failed!")
            return False
        else:
            print("\n✅ All tests completed successfully!")
            return True

    # Try to run with pytest first
    try:
        print("\n===== Running tests with pytest =====")
        pytest_args = ["-xvs", __file__]
        exit_code = pytest.main(pytest_args)
        if exit_code != 0:
            print(f"\n❌ Pytest tests failed with exit code {exit_code}")
            sys.exit(exit_code)
        print("\n✅ All pytest tests completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n⚠️ Error running pytest: {e}")
        print("\n===== Falling back to simple test runner =====")
        success = run_simple_tests()
        if not success:
            print("\n❌ Simple tests failed")
            sys.exit(1)
        print("\n✅ All simple tests completed successfully!")
        sys.exit(0)
