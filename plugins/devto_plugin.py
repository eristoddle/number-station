
import logging
import time
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.plugins import SourcePlugin, PluginMetadata
from src.models import ContentItem

class DevToPlugin(SourcePlugin):
    """
    Plugin for fetching content from Dev.to.

    Validates Requirements 4.3, 4.4.
    """

    API_URL = "https://dev.to/api/articles"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config = {}
        self._tag = None
        self._username = None
        self._fetch_interval = 300
        self._last_fetch = 0

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Dev.to Source",
            version="1.0.0",
            description="Fetches articles from Dev.to",
            author="Number Station Team",
            plugin_type="source",
            dependencies=["requests"],
            capabilities=["devto", "tech"],
            config_schema={
                "tag": "string (optional) - Filter by tag",
                "username": "string (optional) - Filter by username",
                "fetch_interval": "integer (optional, default=300)",
                "limit": "integer (optional, default=10)"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the plugin configuration."""
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the plugin."""
        self._config = config
        self._tag = config.get("tag")
        self._username = config.get("username")
        self._fetch_interval = config.get("fetch_interval", 300)
        self._limit = min(config.get("limit", 10), 30)
        return True

    def fetch_content(self) -> List[ContentItem]:
        """Fetch articles."""
        if time.time() - self._last_fetch < self._fetch_interval:
            return []

        try:
            params = {"per_page": self._limit}
            if self._tag:
                params["tag"] = self._tag
            if self._username:
                params["username"] = self._username

            self.logger.info(f"Fetching Dev.to articles (params={params})")

            resp = requests.get(self.API_URL, params=params, timeout=10)
            resp.raise_for_status()

            articles = resp.json()
            items = []

            for article in articles:
                items.append(self._parse_article(article))

            self._last_fetch = time.time()
            return items

        except Exception as e:
            self.logger.error(f"Error fetching Dev.to: {e}")
            return []

    def _parse_article(self, article: Dict[str, Any]) -> ContentItem:
        """Convert Dev.to article to ContentItem."""
        # published_at format: "2019-07-24T13:52:14Z"
        timestamp = datetime.now()
        if "published_at" in article and article["published_at"]:
            try:
                timestamp = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00"))
            except ValueError:
                pass

        tags = article.get("tag_list", [])
        if isinstance(tags, str): # sometimes string not list? API docs say array but safer check
             tags = [t.strip() for t in tags.split(",")]

        return ContentItem(
            id=f"devto_{article.get('id')}",
            source="Dev.to",
            source_type="devto",
            title=article.get("title", "No Title"),
            content=article.get("description", "") or article.get("title", ""),
            timestamp=timestamp,
            url=article.get("url", ""),
            author=article.get("user", {}).get("name"),
            tags=tags,
            media_urls=[article.get("cover_image")] if article.get("cover_image") else [],
            metadata={
                "reactions": article.get("public_reactions_count"),
                "comments": article.get("comments_count")
            }
        )

    def test_connection(self) -> bool:
        try:
            resp = requests.head(self.API_URL, timeout=5)
            # Dev.to might not allow HEAD, retry with GET limit 1
            if resp.status_code == 405:
                 resp = requests.get(self.API_URL, params={"per_page": 1}, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
