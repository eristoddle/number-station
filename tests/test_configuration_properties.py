#!/usr/bin/env python3
"""
Property-based tests for Number Station Configuration Round-Trip Persistence.

This module contains property-based tests that verify configuration round-trip persistence
across all valid inputs using the Hypothesis testing framework.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import string

from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.configuration import ConfigurationManager, ConfigurationValidationError
from src.models import UserPreferences, SourceConfiguration, PluginMetadata
from src.database import DatabaseManager


# Custom strategies for generating test data
@composite
def valid_ui_mode(draw):
    """Generate valid UI mode strings."""
    return draw(st.sampled_from(["stream", "board"]))


@composite
def valid_theme(draw):
    """Generate valid theme strings."""
    themes = ["default", "dark", "light", "blue", "green", "custom"]
    return draw(st.sampled_from(themes))


@composite
def valid_update_interval(draw):
    """Generate valid update intervals (>= 60 seconds)."""
    return draw(st.integers(min_value=60, max_value=3600))


@composite
def valid_items_per_page(draw):
    """Generate valid items per page values."""
    return draw(st.integers(min_value=10, max_value=200))


@composite
def valid_user_preferences(draw):
    """Generate valid UserPreferences instances."""
    return UserPreferences(
        ui_mode=draw(valid_ui_mode()),
        theme=draw(valid_theme()),
        update_interval=draw(valid_update_interval()),
        items_per_page=draw(valid_items_per_page()),
        auto_refresh=draw(st.booleans()),
        show_media=draw(st.booleans()),
        show_author=draw(st.booleans()),
        show_timestamp=draw(st.booleans())
    )


@composite
def valid_plugin_name(draw):
    """Generate valid plugin names."""
    return draw(st.text(
        alphabet=string.ascii_letters + string.digits + "_-",
        min_size=3,
        max_size=50
    ).filter(lambda x: x[0].isalpha()))


@composite
def valid_plugin_type(draw):
    """Generate valid plugin types."""
    return draw(st.sampled_from(["source", "filter", "theme"]))


@composite
def valid_source_type(draw):
    """Generate valid source types."""
    return draw(st.sampled_from(["rss", "twitter", "reddit", "custom", "hackernews", "devto"]))


@composite
def valid_url(draw):
    """Generate valid URLs."""
    domains = ["example.com", "test.org", "sample.net", "demo.io"]
    protocols = ["http", "https"]

    protocol = draw(st.sampled_from(protocols))
    domain = draw(st.sampled_from(domains))
    path = draw(st.text(
        alphabet=string.ascii_letters + string.digits + "/-_",
        min_size=0,
        max_size=50
    ))

    return f"{protocol}://{domain}/{path}"


@composite
def valid_plugin_metadata(draw):
    """Generate valid PluginMetadata instances."""
    return PluginMetadata(
        name=draw(valid_plugin_name()),
        version=draw(st.text(
            alphabet=string.digits + ".",
            min_size=3,
            max_size=10
        ).filter(lambda x: x.count('.') >= 1)),
        description=draw(st.text(min_size=10, max_size=200)),
        author=draw(st.text(min_size=3, max_size=50)),
        plugin_type=draw(valid_plugin_type()),
        enabled=draw(st.booleans()),
        dependencies=draw(st.lists(valid_plugin_name(), min_size=0, max_size=5)),
        capabilities=draw(st.lists(st.text(min_size=3, max_size=20), min_size=0, max_size=10)),
        config_schema=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=0,
            max_size=10
        ))
    )


@composite
def unique_source_configurations(draw, min_size=1, max_size=5):
    """Generate a list of SourceConfiguration instances with unique names."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    configs = []
    used_names = set()

    for i in range(size):
        # Generate a unique name
        base_name = draw(st.text(min_size=3, max_size=45))  # Leave room for suffix
        name = base_name
        counter = 0
        while name in used_names:
            counter += 1
            name = f"{base_name}_{counter}"
        used_names.add(name)

        config = SourceConfiguration(
            name=name,
            source_type=draw(valid_source_type()),
            url=draw(st.one_of(st.none(), valid_url())),
            enabled=draw(st.booleans()),
            fetch_interval=draw(valid_update_interval()),
            tags=draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10)),
            config=draw(st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.one_of(st.text(), st.integers(), st.booleans()),
                min_size=0,
                max_size=10
            ))
        )
        configs.append(config)

    return configs


@composite
def valid_plugin_config_dict(draw):
    """Generate valid plugin configuration dictionary."""
    num_plugins = draw(st.integers(min_value=1, max_value=5))
    plugin_configs = {}

    for _ in range(num_plugins):
        plugin_name = draw(valid_plugin_name())
        plugin_configs[plugin_name] = {
            'enabled': draw(st.booleans()),
            'config': draw(st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.one_of(st.text(), st.integers(), st.booleans()),
                min_size=0,
                max_size=10
            ))
        }

    return plugin_configs


@composite
def valid_system_config(draw):
    """Generate valid system configuration."""
    return {
        "version": draw(st.text(
            alphabet=string.digits + ".",
            min_size=3,
            max_size=10
        ).filter(lambda x: x.count('.') >= 1)),
        "database_path": draw(st.text(min_size=5, max_size=50)),
        "log_level": draw(st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"])),
        "max_content_age_days": draw(st.integers(min_value=1, max_value=365)),
        "default_fetch_interval": draw(st.integers(min_value=60, max_value=3600)),
        "max_concurrent_fetches": draw(st.integers(min_value=1, max_value=20)),
        "rate_limit_requests_per_minute": draw(st.integers(min_value=1, max_value=1000))
    }


class TestConfigurationRoundTripPersistence:
    """
    Property-based tests for configuration round-trip persistence.

    **Feature: number-station, Property 3: Configuration Round-Trip Persistence**
    **Validates: Requirements 1.4, 10.1, 10.2, 10.3, 10.4**
    """

    def create_test_environment(self):
        """Create a temporary test environment with database and configuration manager."""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)

        db_path = temp_path / "test.db"
        config_dir = temp_path / "config"

        db = DatabaseManager(db_path)
        config_manager = ConfigurationManager(db, config_dir)

        return temp_path, db, config_manager

    def cleanup_test_environment(self, temp_path):
        """Clean up temporary test environment."""
        shutil.rmtree(temp_path)

    @given(valid_user_preferences())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_user_preferences_round_trip_persistence(self, user_prefs: UserPreferences):
        """
        Property: For any valid user preferences, saving then loading should produce equivalent configuration.

        **Validates: Requirements 1.4, 10.1**
        - THE Number_Station SHALL maintain configuration persistence across sessions
        - THE Number_Station SHALL persist user preferences to local storage
        """
        temp_path, db, config_manager = self.create_test_environment()
        try:
            # Save user preferences to database
            assert db.save_user_preferences(user_prefs)

            # Save configuration to files
            assert config_manager.save_config()

            # Load configuration from files
            assert config_manager.load_config()

            # Retrieve loaded preferences
            loaded_prefs = db.get_user_preferences()

            # Verify round-trip persistence
            assert loaded_prefs.ui_mode == user_prefs.ui_mode
            assert loaded_prefs.theme == user_prefs.theme
            assert loaded_prefs.update_interval == user_prefs.update_interval
            assert loaded_prefs.items_per_page == user_prefs.items_per_page
            assert loaded_prefs.auto_refresh == user_prefs.auto_refresh
            assert loaded_prefs.show_media == user_prefs.show_media
            assert loaded_prefs.show_author == user_prefs.show_author
            assert loaded_prefs.show_timestamp == user_prefs.show_timestamp
        finally:
            self.cleanup_test_environment(temp_path)

    @given(valid_plugin_config_dict())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_plugin_configurations_round_trip_persistence(self, plugin_configs: Dict[str, Dict[str, Any]]):
        """
        Property: For any valid plugin configurations, saving then loading should produce equivalent configuration.

        **Validates: Requirements 1.4, 10.2**
        - THE Number_Station SHALL maintain configuration persistence across sessions
        - THE Number_Station SHALL persist plugin configurations to local storage
        """
        temp_path, db, config_manager = self.create_test_environment()
        try:
            # Save plugin configurations to database
            for plugin_name, config_data in plugin_configs.items():
                assert db.save_plugin_config(
                    plugin_name,
                    config_data['config'],
                    config_data['enabled']
                )

            # Save configuration to files
            assert config_manager.save_config()

            # Clear database to simulate fresh load
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM plugin_configs")
                conn.commit()

            # Load configuration from files
            assert config_manager.load_config()

            # Retrieve loaded plugin configurations
            loaded_configs = db.get_all_plugin_configs()

            # Verify round-trip persistence
            assert len(loaded_configs) == len(plugin_configs)
            for plugin_name, original_config in plugin_configs.items():
                assert plugin_name in loaded_configs
                loaded_config = loaded_configs[plugin_name]
                assert loaded_config['enabled'] == original_config['enabled']
                assert loaded_config['config'] == original_config['config']
        finally:
            self.cleanup_test_environment(temp_path)

    @given(unique_source_configurations(min_size=1, max_size=5))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_source_configurations_round_trip_persistence(self, source_configs: List[SourceConfiguration]):
        """
        Property: For any valid source configurations, saving then loading should produce equivalent configuration.

        **Validates: Requirements 1.4, 10.3**
        - THE Number_Station SHALL maintain configuration persistence across sessions
        - THE Number_Station SHALL persist source configurations to local storage
        """
        temp_path, db, config_manager = self.create_test_environment()
        try:
            # Save source configurations to database
            for source_config in source_configs:
                assert db.save_source_config(source_config)

            # Save configuration to files
            assert config_manager.save_config()

            # Clear database to simulate fresh load
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM source_configurations")
                conn.commit()

            # Load configuration from files
            assert config_manager.load_config()

            # Retrieve loaded source configurations by type
            loaded_configs_by_type = {}
            source_types = {config.source_type for config in source_configs}

            for source_type in source_types:
                # Get ALL configurations for this type, not just enabled ones
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM source_configurations WHERE source_type = ?",
                        (source_type,)
                    )
                    rows = cursor.fetchall()
                    loaded_configs_by_type[source_type] = [SourceConfiguration.from_dict(dict(row)) for row in rows]

            # Verify round-trip persistence
            original_by_type = {}
            for config in source_configs:
                if config.source_type not in original_by_type:
                    original_by_type[config.source_type] = []
                original_by_type[config.source_type].append(config)

            for source_type, original_configs in original_by_type.items():
                loaded_configs = loaded_configs_by_type[source_type]
                assert len(loaded_configs) == len(original_configs)

                # Sort by name for comparison
                original_sorted = sorted(original_configs, key=lambda x: x.name)
                loaded_sorted = sorted(loaded_configs, key=lambda x: x.name)

                for original, loaded in zip(original_sorted, loaded_sorted):
                    assert loaded.name == original.name
                    assert loaded.source_type == original.source_type
                    assert loaded.url == original.url
                    assert loaded.enabled == original.enabled
                    assert loaded.fetch_interval == original.fetch_interval
                    assert loaded.tags == original.tags
                    assert loaded.config == original.config
        finally:
            self.cleanup_test_environment(temp_path)

    @given(valid_system_config())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_system_configuration_round_trip_persistence(self, system_config: Dict[str, Any]):
        """
        Property: For any valid system configuration, saving then loading should produce equivalent configuration.

        **Validates: Requirements 1.4, 10.4**
        - THE Number_Station SHALL maintain configuration persistence across sessions
        - System configuration should persist across sessions
        """
        temp_path, db, config_manager = self.create_test_environment()
        try:
            # Save system configuration to file
            assert config_manager._save_system_config(system_config)

            # Load system configuration from file
            loaded_config = config_manager._get_system_config()

            # Verify round-trip persistence
            for key, value in system_config.items():
                assert key in loaded_config
                assert loaded_config[key] == value
        finally:
            self.cleanup_test_environment(temp_path)

    @given(
        valid_user_preferences(),
        valid_plugin_config_dict(),
        unique_source_configurations(min_size=1, max_size=3),
        valid_system_config()
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_complete_configuration_round_trip_persistence(
        self,
        user_prefs: UserPreferences,
        plugin_configs: Dict[str, Dict[str, Any]],
        source_configs: List[SourceConfiguration],
        system_config: Dict[str, Any]
    ):
        """
        Property: For any complete valid configuration set, saving then loading should produce equivalent configuration.

        **Validates: Requirements 1.4, 10.1, 10.2, 10.3, 10.4**
        - THE Number_Station SHALL maintain configuration persistence across sessions
        - All configuration types should persist together correctly
        """
        temp_path, db, config_manager = self.create_test_environment()
        try:
            # Save all configurations to database
            assert db.save_user_preferences(user_prefs)

            for plugin_name, config_data in plugin_configs.items():
                assert db.save_plugin_config(
                    plugin_name,
                    config_data['config'],
                    config_data['enabled']
                )

            for source_config in source_configs:
                assert db.save_source_config(source_config)

            # Save system configuration
            assert config_manager._save_system_config(system_config)

            # Save all configurations to files
            assert config_manager.save_config()

            # Clear database to simulate fresh load
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_preferences")
                cursor.execute("DELETE FROM plugin_configs")
                cursor.execute("DELETE FROM source_configurations")
                conn.commit()

            # Load all configurations from files
            assert config_manager.load_config()

            # Verify user preferences
            loaded_user_prefs = db.get_user_preferences()
            assert loaded_user_prefs.ui_mode == user_prefs.ui_mode
            assert loaded_user_prefs.theme == user_prefs.theme
            assert loaded_user_prefs.update_interval == user_prefs.update_interval
            assert loaded_user_prefs.items_per_page == user_prefs.items_per_page
            assert loaded_user_prefs.auto_refresh == user_prefs.auto_refresh
            assert loaded_user_prefs.show_media == user_prefs.show_media
            assert loaded_user_prefs.show_author == user_prefs.show_author
            assert loaded_user_prefs.show_timestamp == user_prefs.show_timestamp

            # Verify plugin configurations
            loaded_plugin_configs = db.get_all_plugin_configs()
            assert len(loaded_plugin_configs) == len(plugin_configs)
            for plugin_name, original_config in plugin_configs.items():
                assert plugin_name in loaded_plugin_configs
                loaded_config = loaded_plugin_configs[plugin_name]
                assert loaded_config['enabled'] == original_config['enabled']
                assert loaded_config['config'] == original_config['config']

            # Verify source configurations
            source_types = {config.source_type for config in source_configs}
            for source_type in source_types:
                # Get ALL configurations for this type, not just enabled ones
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM source_configurations WHERE source_type = ?",
                        (source_type,)
                    )
                    rows = cursor.fetchall()
                    loaded_sources = [SourceConfiguration.from_dict(dict(row)) for row in rows]

                original_sources = [c for c in source_configs if c.source_type == source_type]
                assert len(loaded_sources) == len(original_sources)

            # Verify system configuration
            loaded_system_config = config_manager._get_system_config()
            for key, value in system_config.items():
                assert key in loaded_system_config
                assert loaded_system_config[key] == value
        finally:
            self.cleanup_test_environment(temp_path)

    @given(
        valid_user_preferences(),
        valid_plugin_config_dict(),
        unique_source_configurations(min_size=1, max_size=3)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_configuration_export_import_round_trip_persistence(
        self,
        user_prefs: UserPreferences,
        plugin_configs: Dict[str, Dict[str, Any]],
        source_configs: List[SourceConfiguration]
    ):
        """
        Property: For any valid configuration, export then import should produce equivalent configuration.

        **Validates: Requirements 10.5, 10.6**
        - THE Number_Station SHALL provide configuration export functionality
        - THE Number_Station SHALL provide configuration import functionality
        """
        temp_path, db, config_manager = self.create_test_environment()
        try:
            # Save all configurations to database
            assert db.save_user_preferences(user_prefs)

            for plugin_name, config_data in plugin_configs.items():
                assert db.save_plugin_config(
                    plugin_name,
                    config_data['config'],
                    config_data['enabled']
                )

            for source_config in source_configs:
                assert db.save_source_config(source_config)

            # Export configuration
            export_path = temp_path / "export.json"
            assert config_manager.export_config(export_path, include_sensitive=True)
            assert export_path.exists()

            # Clear database to simulate fresh system
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_preferences")
                cursor.execute("DELETE FROM plugin_configs")
                cursor.execute("DELETE FROM source_configurations")
                conn.commit()

            # Import configuration
            assert config_manager.import_config(export_path, merge=False)

            # Verify user preferences
            loaded_user_prefs = db.get_user_preferences()
            assert loaded_user_prefs.ui_mode == user_prefs.ui_mode
            assert loaded_user_prefs.theme == user_prefs.theme
            assert loaded_user_prefs.update_interval == user_prefs.update_interval
            assert loaded_user_prefs.items_per_page == user_prefs.items_per_page
            assert loaded_user_prefs.auto_refresh == user_prefs.auto_refresh
            assert loaded_user_prefs.show_media == user_prefs.show_media
            assert loaded_user_prefs.show_author == user_prefs.show_author
            assert loaded_user_prefs.show_timestamp == user_prefs.show_timestamp

            # Verify plugin configurations
            loaded_plugin_configs = db.get_all_plugin_configs()
            assert len(loaded_plugin_configs) == len(plugin_configs)
            for plugin_name, original_config in plugin_configs.items():
                assert plugin_name in loaded_plugin_configs
                loaded_config = loaded_plugin_configs[plugin_name]
                assert loaded_config['enabled'] == original_config['enabled']
                assert loaded_config['config'] == original_config['config']

            # Verify source configurations
            source_types = {config.source_type for config in source_configs}
            for source_type in source_types:
                # Get ALL configurations for this type, not just enabled ones
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM source_configurations WHERE source_type = ?",
                        (source_type,)
                    )
                    rows = cursor.fetchall()
                    loaded_sources = [SourceConfiguration.from_dict(dict(row)) for row in rows]

                original_sources = [c for c in source_configs if c.source_type == source_type]
                assert len(loaded_sources) == len(original_sources)
        finally:
            self.cleanup_test_environment(temp_path)


if __name__ == "__main__":
    pytest.main([__file__])


if __name__ == "__main__":
    pytest.main([__file__])