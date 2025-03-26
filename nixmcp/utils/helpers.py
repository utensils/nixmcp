"""
Helper functions for NixMCP.
"""

import logging
from typing import Optional, Callable, TypeVar

# Get logger
logger = logging.getLogger("nixmcp")

# Type variables for better type annotations
T = TypeVar("T")


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


def get_context_or_fallback(context: Optional[T], context_name: str) -> T:
    """Get the provided context or fall back to global context.

    Args:
        context: The context passed to the function, potentially None
        context_name: The name of the context to retrieve from server if not provided

    Returns:
        The provided context or the global context from the server
    """
    if context is None:
        # Import here to avoid circular imports
        import nixmcp.server

        return getattr(nixmcp.server, context_name)

    return context


def check_loading_status(func: Callable) -> Callable:
    """Decorator that checks if Home Manager client is loaded before executing a method.

    This decorator is intended for HomeManagerContext methods to avoid duplicating the
    loading status check code across multiple methods.

    Args:
        func: The function to decorate

    Returns:
        A wrapped function that checks loading status before executing
    """

    def wrapper(self, *args, **kwargs):
        # Get the default response values based on the method name
        method_name = func.__name__
        default_values = {}

        # Add method-specific default values
        if method_name == "search_options":
            default_values = {"count": 0, "options": []}
        elif method_name == "get_option" and args:
            default_values = {"name": args[0]}  # First arg should be option_name
        elif method_name == "get_stats":
            default_values = {"total_options": 0}

        # Check if data is still being loaded
        with self.hm_client.loading_lock:
            if not self.hm_client.is_loaded and self.hm_client.loading_in_progress:
                # Return a loading status instead of waiting indefinitely
                response = {
                    "loading": True,
                    "error": "Home Manager data is still being loaded. Please try again in a moment.",
                    "found": False,
                }
                response.update(default_values)
                return response

            # If loading failed, report the error
            if self.hm_client.loading_error:
                response = {
                    "loading": False,
                    "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                    "found": False,
                }
                response.update(default_values)
                return response

        # Ensure we have the client and it's not loading
        if not hasattr(self, "hm_client") or not self.hm_client:
            response = {
                "loading": False,
                "error": "Home Manager client not initialized",
                "found": False,
            }
            response.update(default_values)
            return response

        # If we get here, the client is loaded and ready, so call the original function
        return func(self, *args, **kwargs)

    return wrapper
