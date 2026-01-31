#!/usr/bin/env python3
"""
Number Station - Database Management

This module provides database connection, schema management, and migration utilities
for the Number Station application using SQLite.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json
from contextlib import contextmanager

from .models import ContentItem, UserPreferences, PluginMetadata, SourceConfiguration, SourceMetadata


class DatabaseManager:
    """
    Manages SQLite database operations for Number Station.

    Provides connection management, schema creation, migrations, and CRUD operations
    for all data models.
    """

    def __init__(self, db_path: Union[str, Path] = "data/number_station.db"):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

        # Initialize database schema
        self._init_database()

    def _init_database(self):
        """Initialize database schema if it doesn't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create content_items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_items (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    author TEXT,
                    timestamp DATETIME NOT NULL,
                    url TEXT NOT NULL,
                    tags TEXT, -- JSON array
                    media_urls TEXT, -- JSON array
                    metadata TEXT, -- JSON object
                    relevance_score REAL DEFAULT 0.0,
                    embedding TEXT, -- JSON array
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create plugin_configs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plugin_configs (
                    plugin_name TEXT PRIMARY KEY,
                    config_data TEXT NOT NULL, -- JSON object
                    enabled BOOLEAN DEFAULT TRUE,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create user_preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create source_configurations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS source_configurations (
                    name TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    url TEXT,
                    enabled BOOLEAN DEFAULT TRUE,
                    fetch_interval INTEGER DEFAULT 300,
                    tags TEXT, -- JSON array
                    config TEXT, -- JSON object
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create plugin_metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plugin_metadata (
                    name TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    description TEXT NOT NULL,
                    author TEXT NOT NULL,
                    plugin_type TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    dependencies TEXT, -- JSON array
                    capabilities TEXT, -- JSON array
                    config_schema TEXT, -- JSON object
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create source_metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS source_metadata (
                    source_id TEXT PRIMARY KEY,
                    last_fetch_attempt DATETIME NOT NULL,
                    last_fetch_success DATETIME,
                    last_item_count INTEGER DEFAULT 0,
                    total_items_fetched INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    consecutive_errors INTEGER DEFAULT 0,
                    last_error TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_timestamp ON content_items(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_source ON content_items(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_source_type ON content_items(source_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_plugin_type ON plugin_metadata(plugin_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_type ON source_configurations(source_type)")

            conn.commit()
            self.logger.info("Database schema initialized successfully")

    @contextmanager
    def get_connection(self):
        """
        Get database connection with automatic cleanup.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # ContentItem operations

    def save_content_item(self, item: ContentItem) -> bool:
        """
        Save a content item to the database.

        Args:
            item: ContentItem to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                data = item.to_dict()

                cursor.execute("""
                    INSERT OR REPLACE INTO content_items
                    (id, source, source_type, title, content, author, timestamp, url, tags, media_urls, metadata, relevance_score, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['id'], data['source'], data['source_type'], data['title'],
                    data['content'], data['author'], data['timestamp'], data['url'],
                    data['tags'], data['media_urls'], data['metadata'], data['relevance_score'], data['embedding']
                ))

                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error saving content item {item.id}: {e}")
            return False

    def get_content_item(self, item_id: str) -> Optional[ContentItem]:
        """
        Retrieve a content item by ID.

        Args:
            item_id: ID of the content item

        Returns:
            ContentItem if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM content_items WHERE id = ?", (item_id,))
                row = cursor.fetchone()

                if row:
                    return ContentItem.from_dict(dict(row))
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving content item {item_id}: {e}")
            return None

    def get_content_items(
        self,
        source: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "timestamp DESC"
    ) -> List[ContentItem]:
        """
        Retrieve content items with optional filtering.

        Args:
            source: Filter by source name
            source_type: Filter by source type
            limit: Maximum number of items to return
            offset: Number of items to skip
            order_by: SQL ORDER BY clause

        Returns:
            List of ContentItem objects
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM content_items"
                params = []
                conditions = []

                if source:
                    conditions.append("source = ?")
                    params.append(source)

                if source_type:
                    conditions.append("source_type = ?")
                    params.append(source_type)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [ContentItem.from_dict(dict(row)) for row in rows]
        except Exception as e:
            self.logger.error(f"Error retrieving content items: {e}")
            return []

    def delete_content_item(self, item_id: str) -> bool:
        """
        Delete a content item by ID.

        Args:
            item_id: ID of the content item to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM content_items WHERE id = ?", (item_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting content item {item_id}: {e}")
            return False

    # User preferences operations

    def save_user_preferences(self, preferences: UserPreferences) -> bool:
        """
        Save user preferences to the database.

        Args:
            preferences: UserPreferences object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                prefs_dict = preferences.to_dict()

                for key, value in prefs_dict.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, (key, json.dumps(value)))

                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error saving user preferences: {e}")
            return False

    def get_user_preferences(self) -> UserPreferences:
        """
        Retrieve user preferences from the database.

        Returns:
            UserPreferences object (with defaults if not found)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM user_preferences")
                rows = cursor.fetchall()

                prefs_dict = {}
                for row in rows:
                    prefs_dict[row['key']] = json.loads(row['value'])

                return UserPreferences.from_dict(prefs_dict)
        except Exception as e:
            self.logger.error(f"Error retrieving user preferences: {e}")
            return UserPreferences()  # Return defaults

    # Plugin configuration operations

    def save_plugin_config(self, plugin_name: str, config_data: Dict[str, Any], enabled: bool = True) -> bool:
        """
        Save plugin configuration to the database.

        Args:
            plugin_name: Name of the plugin
            config_data: Plugin configuration data
            enabled: Whether the plugin is enabled

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO plugin_configs (plugin_name, config_data, enabled, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (plugin_name, json.dumps(config_data), enabled))

                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error saving plugin config for {plugin_name}: {e}")
            return False

    def get_plugin_config(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve plugin configuration from the database.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin configuration dict if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT config_data, enabled FROM plugin_configs WHERE plugin_name = ?",
                    (plugin_name,)
                )
                row = cursor.fetchone()

                if row:
                    return {
                        'config': json.loads(row['config_data']),
                        'enabled': bool(row['enabled'])
                    }
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving plugin config for {plugin_name}: {e}")
            return None

    def get_all_plugin_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve all plugin configurations.

        Returns:
            Dict mapping plugin names to their configurations
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT plugin_name, config_data, enabled FROM plugin_configs")
                rows = cursor.fetchall()

                configs = {}
                for row in rows:
                    configs[row['plugin_name']] = {
                        'config': json.loads(row['config_data']),
                        'enabled': bool(row['enabled'])
                    }

                return configs
        except Exception as e:
            self.logger.error(f"Error retrieving all plugin configs: {e}")
            return {}

    # Source configuration operations

    def save_source_config(self, source_config: SourceConfiguration) -> bool:
        """
        Save source configuration to the database.

        Args:
            source_config: SourceConfiguration object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                data = source_config.to_dict()

                cursor.execute("""
                    INSERT OR REPLACE INTO source_configurations
                    (name, source_type, url, enabled, fetch_interval, tags, config, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    data['name'], data['source_type'], data['url'], data['enabled'],
                    data['fetch_interval'], data['tags'], data['config']
                ))

                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error saving source config {source_config.name}: {e}")
            return False

    def get_source_config(self, name: str) -> Optional[SourceConfiguration]:
        """
        Retrieve source configuration by name.

        Args:
            name: Name of the source configuration

        Returns:
            SourceConfiguration if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM source_configurations WHERE name = ?", (name,))
                row = cursor.fetchone()

                if row:
                    return SourceConfiguration.from_dict(dict(row))
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving source config {name}: {e}")
            return None

    def get_source_configs_by_type(self, source_type: str) -> List[SourceConfiguration]:
        """
        Retrieve all source configurations of a specific type.

        Args:
            source_type: Type of source (e.g., 'rss', 'twitter')

        Returns:
            List of SourceConfiguration objects
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM source_configurations WHERE source_type = ? AND enabled = TRUE",
                    (source_type,)
                )
                rows = cursor.fetchall()

                return [SourceConfiguration.from_dict(dict(row)) for row in rows]
        except Exception as e:
            self.logger.error(f"Error retrieving source configs for type {source_type}: {e}")
            return []

    def delete_source_config(self, name: str) -> bool:
        """
        Delete a source configuration by name.

        Args:
            name: Name of the source configuration to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM source_configurations WHERE name = ?", (name,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting source config {name}: {e}")
            return False

    # Source metadata operations

    def save_source_metadata(self, metadata: SourceMetadata) -> bool:
        """
        Save source metadata/statistics.

        Args:
            metadata: SourceMetadata object

        Returns:
            bool: True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                data = metadata.to_dict()

                cursor.execute("""
                    INSERT OR REPLACE INTO source_metadata
                    (source_id, last_fetch_attempt, last_fetch_success, last_item_count,
                     total_items_fetched, error_count, consecutive_errors, last_error, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    data['source_id'], data['last_fetch_attempt'], data['last_fetch_success'],
                    data['last_item_count'], data['total_items_fetched'], data['error_count'],
                    data['consecutive_errors'], data['last_error']
                ))

                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error saving source metadata for {metadata.source_id}: {e}")
            return False

    def get_source_metadata(self, source_id: str) -> Optional[SourceMetadata]:
        """
        Retrieve source metadata.

        Args:
            source_id: Source ID (name)

        Returns:
             SourceMetadata object or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM source_metadata WHERE source_id = ?", (source_id,))
                row = cursor.fetchone()

                if row:
                    return SourceMetadata.from_dict(dict(row))
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving source metadata for {source_id}: {e}")
            return None

    # Plugin metadata operations

    def save_plugin_metadata(self, metadata: PluginMetadata) -> bool:
        """
        Save plugin metadata to the database.

        Args:
            metadata: PluginMetadata object

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                data = metadata.to_dict()

                cursor.execute("""
                    INSERT OR REPLACE INTO plugin_metadata
                    (name, version, description, author, plugin_type, enabled,
                     dependencies, capabilities, config_schema, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    data['name'], data['version'], data['description'], data['author'],
                    data['plugin_type'], data['enabled'], data['dependencies'],
                    data['capabilities'], data['config_schema']
                ))

                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error saving plugin metadata {metadata.name}: {e}")
            return False

    def get_plugin_metadata(self, name: str) -> Optional[PluginMetadata]:
        """
        Retrieve plugin metadata by name.

        Args:
            name: Name of the plugin

        Returns:
            PluginMetadata if found, None otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM plugin_metadata WHERE name = ?", (name,))
                row = cursor.fetchone()

                if row:
                    return PluginMetadata.from_dict(dict(row))
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving plugin metadata {name}: {e}")
            return None

    def get_plugins_by_type(self, plugin_type: str) -> List[PluginMetadata]:
        """
        Retrieve all plugins of a specific type.

        Args:
            plugin_type: Type of plugin ('source', 'filter', 'theme')

        Returns:
            List of PluginMetadata objects
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM plugin_metadata WHERE plugin_type = ? AND enabled = TRUE",
                    (plugin_type,)
                )
                rows = cursor.fetchall()

                return [PluginMetadata.from_dict(dict(row)) for row in rows]
        except Exception as e:
            self.logger.error(f"Error retrieving plugins for type {plugin_type}: {e}")
            return []

    # Utility methods

    def cleanup_old_content(self, days: int = 30) -> int:
        """
        Remove content items older than specified days.

        Args:
            days: Number of days to keep content

        Returns:
            Number of items deleted
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM content_items
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days))

                conn.commit()
                deleted_count = cursor.rowcount
                self.logger.info(f"Cleaned up {deleted_count} old content items")
                return deleted_count
        except Exception as e:
            self.logger.error(f"Error cleaning up old content: {e}")
            return 0

    def get_database_stats(self) -> Dict[str, int]:
        """
        Get database statistics.

        Returns:
            Dict with table row counts
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                stats = {}
                tables = ['content_items', 'plugin_configs', 'user_preferences',
                         'source_configurations', 'plugin_metadata']

                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]

                return stats
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}


# Global database instance
_db_manager = None


def get_database() -> DatabaseManager:
    """
    Get the global database manager instance.

    Returns:
        DatabaseManager: Global database instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager