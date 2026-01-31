
import streamlit as st
from datetime import datetime
from src.models import ContentItem

def render_content_card(item: ContentItem):
    """
    Render a single content item as a card.

    Args:
        item: ContentItem to render
    """
    # Card container styling could be done with custom CSS,
    # but for native Streamlit we use containers/expanders/markdown.

    with st.container():
        # Header: Title + Source + Time
        # Using columns to layout metadata
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.markdown(f"### [{item.title}]({item.url})")
            st.caption(f"{item.source} • {item.author or 'Unknown Author'}")
        with col2:
            st.caption(item.timestamp.strftime("%Y-%m-%d %H:%M"))

        # Tags
        if item.tags:
            # Simple tag display
            tags_html = " ".join([f"`{tag}`" for tag in item.tags])
            st.markdown(tags_html)

        # Media (Image)
        # Display first image if available
        if item.media_urls:
            # Check if valid image url (simple check)
            img_url = item.media_urls[0]
            if img_url:
                try:
                    st.image(img_url, use_column_width=True)
                except Exception:
                    st.warning("Failed to load image")

        # Content snippet
        # Truncate if too long? Or expander.
        # Requirement 2.1: "chronological content feed"
        # We usually want a snippet with "read more" expansion.

        display_content = item.content
        if len(display_content) > 500:
            st.markdown(display_content[:500] + "...")
            with st.expander("Read More"):
                st.markdown(display_content)
        else:
            st.markdown(display_content)

        st.divider()

def render_sidebar_status(plugin_manager, db_manager):
    """Render system status in sidebar."""
    st.sidebar.subheader("System Status")

    # Plugin Health
    # We might want to cache this or update less frequently?
    # For now, real-time fetch on render.
    status = plugin_manager.get_plugin_status()

    healthy_count = sum(1 for p in status.values() if p['healthy'])
    total_count = len(status)

    st.sidebar.metric("Plugins Healthy", f"{healthy_count}/{total_count}")

    # Source Stats?
    stats = db_manager.get_database_stats()
    st.sidebar.metric("Total Items", stats.get('content_items', 0))
