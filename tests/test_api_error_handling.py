
import pytest
from unittest.mock import MagicMock, patch
import requests

from plugins.twitter_plugin import TwitterPlugin
from plugins.reddit_plugin import RedditPlugin
from plugins.hackernews_plugin import HackerNewsPlugin
from plugins.devto_plugin import DevToPlugin
from plugins.web_scraper_plugin import WebScraperPlugin
from plugins.rss_plugin import RSSPlugin

class TestAPIErrorHandling:

    @pytest.fixture(params=[
        TwitterPlugin, RedditPlugin, HackerNewsPlugin,
        DevToPlugin, WebScraperPlugin, RSSPlugin
    ])
    def plugin(self, request):
        p = request.param()
        # Minimal config to pass checks
        configs = {
            TwitterPlugin: {"bearer_token": "abc", "query": "q"},
            RedditPlugin: {"subreddits": ["test"], "user_agent": "ua"},
            HackerNewsPlugin: {},
            DevToPlugin: {},
            WebScraperPlugin: {"url": "http://x", "content_selector": "div"},
            RSSPlugin: {"url": "http://x"}
        }
        p.configure(configs.get(request.param, {}))
        return p

    def test_network_failure_handling(self, plugin):
        """
        Property 17: API Error Handling Clarity.
        Ensure network failures (timeout, connection abort) are caught and do not crash the app.
        """
        # Target usually requests.get, but rss uses feedparser
        # We need to patch where appropriate.

        target = "requests.get"
        if isinstance(plugin, RSSPlugin):
            target = "feedparser.parse"

        with patch(target, side_effect=Exception("Connection Reset")):
            # Reset fetch timer to force execution
            plugin._last_fetch = 0

            try:
                results = plugin.fetch_content()
                assert results == []
            except Exception as e:
                pytest.fail(f"Plugin {plugin.__class__.__name__} raised exception on network error: {e}")

    def test_http_error_handling(self, plugin):
        """
        Property 17: HTTP 500/404 errors should be handled gracefully.
        """
        if isinstance(plugin, RSSPlugin):
            return # Feedparser handles http errors differently (bozo), tested elsewhere

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
            mock_get.return_value = mock_resp

            plugin._last_fetch = 0

            try:
                results = plugin.fetch_content()
                assert results == []
            except Exception as e:
                 pytest.fail(f"Plugin {plugin.__class__.__name__} raised exception on HTTP error: {e}")
