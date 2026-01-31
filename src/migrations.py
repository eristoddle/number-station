#!/usr/bin/env python3
"""
Number Station - Database Migration Utilities

This module provides database migration functionality to handle schema updates
and data transformations as the application evolves.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Callable
from datetime import datetime

from .database import DatabaseManager


class Migration:
    """
    Represents a single database migration.
    """

    def __init__(self, version: str, description: str, up_func: Callable, down_func: Callable = None):
        """
        Initialize migration.

        Args:
            version: Migration version (e.g., "001", "002")
            description: Human-readable description
            up_func: Function to apply the migration
            down_func: Function to rollback the migration (optional)
        """
        self.version = version
        self.description = description
        self.up_func = up_func
        self.down_func = down_func
        self.timestamp = datetime.now()


class MigrationManager:
    """
    Manages database migrations for Number Station.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize migration manager.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.migrations: List[Migration] = []

        # Initialize migration tracking table
        self._init_migration_table()

        # Register built-in migrations
        self._register_migrations()

    def _init_migration_table(self):
        """Initialize the migration tracking table."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _register_migrations(self):
        """Register all available migrations."""
        # Migration 001: Initial schema (already handled by DatabaseManager._init_database)
        self.register_migration(
            "001",
            "Initial database schema",
            self._migration_001_up,
            self._migration_001_down
        )

        # Future migrations can be added here
        # Example:
        # self.register_migration(
        #     "002",
        #     "Add content indexing",
        #     self._migration_002_up,
        #     self._migration_002_down
        # )

    def register_migration(self, version: str, description: str, up_func: Callable, down_func: Callable = None):
        """
        Register a new migration.

        Args:
            version: Migration version
            description: Migration description
            up_func: Function to apply migration
            down_func: Function to rollback migration
        """
        migration = Migration(version, description, up_func, down_func)
        self.migrations.append(migration)
        self.migrations.sort(key=lambda m: m.version)

    def get_applied_migrations(self) -> List[str]:
        """
        Get list of applied migration versions.

        Returns:
            List of applied migration versions
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error getting applied migrations: {e}")
            return []

    def get_pending_migrations(self) -> List[Migration]:
        """
        Get list of pending migrations.

        Returns:
            List of Migration objects that haven't been applied
        """
        applied = set(self.get_applied_migrations())
        return [m for m in self.migrations if m.version not in applied]

    def apply_migration(self, migration: Migration) -> bool:
        """
        Apply a single migration.

        Args:
            migration: Migration to apply

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Applying migration {migration.version}: {migration.description}")

            with self.db_manager.get_connection() as conn:
                # Apply the migration
                migration.up_func(conn)

                # Record the migration as applied
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO schema_migrations (version, description)
                    VALUES (?, ?)
                """, (migration.version, migration.description))

                conn.commit()
                self.logger.info(f"Migration {migration.version} applied successfully")
                return True

        except Exception as e:
            self.logger.error(f"Error applying migration {migration.version}: {e}")
            return False

    def rollback_migration(self, migration: Migration) -> bool:
        """
        Rollback a single migration.

        Args:
            migration: Migration to rollback

        Returns:
            bool: True if successful, False otherwise
        """
        if not migration.down_func:
            self.logger.error(f"Migration {migration.version} has no rollback function")
            return False

        try:
            self.logger.info(f"Rolling back migration {migration.version}: {migration.description}")

            with self.db_manager.get_connection() as conn:
                # Rollback the migration
                migration.down_func(conn)

                # Remove the migration record
                cursor = conn.cursor()
                cursor.execute("DELETE FROM schema_migrations WHERE version = ?", (migration.version,))

                conn.commit()
                self.logger.info(f"Migration {migration.version} rolled back successfully")
                return True

        except Exception as e:
            self.logger.error(f"Error rolling back migration {migration.version}: {e}")
            return False

    def migrate_up(self, target_version: str = None) -> bool:
        """
        Apply all pending migrations up to target version.

        Args:
            target_version: Stop at this version (None for all pending)

        Returns:
            bool: True if all migrations successful, False otherwise
        """
        pending = self.get_pending_migrations()

        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            self.logger.info("No pending migrations to apply")
            return True

        success = True
        for migration in pending:
            if not self.apply_migration(migration):
                success = False
                break

        return success

    def migrate_down(self, target_version: str) -> bool:
        """
        Rollback migrations down to target version.

        Args:
            target_version: Rollback to this version

        Returns:
            bool: True if all rollbacks successful, False otherwise
        """
        applied = self.get_applied_migrations()
        to_rollback = [v for v in applied if v > target_version]
        to_rollback.sort(reverse=True)  # Rollback in reverse order

        if not to_rollback:
            self.logger.info(f"Already at or below target version {target_version}")
            return True

        success = True
        for version in to_rollback:
            migration = next((m for m in self.migrations if m.version == version), None)
            if migration and not self.rollback_migration(migration):
                success = False
                break

        return success

    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status.

        Returns:
            Dict with migration status information
        """
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        return {
            'applied_count': len(applied),
            'pending_count': len(pending),
            'applied_versions': applied,
            'pending_versions': [m.version for m in pending],
            'current_version': applied[-1] if applied else None,
            'latest_version': self.migrations[-1].version if self.migrations else None
        }

    # Built-in migration functions

    def _migration_001_up(self, conn: sqlite3.Connection):
        """Migration 001: Initial schema (no-op since handled by DatabaseManager)."""
        # This is a no-op since the initial schema is created by DatabaseManager._init_database
        pass

    def _migration_001_down(self, conn: sqlite3.Connection):
        """Rollback migration 001: Drop all tables."""
        cursor = conn.cursor()
        tables = [
            'content_items',
            'plugin_configs',
            'user_preferences',
            'source_configurations',
            'plugin_metadata'
        ]

        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # Example future migration (commented out)
    # def _migration_002_up(self, conn: sqlite3.Connection):
    #     """Migration 002: Add full-text search index."""
    #     cursor = conn.cursor()
    #     cursor.execute("""
    #         CREATE VIRTUAL TABLE IF NOT EXISTS content_search
    #         USING fts5(id, title, content, content=content_items)
    #     """)
    #
    #     # Populate the search index
    #     cursor.execute("""
    #         INSERT INTO content_search(id, title, content)
    #         SELECT id, title, content FROM content_items
    #     """)
    #
    # def _migration_002_down(self, conn: sqlite3.Connection):
    #     """Rollback migration 002: Drop search index."""
    #     cursor = conn.cursor()
    #     cursor.execute("DROP TABLE IF EXISTS content_search")


def run_migrations(db_manager: DatabaseManager = None) -> bool:
    """
    Run all pending migrations.

    Args:
        db_manager: DatabaseManager instance (uses global if None)

    Returns:
        bool: True if successful, False otherwise
    """
    if db_manager is None:
        from .database import get_database
        db_manager = get_database()

    migration_manager = MigrationManager(db_manager)
    return migration_manager.migrate_up()


def get_migration_status(db_manager: DatabaseManager = None) -> Dict[str, Any]:
    """
    Get migration status.

    Args:
        db_manager: DatabaseManager instance (uses global if None)

    Returns:
        Dict with migration status
    """
    if db_manager is None:
        from .database import get_database
        db_manager = get_database()

    migration_manager = MigrationManager(db_manager)
    return migration_manager.get_migration_status()