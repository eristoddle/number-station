
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
        # Selection and Title
        col_select, col_title, col_time = st.columns([0.05, 0.75, 0.2])
        with col_select:
            st.checkbox("", key=f"select_{item.id}", label_visibility="collapsed")

        with col_title:
            st.markdown(f"### [{item.title}]({item.url})")
            st.caption(f"{item.source} • {item.author or 'Unknown Author'}")
        with col_time:
            st.caption(item.timestamp.strftime("%Y-%m-%d %H:%M"))

        # Tags
        if item.tags:
            tags_html = " ".join([f"`{tag}`" for tag in item.tags])
            st.markdown(tags_html)

        # Media
        if item.media_urls:
            img_url = item.media_urls[0]
            if img_url:
                try:
                    st.image(img_url, use_column_width=True)
                except Exception:
                    pass

        # Content snippet
        display_content = item.content
        if len(display_content) > 500:
            st.markdown(display_content[:500] + "...")
            with st.expander("Read More"):
                st.markdown(display_content)
        else:
            st.markdown(display_content)

        # Action Buttons
        act_col1, act_col2, act_col3, act_col4, _ = st.columns([0.1, 0.1, 0.1, 0.1, 0.6])
        with act_col1:
            if st.button("📤", key=f"share_{item.id}", help="Share"):
                st.session_state.action_item = item
                st.session_state.active_modal = "share"
                st.rerun()
        with act_col2:
            if st.button("📅", key=f"sched_{item.id}", help="Schedule"):
                st.session_state.action_item = item
                st.session_state.active_modal = "schedule"
                st.rerun()
        with act_col3:
            if st.button("📥", key=f"collect_{item.id}", help="Collect"):
                st.session_state.action_item = item
                st.session_state.active_modal = "collect"
                st.rerun()
        with act_col4:
            if st.button("👁️", key=f"preview_{item.id}", help="Preview"):
                st.session_state.action_item = item
                st.session_state.active_modal = "preview"
                st.rerun()

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
