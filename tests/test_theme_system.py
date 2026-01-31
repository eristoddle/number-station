
import pytest
from hypothesis import given, strategies as st
from unittest.mock import MagicMock
from src.plugins import UIContext
from plugins.default_theme import DefaultTheme

class TestThemeSystem:

    def test_theme_plugin_interface(self):
        """
        Property 27: Theme Loading and Application.
        Ensures theme plugins implement the required interface.
        """
        theme = DefaultTheme()
        assert theme.metadata.plugin_type == "theme"
        assert callable(theme.get_css)
        assert callable(theme.apply_theme)

    def test_default_theme_compatibility(self):
        """
        Property 29: Default Theme Compatibility.
        """
        theme = DefaultTheme()
        assert theme.supports_mode("stream")
        assert theme.supports_mode("board")

        # Test CSS generation
        css = theme.get_css()
        assert isinstance(css, str)
        assert ".content-card" in css

    @given(st.sampled_from(["stream", "board"]))
    def test_apply_theme_to_context(self, mode):
        theme = DefaultTheme()
        ctx = UIContext(
            mode=mode,
            theme_name="Default",
            user_preferences={},
            content_count=10,
            active_sources=["RSS"]
        )

        styles = theme.apply_theme(ctx)
        assert "backgroundColor" in styles
        assert "textColor" in styles
