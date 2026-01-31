
import pytest
import logging
from unittest.mock import MagicMock
from src.aggregator import ContentAggregator

def test_error_logging_continuity():
    """
    Property 4: Error Logging and Continuity.
    Ensures that failures in one source do not stop others.
    """
    db = MagicMock()
    pm = MagicMock()
    aggregator = ContentAggregator(pm, db)

    # Plugin 1 fails
    p1 = MagicMock()
    p1.metadata.capabilities = ["rss"]
    p1.configure.side_effect = Exception("P1 Crash")

    # Plugin 2 succeeds
    p2 = MagicMock()
    p2.metadata.capabilities = ["twitter"]
    p2.configure.return_value = True
    p2.fetch_content.return_value = []

    pm.get_source_plugins.return_value = [p1, p2]

    # Sources
    s1 = MagicMock(name="s1", source_type="rss", enabled=True, fetch_interval=0)
    s2 = MagicMock(name="s2", source_type="twitter", enabled=True, fetch_interval=0)

    # Mock DB get_source_configs_by_type
    def get_configs(stype):
        if stype == "rss": return [s1]
        if stype == "twitter": return [s2]
        return []

    db.get_source_configs_by_type.side_effect = get_configs
    db.get_source_metadata.return_value = None

    results = aggregator.fetch_all()

    # Plugin 2 should still have been called despite Plugin 1 failing
    p2.fetch_content.assert_called()
    assert "s2" in results # or at least processed
