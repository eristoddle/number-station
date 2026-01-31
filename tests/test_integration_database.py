#!/usr/bin/env python3
"""
Integration tests for Number Station database functionality.
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from src.database import get_database, DatabaseManager
from src.models import ContentItem, UserPreferences
from src.migrations import run_migrations, get_migration_status


def test_global_database_instance():
    """Test that global database instance works correctly."""
    # This test uses the default database path
    db = get_database()
    assert isinstance(db, DatabaseManager)

    # Test basic functionality
    prefs = UserPreferences(ui_mode="stream", theme="default")
    assert db.save_user_preferences(prefs) is True

    retrieved = db.get_user_preferences()
    assert retrieved.ui_mode == "stream"
    assert retrieved.theme == "default"


def test_database_with_real_content():
    """Test database with realistic content data."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = DatabaseManager(db_path)

        # Create realistic content items
        items = [
            ContentItem(
                id="rss-techcrunch-1",
                source="TechCrunch",
                source_type="rss",
                title="AI Startup Raises $50M Series A",
                content="A new AI startup focused on natural language processing has raised $50 million...",
                author="Sarah Johnson",
                timestamp=datetime(2023, 12, 1, 10, 30, 0),
                url="https://techcrunch.com/ai-startup-raises-50m",
                tags=["ai", "startup", "funding"],
                media_urls=["https://techcrunch.com/images/ai-startup.jpg"],
                metadata={"category": "technology", "word_count": 850}
            ),
            ContentItem(
                id="reddit-programming-1",
                source="r/programming",
                source_type="reddit",
                title="What's your favorite Python library?",
                content="I'm looking for recommendations for Python libraries that have made your development work easier...",
                author="pythondev123",
                timestamp=datetime(2023, 12, 1, 14, 15, 0),
                url="https://reddit.com/r/programming/comments/abc123",
                tags=["python", "libraries", "discussion"],
                media_urls=[],
                metadata={"upvotes": 42, "comments": 18}
            ),
            ContentItem(
                id="twitter-elonmusk-1",
                source="@elonmusk",
                source_type="twitter",
                title="Mars mission update",
                content="Exciting progress on the Mars mission! New rocket tests completed successfully. 🚀",
                author="Elon Musk",
                timestamp=datetime(2023, 12, 1, 16, 45, 0),
                url="https://twitter.com/elonmusk/status/123456789",
                tags=["mars", "spacex", "rocket"],
                media_urls=["https://pbs.twimg.com/media/rocket-test.jpg"],
                metadata={"retweets": 1250, "likes": 5430}
            )
        ]

        # Save all items
        for item in items:
            assert db.save_content_item(item) is True

        # Test retrieval and filtering
        all_items = db.get_content_items()
        assert len(all_items) == 3

        # Test filtering by source type
        rss_items = db.get_content_items(source_type="rss")
        assert len(rss_items) == 1
        assert rss_items[0].source == "TechCrunch"

        reddit_items = db.get_content_items(source_type="reddit")
        assert len(reddit_items) == 1
        assert reddit_items[0].source == "r/programming"

        twitter_items = db.get_content_items(source_type="twitter")
        assert len(twitter_items) == 1
        assert twitter_items[0].source == "@elonmusk"

        # Test ordering (should be by timestamp DESC by default)
        ordered_items = db.get_content_items()
        assert ordered_items[0].id == "twitter-elonmusk-1"  # Latest timestamp
        assert ordered_items[1].id == "reddit-programming-1"
        assert ordered_items[2].id == "rss-techcrunch-1"  # Earliest timestamp

        # Test pagination
        page1 = db.get_content_items(limit=2, offset=0)
        assert len(page1) == 2

        page2 = db.get_content_items(limit=2, offset=2)
        assert len(page2) == 1

        # Test database stats
        stats = db.get_database_stats()
        assert stats['content_items'] == 3

    finally:
        os.unlink(db_path)


def test_migration_integration():
    """Test migration system integration."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        # Create database and run migrations
        db = DatabaseManager(db_path)
        success = run_migrations(db)
        assert success is True

        # Check migration status
        status = get_migration_status(db)
        assert status['applied_count'] >= 1
        assert "001" in status['applied_versions']

        # Verify database still works after migrations
        item = ContentItem(
            id="migration-test",
            source="test",
            source_type="test",
            title="Migration Test",
            content="Testing after migration",
            timestamp=datetime.now(),
            url="https://example.com"
        )

        assert db.save_content_item(item) is True
        retrieved = db.get_content_item("migration-test")
        assert retrieved is not None
        assert retrieved.title == "Migration Test"

    finally:
        os.unlink(db_path)


def test_database_error_handling():
    """Test database error handling."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = DatabaseManager(db_path)

        # Test retrieving non-existent item
        item = db.get_content_item("nonexistent")
        assert item is None

        # Test deleting non-existent item
        result = db.delete_content_item("nonexistent")
        assert result is False

        # Test retrieving non-existent plugin config
        config = db.get_plugin_config("nonexistent")
        assert config is None

        # Test retrieving non-existent source config
        source = db.get_source_config("nonexistent")
        assert source is None

    finally:
        os.unlink(db_path)


def test_content_cleanup():
    """Test content cleanup functionality."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = DatabaseManager(db_path)

        # Create some test content
        for i in range(5):
            item = ContentItem(
                id=f"cleanup-test-{i}",
                source="test",
                source_type="test",
                title=f"Cleanup Test {i}",
                content="Test content",
                timestamp=datetime.now(),
                url=f"https://example.com/{i}"
            )
            db.save_content_item(item)

        # Verify items exist
        items = db.get_content_items()
        assert len(items) == 5

        # Test cleanup (should not delete anything since items are new)
        deleted = db.cleanup_old_content(days=30)
        assert deleted == 0

        # Verify items still exist
        items = db.get_content_items()
        assert len(items) == 5

    finally:
        os.unlink(db_path)