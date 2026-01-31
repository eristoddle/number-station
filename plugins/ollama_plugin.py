
import logging
import requests
from typing import List, Dict, Any, Optional
from src.plugins import AIPlugin, PluginMetadata
from src.models import ContentItem

class OllamaPlugin(AIPlugin):
    """
    AI plugin for local Ollama integration.

    Validates Requirements 6.2, 11.1, 11.2:
    - Text generation using local models (Ollama)
    - Content summarization
    """

    API_URL = "http://localhost:11434/api/chat"

    def __init__(self):
        super().__init__()
        self._host = "localhost"
        self._port = 11434
        self._model = "llama3"

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Ollama AI Plugin",
            version="1.0.0",
            description="AI features using local Ollama models",
            author="Number Station Team",
            plugin_type="ai",
            dependencies=["requests"],
            capabilities=["summarization", "generation", "local_ai"],
            config_schema={
                "host": "string (optional, default='localhost')",
                "port": "integer (optional, default=11434)",
                "model": "string (optional, default='llama3')"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        self._config = config
        self._host = config.get("host", "localhost")
        self._port = config.get("port", 11434)
        self._model = config.get("model", "llama3")
        self.API_URL = f"http://{self._host}:{self._port}/api/chat"
        return True

    def rank_items(self, items: List[ContentItem]) -> List[ContentItem]:
        return sorted(items, key=lambda x: x.relevance_score, reverse=True)

    def process_item(self, item: ContentItem) -> ContentItem:
        summary = self.generate_text(f"Summarize this in one sentence: {item.content}")
        item.metadata["ai_summary"] = summary
        return item

    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate text using local Ollama instance."""
        try:
            messages = [{"role": "user", "content": prompt}]
            if context and context.get("system_prompt"):
                messages.insert(0, {"role": "system", "content": context["system_prompt"]})

            payload = {
                "model": self._model,
                "messages": messages,
                "stream": False
            }

            response = requests.post(self.API_URL, json=payload, timeout=60)

            if response.status_code == 200:
                data = response.json()
                return data["message"]["content"].strip()
            else:
                return f"Error from Ollama: {response.text}"

        except Exception as e:
            self.logger.error(f"Error calling Ollama: {e}")
            return f"Error: Local Ollama process may not be running or model '{self._model}' not found. {str(e)}"

    def summarize_items(self, items: List[ContentItem], style: str = "concise") -> str:
        """Summarize multiple items."""
        if not items:
            return "No items to summarize."

        combined_content = "\n\n".join([f"Item {i+1}: {item.title}\n{item.content[:500]}" for i, item in enumerate(items)])
        prompt = f"Please provide a {style} summary of the following {len(items)} content items:\n\n{combined_content}"

        return self.generate_text(prompt)
