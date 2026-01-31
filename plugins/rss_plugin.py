
import logging
import time
import feedparser
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from dateutil import parser as date_parser

from src.plugins import SourcePlugin, PluginMetadata
from src.models import ContentItem

class RSSPlugin(SourcePlugin):
    """
    Plugin for fetching content from RSS/Atom feeds.

    Validates Requirements 3.1, 3.2, 3.4, 3.5.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config = {}
        self._url = None
        self._fetch_interval = 300 # Default 5 minutes
        self._last_fetch = 0
        self._error_count = 0
        self._backoff_factor = 2

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="RSS Source",
            version="1.0.0",
            description="Fetches content from RSS and Atom feeds",
            author="Number Station Team",
            plugin_type="source",
            dependencies=["feedparser", "requests"],
            capabilities=["rss", "atom", "xml"],
            config_schema={
                "url": "string (required)",
                "fetch_interval": "integer (optional, default=300)",
                "retry_count": "integer (optional, default=3)",
                "timeout": "integer (optional, default=10)"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the plugin configuration."""
        if "url" not in config:
            self.logger.error("RSS Plugin config missing required 'url' field")
            return False

        if not isinstance(config["url"], str) or not config["url"].startswith(("http://", "https://")):
             self.logger.error(f"Invalid RSS URL: {config.get('url')}")
             return False

        if "fetch_interval" in config and not isinstance(config["fetch_interval"], int):
            self.logger.error("fetch_interval must be an integer")
            return False

        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the plugin."""
        if not self.validate_config(config):
            return False

        self._config = config
        self._url = config["url"]
        self._fetch_interval = config.get("fetch_interval", 300)
        return True

    def fetch_content(self) -> List[ContentItem]:
        """Fetch content from the RSS feed."""
        if not self._url:
            self.logger.error("RSS Plugin not configured")
            return []

        # Check fetch interval
        current_time = time.time()
        if current_time - self._last_fetch < self._fetch_interval:
            return []

        try:
            self.logger.info(f"Fetching RSS feed from {self._url}")
            feed = feedparser.parse(self._url)

            if feed.bozo:
                self.logger.warning(f"Error parsing feed {self._url}: {feed.bozo_exception}")
                # Bozo bit set means error, but feedparser might still have data.
                # If no entries, it's a hard failure.
                if not feed.entries:
                    raise Exception(f"Failed to parse feed: {feed.bozo_exception}")

            items = []
            for entry in feed.entries:
                content_item = self._parse_entry(entry)
                if content_item:
                    items.append(content_item)

            self._last_fetch = current_time
            self._error_count = 0 # Reset error count on success
            return items

        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error fetching RSS feed: {e}")
            # Identify if we should backoff?
            # (Requirement 3.5: Exponential backoff retry)
            # The backoff logic is often handled by the scheduler or here.
            # If handled here, we effectively increase _last_fetch to delay next try.
            backoff_delay = self._fetch_interval * (self._backoff_factor ** self._error_count)
            self._last_fetch = current_time + backoff_delay - self._fetch_interval # Artificially delay next fetch
            self.logger.info(f"Backing off for {backoff_delay} seconds")
            return []

    def test_connection(self) -> bool:
        """Test connection to the RSS feed."""
        if not self._url:
            return False
        try:
            response = requests.head(self._url, timeout=10)
            return response.status_code == 200
        except Exception:
            try:
                # Fallback to get if head fails
                response = requests.get(self._url, timeout=10)
                return response.status_code == 200
            except Exception as e:
                self.logger.error(f"Connection test failed: {e}")
                return False

    def _parse_entry(self, entry: Any) -> Optional[ContentItem]:
        """Convert feed entry to ContentItem."""
        try:
            # Generate ID (use guid or link)
            entry_id = getattr(entry, "id", getattr(entry, "link", None))
            if not entry_id:
                # Fallback to hash of title and date?
                return None

            # Parse timestamp
            published = getattr(entry, "published_parsed", getattr(entry, "updated_parsed", None))
            if published:
                timestamp = datetime.fromtimestamp(time.mktime(published))
            else:
                timestamp = datetime.now()

            # Content normalization (summary or content)
            content = ""
            if hasattr(entry, "content"):
                content = entry.content[0].value
            elif hasattr(entry, "summary"):
                content = entry.summary
            else:
                content = getattr(entry, "title", "")

            # Image extraction (media_content, enclosures, or img tags)
            media_urls = []
            if hasattr(entry, "media_content"):
                media_urls.extend([m["url"] for m in entry.media_content if "url" in m])
            if hasattr(entry, "enclosures"):
                media_urls.extend([e["href"] for e in entry.enclosures if "href" in e])

            return ContentItem(
                id=entry_id,
                source=self._url,
                source_type="rss",
                title=getattr(entry, "title", "No Title"),
                content=str(content), # Ensure string
                timestamp=timestamp,
                url=getattr(entry, "link", self._url),
                author=getattr(entry, "author", None),
                tags=[tag.term for tag in getattr(entry, "tags", [])],
                media_urls=media_urls,
                metadata={"raw_entry": str(entry)}
            )
        except Exception as e:
            self.logger.error(f"Error parsing entry: {e}")
            return None
