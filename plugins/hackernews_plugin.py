
import logging
import time
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.plugins import SourcePlugin, PluginMetadata
from src.models import ContentItem

class HackerNewsPlugin(SourcePlugin):
    """
    Plugin for fetching content from Hacker News.

    Validates Requirements 4.3, 4.4.
    """

    API_BASE = "https://hacker-news.firebaseio.com/v0"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config = {}
        self._max_items = 20
        self._fetch_interval = 300
        self._last_fetch = 0

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Hacker News Source",
            version="1.0.0",
            description="Fetches top stories from Hacker News",
            author="Number Station Team",
            plugin_type="source",
            dependencies=["requests"],
            capabilities=["hackernews", "tech"],
            config_schema={
                "fetch_interval": "integer (optional, default=300)",
                "max_items": "integer (optional, default=20)"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the plugin configuration."""
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the plugin."""
        self._config = config
        self._fetch_interval = config.get("fetch_interval", 300)
        self._max_items = min(config.get("max_items", 20), 50) # Limit to 50 max to avoid hammering API
        return True

    def fetch_content(self) -> List[ContentItem]:
        """Fetch top stories."""
        if time.time() - self._last_fetch < self._fetch_interval:
            return []

        try:
            self.logger.info("Fetching Hacker News top stories")

            # Get Top Stories IDs
            resp = requests.get(f"{self.API_BASE}/topstories.json", timeout=10)
            resp.raise_for_status()
            story_ids = resp.json()[:self._max_items]

            items = []
            for sid in story_ids:
                try:
                    item_resp = requests.get(f"{self.API_BASE}/item/{sid}.json", timeout=5)
                    if item_resp.status_code != 200:
                        continue

                    story = item_resp.json()
                    if not story or story.get("type") != "story":
                        continue

                    items.append(self._parse_story(story))
                except Exception as e:
                    self.logger.error(f"Error fetching HN item {sid}: {e}")

            self._last_fetch = time.time()
            return items

        except Exception as e:
            self.logger.error(f"Error fetching Hacker News: {e}")
            return []

    def _parse_story(self, story: Dict[str, Any]) -> ContentItem:
        """Convert HN story to ContentItem."""
        timestamp = datetime.fromtimestamp(story.get("time", time.time()))

        return ContentItem(
            id=f"hn_{story.get('id')}",
            source="Hacker News",
            source_type="hackernews",
            title=story.get("title", "No Title"),
            content=story.get("text", "") or story.get("url", ""),
            timestamp=timestamp,
            url=story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}"),
            author=story.get("by"),
            tags=["tech", "hackernews"],
            metadata={"score": story.get("score"), "descendants": story.get("descendants")}
        )

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{self.API_BASE}/maxitem.json", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
