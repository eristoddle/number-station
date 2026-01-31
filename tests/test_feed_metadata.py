
import pytest
from hypothesis import given, strategies as st
from datetime import datetime
import tempfile
import shutil
from pathlib import Path

from src.models import SourceMetadata
from src.database import DatabaseManager

class TestFeedMetadata:

    @pytest.fixture
    def db_manager(self):
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_metadata.db"
        manager = DatabaseManager(db_path)
        yield manager
        shutil.rmtree(temp_dir)

    @given(st.builds(SourceMetadata,
        source_id=st.text(min_size=1),
        last_fetch_attempt=st.datetimes(),
        last_fetch_success=st.one_of(st.none(), st.datetimes()),
        last_item_count=st.integers(min_value=0),
        total_items_fetched=st.integers(min_value=0),
        error_count=st.integers(min_value=0),
        consecutive_errors=st.integers(min_value=0),
        last_error=st.one_of(st.none(), st.text())
    ))
    def test_metadata_round_trip(self, db_manager, metadata):
        """
        Property 14: Feed Metadata Accuracy.
        Verify that metadata can be saved and retrieved without loss.
        """
        # Save
        assert db_manager.save_source_metadata(metadata) is True

        # Load
        loaded = db_manager.get_source_metadata(metadata.source_id)

        assert loaded is not None
        assert loaded.source_id == metadata.source_id
        assert loaded.last_item_count == metadata.last_item_count
        assert loaded.error_count == metadata.error_count

        # Check timestamps roughly (isoformat conversion can lose precision)
        # We stored as ISO strings in DB (wait, sqlite handles datetime if adapter registered?)
        # Base implementation uses execute parameters.
        # But we didn't register adapter?
        # Wait, DatabaseManager init sets parsers:
        # sqlite3.connect(..., detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        # And table definition: last_fetch_attempt DATETIME NOT NULL
        # So sqlite3 handles it if we pass datetime objects.
        # But SourceMetadata.to_dict converts to isoformat string!
        # And from_dict parses it back.
        # So it relies on isoformat details.

        assert loaded.last_fetch_attempt == metadata.last_fetch_attempt
        assert loaded.last_fetch_success == metadata.last_fetch_success
