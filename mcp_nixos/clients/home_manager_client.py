"""
Home Manager HTML parser and search engine.
"""

import logging
import os
import re
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, cast, Union

from bs4 import BeautifulSoup, Tag, PageElement

# Get logger
logger = logging.getLogger("mcp_nixos")

# Import caches and HTML client
from mcp_nixos.cache.simple_cache import SimpleCache
from mcp_nixos.clients.html_client import HTMLClient


class HomeManagerClient:
    """Client for fetching and searching Home Manager documentation."""

    def __init__(self):
        """Initialize the Home Manager client with caching."""
        self.hm_urls = {
            "options": "https://nix-community.github.io/home-manager/options.xhtml",
            "nixos-options": "https://nix-community.github.io/home-manager/nixos-options.xhtml",
            "nix-darwin-options": "https://nix-community.github.io/home-manager/nix-darwin-options.xhtml",
        }
        self.cache_ttl = int(os.environ.get("MCP_NIXOS_CACHE_TTL", 86400))
        self.cache = SimpleCache(max_size=100, ttl=self.cache_ttl)  # Memory cache
        self.html_client = HTMLClient(ttl=self.cache_ttl)  # Filesystem cache via HTMLClient

        # Data structures
        self.options: Dict[str, Dict[str, Any]] = {}
        self.options_by_category: Dict[str, List[str]] = defaultdict(list)
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)
        self.prefix_index: Dict[str, Set[str]] = defaultdict(set)
        self.hierarchical_index: Dict[Tuple[str, str], Set[str]] = defaultdict(set)

        self.data_version = "1.0.0"
        self.cache_key = f"home_manager_data_v{self.data_version}"

        # State flags
        self.is_loaded = False
        self.loading_error: Optional[str] = None
        self.loading_lock = threading.RLock()
        self.loading_thread: Optional[threading.Thread] = None
        self.loading_in_progress = False

        # Timing parameters - configurable for tests
        self.retry_delay = 1.0
        self.initial_load_delay = 0.1

        logger.info("Home Manager client initialized")

    def fetch_url(self, url: str, force_refresh: bool = False) -> str:
        """Fetch HTML content from a URL with filesystem caching."""
        logger.debug(f"Fetching URL: {url}")
        try:
            content, metadata = self.html_client.fetch(url, force_refresh=force_refresh)
            if content is None:
                error_msg = metadata.get("error", "Unknown error")
                raise Exception(f"Failed to fetch URL {url}: {error_msg}")
            logger.debug(f"Retrieved {url} {'from cache' if metadata.get('from_cache') else 'from web'}")
            return content
        except Exception as e:
            logger.error(f"Error in fetch_url for {url}: {str(e)}")
            raise

    # --- Refactored Parsing Logic ---

    def _extract_option_name(self, dt_element: Union[Tag, PageElement]) -> Optional[str]:
        """Extracts the option name from a <dt> element."""
        if not isinstance(dt_element, Tag):
            return None

        term_span = dt_element.find("span", class_="term")
        if term_span and isinstance(term_span, Tag):
            code = term_span.find("code")
            if code and isinstance(code, Tag) and hasattr(code, "text"):
                return code.text.strip()
        return None

    def _extract_metadata_from_paragraphs(self, p_elements: List[Union[Tag, PageElement]]) -> Dict[str, Optional[str]]:
        """Extracts metadata (Type, Default, Example, Versions) from <p> elements."""
        metadata: Dict[str, Optional[str]] = {
            "type": None,
            "default": None,
            "example": None,
            "introduced_version": None,
            "deprecated_version": None,
        }
        for p in p_elements:
            if not hasattr(p, "text"):
                continue
            text = p.text.strip()
            if "Type:" in text:
                metadata["type"] = text.split("Type:", 1)[1].strip()
            elif "Default:" in text:
                metadata["default"] = text.split("Default:", 1)[1].strip()
            elif "Example:" in text:
                metadata["example"] = text.split("Example:", 1)[1].strip()
            elif "Introduced in version:" in text or "Since:" in text:
                match = re.search(r"(Introduced in version|Since):\s*([\d.]+)", text)
                if match:
                    metadata["introduced_version"] = match.group(2)
            elif "Deprecated in version:" in text or "Deprecated since:" in text:
                match = re.search(r"(Deprecated in version|Deprecated since):\s*([\d.]+)", text)
                if match:
                    metadata["deprecated_version"] = match.group(2)
        return metadata

    def _find_manual_url(self, dd_element: Tag) -> Optional[str]:
        """Finds a potential manual URL within a <dd> element."""
        link = dd_element.find("a", href=True) if isinstance(dd_element, Tag) else None
        href = link.get("href", "") if link and isinstance(link, Tag) else ""
        if href and isinstance(href, str) and "manual" in href:
            return href
        return None

    def _find_category(self, dt_element: Tag) -> str:
        """Determines the category based on the preceding <h3> heading."""
        heading = dt_element.find_previous("h3")
        if heading and hasattr(heading, "text"):
            return heading.text.strip()
        return "Uncategorized"

    def _parse_single_option(self, dt_element: Union[Tag, PageElement], doc_type: str) -> Optional[Dict[str, Any]]:
        """Parses a single option from its <dt> and associated <dd> element."""
        dt_tag = cast(Tag, dt_element) if isinstance(dt_element, Tag) else None
        if not dt_tag:
            return None

        option_name = self._extract_option_name(dt_tag)
        if not option_name:
            return None

        dd = dt_tag.find_next_sibling("dd") if isinstance(dt_tag, Tag) else None
        if not dd or not isinstance(dd, Tag):
            return None

        p_elements = dd.find_all("p") if isinstance(dd, Tag) else []
        description = p_elements[0].text.strip() if p_elements and hasattr(p_elements[0], "text") else ""
        metadata = self._extract_metadata_from_paragraphs(list(p_elements[1:]))
        manual_url = self._find_manual_url(dd)
        category = self._find_category(dt_tag)

        return {
            "name": option_name,
            "type": metadata["type"],
            "description": description,
            "default": metadata["default"],
            "example": metadata["example"],
            "category": category,
            "source": doc_type,
            "introduced_version": metadata["introduced_version"],
            "deprecated_version": metadata["deprecated_version"],
            "manual_url": manual_url,
        }

    def parse_html(self, html: str, doc_type: str) -> List[Dict[str, Any]]:
        """Parse Home Manager HTML documentation (Refactored Main Loop)."""
        options = []
        try:
            logger.info(f"Parsing HTML content for {doc_type}")
            soup = BeautifulSoup(html, "html.parser")
            variablelist = soup.find(class_="variablelist")
            if not variablelist:
                return []
            dl = variablelist.find("dl")
            if not dl or not isinstance(dl, Tag):
                return []
            dt_elements = dl.find_all("dt", recursive=False)

            for dt in dt_elements:
                try:
                    option = self._parse_single_option(dt, doc_type)
                    if option:
                        options.append(option)
                except Exception as e:
                    option_name_guess = self._extract_option_name(dt) or "unknown"
                    logger.warning(f"Error parsing option '{option_name_guess}' in {doc_type}: {str(e)}")
                    continue  # Skip this option, proceed with others

            logger.info(f"Parsed {len(options)} options from {doc_type}")
            return options
        except Exception as e:
            logger.error(f"Critical error parsing HTML for {doc_type}: {str(e)}")
            return []  # Return empty list on major parsing failure

    # --- Indexing Logic (Largely Unchanged) ---

    def build_search_indices(self, options: List[Dict[str, Any]]) -> None:
        """Build in-memory search indices for fast option lookup."""
        try:
            logger.info("Building search indices for Home Manager options")
            # Reset indices
            self.options = {}
            self.options_by_category = defaultdict(list)
            self.inverted_index = defaultdict(set)
            self.prefix_index = defaultdict(set)
            self.hierarchical_index = defaultdict(set)

            for option in options:
                option_name = option["name"]
                self.options[option_name] = option
                category = option.get("category", "Uncategorized")
                self.options_by_category[category].append(option_name)

                # Build indices
                name_words = re.findall(r"\w+", option_name.lower())
                desc_words = re.findall(r"\w+", option.get("description", "").lower())
                for word in set(name_words + desc_words):
                    if len(word) > 2:
                        self.inverted_index[word].add(option_name)

                parts = option_name.split(".")
                for i in range(1, len(parts) + 1):
                    prefix = ".".join(parts[:i])
                    self.prefix_index[prefix].add(option_name)
                    if i < len(parts):  # Hierarchical index for parent/child
                        parent = ".".join(parts[:i])
                        child = parts[i]
                        # Use tuple key for hierarchical index
                        self.hierarchical_index[(parent, child)].add(option_name)

            logger.info(
                f"Built indices: {len(self.options)} options, {len(self.inverted_index)} words, "
                f"{len(self.prefix_index)} prefixes, {len(self.hierarchical_index)} hierarchical parts"
            )
        except Exception as e:
            logger.error(f"Error building search indices: {str(e)}")
            raise

    # --- Loading Logic (Unchanged) ---

    def load_all_options(self) -> List[Dict[str, Any]]:
        """Load options from all Home Manager HTML documentation sources."""
        all_options = []
        errors = []
        for doc_type, url in self.hm_urls.items():
            try:
                logger.info(f"Loading options from {doc_type}: {url}")
                html = self.fetch_url(url)
                options = self.parse_html(html, doc_type)
                all_options.extend(options)
            except Exception as e:
                error_msg = f"Error loading options from {doc_type} ({url}): {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        if not all_options and errors:
            raise Exception(f"Failed to load any Home Manager options: {'; '.join(errors)}")
        logger.info(f"Loaded {len(all_options)} options total")
        return all_options

    def ensure_loaded(self, force_refresh: bool = False) -> None:
        """Ensure that options are loaded and indices are built."""
        if self.is_loaded and not force_refresh:
            return
        if self.loading_error and not force_refresh:
            raise Exception(f"Previous loading attempt failed: {self.loading_error}")

        # Simplified check and wait for background loading
        if self.loading_in_progress and not force_refresh:
            logger.info("Waiting for background data loading...")
            if self.loading_thread:
                self.loading_thread.join(timeout=5.0)  # Wait up to 5 seconds
                if self.loading_in_progress:  # Still loading? Timeout.
                    raise Exception("Timed out waiting for background loading")
                if self.is_loaded:
                    return  # Success
                if self.loading_error:
                    raise Exception(f"Loading failed: {self.loading_error}")

        with self.loading_lock:
            # Double-check state after acquiring lock
            if self.is_loaded and not force_refresh:
                return
            if self.loading_error and not force_refresh:
                raise Exception(f"Loading failed: {self.loading_error}")
            if self.loading_in_progress and not force_refresh:  # Another thread started?
                logger.info("Loading already in progress by another thread.")
                # Allow the caller to retry or handle as needed. Here we just return.
                # Or wait again: self.loading_thread.join(...)
                return

            if force_refresh:
                logger.info("Forced refresh requested, invalidating cache")
                self.invalidate_cache()
                self.is_loaded = False
                self.loading_error = None

            self.loading_in_progress = True  # Mark as loading *before* starting work

        try:
            self._load_data_internal()
            with self.loading_lock:
                self.is_loaded = True
                self.loading_error = None  # Clear any previous error
                self.loading_in_progress = False
            logger.info("HomeManagerClient data successfully loaded/refreshed")
        except Exception as e:
            with self.loading_lock:
                self.loading_error = str(e)
                self.loading_in_progress = False
            logger.error(f"Failed to load/refresh Home Manager options: {str(e)}")
            raise

    def invalidate_cache(self) -> None:
        """Invalidate the disk cache for Home Manager data."""
        try:
            logger.info(f"Invalidating Home Manager data cache with key {self.cache_key}")
            if self.html_client and hasattr(self.html_client, "cache") and self.html_client.cache:
                self.html_client.cache.invalidate_data(self.cache_key)
                for url in self.hm_urls.values():
                    self.html_client.cache.invalidate(url)
                logger.info("Home Manager data cache invalidated")
            else:
                logger.warning("Cannot invalidate cache: HTML client cache not available")
        except Exception as e:
            logger.error(f"Failed to invalidate Home Manager data cache: {str(e)}")

    def force_refresh(self) -> bool:
        """Force a complete refresh of Home Manager data from the web."""
        try:
            logger.info("Forcing a complete refresh of Home Manager data")
            with self.loading_lock:
                self.is_loaded = False
                self.loading_error = None
            # Call ensure_loaded with force_refresh=True
            self.ensure_loaded(force_refresh=True)
            return self.is_loaded  # Return true if loading succeeded
        except Exception as e:
            logger.error(f"Failed to force refresh Home Manager data: {str(e)}")
            return False

    def load_in_background(self) -> None:
        """Start loading options in a background thread if not already loaded/loading."""
        with self.loading_lock:
            if self.is_loaded or self.loading_in_progress:
                logger.debug("Skipping background load: Already loaded or in progress.")
                return
            logger.info("Starting background thread for loading Home Manager options")
            self.loading_in_progress = True  # Set flag within lock
            self.loading_error = None  # Clear previous error
            self.loading_thread = threading.Thread(target=self._background_load_task, daemon=True)
            self.loading_thread.start()

    def _background_load_task(self):
        """Task executed by the background loading thread."""
        try:
            logger.info("Background thread started loading Home Manager options")
            self._load_data_internal()
            with self.loading_lock:
                self.is_loaded = True
                self.loading_error = None
                self.loading_in_progress = False
            logger.info("Background loading of Home Manager options completed successfully")
        except Exception as e:
            error_msg = str(e)
            with self.loading_lock:
                self.loading_error = error_msg
                self.is_loaded = False  # Ensure loaded is false on error
                self.loading_in_progress = False
            logger.error(f"Background loading of Home Manager options failed: {error_msg}")

    # --- Caching Logic (Refactored) ---

    def _validate_hm_cache_data(self, data: Optional[Dict], binary_data: Optional[Dict]) -> bool:
        """Validates loaded cache data for Home Manager."""
        if not data or not binary_data:
            return False
        if data.get("options_count", 0) == 0 or not data.get("options"):
            logger.warning("Cached HM data has zero options.")
            return False
        # Check if required indices exist in binary data
        if not all(
            k in binary_data for k in ["options_by_category", "inverted_index", "prefix_index", "hierarchical_index"]
        ):
            logger.warning("Cached HM binary data missing required indices.")
            return False
        return True

    def _load_from_cache(self) -> bool:
        """Attempt to load data from disk cache."""
        try:
            logger.info("Attempting to load Home Manager data from disk cache")

            if not self.html_client or not hasattr(self.html_client, "cache") or not self.html_client.cache:
                logger.warning("Cannot load from cache: HTML client cache not available")
                return False

            data_result = self.html_client.cache.get_data(self.cache_key)
            if not data_result or len(data_result) != 2:
                logger.warning("Invalid data returned from cache.get_data")
                return False

            data, data_meta = data_result

            binary_result = self.html_client.cache.get_binary_data(self.cache_key)
            if not binary_result or len(binary_result) != 2:
                logger.warning("Invalid data returned from cache.get_binary_data")
                return False

            binary_data, bin_meta = binary_result

            if not data_meta or not data_meta.get("cache_hit") or not bin_meta or not bin_meta.get("cache_hit"):
                logger.info(f"No complete HM cached data found for key {self.cache_key}")
                return False

            if not self._validate_hm_cache_data(data, binary_data):
                logger.warning("Invalid HM cache data found, ignoring.")
                self.invalidate_cache()  # Invalidate corrupt cache
                return False

            # Load data
            if not data or not isinstance(data, dict) or "options" not in data:
                logger.warning("Invalid options data structure in cache")
                return False

            self.options = data["options"]

            if not binary_data or not isinstance(binary_data, dict):
                logger.warning("Invalid binary data structure in cache")
                return False

            if "options_by_category" in binary_data:
                self.options_by_category = defaultdict(list, binary_data["options_by_category"])
            else:
                self.options_by_category = defaultdict(list)
                logger.warning("Missing options_by_category in cache")

            if "inverted_index" in binary_data:
                self.inverted_index = defaultdict(set, {k: set(v) for k, v in binary_data["inverted_index"].items()})
            else:
                self.inverted_index = defaultdict(set)
                logger.warning("Missing inverted_index in cache")

            if "prefix_index" in binary_data:
                self.prefix_index = defaultdict(set, {k: set(v) for k, v in binary_data["prefix_index"].items()})
            else:
                self.prefix_index = defaultdict(set)
                logger.warning("Missing prefix_index in cache")

            self.hierarchical_index = defaultdict(set)
            if "hierarchical_index" in binary_data and binary_data["hierarchical_index"]:
                for k_str, v in binary_data["hierarchical_index"].items():
                    try:
                        if not k_str:
                            continue
                        # Safer eval for tuple string like "('programs', 'git')"
                        key_tuple = eval(k_str, {"__builtins__": {}}, {})
                        if isinstance(key_tuple, tuple) and len(key_tuple) == 2:
                            self.hierarchical_index[key_tuple] = set(v) if v else set()
                        else:
                            logger.warning(f"Skipping invalid hierarchical key from cache: {k_str}")
                    except Exception as e:
                        logger.warning(f"Error evaluating hierarchical key '{k_str}': {e}")
            else:
                logger.warning("Missing hierarchical_index in cache")

            logger.info(f"Loaded {len(self.options)} Home Manager options from disk cache")
            return True
        except Exception as e:
            logger.error(f"Failed to load Home Manager data from disk cache: {str(e)}")
            self.invalidate_cache()  # Invalidate potentially corrupt cache
            return False

    def _save_in_memory_data(self) -> bool:
        """Save in-memory data structures to disk cache."""
        try:
            if not self.options:  # Don't save empty data
                logger.warning("Attempted to save empty HM options, skipping.")
                return False

            logger.info(f"Saving {len(self.options)} Home Manager options to disk cache")
            serializable_data = {
                "options_count": len(self.options),
                "options": self.options,  # Options are already dicts
                "timestamp": time.time(),
            }
            binary_data = {
                "options_by_category": dict(self.options_by_category),  # Convert defaultdict
                "inverted_index": {k: list(v) for k, v in self.inverted_index.items()},
                "prefix_index": {k: list(v) for k, v in self.prefix_index.items()},
                # Convert tuple keys to strings for JSON/Pickle compatibility
                "hierarchical_index": {str(k): list(v) for k, v in self.hierarchical_index.items()},
            }

            if not self.html_client or not hasattr(self.html_client, "cache") or not self.html_client.cache:
                logger.warning("Cannot save to cache: HTML client cache not available")
                return False

            self.html_client.cache.set_data(self.cache_key, serializable_data)
            self.html_client.cache.set_binary_data(self.cache_key, binary_data)
            logger.info(f"Successfully saved Home Manager data to disk cache with key {self.cache_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save Home Manager data to disk cache: {str(e)}")
            return False

    def _load_data_internal(self) -> None:
        """Internal method to load data, trying cache first, then web."""
        if self._load_from_cache():
            self.is_loaded = True
            logger.info("HM options loaded from disk cache.")
            return

        logger.info("Loading HM options from web")
        options = self.load_all_options()
        if not options:
            raise Exception("Failed to load any HM options from web sources.")
        self.build_search_indices(options)
        self._save_in_memory_data()  # Save newly loaded data
        self.is_loaded = True
        logger.info("HM options loaded from web and indices built.")

    # --- Search & Get Methods (Simplified loading checks) ---

    def _check_load_status(self, operation_name: str) -> Optional[Dict[str, Any]]:
        """Checks loading status and returns error dict if not ready."""
        if not self.is_loaded:
            if self.loading_in_progress:
                msg = "Home Manager data is still loading. Please try again shortly."
                logger.warning(f"Cannot {operation_name}: {msg}")
                return {"error": msg, "loading": True, "found": False}
            elif self.loading_error:
                msg = f"Failed to load Home Manager data: {self.loading_error}"
                logger.error(f"Cannot {operation_name}: {msg}")
                return {"error": msg, "loading": False, "found": False}
            else:
                # Should not happen if ensure_loaded is used, but handle defensively
                msg = "Home Manager data not loaded. Ensure loading process completes."
                logger.error(f"Cannot {operation_name}: {msg}")
                return {"error": msg, "loading": False, "found": False}
        return None  # No error, ready to proceed

    def search_options(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search Home Manager options using in-memory indices."""
        if status_error := self._check_load_status("search options"):
            return status_error
        logger.info(f"Searching Home Manager options for: '{query}'")
        query = query.strip().lower()
        if not query:
            return {"count": 0, "options": [], "error": "Empty query", "found": False}

        matches: Dict[str, int] = {}  # option_name -> score
        words = re.findall(r"\w+", query)

        # Exact match
        if query in self.options:
            matches[query] = 100
        # Prefix match
        if query in self.prefix_index:
            for name in self.prefix_index[query]:
                matches[name] = max(matches.get(name, 0), 80)
        # Hierarchical child match
        if query.endswith(".") and query[:-1] in self.prefix_index:
            parent_prefix = query[:-1]
            for name in self.prefix_index[parent_prefix]:
                if name.startswith(query):  # Matches children
                    matches[name] = max(matches.get(name, 0), 90)

        # Word match
        candidate_sets = []
        for word in words:
            if word in self.inverted_index:
                candidate_sets.append(self.inverted_index[word])
        # Find intersection if multiple words
        candidates = set.intersection(*candidate_sets) if candidate_sets else set()

        for name in candidates:
            score = 50  # Base score for word match
            if any(word in name.lower() for word in words):
                score += 10  # Boost if word in name
            matches[name] = max(matches.get(name, 0), score)

        # Sort matches: score desc, name asc
        sorted_matches = sorted(matches.items(), key=lambda item: (-item[1], item[0]))

        # Format results
        result_options = [
            {**self.options[name], "score": score} for name, score in sorted_matches[:limit]  # Add score to result
        ]

        return {"count": len(matches), "options": result_options, "found": len(result_options) > 0}

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific Home Manager option."""
        if status_error := self._check_load_status("get option"):
            return status_error
        logger.info(f"Getting Home Manager option: {option_name}")

        option = self.options.get(option_name)
        if option:
            result = option.copy()  # Return a copy
            result["found"] = True
            # Find related options if needed (simplified example)
            if "." in option_name:
                parent_path = ".".join(option_name.split(".")[:-1])
                related = [
                    {k: self.options[name].get(k) for k in ["name", "type", "description"]}
                    for name in self.prefix_index.get(parent_path, set())
                    if name != option_name and name.startswith(parent_path + ".")
                ][
                    :5
                ]  # Limit related
                if related:
                    result["related_options"] = related
            return result
        else:
            # Suggest similar options if not found
            suggestions = [name for name in self.prefix_index.get(option_name, set())]
            if not suggestions and "." in option_name:  # Try parent prefix
                parent = ".".join(option_name.split(".")[:-1])
                suggestions = [name for name in self.prefix_index.get(parent, set()) if name.startswith(parent + ".")]

            error_msg = "Option not found"
            response: Dict[str, Any] = {"name": option_name, "error": error_msg, "found": False}
            if suggestions:
                response["suggestions"] = sorted(suggestions)[:5]  # Limit suggestions
                response["error"] += f". Did you mean one of: {', '.join(response['suggestions'])}?"
            return response

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about Home Manager options."""
        if status_error := self._check_load_status("get stats"):
            return status_error
        logger.info("Getting Home Manager option statistics")

        options_by_source = defaultdict(int)
        options_by_type = defaultdict(int)
        for option in self.options.values():
            options_by_source[option.get("source", "unknown")] += 1
            options_by_type[option.get("type", "unknown")] += 1

        return {
            "total_options": len(self.options),
            "total_categories": len(self.options_by_category),
            "total_types": len(options_by_type),
            "by_source": dict(options_by_source),
            "by_category": {cat: len(opts) for cat, opts in self.options_by_category.items()},
            "by_type": dict(options_by_type),
            "index_stats": {
                "words": len(self.inverted_index),
                "prefixes": len(self.prefix_index),
                "hierarchical_parts": len(self.hierarchical_index),
            },
            "found": True,
        }

    def get_options_list(self) -> Dict[str, Any]:
        """Get a hierarchical list of top-level Home Manager options."""
        if status_error := self._check_load_status("get options list"):
            return status_error
        # Reuse get_stats and structure the output if needed, or use category index directly
        # This simplified version just uses the category index
        result = {"options": {}, "count": 0, "found": True}
        for category, names in self.options_by_category.items():
            result["options"][category] = {
                "count": len(names),
                "has_children": True,  # Assume categories have children for list view
            }
        result["count"] = len(self.options_by_category)
        return result

    def get_options_by_prefix(self, option_prefix: str) -> Dict[str, Any]:
        """Get all options under a specific option prefix."""
        if status_error := self._check_load_status("get options by prefix"):
            return status_error
        logger.info(f"Getting HM options by prefix: {option_prefix}")

        matching_names = self.prefix_index.get(option_prefix, set())
        # Also include options *starting* with the prefix + "." if it's not already a full path
        if not option_prefix.endswith("."):
            for name in self.options:
                if name.startswith(option_prefix + "."):
                    matching_names.add(name)

        options_data = [self.options[name] for name in sorted(matching_names)]
        if not options_data:
            return {"prefix": option_prefix, "error": f"No options found with prefix '{option_prefix}'", "found": False}

        type_counts = defaultdict(int)
        enable_options = []
        for opt in options_data:
            type_counts[opt.get("type", "unknown")] += 1
            name = opt["name"]
            if name.endswith(".enable") and opt.get("type") == "boolean":
                parts = name.split(".")
                if len(parts) >= 2:
                    enable_options.append(
                        {"name": name, "parent": parts[-2], "description": opt.get("description", "")}
                    )

        return {
            "prefix": option_prefix,
            "options": options_data,
            "count": len(options_data),
            "types": dict(type_counts),
            "enable_options": enable_options,
            "found": True,
        }
