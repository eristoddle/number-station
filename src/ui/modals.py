
import streamlit as st
from datetime import datetime, timedelta
from src.models import ContentItem, ShareableContent, ScheduledPost
from src.database import get_database
import uuid

def render_modals(plugin_manager):
    """Render any active modals based on session state."""
    if 'active_modal' not in st.session_state or not st.session_state.active_modal:
        return

    item = st.session_state.get('action_item')
    if not item:
        st.session_state.active_modal = None
        return

    modal_type = st.session_state.active_modal

    # We use a container at the top of the app or a Dialog if available.
    # For compatibility, we'll use st.sidebar or a big container.
    # Better: use st.expander or similar in the main area.

    with st.container(border=True):
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.subheader(f"{modal_type.capitalize()}: {item.title}")
        with col2:
            if st.button("✖️", key="close_modal"):
                st.session_state.active_modal = None
                st.rerun()

        if modal_type == "share":
            render_share_modal(item, plugin_manager)
        elif modal_type == "schedule":
            render_schedule_modal(item, plugin_manager)
        elif modal_type == "collect":
            render_collect_modal(item)
        elif modal_type == "preview":
            render_preview_modal(item)

def render_share_modal(item: ContentItem, plugin_manager):
    st.write("Share this content to social media.")

    destinations = plugin_manager.get_destination_plugins()
    if not destinations:
        st.warning("No destination plugins enabled. Go to Settings to enable them.")
        return

    dest_names = [d.metadata.name for d in destinations]
    selected_dest_name = st.selectbox("Select Destination", dest_names)
    selected_dest = next(d for d in destinations if d.metadata.name == selected_dest_name)

    # Capabilities
    caps = selected_dest.get_capabilities()

    default_text = f"{item.title}\n{item.url}"
    share_text = st.text_area("Share Text", value=default_text[:caps.max_length], max_chars=caps.max_length)
    st.caption(f"{len(share_text)} / {caps.max_length} characters")

    native_reshare = False
    if selected_dest.supports_reshare(item.source_type):
        native_reshare = st.checkbox(f"Use native reshare (e.g. Retweet)", value=True)

    if st.button("Share Now", type="primary"):
        with st.spinner("Sharing..."):
            if native_reshare:
                result = selected_dest.reshare(item)
            else:
                shareable = ShareableContent(content_item=item, text=share_text)
                result = selected_dest.post_content(shareable)

            if result.success:
                st.success(f"Successfully shared! [View Post]({result.url})")
            else:
                st.error(f"Failed to share: {result.error}")

def render_schedule_modal(item: ContentItem, plugin_manager):
    st.write("Schedule this content for later.")

    destinations = plugin_manager.get_destination_plugins()
    if not destinations:
        st.warning("No destination plugins enabled.")
        return

    selected_dest_name = st.selectbox("Select Destination", [d.metadata.name for d in destinations])

    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", value=datetime.now().date())
    with col2:
        time = st.time_input("Time", value=(datetime.now() + timedelta(hours=1)).time())

    scheduled_datetime = datetime.combine(date, time)

    recurrence = st.selectbox("Recurrence", [None, "daily", "weekly"])

    default_text = f"{item.title}\n{item.url}"
    share_text = st.text_area("Post Content", value=default_text)

    if st.button("Schedule Post", type="primary"):
        db = get_database()
        # Find destination plugin class/internal name
        dest_plugin = next(d for d in destinations if d.metadata.name == selected_dest_name)
        plugin_internal_name = f"{dest_plugin.__class__.__module__}.{dest_plugin.__class__.__name__}"

        new_post = ScheduledPost(
            id=str(uuid.uuid4()),
            destination_plugin=plugin_internal_name,
            content=ShareableContent(content_item=item, text=share_text),
            scheduled_time=scheduled_datetime,
            recurrence=recurrence,
            status="pending"
        )

        if db.save_scheduled_post(new_post):
            st.success(f"Post scheduled for {scheduled_datetime}")
            time.sleep(1)
            st.session_state.active_modal = None
            st.rerun()
        else:
            st.error("Failed to save scheduled post.")

def render_collect_modal(item: ContentItem):
    st.write("Add this item to a curation collection.")
    db = get_database()
    collections = db.get_content_collections()

    if not collections:
        st.info("No collections found. Create one first.")
        new_name = st.text_input("New Collection Name")
        if st.button("Create and Add"):
            coll_id = str(uuid.uuid4())
            new_coll = ContentCollection(id=coll_id, name=new_name, item_ids=[item.id])
            if db.save_content_collection(new_coll):
                st.success(f"Created '{new_name}' and added item.")
                st.session_state.active_modal = None
                st.rerun()
    else:
        coll_names = [c.name for c in collections]
        selected_coll_name = st.selectbox("Select Collection", coll_names)

        if st.button("Add to Collection", type="primary"):
            coll = next(c for c in collections if c.name == selected_coll_name)
            if item.id not in coll.item_ids:
                coll.item_ids.append(item.id)
                coll.updated_at = datetime.now()
                if db.save_content_collection(coll):
                    st.success(f"Added to {selected_coll_name}")
                    st.session_state.active_modal = None
                    st.rerun()
                else:
                    st.error("Failed to update collection.")
            else:
                st.info("Item already in collection.")

def render_preview_modal(item: ContentItem):
    st.markdown(f"## {item.title}")
    st.markdown(f"**Source:** {item.source} | **Author:** {item.author}")
    st.markdown(f"**Date:** {item.timestamp}")
    st.markdown(f"**URL:** [{item.url}]({item.url})")

    if item.media_urls:
        st.image(item.media_urls, caption="Media Assets")

    st.divider()
    st.markdown(item.content)

    if item.metadata:
        with st.expander("Raw Metadata"):
            st.json(item.metadata)
