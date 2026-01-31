
import pytest
from hypothesis import given, strategies as st
from datetime import datetime

from src.models import ContentItem
from plugins.twitter_plugin import TwitterPlugin
from plugins.reddit_plugin import RedditPlugin
from plugins.hackernews_plugin import HackerNewsPlugin
from plugins.devto_plugin import DevToPlugin

class TestContentNormalization:

    @given(st.builds(ContentItem,
        id=st.text(min_size=1),
        source=st.text(min_size=1),
        source_type=st.text(min_size=1),
        title=st.text(min_size=1),
        url=st.text(min_size=1),
        tags=st.lists(st.text()),
        media_urls=st.lists(st.text()),
        metadata=st.dictionaries(st.text(), st.text())
    ))
    def test_content_item_schema_adherence(self, item):
        """
        Property 12: Content Normalization Consistency.
        Baseline check that ContentItem objects themselves preserve invariants.
        """
        assert isinstance(item.timestamp, datetime)
        assert isinstance(item.tags, list)
        assert isinstance(item.media_urls, list)
        assert isinstance(item.metadata, dict)

    def test_plugin_output_normalization(self):
        """
        Verify different plugins produce consistent output structures.
        """
        # Hackernews
        hn = HackerNewsPlugin()
        story = {
            "id": 12345, "title": "HN Story", "text": "Content",
            "time": 1600000000, "url": "http://example.com"
        }
        item = hn._parse_story(story)
        self._assert_normalized(item, "hackernews")

        # DevTo
        dt = DevToPlugin()
        article = {
            "id": 999, "title": "Dev Article", "description": "Desc",
            "published_at": "2023-01-01T12:00:00Z", "url": "http://dev.to/art",
            "tag_list": ["python", "code"]
        }
        item = dt._parse_article(article)
        self._assert_normalized(item, "devto")
        assert "python" in item.tags

    def _assert_normalized(self, item: ContentItem, expected_type: str):
        assert item.source_type == expected_type
        assert item.id != ""
        assert item.title != ""
        assert item.url.startswith("http")
        assert isinstance(item.timestamp, datetime)
