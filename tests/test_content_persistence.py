
import pytest
from hypothesis import given, strategies as st
from datetime import datetime
import tempfile
import shutil
from pathlib import Path
import json

from src.database import DatabaseManager
from src.models import ContentItem

class TestContentPersistence:

    @pytest.fixture
    def db_manager(self):
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_content.db"
        manager = DatabaseManager(db_path)
        yield manager
        shutil.rmtree(temp_dir)

    @given(st.builds(ContentItem,
        id=st.text(min_size=1),
        source=st.text(min_size=1),
        source_type=st.text(min_size=1),
        title=st.text(min_size=1),
        content=st.text(),
        url=st.text(min_size=1),
        timestamp=st.datetimes(), # naive or aware? python sqlite adapter usually stores as string
        tags=st.lists(st.text()),
        media_urls=st.lists(st.text()),
        metadata=st.dictionaries(st.text(), st.text())
    ))
    def test_source_url_preservation(self, db_manager, item):
        """
        Property 33: Source URL Preservation.
        Verify URL is preserved exactly through DB round trip.
        """
        # Ensure timestamp is safe for comparison (sqlite ISO format microsecond precision differences)
        # We can accept minor loss of precision or require exact string match?
        # Let's focus on URL as per property.

        saved = db_manager.save_content_item(item)
        assert saved is True

        loaded = db_manager.get_content_item(item.id)
        assert loaded is not None
        assert loaded.url == item.url # Exact match required

        # Verify other critical fields
        assert loaded.source == item.source
        assert loaded.id == item.id

    @given(st.builds(ContentItem,
        id=st.text(min_size=1).filter(lambda x: x.strip() != ""),
        source=st.text(min_size=1),
        source_type=st.text(min_size=1),
        title=st.text(min_size=1),
        url=st.text(min_size=1),
        # Optional fields might be None or empty
        author=st.one_of(st.none(), st.text()),
        tags=st.one_of(st.none(), st.lists(st.text())),
        media_urls=st.one_of(st.none(), st.lists(st.text())),
        metadata=st.one_of(st.none(), st.dictionaries(st.text(), st.text()))
    ))
    def test_missing_field_graceful_handling_persistence(self, db_manager, item):
        """
        Property 34: Missing Field Graceful Handling (Persistence).
        Verify that items with None/Empty optional fields save/load correctly
        and are normalized to defaults if None.
        """
        # Note: ContentItem __post_init__ converts None to lists/dicts.
        # But if we manually bypass init or if DB stores NULL?
        # Database definition:
        # tags TEXT (JSON)
        # media_urls TEXT (JSON)
        # metadata TEXT (JSON)
        # If they are None in object, to_dict/save might handle them.

        # Ensure ID is valid (checked by filter).

        saved = db_manager.save_content_item(item)
        assert saved is True

        loaded = db_manager.get_content_item(item.id)
        assert loaded is not None

        # Check normalization
        assert isinstance(loaded.tags, list)
        assert isinstance(loaded.media_urls, list)
        assert isinstance(loaded.metadata, dict)

        if item.tags:
            assert loaded.tags == item.tags
        else:
            assert loaded.tags == [] # Normalized
