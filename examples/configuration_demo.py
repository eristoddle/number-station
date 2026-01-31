#!/usr/bin/env python3
"""
Number Station Configuration Management Demo

This script demonstrates the configuration management system capabilities
including save/load/validate methods, JSON persistence, and export/import functionality.
"""

import sys
import os
from pathlib import Path
import tempfile
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.configuration import ConfigurationManager
from src.database import DatabaseManager
from src.models import UserPreferences, SourceConfiguration


def demo_configuration_management():
    """Demonstrate configuration management capabilities."""
    print("🚀 Number Station Configuration Management Demo")
    print("=" * 50)

    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Initialize database and configuration manager
        db_path = temp_path / "demo.db"
        config_dir = temp_path / "config"

        print(f"📁 Using temporary directory: {temp_path}")

        db = DatabaseManager(db_path)
        config_manager = ConfigurationManager(db, config_dir)

        print("✅ Database and configuration manager initialized")

        # 1. Demonstrate saving configurations
        print("\n1️⃣ Saving Configurations")
        print("-" * 30)

        # Set up some test data
        prefs = UserPreferences(
            ui_mode="board",
            theme="dark",
            update_interval=600,
            auto_refresh=True
        )
        db.save_user_preferences(prefs)
        print(f"   📝 User preferences: {prefs.ui_mode} mode, {prefs.theme} theme")

        # Add a source configuration
        source_config = SourceConfiguration(
            name="demo_rss_feed",
            source_type="rss",
            url="https://example.com/feed.xml",
            fetch_interval=300,
            tags=["demo", "test"]
        )
        db.save_source_config(source_config)
        print(f"   📡 Source config: {source_config.name} ({source_config.source_type})")

        # Save all configurations
        if config_manager.save_config():
            print("   ✅ All configurations saved successfully")
        else:
            print("   ❌ Failed to save configurations")

        # 2. Demonstrate configuration validation
        print("\n2️⃣ Configuration Validation")
        print("-" * 30)

        # Valid configuration
        valid_prefs = {
            "ui_mode": "stream",
            "theme": "light",
            "update_interval": 300
        }

        try:
            if config_manager.validate_config("user_prefs", valid_prefs):
                print("   ✅ Valid user preferences configuration")
        except Exception as e:
            print(f"   ❌ Validation error: {e}")

        # Invalid configuration
        invalid_prefs = {
            "ui_mode": "invalid_mode",
            "theme": "default",
            "update_interval": 30  # Too low
        }

        try:
            config_manager.validate_config("user_prefs", invalid_prefs)
            print("   ❌ Should have failed validation")
        except Exception as e:
            print(f"   ✅ Correctly rejected invalid config: {e}")

        # 3. Demonstrate configuration export
        print("\n3️⃣ Configuration Export")
        print("-" * 30)

        export_path = temp_path / "exported_config.json"

        if config_manager.export_config(export_path, include_sensitive=False):
            print(f"   ✅ Configuration exported to: {export_path.name}")

            # Show export structure
            with open(export_path, 'r') as f:
                export_data = json.load(f)

            print(f"   📊 Export contains: {list(export_data.keys())}")
            print(f"   📅 Export timestamp: {export_data['export_metadata']['timestamp']}")
        else:
            print("   ❌ Failed to export configuration")

        # 4. Demonstrate configuration import
        print("\n4️⃣ Configuration Import")
        print("-" * 30)

        # Modify current configuration
        new_prefs = UserPreferences(
            ui_mode="stream",
            theme="light",
            update_interval=900
        )
        db.save_user_preferences(new_prefs)
        print(f"   📝 Modified preferences: {new_prefs.ui_mode} mode, {new_prefs.theme} theme")

        # Import original configuration
        if config_manager.import_config(export_path, merge=False):
            print("   ✅ Configuration imported successfully")

            # Verify restoration
            restored_prefs = db.get_user_preferences()
            print(f"   🔄 Restored preferences: {restored_prefs.ui_mode} mode, {restored_prefs.theme} theme")
        else:
            print("   ❌ Failed to import configuration")

        # 5. Demonstrate configuration status
        print("\n5️⃣ Configuration Status")
        print("-" * 30)

        status = config_manager.get_config_status()

        print(f"   📊 Database stats: {status['database_stats']}")

        print("   📁 Configuration files:")
        for name, info in status["config_files"].items():
            status_icon = "✅" if info["exists"] else "❌"
            print(f"      {status_icon} {name}: {info['size']} bytes")

        print("   🔍 Validation status:")
        for name, valid in status["validation_status"].items():
            if isinstance(valid, bool):
                status_icon = "✅" if valid else "❌"
                print(f"      {status_icon} {name}")

        # 6. Demonstrate backup and restore
        print("\n6️⃣ Backup and Restore")
        print("-" * 30)

        # Create backup
        backup_path = config_manager._create_config_backup()
        if backup_path:
            print(f"   💾 Backup created: {backup_path.name}")

        # Reset to defaults
        if config_manager.reset_to_defaults():
            print("   🔄 Reset to defaults completed")

            # Check current preferences
            default_prefs = db.get_user_preferences()
            print(f"   📝 Default preferences: {default_prefs.ui_mode} mode, {default_prefs.theme} theme")

        # Restore from backup
        if backup_path and config_manager.import_config(backup_path, merge=False):
            print("   ✅ Restored from backup")

            # Verify restoration
            restored_prefs = db.get_user_preferences()
            print(f"   🔄 Final preferences: {restored_prefs.ui_mode} mode, {restored_prefs.theme} theme")

        print("\n🎉 Configuration Management Demo Complete!")
        print("=" * 50)

        # Summary of capabilities
        print("\n📋 Configuration Management Capabilities:")
        print("   ✅ Save/Load configurations to/from JSON files")
        print("   ✅ Validate configuration data with detailed error messages")
        print("   ✅ Export configurations with optional sensitive data filtering")
        print("   ✅ Import configurations with merge or replace options")
        print("   ✅ Automatic backup creation before destructive operations")
        print("   ✅ Reset to default configurations")
        print("   ✅ Configuration status monitoring and reporting")
        print("   ✅ Round-trip persistence (save → load → equivalent config)")
        print("   ✅ Error handling and graceful degradation")
        print("   ✅ Support for all configuration types (user, plugin, source, system)")


if __name__ == "__main__":
    demo_configuration_management()