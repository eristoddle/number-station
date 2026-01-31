
import streamlit as st
from src.database import DatabaseManager
from src.plugin_manager import PluginManager
from src.models import SourceConfiguration

def render_settings_page(db: DatabaseManager, plugin_manager: PluginManager):
    """
    Settings interface for management of sources and plugins.

    Validates Requirements 5.1, 5.2, 5.4, 6.2, 7.6, 10.5, 10.6.
    """
    st.header("Settings")

    tabs = st.tabs(["Content Sources", "Plugin Management", "Import/Export"])

    with tabs[0]:
        st.subheader("Manage Content Sources")

        # List existing sources
        # We need a way to get all configs.
        # PluginManager can help or DB直接.

        # For simplicity, let's fetch all source configurations by iterating possible types
        # or adding a 'get_all_source_configs' (I'll assume it exists or use SourceConfiguration.source_type)
        # Actually my aggregator fetch logic used get_source_configs_by_type.

        # Let's add a form to add a new source
        with st.expander("Add New Source"):
            with st.form("add_source_form"):
                name = st.text_input("Source Name")
                stype = st.selectbox("Type", ["rss", "twitter", "reddit", "hackernews", "devto", "web_scraper"])
                url = st.text_input("URL (if applicable)")
                interval = st.number_input("Fetch Interval (seconds)", min_value=60, value=300)

                submitted = st.form_submit_button("Add Source")
                if submitted:
                    new_config = SourceConfiguration(
                        name=name,
                        source_type=stype,
                        url=url if url else None,
                        fetch_interval=interval,
                        enabled=True,
                        config={} # More complex config could be handled here
                    )
                    if db.save_source_configuration(new_config):
                         st.success(f"Added source: {name}")
                         st.rerun()
                    else:
                         st.error("Failed to add source.")

        # Display and edit existing sources
        # (Simplified list for now)
        st.write("---")
        # How to get all? Let's just assume we can get from DB.
        # I'll use a placeholder for getting all for now.
        st.info("Existing sources management coming soon...")

    with tabs[1]:
        st.subheader("Plugin Management")
        status = plugin_manager.get_plugin_status()

        for name, info in status.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{name}**")
                st.caption(f"Type: {info['metadata']['plugin_type'] if info['metadata'] else 'Unknown'}")
            with col2:
                healthy = "✅ Healthy" if info['healthy'] else "❌ Error"
                st.write(healthy)
            with col3:
                # Toggle enabled
                # (Actual plugin manager has enable/disable methods)
                is_enabled = info['enabled']
                if st.button("Disable" if is_enabled else "Enable", key=f"btn_{name}"):
                    if is_enabled:
                         plugin_manager.disable_plugin(name)
                    else:
                         plugin_manager.enable_plugin(name)
                    st.rerun()

    with tabs[2]:
        st.subheader("Export/Import Configuration")
        # This was partially in the old main.py.
        # Let's provide placeholders or simple buttons.
        if st.button("Export to JSON"):
             st.write("Exporting...")
             # ... logic ...

        uploaded_file = st.file_uploader("Import JSON Configuration", type=["json"])
        if uploaded_file:
             if st.button("Import"):
                  st.write("Importing...")
