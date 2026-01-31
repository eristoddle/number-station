#!/usr/bin/env python3
"""
Number Station - Configuration Management System

This module provides centralized configuration management with save/load/validate methods,
JSON-based configuration persistence, and configuration export/import functionality.

Validates Requirements 1.4, 10.1, 10.2, 10.3, 10.5, 10.6:
- Configuration persistence across sessions
- User preferences persistence
- Plugin configurations persistence
- Source configurations persistence
- Configuration export functionality
- Configuration import functionality
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import asdict
import shutil
import tempfile

from .models import UserPreferences, PluginMetadata, SourceConfiguration
from .database import DatabaseManager


class ConfigurationValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigurationManager:
    """
    Centralized configuration management system.

    Provides save/load/validate methods for all configuration types,
    JSON-based persistence, and export/import functionality.
    """

    def __init__(self, db_manager: DatabaseManager, config_dir: Union[str, Path] = "config"):
        """
        Initialize configuration manager.

        Args:
            db_manager: Database manager instance
            config_dir: Directory for configuration files
        """
        self.db = db_manager
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

        # Configuration file paths
        self.user_prefs_file = self.config_dir / "user_preferences.json"
        self.plugin_configs_file = self.config_dir / "plugin_configs.json"
        self.source_configs_file = self.config_dir / "source_configs.json"
        self.system_config_file = self.config_dir / "system_config.json"

        # Default system configuration
        self.default_system_config = {
            "version": "1.0.0",
            "database_path": "data/number_station.db",
            "log_level": "INFO",
            "max_content_age_days": 30,
            "default_fetch_interval": 300,
            "max_concurrent_fetches": 5,
            "rate_limit_requests_per_minute": 60,
            "ui_settings": {
                "default_items_per_page": 50,
                "max_items_per_page": 200,
                "enable_auto_refresh": True,
                "refresh_interval_seconds": 30
            },
            "security": {
                "enable_content_sanitization": True,
                "allowed_media_types": ["image/jpeg", "image/png", "image/gif", "image/webp"],
                "max_content_length": 1000000  # 1MB
            }
        }

    def save_config(self) -> bool:
        """
        Save all configurations to persistent storage.

        Returns:
            bool: True if all configurations saved successfully, False otherwise
        """
        try:
            success = True

            # Save user preferences
            if not self._save_user_preferences():
                success = False
                self.logger.error("Failed to save user preferences")

            # Save plugin configurations
            if not self._save_plugin_configs():
                success = False
                self.logger.error("Failed to save plugin configurations")

            # Save source configurations
            if not self._save_source_configs():
                success = False
                self.logger.error("Failed to save source configurations")

            # Save system configuration
            if not self._save_system_config():
                success = False
                self.logger.error("Failed to save system configuration")

            if success:
                self.logger.info("All configurations saved successfully")
            else:
                self.logger.error("Some configurations failed to save")

            return success

        except Exception as e:
            self.logger.error(f"Error saving configurations: {e}")
            return False

    def load_config(self) -> bool:
        """
        Load all configurations from persistent storage.

        Returns:
            bool: True if all configurations loaded successfully, False otherwise
        """
        try:
            success = True

            # Load user preferences
            if not self._load_user_preferences():
                success = False
                self.logger.warning("Failed to load user preferences, using defaults")

            # Load plugin configurations
            if not self._load_plugin_configs():
                success = False
                self.logger.warning("Failed to load plugin configurations")

            # Load source configurations
            if not self._load_source_configs():
                success = False
                self.logger.warning("Failed to load source configurations")

            # Load system configuration
            if not self._load_system_config():
                success = False
                self.logger.warning("Failed to load system configuration, using defaults")

            if success:
                self.logger.info("All configurations loaded successfully")
            else:
                self.logger.warning("Some configurations failed to load, using defaults where applicable")

            return success

        except Exception as e:
            self.logger.error(f"Error loading configurations: {e}")
            return False

    def validate_config(self, config_type: str, config_data: Dict[str, Any]) -> bool:
        """
        Validate configuration data for a specific type.

        Args:
            config_type: Type of configuration ('user_prefs', 'plugin', 'source', 'system')
            config_data: Configuration data to validate

        Returns:
            bool: True if configuration is valid, False otherwise

        Raises:
            ConfigurationValidationError: If validation fails with details
        """
        try:
            if config_type == "user_prefs":
                return self._validate_user_preferences(config_data)
            elif config_type == "plugin":
                return self._validate_plugin_config(config_data)
            elif config_type == "source":
                return self._validate_source_config(config_data)
            elif config_type == "system":
                return self._validate_system_config(config_data)
            else:
                raise ConfigurationValidationError(f"Unknown configuration type: {config_type}")

        except Exception as e:
            self.logger.error(f"Configuration validation error for {config_type}: {e}")
            raise ConfigurationValidationError(f"Validation failed for {config_type}: {e}")

    def export_config(self, export_path: Union[str, Path], include_sensitive: bool = False) -> bool:
        """
        Export all configurations to a JSON file.

        Args:
            export_path: Path to export file
            include_sensitive: Whether to include sensitive data (API keys, etc.)

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            export_path = Path(export_path)
            export_data = {
                "export_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "version": "1.0.0",
                    "include_sensitive": include_sensitive
                },
                "user_preferences": {},
                "plugin_configs": {},
                "source_configs": {},
                "system_config": {}
            }

            # Export user preferences
            user_prefs = self.db.get_user_preferences()
            export_data["user_preferences"] = user_prefs.to_dict()

            # Export plugin configurations
            plugin_configs = self.db.get_all_plugin_configs()
            if not include_sensitive:
                # Filter out sensitive data from plugin configs
                plugin_configs = self._filter_sensitive_plugin_data(plugin_configs)
            export_data["plugin_configs"] = plugin_configs

            # Export source configurations
            source_configs = {}
            # Get all source types from database
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT source_type FROM source_configurations")
                source_types = [row[0] for row in cursor.fetchall()]

            for source_type in source_types:
                # Get ALL configurations for this type, not just enabled ones
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM source_configurations WHERE source_type = ?",
                        (source_type,)
                    )
                    rows = cursor.fetchall()
                    configs = [SourceConfiguration.from_dict(dict(row)) for row in rows]

                source_configs[source_type] = []
                for config in configs:
                    config_dict = config.to_dict()
                    if not include_sensitive:
                        # Filter out sensitive data from source configs
                        config_dict = self._filter_sensitive_source_data(config_dict)
                    source_configs[source_type].append(config_dict)

            export_data["source_configs"] = source_configs

            # Export system configuration
            system_config = self._get_system_config()
            if not include_sensitive:
                # Filter out sensitive system data
                system_config = self._filter_sensitive_system_data(system_config)
            export_data["system_config"] = system_config

            # Write to file
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Configuration exported successfully to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting configuration: {e}")
            return False

    def import_config(self, import_path: Union[str, Path], merge: bool = True) -> bool:
        """
        Import configurations from a JSON file.

        Args:
            import_path: Path to import file
            merge: If True, merge with existing config; if False, replace entirely

        Returns:
            bool: True if import successful, False otherwise
        """
        try:
            import_path = Path(import_path)
            if not import_path.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")

            # Create backup before import
            backup_path = self._create_config_backup()
            if not backup_path:
                self.logger.warning("Failed to create backup before import")

            # Load import data
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # Validate import data structure
            if not self._validate_import_data(import_data):
                raise ConfigurationValidationError("Invalid import data structure")

            success = True

            # Import user preferences
            if "user_preferences" in import_data:
                if not self._import_user_preferences(import_data["user_preferences"], merge):
                    success = False

            # Import plugin configurations
            if "plugin_configs" in import_data:
                if not self._import_plugin_configs(import_data["plugin_configs"], merge):
                    success = False

            # Import source configurations
            if "source_configs" in import_data:
                if not self._import_source_configs(import_data["source_configs"], merge):
                    success = False

            # Import system configuration
            if "system_config" in import_data:
                if not self._import_system_config(import_data["system_config"], merge):
                    success = False

            if success:
                self.logger.info(f"Configuration imported successfully from {import_path}")
            else:
                self.logger.error("Some configurations failed to import")
                # Restore from backup if available
                if backup_path and backup_path.exists():
                    self.logger.info("Attempting to restore from backup")
                    self.import_config(backup_path, merge=False)

            return success

        except Exception as e:
            self.logger.error(f"Error importing configuration: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """
        Reset all configurations to default values.

        Returns:
            bool: True if reset successful, False otherwise
        """
        try:
            # Create backup before reset
            backup_path = self._create_config_backup()
            if backup_path:
                self.logger.info(f"Created backup before reset: {backup_path}")

            # Reset user preferences
            default_prefs = UserPreferences()
            if not self.db.save_user_preferences(default_prefs):
                self.logger.error("Failed to reset user preferences")
                return False

            # Clear plugin configurations
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM plugin_configs")
                conn.commit()

            # Clear source configurations
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM source_configurations")
                conn.commit()

            # Reset system configuration
            if not self._save_system_config(self.default_system_config):
                self.logger.error("Failed to reset system configuration")
                return False

            # Remove configuration files
            for config_file in [self.user_prefs_file, self.plugin_configs_file,
                              self.source_configs_file, self.system_config_file]:
                if config_file.exists():
                    config_file.unlink()

            self.logger.info("All configurations reset to defaults")
            return True

        except Exception as e:
            self.logger.error(f"Error resetting configurations: {e}")
            return False

    def get_config_status(self) -> Dict[str, Any]:
        """
        Get status information about all configurations.

        Returns:
            Dict containing configuration status information
        """
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "database_stats": self.db.get_database_stats(),
                "config_files": {},
                "validation_status": {}
            }

            # Check configuration files
            config_files = {
                "user_preferences": self.user_prefs_file,
                "plugin_configs": self.plugin_configs_file,
                "source_configs": self.source_configs_file,
                "system_config": self.system_config_file
            }

            for name, path in config_files.items():
                status["config_files"][name] = {
                    "exists": path.exists(),
                    "size": path.stat().st_size if path.exists() else 0,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else None
                }

            # Validate current configurations
            try:
                user_prefs = self.db.get_user_preferences()
                status["validation_status"]["user_preferences"] = self.validate_config("user_prefs", user_prefs.to_dict())
            except Exception as e:
                status["validation_status"]["user_preferences"] = f"Error: {e}"

            try:
                system_config = self._get_system_config()
                status["validation_status"]["system_config"] = self.validate_config("system", system_config)
            except Exception as e:
                status["validation_status"]["system_config"] = f"Error: {e}"

            return status

        except Exception as e:
            self.logger.error(f"Error getting configuration status: {e}")
            return {"error": str(e)}

    # Private helper methods

    def _save_user_preferences(self) -> bool:
        """Save user preferences to JSON file."""
        try:
            user_prefs = self.db.get_user_preferences()
            prefs_data = user_prefs.to_dict()

            with open(self.user_prefs_file, 'w', encoding='utf-8') as f:
                json.dump(prefs_data, f, indent=2)

            return True
        except Exception as e:
            self.logger.error(f"Error saving user preferences to file: {e}")
            return False

    def _load_user_preferences(self) -> bool:
        """Load user preferences from JSON file."""
        try:
            if not self.user_prefs_file.exists():
                return True  # No file to load, use database defaults

            with open(self.user_prefs_file, 'r', encoding='utf-8') as f:
                prefs_data = json.load(f)

            # Validate and create preferences object
            if self.validate_config("user_prefs", prefs_data):
                user_prefs = UserPreferences.from_dict(prefs_data)
                return self.db.save_user_preferences(user_prefs)

            return False
        except Exception as e:
            self.logger.error(f"Error loading user preferences from file: {e}")
            return False

    def _save_plugin_configs(self) -> bool:
        """Save plugin configurations to JSON file."""
        try:
            plugin_configs = self.db.get_all_plugin_configs()

            with open(self.plugin_configs_file, 'w', encoding='utf-8') as f:
                json.dump(plugin_configs, f, indent=2)

            return True
        except Exception as e:
            self.logger.error(f"Error saving plugin configs to file: {e}")
            return False

    def _load_plugin_configs(self) -> bool:
        """Load plugin configurations from JSON file."""
        try:
            if not self.plugin_configs_file.exists():
                return True  # No file to load

            with open(self.plugin_configs_file, 'r', encoding='utf-8') as f:
                plugin_configs = json.load(f)

            # Load each plugin configuration
            success = True
            for plugin_name, config_data in plugin_configs.items():
                if not self.db.save_plugin_config(
                    plugin_name,
                    config_data.get('config', {}),
                    config_data.get('enabled', True)
                ):
                    success = False

            return success
        except Exception as e:
            self.logger.error(f"Error loading plugin configs from file: {e}")
            return False

    def _save_source_configs(self) -> bool:
        """Save source configurations to JSON file."""
        try:
            # Get all source configurations (including disabled ones)
            source_configs = {}
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT source_type FROM source_configurations")
                source_types = [row[0] for row in cursor.fetchall()]

            for source_type in source_types:
                # Get ALL configurations for this type, not just enabled ones
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM source_configurations WHERE source_type = ?",
                        (source_type,)
                    )
                    rows = cursor.fetchall()
                    configs = [SourceConfiguration.from_dict(dict(row)) for row in rows]

                source_configs[source_type] = [config.to_dict() for config in configs]

            with open(self.source_configs_file, 'w', encoding='utf-8') as f:
                json.dump(source_configs, f, indent=2)

            return True
        except Exception as e:
            self.logger.error(f"Error saving source configs to file: {e}")
            return False

    def _load_source_configs(self) -> bool:
        """Load source configurations from JSON file."""
        try:
            if not self.source_configs_file.exists():
                return True  # No file to load

            with open(self.source_configs_file, 'r', encoding='utf-8') as f:
                source_configs = json.load(f)

            # Load each source configuration
            success = True
            for source_type, configs in source_configs.items():
                for config_data in configs:
                    try:
                        source_config = SourceConfiguration.from_dict(config_data)
                        if not self.db.save_source_config(source_config):
                            success = False
                    except Exception as e:
                        self.logger.error(f"Error loading source config {config_data.get('name', 'unknown')}: {e}")
                        success = False

            return success
        except Exception as e:
            self.logger.error(f"Error loading source configs from file: {e}")
            return False

    def _save_system_config(self, config_data: Optional[Dict[str, Any]] = None) -> bool:
        """Save system configuration to JSON file."""
        try:
            if config_data is None:
                config_data = self._get_system_config()

            with open(self.system_config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)

            return True
        except Exception as e:
            self.logger.error(f"Error saving system config to file: {e}")
            return False

    def _load_system_config(self) -> bool:
        """Load system configuration from JSON file."""
        try:
            if not self.system_config_file.exists():
                # Create default system config
                return self._save_system_config(self.default_system_config)

            with open(self.system_config_file, 'r', encoding='utf-8') as f:
                system_config = json.load(f)

            # Validate system configuration
            return self.validate_config("system", system_config)
        except Exception as e:
            self.logger.error(f"Error loading system config from file: {e}")
            return False

    def _get_system_config(self) -> Dict[str, Any]:
        """Get current system configuration."""
        try:
            if self.system_config_file.exists():
                with open(self.system_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self.default_system_config.copy()
        except Exception:
            return self.default_system_config.copy()

    def _validate_user_preferences(self, config_data: Dict[str, Any]) -> bool:
        """Validate user preferences configuration."""
        required_fields = ['ui_mode', 'theme', 'update_interval']

        for field in required_fields:
            if field not in config_data:
                raise ConfigurationValidationError(f"Missing required field: {field}")

        # Validate specific values
        if config_data['ui_mode'] not in ['stream', 'board']:
            raise ConfigurationValidationError(f"Invalid ui_mode: {config_data['ui_mode']}")

        if not isinstance(config_data['update_interval'], int) or config_data['update_interval'] < 60:
            raise ConfigurationValidationError("update_interval must be an integer >= 60")

        return True

    def _validate_plugin_config(self, config_data: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        if not isinstance(config_data, dict):
            raise ConfigurationValidationError("Plugin config must be a dictionary")

        for plugin_name, plugin_config in config_data.items():
            if not isinstance(plugin_config, dict):
                raise ConfigurationValidationError(f"Plugin config for {plugin_name} must be a dictionary")

            if 'enabled' in plugin_config and not isinstance(plugin_config['enabled'], bool):
                raise ConfigurationValidationError(f"Plugin {plugin_name} 'enabled' must be boolean")

        return True

    def _validate_source_config(self, config_data: Dict[str, Any]) -> bool:
        """Validate source configuration."""
        required_fields = ['name', 'source_type']

        for field in required_fields:
            if field not in config_data:
                raise ConfigurationValidationError(f"Missing required field: {field}")

        if 'fetch_interval' in config_data:
            if not isinstance(config_data['fetch_interval'], int) or config_data['fetch_interval'] < 60:
                raise ConfigurationValidationError("fetch_interval must be an integer >= 60")

        return True

    def _validate_system_config(self, config_data: Dict[str, Any]) -> bool:
        """Validate system configuration."""
        required_fields = ['version', 'database_path']

        for field in required_fields:
            if field not in config_data:
                raise ConfigurationValidationError(f"Missing required field: {field}")

        return True

    def _filter_sensitive_plugin_data(self, plugin_configs: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from plugin configurations."""
        filtered = {}
        sensitive_keys = ['api_key', 'secret', 'token', 'password', 'credential']

        for plugin_name, config in plugin_configs.items():
            filtered_config = {'enabled': config.get('enabled', True), 'config': {}}

            for key, value in config.get('config', {}).items():
                if not any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                    filtered_config['config'][key] = value
                else:
                    filtered_config['config'][key] = "***FILTERED***"

            filtered[plugin_name] = filtered_config

        return filtered

    def _filter_sensitive_source_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from source configurations."""
        filtered = config_data.copy()
        sensitive_keys = ['api_key', 'secret', 'token', 'password', 'credential']

        if 'config' in filtered and isinstance(filtered['config'], str):
            try:
                config_dict = json.loads(filtered['config'])
                for key in list(config_dict.keys()):
                    if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                        config_dict[key] = "***FILTERED***"
                filtered['config'] = json.dumps(config_dict)
            except json.JSONDecodeError:
                pass

        return filtered

    def _filter_sensitive_system_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from system configuration."""
        # System config typically doesn't contain sensitive data, but filter just in case
        return config_data.copy()

    def _validate_import_data(self, import_data: Dict[str, Any]) -> bool:
        """Validate the structure of import data."""
        required_sections = ['export_metadata']

        for section in required_sections:
            if section not in import_data:
                raise ConfigurationValidationError(f"Missing required section: {section}")

        # Check metadata
        metadata = import_data['export_metadata']
        if 'timestamp' not in metadata or 'version' not in metadata:
            raise ConfigurationValidationError("Invalid export metadata")

        return True

    def _import_user_preferences(self, prefs_data: Dict[str, Any], merge: bool) -> bool:
        """Import user preferences."""
        try:
            if self.validate_config("user_prefs", prefs_data):
                if merge:
                    # Merge with existing preferences
                    current_prefs = self.db.get_user_preferences()
                    current_dict = current_prefs.to_dict()
                    current_dict.update(prefs_data)
                    user_prefs = UserPreferences.from_dict(current_dict)
                else:
                    user_prefs = UserPreferences.from_dict(prefs_data)

                return self.db.save_user_preferences(user_prefs)
            return False
        except Exception as e:
            self.logger.error(f"Error importing user preferences: {e}")
            return False

    def _import_plugin_configs(self, plugin_configs: Dict[str, Any], merge: bool) -> bool:
        """Import plugin configurations."""
        try:
            if not merge:
                # Clear existing plugin configs
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM plugin_configs")
                    conn.commit()

            # Import each plugin configuration
            success = True
            for plugin_name, config_data in plugin_configs.items():
                if not self.db.save_plugin_config(
                    plugin_name,
                    config_data.get('config', {}),
                    config_data.get('enabled', True)
                ):
                    success = False

            return success
        except Exception as e:
            self.logger.error(f"Error importing plugin configs: {e}")
            return False

    def _import_source_configs(self, source_configs: Dict[str, Any], merge: bool) -> bool:
        """Import source configurations."""
        try:
            if not merge:
                # Clear existing source configs
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM source_configurations")
                    conn.commit()

            # Import each source configuration
            success = True
            for source_type, configs in source_configs.items():
                for config_data in configs:
                    try:
                        source_config = SourceConfiguration.from_dict(config_data)
                        if not self.db.save_source_config(source_config):
                            success = False
                    except Exception as e:
                        self.logger.error(f"Error importing source config {config_data.get('name', 'unknown')}: {e}")
                        success = False

            return success
        except Exception as e:
            self.logger.error(f"Error importing source configs: {e}")
            return False

    def _import_system_config(self, system_config: Dict[str, Any], merge: bool) -> bool:
        """Import system configuration."""
        try:
            if self.validate_config("system", system_config):
                if merge:
                    # Merge with existing system config
                    current_config = self._get_system_config()
                    current_config.update(system_config)
                    return self._save_system_config(current_config)
                else:
                    return self._save_system_config(system_config)
            return False
        except Exception as e:
            self.logger.error(f"Error importing system config: {e}")
            return False

    def _create_config_backup(self) -> Optional[Path]:
        """Create a backup of current configuration."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.config_dir / "backups"
            backup_dir.mkdir(exist_ok=True)

            backup_path = backup_dir / f"config_backup_{timestamp}.json"

            if self.export_config(backup_path, include_sensitive=True):
                return backup_path
            return None
        except Exception as e:
            self.logger.error(f"Error creating config backup: {e}")
            return None


# Global configuration manager instance
_config_manager = None


def get_configuration_manager(db_manager: Optional[DatabaseManager] = None) -> ConfigurationManager:
    """
    Get the global configuration manager instance.

    Args:
        db_manager: Database manager instance (optional, will use default if not provided)

    Returns:
        ConfigurationManager: Global configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        if db_manager is None:
            from .database import get_database
            db_manager = get_database()
        _config_manager = ConfigurationManager(db_manager)
    return _config_manager