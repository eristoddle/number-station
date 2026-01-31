
import logging
import requests
from typing import List, Dict, Any, Optional
from src.plugins import AIPlugin, PluginMetadata
from src.models import ContentItem

class AnthropicPlugin(AIPlugin):
    """
    AI plugin for Anthropic integration.

    Validates Requirements 6.2, 11.1, 11.2:
    - Text generation using Claude models
    - Content summarization
    """

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self):
        super().__init__()
        self._api_key = None
        self._model = "claude-3-haiku-20240307"

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Anthropic AI Plugin",
            version="1.0.0",
            description="AI features using Anthropic Claude",
            author="Number Station Team",
            plugin_type="ai",
            dependencies=["requests"],
            capabilities=["summarization", "generation"],
            config_schema={
                "api_key": "string (required) - Anthropic API Key",
                "model": "string (optional, default='claude-3-haiku-20240307')"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        if not config.get("api_key"):
            self.logger.error("Anthropic plugin config missing 'api_key'")
            return False
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        if not self.validate_config(config):
            return False
        self._config = config
        self._api_key = config["api_key"]
        self._model = config.get("model", "claude-3-haiku-20240307")
        return True

    def rank_items(self, items: List[ContentItem]) -> List[ContentItem]:
        return sorted(items, key=lambda x: x.relevance_score, reverse=True)

    def process_item(self, item: ContentItem) -> ContentItem:
        summary = self.generate_text(f"Summarize this in one sentence: {item.content}")
        item.metadata["ai_summary"] = summary
        return item

    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate text using Anthropic API."""
        if not self._api_key:
            return "Error: Anthropic API key not configured"

        try:
            headers = {
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self._model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            }

            if context and context.get("system_prompt"):
                payload["system"] = context["system_prompt"]

            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return data["content"][0]["text"].strip()
            else:
                return f"Error from Anthropic API: {response.text}"

        except Exception as e:
            self.logger.error(f"Error calling Anthropic API: {e}")
            return f"Error: {str(e)}"

    def summarize_items(self, items: List[ContentItem], style: str = "concise") -> str:
        """Summarize multiple items."""
        if not items:
            return "No items to summarize."

        combined_content = "\n\n".join([f"Item {i+1}: {item.title}\n{item.content[:500]}" for i, item in enumerate(items)])
        prompt = f"Please provide a {style} summary of the following {len(items)} content items:\n\n{combined_content}"

        return self.generate_text(prompt)
