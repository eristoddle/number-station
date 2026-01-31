
import streamlit as st
from datetime import datetime
from src.database import DatabaseManager
from src.ui.components import render_content_card

def render_stream_mode(db: DatabaseManager):
    """
    Render the chronological content stream.

    Validates Requirements 2.1, 2.4.
    """
    st.header("Stream Feed")

    # Filter Controls
    col1, col2 = st.columns([2, 1])
    with col1:
        search_query = st.text_input("Search", placeholder="Search content...", key="stream_search")
    with col2:
        # Get unique source types for filter
        # Ideally cached or queried efficiently
        source_type_filter = st.selectbox("Source Type", ["All", "rss", "twitter", "reddit", "hackernews", "devto", "web_scraper", "custom"])

    # Query Data
    # We rely on db.get_content_items which supports limit, offset, source_type.
    # We interpret "search" as... filtering in DB?
    # Current DB implementation only filters by exact source/source_type.
    # Implementing full text search in SQLite requires FTS5 or simple LIKE.
    # Current `get_content_items` doesn't implement search parameter.
    # I will assume for MVP we fetch and filter in memory OR I update DB later.
    # The requirement 2.4 says "content filtering and search".
    # I should pass parameters to get_content_items.
    # But `get_content_items` signature is currently:
    # (source, source_type, limit, offset, order_by)
    # I will stick to what's available and maybe filter in memory for 'search' until DB is updated.

    limit = st.number_input("Items to show", min_value=10, max_value=100, value=20)

    filter_type = None if source_type_filter == "All" else source_type_filter

    items = db.get_content_items(
        source_type=filter_type,
        limit=limit,
        order_by="timestamp DESC"
    )

    # In-memory search filter (naive) if search term exists
    if search_query:
        query = search_query.lower()
        items = [i for i in items if query in i.title.lower() or query in i.content.lower()]

    # Render
    if not items:
        st.info("No content found matching your criteria.")
    else:
        for item in items:
            render_content_card(item)
