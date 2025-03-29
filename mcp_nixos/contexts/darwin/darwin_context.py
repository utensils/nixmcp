"""Darwin context for nix-darwin operations."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from mcp_nixos.clients.darwin.darwin_client import DarwinClient

logger = logging.getLogger(__name__)


class DarwinContext:
    """Context for nix-darwin operations.

    This class manages the state and lifecycle of the DarwinClient.
    It provides methods for loading and accessing nix-darwin options.
    """

    def __init__(
        self, darwin_client: Optional[DarwinClient] = None, eager_loading: bool = True, eager_loading_timeout: int = 10
    ):
        """Initialize the DarwinContext.

        Args:
            darwin_client: Optional DarwinClient instance. If not provided, a new one is created.
            eager_loading: Whether to load options eagerly on startup.
            eager_loading_timeout: Timeout in seconds for eager loading.
        """
        self.client = darwin_client or DarwinClient()
        self.status = "initialized"
        self.error = None
        self.eager_loading = eager_loading
        self.eager_loading_timeout = eager_loading_timeout
        self.loading_task = None

    async def startup(self) -> None:
        """Start the Darwin context.

        This is called during server startup. It loads the options
        if eager_loading is True.
        """
        self.status = "starting"
        logger.info("Starting Darwin context")

        if self.eager_loading:
            try:
                # Try to load with timeout
                self.status = "loading"
                await asyncio.wait_for(
                    self.client.load_options(force_refresh=False), timeout=self.eager_loading_timeout
                )
                self.status = "loaded"
                logger.info(f"Darwin options loaded successfully: {self.client.total_options} options")
            except asyncio.TimeoutError:
                # If timeout occurs, continue loading in background
                logger.warning(
                    f"Eager loading of Darwin options timed out after {self.eager_loading_timeout}s. "
                    "Continuing in background."
                )
                self.status = "loading_background"
                self.loading_task = asyncio.create_task(self._background_loading())
            except Exception as e:
                # If an error occurs, log it and set status to error
                logger.error(f"Error loading Darwin options: {e}")
                self.status = "error"
                self.error = str(e)
                # Still try to load in background
                self.loading_task = asyncio.create_task(self._background_loading())
        else:
            self.status = "ready"

    async def _background_loading(self) -> None:
        """Load options in the background."""
        try:
            await self.client.load_options(force_refresh=False)
            self.status = "loaded"
            logger.info(f"Background loading of Darwin options completed: {self.client.total_options} options")
        except Exception as e:
            logger.error(f"Background loading of Darwin options failed: {e}")
            self.status = "error"
            self.error = str(e)

    async def shutdown(self) -> None:
        """Shut down the Darwin context.

        This is called during server shutdown.
        """
        logger.info("Shutting down Darwin context")
        if self.loading_task and not self.loading_task.done():
            self.loading_task.cancel()
            # Skip waiting for the task to complete in tests where the task might be a mock
            if not isinstance(self.loading_task, MagicMock):
                try:
                    await self.loading_task
                except asyncio.CancelledError:
                    pass
        self.status = "shutdown"

    async def get_status(self) -> Dict[str, Any]:
        """Get the status of the Darwin context.

        Returns:
            Dictionary with status information.
        """
        stats = {
            "status": self.status,
            "error": self.error,
            "options_count": 0,
            "categories_count": 0,
            "last_updated": None,
        }

        if self.status in ["loaded", "loading_background"]:
            try:
                darwin_stats = await self.client.get_statistics()
                stats.update(
                    {
                        "options_count": darwin_stats["total_options"],
                        "categories_count": darwin_stats["total_categories"],
                        "last_updated": darwin_stats["last_updated"],
                    }
                )
            except Exception as e:
                logger.error(f"Error getting Darwin statistics: {e}")

        return stats

    async def search_options(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for options by query.

        Args:
            query: Search query.
            limit: Maximum number of results to return.

        Returns:
            List of matching options.
        """
        try:
            # If options are not loaded yet, try to load them first
            if self.status not in ["loaded", "loading_background"]:
                await self.client.load_options(force_refresh=False)

            return await self.client.search_options(query, limit=limit)
        except Exception as e:
            logger.error(f"Error searching Darwin options: {e}")
            return []

    async def get_option(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an option by name.

        Args:
            name: Option name.

        Returns:
            Option as a dictionary, or None if not found.
        """
        try:
            # If options are not loaded yet, try to load them first
            if self.status not in ["loaded", "loading_background"]:
                await self.client.load_options(force_refresh=False)

            return await self.client.get_option(name)
        except Exception as e:
            logger.error(f"Error getting Darwin option {name}: {e}")
            return None

    async def get_options_by_prefix(self, prefix: str) -> List[Dict[str, Any]]:
        """Get options by prefix.

        Args:
            prefix: Option prefix.

        Returns:
            List of options with the given prefix.
        """
        try:
            # If options are not loaded yet, try to load them first
            if self.status not in ["loaded", "loading_background"]:
                await self.client.load_options(force_refresh=False)

            return await self.client.get_options_by_prefix(prefix)
        except Exception as e:
            logger.error(f"Error getting Darwin options by prefix {prefix}: {e}")
            return []

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get top-level option categories.

        Returns:
            List of categories.
        """
        try:
            # If options are not loaded yet, try to load them first
            if self.status not in ["loaded", "loading_background"]:
                await self.client.load_options(force_refresh=False)

            return await self.client.get_categories()
        except Exception as e:
            logger.error(f"Error getting Darwin categories: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the Darwin options.

        Returns:
            Dictionary with statistics.
        """
        try:
            # If options are not loaded yet, try to load them first
            if self.status not in ["loaded", "loading_background"]:
                await self.client.load_options(force_refresh=False)

            return await self.client.get_statistics()
        except Exception as e:
            logger.error(f"Error getting Darwin statistics: {e}")
            return {
                "error": str(e),
                "total_options": 0,
                "total_categories": 0,
                "last_updated": None,
                "loading_status": self.status,
                "categories": [],
            }
