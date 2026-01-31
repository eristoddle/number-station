
import logging
import time
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.plugins import SourcePlugin, PluginMetadata
from src.models import ContentItem

class TwitterPlugin(SourcePlugin):
    """
    Plugin for fetching content from Twitter/X using API v2.

    Validates Requirements 4.1, 4.4, 4.6, 4.7.
    """

    API_URL = "https://api.twitter.com/2"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config = {}
        self._bearer_token = None
        self._query = None
        self._fetch_interval = 300
        self._last_fetch = 0
        self._rate_limit_reset = 0

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Twitter Source",
            version="1.0.0",
            description="Fetches tweets based on search queries",
            author="Number Station Team",
            plugin_type="source",
            dependencies=["requests"],
            capabilities=["twitter", "social"],
            config_schema={
                "bearer_token": "string (required) - API Bearer Token",
                "query": "string (required) - Search query",
                "fetch_interval": "integer (optional, default=300)",
                "max_results": "integer (optional, default=10)"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the plugin configuration."""
        if "bearer_token" not in config:
            self.logger.error("Twitter plugin config missing 'bearer_token'")
            return False

        if "query" not in config:
            self.logger.error("Twitter plugin config missing 'query'")
            return False

        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the plugin."""
        if not self.validate_config(config):
            return False

        self._config = config
        self._bearer_token = config["bearer_token"]
        self._query = config["query"]
        self._fetch_interval = config.get("fetch_interval", 300)
        self._max_results = min(config.get("max_results", 10), 100)
        return True

    def fetch_content(self) -> List[ContentItem]:
        """Fetch tweets matching the query."""
        if not self._bearer_token:
            return []

        # Check rate limit
        current_time = time.time()
        if current_time < self._rate_limit_reset:
            self.logger.warning(f"Twitter rate limit active. Resets in {int(self._rate_limit_reset - current_time)}s")
            return []

        # Check interval
        if current_time - self._last_fetch < self._fetch_interval:
            return []

        try:
            headers = {"Authorization": f"Bearer {self._bearer_token}"}
            params = {
                "query": self._query,
                "max_results": self._max_results,
                "tweet.fields": "created_at,author_id,entities,lang",
                "expansions": "author_id,attachments.media_keys",
                "media.fields": "url,preview_image_url"
            }

            url = f"{self.API_URL}/tweets/search/recent"
            self.logger.info(f"Fetching tweets for query: {self._query}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            # Handle rate limiting headers
            remaining = response.headers.get("x-rate-limit-remaining")
            reset = response.headers.get("x-rate-limit-reset")

            if remaining and int(remaining) == 0 and reset:
                self._rate_limit_reset = int(reset)

            if response.status_code == 429:
                self.logger.warning("Twitter rate limit exceeded")
                if reset:
                     self._rate_limit_reset = int(reset)
                else:
                     self._rate_limit_reset = current_time + 900 # Default 15 min
                return []

            response.raise_for_status()

            data = response.json()
            return self._parse_response(data)

        except Exception as e:
            self.logger.error(f"Error fetching tweets: {e}")
            return []
        finally:
            self._last_fetch = time.time()

    def _parse_response(self, data: Dict[str, Any]) -> List[ContentItem]:
        """Parse Twitter API response."""
        items = []
        if "data" not in data:
            return []

        # Create map of users for author expansion
        users = {}
        if "includes" in data and "users" in data["includes"]:
            for u in data["includes"]["users"]:
                users[u["id"]] = u

        # Create map of media
        media_map = {}
        if "includes" in data and "media" in data["includes"]:
            for m in data["includes"]["media"]:
                 if "media_key" in m:
                     media_map[m["media_key"]] = m.get("url", m.get("preview_image_url"))

        for tweet in data["data"]:
            try:
                tweet_id = tweet["id"]
                text = tweet["text"]
                author_id = tweet.get("author_id")
                created_at_str = tweet.get("created_at")

                # Resolve author
                author_name = "Unknown"
                if author_id and author_id in users:
                    author_name = f"@{users[author_id]['username']}"

                # Resolve timestamp
                timestamp = datetime.now()
                if created_at_str:
                    try:
                        timestamp = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                # Resolve media
                media_urls = []
                if "attachments" in tweet and "media_keys" in tweet["attachments"]:
                    for key in tweet["attachments"]["media_keys"]:
                        if key in media_map and media_map[key]:
                            media_urls.append(media_map[key])

                # Tags (hashtags)
                tags = []
                if "entities" in tweet and "hashtags" in tweet["entities"]:
                    tags = [t["tag"] for t in tweet["entities"]["hashtags"]]

                item = ContentItem(
                    id=f"twitter_{tweet_id}",
                    source="twitter",
                    source_type="twitter",
                    title=f"Tweet by {author_name}",
                    content=text,
                    timestamp=timestamp,
                    url=f"https://twitter.com/{users.get(author_id, {}).get('username', 'user')}/status/{tweet_id}",
                    author=author_name,
                    tags=tags,
                    media_urls=media_urls,
                    metadata={"raw_tweet": json.dumps(tweet)}
                )
                items.append(item)
            except Exception as e:
                self.logger.error(f"Error parsing tweet: {e}")
                continue

        return items

    def test_connection(self) -> bool:
        """Test connection to Twitter API."""
        if not self._bearer_token:
            return False

        # Note: 'recent' search doesn't support HEAD or lightweight auth check easily without valid query.
        # But we can try a simple query or check /2/me if we had user context.
        # With app-only token, maybe we just verify we don't get 401.
        try:
            headers = {"Authorization": f"Bearer {self._bearer_token}"}
            # Use a dummy request that should define validity of token
            # Actually, without query, this endpoint returns 400.
            # 401 means invalid token.
            url = f"{self.API_URL}/tweets/search/recent?query=test&max_results=10"
            response = requests.get(url, headers=headers, timeout=5)

            return response.status_code == 200
        except Exception:
            return False
