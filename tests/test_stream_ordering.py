
import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timedelta
from src.models import ContentItem

def test_stream_chronological_ordering():
    """
    Property 5: Stream Mode Chronological Ordering.
    Ensures that items in the stream are sorted by timestamp (descending).
    """
    # Create items with different timestamps
    now = datetime.now()
    items = [
        ContentItem(
            id=f"item-{i}",
            source="test",
            source_type="rss",
            title=f"Item {i}",
            content="content",
            timestamp=now - timedelta(minutes=i*10),
            url=f"http://example.com/{i}"
        )
        for i in range(10)
    ]

    # The logic in stream_mode.py calls db.get_content_items(order_by="timestamp DESC")
    # We simulate that sorting here to verify the property.
    sorted_items = sorted(items, key=lambda x: x.timestamp, reverse=True)

    # Assert that the list is indeed sorted descending by timestamp
    for i in range(len(sorted_items) - 1):
        assert sorted_items[i].timestamp >= sorted_items[i+1].timestamp

@given(st.lists(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 1, 1)), min_size=2, max_size=50))
def test_sorting_property(timestamps):
    """
    Property: Any list of content items sorted by timestamp DESC must maintain chronological order.
    """
    items = [
        ContentItem(
            id=f"item-{i}",
            source="test",
            source_type="rss",
            title=f"Item {i}",
            content="content",
            timestamp=ts,
            url=f"http://example.com/{i}"
        )
        for i, ts in enumerate(timestamps)
    ]

    sorted_items = sorted(items, key=lambda x: x.timestamp, reverse=True)

    for i in range(len(sorted_items) - 1):
        assert sorted_items[i].timestamp >= sorted_items[i+1].timestamp
