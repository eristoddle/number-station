
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
from src.ui.components import render_sidebar_status

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

    # Session State for Mode
    if 'ui_mode' not in st.session_state:
        # Load from user prefs
        prefs = db.get_user_preferences()
        st.session_state.ui_mode = prefs.ui_mode

    # Manual Fetch Trigger
    with st.sidebar:
        st.header("Actions")
        if st.button("🔄 Refresh Content"):
            with st.spinner("Fetching content..."):
                results = aggregator.fetch_all()
                total_new = sum(results.values())
                if total_new > 0:
                    st.success(f"Fetched {total_new} new items!")
                    time.sleep(1) # Show success message briefly
                    st.rerun()
                else:
                    st.info("No new content found.")

        # Mode Switcher
        mode = st.radio(
            "View Mode",
            ["Stream", "Board"],
            index=0 if st.session_state.ui_mode == "stream" else 1
        )

        # Update state if changed
        selected_mode = mode.lower()
        if selected_mode != st.session_state.ui_mode:
            st.session_state.ui_mode = selected_mode
            # Save preference?
            # Yes, per requirement "Implement session state management for UI mode switching"
            # It implies persistence? UserPrefs stores it.
            # Ideally we update UserPrefs DB too, or just session.
            # Let's simple session for now, user manually saves prefs in settings page.
            st.rerun()

        st.divider()
        render_sidebar_status(plugin_manager, db)

    # Render Main View
    if st.session_state.ui_mode == "stream":
        render_stream_mode(db)
    elif st.session_state.ui_mode == "board":
        render_board_mode(db)
    else:
        st.error(f"Unknown mode: {st.session_state.ui_mode}")

if __name__ == "__main__":
    main()