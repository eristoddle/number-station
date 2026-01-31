#!/usr/bin/env python3
"""
Example Source Plugin for Number Station

This is a simple example source plugin that demonstrates how to implement
the SourcePlugin interface. It generates mock content for testing purposes.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from src.plugins import SourcePlugin
from src.models import ContentItem, PluginMetadata


class ExampleSourcePlugin(SourcePlugin):
    """
    Example source plugin that generates mock content.

    This plugin demonstrates the SourcePlugin interface and can be used
    for testing the plugin system functionality.
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="example_source",
            version="1.0.0",
            description="Example source plugin for testing",
            author="Number Station Team",
            plugin_type="source",
            enabled=True,
            dependencies=[],
            capabilities=["mock_content", "testing"],
            config_schema={
                "type": "object",
                "properties": {
                    "item_count": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 5,
                        "description": "Number of mock items to generate"
                    },
                    "source_name": {
                        "type": "string",
                        "default": "example",
                        "description": "Name to use as content source"
                    }
                }
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        try:
            # Check required fields and types
            if 'item_count' in config:
                item_count = config['item_count']
                if not isinstance(item_count, int) or item_count < 1 or item_count > 100:
                    self.logger.error("item_count must be an integer between 1 and 100")
                    return False

            if 'source_name' in config:
                source_name = config['source_name']
                if not isinstance(source_name, str) or len(source_name.strip()) == 0:
                    self.logger.error("source_name must be a non-empty string")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return False

    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the plugin with provided settings."""
        try:
            if not self.validate_config(config):
                return False

            self._config = config.copy()
            self.logger.info(f"Configured example source plugin with config: {config}")
            return True

        except Exception as e:
            self.logger.error(f"Configuration error: {e}")
            return False

    def fetch_content(self) -> List[ContentItem]:
        """Fetch mock content items."""
        try:
            item_count = self._config.get('item_count', 5)
            source_name = self._config.get('source_name', 'example')

            items = []
            base_time = datetime.now()

            for i in range(item_count):
                # Generate mock content item
                item_id = str(uuid.uuid4())
                timestamp = base_time - timedelta(minutes=i * 10)

                item = ContentItem(
                    id=item_id,
                    source=source_name,
                    source_type="example",
                    title=f"Example Item {i + 1}",
                    content=f"This is example content item number {i + 1}. "
                           f"Generated at {timestamp.isoformat()}.",
                    author="Example Author",
                    timestamp=timestamp,
                    url=f"https://example.com/item/{item_id}",
                    tags=["example", "test", f"item-{i + 1}"],
                    media_urls=[],
                    metadata={
                        "generated": True,
                        "item_number": i + 1,
                        "plugin": "example_source"
                    }
                )

                items.append(item)

            self.logger.info(f"Generated {len(items)} mock content items")
            return items

        except Exception as e:
            self.logger.error(f"Error fetching content: {e}")
            return []

    def test_connection(self) -> bool:
        """Test connection (always succeeds for mock plugin)."""
        try:
            self.logger.info("Testing example source connection")
            # Mock plugins always have a successful connection
            return True

        except Exception as e:
            self.logger.error(f"Connection test error: {e}")
            return False