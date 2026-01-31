#!/usr/bin/env python3
"""
Number Station - Content Aggregation Dashboard
Main application entry point
"""

import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_database
from src.models import ContentItem, UserPreferences
from src.migrations import run_migrations, get_migration_status
from src.configuration import get_configuration_manager


def initialize_database():
    """Initialize database and run migrations."""
    try:
        db = get_database()

        # Run migrations
        migration_success = run_migrations(db)
        if migration_success:
            st.success("✅ Database initialized successfully")
        else:
            st.error("❌ Database migration failed")

        # Initialize configuration manager
        config_manager = get_configuration_manager(db)

        # Load existing configurations
        config_load_success = config_manager.load_config()
        if config_load_success:
            st.success("✅ Configuration loaded successfully")
        else:
            st.warning("⚠️ Some configurations failed to load, using defaults")

        return db, config_manager
    except Exception as e:
        st.error(f"❌ Database initialization failed: {e}")
        return None, None


def show_database_status(db):
    """Show database status and statistics."""
    st.subheader("📊 Database Status")

    # Migration status
    migration_status = get_migration_status(db)
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Applied Migrations", migration_status['applied_count'])
        st.metric("Pending Migrations", migration_status['pending_count'])

    with col2:
        if migration_status['current_version']:
            st.metric("Current Version", migration_status['current_version'])
        if migration_status['latest_version']:
            st.metric("Latest Version", migration_status['latest_version'])

    # Database statistics
    stats = db.get_database_stats()
    st.subheader("📈 Content Statistics")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Content Items", stats.get('content_items', 0))
    with col2:
        st.metric("Source Configs", stats.get('source_configurations', 0))
    with col3:
        st.metric("Plugin Configs", stats.get('plugin_configs', 0))


def show_sample_content(db):
    """Show sample content and allow adding test data."""
    st.subheader("📝 Content Management")

    # Add sample content button
    if st.button("Add Sample Content"):
        sample_items = [
            ContentItem(
                id=f"sample-{datetime.now().timestamp()}",
                source="Sample RSS Feed",
                source_type="rss",
                title="Welcome to Number Station",
                content="This is a sample content item to demonstrate the database functionality.",
                author="Number Station Team",
                timestamp=datetime.now(),
                url="https://example.com/welcome",
                tags=["welcome", "sample"],
                media_urls=[],
                metadata={"category": "announcement"}
            ),
            ContentItem(
                id=f"sample-tech-{datetime.now().timestamp()}",
                source="Tech News",
                source_type="rss",
                title="Latest Technology Trends",
                content="Exploring the latest trends in technology and software development.",
                author="Tech Reporter",
                timestamp=datetime.now(),
                url="https://example.com/tech-trends",
                tags=["technology", "trends"],
                media_urls=["https://example.com/tech-image.jpg"],
                metadata={"category": "technology", "word_count": 500}
            )
        ]

        for item in sample_items:
            if db.save_content_item(item):
                st.success(f"✅ Added: {item.title}")
            else:
                st.error(f"❌ Failed to add: {item.title}")

        st.rerun()

    # Display existing content
    content_items = db.get_content_items(limit=10)

    if content_items:
        st.subheader("Recent Content")
        for item in content_items:
            with st.expander(f"{item.title} ({item.source_type})"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**Source:** {item.source}")
                    st.write(f"**Author:** {item.author or 'Unknown'}")
                    st.write(f"**Content:** {item.content[:200]}...")
                    if item.tags:
                        st.write(f"**Tags:** {', '.join(item.tags)}")

                with col2:
                    st.write(f"**Type:** {item.source_type}")
                    st.write(f"**Time:** {item.timestamp.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**URL:** [Link]({item.url})")
    else:
        st.info("No content items found. Click 'Add Sample Content' to get started.")


def show_user_preferences(db, config_manager):
    """Show and manage user preferences."""
    st.subheader("⚙️ User Preferences")

    # Load current preferences
    current_prefs = db.get_user_preferences()

    # Create form for preferences
    with st.form("preferences_form"):
        ui_mode = st.selectbox(
            "UI Mode",
            ["stream", "board"],
            index=0 if current_prefs.ui_mode == "stream" else 1
        )

        theme = st.selectbox(
            "Theme",
            ["default", "dark", "light"],
            index=["default", "dark", "light"].index(current_prefs.theme)
        )

        update_interval = st.number_input(
            "Update Interval (seconds)",
            min_value=60,
            max_value=3600,
            value=current_prefs.update_interval,
            step=60
        )

        auto_refresh = st.checkbox(
            "Auto Refresh",
            value=current_prefs.auto_refresh
        )

        submitted = st.form_submit_button("Save Preferences")

        if submitted:
            new_prefs = UserPreferences(
                ui_mode=ui_mode,
                theme=theme,
                update_interval=update_interval,
                auto_refresh=auto_refresh
            )

            if db.save_user_preferences(new_prefs):
                # Also save to configuration files
                config_manager.save_config()
                st.success("✅ Preferences saved successfully")
                st.rerun()
            else:
                st.error("❌ Failed to save preferences")
    """Show configuration management interface."""
    st.subheader("⚙️ Configuration Management")

    # Configuration status
    status = config_manager.get_config_status()

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Configuration Files Status:**")
        for name, info in status["config_files"].items():
            status_icon = "✅" if info["exists"] else "❌"
            st.write(f"{status_icon} {name.replace('_', ' ').title()}")
            if info["exists"]:
                st.write(f"   Size: {info['size']} bytes")
                if info["modified"]:
                    st.write(f"   Modified: {info['modified'][:19]}")

    with col2:
        st.write("**Validation Status:**")
        for name, valid in status["validation_status"].items():
            if isinstance(valid, bool):
                status_icon = "✅" if valid else "❌"
                st.write(f"{status_icon} {name.replace('_', ' ').title()}")
            else:
                st.write(f"❌ {name.replace('_', ' ').title()}: {valid}")

    st.divider()

    # Configuration operations
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("💾 Save All Config"):
            if config_manager.save_config():
                st.success("✅ All configurations saved")
                st.rerun()
            else:
                st.error("❌ Failed to save configurations")

    with col2:
        if st.button("🔄 Reload Config"):
            if config_manager.load_config():
                st.success("✅ Configurations reloaded")
                st.rerun()
            else:
                st.error("❌ Failed to reload configurations")

    with col3:
        if st.button("🔄 Reset to Defaults"):
            if st.session_state.get('confirm_reset', False):
                if config_manager.reset_to_defaults():
                    st.success("✅ Reset to defaults completed")
                    st.session_state.confirm_reset = False
                    st.rerun()
                else:
                    st.error("❌ Failed to reset configurations")
            else:
                st.session_state.confirm_reset = True
                st.warning("⚠️ Click again to confirm reset to defaults")

    with col4:
        if st.button("📊 Show Status"):
            st.json(status)

    st.divider()

    # Export/Import section
    st.subheader("📤 Export/Import Configuration")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Export Configuration**")
        include_sensitive = st.checkbox("Include sensitive data (API keys, etc.)", value=False)

        if st.button("📤 Export Configuration"):
            import tempfile
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_filename = f"number_station_config_{timestamp}.json"

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                if config_manager.export_config(tmp_file.name, include_sensitive=include_sensitive):
                    with open(tmp_file.name, 'r') as f:
                        config_data = f.read()

                    st.download_button(
                        label="💾 Download Configuration",
                        data=config_data,
                        file_name=export_filename,
                        mime="application/json"
                    )
                    st.success("✅ Configuration exported successfully")
                else:
                    st.error("❌ Failed to export configuration")

    with col2:
        st.write("**Import Configuration**")
        uploaded_file = st.file_uploader("Choose configuration file", type=['json'])
        merge_config = st.checkbox("Merge with existing configuration", value=True)

        if uploaded_file is not None:
            if st.button("📥 Import Configuration"):
                import tempfile

                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue().decode('utf-8'))
                    tmp_file.flush()

                    if config_manager.import_config(tmp_file.name, merge=merge_config):
                        st.success("✅ Configuration imported successfully")
                        st.rerun()
                    else:
                        st.error("❌ Failed to import configuration")

    # Configuration validation
    st.divider()
    st.subheader("🔍 Configuration Validation")

    validation_type = st.selectbox(
        "Select configuration type to validate",
        ["user_prefs", "plugin", "source", "system"]
    )

    validation_data = st.text_area(
        "Enter configuration JSON to validate",
        height=150,
        placeholder='{"ui_mode": "stream", "theme": "default", "update_interval": 300}'
    )

    if st.button("✅ Validate Configuration"):
        if validation_data.strip():
            try:
                import json
                config_data = json.loads(validation_data)

                if config_manager.validate_config(validation_type, config_data):
                    st.success("✅ Configuration is valid")
                else:
                    st.error("❌ Configuration is invalid")
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {e}")
            except Exception as e:
                st.error(f"❌ Validation error: {e}")
        else:
            st.warning("⚠️ Please enter configuration data to validate")


def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Number Station",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("📡 Number Station")
    st.subheader("Content Aggregation Dashboard")

    # Initialize database and configuration
    db, config_manager = initialize_database()

    if db is None or config_manager is None:
        st.error("Cannot continue without database and configuration. Please check the error messages above.")
        return

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Overview", "Database Status", "Content Management", "User Preferences", "Configuration Management"]
    )

    if page == "Overview":
        st.markdown("""
        ### Welcome to Number Station

        This is a comprehensive dashboard tool for content aggregation and curation.

        **Features implemented:**
        - ✅ Core data models (ContentItem, UserPreferences, etc.)
        - ✅ SQLite database schema with full CRUD operations
        - ✅ Database migration system
        - ✅ Configuration management system with JSON persistence
        - ✅ Configuration export/import functionality
        - ✅ Configuration validation and backup system
        - ✅ Comprehensive test coverage

        **Features in development:**
        - 🚧 RSS feed aggregation
        - 🚧 Social media integration
        - 🚧 Dual UI modes (Stream & Board)
        - 🚧 Extensible plugin architecture
        - 🚧 Customizable themes

        **Current Status:** Core infrastructure and configuration management completed ✅
        """)

        # Show quick stats
        stats = db.get_database_stats()
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Content Items", stats.get('content_items', 0))
        with col2:
            st.metric("Configurations", stats.get('source_configurations', 0))
        with col3:
            st.metric("Plugins", stats.get('plugin_configs', 0))

        # Show configuration status
        st.divider()
        config_status = config_manager.get_config_status()
        st.subheader("📋 Configuration Status")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**Configuration Files:**")
            for name, info in config_status["config_files"].items():
                status_icon = "✅" if info["exists"] else "❌"
                st.write(f"{status_icon} {name.replace('_', ' ').title()}")

        with col2:
            st.write("**Validation Status:**")
            for name, valid in config_status["validation_status"].items():
                if isinstance(valid, bool):
                    status_icon = "✅" if valid else "❌"
                    st.write(f"{status_icon} {name.replace('_', ' ').title()}")

    elif page == "Database Status":
        show_database_status(db)

    elif page == "Content Management":
        show_sample_content(db)

    elif page == "User Preferences":
        show_user_preferences(db, config_manager)

    elif page == "Configuration Management":
        show_configuration_management(config_manager)

    # Show project structure in sidebar
    with st.sidebar.expander("📁 Project Structure"):
        st.code("""
        number-station/
        ├── src/
        │   ├── models.py         ✅ Data models
        │   ├── database.py       ✅ Database manager
        │   ├── migrations.py     ✅ Migration system
        │   ├── configuration.py  ✅ Config management
        │   └── main.py           ✅ Main application
        ├── plugins/              📁 Plugin modules
        ├── config/               ✅ Configuration files
        ├── tests/                ✅ Test suite
        ├── data/                 📁 Data storage
        └── requirements.txt      ✅ Dependencies
        """)

    # Show configuration actions in sidebar
    with st.sidebar.expander("⚙️ Quick Config Actions"):
        if st.button("💾 Save All Config", key="sidebar_save"):
            if config_manager.save_config():
                st.success("✅ Saved")
            else:
                st.error("❌ Failed")

        if st.button("🔄 Reload Config", key="sidebar_reload"):
            if config_manager.load_config():
                st.success("✅ Reloaded")
            else:
                st.error("❌ Failed")


if __name__ == "__main__":
    main()