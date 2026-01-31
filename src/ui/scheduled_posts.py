
import streamlit as st
from datetime import datetime
from src.database import get_database
from src.models import ScheduledPost

def render_scheduled_posts_page(db_manager, plugin_manager):
    st.header("📅 Scheduled Posts")

    status_filter = st.selectbox("Filter by Status", [None, "pending", "success", "failed", "executing", "cancelled"])

    posts = db_manager.get_scheduled_posts(status=status_filter)

    if not posts:
        st.info("No scheduled posts found.")
        return

    for post in posts:
        with st.container(border=True):
            col1, col2, col3 = st.columns([0.5, 0.25, 0.25])

            with col1:
                st.write(f"**To:** {post.destination_plugin.split('.')[-1]}")
                st.write(f"**Content:** {post.content.text[:100]}...")
                st.caption(f"Scheduled for: {post.scheduled_time}")

            with col2:
                status_colors = {
                    "pending": "blue",
                    "success": "green",
                    "failed": "red",
                    "executing": "orange",
                    "cancelled": "grey"
                }
                color = status_colors.get(post.status, "white")
                st.markdown(f"Status: **:{color}[{post.status.upper()}]**")
                if post.retry_count > 0:
                    st.caption(f"Retries: {post.retry_count}")

            with col3:
                if post.status == "pending":
                    if st.button("Cancel", key=f"cancel_{post.id}"):
                        post.status = "cancelled"
                        db_manager.save_scheduled_post(post)
                        st.rerun()

                if st.button("Delete", key=f"del_post_{post.id}"):
                    db_manager.delete_scheduled_post(post.id)
                    st.rerun()

            if post.last_error:
                with st.expander("Show Error"):
                    st.error(post.last_error)

            if post.result_url:
                st.markdown(f"[View Live Post]({post.result_url})")
