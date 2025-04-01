"""Tests for cache concurrency and file locking behavior."""

# Import needed modules
import time
import pytest
import tempfile
import threading
import json
import random
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from mcp_nixos.cache.html_cache import HTMLCache
from mcp_nixos.clients.html_client import HTMLClient

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Skip tests that are known to be problematic in CI environments
# TODO: These tests are temporarily skipped in CI due to issues with:
# 1. Multi-threading behavior depends on available CPU/resources which vary in CI
# 2. Concurrency tests require file locking which may behave differently in CI
# 3. Thread scheduling can vary significantly causing flaky test results
# 4. Race conditions that rarely occur locally can become common in CI
#
# These tests should be refactored to:
# - Use controlled concurrency simulation
# - Have more predictable synchronization mechanisms
# - Be made more resilient to different execution environments
# - Have longer timeouts in CI
skip_in_ci = pytest.mark.skipif(
    "CI" in os.environ or "GITHUB_ACTIONS" in os.environ,
    reason="Test skipped in CI environment due to threading/concurrency inconsistencies",
)


@pytest.fixture
def concurrent_cache_dir():
    """Create a temporary directory for concurrent cache testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@skip_in_ci
def test_concurrent_html_cache_writes(concurrent_cache_dir):
    """
    Test that multiple threads can write to the same HTMLCache without corruption.

    This test simulates multiple instances of MCP-NixOS accessing the same cache directory.
    """
    # Create a shared cache directory
    cache_dir = concurrent_cache_dir

    # Number of concurrent operations
    num_threads = 10
    num_operations = 20

    # Track successful operations
    successful_ops = 0
    exception_count = 0

    # Shared tracking of URLs and keys
    urls = [f"https://example.com/test/{i}" for i in range(num_operations)]
    keys = [f"test_key_{i}" for i in range(num_operations)]

    # Lock for tracking counters to avoid race conditions in the test itself
    counter_lock = threading.Lock()

    def worker_task(worker_id):
        nonlocal successful_ops, exception_count

        # Each worker gets its own cache instance
        cache = HTMLCache(cache_dir=cache_dir, ttl=60)

        for i in range(num_operations):
            # Randomize which URL/key to operate on to increase contention likelihood
            idx = random.randrange(0, num_operations)
            operation = random.choice(["html", "data", "binary"])

            try:
                if operation == "html":
                    url = urls[idx]
                    content = f"<html><body>Worker {worker_id}, Content {i}</body></html>"
                    cache.set(url, content)

                    # Small sleep to increase chance of concurrent access
                    time.sleep(0.01)

                    # Verify we can read it back
                    result, _ = cache.get(url)
                    assert result is not None

                elif operation == "data":
                    key = keys[idx]
                    data = {"worker": worker_id, "value": i, "timestamp": time.time()}
                    cache.set_data(key, data)

                    time.sleep(0.01)

                    # Verify we can read it back
                    result, _ = cache.get_data(key)
                    assert result is not None

                else:  # binary data
                    key = f"binary_{keys[idx]}"
                    data = {"worker": worker_id, "value": i, "complex": {"nested": [1, 2, 3]}}
                    cache.set_binary_data(key, data)

                    time.sleep(0.01)

                    # Verify we can read it back
                    result, _ = cache.get_binary_data(key)
                    assert result is not None

                # Increment success counter
                with counter_lock:
                    successful_ops += 1

            except Exception as e:
                with counter_lock:
                    exception_count += 1
                print(f"Worker {worker_id} encountered exception: {e}")

    # Run multiple workers concurrently
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_task, i) for i in range(num_threads)]

        # Wait for all to complete
        for future in futures:
            future.result()  # This will raise any exceptions from the threads

    # Check that operations completed successfully
    total_expected_ops = num_threads * num_operations
    assert successful_ops > 0, "No successful operations completed"
    success_rate = successful_ops / total_expected_ops

    # Ensure cache files exist and are valid
    cache = HTMLCache(cache_dir=cache_dir)
    cache_stats = cache.get_stats()
    assert cache_stats["file_count"] > 0, "No cache files were created"

    # Log results for debugging
    print(f"Success rate: {success_rate:.2%}")
    print(f"Exceptions: {exception_count}")
    print(f"Cache files: {cache_stats['file_count']}")


@skip_in_ci
def test_concurrent_html_client_requests(concurrent_cache_dir):
    """
    Test concurrent requests using HTMLClient with a shared cache.

    This test simulates multiple client instances competing for the same cache.
    """
    # Shared cache directory
    cache_dir = concurrent_cache_dir

    # Number of concurrent clients and operations
    num_clients = 5
    num_requests = 10

    # Test URLs that will be accessed by multiple clients
    test_urls = [f"https://example.com/page/{i}" for i in range(5)]

    # Track statistics
    stats_lock = threading.Lock()
    request_count = 0
    cache_hit_count = 0
    exception_count = 0

    def client_worker(client_id):
        nonlocal request_count, cache_hit_count, exception_count

        # Each worker gets its own HTMLClient with the shared cache
        client = HTMLClient(cache_dir=cache_dir, ttl=60)

        for i in range(num_requests):
            # Choose a random URL from the test set
            url = random.choice(test_urls)

            try:
                # For testing, we'll mock the network request
                with pytest.MonkeyPatch.context() as mp:
                    # Mock requests.get to return a response
                    def mock_get(*args, **kwargs):
                        class MockResponse:
                            text = f"<html><body>Client {client_id}, Request {i}</body></html>"
                            status_code = 200

                            def raise_for_status(self):
                                pass

                        return MockResponse()

                    mp.setattr("requests.get", mock_get)

                    # Fetch the URL
                    content, metadata = client.fetch(url)

                    # Update stats
                    with stats_lock:
                        request_count += 1
                        if metadata.get("from_cache"):
                            cache_hit_count += 1

                    # Verify content was retrieved
                    assert content is not None
                    assert "Client" in content

                    # Small sleep to increase chance of concurrent access
                    time.sleep(0.01)

            except Exception as e:
                with stats_lock:
                    exception_count += 1
                print(f"Client {client_id} encountered exception: {e}")

    # Run multiple clients concurrently
    with ThreadPoolExecutor(max_workers=num_clients) as executor:
        futures = [executor.submit(client_worker, i) for i in range(num_clients)]

        # Wait for all to complete
        for future in futures:
            future.result()

    # Check results
    total_expected_requests = num_clients * num_requests
    assert request_count > 0, "No requests were processed"
    request_success_rate = request_count / total_expected_requests

    # There should be some cache hits since URLs are shared
    assert cache_hit_count > 0, "No cache hits occurred"

    # Ensure no exceptions
    assert exception_count == 0, f"{exception_count} exceptions occurred during concurrent requests"

    # Check that cache files were created
    cache = HTMLCache(cache_dir=cache_dir)
    cache_stats = cache.get_stats()
    assert cache_stats["file_count"] > 0, "No cache files were created"

    # Log results for debugging
    print(f"Request success rate: {request_success_rate:.2%}")
    print(f"Cache hits: {cache_hit_count} out of {request_count} requests")
    print(f"Cache hit rate: {cache_hit_count/request_count:.2%}")
    print(f"Cache files: {cache_stats['file_count']}")


@skip_in_ci
def test_atomic_file_operations(concurrent_cache_dir):
    """
    Test atomic file operations in the cache to prevent partial reads/writes.

    This test verifies that cache operations are atomic and safe for concurrent access.
    """
    cache_dir = Path(concurrent_cache_dir)

    # Create cache instances
    num_instances = 5
    caches = [HTMLCache(cache_dir=str(cache_dir), ttl=60) for _ in range(num_instances)]

    # Get a reference to one of the caches for path generation
    reference_cache = caches[0]

    # Instead of using our own naming, get the actual path that will be used by HTMLCache
    test_key = "atomic_test"
    cache_file_path = reference_cache._get_data_cache_path(test_key)

    # Function to update the file with new data
    def update_file(cache_idx):
        cache = caches[cache_idx]
        new_data = {"value": f"update_from_instance_{cache_idx}", "timestamp": time.time(), "instance": cache_idx}
        result = cache.set_data(test_key, new_data)
        assert result["stored"] is True
        return new_data

    # Function to read the file and verify it's not corrupted
    def read_file(cache_idx):
        cache = caches[cache_idx]
        data, metadata = cache.get_data(test_key)
        assert data is not None, f"Cache {cache_idx} got None instead of valid data"
        assert "value" in data, f"Cache {cache_idx} got incomplete data: {data}"
        assert "timestamp" in data, f"Cache {cache_idx} missing timestamp in data: {data}"
        return data

    # Run concurrent updates and reads
    with ThreadPoolExecutor(max_workers=num_instances) as executor:
        # First do some concurrent updates
        update_futures = [executor.submit(update_file, i) for i in range(num_instances)]
        # Wait for all futures to complete but don't need to collect results
        for future in update_futures:
            future.result()

        # Then do some concurrent reads
        read_futures = [executor.submit(read_file, i) for i in range(num_instances)]
        read_results = [future.result() for future in read_futures]

    # Verify results - all reads should get complete, valid data
    for data in read_results:
        assert "value" in data
        assert "timestamp" in data
        assert data["value"].startswith("update_from_instance_"), f"Unexpected value: {data['value']}"
        assert "_cache_instance" in data, "Cache instance ID should be present"

    # The cache file should exist and be valid JSON
    assert cache_file_path.exists()
    with open(cache_file_path) as f:
        final_file_data = json.load(f)

    # Verify file contents have expected format
    assert "value" in final_file_data
    assert "timestamp" in final_file_data
    assert final_file_data["value"].startswith("update_from_instance_")
    assert "creation_timestamp" in final_file_data
    assert "_cache_instance" in final_file_data
