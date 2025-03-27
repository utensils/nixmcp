"""Darwin client for fetching and parsing nix-darwin documentation."""

import dataclasses
import logging
import os
import pathlib
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Sized

from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement

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
        # Use the HTMLCache that's already in the html_client, instead of creating a new one
        self.html_cache = self.html_client.cache
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
            if self.html_client and self.html_client.cache:
                self.html_client.cache.invalidate_data(self.cache_key)

                # Also invalidate HTML cache for the source URL
                self.html_client.cache.invalidate(self.OPTION_REFERENCE_URL)

            # Special handling for bad legacy cache files in current directory
            legacy_bad_path = pathlib.Path("darwin")
            if legacy_bad_path.exists() and legacy_bad_path.is_dir():
                logger.warning("Found legacy 'darwin' directory in current path - attempting cleanup")
                try:
                    # Only remove if it's empty or seems to contain cache files
                    safe_to_remove = True
                    for item in legacy_bad_path.iterdir():
                        condition1 = item.name.endswith(".html")
                        condition2 = item.name.endswith(".data.json")
                        condition3 = item.name.endswith(".data.pickle")
                        if not (condition1 or condition2 or condition3):
                            safe_to_remove = False
                            break

                    if safe_to_remove:
                        for item in legacy_bad_path.iterdir():
                            if item.is_file():
                                logger.info(f"Removing legacy cache file: {item}")
                                item.unlink()
                        logger.info("Removing legacy darwin directory")
                        legacy_bad_path.rmdir()
                    else:
                        logger.warning("Legacy 'darwin' directory contains non-cache files - not removing")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to clean up legacy cache: {cleanup_err}")

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
        option_dls: Sequence[PageElement] = []
        if isinstance(soup, BeautifulSoup) or isinstance(soup, Tag):
            option_dls = soup.find_all("dl", class_="variablelist")
        logger.info(f"Found {len(option_dls)} variablelist elements")

        total_processed = 0

        for dl in option_dls:
            # Process each dt/dd pair
            dts: Sequence[PageElement] = []
            if isinstance(dl, Tag):
                dts = dl.find_all("dt")

            for dt in dts:
                # Get the option element with the id
                option_link = None
                if isinstance(dt, Tag):
                    # BeautifulSoup's find method accepts keyword arguments directly for attributes
                    # Use a lambda that returns a boolean for attribute matching
                    option_link = dt.find(
                        "a", attrs={"id": lambda x: bool(x) and isinstance(x, str) and x.startswith("opt-")}
                    )

                if not option_link and isinstance(dt, Tag):
                    # Try finding a link with href to an option
                    # Use a lambda that returns a boolean for attribute matching
                    option_link = dt.find(
                        "a", attrs={"href": lambda x: bool(x) and isinstance(x, str) and x.startswith("#opt-")}
                    )
                    if not option_link:
                        continue

                # Extract option id from the element
                option_id = ""
                if option_link and isinstance(option_link, Tag):
                    if option_link.get("id"):
                        option_id = str(option_link.get("id", ""))
                    elif option_link.get("href"):
                        href_value = option_link.get("href", "")
                        if isinstance(href_value, str):
                            option_id = href_value.lstrip("#")
                    else:
                        continue

                if not option_id.startswith("opt-"):
                    continue

                # Find the option name inside the link
                option_code = None
                if isinstance(dt, Tag):
                    # BeautifulSoup's find method accepts class_ for class attribute
                    option_code = dt.find("code", class_="option")
                if option_code and hasattr(option_code, "text"):
                    option_name = option_code.text.strip()
                else:
                    # Fall back to ID-based name
                    option_name = option_id[4:]  # Remove the opt- prefix

                # Get the description from the dd
                dd = None
                if isinstance(dt, Tag):
                    dd = dt.find_next("dd")
                if not dd or not isinstance(dd, Tag):
                    continue

                # Process the option details
                option = self._parse_option_details(option_name, dd)
                if option:
                    self.options[option_name] = option
                    self._index_option(option_name, option)
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
            paragraphs: Sequence[PageElement] = []
            if isinstance(dd, Tag):
                paragraphs = dd.find_all("p", recursive=False)
            if paragraphs:
                description = " ".join(p.get_text(strip=True) for p in paragraphs if hasattr(p, "get_text"))

            # Extract metadata using the helper function
            metadata = self._extract_metadata_from_dd(dd)
            option_type = metadata["type"]
            default_value = metadata["default"]
            example = metadata["example"]
            declared_by = metadata["declared_by"]

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

    def _extract_metadata_from_dd(self, dd: Tag) -> Dict[str, str]:
        """Extract type, default, example, and declared_by from a dd tag."""
        metadata = {
            "type": "",
            "default": "",
            "example": "",
            "declared_by": "",
        }

        # Find the type, default, and example information using spans
        type_element = None
        if isinstance(dd, Tag):
            # Use attrs for more reliable matching
            type_element = dd.find("span", string="Type:")
        if (
            type_element
            and isinstance(type_element, Tag)
            and type_element.parent
            and hasattr(type_element.parent, "get_text")
        ):
            metadata["type"] = type_element.parent.get_text().replace("Type:", "").strip()

        default_element = None
        if isinstance(dd, Tag):
            default_element = dd.find("span", string="Default:")
        if (
            default_element
            and isinstance(default_element, Tag)
            and default_element.parent
            and hasattr(default_element.parent, "get_text")
        ):
            metadata["default"] = default_element.parent.get_text().replace("Default:", "").strip()

        example_element = None
        if isinstance(dd, Tag):
            example_element = dd.find("span", string="Example:")
        if (
            example_element
            and isinstance(example_element, Tag)
            and example_element.parent
            and hasattr(example_element.parent, "get_text")
        ):
            example_value = example_element.parent.get_text().replace("Example:", "").strip()
            if example_value:
                metadata["example"] = example_value

        # Alternative approach: look for itemizedlists if fields are missing
        if not metadata["type"] or not metadata["default"] or not metadata["example"]:
            if isinstance(dd, Tag):
                for div in dd.find_all("div", class_="itemizedlist"):
                    if hasattr(div, "get_text"):
                        item_text = div.get_text(strip=True)
                        if isinstance(item_text, str):
                            if "Type:" in item_text and not metadata["type"]:
                                metadata["type"] = item_text.split("Type:", 1)[1].strip()
                            elif "Default:" in item_text and not metadata["default"]:
                                metadata["default"] = item_text.split("Default:", 1)[1].strip()
                            elif "Example:" in item_text and not metadata["example"]:
                                metadata["example"] = item_text.split("Example:", 1)[1].strip()
                            elif "Declared by:" in item_text and not metadata["declared_by"]:
                                metadata["declared_by"] = item_text.split("Declared by:", 1)[1].strip()

        # Look for declared_by information in code tags if still missing
        if not metadata["declared_by"] and isinstance(dd, Tag):
            code_elements = dd.find_all("code")
            for code in code_elements:
                if hasattr(code, "get_text"):
                    code_text = code.get_text()
                    if isinstance(code_text, str) and ("nix" in code_text or "darwin" in code_text):
                        metadata["declared_by"] = code.get_text(strip=True)
                        break

        return metadata

    def _index_option(self, option_name: str, option: DarwinOption) -> None:
        """Index an option for searching.

        Args:
            option: The option to index.
        """
        # Index by name
        name_parts = option_name.split(".")
        for i in range(len(name_parts)):
            prefix = ".".join(name_parts[: i + 1])
            self.name_index[prefix].append(option_name)

            # Add to prefix index
            if i < len(name_parts) - 1:
                self.prefix_index[prefix].append(option_name)

        # Index by words in name and description
        name_words = re.findall(r"\w+", option_name.lower())
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

            # Check if cache is available
            if not self.html_client or not self.html_client.cache:
                logger.warning("HTML client or cache not available")
                return False

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

            # Validate data before loading - prevent loading empty datasets
            if not data.get("options") or len(data["options"]) == 0:
                logger.warning("Cached data has empty options dictionary - ignoring cache")
                return False

            if data.get("total_options", 0) == 0:
                logger.warning("Cached data has zero total_options - ignoring cache")
                return False

            # Make sure we have a reasonable number of options (sanity check)
            if len(data["options"]) < 10:
                logger.warning(f"Cached data has suspiciously few options: {len(data['options'])} - ignoring cache")
                return False

            # Make sure our indices are not empty
            name_index_missing = not binary_data.get("name_index")
            word_index_missing = not binary_data.get("word_index")
            prefix_index_missing = not binary_data.get("prefix_index")

            if name_index_missing or word_index_missing or prefix_index_missing:
                logger.warning("Cached binary data has empty indices - ignoring cache")
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

            # Final validation check
            if len(self.options) != self.total_options:
                logger.warning(
                    f"Data integrity issue: option count mismatch ({len(self.options)} vs {self.total_options})"
                )
                # Fix the count to match reality
                self.total_options = len(self.options)

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
            # Check if cache is available
            if not self.html_client or not self.html_client.cache:
                logger.warning("HTML client or cache not available")
                return False

            # Don't cache empty data sets
            if not self.options or not isinstance(self.options, dict) or len(self.options) == 0:
                logger.warning("Not caching empty options dataset - no options were found")
                return False

            if self.total_options == 0:
                logger.warning("Not caching options dataset with zero total_options")
                return False

            logger.info(f"Saving nix-darwin data structures to disk cache with {len(self.options)} options")

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

            # Additional validation check
            if len(serializable_options) < 10:
                logger.warning(
                    f"Only found {len(serializable_options)} options, which is suspiciously low. "
                    "Checking data validity..."
                )

                # Verify that we have more than just empty structures
                if (
                    not isinstance(serializable_data, dict)
                    or "options" not in serializable_data
                    or not isinstance(serializable_data["options"], Sized)
                    or len(serializable_data["options"]) == 0
                    or self.total_options < 10
                ):
                    logger.error(
                        "Data validation failed: Too few options found, refusing to cache potentially corrupt data"
                    )
                    return False

            # Save the basic metadata as JSON
            self.html_client.cache.set_data(self.cache_key, serializable_data)

            # For complex data structures, use binary serialization
            binary_data = {
                "name_index": dict(self.name_index),
                "word_index": {k: list(v) for k, v in self.word_index.items()},
                "prefix_index": dict(self.prefix_index),
            }

            # Verify index data integrity
            if not binary_data["name_index"] or not binary_data["word_index"] or not binary_data["prefix_index"]:
                logger.error("Data validation failed: Missing index data, refusing to cache incomplete data")
                return False

            if self.html_client and self.html_client.cache:
                self.html_client.cache.set_binary_data(self.cache_key, binary_data)
            logger.info(f"Successfully saved nix-darwin data to disk cache with key {self.cache_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save nix-darwin data to disk cache: {str(e)}")
            return False

    async def search_options(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for options by query.

        Args:
            query: Search query. Can include multiple words, quoted phrases for exact matching,
                  and supports fuzzy matching for typos.
            limit: Maximum number of results to return.

        Returns:
            List of matching options as dictionaries.
        """
        if not self.options:
            raise ValueError("Options not loaded. Call load_options() first.")

        results = []
        scored_matches: Dict[str, int] = {}
        query = query.strip()

        # Handle empty query
        if not query:
            # Return a sample of options as a fallback
            sample_size = min(limit, len(self.options))
            sample_names = list(self.options.keys())[:sample_size]
            return [self._option_to_dict(self.options[name]) for name in sample_names]

        # Priority 1: Exact name match
        if query in self.options:
            results.append(self._option_to_dict(self.options[query]))

        # Extract quoted phrases for exact matching
        quoted_phrases = re.findall(r'"([^"]+)"', query)
        # Remove quoted phrases from the query for word matching
        clean_query = re.sub(r'"[^"]+"', "", query)

        # Get individual words, filtering out short words
        query_words = [w.lower() for w in re.findall(r"\w+", clean_query) if len(w) > 2]

        # Add the original query as a whole if it's not too long
        if len(query) < 50 and " " not in query and query not in query_words:
            query_words.append(query.lower())

        # Priority 2: Prefix match and hierarchical path matching
        remaining_limit = limit - len(results)
        if remaining_limit > 0:
            # Check for hierarchical path matches (e.g., "programs.git")
            path_components = query.split(".")
            if len(path_components) > 1:
                # Prioritize options that match the hierarchical path pattern
                for name in self.options:
                    name_components = name.split(".")
                    if len(name_components) >= len(path_components):
                        # Check if all components match as a prefix
                        if all(nc.startswith(pc) for nc, pc in zip(name_components, path_components)):
                            if name not in [r["name"] for r in results]:
                                score = 100 - (len(name) - len(query))  # Shorter matches get higher scores
                                scored_matches[name] = max(scored_matches.get(name, 0), score)

            # Regular prefix matching
            for word in query_words:
                prefix_matches = self.name_index.get(word, [])
                for name in prefix_matches:
                    if name not in [r["name"] for r in results]:
                        # Score based on how early the match occurs in the name
                        name_lower = name.lower()
                        position = name_lower.find(word)
                        if position != -1:
                            # Higher score for matches at the beginning or after a separator
                            score = 80
                            if position == 0 or name_lower[position - 1] in ".-_":
                                score += 10
                            # Adjust score based on match position
                            score -= int(position * 0.5)
                            scored_matches[name] = max(scored_matches.get(name, 0), score)

        # Priority 3: Word match with scoring
        remaining_limit = limit - len(results)
        if remaining_limit > 0:
            # Process each word in the query
            for word in query_words:
                # Exact word matches
                if word in self.word_index:
                    for name in self.word_index[word]:
                        if name not in [r["name"] for r in results]:
                            # Base score for exact word match
                            score = 60
                            # Boost score if the word appears in name multiple times
                            name_lower = name.lower()
                            word_count = name_lower.count(word)
                            if word_count > 1:
                                score += 5 * (word_count - 1)
                            scored_matches[name] = max(scored_matches.get(name, 0), score)

                # Fuzzy matching for words longer than 4 characters
                if len(word) > 4:
                    # Simple fuzzy matching - check for words with one character different
                    for index_word in self.word_index:
                        if abs(len(index_word) - len(word)) <= 1:  # Length must be similar
                            # Calculate Levenshtein distance (or a simpler approximation)
                            distance = self._levenshtein_distance(word, index_word)
                            if distance <= 2:  # Allow up to 2 character differences
                                for name in self.word_index[index_word]:
                                    if name not in [r["name"] for r in results]:
                                        # Score inversely proportional to the distance
                                        score = 40 - (distance * 10)
                                        scored_matches[name] = max(scored_matches.get(name, 0), score)

        # Priority 4: Quoted phrase exact matching
        for phrase in quoted_phrases:
            phrase_lower = phrase.lower()
            for name, option in self.options.items():
                if name not in [r["name"] for r in results]:
                    # Check name
                    if phrase_lower in name.lower():
                        scored_matches[name] = max(scored_matches.get(name, 0), 90)
                    # Check description
                    elif option.description and phrase_lower in option.description.lower():
                        scored_matches[name] = max(scored_matches.get(name, 0), 50)

        # Sort matches by score and add to results
        sorted_matches = sorted(scored_matches.items(), key=lambda x: x[1], reverse=True)
        for name, _ in sorted_matches:
            if name not in [r["name"] for r in results]:
                results.append(self._option_to_dict(self.options[name]))
                if len(results) >= limit:
                    break

        # If no results found, provide a helpful message
        if not results:
            logging.info(f"No results found for query: {query}")
            # You could return a special result indicating no matches were found
            # or implement additional fallback search strategies here

        return results[:limit]

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate the Levenshtein distance between two strings.

        This is a simple implementation for fuzzy matching.

        Args:
            s1: First string
            s2: Second string

        Returns:
            The edit distance between the strings
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if not s2:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Calculate insertions, deletions and substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row.copy()

        return previous_row[-1]

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
