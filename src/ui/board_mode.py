
import streamlit as st
from src.database import DatabaseManager
from src.ui.components import render_content_card

def render_board_mode(db: DatabaseManager):
    """
    Render the board layout with multiple columns (lanes).

    Validates Requirements 2.2, 2.5, 2.6.
    """
    st.header("Board View")

    # Configure Lanes
    # For MVP, let's allow users to pick which source types or sources correspond to which lane
    # Or just show 3 columns: RSS, Social, Web

    col_options = ["RSS", "Twitter", "Reddit", "Hacker News", "Dev.to"]

    if 'board_lanes' not in st.session_state:
        st.session_state.board_lanes = ["RSS", "Twitter", "Reddit"]

    with st.expander("Configure Lanes"):
        new_lanes = st.multiselect("Select Lanes", col_options, default=st.session_state.board_lanes)
        if st.button("Update Board"):
            st.session_state.board_lanes = new_lanes
            st.rerun()

    if not st.session_state.board_lanes:
        st.info("Please select at least one lane to display.")
        return

    # Create Columns
    cols = st.columns(len(st.session_state.board_lanes))

    source_map = {
        "RSS": "rss",
        "Twitter": "twitter",
        "Reddit": "reddit",
        "Hacker News": "hackernews",
        "Dev.to": "devto"
    }

    for i, lane_name in enumerate(st.session_state.board_lanes):
        with cols[i]:
            st.subheader(lane_name)

            # Fetch items for this lane
            source_type = source_map.get(lane_name)
            items = db.get_content_items(source_type=source_type, limit=10, order_by="timestamp DESC")

            if not items:
                st.write("No items found.")
            else:
                for item in items:
                    # Smaller cards for board mode?
                    # We can use the same component for now, or a compact version
                    with st.container():
                        st.markdown(f"**[{item.title}]({item.url})**")
                        st.caption(f"{item.timestamp.strftime('%H:%M')} • {item.source}")
                        if item.media_urls:
                             st.image(item.media_urls[0], use_column_width=True)
                        st.markdown(item.content[:150] + "...")
                        st.divider()
