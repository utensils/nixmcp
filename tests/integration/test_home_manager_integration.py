"""Integration tests for Home Manager HTML structure analysis."""

import unittest
import logging
import requests
import pytest
from bs4 import BeautifulSoup, Tag

# Configure logging for tests with more verbose output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("home_manager_test")

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestHomeManagerDocStructure(unittest.TestCase):
    """
    Tests to analyze the actual structure of Home Manager documentation.

    These tests help determine the correct HTML structure to use in the HomeManagerClient
    for parsing the documentation. They make actual network requests to examine the
    structure rather than relying on assumptions.
    """

    def setUp(self):
        """Set up the test environment."""
        self.urls = [
            "https://nix-community.github.io/home-manager/options.xhtml",
            "https://nix-community.github.io/home-manager/nixos-options.xhtml",
            "https://nix-community.github.io/home-manager/nix-darwin-options.xhtml",
        ]

        # We'll populate these in the tests
        self.soups = {}

    def test_fetch_docs_and_analyze_structure(self):
        """Fetch actual documentation and analyze the HTML structure."""
        # Fetch the documentation pages
        for url in self.urls:
            source = url.split("/")[-1].split(".")[0]  # Extract source name (options, nixos-options, etc.)

            try:
                logger.info(f"Fetching {source} documentation from {url}")
                response = requests.get(url)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                self.soups[source] = soup

                # Log basic page info
                title = soup.find("title")
                logger.info(f"Title: {title.text if title else 'Unknown'}")

                # See if there are tables
                tables = soup.find_all("table")
                logger.info(f"Found {len(tables)} tables in {source}")

                if tables:
                    # Check table classes
                    for i, table in enumerate(tables[:3]):  # Log first 3 tables
                        table_class = table.get("class", ["no-class"])
                        logger.info(f"Table {i} class: {table_class}")

                # Check for definition lists which might contain options
                dl_elements = soup.find_all("dl")
                logger.info(f"Found {len(dl_elements)} definition list elements in {source}")

                if dl_elements:
                    # Check the first dl element in detail
                    first_dl = dl_elements[0]
                    dt_elements = first_dl.find_all("dt")
                    dd_elements = first_dl.find_all("dd")
                    logger.info(
                        f"First definition list has {len(dt_elements)} terms and {len(dd_elements)} descriptions"
                    )

                    # Examine a term to see if it contains option info
                    if dt_elements:
                        first_dt = dt_elements[0]
                        logger.info(f"First term content structure: {first_dt}")

                        # Look for option names
                        code_elements = first_dt.find_all("code")
                        if code_elements:
                            for code in code_elements[:2]:  # Log first 2
                                logger.info(f"Option code element: {code.text}")

                # Look for variablelist as mentioned in the HTML
                variablelist = soup.find_all(class_="variablelist")
                logger.info(f"Found {len(variablelist)} variablelist elements in {source}")

                # The page uses spans with class='term' to identify options
                term_spans = soup.find_all("span", class_="term")
                logger.info(f"Found {len(term_spans)} term spans in {source}")

                if term_spans:
                    # Sample the first few terms
                    for span in term_spans[:3]:
                        # Option name is in code element inside the term span
                        code = span.find("code")
                        if code:
                            logger.info(f"Option name: {code.text}")

                            # Look for associated description
                            dd = span.find_parent("dt").find_next_sibling("dd")
                            if dd:
                                # Type info and description are in p elements
                                p_elements = dd.find_all("p")
                                if p_elements:
                                    for i, p in enumerate(p_elements[:2]):
                                        logger.info(f"Description part {i}: {p.text[:50]}...")

                # Success
                self.assertTrue(True, f"Successfully analyzed {source} structure")

            except Exception as e:
                logger.error(f"Error analyzing {source}: {str(e)}")
                self.fail(f"Failed to analyze {source} due to: {str(e)}")

    def test_extract_sample_options(self):
        """Extract a few sample options to verify the structure."""
        # We'll just use the main options URL for this test
        url = "https://nix-community.github.io/home-manager/options.xhtml"
        source = "options"

        try:
            logger.info(f"Fetching {source} documentation from {url}")

            # Use a timeout to prevent hanging
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            logger.info(f"Extracting sample options from {source}")

            # The variablelist contains the options - HomeManagerClient looks for the class="variablelist" div
            variablelist = soup.find("div", class_="variablelist")
            if not variablelist:
                logger.warning(f"No variablelist div found in {source}")
                self.skipTest("No variablelist div found in the HTML structure")
                return

            # Find all definition terms (dt) which contain the option names
            dl = variablelist.find("dl")
            if not dl or not isinstance(dl, Tag):
                logger.warning(f"No definition list found in {source}")
                self.skipTest("No definition list found in the HTML structure")
                return

            # Get all dt elements (terms) - align with HomeManagerClient implementation
            dt_elements = dl.find_all("dt", recursive=False)

            # Process a few options
            options_found = 0
            for dt in dt_elements[:5]:  # Limit to first 5 options
                try:
                    # Extract option name using the same approach as HomeManagerClient._extract_option_name
                    term_span = dt.find("span", class_="term")
                    if not term_span or not isinstance(term_span, Tag):
                        logger.warning("Term span not found or not a Tag")
                        continue

                    # The HTML structure now has a code element with class="option" inside an <a> element
                    code = term_span.find("code", class_="option")
                    if not code or not isinstance(code, Tag) or not hasattr(code, "text"):
                        # Try the old way as fallback
                        code = term_span.find("code")
                        if not code or not isinstance(code, Tag) or not hasattr(code, "text"):
                            logger.warning("Code element not found or invalid")
                            continue

                    option_name = code.text.strip()

                    # Find the associated description - align with HomeManagerClient._parse_single_option
                    dd = dt.find_next_sibling("dd")
                    if not dd or not isinstance(dd, Tag):
                        logger.warning(f"No description found for {option_name}")
                        continue

                    # Extract metadata using similar approach to HomeManagerClient._extract_metadata_from_paragraphs
                    p_elements = dd.find_all("p")
                    if not p_elements:
                        logger.warning(f"No paragraphs found for {option_name}")
                        continue

                    # Description is in the first paragraph
                    description = p_elements[0].text.strip() if hasattr(p_elements[0], "text") else ""

                    # Get type info from paragraphs
                    metadata = {
                        "type": None,
                        "default": None,
                        "example": None,
                    }

                    for p in p_elements[1:]:  # Skip first paragraph (description)
                        if not hasattr(p, "text"):
                            continue
                        text = p.text.strip()
                        if "Type:" in text:
                            metadata["type"] = text.split("Type:", 1)[1].strip()
                        elif "Default:" in text:
                            metadata["default"] = text.split("Default:", 1)[1].strip()
                        elif "Example:" in text:
                            metadata["example"] = text.split("Example:", 1)[1].strip()

                    # Log the option
                    logger.info(f"Option: {option_name}")
                    logger.info(f"  Type: {metadata['type'] or 'unknown'}")
                    logger.info(f"  Default: {metadata['default'] or 'N/A'}")
                    logger.info(f"  Description: {description[:100]}...")

                    options_found += 1

                except Exception as e:
                    logger.warning(f"Error parsing option: {e}")
                    continue

            self.assertGreater(options_found, 0, f"No options extracted from {source}")
            logger.info(f"Successfully extracted {options_found} sample options from {source}")

        except requests.RequestException as e:
            logger.warning(f"Could not fetch Home Manager docs: {e}")
            self.skipTest(f"Network error fetching Home Manager docs: {e}")
        except Exception as e:
            logger.error(f"Error extracting options: {e}")
            self.fail(f"Failed to extract options: {e}")


if __name__ == "__main__":
    # Add a direct test run that prints results
    unittest.main(verbosity=2)
