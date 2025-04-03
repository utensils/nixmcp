"""Helper functions for patching in tests."""

import contextlib
from unittest.mock import patch


@contextlib.contextmanager
def patch_dict(patch_dict):
    """Apply multiple patches from a dictionary.

    Args:
        patch_dict: A dictionary of {target: mock_value} pairs to patch

    Yields:
        None: Just provides a context manager
    """
    # Create patch objects
    patchers = []
    for target, value in patch_dict.items():
        # Only try to patch targets that exist
        # This helps avoid errors when running tests against different versions
        # of the code where some attributes might not exist
        try:
            patcher = patch(target, value)
            patchers.append(patcher)
        except (AttributeError, ImportError) as e:
            print(f"Warning: Could not patch {target}: {e}")

    # Start all patchers
    for patcher in patchers:
        patcher.start()

    try:
        # Yield control back to the context
        yield
    finally:
        # Stop all patchers
        for patcher in patchers:
            patcher.stop()
