"""
Helper functions for NixMCP.
"""

import logging

# Get logger
logger = logging.getLogger("nixmcp")


def create_wildcard_query(query: str) -> str:
    """Create a wildcard query from a regular query string.

    Args:
        query: The original query string

    Returns:
        A query string with wildcards added
    """
    if " " in query:
        # For multi-word queries, add wildcards around each word
        words = query.split()
        wildcard_terms = [f"*{word}*" for word in words]
        return " ".join(wildcard_terms)
    else:
        # For single word queries, just wrap with wildcards
        return f"*{query}*"
