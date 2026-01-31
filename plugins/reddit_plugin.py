
import logging
import time
import requests
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.plugins import SourcePlugin, PluginMetadata
from src.models import ContentItem

class RedditPlugin(SourcePlugin):
    """
    Plugin for fetching content from Reddit using API.

    Validates Requirements 4.2, 4.4, 4.6.
    """

    AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    API_URL = "https://oauth.reddit.com"
    PUBLIC_URL = "https://www.reddit.com"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config = {}
        self._client_id = None
        self._client_secret = None
        self._user_agent = "NumberStation/1.0"
        self._subreddits = []
        self._access_token = None
        self._token_expiry = 0
        self._fetch_interval = 300
        self._last_fetch = 0

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Reddit Source",
            version="1.0.0",
            description="Fetches posts from specified subreddits",
            author="Number Station Team",
            plugin_type="source",
            dependencies=["requests"],
            capabilities=["reddit", "social"],
            config_schema={
                "client_id": "string (optional) - App Client ID",
                "client_secret": "string (optional) - App Client Secret",
                "user_agent": "string (required) - Unqiue User Agent",
                "subreddits": "list<string> (required) - List of subreddits",
                "fetch_interval": "integer (optional, default=300)"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate the plugin configuration."""
        if "subreddits" not in config or not isinstance(config["subreddits"], list):
            self.logger.error("Reddit plugin config missing 'subreddits' list")
            return False

        if "user_agent" not in config:
             self.logger.warning("Reddit plugin usually requires custom 'user_agent'")

        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the plugin."""
        if not self.validate_config(config):
            return False

        self._config = config
        self._client_id = config.get("client_id")
        self._client_secret = config.get("client_secret")
        self._user_agent = config.get("user_agent", "NumberStation/1.0")
        self._subreddits = config["subreddits"]
        self._fetch_interval = config.get("fetch_interval", 300)
        return True

    def _authenticate(self) -> bool:
        """Obtain OAuth access token."""
        if not self._client_id or not self._client_secret:
            return False

        if time.time() < self._token_expiry:
            return True

        try:
            auth = requests.auth.HTTPBasicAuth(self._client_id, self._client_secret)
            data = {"grant_type": "client_credentials"}
            headers = {"User-Agent": self._user_agent}

            response = requests.post(self.AUTH_URL, auth=auth, data=data, headers=headers, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]
            self._token_expiry = time.time() + token_data.get("expires_in", 3600) - 60
            return True
        except Exception as e:
            self.logger.error(f"Reddit authentication failed: {e}")
            return False

    def fetch_content(self) -> List[ContentItem]:
        """Fetch posts from subreddits."""
        if not self._subreddits:
            return []

        if time.time() - self._last_fetch < self._fetch_interval:
            return []

        authenticated = self._authenticate()
        items = []

        for subreddit in self._subreddits:
            try:
                if authenticated:
                    url = f"{self.API_URL}/r/{subreddit}/new"
                    headers = {
                        "Authorization": f"bearer {self._access_token}",
                        "User-Agent": self._user_agent
                    }
                else:
                    # Fallback to public JSON (rate limited heavily)
                    url = f"{self.PUBLIC_URL}/r/{subreddit}/new.json"
                    headers = {"User-Agent": self._user_agent}

                self.logger.info(f"Fetching Reddit posts for r/{subreddit}")
                response = requests.get(url, headers=headers, params={"limit": 10}, timeout=10)

                if response.status_code == 429:
                     self.logger.warning("Reddit rate limit exceeded")
                     break # Stop fetching for now

                response.raise_for_status()
                data = response.json()

                subreddit_items = self._parse_response(data, subreddit)
                items.extend(subreddit_items)

            except Exception as e:
                self.logger.error(f"Error fetching r/{subreddit}: {e}")

        self._last_fetch = time.time()
        return items

    def _parse_response(self, data: Dict[str, Any], subreddit: str) -> List[ContentItem]:
        """Parse Reddit API response."""
        items = []
        try:
            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                if not post:
                    continue

                post_id = post.get("id")
                title = post.get("title", "No Title")
                selftext = post.get("selftext", "")
                url = post.get("url", "")
                permalink = f"https://reddit.com{post.get('permalink')}"
                author = post.get("author", "unknown")
                created_utc = post.get("created_utc", time.time())

                tags = [subreddit, "reddit"]
                if post.get("over_18"):
                    tags.append("nsfw")
                if post.get("spoiler"):
                    tags.append("spoiler")

                media_urls = []
                # Check for images
                if "preview" in post and "images" in post["preview"]:
                    for img in post["preview"]["images"]:
                        if "source" in img:
                            media_urls.append(img["source"]["url"].replace("&amp;", "&"))

                # Check for direct image link not in preview
                if url.endswith(('.jpg', '.png', '.gif')) and url not in media_urls:
                    media_urls.append(url)

                content = selftext
                if not content and not post.get("is_self"):
                     content = f"[Link Post] {url}"

                item = ContentItem(
                    id=f"reddit_{post_id}",
                    source=f"r/{subreddit}",
                    source_type="reddit",
                    title=title,
                    content=content,
                    timestamp=datetime.fromtimestamp(created_utc),
                    url=permalink,
                    author=author,
                    tags=tags,
                    media_urls=media_urls,
                    metadata={"upvotes": post.get("ups"), "comments": post.get("num_comments")}
                )
                items.append(item)
        except Exception as e:
             self.logger.error(f"Error parsing reddit response: {e}")

        return items

    def test_connection(self) -> bool:
        """Test connection to Reddit."""
        # Try fetching a public sub JSON or use auth check
        try:
             # Just check if we can reach reddit
             headers = {"User-Agent": self._user_agent}
             response = requests.head("https://www.reddit.com/r/all/about.json", headers=headers, timeout=5)
             return response.status_code == 200
        except Exception:
             return False
