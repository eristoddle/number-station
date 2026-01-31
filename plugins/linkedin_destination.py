
import logging
import requests
from typing import List, Dict, Any, Optional
from src.plugins import DestinationPlugin, PluginMetadata
from src.models import (
    ContentItem, ShareableContent, PostResult,
    ValidationResult, DestinationCapabilities
)

class LinkedInDestinationPlugin(DestinationPlugin):
    """
    Destination plugin for posting to LinkedIn.

    Validates Requirements 10.1, 10.2, 10.3, 10.4:
    - LinkedIn UGC Post API integration
    - OAuth 2.0 authentication
    - Post validation (3000 chars)
    """

    API_URL = "https://api.linkedin.com/v2/ugcPosts"

    def __init__(self):
        super().__init__()
        self._access_token = None
        self._person_id = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="LinkedIn Destination",
            version="1.0.0",
            description="Posts content to LinkedIn",
            author="Number Station Team",
            plugin_type="destination",
            dependencies=["requests"],
            capabilities=["linkedin", "social"],
            config_schema={
                "access_token": "string (required) - OAuth 2.0 Access Token",
                "person_id": "string (optional) - LinkedIn Person ID (urn:li:person:ID)"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        if not config.get("access_token"):
            self.logger.error("LinkedIn destination config missing 'access_token'")
            return False
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        if not self.validate_config(config):
            return False
        self._config = config
        self._access_token = config["access_token"]
        self._person_id = config.get("person_id")
        return True

    def _get_person_id(self) -> Optional[str]:
        """Fetch the authenticated user's URN."""
        if self._person_id:
            return self._person_id

        try:
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = requests.get("https://api.linkedin.com/v2/me", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self._person_id = f"urn:li:person:{data['id']}"
                return self._person_id
            else:
                self.logger.error(f"Failed to fetch LinkedIn person ID: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching LinkedIn profile: {e}")
            return None

    def post_content(self, content: ShareableContent) -> PostResult:
        """Post content to LinkedIn feed."""
        if not self._access_token:
            return PostResult(success=False, error="Plugin not configured")

        person_id = self._get_person_id()
        if not person_id:
            return PostResult(success=False, error="Could not determine LinkedIn Person URN")

        validation = self.validate_content(content)
        if not validation.valid:
            return PostResult(success=False, error=", ".join(validation.errors))

        try:
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json"
            }

            payload = {
                "author": person_id,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content.text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }

            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=10)

            if response.status_code == 201:
                data = response.json()
                post_id = data.get("id")
                return PostResult(
                    success=True,
                    post_id=post_id,
                    url=f"https://www.linkedin.com/feed/update/{post_id}" if post_id else None
                )
            else:
                return PostResult(success=False, error=f"LinkedIn API Error ({response.status_code}): {response.text}")

        except Exception as e:
            self.logger.error(f"Error posting to LinkedIn: {e}")
            return PostResult(success=False, error=str(e))

    def validate_content(self, content: ShareableContent) -> ValidationResult:
        """Validate content against LinkedIn limits."""
        errors = []

        if not content.text:
            errors.append("Content text cannot be empty")

        if len(content.text) > 3000:
            errors.append(f"Content length {len(content.text)} exceeds LinkedIn's 3000 character limit")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )

    def get_capabilities(self) -> DestinationCapabilities:
        """Return LinkedIn-specific capabilities."""
        return DestinationCapabilities(
            max_length=3000,
            supports_media=True,
            supported_media_types=["image/jpeg", "image/png", "video/mp4"],
            supports_reshare=False,
            name="LinkedIn"
        )

    def supports_reshare(self, source_type: str) -> bool:
        """Native reshare not supported via UGC API."""
        return False

    def reshare(self, content_item: ContentItem) -> PostResult:
        """Reshare is not supported."""
        return PostResult(success=False, error="Native reshare not supported for LinkedIn")
