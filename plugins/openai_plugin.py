
import logging
import requests
from typing import List, Dict, Any, Optional
from src.plugins import AIPlugin, PluginMetadata
from src.models import ContentItem, PluginMetadata

class OpenAIPlugin(AIPlugin):
    """
    AI plugin for OpenAI integration.

    Validates Requirements 6.2, 11.1, 11.2:
    - Text generation using GPT models
    - Content summarization
    """

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self):
        super().__init__()
        self._api_key = None
        self._model = "gpt-3.5-turbo"

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="OpenAI AI Plugin",
            version="1.0.0",
            description="AI features using OpenAI GPT",
            author="Number Station Team",
            plugin_type="ai",
            dependencies=["requests"],
            capabilities=["summarization", "generation", "ranking"],
            config_schema={
                "api_key": "string (required) - OpenAI API Key",
                "model": "string (optional, default='gpt-3.5-turbo')"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        if not config.get("api_key"):
            self.logger.error("OpenAI plugin config missing 'api_key'")
            return False
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        if not self.validate_config(config):
            return False
        self._config = config
        self._api_key = config["api_key"]
        self._model = config.get("model", "gpt-3.5-turbo")
        return True

    def rank_items(self, items: List[ContentItem]) -> List[ContentItem]:
        """Rank items by relevance (stub)."""
        # In a real implementation, this would use embeddings or a prompt to score items.
        return sorted(items, key=lambda x: x.relevance_score, reverse=True)

    def process_item(self, item: ContentItem) -> ContentItem:
        """Process a single item (e.g., summarize it)."""
        summary = self.generate_text(f"Summarize this content in one sentence: {item.content}")
        item.metadata["ai_summary"] = summary
        return item

    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate text using OpenAI API."""
        if not self._api_key:
            return "Error: OpenAI API key not configured"

        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }

            messages = [{"role": "user", "content": prompt}]
            if context and context.get("system_prompt"):
                messages.insert(0, {"role": "system", "content": context["system_prompt"]})

            payload = {
                "model": self._model,
                "messages": messages,
                "temperature": 0.7
            }

            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                return f"Error from OpenAI API: {response.text}"

        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {e}")
            return f"Error: {str(e)}"

    def summarize_items(self, items: List[ContentItem], style: str = "concise") -> str:
        """Summarize multiple items."""
        if not items:
            return "No items to summarize."

        combined_content = "\n\n".join([f"Item {i+1}: {item.title}\n{item.content[:500]}" for i, item in enumerate(items)])

        prompt = f"Please provide a {style} summary of the following {len(items)} content items:\n\n{combined_content}"

        return self.generate_text(prompt)
