#!/usr/bin/env python3
"""
Tests for Number Station database functionality.
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from src.database import DatabaseManager
from src.models import ContentItem, UserPreferences, PluginMetadata, SourceConfiguration
from src.migrations import MigrationManager, run_migrations


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        db_manager = DatabaseManager(db_path)
        yield db_manager

        # Cleanup
        os.unlink(db_path)

    def test_database_initialization(self, temp_db):
        """Test that database initializes correctly."""
        # Database should be created and tables should exist
        with temp_db.get_connection() as conn:
            cursor = conn.cursor()

            # Check that all required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            expected_tables = {
                'content_items',
                'plugin_configs',
                'user_preferences',
                'source_configurations',
                'plugin_metadata'
            }

            assert expected_tables.issubset(tables)

    def test_content_item_operations(self, temp_db):
        """Test ContentItem CRUD operations."""
        # Create a test content item
        item = ContentItem(
            id="test-1",
            source="test-source",
            source_type="rss",
            title="Test Article",
            content="This is test content",
            author="Test Author",
            timestamp=datetime.now(),
            url="https://example.com/test",
            tags=["test", "article"],
            media_urls=["https://example.com/image.jpg"],
            metadata={"category": "tech"}
        )

        # Test save
        assert temp_db.save_content_item(item) is True

        # Test retrieve
        retrieved = temp_db.get_content_item("test-1")
        assert retrieved is not None
        assert retrieved.id == item.id
        assert retrieved.title == item.title
        assert retrieved.tags == item.tags
        assert retrieved.metadata == item.metadata

        # Test list
        items = temp_db.get_content_items()
        assert len(items) == 1
        assert items[0].id == item.id

        # Test filter by source
        items = temp_db.get_content_items(source="test-source")
        assert len(items) == 1

        items = temp_db.get_content_items(source="nonexistent")
        assert len(items) == 0

        # Test delete
        assert temp_db.delete_content_item("test-1") is True
        assert temp_db.get_content_item("test-1") is None

    def test_user_preferences_operations(self, temp_db):
        """Test UserPreferences operations."""
        # Create test preferences
        prefs = UserPreferences(
            ui_mode="board",
            theme="dark",
            update_interval=600,
            auto_refresh=False
        )

        # Test save
        assert temp_db.save_user_preferences(prefs) is True

        # Test retrieve
        retrieved = temp_db.get_user_preferences()
        assert retrieved.ui_mode == "board"
        assert retrieved.theme == "dark"
        assert retrieved.update_interval == 600
        assert retrieved.auto_refresh is False

    def test_plugin_config_operations(self, temp_db):
        """Test plugin configuration operations."""
        config_data = {
            "api_key": "test-key",
            "endpoint": "https://api.example.com",
            "rate_limit": 100
        }

        # Test save
        assert temp_db.save_plugin_config("test-plugin", config_data, enabled=True) is True

        # Test retrieve
        retrieved = temp_db.get_plugin_config("test-plugin")
        assert retrieved is not None
        assert retrieved['config'] == config_data
        assert retrieved['enabled'] is True

        # Test get all configs
        all_configs = temp_db.get_all_plugin_configs()
        assert "test-plugin" in all_configs
        assert all_configs["test-plugin"]['config'] == config_data

    def test_source_config_operations(self, temp_db):
        """Test SourceConfiguration operations."""
        source_config = SourceConfiguration(
            name="test-rss",
            source_type="rss",
            url="https://example.com/feed.xml",
            enabled=True,
            fetch_interval=300,
            tags=["news", "tech"],
            config={"user_agent": "NumberStation/1.0"}
        )

        # Test save
        assert temp_db.save_source_config(source_config) is True

        # Test retrieve
        retrieved = temp_db.get_source_config("test-rss")
        assert retrieved is not None
        assert retrieved.name == source_config.name
        assert retrieved.url == source_config.url
        assert retrieved.tags == source_config.tags

        # Test get by type
        rss_configs = temp_db.get_source_configs_by_type("rss")
        assert len(rss_configs) == 1
        assert rss_configs[0].name == "test-rss"

        # Test delete
        assert temp_db.delete_source_config("test-rss") is True
        assert temp_db.get_source_config("test-rss") is None

    def test_plugin_metadata_operations(self, temp_db):
        """Test PluginMetadata operations."""
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test Author",
            plugin_type="source",
            enabled=True,
            dependencies=["requests"],
            capabilities=["rss", "json"],
            config_schema={"type": "object", "properties": {"url": {"type": "string"}}}
        )

        # Test save
        assert temp_db.save_plugin_metadata(metadata) is True

        # Test retrieve
        retrieved = temp_db.get_plugin_metadata("test-plugin")
        assert retrieved is not None
        assert retrieved.name == metadata.name
        assert retrieved.version == metadata.version
        assert retrieved.dependencies == metadata.dependencies

        # Test get by type
        source_plugins = temp_db.get_plugins_by_type("source")
        assert len(source_plugins) == 1
        assert source_plugins[0].name == "test-plugin"

    def test_database_stats(self, temp_db):
        """Test database statistics."""
        # Add some test data
        item = ContentItem(
            id="stats-test",
            source="test",
            source_type="rss",
            title="Stats Test",
            content="Test content",
            timestamp=datetime.now(),
            url="https://example.com"
        )
        temp_db.save_content_item(item)

        prefs = UserPreferences()
        temp_db.save_user_preferences(prefs)

        # Get stats
        stats = temp_db.get_database_stats()
        assert stats['content_items'] >= 1
        assert stats['user_preferences'] >= 1


class TestMigrationManager:
    """Test MigrationManager functionality."""

    @pytest.fixture
    def temp_db_with_migrations(self):
        """Create a temporary database with migration manager."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        db_manager = DatabaseManager(db_path)
        migration_manager = MigrationManager(db_manager)

        yield db_manager, migration_manager

        # Cleanup
        os.unlink(db_path)

    def test_migration_table_creation(self, temp_db_with_migrations):
        """Test that migration table is created."""
        db_manager, migration_manager = temp_db_with_migrations

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
            assert cursor.fetchone() is not None

    def test_migration_status(self, temp_db_with_migrations):
        """Test migration status reporting."""
        db_manager, migration_manager = temp_db_with_migrations

        status = migration_manager.get_migration_status()
        assert 'applied_count' in status
        assert 'pending_count' in status
        assert 'applied_versions' in status
        assert 'pending_versions' in status

    def test_run_migrations(self, temp_db_with_migrations):
        """Test running migrations."""
        db_manager, migration_manager = temp_db_with_migrations

        # Run migrations
        success = migration_manager.migrate_up()
        assert success is True

        # Check that migration was recorded
        applied = migration_manager.get_applied_migrations()
        assert "001" in applied


def test_content_item_validation():
    """Test ContentItem validation."""
    # Test valid item
    item = ContentItem(
        id="valid-1",
        source="test",
        source_type="rss",
        title="Valid Item",
        content="Content",
        timestamp=datetime.now(),
        url="https://example.com"
    )
    assert item.id == "valid-1"

    # Test invalid items
    with pytest.raises(ValueError):
        ContentItem(
            id="",  # Empty ID should fail
            source="test",
            source_type="rss",
            title="Invalid",
            content="Content",
            timestamp=datetime.now(),
            url="https://example.com"
        )

    with pytest.raises(ValueError):
        ContentItem(
            id="test",
            source="",  # Empty source should fail
            source_type="rss",
            title="Invalid",
            content="Content",
            timestamp=datetime.now(),
            url="https://example.com"
        )


def test_content_item_serialization():
    """Test ContentItem to_dict and from_dict methods."""
    original = ContentItem(
        id="serialize-test",
        source="test-source",
        source_type="rss",
        title="Serialization Test",
        content="Test content",
        author="Test Author",
        timestamp=datetime(2023, 1, 1, 12, 0, 0),
        url="https://example.com/test",
        tags=["test", "serialization"],
        media_urls=["https://example.com/image.jpg"],
        metadata={"category": "test", "priority": 1}
    )

    # Convert to dict and back
    data = original.to_dict()
    restored = ContentItem.from_dict(data)

    # Check all fields match
    assert restored.id == original.id
    assert restored.source == original.source
    assert restored.source_type == original.source_type
    assert restored.title == original.title
    assert restored.content == original.content
    assert restored.author == original.author
    assert restored.timestamp == original.timestamp
    assert restored.url == original.url
    assert restored.tags == original.tags
    assert restored.media_urls == original.media_urls
    assert restored.metadata == original.metadata