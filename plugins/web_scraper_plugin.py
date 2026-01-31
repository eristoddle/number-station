
import logging
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.plugins import SourcePlugin, PluginMetadata
from src.models import ContentItem

class WebScraperPlugin(SourcePlugin):
    """
    Plugin for scraping content from websites using CSS selectors.

    Validates Requirements 3.3, 5.3, 5.5.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config = {}
        self._url = None
        self._content_selector = None
        self._title_selector = None
        self._fetch_interval = 300
        self._last_fetch = 0

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Web Scraper",
            version="1.0.0",
            description="Scrapes content from websites using CSS selectors",
            author="Number Station Team",
            plugin_type="source",
            dependencies=["beautifulsoup4", "requests"],
            capabilities=["html", "scraping"],
            config_schema={
                "url": "string (required)",
                "content_selector": "string (required) - CSS selector for content",
                "title_selector": "string (optional) - CSS selector for title",
                "fetch_interval": "integer (optional, default=300)",
                "date_selector": "string (optional)"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the plugin configuration."""
        if "url" not in config:
            self.logger.error("Web Scraper config missing required 'url' field")
            return False

        if not isinstance(config["url"], str) or not config["url"].startswith(("http://", "https://")):
             self.logger.error(f"Invalid URL: {config.get('url')}")
             return False

        if "content_selector" not in config:
            self.logger.error("Web Scraper config missing required 'content_selector' field")
            return False

        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the plugin."""
        if not self.validate_config(config):
            return False

        self._config = config
        self._url = config["url"]
        self._content_selector = config["content_selector"]
        self._title_selector = config.get("title_selector", "title") # Default to <title> tag
        self._fetch_interval = config.get("fetch_interval", 300)
        return True

    def fetch_content(self) -> List[ContentItem]:
        """Fetch content from the website."""
        if not self._url or not self._content_selector:
            return []

        # Check fetch interval
        current_time = time.time()
        if current_time - self._last_fetch < self._fetch_interval:
            return []

        try:
            self.logger.info(f"Scraping {self._url}")
            response = requests.get(self._url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract content elements
            elements = soup.select(self._content_selector)

            items = []
            for i, element in enumerate(elements):
                content_text = element.get_text(separator="\n", strip=True)
                if not content_text:
                    continue

                # Try to find a title
                title = "No Title"
                if self._title_selector:
                    # If title selector is inside the content element? Or global?
                    # Typically global title for page, or item specific?
                    # Requirement 3.3 implies "website scraping", possibly for news list or single page.
                    # Let's assume list of items if content_selector maps to multiple items.
                    # Or single item if one.
                    # If multiple elements, we might need a container selector + item selector logic.
                    # For simplicity, current logic treats each matching element as an item.
                    # Title retrieval is tricky if it's per item.
                    # Let's assume title_selector is RELATIVE to element if possible?
                    # BeautifulSoup select supports context.
                    try:
                        title_el = element.select_one(self._title_selector)
                        if title_el:
                            title = title_el.get_text(strip=True)
                        else:
                            # Fallback to page title if not found in element
                            page_title = soup.select_one("title")
                            title = page_title.get_text(strip=True) if page_title else "No Title"
                    except Exception:
                         title = "No Title"

                # Generate ID
                item_id = f"{self._url}#{i}-{hash(content_text[:50])}" # Simple ID generation

                # Timestamp - complicated without metadata extraction
                timestamp = datetime.now()

                item = ContentItem(
                    id=item_id,
                    source=self._url,
                    source_type="web_scraper",
                    title=title,
                    content=content_text,
                    timestamp=timestamp,
                    url=self._url,
                    metadata={"selector": self._content_selector}
                )
                items.append(item)

            self._last_fetch = current_time
            return items

        except Exception as e:
            self.logger.error(f"Error scraping website: {e}")
            return []

    def test_connection(self) -> bool:
        """Test connection to the website."""
        if not self._url:
            return False
        try:
            response = requests.head(self._url, timeout=10)
            return response.status_code == 200
        except Exception:
            try:
                response = requests.get(self._url, timeout=10)
                return response.status_code == 200
            except Exception:
                return False
