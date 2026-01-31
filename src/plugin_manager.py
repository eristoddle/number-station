#!/usr/bin/env python3
"""
Number Station - Plugin Manager

This module provides the PluginManager class that integrates the plugin registry
with the database and configuration systems. It handles plugin lifecycle management,
configuration persistence, and error isolation.

Validates Requirements 6.1, 6.2, 6.3, 7.1, 7.2, 7.7:
- Plugin registry system
- Plugin lifecycle management (initialize, start, stop, cleanup)
- Plugin compatibility validation and error isolation
- Plugin registration endpoints
- Plugin lifecycle management
- Plugin API compliance validation
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import traceback

from .plugins import PluginRegistry, SourcePlugin, FilterPlugin, ThemePlugin, PluginValidationError, PluginCompatibilityError
from .models import PluginMetadata
from .database import DatabaseManager


class PluginManager:
    """
    Manages plugin lifecycle, configuration, and integration with the database.

    Provides high-level plugin management functionality including loading,
    configuration, enabling/disabling, and error isolation.
    """

    def __init__(self, db_manager: DatabaseManager, plugin_dirs: Optional[List[Path]] = None):
        """
        Initialize the plugin manager.

        Args:
            db_manager: Database manager instance
            plugin_dirs: List of directories to search for plugins
        """
        self.logger = logging.getLogger(__name__)
        self.db = db_manager
        self.registry = PluginRegistry()
        self.plugin_dirs = plugin_dirs or [Path("plugins")]

        # Plugin state tracking
        self._plugin_health: Dict[str, bool] = {}
        self._plugin_errors: Dict[str, List[str]] = {}

    def initialize_plugins(self) -> bool:
        """
        Initialize the plugin system.

        Discovers available plugins, loads enabled plugins from database,
        and starts them according to their configuration.

        Returns:
            bool: True if initialization was successful, False otherwise

        Validates Requirements 1.2:
        - WHEN the application starts, THE Number_Station SHALL initialize all enabled plugins
        """
        try:
            self.logger.info("Initializing plugin system")

            # Discover available plugins
            discovered = self.registry.discover_plugins(self.plugin_dirs)
            self.logger.info(f"Discovered {len(discovered)} plugins")

            # Load plugin configurations from database
            plugin_configs = self.db.get_all_plugin_configs()

            # Load and start enabled plugins
            success_count = 0
            for plugin_name in discovered:
                try:
                    # Check if plugin has configuration in database
                    config = plugin_configs.get(plugin_name, {})
                    enabled = config.get('enabled', True)
                    plugin_config = config.get('config', {})

                    if enabled:
                        if self.load_plugin(plugin_name, plugin_config):
                            if self.start_plugin(plugin_name):
                                success_count += 1
                                self._plugin_health[plugin_name] = True
                            else:
                                self._plugin_health[plugin_name] = False
                        else:
                            self._plugin_health[plugin_name] = False
                    else:
                        self.logger.info(f"Plugin {plugin_name} is disabled, skipping")

                except Exception as e:
                    self.logger.error(f"Error initializing plugin {plugin_name}: {e}")
                    self._plugin_health[plugin_name] = False
                    self._add_plugin_error(plugin_name, str(e))

            self.logger.info(f"Successfully initialized {success_count} plugins")
            return success_count > 0 or len(discovered) == 0  # Success if we loaded some plugins or there were none to load

        except Exception as e:
            self.logger.error(f"Error initializing plugin system: {e}")
            return False

    def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load a plugin with configuration.

        Args:
            plugin_name: Name of the plugin to load
            config: Optional configuration for the plugin

        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            # Load plugin through registry
            if not self.registry.load_plugin(plugin_name, config):
                return False

            # Get plugin instance and save metadata to database
            plugin_instance = self.registry.get_plugin(plugin_name)
            if plugin_instance:
                metadata = plugin_instance.metadata
                self.db.save_plugin_metadata(metadata)

                # Save configuration if provided
                if config:
                    self.db.save_plugin_config(plugin_name, config, True)

            self.logger.info(f"Loaded plugin: {plugin_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name}: {e}")
            self._add_plugin_error(plugin_name, str(e))
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            bool: True if unloading was successful, False otherwise
        """
        try:
            # Stop plugin first
            self.stop_plugin(plugin_name)

            # Unload through registry
            if self.registry.unload_plugin(plugin_name):
                # Clean up health tracking
                if plugin_name in self._plugin_health:
                    del self._plugin_health[plugin_name]
                if plugin_name in self._plugin_errors:
                    del self._plugin_errors[plugin_name]

                self.logger.info(f"Unloaded plugin: {plugin_name}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_name}: {e}")
            self._add_plugin_error(plugin_name, str(e))
            return False

    def start_plugin(self, plugin_name: str) -> bool:
        """
        Start a loaded plugin.

        Args:
            plugin_name: Name of the plugin to start

        Returns:
            bool: True if starting was successful, False otherwise
        """
        try:
            plugin_instance = self.registry.get_plugin(plugin_name)
            if not plugin_instance:
                self.logger.error(f"Plugin not loaded: {plugin_name}")
                return False

            if plugin_instance.start():
                self._plugin_health[plugin_name] = True
                self.logger.info(f"Started plugin: {plugin_name}")
                return True
            else:
                self._plugin_health[plugin_name] = False
                return False

        except Exception as e:
            self.logger.error(f"Error starting plugin {plugin_name}: {e}")
            self._plugin_health[plugin_name] = False
            self._add_plugin_error(plugin_name, str(e))
            return False

    def stop_plugin(self, plugin_name: str) -> bool:
        """
        Stop a running plugin.

        Args:
            plugin_name: Name of the plugin to stop

        Returns:
            bool: True if stopping was successful, False otherwise
        """
        try:
            plugin_instance = self.registry.get_plugin(plugin_name)
            if not plugin_instance:
                self.logger.warning(f"Plugin not loaded: {plugin_name}")
                return True  # Already stopped

            if plugin_instance.stop():
                self.logger.info(f"Stopped plugin: {plugin_name}")
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"Error stopping plugin {plugin_name}: {e}")
            self._add_plugin_error(plugin_name, str(e))
            return False

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a plugin (load and start if not already running).

        Args:
            plugin_name: Name of the plugin to enable

        Returns:
            bool: True if enabling was successful, False otherwise
        """
        try:
            # Update database configuration
            config = self.db.get_plugin_config(plugin_name) or {'config': {}, 'enabled': False}
            config['enabled'] = True

            if not self.db.save_plugin_config(plugin_name, config['config'], True):
                return False

            # Load and start plugin if not already loaded
            plugin_instance = self.registry.get_plugin(plugin_name)
            if not plugin_instance:
                if not self.load_plugin(plugin_name, config['config']):
                    return False

            return self.start_plugin(plugin_name)

        except Exception as e:
            self.logger.error(f"Error enabling plugin {plugin_name}: {e}")
            self._add_plugin_error(plugin_name, str(e))
            return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a plugin (stop and update configuration).

        Args:
            plugin_name: Name of the plugin to disable

        Returns:
            bool: True if disabling was successful, False otherwise
        """
        try:
            # Stop plugin
            self.stop_plugin(plugin_name)

            # Update database configuration
            config = self.db.get_plugin_config(plugin_name) or {'config': {}, 'enabled': True}
            config['enabled'] = False

            return self.db.save_plugin_config(plugin_name, config['config'], False)

        except Exception as e:
            self.logger.error(f"Error disabling plugin {plugin_name}: {e}")
            self._add_plugin_error(plugin_name, str(e))
            return False

    def configure_plugin(self, plugin_name: str, config: Dict[str, Any]) -> bool:
        """
        Configure a plugin with new settings.

        Args:
            plugin_name: Name of the plugin to configure
            config: New configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        try:
            plugin_instance = self.registry.get_plugin(plugin_name)
            if not plugin_instance:
                self.logger.error(f"Plugin not loaded: {plugin_name}")
                return False

            # Validate configuration
            if not plugin_instance.validate_config(config):
                self.logger.error(f"Invalid configuration for plugin {plugin_name}")
                return False

            # Apply configuration
            if not plugin_instance.configure(config):
                self.logger.error(f"Failed to configure plugin {plugin_name}")
                return False

            # Save to database
            current_config = self.db.get_plugin_config(plugin_name) or {'enabled': True}
            enabled = current_config.get('enabled', True)

            if self.db.save_plugin_config(plugin_name, config, enabled):
                self.logger.info(f"Configured plugin: {plugin_name}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error configuring plugin {plugin_name}: {e}")
            self._add_plugin_error(plugin_name, str(e))
            return False

    def get_source_plugins(self) -> List[SourcePlugin]:
        """
        Get all enabled source plugins.

        Returns:
            List of enabled SourcePlugin instances
        """
        return self.registry.get_plugins_by_type('source')

    def get_filter_plugins(self) -> List[FilterPlugin]:
        """
        Get all enabled filter plugins.

        Returns:
            List of enabled FilterPlugin instances
        """
        return self.registry.get_plugins_by_type('filter')

    def get_theme_plugins(self) -> List[ThemePlugin]:
        """
        Get all enabled theme plugins.

        Returns:
            List of enabled ThemePlugin instances
        """
        return self.registry.get_plugins_by_type('theme')

    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all plugins.

        Returns:
            Dict mapping plugin names to their status information
        """
        status = {}

        # Get all available plugins
        available_plugins = self.registry.list_available_plugins()
        loaded_plugins = self.registry.list_loaded_plugins()

        for plugin_name in available_plugins:
            plugin_instance = self.registry.get_plugin(plugin_name)
            metadata = self.registry.get_plugin_metadata(plugin_name)

            status[plugin_name] = {
                'loaded': plugin_name in loaded_plugins,
                'enabled': plugin_instance.enabled if plugin_instance else False,
                'healthy': self._plugin_health.get(plugin_name, False),
                'errors': self._plugin_errors.get(plugin_name, []),
                'metadata': metadata.to_dict() if metadata else None
            }

        return status

    def get_plugin_health(self, plugin_name: str) -> bool:
        """
        Check if a plugin is healthy (running without errors).

        Args:
            plugin_name: Name of the plugin to check

        Returns:
            bool: True if plugin is healthy, False otherwise
        """
        return self._plugin_health.get(plugin_name, False)

    def get_plugin_errors(self, plugin_name: str) -> List[str]:
        """
        Get error messages for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            List of error messages
        """
        return self._plugin_errors.get(plugin_name, [])

    def clear_plugin_errors(self, plugin_name: str) -> None:
        """
        Clear error messages for a plugin.

        Args:
            plugin_name: Name of the plugin
        """
        if plugin_name in self._plugin_errors:
            del self._plugin_errors[plugin_name]

    def _add_plugin_error(self, plugin_name: str, error_message: str) -> None:
        """
        Add an error message for a plugin.

        Args:
            plugin_name: Name of the plugin
            error_message: Error message to add
        """
        if plugin_name not in self._plugin_errors:
            self._plugin_errors[plugin_name] = []

        self._plugin_errors[plugin_name].append(error_message)

        # Keep only the last 10 errors per plugin
        if len(self._plugin_errors[plugin_name]) > 10:
            self._plugin_errors[plugin_name] = self._plugin_errors[plugin_name][-10:]

    def test_plugin_connection(self, plugin_name: str) -> bool:
        """
        Test connection for a source plugin.

        Args:
            plugin_name: Name of the source plugin to test

        Returns:
            bool: True if connection test passed, False otherwise
        """
        try:
            plugin_instance = self.registry.get_plugin(plugin_name)
            if not plugin_instance:
                self.logger.error(f"Plugin not loaded: {plugin_name}")
                return False

            if not isinstance(plugin_instance, SourcePlugin):
                self.logger.error(f"Plugin {plugin_name} is not a source plugin")
                return False

            return plugin_instance.test_connection()

        except Exception as e:
            self.logger.error(f"Error testing plugin connection {plugin_name}: {e}")
            self._add_plugin_error(plugin_name, f"Connection test failed: {str(e)}")
            return False

    def shutdown(self) -> bool:
        """
        Shutdown the plugin system.

        Stops and unloads all plugins in a safe manner.

        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        try:
            self.logger.info("Shutting down plugin system")

            loaded_plugins = self.registry.list_loaded_plugins()
            success_count = 0

            for plugin_name in loaded_plugins:
                try:
                    if self.unload_plugin(plugin_name):
                        success_count += 1
                except Exception as e:
                    self.logger.error(f"Error shutting down plugin {plugin_name}: {e}")

            self.logger.info(f"Successfully shut down {success_count}/{len(loaded_plugins)} plugins")
            return success_count == len(loaded_plugins)

        except Exception as e:
            self.logger.error(f"Error shutting down plugin system: {e}")
            return False