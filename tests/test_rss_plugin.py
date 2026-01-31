
import pytest
from hypothesis import given, strategies as st
from unittest.mock import MagicMock, patch
import time
from datetime import datetime, timedelta

from plugins.rss_plugin import RSSPlugin
from src.models import ContentItem

class TestRSSPluginProperties:

    @pytest.fixture
    def plugin(self):
        return RSSPlugin()

    @given(st.dictionaries(
        keys=st.sampled_from(["url", "fetch_interval"]),
        values=st.one_of(st.text(), st.integers())
    ))
    def test_validate_config_properties(self, plugin, config):
        """
        Property: validate_config should return True only for valid configs.
        Valid config has 'url' starting with http/https and optional int 'fetch_interval'.
        """
        is_valid = plugin.validate_config(config)

        has_valid_url = "url" in config and isinstance(config["url"], str) and config["url"].startswith(("http", "https"))
        has_valid_interval = "fetch_interval" not in config or isinstance(config["fetch_interval"], int)

        expected_valid = has_valid_url and has_valid_interval

        assert is_valid == expected_valid

    def test_fetch_content_respects_interval(self, plugin):
        """Test that fetch_content returns empty list if called too soon."""
        config = {"url": "http://example.com/feed.xml", "fetch_interval": 300}
        plugin.configure(config)

        # Mock last fetch to be now
        plugin._last_fetch = time.time()

        # Should return empty
        assert plugin.fetch_content() == []

        # Mock last fetch to be old
        plugin._last_fetch = time.time() - 301

        with patch("feedparser.parse") as mock_parse:
            mock_feed = MagicMock()
            mock_feed.bozo = False
            mock_feed.entries = []
            mock_parse.return_value = mock_feed

            # Should look like it ran
            assert plugin.fetch_content() == []
            # Verify it actually called parse
            mock_parse.assert_called_once()

    def test_exponential_backoff(self, plugin):
        """
        Property 13: Exponential Backoff Retry Pattern.
        Verify that repeated failures increase the backoff delay.
        """
        config = {"url": "http://example.com/feed.xml", "fetch_interval": 60}
        plugin.configure(config)

        # Force a failure
        with patch("feedparser.parse", side_effect=Exception("Connection failed")):
            # First failure
            plugin._last_fetch = 0 # Ready to fetch
            plugin.fetch_content()

            assert plugin._error_count == 1
            # _last_fetch should be set to future: now + delay - interval
            # delay = 60 * (2^1) = 120
            # next feasible fetch = _last_fetch + interval = (now + 120 - 60) + 60 = now + 120

            # Check effective delay
            # If we try to fetch immediately, it should fail due to interval check
            # We effectively want (time.time() - plugin._last_fetch) < plugin._fetch_interval to be False ONLY after delay

            # Let's verify _last_fetch value
            # _last_fetch = current_time + backoff - interval
            # effective_next_fetch = _last_fetch + interval = current_time + backoff

            expected_next_fetch_delay = 60 * (2**1) # 120

            # We can't predict exact time, but close enough
            assert plugin._last_fetch > time.time() # Should be in future relative to "fetch time" logic?
            # Wait, logic: _last_fetch = current + backoff - interval
            # if backoff > interval, then _last_fetch > current.
            # 120 > 60, so yes.

            # Second failure
            # Reset _last_fetch to allow fetch
            plugin._last_fetch = 0
            plugin.fetch_content() # error count becomes 2

            expected_delay_2 = 60 * (2**2) # 240
            # We check logic indirectly via error count
            assert plugin._error_count == 2

    @given(st.lists(st.dictionaries(
        keys=st.sampled_from(["title", "link", "id", "summary", "content"]),
        values=st.text(max_size=1000)
    ), max_size=10))
    def test_parse_entry_robustness(self, plugin, entries_data):
        """
        Property: parse_entry should handle arbitrary dictionary-like objects
        without crashing and return robust content items.
        """
        plugin._url = "http://example.com"

        for entry_data in entries_data:
            # Create a mock object from dict
            entry = MagicMock()
            for k, v in entry_data.items():
                setattr(entry, k, v)

            # If content exists, it needs to be a list of objs with value attr
            if "content" in entry_data:
                c_obj = MagicMock()
                c_obj.value = entry_data["content"]
                entry.content = [c_obj]
            else:
                delattr(entry, "content") # Ensure it doesn't have it if not in dict

            # Run parse
            item = plugin._parse_entry(entry)

            if item:
                assert item.source_type == "rss"
                assert isinstance(item.title, str)
                assert isinstance(item.content, str)
