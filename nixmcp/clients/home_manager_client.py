"""
Home Manager HTML parser and search engine.
"""

import re
import os
import time
import logging
import threading
from typing import Dict, List, Any
from collections import defaultdict
from bs4 import BeautifulSoup

# Get logger
logger = logging.getLogger("nixmcp")

# Import caches
from nixmcp.cache.simple_cache import SimpleCache
from nixmcp.clients.html_client import HTMLClient


class HomeManagerClient:
    """Client for fetching and searching Home Manager documentation."""

    def __init__(self):
        """Initialize the Home Manager client with caching."""
        # URLs for Home Manager HTML documentation
        self.hm_urls = {
            "options": "https://nix-community.github.io/home-manager/options.xhtml",
            "nixos-options": "https://nix-community.github.io/home-manager/nixos-options.xhtml",
            "nix-darwin-options": "https://nix-community.github.io/home-manager/nix-darwin-options.xhtml",
        }

        # Get cache TTL from environment or use default (24 hours)
        self.cache_ttl = int(os.environ.get("NIXMCP_CACHE_TTL", 86400))

        # Create cache for parsed data
        self.cache = SimpleCache(max_size=100, ttl=self.cache_ttl)

        # Create HTML client with filesystem caching
        self.html_client = HTMLClient(ttl=self.cache_ttl)

        # In-memory data structures for search
        self.options = {}  # All options indexed by name
        self.options_by_category = defaultdict(list)  # Options indexed by category
        self.inverted_index = defaultdict(set)  # Word -> set of option names
        self.prefix_index = defaultdict(set)  # Prefix -> set of option names
        self.hierarchical_index = defaultdict(set)  # Hierarchical parts -> set of option names

        # Version for cache compatibility
        self.data_version = "1.0.0"

        # Cache key for data
        self.cache_key = f"home_manager_data_v{self.data_version}"

        # Request timeout settings
        self.connect_timeout = 5.0  # seconds
        self.read_timeout = 15.0  # seconds

        # Retry settings
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

        # Loading state
        self.is_loaded = False
        self.loading_error = None
        self.loading_lock = threading.RLock()
        self.loading_thread = None
        self.loading_in_progress = False

        logger.info("Home Manager client initialized")

    def fetch_url(self, url: str, force_refresh: bool = False) -> str:
        """Fetch HTML content from a URL with filesystem caching and error handling.

        Args:
            url: The URL to fetch HTML content from
            force_refresh: Whether to bypass cache and force a refresh from the web

        Returns:
            The HTML content as a string

        Raises:
            Exception: If there was an error fetching or parsing the content
        """
        logger.debug(f"Fetching URL with filesystem cache: {url}")

        try:
            # Use our HTML client with filesystem caching
            content, metadata = self.html_client.fetch(url, force_refresh=force_refresh)

            # Check for errors
            if content is None:
                error_msg = metadata.get("error", "Unknown error")
                logger.error(f"Error fetching URL {url}: {error_msg}")
                raise Exception(f"Failed to fetch URL: {error_msg}")

            # Log cache status
            if metadata.get("from_cache", False):
                logger.debug(f"Retrieved {url} from cache")
            else:
                logger.debug(f"Retrieved {url} from web")

            return content

        except Exception as e:
            logger.error(f"Error in fetch_url for {url}: {str(e)}")
            raise

    def parse_html(self, html: str, doc_type: str) -> List[Dict[str, Any]]:
        """Parse Home Manager HTML documentation and extract options."""
        options = []

        try:
            logger.info(f"Parsing HTML content for {doc_type}")
            soup = BeautifulSoup(html, "html.parser")

            # Find the variablelist that contains the options
            variablelist = soup.find(class_="variablelist")

            if not variablelist:
                logger.warning(f"No variablelist found in {doc_type} HTML")
                return []

            # Find the definition list that contains all the options
            dl = variablelist.find("dl")

            if not dl:
                logger.warning(f"No definition list found in {doc_type} HTML")
                return []

            # Get all dt (term) elements - these contain option names
            dt_elements = dl.find_all("dt")

            if not dt_elements:
                logger.warning(f"No option terms found in {doc_type} HTML")
                return []

            # Process each term (dt) and its description (dd)
            for dt in dt_elements:
                try:
                    # Find the term span that contains the option name
                    term_span = dt.find("span", class_="term")
                    if not term_span:
                        continue

                    # Find the code element with the option name
                    code = term_span.find("code")
                    if not code:
                        continue

                    # Get the option name
                    option_name = code.text.strip()

                    # Find the associated description element
                    dd = dt.find_next_sibling("dd")
                    if not dd:
                        continue

                    # Get paragraphs from the description
                    p_elements = dd.find_all("p")

                    # Extract description, type, default, and example
                    description = ""
                    option_type = ""
                    default_value = None
                    example_value = None
                    introduced_version = None
                    deprecated_version = None
                    manual_url = None

                    # First paragraph is typically the description
                    if p_elements and len(p_elements) > 0:
                        description = p_elements[0].text.strip()

                    # Look for type info in subsequent paragraphs
                    for p in p_elements[1:]:
                        text = p.text.strip()

                        # Extract type
                        if "Type:" in text:
                            option_type = text.split("Type:")[1].strip()

                        # Extract default value
                        elif "Default:" in text:
                            default_value = text.split("Default:")[1].strip()

                        # Extract example
                        elif "Example:" in text:
                            example_value = text.split("Example:")[1].strip()

                        # Extract introduced version
                        elif "Introduced in version:" in text or "Since:" in text:
                            introduced_match = re.search(r"(Introduced in version|Since):\s*([0-9\.]+)", text)
                            if introduced_match:
                                introduced_version = introduced_match.group(2)

                        # Extract deprecated version
                        elif "Deprecated in version:" in text or "Deprecated since:" in text:
                            deprecated_match = re.search(
                                r"(Deprecated in version|Deprecated since):\s*([0-9\.]+)", text
                            )
                            if deprecated_match:
                                deprecated_version = deprecated_match.group(2)

                    # Try to find a manual link
                    link_element = dd.find("a", href=True)
                    if link_element and "manual" in link_element.get("href", ""):
                        manual_url = link_element.get("href")

                    # Determine the category
                    # Use the previous heading or a default category
                    category_heading = dt.find_previous("h3")
                    category = category_heading.text.strip() if category_heading else "Uncategorized"

                    # Create the option record
                    option = {
                        "name": option_name,
                        "type": option_type,
                        "description": description,
                        "default": default_value,
                        "example": example_value,
                        "category": category,
                        "source": doc_type,
                        "introduced_version": introduced_version,
                        "deprecated_version": deprecated_version,
                        "manual_url": manual_url,
                    }

                    options.append(option)

                except Exception as e:
                    logger.warning(f"Error parsing option in {doc_type}: {str(e)}")
                    continue

            logger.info(f"Parsed {len(options)} options from {doc_type}")
            return options

        except Exception as e:
            logger.error(f"Error parsing HTML content for {doc_type}: {str(e)}")
            return []

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

            # Process each option
            for option in options:
                option_name = option["name"]

                # Store the complete option
                self.options[option_name] = option

                # Index by category
                category = option.get("category", "Uncategorized")
                self.options_by_category[category].append(option_name)

                # Build inverted index for all words in name and description
                name_words = re.findall(r"\w+", option_name.lower())
                desc_words = re.findall(r"\w+", option.get("description", "").lower())

                # Add to inverted index with higher weight for name words
                for word in name_words:
                    if len(word) > 2:  # Skip very short words
                        self.inverted_index[word].add(option_name)

                for word in desc_words:
                    if len(word) > 2:  # Skip very short words
                        self.inverted_index[word].add(option_name)

                # Build prefix index for quick prefix searches
                parts = option_name.split(".")
                for i in range(1, len(parts) + 1):
                    prefix = ".".join(parts[:i])
                    self.prefix_index[prefix].add(option_name)

                # Build hierarchical index for each path component
                for i, part in enumerate(parts):
                    # Get the parent path up to this component
                    parent_path = ".".join(parts[:i]) if i > 0 else ""

                    # Add this part to the hierarchical index
                    self.hierarchical_index[(parent_path, part)].add(option_name)

            logger.info(
                f"Built search indices with {len(self.options)} options, "
                f"{len(self.inverted_index)} words, "
                f"{len(self.prefix_index)} prefixes, "
                f"{len(self.hierarchical_index)} hierarchical parts"
            )

        except Exception as e:
            logger.error(f"Error building search indices: {str(e)}")
            raise

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
                logger.info(f"Loaded {len(options)} options from {doc_type}")
            except Exception as e:
                error_msg = f"Error loading options from {doc_type}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        if not all_options and errors:
            error_summary = "; ".join(errors)
            logger.error(f"Failed to load any options: {error_summary}")
            raise Exception(f"Failed to load Home Manager options: {error_summary}")

        logger.info(f"Loaded a total of {len(all_options)} options from all sources")
        return all_options

    def ensure_loaded(self, force_refresh: bool = False) -> None:
        """Ensure that options are loaded and indices are built.

        Args:
            force_refresh: Whether to bypass cache and force a refresh from the web
        """
        # First check if already loaded without acquiring the lock
        # This is a quick check to avoid lock contention
        if self.is_loaded and not force_refresh:
            return

        # Check if we know there was a loading error without acquiring the lock
        if self.loading_error and not force_refresh:
            raise Exception(f"Previous loading attempt failed: {self.loading_error}")

        # Check if background loading is in progress without the lock first
        if self.loading_in_progress and not force_refresh:
            logger.info("Waiting for background data loading to complete...")
            # Wait outside of lock to prevent deadlock
            max_wait = 3  # seconds - reduced from 10 to prevent blocking for too long
            start_time = time.time()

            # Wait with timeout for background loading to complete
            while self.loading_in_progress and time.time() - start_time < max_wait:
                time.sleep(0.05)  # Reduced sleep time for more frequent checks
                if self.is_loaded:
                    return

            # Double-check loading state with the lock after waiting
            with self.loading_lock:
                if self.is_loaded and not force_refresh:
                    return
                # Split complex condition into parts to avoid linting issues
                in_progress = self.loading_in_progress
                has_thread = self.loading_thread
                thread_alive = has_thread and self.loading_thread.is_alive()
                no_force = not force_refresh
                if in_progress and has_thread and thread_alive and no_force:
                    # Still loading but we've waited long enough - raise exception with timeout
                    raise Exception("Timed out waiting for background loading to complete")
                elif self.loading_error and not force_refresh:
                    raise Exception(f"Loading failed: {self.loading_error}")

        # At this point, either:
        # 1. No background loading was happening
        # 2. Background loading finished or failed while we were waiting
        # 3. We're forcing a refresh
        with self.loading_lock:
            # Double-check loaded state after acquiring lock
            if self.is_loaded and not force_refresh:
                return

            if self.loading_error and not force_refresh:
                raise Exception(f"Loading attempt failed: {self.loading_error}")

            # If another background load is now in progress and we're not forcing refresh, wait for it
            if self.loading_in_progress and not force_refresh:
                # Release the lock and retry from the beginning
                # This avoids the case where we'd try to load while another thread is already loading
                pass  # The lock is released automatically when we exit the 'with' block
                # Recurse with a small delay to let the other thread make progress
                time.sleep(0.01)
                return self.ensure_loaded(force_refresh=False)

            # If we're forcing a refresh, invalidate the cache
            if force_refresh:
                logger.info("Forced refresh requested, invalidating cache")
                self.invalidate_cache()
                self.is_loaded = False
                self.loading_error = None

            # No loading in progress or forced refresh, we'll do it ourselves
            self.loading_in_progress = True

        try:
            # Do the actual loading outside the lock to prevent deadlocks
            self._load_data_internal()

            # Update state after loading
            with self.loading_lock:
                self.is_loaded = True
                self.loading_in_progress = False
                logger.info("HomeManagerClient data successfully loaded")
        except Exception as e:
            with self.loading_lock:
                self.loading_error = str(e)
                self.loading_in_progress = False
            logger.error(f"Failed to load Home Manager options: {str(e)}")
            raise

    def invalidate_cache(self) -> None:
        """Invalidate the disk cache for Home Manager data."""
        try:
            logger.info(f"Invalidating Home Manager data cache with key {self.cache_key}")
            self.html_client.cache.invalidate_data(self.cache_key)

            # Also invalidate HTML caches
            for url in self.hm_urls.values():
                self.html_client.cache.invalidate(url)

            logger.info("Home Manager data cache invalidated")
        except Exception as e:
            logger.error(f"Failed to invalidate Home Manager data cache: {str(e)}")
            # Continue execution, don't fail on cache invalidation errors

    def load_in_background(self) -> None:
        """Start loading options in a background thread."""

        def _load_data():
            try:
                # Set flag outside of lock to minimize time spent in locked section
                # This is safe because we're the only thread that could be changing this flag
                # at this point (the main thread has already passed this critical section)
                self.loading_in_progress = True
                logger.info("Background thread started loading Home Manager options")

                # Do the actual loading without holding the lock
                self._load_data_internal()

                # Update state after successful loading
                with self.loading_lock:
                    self.is_loaded = True
                    self.loading_in_progress = False

                logger.info("Background loading of Home Manager options completed successfully")
            except Exception as e:
                # Update state after failed loading
                error_msg = str(e)
                with self.loading_lock:
                    self.loading_error = error_msg
                    self.loading_in_progress = False
                logger.error(f"Background loading of Home Manager options failed: {error_msg}")

        # Check if we should start a background thread
        # First check without the lock for efficiency
        if self.is_loaded:
            logger.info("Data already loaded, no need for background loading")
            return

        if self.loading_thread is not None and self.loading_thread.is_alive():
            logger.info("Background loading thread already running")
            return

        # Only take the lock to check/update thread state
        with self.loading_lock:
            # Double-check the state after acquiring the lock
            if self.is_loaded:
                logger.info("Data already loaded, no need for background loading")
                return

            if self.loading_thread is not None and self.loading_thread.is_alive():
                logger.info("Background loading thread already running")
                return

            if self.loading_in_progress:
                logger.info("Loading already in progress in another thread")
                return

            # Start the loading thread
            logger.info("Starting background thread for loading Home Manager options")
            self.loading_thread = threading.Thread(target=_load_data, daemon=True)
            # Set loading_in_progress here to ensure it's set before the thread starts
            self.loading_in_progress = True
            self.loading_thread.start()

    def _save_in_memory_data(self) -> bool:
        """Save in-memory data structures to disk cache.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Saving Home Manager data structures to disk cache")

            # Convert set objects to lists for JSON serialization
            serializable_data = {
                "options_count": len(self.options),
                "options": self.options,
                "timestamp": time.time(),
            }

            # Save the basic metadata as JSON
            self.html_client.cache.set_data(self.cache_key, serializable_data)

            # For complex data structures like defaultdict and sets,
            # use binary serialization with pickle
            binary_data = {
                "options_by_category": self.options_by_category,
                "inverted_index": {k: list(v) for k, v in self.inverted_index.items()},
                "prefix_index": {k: list(v) for k, v in self.prefix_index.items()},
                "hierarchical_index": {str(k): list(v) for k, v in self.hierarchical_index.items()},
            }

            self.html_client.cache.set_binary_data(self.cache_key, binary_data)
            logger.info(f"Successfully saved Home Manager data to disk cache with key {self.cache_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save Home Manager data to disk cache: {str(e)}")
            return False

    def _load_from_cache(self) -> bool:
        """Attempt to load data from disk cache.

        Returns:
            bool: True if successfully loaded from cache, False otherwise
        """
        try:
            logger.info("Attempting to load Home Manager data from disk cache")

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
            self.options = data["options"]

            # Load complex data structures
            self.options_by_category = binary_data["options_by_category"]

            # Convert lists back to sets for the indices
            self.inverted_index = defaultdict(set)
            for k, v in binary_data["inverted_index"].items():
                self.inverted_index[k] = set(v)

            self.prefix_index = defaultdict(set)
            for k, v in binary_data["prefix_index"].items():
                self.prefix_index[k] = set(v)

            # Handle tuple keys in hierarchical_index
            self.hierarchical_index = defaultdict(set)
            for k_str, v in binary_data["hierarchical_index"].items():
                # Convert string representation back to tuple
                # Expected format is like "('parent', 'child')"
                # Remove the tuple syntax and split by comma
                k_str = k_str.strip("()")
                if "," in k_str:
                    parts = k_str.split(",")
                    # Handle empty string in first part
                    if len(parts) == 2:
                        first = parts[0].strip("' \"")
                        second = parts[1].strip("' \"")
                        key = (first, second)
                        self.hierarchical_index[key] = set(v)

            logger.info(f"Successfully loaded Home Manager data from disk cache with {len(self.options)} options")
            return True
        except Exception as e:
            logger.error(f"Failed to load Home Manager data from disk cache: {str(e)}")
            return False

    def _load_data_internal(self) -> None:
        """Internal method to load data without modifying state flags."""
        try:
            # First try to load from cache
            if self._load_from_cache():
                self.is_loaded = True
                logger.info("Successfully loaded Home Manager data from disk cache")
                return

            # If cache loading failed, load from web
            logger.info("Loading Home Manager options from web")
            options = self.load_all_options()
            self.build_search_indices(options)

            # Save to cache for next time
            self._save_in_memory_data()

            logger.info("Successfully loaded Home Manager options and built indices")
        except Exception as e:
            logger.error(f"Failed to load Home Manager options: {str(e)}")
            raise

    def search_options(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for Home Manager options using the in-memory indices.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            Dict containing search results and metadata
        """
        try:
            # Check if loaded without trying to ensure loading
            if not self.is_loaded:
                logger.warning(f"Search request received while data is still loading: {query}")
                if self.loading_in_progress:
                    return {
                        "count": 0,
                        "options": [],
                        "loading": True,
                        "error": "Home Manager data is still loading. Please try again in a few seconds.",
                        "found": False,
                    }
                elif self.loading_error:
                    return {
                        "count": 0,
                        "options": [],
                        "error": f"Failed to load data: {self.loading_error}",
                        "found": False,
                    }

            logger.info(f"Searching Home Manager options for: {query}")
            query = query.strip()

            if not query:
                return {"count": 0, "options": [], "error": "Empty query", "found": False}

            # Track matched options and their scores
            matches = {}  # option_name -> score

            # Check for exact match
            if query in self.options:
                matches[query] = 100  # Highest possible score

            # Check for hierarchical path match (services.foo.*)
            if "." in query:
                # If query ends with wildcard, use prefix search
                if query.endswith("*"):
                    prefix = query[:-1]  # Remove the '*'
                    for option_name in self.prefix_index.get(prefix, set()):
                        matches[option_name] = 90  # Very high score for prefix match
                else:
                    # Try prefix search anyway
                    for option_name in self.prefix_index.get(query, set()):
                        if option_name.startswith(query + "."):
                            matches[option_name] = 80  # High score for hierarchical match
            else:
                # For top-level prefixes without dots (e.g., "home" or "xdg")
                # This ensures we find options like "home.file.*" when searching for "home"
                for option_name in self.options.keys():
                    # Check if option_name starts with query followed by a dot
                    if option_name.startswith(query + "."):
                        matches[option_name] = 75  # High score but not as high as exact matches

            # Split query into words for text search
            words = re.findall(r"\w+", query.lower())
            if words:
                # Find options that match all words
                candidates = set()
                for i, word in enumerate(words):
                    # For the first word, get all matches
                    if i == 0:
                        candidates = self.inverted_index.get(word, set()).copy()
                    # For subsequent words, intersect with existing matches
                    else:
                        word_matches = self.inverted_index.get(word, set())
                        candidates &= word_matches

                # Add candidates to matches with appropriate scores
                for option_name in candidates:
                    # Calculate score based on whether words appear in name or description
                    option = self.options[option_name]

                    score = 0
                    for word in words:
                        # Higher score if word is in name
                        if word in option_name.lower():
                            score += 10
                        # Lower score if only in description
                        elif word in option.get("description", "").lower():
                            score += 3

                    matches[option_name] = max(matches.get(option_name, 0), score)

            # If still no matches, try partial matching with prefixes of words
            if not matches and len(words) > 0:
                word_prefixes = [w[:3] for w in words if len(w) >= 3]
                for prefix in word_prefixes:
                    # Find all words that start with this prefix
                    for word, options in self.inverted_index.items():
                        if word.startswith(prefix):
                            for option_name in options:
                                matches[option_name] = matches.get(option_name, 0) + 2

            # Sort matches by score
            sorted_matches = sorted(
                matches.items(), key=lambda x: (-x[1], x[0])  # Sort by score (desc) then name (asc)
            )

            # Get top matches
            top_matches = sorted_matches[:limit]

            # Format results
            result_options = []
            for option_name, score in top_matches:
                option = self.options[option_name]
                result_options.append(
                    {
                        "name": option_name,
                        "description": option.get("description", ""),
                        "type": option.get("type", ""),
                        "default": option.get("default", ""),
                        "category": option.get("category", ""),
                        "source": option.get("source", ""),
                        "score": score,
                    }
                )

            result = {"count": len(matches), "options": result_options, "found": len(result_options) > 0}
            return result

        except Exception as e:
            logger.error(f"Error searching Home Manager options: {str(e)}")
            return {"count": 0, "options": [], "error": str(e), "found": False}

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific Home Manager option.

        Args:
            option_name: Name of the option

        Returns:
            Dict containing option details
        """
        try:
            # Check if loaded without trying to ensure loading
            if not self.is_loaded:
                logger.warning(f"Option request received while data is still loading: {option_name}")
                if self.loading_in_progress:
                    return {
                        "name": option_name,
                        "loading": True,
                        "error": "Home Manager data is still loading. Please try again in a few seconds.",
                        "found": False,
                    }
                elif self.loading_error:
                    return {"name": option_name, "error": f"Failed to load data: {self.loading_error}", "found": False}

            logger.info(f"Getting Home Manager option: {option_name}")

            # Check for exact match
            if option_name in self.options:
                option = self.options[option_name]

                # Find related options (same parent path)
                related_options = []
                if "." in option_name:
                    parts = option_name.split(".")
                    parent_path = ".".join(parts[:-1])

                    # Get options with same parent path
                    for other_name, other_option in self.options.items():
                        if other_name != option_name and other_name.startswith(parent_path + "."):
                            related_options.append(
                                {
                                    "name": other_name,
                                    "description": other_option.get("description", ""),
                                    "type": other_option.get("type", ""),
                                }
                            )

                    # Limit to top 5 related options
                    related_options = related_options[:5]

                result = {
                    "name": option_name,
                    "description": option.get("description", ""),
                    "type": option.get("type", ""),
                    "default": option.get("default", ""),
                    "example": option.get("example", ""),
                    "category": option.get("category", ""),
                    "source": option.get("source", ""),
                    "found": True,
                }

                if related_options:
                    result["related_options"] = related_options

                return result

            # Try to find options that start with the given name
            if option_name in self.prefix_index:
                matches = list(self.prefix_index[option_name])
                logger.info(f"Option {option_name} not found, but found {len(matches)} options with this prefix")

                # Get the first matching option
                if matches:
                    suggested_name = matches[0]
                    return {
                        "name": option_name,
                        "error": f"Option not found. Did you mean '{suggested_name}'?",
                        "found": False,
                        "suggestions": matches[:5],  # Include up to 5 suggestions
                    }

            # No matches found
            return {"name": option_name, "error": "Option not found", "found": False}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting Home Manager option: {error_msg}")
            return {"name": option_name, "error": error_msg, "found": False}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about Home Manager options.

        Returns:
            Dict containing statistics
        """
        try:
            # Check if loaded without trying to ensure loading
            if not self.is_loaded:
                logger.warning("Stats request received while data is still loading")
                if self.loading_in_progress:
                    return {
                        "total_options": 0,
                        "loading": True,
                        "error": "Home Manager data is still loading. Please try again in a few seconds.",
                        "found": False,
                    }
                elif self.loading_error:
                    return {"total_options": 0, "error": f"Failed to load data: {self.loading_error}", "found": False}

            logger.info("Getting Home Manager option statistics")

            # Count options by source
            options_by_source = defaultdict(int)
            for option in self.options.values():
                source = option.get("source", "unknown")
                options_by_source[source] += 1

            # Count options by category
            options_by_category = {category: len(options) for category, options in self.options_by_category.items()}

            # Count options by type
            options_by_type = defaultdict(int)
            for option in self.options.values():
                option_type = option.get("type", "unknown")
                options_by_type[option_type] += 1

            # Extract some top-level stats
            total_options = len(self.options)
            total_categories = len(self.options_by_category)
            total_types = len(options_by_type)

            return {
                "total_options": total_options,
                "total_categories": total_categories,
                "total_types": total_types,
                "by_source": options_by_source,
                "by_category": options_by_category,
                "by_type": options_by_type,
                "index_stats": {
                    "words": len(self.inverted_index),
                    "prefixes": len(self.prefix_index),
                    "hierarchical_parts": len(self.hierarchical_index),
                },
                "found": True,
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting Home Manager option statistics: {error_msg}")
            return {"error": error_msg, "total_options": 0, "found": False}
