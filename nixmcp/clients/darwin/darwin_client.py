"""Darwin client for fetching and parsing nix-darwin documentation."""

import dataclasses
import logging
import re
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
        self.html_client = html_client or HTMLClient(ttl=cache_ttl)
        self.html_cache = HTMLCache("darwin", ttl=cache_ttl)
        self.memory_cache = SimpleCache(max_size=1000, ttl=cache_ttl)

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

            # Try to load from memory cache first
            if not force_refresh and await self._load_from_memory_cache():
                self.loading_status = "loaded"
                return self.options

            # If memory cache fails, parse the HTML
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
            # SimpleCache.get is not async - don't use await
            cached_data = self.memory_cache.get("options_data")
            if not cached_data:
                return False

            self.options = cached_data.get("options", {})
            self.name_index = cached_data.get("name_index", defaultdict(list))
            self.word_index = cached_data.get("word_index", defaultdict(set))
            self.prefix_index = cached_data.get("prefix_index", defaultdict(list))
            self.total_options = cached_data.get("total_options", 0)
            self.total_categories = cached_data.get("total_categories", 0)

            if "last_updated" in cached_data:
                self.last_updated = cached_data["last_updated"]

            return bool(self.options)
        except Exception as e:
            logger.error(f"Error loading from memory cache: {e}")
            return False

    async def _cache_parsed_data(self) -> None:
        """Cache parsed data to memory cache."""
        try:
            cache_data = {
                "options": self.options,
                "name_index": dict(self.name_index),
                "word_index": {k: list(v) for k, v in self.word_index.items()},
                "prefix_index": dict(self.prefix_index),
                "total_options": self.total_options,
                "total_categories": self.total_categories,
                "last_updated": datetime.now(),
            }
            # SimpleCache.set is not async - don't use await
            self.memory_cache.set("options_data", cache_data)
        except Exception as e:
            logger.error(f"Error caching parsed data: {e}")

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
