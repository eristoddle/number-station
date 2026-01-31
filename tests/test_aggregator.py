
import pytest
from hypothesis import given, strategies as st
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import time

from src.aggregator import ContentAggregator
from src.models import SourceConfiguration, SourceMetadata, ContentItem, PluginMetadata
from src.plugins import SourcePlugin

class TestAggregatorScheduling:

    @pytest.fixture
    def mock_components(self):
        pm = MagicMock()
        db = MagicMock()
        return pm, db

    @given(st.integers(min_value=0, max_value=10000))
    def test_scheduling_logic(self, timestamp_offset):
        """
        Property 10: Content Fetch Scheduling.
        Verify that fetch is only triggered when checks align with interval.
        """
        pm = MagicMock()
        db = MagicMock()
        aggregator = ContentAggregator(pm, db)

        # Setup Mock Plugin
        plugin = MagicMock(spec=SourcePlugin)
        plugin.metadata = PluginMetadata(
            name="TestPlugin", version="1", description="d", author="a",
            plugin_type="source", capabilities=["test"]
        )
        plugin.fetch_content.return_value = []
        plugin.configure.return_value = True
        pm.get_source_plugins.return_value = [plugin]

        # Setup Mock Config
        config = SourceConfiguration(
            name="test_source", source_type="test", url="http://x",
            fetch_interval=300, config={}
        )
        db.get_source_configs_by_type.return_value = [config]

        # Setup Metadata
        now = time.time()
        last_fetch = now - timestamp_offset

        metadata = SourceMetadata(
            source_id="test_source",
            last_fetch_attempt=datetime.fromtimestamp(last_fetch),
            last_fetch_success=None,
            last_item_count=0, total_items_fetched=0, error_count=0, consecutive_errors=0
        )
        db.get_source_metadata.return_value = metadata

        # Run
        # We assume if (now - last_fetch) >= interval, it triggers.
        # interval = 300.

        with patch("time.time", return_value=now):
            aggregator.fetch_all()

        due = (now - last_fetch) >= 300

        if due:
            # Should have fetched
            plugin.fetch_content.assert_called()
            # Metadata updated
            assert db.save_source_metadata.called
        else:
            # Should skip
            plugin.fetch_content.assert_not_called()

    def test_deduplication(self):
        """Test that existing items are not counted as new."""
        pm = MagicMock()
        db = MagicMock()
        aggregator = ContentAggregator(pm, db)

        # 1 New, 1 Existing
        item_new = ContentItem(id="new", source="s", source_type="t", title="t", content="c", timestamp=datetime.now(), url="u")
        item_old = ContentItem(id="old", source="s", source_type="t", title="t", content="c", timestamp=datetime.now(), url="u")

        # Plugin returns both
        plugin = MagicMock()
        plugin.metadata.capabilities = ["test"]
        plugin.fetch_content.return_value = [item_new, item_old]
        pm.get_source_plugins.return_value = [plugin]

        config = SourceConfiguration(name="s", source_type="test", fetch_interval=0) # force fetch
        db.get_source_configs_by_type.return_value = [config]
        db.get_source_metadata.return_value = None # Force fetch

        # DB mocks
        # get_content_item returns True for old, None for new
        def get_item(iid):
            if iid == "old": return item_old
            return None
        db.get_content_item.side_effect = get_item
        db.save_content_item.return_value = True

        results = aggregator.fetch_all()

        assert results["s"] == 1 # Only 1 new item counted
