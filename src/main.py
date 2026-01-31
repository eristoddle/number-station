
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
import time

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_database
from src.configuration import get_configuration_manager
from src.plugin_manager import PluginManager
from src.aggregator import ContentAggregator
from src.ui.stream_mode import render_stream_mode
from src.ui.board_mode import render_board_mode
from src.ui.settings import render_settings_page
from src.ui.components import render_sidebar_status
from src.ui.collections import render_collections_page
from src.ui.scheduled_posts import render_scheduled_posts_page
from src.ui.modals import render_modals

# Initialize core systems (cached)
@st.cache_resource
def get_core_systems():
    db = get_database()
    config_manager = get_configuration_manager(db)
    config_manager.load_config()

    plugin_manager = PluginManager(db)
    plugin_manager.initialize_plugins()

    aggregator = ContentAggregator(plugin_manager, db)

    return db, config_manager, plugin_manager, aggregator

def main():
    st.set_page_config(
        page_title="Number Station",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize Headers & Styling
    st.title("📡 Number Station")

    # Get Systems
    try:
        db, config_manager, plugin_manager, aggregator = get_core_systems()
    except Exception as e:
        st.error(f"Critical System Error: {e}")
        return

    # Render Modals (if any active)
    render_modals(plugin_manager)

    # Session State for Mode
    if 'ui_mode' not in st.session_state:
        # Load from user prefs
        prefs = db.get_user_preferences()
        st.session_state.ui_mode = prefs.ui_mode

    # Sidebar: Actions, Mode, Theme
    with st.sidebar:
        st.header("Actions")
        if st.button("🔄 Refresh Content"):
            with st.spinner("Fetching content..."):
                results = aggregator.fetch_all()
                total_new = sum(results.values())
                if total_new > 0:
                    st.success(f"Fetched {total_new} new items!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.info("No new content found.")

        st.divider()
        st.header("Navigation")

        # View Selection
        view_tabs = ["Stream", "Board", "Collections", "Scheduled", "Settings"]
        current_view = st.session_state.get('current_view', "Stream")
        view = st.radio(
            "Go to",
            view_tabs,
            index=view_tabs.index(current_view) if current_view in view_tabs else 0
        )

        if view != current_view:
            st.session_state.current_view = view
            if view in ["Stream", "Board"]:
                 st.session_state.ui_mode = view.lower()
            st.rerun()

        # Theme Switcher
        themes = plugin_manager.get_theme_plugins()
        theme_names = [t.metadata.name for t in themes]
        if not theme_names:
            theme_names = ["Default"]

        selected_theme_name = st.selectbox("UI Theme", theme_names)

        # Apply CSS for the selected theme
        active_theme = next((t for t in themes if t.metadata.name == selected_theme_name), None)
        if active_theme:
            st.markdown(f"<style>{active_theme.get_css()}</style>", unsafe_allow_html=True)

        st.divider()
        render_sidebar_status(plugin_manager, db)

    # Render Main View
    view = st.session_state.get('current_view', "Stream")
    if view == "Stream":
        render_stream_mode(db)
    elif view == "Board":
        render_board_mode(db)
    elif view == "Collections":
        render_collections_page(db, plugin_manager)
    elif view == "Scheduled":
        render_scheduled_posts_page(db, plugin_manager)
    elif view == "Settings":
        render_settings_page(db, plugin_manager)
    else:
        st.error(f"Unknown view: {view}")

if __name__ == "__main__":
    main()