"""
Shared utility functions for MCP completions.
"""

import logging
from typing import Dict

# Get logger
logger = logging.getLogger("nixmcp")


def create_completion_item(label: str, value: str, detail: str = "") -> Dict[str, str]:
    """
    Create a standardized completion item following the MCP specification.

    Args:
        label: Display text for the user
        value: Actual value to insert
        detail: Optional longer description

    Returns:
        Dictionary with label, value and optional detail
    """
    item = {"label": label, "value": value}
    if detail:
        item["detail"] = detail
    return item
