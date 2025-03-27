"""Darwin client for fetching and parsing nix-darwin documentation."""

import dataclasses
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from bs4 import BeautifulSoup, Tag

from nixmcp.cache.html_cache import HTMLCache
from nixmcp.cache.simple_cache import SimpleCache
from nixmcp.clients.html_client import HTMLClient

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DarwinOption:
    """Data class for a nix-darwin configuration option."""

    name: str
    description: str
    type: str = ""
    default: str = ""
    example: str = ""
    declared_by: str = ""
    sub_options: Dict[str, "DarwinOption"] = dataclasses.field(default_factory=dict)
    parent: Optional[str] = None


class DarwinClient:
    """Client for fetching and parsing nix-darwin documentation."""

    BASE_URL = "https://daiderd.com/nix-darwin/manual"
    OPTION_REFERENCE_URL = f"{BASE_URL}/index.html"

    def __init__(self, html_client: Optional[HTMLClient] = None, cache_ttl: int = 86400):
        """Initialize the DarwinClient.

        Args:
            html_client: Optional HTMLClient to use for fetching. If not provided, a new one will be created.
            cache_ttl: Time-to-live for cache entries in seconds. Default is 24 hours.
        """
        # Get cache TTL from environment or use default (24 hours)
        self.cache_ttl = int(os.environ.get("NIXMCP_CACHE_TTL", cache_ttl))

        self.html_client = html_client or HTMLClient(ttl=self.cache_ttl)
        self.html_cache = HTMLCache("darwin", ttl=self.cache_ttl)
        self.memory_cache = SimpleCache(max_size=1000, ttl=self.cache_ttl)

        # Search indices
        self.options: Dict[str, DarwinOption] = {}
        self.name_index: Dict[str, List[str]] = defaultdict(list)
        self.word_index: Dict[str, Set[str]] = defaultdict(set)
        self.prefix_index: Dict[str, List[str]] = defaultdict(list)

        # Statistics
        self.total_options = 0
        self.total_categories = 0
        self.last_updated: Optional[datetime] = None
        self.loading_status = "not_started"
        self.error_message = ""

        # Version for cache compatibility
        self.data_version = "1.0.0"

        # Cache key for data
        self.cache_key = f"darwin_data_v{self.data_version}"

    async def fetch_url(self, url: str, force_refresh: bool = False) -> str:
        """Fetch URL content from the HTML client.

        This method adapts the HTMLClient.fetch() method which returns (content, metadata)
        to a simpler interface that returns just the content.

        Args:
            url: The URL to fetch
            force_refresh: Whether to bypass the cache

        Returns:
            The HTML content as a string

        Raises:
            ValueError: If the fetch fails
        """
        try:
            # The fetch method is not async, but we're in an async context
            # This approach ensures we don't block the event loop
            content, metadata = self.html_client.fetch(url, force_refresh=force_refresh)

            if content is None:
                error = metadata.get("error", "Unknown error")
                raise ValueError(f"Failed to fetch URL {url}: {error}")

            # Log cache status
            if metadata.get("from_cache", False):
                logger.debug(f"Retrieved {url} from cache")
            else:
                logger.debug(f"Retrieved {url} from web")

            return content

        except Exception as e:
            logger.error(f"Error in fetch_url for {url}: {str(e)}")
            raise

    async def load_options(self, force_refresh: bool = False) -> Dict[str, DarwinOption]:
        """Load nix-darwin options from documentation.

        Args:
            force_refresh: If True, ignore cache and fetch fresh data.

        Returns:
            Dict of options keyed by option name.
        """
        try:
            self.loading_status = "loading"

            # If force refresh, invalidate caches
            if force_refresh:
                logger.info("Forced refresh requested, invalidating caches")
                self.invalidate_cache()

            # Try to load from memory or filesystem cache first
            if not force_refresh and await self._load_from_memory_cache():
                self.loading_status = "loaded"
                return self.options

            # If cache fails, parse the HTML
            html = await self.fetch_url(self.OPTION_REFERENCE_URL, force_refresh=force_refresh)
            if not html:
                raise ValueError(f"Failed to fetch nix-darwin options from {self.OPTION_REFERENCE_URL}")

            soup = BeautifulSoup(html, "html.parser")
            await self._parse_options(soup)

            # Cache the parsed data
            await self._cache_parsed_data()

            self.loading_status = "loaded"
            self.last_updated = datetime.now()
            return self.options

        except Exception as e:
            self.loading_status = "error"
            self.error_message = str(e)
            logger.error(f"Error loading nix-darwin options: {e}")
            raise

    def invalidate_cache(self) -> None:
        """Invalidate both memory and filesystem cache for nix-darwin data."""
        try:
            logger.info(f"Invalidating nix-darwin data cache with key {self.cache_key}")

            # Clear memory cache by setting to None with the current timestamp
            if self.cache_key in self.memory_cache.cache:
                # Simple way to mark as invalid without needing a remove method
                del self.memory_cache.cache[self.cache_key]

            # Invalidate filesystem cache
            self.html_client.cache.invalidate_data(self.cache_key)

            # Also invalidate HTML cache for the source URL
            self.html_client.cache.invalidate(self.OPTION_REFERENCE_URL)

            logger.info("nix-darwin data cache invalidated")
        except Exception as e:
            logger.error(f"Failed to invalidate nix-darwin data cache: {str(e)}")
            # Continue execution, don't fail on cache invalidation errors

    async def _parse_options(self, soup: BeautifulSoup) -> None:
        """Parse nix-darwin options from BeautifulSoup object.

        Args:
            soup: BeautifulSoup object of the options page.
        """
        self.options = {}
        self.name_index = defaultdict(list)
        self.word_index = defaultdict(set)
        self.prefix_index = defaultdict(list)

        # Find option definitions (dl elements)
        option_dls = soup.find_all("dl", class_="variablelist")
        logger.info(f"Found {len(option_dls)} variablelist elements")

        total_processed = 0

        for dl in option_dls:
            # Process each dt/dd pair
            dts = dl.find_all("dt")

            for dt in dts:
                # Get the option element with the id
                option_link = dt.find("a", id=lambda x: x and x.startswith("opt-"))

                if not option_link:
                    # Try finding a link with href to an option
                    option_link = dt.find("a", href=lambda x: x and x.startswith("#opt-"))
                    if not option_link:
                        continue

                # Extract option id from the element
                if option_link.get("id"):
                    option_id = option_link.get("id", "")
                elif option_link.get("href"):
                    option_id = option_link.get("href", "").lstrip("#")
                else:
                    continue

                if not option_id.startswith("opt-"):
                    continue

                # Find the option name inside the link
                option_code = dt.find("code", class_="option")
                if option_code:
                    option_name = option_code.text.strip()
                else:
                    # Fall back to ID-based name
                    option_name = option_id[4:]  # Remove the opt- prefix

                # Get the description from the dd
                dd = dt.find_next("dd")
                if not dd:
                    continue

                option = self._parse_option_details(option_name, dd)
                if option:
                    self.options[option_name] = option
                    self._index_option(option)
                    total_processed += 1

                    # Log progress every 250 options to reduce log verbosity
                    if total_processed % 250 == 0:
                        logger.info(f"Processed {total_processed} options...")

        # Update statistics
        self.total_options = len(self.options)
        self.total_categories = len(self._get_top_level_categories())
        logger.info(f"Parsed {self.total_options} options in {self.total_categories} categories")

    def _parse_option_details(self, name: str, dd: Tag) -> Optional[DarwinOption]:
        """Parse option details from a dd tag.

        Args:
            name: Option name.
            dd: The dd tag containing option details.

        Returns:
            DarwinOption object or None if parsing failed.
        """
        try:
            # Extract description and other metadata
            description = ""
            option_type = ""
            default_value = ""
            example = ""
            declared_by = ""

            # Extract paragraphs for description
            paragraphs = dd.find_all("p", recursive=False)
            if paragraphs:
                description = " ".join(p.get_text(strip=True) for p in paragraphs)

            # Find the type, default, and example information
            type_element = dd.find("span", string=lambda text: text and "Type:" in text)
            if type_element and type_element.parent:
                option_type = type_element.parent.get_text().replace("Type:", "").strip()

            default_element = dd.find("span", string=lambda text: text and "Default:" in text)
            if default_element and default_element.parent:
                default_value = default_element.parent.get_text().replace("Default:", "").strip()

            example_element = dd.find("span", string=lambda text: text and "Example:" in text)
            if example_element and example_element.parent:
                example_value = example_element.parent.get_text().replace("Example:", "").strip()
                if example_value:
                    example = example_value

            # Alternative approach for finding metadata - look for itemizedlists
            if not option_type or not default_value or not example:
                # Look for type, default, example in itemizedlists
                for div in dd.find_all("div", class_="itemizedlist"):
                    item_text = div.get_text(strip=True)

                    if "Type:" in item_text and not option_type:
                        option_type = item_text.split("Type:", 1)[1].strip()
                    elif "Default:" in item_text and not default_value:
                        default_value = item_text.split("Default:", 1)[1].strip()
                    elif "Example:" in item_text and not example:
                        example = item_text.split("Example:", 1)[1].strip()
                    elif "Declared by:" in item_text and not declared_by:
                        declared_by = item_text.split("Declared by:", 1)[1].strip()

            # Look for declared_by information
            code_elements = dd.find_all("code")
            for code in code_elements:
                if "nix" in code.get_text() or "darwin" in code.get_text():
                    declared_by = code.get_text(strip=True)
                    break

            return DarwinOption(
                name=name,
                description=description,
                type=option_type,
                default=default_value,
                example=example,
                declared_by=declared_by,
                sub_options={},
                parent=None,
            )
        except Exception as e:
            logger.error(f"Error parsing option {name}: {e}")
            return None

    def _index_option(self, option: DarwinOption) -> None:
        """Index an option for searching.

        Args:
            option: The option to index.
        """
        # Index by name
        name_parts = option.name.split(".")
        for i in range(len(name_parts)):
            prefix = ".".join(name_parts[: i + 1])
            self.name_index[prefix].append(option.name)

            # Add to prefix index
            if i < len(name_parts) - 1:
                self.prefix_index[prefix].append(option.name)

        # Index by words in name and description
        name_words = re.findall(r"\w+", option.name.lower())
        desc_words = re.findall(r"\w+", option.description.lower())

        for word in set(name_words + desc_words):
            if len(word) > 2:  # Skip very short words
                self.word_index[word].add(option.name)

    def _get_top_level_categories(self) -> List[str]:
        """Get top-level option categories.

        Returns:
            List of top-level category names.
        """
        categories = set()
        for name in self.options.keys():
            parts = name.split(".")
            if parts:
                categories.add(parts[0])
        return sorted(list(categories))

    async def _load_from_memory_cache(self) -> bool:
        """Attempt to load options from memory cache.

        Returns:
            True if loading was successful, False otherwise.
        """
        try:
            # First try loading from memory cache
            cached_data = self.memory_cache.get(self.cache_key)
            if cached_data:
                logger.info("Found darwin options in memory cache")
                self.options = cached_data.get("options", {})
                self.name_index = cached_data.get("name_index", defaultdict(list))
                self.word_index = cached_data.get("word_index", defaultdict(set))
                self.prefix_index = cached_data.get("prefix_index", defaultdict(list))
                self.total_options = cached_data.get("total_options", 0)
                self.total_categories = cached_data.get("total_categories", 0)

                if "last_updated" in cached_data:
                    self.last_updated = cached_data["last_updated"]

                return bool(self.options)

            # If memory cache fails, try loading from filesystem cache
            return await self._load_from_filesystem_cache()

        except Exception as e:
            logger.error(f"Error loading from memory cache: {e}")
            return False

    async def _load_from_filesystem_cache(self) -> bool:
        """Attempt to load data from disk cache.

        Returns:
            bool: True if successfully loaded from cache, False otherwise
        """
        try:
            logger.info("Attempting to load nix-darwin data from disk cache")

            # Load the basic metadata
            data, metadata = self.html_client.cache.get_data(self.cache_key)
            if not data or not metadata.get("cache_hit", False):
                logger.info(f"No cached data found for key {self.cache_key}")
                return False

            # Check if we have the binary data as well
            binary_data, binary_metadata = self.html_client.cache.get_binary_data(self.cache_key)
            if not binary_data or not binary_metadata.get("cache_hit", False):
                logger.info(f"No cached binary data found for key {self.cache_key}")
                return False

            # Load basic options data
            # Convert dictionaries back to DarwinOption objects
            self.options = {}
            for name, option_dict in data["options"].items():
                self.options[name] = DarwinOption(
                    name=option_dict["name"],
                    description=option_dict["description"],
                    type=option_dict.get("type", ""),
                    default=option_dict.get("default", ""),
                    example=option_dict.get("example", ""),
                    declared_by=option_dict.get("declared_by", ""),
                    sub_options={},  # Sub-options will be populated if needed
                    parent=option_dict.get("parent", None),
                )

            self.total_options = data.get("total_options", 0)
            self.total_categories = data.get("total_categories", 0)

            if "last_updated" in data:
                self.last_updated = datetime.fromisoformat(data["last_updated"])

            # Load complex data structures
            self.name_index = binary_data["name_index"]

            # Convert lists back to sets for the word_index
            self.word_index = defaultdict(set)
            for k, v in binary_data["word_index"].items():
                self.word_index[k] = set(v)

            self.prefix_index = binary_data["prefix_index"]

            # Memory cache for faster subsequent access
            await self._cache_to_memory()

            logger.info(f"Successfully loaded nix-darwin data from disk cache with {len(self.options)} options")
            return True
        except Exception as e:
            logger.error(f"Failed to load nix-darwin data from disk cache: {str(e)}")
            return False

    async def _cache_parsed_data(self) -> None:
        """Cache parsed data to memory cache and filesystem."""
        try:
            # First cache to memory for fast access
            await self._cache_to_memory()

            # Then persist to filesystem cache
            await self._save_to_filesystem_cache()
        except Exception as e:
            logger.error(f"Error caching parsed data: {e}")

    async def _cache_to_memory(self) -> None:
        """Cache parsed data to memory cache."""
        try:
            cache_data = {
                "options": self.options,
                "name_index": dict(self.name_index),
                "word_index": {k: list(v) for k, v in self.word_index.items()},
                "prefix_index": dict(self.prefix_index),
                "total_options": self.total_options,
                "total_categories": self.total_categories,
                "last_updated": self.last_updated or datetime.now(),
            }
            # SimpleCache.set is not async - don't use await
            self.memory_cache.set(self.cache_key, cache_data)
        except Exception as e:
            logger.error(f"Error caching data to memory: {e}")

    async def _save_to_filesystem_cache(self) -> bool:
        """Save in-memory data structures to disk cache.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Saving nix-darwin data structures to disk cache")

            # Prepare basic data for JSON serialization
            # Convert DarwinOption objects to dictionaries for JSON serialization
            serializable_options = {name: self._option_to_dict(option) for name, option in self.options.items()}

            serializable_data = {
                "options": serializable_options,
                "total_options": self.total_options,
                "total_categories": self.total_categories,
                "last_updated": self.last_updated.isoformat() if self.last_updated else datetime.now().isoformat(),
                "timestamp": time.time(),
            }

            # Save the basic metadata as JSON
            self.html_client.cache.set_data(self.cache_key, serializable_data)

            # For complex data structures, use binary serialization
            binary_data = {
                "name_index": dict(self.name_index),
                "word_index": {k: list(v) for k, v in self.word_index.items()},
                "prefix_index": dict(self.prefix_index),
            }

            self.html_client.cache.set_binary_data(self.cache_key, binary_data)
            logger.info(f"Successfully saved nix-darwin data to disk cache with key {self.cache_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save nix-darwin data to disk cache: {str(e)}")
            return False

    async def search_options(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for options by query.

        Args:
            query: Search query.
            limit: Maximum number of results to return.

        Returns:
            List of matching options as dictionaries.
        """
        if not self.options:
            raise ValueError("Options not loaded. Call load_options() first.")

        results = []

        # Priority 1: Exact name match
        if query in self.options:
            results.append(self._option_to_dict(self.options[query]))

        # Priority 2: Prefix match
        if len(results) < limit:
            prefix_matches = self.name_index.get(query, [])
            for name in prefix_matches:
                if name not in [r["name"] for r in results]:
                    results.append(self._option_to_dict(self.options[name]))
                    if len(results) >= limit:
                        break

        # Priority 3: Word match
        if len(results) < limit:
            query_words = re.findall(r"\w+", query.lower())
            matched_options = set()

            for word in query_words:
                if len(word) > 2:
                    matched_options.update(self.word_index.get(word, set()))

            for name in matched_options:
                if name not in [r["name"] for r in results]:
                    results.append(self._option_to_dict(self.options[name]))
                    if len(results) >= limit:
                        break

        return results[:limit]

    async def get_option(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an option by name.

        Args:
            name: Option name.

        Returns:
            Option as a dictionary, or None if not found.
        """
        if not self.options:
            raise ValueError("Options not loaded. Call load_options() first.")

        option = self.options.get(name)
        if not option:
            return None

        return self._option_to_dict(option)

    async def get_options_by_prefix(self, prefix: str) -> List[Dict[str, Any]]:
        """Get options by prefix.

        Args:
            prefix: Option prefix.

        Returns:
            List of options with the given prefix.
        """
        if not self.options:
            raise ValueError("Options not loaded. Call load_options() first.")

        options = []
        for name in sorted(self.prefix_index.get(prefix, [])):
            options.append(self._option_to_dict(self.options[name]))

        return options

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get top-level option categories.

        Returns:
            List of category information with option counts.
        """
        if not self.options:
            raise ValueError("Options not loaded. Call load_options() first.")

        categories = []
        for category in self._get_top_level_categories():
            count = len(self.prefix_index.get(category, []))
            categories.append(
                {
                    "name": category,
                    "option_count": count,
                    "path": category,
                }
            )

        return categories

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the loaded options.

        Returns:
            Dictionary with statistics.
        """
        if not self.options:
            raise ValueError("Options not loaded. Call load_options() first.")

        return {
            "total_options": self.total_options,
            "total_categories": self.total_categories,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "loading_status": self.loading_status,
            "categories": await self.get_categories(),
        }

    def _option_to_dict(self, option: DarwinOption) -> Dict[str, Any]:
        """Convert an option to a dictionary.

        Args:
            option: The option to convert.

        Returns:
            Dictionary representation of the option.
        """
        return {
            "name": option.name,
            "description": option.description,
            "type": option.type,
            "default": option.default,
            "example": option.example,
            "declared_by": option.declared_by,
            "sub_options": [self._option_to_dict(sub) for sub in option.sub_options.values()],
            "parent": option.parent,
        }
