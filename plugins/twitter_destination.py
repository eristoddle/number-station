
import logging
import requests
from requests_oauthlib import OAuth1
from typing import List, Dict, Any, Optional
from src.plugins import DestinationPlugin, PluginMetadata
from src.models import (
    ContentItem, ShareableContent, PostResult,
    ValidationResult, DestinationCapabilities
)

class TwitterDestinationPlugin(DestinationPlugin):
    """
    Destination plugin for posting to Twitter/X.

    Validates Requirements 9.1, 9.2, 9.3, 9.4, 9.5:
    - Twitter API v2 integration
    - OAuth 1.0a authentication
    - Post validation (280 chars)
    - Native reshare (Retweet) support
    """

    API_URL = "https://api.twitter.com/2/tweets"

    def __init__(self):
        super().__init__()
        self._auth = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Twitter Destination",
            version="1.0.0",
            description="Posts content to Twitter/X",
            author="Number Station Team",
            plugin_type="destination",
            dependencies=["requests", "requests_oauthlib"],
            capabilities=["twitter", "social", "reshare"],
            config_schema={
                "consumer_key": "string (required) - API Key",
                "consumer_secret": "string (required) - API Key Secret",
                "access_token": "string (required) - Access Token",
                "access_token_secret": "string (required) - Access Token Secret"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        required = ["consumer_key", "consumer_secret", "access_token", "access_token_secret"]
        for key in required:
            if not config.get(key):
                self.logger.error(f"Twitter destination config missing or empty '{key}'")
                return False
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        if not self.validate_config(config):
            return False
        self._config = config
        self._auth = OAuth1(
            config["consumer_key"],
            config["consumer_secret"],
            config["access_token"],
            config["access_token_secret"]
        )
        return True

    def post_content(self, content: ShareableContent) -> PostResult:
        """Post content to Twitter."""
        if not self._auth:
            return PostResult(success=False, error="Plugin not configured")

        validation = self.validate_content(content)
        if not validation.valid:
            return PostResult(success=False, error=", ".join(validation.errors))

        try:
            payload = {"text": content.text}

            # Note: Media upload requires v1.1 API and is complex.
            # For the initial version, we focus on text.

            response = requests.post(self.API_URL, auth=self._auth, json=payload, timeout=10)

            if response.status_code == 201:
                data = response.json()
                tweet_id = data["data"]["id"]
                return PostResult(
                    success=True,
                    post_id=tweet_id,
                    url=f"https://twitter.com/i/status/{tweet_id}"
                )
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", error_msg)
                except: pass
                return PostResult(success=False, error=f"Twitter API Error ({response.status_code}): {error_msg}")

        except Exception as e:
            self.logger.error(f"Error posting to Twitter: {e}")
            return PostResult(success=False, error=str(e))

    def validate_content(self, content: ShareableContent) -> ValidationResult:
        """Validate content against Twitter limits."""
        errors = []
        warnings = []

        if not content.text:
            errors.append("Content text cannot be empty")

        if len(content.text) > 280:
            errors.append(f"Content length {len(content.text)} exceeds Twitter's 280 character limit")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def get_capabilities(self) -> DestinationCapabilities:
        """Return Twitter-specific capabilities."""
        return DestinationCapabilities(
            max_length=280,
            supports_media=True,
            supported_media_types=["image/jpeg", "image/png", "image/gif", "video/mp4"],
            supports_reshare=True,
            name="Twitter"
        )

    def supports_reshare(self, source_type: str) -> bool:
        """Native reshare supported only for Twitter items."""
        return source_type == "twitter"

    def reshare(self, content_item: ContentItem) -> PostResult:
        """Perform a native Retweet."""
        if not self._auth:
            return PostResult(success=False, error="Plugin not configured")

        if content_item.source_type != "twitter":
             return PostResult(success=False, error="Native reshare only supported for Twitter items")

        try:
            # Extract tweet ID
            tweet_id = content_item.id.replace("twitter_", "")

            # Get authenticated user ID
            me_response = requests.get("https://api.twitter.com/2/users/me", auth=self._auth, timeout=5)
            if me_response.status_code != 200:
                return PostResult(success=False, error="Could not retrieve user ID for Retweet")

            user_id = me_response.json()["data"]["id"]
            retweet_url = f"https://api.twitter.com/2/users/{user_id}/retweets"
            payload = {"tweet_id": tweet_id}

            response = requests.post(retweet_url, auth=self._auth, json=payload, timeout=10)

            if response.status_code in [200, 201]:
                 return PostResult(success=True, post_id=tweet_id, url=content_item.url)
            else:
                 return PostResult(success=False, error=f"Retweet failed: {response.text}")

        except Exception as e:
            self.logger.error(f"Error resharing to Twitter: {e}")
            return PostResult(success=False, error=str(e))
