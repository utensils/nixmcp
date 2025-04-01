"""Darwin client for fetching and parsing nix-darwin documentation."""

import dataclasses
import logging
import os
import pathlib
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from bs4 import BeautifulSoup, Tag
from bs4.element import PageElement

from mcp_nixos.cache.simple_cache import SimpleCache
from mcp_nixos.clients.html_client import HTMLClient

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

    BASE_URL = "https://nix-darwin.github.io/nix-darwin/manual"
    OPTION_REFERENCE_URL = f"{BASE_URL}/index.html"

    def __init__(self, html_client: Optional[HTMLClient] = None, cache_ttl: int = 86400):
        """Initialize the DarwinClient."""
        self.cache_ttl = int(os.environ.get("MCP_NIXOS_CACHE_TTL", cache_ttl))
        self.html_client = html_client or HTMLClient(ttl=self.cache_ttl)
        self.html_cache = self.html_client.cache  # Reuse HTMLClient's cache
        self.memory_cache = SimpleCache(max_size=1000, ttl=self.cache_ttl)

        self.options: Dict[str, DarwinOption] = {}
        self.name_index: Dict[str, List[str]] = defaultdict(list)
        self.word_index: Dict[str, Set[str]] = defaultdict(set)
        self.prefix_index: Dict[str, List[str]] = defaultdict(list)

        self.total_options = 0
        self.total_categories = 0
        self.last_updated: Optional[datetime] = None
        self.loading_status = "not_started"
        self.error_message = ""
        self.data_version = "1.1.0"  # Bumped due to structure changes
        self.cache_key = f"darwin_data_v{self.data_version}"

    async def fetch_url(self, url: str, force_refresh: bool = False) -> str:
        """Fetch URL content from the HTML client."""
        try:
            content, metadata = self.html_client.fetch(url, force_refresh=force_refresh)
            if content is None:
                error = metadata.get("error", "Unknown error")
                raise ValueError(f"Failed to fetch URL {url}: {error}")

            logger.debug(f"Retrieved {url} {'from cache' if metadata.get('from_cache') else 'from web'}")
            return content
        except Exception as e:
            logger.error(f"Error in fetch_url for {url}: {str(e)}")
            raise

    async def load_options(self, force_refresh: bool = False) -> Dict[str, DarwinOption]:
        """Load nix-darwin options from documentation."""
        try:
            self.loading_status = "loading"
            if force_refresh:
                logger.info("Forced refresh requested, invalidating caches")
                self.invalidate_cache()

            if not force_refresh and await self._load_from_memory_cache():
                self.loading_status = "loaded"
                return self.options

            html = await self.fetch_url(self.OPTION_REFERENCE_URL, force_refresh=force_refresh)
            if not html:
                raise ValueError(f"Failed to fetch options from {self.OPTION_REFERENCE_URL}")

            soup = BeautifulSoup(html, "html.parser")
            await self._parse_options(soup)
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
            if self.cache_key in self.memory_cache.cache:
                del self.memory_cache.cache[self.cache_key]

            if self.html_client and self.html_client.cache:
                self.html_client.cache.invalidate_data(self.cache_key)
                self.html_client.cache.invalidate(self.OPTION_REFERENCE_URL)

            # Legacy cache cleanup (unchanged, but included for completeness)
            legacy_bad_path = pathlib.Path("darwin")
            if legacy_bad_path.exists() and legacy_bad_path.is_dir():
                logger.warning("Found legacy 'darwin' directory in current path - attempting cleanup")
                try:
                    safe_to_remove = all(
                        item.name.endswith((".html", ".data.json", ".data.pickle"))
                        for item in legacy_bad_path.iterdir()
                    )
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

    # --- Refactored Parsing Logic ---

    def _extract_option_id_from_link(self, link: Tag) -> Optional[str]:
        """Extracts the option ID (e.g., 'opt-system.foo') from a link Tag."""
        option_id = None
        id_attr = link.get("id")
        if id_attr and isinstance(id_attr, str) and id_attr.startswith("opt-"):
            option_id = id_attr
        else:
            href_attr = link.get("href")
            if href_attr and isinstance(href_attr, str) and href_attr.startswith("#opt-"):
                option_id = href_attr.lstrip("#")

        if option_id and isinstance(option_id, str) and option_id.startswith("opt-"):
            return option_id
        return None

    def _find_option_description_element(self, link: Tag) -> Optional[Tag]:
        """Finds the <dd> element containing the description for an option link."""
        dt_parent = link.find_parent("dt")
        if not dt_parent or not isinstance(dt_parent, Tag):
            return None
        dd = dt_parent.find_next_sibling("dd")
        return dd if isinstance(dd, Tag) else None

    async def _parse_options(self, soup: BeautifulSoup) -> None:
        """
        Parse nix-darwin options from BeautifulSoup object with enhanced fallbacks.

        This method has been enhanced to handle different HTML structures with multiple
        fallback strategies, similar to the Home Manager fixes.
        """
        self.options = {}
        self.name_index = defaultdict(list)
        self.word_index = defaultdict(set)
        self.prefix_index = defaultdict(list)

        option_links: Sequence[PageElement] = []

        # Multiple strategies for finding option links
        strategies = [
            # Strategy 1: Direct ID attribute search
            lambda s: s.find_all("a", attrs={"id": lambda x: isinstance(x, str) and x.startswith("opt-")}),
            # Strategy 2: Href attribute search
            lambda s: s.find_all("a", attrs={"href": lambda x: isinstance(x, str) and x.startswith("#opt-")}),
            # Strategy 3: Code tags within DT tags (some sites use this structure)
            lambda s: [dt.find("code") for dt in s.find_all("dt") if dt.find("code")],
        ]

        # Try each strategy until we find some options
        for strategy_index, strategy_fn in enumerate(strategies):
            if isinstance(soup, (BeautifulSoup, Tag)):
                option_links = strategy_fn(soup)
                if option_links and len(option_links) > 0:
                    logger.info(f"Found {len(option_links)} option links using strategy {strategy_index+1}")
                    break

        # If we still don't have links, try a more aggressive approach
        if not option_links:
            logger.warning("No option links found with standard strategies, trying fallback approach")
            # Look for any code tag that might contain option names
            code_tags = soup.find_all("code")
            option_links = [code for code in code_tags if code.get_text() and "." in code.get_text()]
            if option_links:
                logger.info(f"Found {len(option_links)} potential options with fallback strategy")

        if not option_links:
            logger.error("Failed to find any option links in the HTML structure")
            return

        logger.info(f"Found {len(option_links)} potential option links")
        total_processed = 0

        for link in option_links:
            if not isinstance(link, Tag):
                continue

            try:
                # Try multiple methods to extract option name
                option_name = None

                # Method 1: Extract from ID
                option_id = self._extract_option_id_from_link(link)
                if option_id:
                    option_name = option_id[4:]  # Remove 'opt-'

                # Method 2: Use code tag text directly
                if not option_name and link.name == "code":
                    option_name = link.get_text().strip()

                # Method 3: Look for nested code tag
                code_tag = link.find("code")
                if not option_name and code_tag and isinstance(code_tag, Tag):
                    option_name = code_tag.get_text().strip()

                if not option_name:
                    continue

                # Try multiple methods to find description
                dd = None

                # Method 1: Standard dt/dd structure
                dd = self._find_option_description_element(link)

                # Method 2: Look for next sibling paragraph
                if not dd and link.parent:
                    for sibling in link.parent.next_siblings:
                        if isinstance(sibling, Tag) and (sibling.name == "dd" or sibling.name == "p"):
                            dd = sibling
                            break

                # Method 3: Use parent's next sibling if link is inside a dt/h3/etc
                if not dd and link.parent and link.parent.next_sibling:
                    next_elem = link.parent.next_sibling
                    while next_elem and (not isinstance(next_elem, Tag) or not next_elem.get_text().strip()):
                        next_elem = next_elem.next_sibling
                    if next_elem and isinstance(next_elem, Tag):
                        dd = next_elem

                if not dd:
                    logger.debug(f"No description found for option {option_name}")
                    continue

                option = self._parse_option_details(option_name, dd)
                if option:
                    self.options[option_name] = option
                    self._index_option(option_name, option)
                    total_processed += 1
                    if total_processed % 250 == 0:
                        logger.info(f"Processed {total_processed} options...")
            except Exception as e:
                # Log and continue - don't let one bad option break the entire parse
                logger.warning(f"Failed to parse option details: {e}")

        self.total_options = len(self.options)
        self.total_categories = len(self._get_top_level_categories())
        logger.info(f"Parsed {self.total_options} options in {self.total_categories} categories")

    # --- Metadata Extraction Helpers ---

    def _extract_text_chunk(self, full_text: str, start_marker: str, end_markers: List[str]) -> str:
        """Extracts text between a start marker and the next marker."""
        start_pos = full_text.find(start_marker)
        if start_pos == -1:
            return ""
        start_pos += len(start_marker)

        end_pos = len(full_text)
        for marker in end_markers:
            pos = full_text.find(marker, start_pos)
            if pos != -1:
                end_pos = min(end_pos, pos)

        return full_text[start_pos:end_pos].strip()

    def _extract_metadata_from_text(self, text_content: str) -> Dict[str, str]:
        """Extracts metadata (Type, Default, Example, Declared by) from raw text."""
        metadata = {}
        markers = ["*Type:*", "*Default:*", "*Example:*", "*Declared by:*"]
        metadata["type"] = self._extract_text_chunk(text_content, "*Type:*", markers)
        metadata["default"] = self._extract_text_chunk(text_content, "*Default:*", markers)
        metadata["example"] = self._extract_text_chunk(text_content, "*Example:*", markers)
        metadata["declared_by"] = self._extract_text_chunk(text_content, "*Declared by:*", markers)
        return metadata

    def _extract_description_from_text(self, full_text: str) -> str:
        """Extracts the main description text before metadata markers."""
        markers = ["*Type:*", "*Default:*", "*Example:*", "*Declared by:*"]
        first_marker_pos = len(full_text)
        for marker in markers:
            pos = full_text.find(marker)
            if pos != -1:
                first_marker_pos = min(first_marker_pos, pos)
        return full_text[:first_marker_pos].strip()

    def _extract_metadata_from_dd_elements(self, dd: Tag) -> Dict[str, str]:
        """Extracts metadata by checking specific HTML elements within the <dd> tag."""
        metadata = {"type": "", "default": "", "example": "", "declared_by": ""}

        # Check itemized lists first
        for div in dd.find_all("div", class_="itemizedlist"):
            item_text = div.get_text(strip=True) if hasattr(div, "get_text") else ""
            if isinstance(item_text, str):
                if "Type:" in item_text and not metadata["type"]:
                    metadata["type"] = item_text.split("Type:", 1)[1].strip()
                elif "Default:" in item_text and not metadata["default"]:
                    metadata["default"] = item_text.split("Default:", 1)[1].strip()
                elif "Example:" in item_text and not metadata["example"]:
                    metadata["example"] = item_text.split("Example:", 1)[1].strip()
                elif "Declared by:" in item_text and not metadata["declared_by"]:
                    metadata["declared_by"] = item_text.split("Declared by:", 1)[1].strip()

        # Check code tags for declared_by if still missing
        if not metadata["declared_by"]:
            for code in dd.find_all("code"):
                code_text = code.get_text() if hasattr(code, "get_text") else ""
                if isinstance(code_text, str) and ("nix" in code_text or "darwin" in code_text):
                    metadata["declared_by"] = code_text.strip()
                    break
        return metadata

    # --- Refactored Detail Parsing ---

    def _parse_option_details(self, name: str, dd: Tag) -> Optional[DarwinOption]:
        """
        Parse option details from a description tag with enhanced resilience.

        This method has been updated to handle different formats of metadata
        with multiple extraction strategies and fallbacks.
        """
        try:
            description = ""
            full_text = dd.get_text(separator=" ", strip=True) if hasattr(dd, "get_text") else ""
            if not full_text:
                logger.warning(f"Empty text found for option {name}")
                # Create a minimal valid option with just the name
                return DarwinOption(name=name, description=f"Option: {name}")

            # Extract from text first
            description = self._extract_description_from_text(full_text)
            metadata_text = self._extract_metadata_from_text(full_text)

            # Fallback/Supplement using element search
            metadata_elem = self._extract_metadata_from_dd_elements(dd)

            # Try regex-based extraction if standard methods fail
            metadata_regex = {}
            if not any([metadata_text.get("type"), metadata_elem.get("type")]):
                # Try to find type with regex
                type_match = re.search(r"type:?\s*(\w+)", full_text, re.IGNORECASE)
                if type_match:
                    metadata_regex["type"] = type_match.group(1)

            if not any([metadata_text.get("default"), metadata_elem.get("default")]):
                # Try to find default with regex
                default_match = re.search(r"default:?\s*([^*]+)", full_text, re.IGNORECASE)
                if default_match:
                    metadata_regex["default"] = default_match.group(1).strip()

            if not any([metadata_text.get("example"), metadata_elem.get("example")]):
                # Try to find example with regex
                example_match = re.search(r"example:?\s*([^*]+)", full_text, re.IGNORECASE)
                if example_match:
                    metadata_regex["example"] = example_match.group(1).strip()

            if not any([metadata_text.get("declared_by"), metadata_elem.get("declared_by")]):
                # Try to find declared_by with regex
                declared_match = re.search(r"declared by:?\s*([^*]+)", full_text, re.IGNORECASE)
                if declared_match:
                    metadata_regex["declared_by"] = declared_match.group(1).strip()

            # Combine results from all strategies, preferring in order:
            # 1. Text extraction (most accurate)
            # 2. Element-based extraction
            # 3. Regex-based extraction (most fallback)
            option_type = metadata_text.get("type") or metadata_elem.get("type") or metadata_regex.get("type", "")
            default_value = (
                metadata_text.get("default") or metadata_elem.get("default") or metadata_regex.get("default", "")
            )
            example = metadata_text.get("example") or metadata_elem.get("example") or metadata_regex.get("example", "")
            declared_by = (
                metadata_text.get("declared_by")
                or metadata_elem.get("declared_by")
                or metadata_regex.get("declared_by", "")
            )

            # Use extracted description if available, otherwise fallback to raw text
            if not description and full_text:
                # As a last resort, try to extract description from the beginning of text
                # up to any of the known metadata markers
                first_metadata = full_text.lower().find("type:")
                if first_metadata == -1:
                    first_metadata = full_text.lower().find("default:")
                if first_metadata == -1:
                    first_metadata = full_text.lower().find("example:")
                if first_metadata == -1:
                    first_metadata = full_text.lower().find("declared by:")

                if first_metadata > 10:  # Only use if we found a marker and have enough text
                    description = full_text[:first_metadata].strip()
                else:
                    description = full_text  # Complete fallback

            # Clean up description if needed
            if description:
                # Remove any trailing metadata keywords
                for keyword in ["Type:", "Default:", "Example:", "Declared by:"]:
                    if description.endswith(keyword):
                        description = description[: -len(keyword)].strip()

            # Create and return the option object
            return DarwinOption(
                name=name,
                description=description,
                type=option_type,
                default=default_value,
                example=example,
                declared_by=declared_by,
            )
        except Exception as e:
            logger.error(f"Error parsing option details for {name}: {e}")
            # Create a minimal valid option with just the name as a fallback
            return DarwinOption(name=name, description=f"Error processing {name}: {str(e)}")

    def _index_option(self, option_name: str, option: DarwinOption) -> None:
        """Index an option for searching."""
        name_parts = option_name.split(".")
        for i in range(len(name_parts)):
            prefix = ".".join(name_parts[: i + 1])
            self.name_index[prefix].append(option_name)
            if i < len(name_parts) - 1:
                self.prefix_index[prefix].append(option_name)

        name_words = re.findall(r"\w+", option_name.lower())
        desc_words = re.findall(r"\w+", option.description.lower())
        for word in set(name_words + desc_words):
            if len(word) > 2:
                self.word_index[word].add(option.name)

    def _get_top_level_categories(self) -> List[str]:
        """Get top-level option categories."""
        categories = {name.split(".")[0] for name in self.options.keys() if "." in name}
        return sorted(list(categories))

    # --- Caching Logic (Refactored for clarity) ---

    async def _load_from_memory_cache(self) -> bool:
        """Attempt to load options from memory cache or delegate to filesystem cache."""
        try:
            cached_data = self.memory_cache.get(self.cache_key)
            if cached_data:
                logger.info("Found darwin options in memory cache")
                self._load_data_into_memory(cached_data)
                return bool(self.options)
            return await self._load_from_filesystem_cache()
        except Exception as e:
            logger.error(f"Error loading from memory cache: {e}")
            return False

    def _load_data_into_memory(self, cached_data: Dict[str, Any]):
        """Loads data from a cache dictionary into the client's attributes."""
        self.options = cached_data.get("options", {})
        self.name_index = cached_data.get("name_index", defaultdict(list))
        self.word_index = cached_data.get("word_index", defaultdict(set))
        self.prefix_index = cached_data.get("prefix_index", defaultdict(list))
        self.total_options = cached_data.get("total_options", 0)
        self.total_categories = cached_data.get("total_categories", 0)
        self.last_updated = cached_data.get("last_updated")

    def _validate_cached_data(self, data: Dict[str, Any], binary_data: Dict[str, Any]) -> bool:
        """Validates the integrity of cached data before loading."""
        if not data or not data.get("options") or len(data["options"]) < 10:
            logger.warning("Cached data has too few options - ignoring cache")
            return False
        if data.get("total_options", 0) < 10:
            logger.warning("Cached data has suspiciously low total_options - ignoring cache")
            return False
        if not binary_data or not all(k in binary_data for k in ["name_index", "word_index", "prefix_index"]):
            logger.warning("Cached binary data missing indices - ignoring cache")
            return False
        if not binary_data["name_index"] or not binary_data["word_index"] or not binary_data["prefix_index"]:
            logger.warning("Cached binary data has empty indices - ignoring cache")
            return False
        return True

    async def _load_from_filesystem_cache(self) -> bool:
        """Attempt to load data from disk cache."""
        try:
            logger.info("Attempting to load nix-darwin data from disk cache")
            if not self.html_client or not self.html_client.cache:
                logger.warning("HTML client or cache not available for filesystem load")
                return False

            data, metadata = self.html_client.cache.get_data(self.cache_key)
            binary_data, binary_metadata = self.html_client.cache.get_binary_data(self.cache_key)

            if not metadata.get("cache_hit") or not binary_metadata.get("cache_hit"):
                logger.info(f"No complete cached data found for key {self.cache_key}")
                return False

            # Ensure data is not None before validation
            if data is None or binary_data is None:
                logger.warning("Cached data or binary_data is None - ignoring cache")
                return False

            if not self._validate_cached_data(data, binary_data):
                return False

            # Load basic options data (convert dicts back to DarwinOption)
            self.options = {name: DarwinOption(**option_dict) for name, option_dict in data.get("options", {}).items()}
            self.total_options = data.get("total_options", len(self.options))
            self.total_categories = data.get("total_categories", 0)
            if "last_updated" in data and data["last_updated"]:
                self.last_updated = datetime.fromisoformat(data["last_updated"])

            # Load complex data structures from binary data
            self.name_index = binary_data["name_index"]
            self.word_index = defaultdict(set, {k: set(v) for k, v in binary_data["word_index"].items()})
            self.prefix_index = binary_data["prefix_index"]

            # Final validation check
            if len(self.options) != self.total_options:
                logger.warning(f"Option count mismatch ({len(self.options)} vs {self.total_options}), correcting.")
                self.total_options = len(self.options)

            await self._cache_to_memory()  # Cache in memory after successful load
            logger.info(f"Successfully loaded nix-darwin data from disk cache ({len(self.options)} options)")
            return True
        except Exception as e:
            logger.error(f"Failed to load nix-darwin data from disk cache: {str(e)}")
            # Invalidate potentially corrupt cache on load failure
            self.invalidate_cache()
            return False

    async def _cache_parsed_data(self) -> None:
        """Cache parsed data to memory cache and filesystem."""
        try:
            await self._cache_to_memory()
            await self._save_to_filesystem_cache()
        except Exception as e:
            logger.error(f"Error caching parsed data: {e}")

    def _prepare_memory_cache_data(self) -> Dict[str, Any]:
        """Prepares the data structure for memory caching."""
        return {
            "options": self.options,
            "name_index": dict(self.name_index),
            # Convert sets to lists for SimpleCache compatibility if needed
            "word_index": {k: list(v) for k, v in self.word_index.items()},
            "prefix_index": dict(self.prefix_index),
            "total_options": self.total_options,
            "total_categories": self.total_categories,
            "last_updated": self.last_updated or datetime.now(),
        }

    async def _cache_to_memory(self) -> None:
        """Cache parsed data to memory cache."""
        try:
            if not self.options:  # Don't cache if loading failed
                return
            cache_data = self._prepare_memory_cache_data()
            self.memory_cache.set(self.cache_key, cache_data)  # SimpleCache.set is sync
        except Exception as e:
            logger.error(f"Error caching data to memory: {e}")

    def _prepare_filesystem_cache_data(self) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Prepares data structures for JSON and binary filesystem caching."""
        if not self.options or self.total_options < 10:
            logger.warning(f"Refusing to cache dataset with only {self.total_options} options.")
            return None, None

        serializable_options = {name: self._option_to_dict(option) for name, option in self.options.items()}
        json_data = {
            "options": serializable_options,
            "total_options": self.total_options,
            "total_categories": self.total_categories,
            "last_updated": self.last_updated.isoformat() if self.last_updated else datetime.now().isoformat(),
            "timestamp": time.time(),
        }

        binary_data = {
            "name_index": dict(self.name_index),
            "word_index": {k: list(v) for k, v in self.word_index.items()},  # Convert sets to lists
            "prefix_index": dict(self.prefix_index),
        }

        # Validate indices before returning
        if not binary_data["name_index"] or not binary_data["word_index"] or not binary_data["prefix_index"]:
            logger.error("Index data is empty, refusing to cache.")
            return None, None

        return json_data, binary_data

    async def _save_to_filesystem_cache(self) -> bool:
        """Save in-memory data structures to disk cache."""
        try:
            if not self.html_client or not self.html_client.cache:
                logger.warning("HTML client or cache not available for saving")
                return False

            json_data, binary_data = self._prepare_filesystem_cache_data()
            if json_data is None or binary_data is None:
                return False  # Validation failed or data was empty

            logger.info(f"Saving nix-darwin data structures to disk cache ({len(self.options)} options)")
            self.html_client.cache.set_data(self.cache_key, json_data)
            self.html_client.cache.set_binary_data(self.cache_key, binary_data)
            logger.info(f"Successfully saved nix-darwin data to disk cache with key {self.cache_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save nix-darwin data to disk cache: {str(e)}")
            return False

    # --- Refactored Search Logic ---

    def _find_exact_matches(self, query: str) -> List[str]:
        """Finds options with exact name match."""
        return [query] if query in self.options else []

    def _find_prefix_matches(self, query: str, query_words: List[str]) -> Dict[str, int]:
        """Finds options matching prefixes (hierarchical or simple)."""
        matches = {}
        # Hierarchical path matching
        path_components = query.split(".")
        if len(path_components) > 1:
            for name in self.options:
                name_components = name.split(".")
                if len(name_components) >= len(path_components) and all(
                    nc.startswith(pc) for nc, pc in zip(name_components, path_components)
                ):
                    score = 100 - (len(name) - len(query))  # Higher score for shorter matches
                    matches[name] = max(matches.get(name, 0), score)

        # Regular prefix matching based on words
        for word in query_words:
            for name in self.name_index.get(word, []):
                name_lower = name.lower()
                position = name_lower.find(word)
                if position != -1:
                    score = 80
                    if position == 0 or name_lower[position - 1] in ".-_":
                        score += 10  # Boost beginning/separated matches
                    score -= int(position * 0.5)  # Penalize later matches
                    matches[name] = max(matches.get(name, 0), score)
        return matches

    def _find_word_matches(self, query_words: List[str]) -> Dict[str, int]:
        """Finds options matching words in name or description."""
        matches = {}
        for word in query_words:
            if word in self.word_index:
                for name in self.word_index[word]:
                    score = 60  # Base score for word match
                    name_lower = name.lower()
                    word_count = name_lower.count(word)
                    if word_count > 1:
                        score += 5 * (word_count - 1)  # Boost multiple occurrences in name
                    matches[name] = max(matches.get(name, 0), score)
        return matches

    def _find_fuzzy_matches(self, query_words: List[str]) -> Dict[str, int]:
        """Finds options using fuzzy matching on words."""
        matches = {}
        if not hasattr(self, "_levenshtein_distance"):  # Simple check if method exists
            return matches  # Skip fuzzy if distance function is missing

        for word in query_words:
            if len(word) <= 4:
                continue  # Only fuzzy match longer words

            for index_word in self.word_index:
                if abs(len(index_word) - len(word)) <= 1:  # Similar length
                    distance = self._levenshtein_distance(word, index_word)
                    if distance <= 2:  # Allow up to 2 edits
                        score = 40 - (distance * 10)  # Score inversely to distance
                        for name in self.word_index[index_word]:
                            matches[name] = max(matches.get(name, 0), score)
        return matches

    def _find_quoted_phrase_matches(self, quoted_phrases: List[str]) -> Dict[str, int]:
        """Finds options matching exact quoted phrases."""
        matches = {}
        for phrase in quoted_phrases:
            phrase_lower = phrase.lower()
            for name, option in self.options.items():
                score = 0
                if phrase_lower in name.lower():
                    score = 90  # High score for name match
                elif option.description and phrase_lower in option.description.lower():
                    score = 50  # Lower score for description match
                if score > 0:
                    matches[name] = max(matches.get(name, 0), score)
        return matches

    def _merge_and_score_results(
        self, all_matches: List[Dict[str, int]], limit: int, initial_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merges results from different strategies, scores, sorts, and limits."""
        scored_matches: Dict[str, int] = {}
        existing_names = {r["name"] for r in initial_results}

        # Merge scores, taking the highest score for each option
        for strategy_matches in all_matches:
            for name, score in strategy_matches.items():
                if name not in existing_names:
                    scored_matches[name] = max(scored_matches.get(name, 0), score)

        # Sort by score (desc) then name (asc)
        sorted_matches = sorted(scored_matches.items(), key=lambda x: (-x[1], x[0]))

        # Add sorted matches to initial results up to the limit
        final_results = initial_results
        for name, _ in sorted_matches:
            if len(final_results) >= limit:
                break
            # Check again for duplicates just in case initial_results had some
            if name not in {r["name"] for r in final_results}:
                option_data = self._option_to_dict(self.options[name])
                # Add score for debugging/ranking?
                # option_data['search_score'] = scored_matches[name]
                final_results.append(option_data)

        return final_results[:limit]

    async def search_options(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for options by query (Refactored Orchestration)."""
        if not self.options:
            await self.load_options()  # Ensure options are loaded
            if not self.options:  # If still not loaded, raise error
                raise ValueError("Options not loaded. Call load_options() successfully first.")

        results: List[Dict[str, Any]] = []
        query = query.strip()
        if not query:  # Handle empty query
            sample_names = list(self.options.keys())[: min(limit, len(self.options))]
            return [self._option_to_dict(self.options[name]) for name in sample_names]

        # --- Strategy 1: Exact Match ---
        exact_matches_names = self._find_exact_matches(query)
        results.extend([self._option_to_dict(self.options[name]) for name in exact_matches_names])

        # --- Prepare for other strategies ---
        quoted_phrases = re.findall(r'"([^"]+)"', query)
        clean_query = re.sub(r'"[^"]+"', "", query).strip()
        query_words = [w.lower() for w in re.findall(r"\w+", clean_query) if len(w) > 2]
        if len(query) < 50 and " " not in query and query not in query_words:
            query_words.append(query.lower())  # Add original simple query term

        # --- Collect results from other strategies ---
        all_strategy_matches = []
        if len(results) < limit:
            prefix_matches = self._find_prefix_matches(query, query.split("."))
            all_strategy_matches.append(prefix_matches)
        if len(results) < limit:
            word_matches = self._find_word_matches(query_words)
            all_strategy_matches.append(word_matches)
        if len(results) < limit:
            fuzzy_matches = self._find_fuzzy_matches(query_words)
            all_strategy_matches.append(fuzzy_matches)
        if len(results) < limit and quoted_phrases:
            quoted_matches = self._find_quoted_phrase_matches(quoted_phrases)
            all_strategy_matches.append(quoted_matches)

        # --- Merge, Score, Sort, and Limit ---
        final_results = self._merge_and_score_results(all_strategy_matches, limit, results)

        if not final_results:
            logging.info(f"No results found for query: {query}")

        return final_results

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate the Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        if not s2:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row[:]  # Use copy
        return previous_row[-1]

    # --- Other Methods (Unchanged unless necessary) ---

    async def get_option(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an option by name."""
        if not self.options:
            await self.load_options()
            if not self.options:
                raise ValueError("Options not loaded.")

        option = self.options.get(name)
        return self._option_to_dict(option) if option else None

    async def get_options_by_prefix(self, prefix: str) -> List[Dict[str, Any]]:
        """Get options by prefix."""
        if not self.options:
            await self.load_options()
            if not self.options:
                raise ValueError("Options not loaded.")

        # Use the more specific prefix_index now
        options = []
        for name in sorted(self.prefix_index.get(prefix, [])):
            if name in self.options:  # Ensure option exists
                options.append(self._option_to_dict(self.options[name]))
        return options

    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get top-level option categories."""
        if not self.options:
            await self.load_options()
            if not self.options:
                raise ValueError("Options not loaded.")

        categories = []
        for category in self._get_top_level_categories():
            count = len(self.prefix_index.get(category, []))  # Approximate count using prefix index
            categories.append({"name": category, "option_count": count, "path": category})
        return categories

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the loaded options."""
        if not self.options:
            await self.load_options()
            if not self.options:
                raise ValueError("Options not loaded.")

        return {
            "total_options": self.total_options,
            "total_categories": self.total_categories,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "loading_status": self.loading_status,
            "categories": await self.get_categories(),  # Reuse get_categories
        }

    def _option_to_dict(self, option: DarwinOption) -> Dict[str, Any]:
        """Convert an option to a dictionary."""
        # Use dataclasses.asdict for potentially simpler conversion if appropriate
        # return dataclasses.asdict(option)
        # Manual conversion for fine control:
        return {
            "name": option.name,
            "description": option.description,
            "type": option.type,
            "default": option.default,
            "example": option.example,
            "declared_by": option.declared_by,
            # Recursively convert sub_options if needed, ensure no infinite loops
            "sub_options": (
                [self._option_to_dict(sub) for sub in option.sub_options.values()] if option.sub_options else []
            ),
            "parent": option.parent,
        }
