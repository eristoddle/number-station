
import pytest
import json
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st
from src.configuration import ConfigurationManager
from unittest.mock import MagicMock

class TestConfigConsistency:

    @pytest.fixture
    def config_manager(self):
        db = MagicMock()
        # Mock DB methods for loading/saving
        db.get_user_preferences.return_value = MagicMock()
        db.get_all_plugin_configs.return_value = {}
        db.get_all_source_configs.return_value = []

        # We need a temporary config path
        with tempfile.TemporaryDirectory() as tmp_dir:
            mgr = ConfigurationManager(db, config_path=Path(tmp_dir))
            yield mgr

    def test_export_import_roundtrip(self, config_manager):
        """
        Property 35: Configuration Export/Import Consistency.
        """
        # 1. Setup initial config
        config_manager.user_prefs.theme = "dark"
        config_manager.user_prefs.ui_mode = "board"

        # 2. Export
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = Path(f.name)
            config_manager.export_config(export_path)

        # 3. Modify current config to something else
        config_manager.user_prefs.theme = "light"

        # 4. Import back
        config_manager.import_config(export_path)

        # 5. Verify consistency
        assert config_manager.user_prefs.theme == "dark"
        assert config_manager.user_prefs.ui_mode == "board"

        export_path.unlink()
