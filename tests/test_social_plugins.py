
import pytest
from hypothesis import given, strategies as st
from unittest.mock import MagicMock, patch
import time
from datetime import datetime
import json

from plugins.twitter_plugin import TwitterPlugin
from plugins.reddit_plugin import RedditPlugin
from src.models import ContentItem

class TestSocialPlugins:

    @pytest.fixture
    def twitter(self):
        plugin = TwitterPlugin()
        plugin.configure({"bearer_token": "test", "query": "test"})
        return plugin

    @pytest.fixture
    def reddit(self):
        plugin = RedditPlugin()
        plugin.configure({"user_agent": "test", "subreddits": ["test"]})
        return plugin

    # --- Twitter Tests ---

    @given(st.lists(st.dictionaries(
        keys=st.sampled_from(["id", "text", "author_id", "created_at"]),
        values=st.text()
    )))
    def test_twitter_parsing_robustness(self, twitter, tweets_data):
        """Property: Twitter plugin should parse arbitrary tweet objects robustly."""
        # Construct API response format
        data = {"data": [{"id": "1", "text": "default"} for _ in range(len(tweets_data))]}

        # Override with generated data
        for i, tweet_data in enumerate(tweets_data):
            if "id" not in tweet_data: tweet_data["id"] = f"id_{i}"
            if "text" not in tweet_data: tweet_data["text"] = "text"
            data["data"][i] = tweet_data

        items = twitter._parse_response(data)
        assert len(items) == len(data["data"])
        for item in items:
            assert isinstance(item, ContentItem)
            assert item.source_type == "twitter"

    def test_twitter_rate_limit_headers(self, twitter):
        """Test that Twitter plugin respects rate limit headers."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}
            mock_response.headers = {
                "x-rate-limit-remaining": "0",
                "x-rate-limit-reset": str(int(time.time() + 100))
            }
            mock_get.return_value = mock_response

            # First call exhausts limit
            twitter.fetch_content()

            assert twitter._rate_limit_reset > time.time()

            # Second call should be blocked locally
            mock_get.reset_mock()
            items = twitter.fetch_content()
            assert items == []
            mock_get.assert_not_called()

    # --- Reddit Tests ---

    @given(st.lists(st.dictionaries(
        keys=st.sampled_from(["id", "title", "selftext", "url", "author", "created_utc", "permalink"]),
        values=st.one_of(st.text(), st.floats())
    )))
    def test_reddit_parsing_robustness(self, reddit, posts_data):
        """Property: Reddit plugin should parse arbitrary post objects robustly."""
        # Construct API response format
        children = []
        for i, post_data in enumerate(posts_data):
            # Ensure minimal required fields for logic not to skip?
            # actual code: if not post: continue.
            # post_id = post.get("id")
            # All gets have defaults except maybe types?
            # created_utc expects float/int for timestamp
            if "created_utc" in post_data and isinstance(post_data["created_utc"], str):
                post_data["created_utc"] = 100000.0

            children.append({"data": post_data})

        data = {"data": {"children": children}}
        items = reddit._parse_response(data, "test")

        # Should parse all that have valid structure
        # Implementation is very permissible
        assert len(items) == len(posts_data)
        for item in items:
            assert isinstance(item, ContentItem)
            assert item.source_type == "reddit"

    def test_reddit_auth_flow(self, reddit):
        """Test the auth flow toggles."""
        # Unauthenticated
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"children": []}}
            mock_get.return_value = mock_response

            reddit.fetch_content()

            # Should use public url
            args, _ = mock_get.call_args
            assert "www.reddit.com/r/test/new.json" in args[0]

        # Authenticated
        reddit.configure({
            "client_id": "cid", "client_secret": "cs",
            "user_agent": "ua", "subreddits": ["test"]
        })

        with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
            # Mock Auth
            mock_auth_resp = MagicMock()
            mock_auth_resp.status_code = 200
            mock_auth_resp.json.return_value = {"access_token": "token", "expires_in": 3600}
            mock_post.return_value = mock_auth_resp

            # Mock Fetch
            mock_fetch_resp = MagicMock()
            mock_fetch_resp.status_code = 200
            mock_fetch_resp.json.return_value = {"data": {"children": []}}
            mock_get.return_value = mock_fetch_resp

            reddit.fetch_content()

            # Should use oauth url
            args, _ = mock_get.call_args
            assert "oauth.reddit.com/r/test/new" in args[0]
            assert "Authorization" in _["headers"]
