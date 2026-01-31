
import streamlit as st
from datetime import datetime
from src.database import get_database
from src.models import ContentCollection
import uuid

def render_collections_page(db_manager, plugin_manager):
    st.header("📚 Content Collections")

    # Sidebar or top actions
    with st.expander("➕ Create New Collection"):
        with st.form("new_collection"):
            name = st.text_input("Collection Name")
            desc = st.text_area("Description")
            submitted = st.form_submit_button("Create")
            if submitted and name:
                new_coll = ContentCollection(
                    id=str(uuid.uuid4()),
                    name=name,
                    description=desc
                )
                if db_manager.save_content_collection(new_coll):
                    st.success(f"Created collection '{name}'")
                    st.rerun()

    collections = db_manager.get_content_collections()

    if not collections:
        st.info("No collections yet. Create your first curation collection above.")
        return

    # List collections
    for coll in collections:
        with st.container(border=True):
            col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
            with col1:
                st.subheader(coll.name)
                st.write(coll.description)
            with col2:
                st.metric("Items", len(coll.item_ids))
            with col3:
                if st.button("View / Edit", key=f"view_{coll.id}"):
                    st.session_state.selected_collection_id = coll.id
                    st.rerun()

    # Detail View
    if 'selected_collection_id' in st.session_state:
        render_collection_detail(st.session_state.selected_collection_id, db_manager, plugin_manager)


def render_collection_detail(coll_id, db_manager, plugin_manager):
    coll = db_manager.get_content_collection(coll_id)
    if not coll:
        st.error("Collection not found.")
        return

    st.divider()
    col_h1, col_h2 = st.columns([0.7, 0.3])
    with col_h1:
        st.header(f"Editing: {coll.name}")
    with col_h2:
        # Export Button
        if st.button("📄 Export to Markdown"):
            from src.markdown_generator import MarkdownGenerator
            items = []
            for item_id in coll.item_ids:
                item = db_manager.get_content_item(item_id)
                if item:
                    items.append(item)

            gen = MarkdownGenerator()
            md_content = gen.generate(coll, items)

            st.download_button(
                label="Download .md file",
                data=md_content,
                file_name=f"{coll.name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )

    # AI Generation Section
    st.subheader("🤖 AI Curation Tools")
    ai_plugins = plugin_manager.get_ai_plugins()
    if ai_plugins:
        ai_col1, ai_col2 = st.columns(2)
        with ai_col1:
            if st.button("✨ Generate Intro"):
                render_ai_generation(coll, "intro", ai_plugins[0])
        with ai_col2:
            if st.button("📝 Generate Summary"):
                render_ai_generation(coll, "summary", ai_plugins[0])
    else:
        st.warning("No AI plugins enabled.")

    # List items
    st.subheader("Items in Collection")
    if not coll.item_ids:
        st.info("This collection is empty.")
    else:
        for item_id in coll.item_ids:
            item = db_manager.get_content_item(item_id)
            if item:
                with st.container():
                    col1, col2 = st.columns([0.9, 0.1])
                    with col1:
                        st.write(f"**{item.title}** ({item.source})")
                    with col2:
                        if st.button("🗑️", key=f"del_{coll.id}_{item.id}"):
                            coll.item_ids.remove(item_id)
                            db_manager.save_content_collection(coll)
                            st.rerun()
            else:
                st.warning(f"Item {item_id} not found in database.")

    if st.button("Delete Collection", type="secondary"):
        if db_manager.delete_content_collection(coll.id):
            del st.session_state.selected_collection_id
            st.rerun()

def render_ai_generation(coll, gen_type, ai_plugin):
    db = get_database()
    items = []
    for item_id in coll.item_ids:
        item = db.get_content_item(item_id)
        if item:
            items.append(item)

    if not items:
        st.error("Collection is empty, cannot generate.")
        return

    with st.spinner(f"Generating {gen_type}..."):
        if gen_type == "intro":
            prompt = f"Write a compelling introduction for a collection of articles about: {coll.name}. The collection contains: " + ", ".join([i.title for i in items])
            result = ai_plugin.generate_text(prompt)
        else:
            result = ai_plugin.summarize_items(items)

        st.session_state[f"ai_gen_{gen_type}"] = result
        st.rerun()

    if f"ai_gen_{gen_type}" in st.session_state:
        st.text_area(f"Generated {gen_type.capitalize()}", value=st.session_state[f"ai_gen_{gen_type}"], height=200)
        if st.button(f"Save {gen_type} to Collection Metadata"):
            coll.metadata[f"ai_{gen_type}"] = st.session_state[f"ai_gen_{gen_type}"]
            db.save_content_collection(coll)
            st.success("Saved!")
