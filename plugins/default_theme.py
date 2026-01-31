
import logging
from typing import Dict, Any, List
from src.plugins import ThemePlugin, UIContext
from src.models import PluginMetadata

class DefaultTheme(ThemePlugin):
    """
    Default theme for Number Station.
    Provides a clean, professional look for both Stream and Board modes.

    Validates Requirements 8.1, 8.4, 8.6.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Default Theme",
            version="1.0.0",
            description="The default clean theme for Number Station",
            author="Number Station Team",
            plugin_type="theme",
            capabilities=["theme", "default"],
            config_schema={
                "primary_color": "string (optional)",
                "font_family": "string (optional)"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        self._config = config
        return True

    def apply_theme(self, ui_context: UIContext) -> Dict[str, Any]:
        """Return theme variables for the UI."""
        return {
            "primaryColor": self._config.get("primary_color", "#FF4B4B"),
            "backgroundColor": "#FFFFFF",
            "secondaryBackgroundColor": "#F0F2F6",
            "textColor": "#31333F",
            "font": self._config.get("font_family", "sans serif")
        }

    def get_css(self) -> str:
        """Return custom CSS for the theme."""
        return """
        .content-card {
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid #e0e0e0;
            margin-bottom: 1rem;
            background-color: white;
            transition: transform 0.2s;
        }
        .content-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        """

    def supports_mode(self, mode: str) -> bool:
        return mode in ["stream", "board"]
