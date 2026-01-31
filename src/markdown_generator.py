
import logging
try:
    import jinja2
except ImportError:
    jinja2 = None

from typing import List
from datetime import datetime
from src.models import ContentItem, ContentCollection, MarkdownTemplate

DEFAULT_TEMPLATE = """---
layout: post
title: {{ collection.name }}
date: {{ now.strftime('%Y-%m-%d %H:%M:%S') }}
---

# {{ collection.name }}

{{ collection.description }}

{% if collection.metadata.ai_intro %}
{{ collection.metadata.ai_intro }}
{% endif %}

## Curated Content

{% for item in items %}
### [{{ item.title }}]({{ item.url }})
*Source: {{ item.source }} | Author: {{ item.author or 'Unknown' }}*

{{ item.content[:300] }}{% if item.content|length > 300 %}...{% endif %}

{% endfor %}

{% if collection.metadata.ai_summary %}
## Summary
{{ collection.metadata.ai_summary }}
{% endif %}
"""

class MarkdownGenerator:
    """
    Generates Markdown files from ContentCollections using Jinja2 templates.

    Validates Requirements 7.1, 7.2, 7.3:
    - Jinja2 template rendering
    - Jekyll frontmatter support
    """

    def __init__(self, template_str: str = None):
        self.logger = logging.getLogger(__name__)
        self.template_str = template_str or DEFAULT_TEMPLATE
        if jinja2:
            self.env = jinja2.Environment()
        else:
            self.logger.warning("Jinja2 not installed, markdown generation will be limited.")

    def generate(self, collection: ContentCollection, items: List[ContentItem]) -> str:
        """Render the collection into a markdown string."""
        if not jinja2:
            return self._generate_fallback(collection, items)

        try:
            template = self.env.from_string(self.template_str)
            return template.render(
                collection=collection,
                items=items,
                now=datetime.now()
            )
        except Exception as e:
            self.logger.error(f"Error rendering markdown: {e}")
            return f"Error rendering markdown: {str(e)}"

    def _generate_fallback(self, collection: ContentCollection, items: List[ContentItem]) -> str:
        """Basic fallback generation if Jinja2 is missing."""
        lines = [
            "---",
            f"title: {collection.name}",
            f"date: {datetime.now().isoformat()}",
            "---",
            "",
            f"# {collection.name}",
            "",
            collection.description,
            ""
        ]

        for item in items:
            lines.append(f"### [{item.title}]({item.url})")
            lines.append(f"*Source: {item.source}*")
            lines.append("")
            lines.append(item.content[:300] + "...")
            lines.append("")

        return "\n".join(lines)
