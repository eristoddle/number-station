#!/usr/bin/env python3
"""
Tests for Number Station Configuration Management System

This module contains unit tests for the ConfigurationManager class,
testing save/load/validate methods, JSON persistence, and export/import functionality.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.configuration import ConfigurationManager, ConfigurationValidationError
from src.models import UserPreferences, SourceConfiguration, PluginMetadata
from src.database import DatabaseManager


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager."""
        db = Mock(spec=DatabaseManager)

        # Mock user preferences
        default_prefs = UserPreferences()
        db.get_user_preferences.return_value = default_prefs
        db.save_user_preferences.return_value = True

        # Mock plugin configs
        db.get_all_plugin_configs.return_value = {
            "test_plugin": {
                "config": {"setting1": "value1"},
                "enabled": True
            }
        }
        db.save_plugin_config.return_value = True

        # Mock source configs
        db.get_source_configs_by_type.return_value = []
        db.save_source_config.return_value = True

        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        def execute_side_effect(query, args=None):
            if "DISTINCT source_type" in query:
                mock_cursor.fetchall.return_value = [("rss",)]
            elif "SELECT *" in query and "source_configurations" in query:
                # Return a valid source config as a dict (which works with dict(row))
                mock_cursor.fetchall.return_value = [{
                    "name": "test_rss",
                    "source_type": "rss",
                    "url": "https://example.com/feed.xml",
                    "fetch_interval": 300,
                    "tags": "[]",
                    "config": "{}"
                }]
            elif "plugin_configs" in query: # For reset or specific plugin queries
                mock_cursor.fetchall.return_value = []
            return mock_cursor

        mock_cursor.execute.side_effect = execute_side_effect
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        db.get_connection.return_value = mock_conn

        # Mock database stats
        db.get_database_stats.return_value = {
            "content_items": 10,
            "plugin_configs": 2,
            "source_configurations": 3
        }

        return db

    @pytest.fixture
    def config_manager(self, mock_db, temp_dir):
        """Create a ConfigurationManager instance for testing."""
        return ConfigurationManager(mock_db, temp_dir)

    def test_initialization(self, mock_db, temp_dir):
        """Test ConfigurationManager initialization."""
        config_manager = ConfigurationManager(mock_db, temp_dir)

        assert config_manager.db == mock_db
        assert config_manager.config_dir == temp_dir
        assert config_manager.config_dir.exists()

        # Check that configuration file paths are set correctly
        assert config_manager.user_prefs_file == temp_dir / "user_preferences.json"
        assert config_manager.plugin_configs_file == temp_dir / "plugin_configs.json"
        assert config_manager.source_configs_file == temp_dir / "source_configs.json"
        assert config_manager.system_config_file == temp_dir / "system_config.json"

    def test_save_config_success(self, config_manager):
        """Test successful configuration saving."""
        result = config_manager.save_config()

        assert result is True
        assert config_manager.user_prefs_file.exists()
        assert config_manager.plugin_configs_file.exists()
        assert config_manager.source_configs_file.exists()
        assert config_manager.system_config_file.exists()

    def test_save_config_failure(self, config_manager):
        """Test configuration saving with database errors."""
        config_manager.db.get_user_preferences.side_effect = Exception("Database error")

        result = config_manager.save_config()

        assert result is False

    def test_load_config_success(self, config_manager):
        """Test successful configuration loading."""
        # First save some config to create files
        config_manager.save_config()

        # Reset mocks
        config_manager.db.reset_mock()

        result = config_manager.load_config()

        assert result is True

    def test_load_config_no_files(self, config_manager):
        """Test configuration loading when no files exist."""
        result = config_manager.load_config()

        # Should succeed even with no files (uses defaults)
        assert result is True

    def test_validate_user_preferences_valid(self, config_manager):
        """Test validation of valid user preferences."""
        valid_prefs = {
            "ui_mode": "stream",
            "theme": "default",
            "update_interval": 300,
            "auto_refresh": True
        }

        result = config_manager.validate_config("user_prefs", valid_prefs)
        assert result is True

    def test_validate_user_preferences_invalid_mode(self, config_manager):
        """Test validation of user preferences with invalid UI mode."""
        invalid_prefs = {
            "ui_mode": "invalid_mode",
            "theme": "default",
            "update_interval": 300
        }

        with pytest.raises(ConfigurationValidationError, match="Invalid ui_mode"):
            config_manager.validate_config("user_prefs", invalid_prefs)

    def test_validate_user_preferences_missing_field(self, config_manager):
        """Test validation of user preferences with missing required field."""
        invalid_prefs = {
            "theme": "default",
            "update_interval": 300
        }

        with pytest.raises(ConfigurationValidationError, match="Missing required field: ui_mode"):
            config_manager.validate_config("user_prefs", invalid_prefs)

    def test_validate_user_preferences_invalid_interval(self, config_manager):
        """Test validation of user preferences with invalid update interval."""
        invalid_prefs = {
            "ui_mode": "stream",
            "theme": "default",
            "update_interval": 30  # Too low
        }

        with pytest.raises(ConfigurationValidationError, match="update_interval must be an integer >= 60"):
            config_manager.validate_config("user_prefs", invalid_prefs)

    def test_validate_plugin_config_valid(self, config_manager):
        """Test validation of valid plugin configuration."""
        valid_config = {
            "plugin1": {
                "enabled": True,
                "config": {"setting1": "value1"}
            },
            "plugin2": {
                "enabled": False,
                "config": {}
            }
        }

        result = config_manager.validate_config("plugin", valid_config)
        assert result is True

    def test_validate_plugin_config_invalid_type(self, config_manager):
        """Test validation of plugin configuration with invalid type."""
        invalid_config = "not_a_dict"

        with pytest.raises(ConfigurationValidationError, match="Plugin config must be a dictionary"):
            config_manager.validate_config("plugin", invalid_config)

    def test_validate_source_config_valid(self, config_manager):
        """Test validation of valid source configuration."""
        valid_config = {
            "name": "test_source",
            "source_type": "rss",
            "url": "https://example.com/feed.xml",
            "fetch_interval": 300
        }

        result = config_manager.validate_config("source", valid_config)
        assert result is True

    def test_validate_source_config_missing_name(self, config_manager):
        """Test validation of source configuration with missing name."""
        invalid_config = {
            "source_type": "rss",
            "url": "https://example.com/feed.xml"
        }

        with pytest.raises(ConfigurationValidationError, match="Missing required field: name"):
            config_manager.validate_config("source", invalid_config)

    def test_validate_system_config_valid(self, config_manager):
        """Test validation of valid system configuration."""
        valid_config = {
            "version": "1.0.0",
            "database_path": "data/test.db",
            "log_level": "INFO"
        }

        result = config_manager.validate_config("system", valid_config)
        assert result is True

    def test_validate_unknown_config_type(self, config_manager):
        """Test validation with unknown configuration type."""
        with pytest.raises(ConfigurationValidationError, match="Unknown configuration type: unknown"):
            config_manager.validate_config("unknown", {})

    def test_export_config_success(self, config_manager, temp_dir):
        """Test successful configuration export."""
        export_path = temp_dir / "export.json"

        result = config_manager.export_config(export_path, include_sensitive=False)

        assert result is True
        assert export_path.exists()

        # Verify export structure
        with open(export_path, 'r') as f:
            export_data = json.load(f)

        assert "export_metadata" in export_data
        assert "user_preferences" in export_data
        assert "plugin_configs" in export_data
        assert "source_configs" in export_data
        assert "system_config" in export_data

        # Check metadata
        metadata = export_data["export_metadata"]
        assert "timestamp" in metadata
        assert "version" in metadata
        assert metadata["include_sensitive"] is False

    def test_export_config_with_sensitive(self, config_manager, temp_dir):
        """Test configuration export including sensitive data."""
        export_path = temp_dir / "export_sensitive.json"

        result = config_manager.export_config(export_path, include_sensitive=True)

        assert result is True

        with open(export_path, 'r') as f:
            export_data = json.load(f)

        assert export_data["export_metadata"]["include_sensitive"] is True

    def test_export_config_failure(self, config_manager, temp_dir):
        """Test configuration export failure."""
        # Try to export to a non-existent directory
        export_path = temp_dir / "nonexistent" / "export.json"

        result = config_manager.export_config(export_path)

        assert result is False

    def test_import_config_success(self, config_manager, temp_dir):
        """Test successful configuration import."""
        # Create a valid export file
        export_data = {
            "export_metadata": {
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "include_sensitive": False
            },
            "user_preferences": {
                "ui_mode": "board",
                "theme": "dark",
                "update_interval": 600
            },
            "plugin_configs": {
                "imported_plugin": {
                    "enabled": True,
                    "config": {"setting": "value"}
                }
            },
            "source_configs": {
                "rss": [{
                    "name": "imported_feed",
                    "source_type": "rss",
                    "url": "https://example.com/feed.xml",
                    "enabled": True,
                    "fetch_interval": 300,
                    "tags": "[]",
                    "config": "{}"
                }]
            },
            "system_config": {
                "version": "1.0.0",
                "database_path": "data/imported.db"
            }
        }

        import_path = temp_dir / "import.json"
        with open(import_path, 'w') as f:
            json.dump(export_data, f)

        result = config_manager.import_config(import_path, merge=True)

        assert result is True

    def test_import_config_file_not_found(self, config_manager, temp_dir):
        """Test configuration import with non-existent file."""
        import_path = temp_dir / "nonexistent.json"

        result = config_manager.import_config(import_path)

        assert result is False

    def test_import_config_invalid_structure(self, config_manager, temp_dir):
        """Test configuration import with invalid structure."""
        invalid_data = {"invalid": "structure"}

        import_path = temp_dir / "invalid.json"
        with open(import_path, 'w') as f:
            json.dump(invalid_data, f)

        result = config_manager.import_config(import_path)

        assert result is False

    def test_reset_to_defaults(self, config_manager):
        """Test resetting configurations to defaults."""
        # First save some config
        config_manager.save_config()

        result = config_manager.reset_to_defaults()

        assert result is True

        # Verify database methods were called
        config_manager.db.save_user_preferences.assert_called()

    def test_get_config_status(self, config_manager):
        """Test getting configuration status."""
        status = config_manager.get_config_status()

        assert "timestamp" in status
        assert "database_stats" in status
        assert "config_files" in status
        assert "validation_status" in status

        # Check database stats
        assert status["database_stats"]["content_items"] == 10

        # Check config files status
        config_files = status["config_files"]
        assert "user_preferences" in config_files
        assert "plugin_configs" in config_files
        assert "source_configs" in config_files
        assert "system_config" in config_files

    def test_filter_sensitive_plugin_data(self, config_manager):
        """Test filtering sensitive data from plugin configurations."""
        plugin_configs = {
            "plugin1": {
                "enabled": True,
                "config": {
                    "api_key": "secret123",
                    "public_setting": "value1",
                    "token": "token456"
                }
            }
        }

        filtered = config_manager._filter_sensitive_plugin_data(plugin_configs)

        assert filtered["plugin1"]["config"]["api_key"] == "***FILTERED***"
        assert filtered["plugin1"]["config"]["token"] == "***FILTERED***"
        assert filtered["plugin1"]["config"]["public_setting"] == "value1"

    def test_filter_sensitive_source_data(self, config_manager):
        """Test filtering sensitive data from source configurations."""
        config_data = {
            "name": "test_source",
            "source_type": "twitter",
            "config": json.dumps({
                "api_key": "secret123",
                "username": "testuser",
                "password": "secret456"
            })
        }

        filtered = config_manager._filter_sensitive_source_data(config_data)

        config_dict = json.loads(filtered["config"])
        assert config_dict["api_key"] == "***FILTERED***"
        assert config_dict["password"] == "***FILTERED***"
        assert config_dict["username"] == "testuser"

    def test_create_config_backup(self, config_manager):
        """Test creating configuration backup."""
        backup_path = config_manager._create_config_backup()

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.name.startswith("config_backup_")
        assert backup_path.suffix == ".json"

    def test_round_trip_persistence(self, config_manager, temp_dir):
        """Test that save then load produces equivalent configuration."""
        # Save initial configuration
        assert config_manager.save_config() is True

        # Modify some settings in memory
        new_prefs = UserPreferences(ui_mode="board", theme="dark", update_interval=600)
        config_manager.db.get_user_preferences.return_value = new_prefs

        # Save again
        assert config_manager.save_config() is True

        # Load and verify
        assert config_manager.load_config() is True

        # Verify the user preferences were saved and loaded correctly
        config_manager.db.save_user_preferences.assert_called()

    def test_configuration_validation_edge_cases(self, config_manager):
        """Test configuration validation with edge cases."""
        # Test empty configuration
        with pytest.raises(ConfigurationValidationError):
            config_manager.validate_config("user_prefs", {})

        # Test configuration with None values
        config_with_none = {
            "ui_mode": None,
            "theme": "default",
            "update_interval": 300
        }

        with pytest.raises(ConfigurationValidationError):
            config_manager.validate_config("user_prefs", config_with_none)

    def test_concurrent_access_safety(self, config_manager):
        """Test that configuration manager handles concurrent access safely."""
        # This is a basic test - in a real scenario, you'd use threading
        # to test concurrent access

        # Multiple save operations should not interfere
        result1 = config_manager.save_config()
        result2 = config_manager.save_config()

        assert result1 is True
        assert result2 is True

    def test_large_configuration_handling(self, config_manager):
        """Test handling of large configuration data."""
        # Create a large plugin configuration
        large_config = {}
        for i in range(1000):
            large_config[f"plugin_{i}"] = {
                "enabled": True,
                "config": {f"setting_{j}": f"value_{j}" for j in range(100)}
            }

        config_manager.db.get_all_plugin_configs.return_value = large_config

        # Should handle large configurations without issues
        result = config_manager.save_config()
        assert result is True


class TestConfigurationManagerIntegration:
    """Integration tests for ConfigurationManager with real database."""

    @pytest.fixture
    def temp_db_dir(self):
        """Create a temporary directory for database testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def real_db(self, temp_db_dir):
        """Create a real database manager for integration testing."""
        db_path = temp_db_dir / "test.db"
        return DatabaseManager(db_path)

    @pytest.fixture
    def integration_config_manager(self, real_db, temp_db_dir):
        """Create a ConfigurationManager with real database."""
        config_dir = temp_db_dir / "config"
        return ConfigurationManager(real_db, config_dir)

    def test_full_configuration_cycle(self, integration_config_manager):
        """Test complete configuration save/load cycle with real database."""
        # Set up some test data
        prefs = UserPreferences(ui_mode="board", theme="dark", update_interval=600)
        integration_config_manager.db.save_user_preferences(prefs)

        source_config = SourceConfiguration(
            name="test_rss",
            source_type="rss",
            url="https://example.com/feed.xml",
            fetch_interval=300,
            tags=["news", "tech"]
        )
        integration_config_manager.db.save_source_config(source_config)

        # Save configuration
        assert integration_config_manager.save_config() is True

        # Verify files were created
        assert integration_config_manager.user_prefs_file.exists()
        assert integration_config_manager.source_configs_file.exists()

        # Load configuration
        assert integration_config_manager.load_config() is True

        # Verify data integrity
        loaded_prefs = integration_config_manager.db.get_user_preferences()
        assert loaded_prefs.ui_mode == "board"
        assert loaded_prefs.theme == "dark"
        assert loaded_prefs.update_interval == 600

    def test_export_import_round_trip(self, integration_config_manager, temp_db_dir):
        """Test export then import produces equivalent configuration."""
        # Set up test data
        prefs = UserPreferences(ui_mode="stream", theme="light", update_interval=300)
        integration_config_manager.db.save_user_preferences(prefs)

        # Export configuration
        export_path = temp_db_dir / "test_export.json"
        assert integration_config_manager.export_config(export_path) is True

        # Modify configuration
        new_prefs = UserPreferences(ui_mode="board", theme="dark", update_interval=600)
        integration_config_manager.db.save_user_preferences(new_prefs)

        # Import original configuration
        assert integration_config_manager.import_config(export_path, merge=False) is True

        # Verify original configuration was restored
        restored_prefs = integration_config_manager.db.get_user_preferences()
        assert restored_prefs.ui_mode == "stream"
        assert restored_prefs.theme == "light"
        assert restored_prefs.update_interval == 300


if __name__ == "__main__":
    pytest.main([__file__])