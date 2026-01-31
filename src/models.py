#!/usr/bin/env python3
"""
Number Station - Core Data Models

This module defines the core data structures used throughout the Number Station
application, including the ContentItem schema and other essential models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import json


@dataclass
class ContentItem:
    """
    Standardized content item schema for all content sources.

    This class represents a single piece of content from any source (RSS, social media, etc.)
    normalized into a consistent format for processing and display.

    Validates Requirements 9.1, 9.3, 9.4:
    - Standard Content_Item schema
    - Metadata fields (source, timestamp, author, tags)
    - Content fields (title, body, media URLs)
    """

    # Required fields
    id: str
    source: str
    source_type: str  # 'rss', 'twitter', 'reddit', 'custom', etc.
    title: str
    content: str
    timestamp: datetime
    url: str

    # Optional fields with defaults
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    media_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # AI/ML Compatibility Fields
    relevance_score: float = 0.0
    embedding: List[float] = field(default_factory=list)

    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        # Ensure required fields are not empty
        if not self.id:
            raise ValueError("ContentItem id cannot be empty")
        if not self.source:
            raise ValueError("ContentItem source cannot be empty")
        if not self.source_type:
            raise ValueError("ContentItem source_type cannot be empty")
        if not self.title:
            raise ValueError("ContentItem title cannot be empty")
        if not self.url:
            raise ValueError("ContentItem url cannot be empty")

        # Ensure lists are not None
        if self.tags is None:
            self.tags = []
        if self.media_urls is None:
            self.media_urls = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert ContentItem to dictionary for serialization."""
        return {
            'id': self.id,
            'source': self.source,
            'source_type': self.source_type,
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'timestamp': self.timestamp.isoformat(),
            'url': self.url,
            'tags': json.dumps(self.tags),
            'media_urls': json.dumps(self.media_urls),
            'metadata': json.dumps(self.metadata),
            'relevance_score': self.relevance_score,
            'embedding': json.dumps(self.embedding)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentItem':
        """Create ContentItem from dictionary (e.g., from database)."""
        # Parse timestamp
        timestamp = data['timestamp']
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # Parse JSON fields
        tags = data.get('tags', '[]')
        if isinstance(tags, str):
            tags = json.loads(tags)

        media_urls = data.get('media_urls', '[]')
        if isinstance(media_urls, str):
            media_urls = json.loads(media_urls)

        metadata = data.get('metadata', '{}')
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        embedding = data.get('embedding', '[]')
        if isinstance(embedding, str):
            embedding = json.loads(embedding)

        return cls(
            id=data['id'],
            source=data['source'],
            source_type=data['source_type'],
            title=data['title'],
            content=data['content'],
            author=data.get('author'),
            timestamp=timestamp,
            url=data['url'],
            tags=tags,
            media_urls=media_urls,
            metadata=metadata,
            relevance_score=data.get('relevance_score', 0.0),
            embedding=embedding
        )


@dataclass
class UserPreferences:
    """
    User preferences and settings.

    Stores UI mode selection, theme choice, update intervals, and display preferences.
    """

    ui_mode: str = "stream"  # "stream" or "board"
    theme: str = "default"
    update_interval: int = 300  # seconds
    items_per_page: int = 50
    auto_refresh: bool = True
    show_media: bool = True
    show_author: bool = True
    show_timestamp: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'ui_mode': self.ui_mode,
            'theme': self.theme,
            'update_interval': self.update_interval,
            'items_per_page': self.items_per_page,
            'auto_refresh': self.auto_refresh,
            'show_media': self.show_media,
            'show_author': self.show_author,
            'show_timestamp': self.show_timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create from dictionary."""
        return cls(
            ui_mode=data.get('ui_mode', 'stream'),
            theme=data.get('theme', 'default'),
            update_interval=data.get('update_interval', 300),
            items_per_page=data.get('items_per_page', 50),
            auto_refresh=data.get('auto_refresh', True),
            show_media=data.get('show_media', True),
            show_author=data.get('show_author', True),
            show_timestamp=data.get('show_timestamp', True)
        )


@dataclass
class PluginMetadata:
    """
    Plugin metadata and configuration information.

    Stores plugin information including version, dependencies, capabilities, and configuration schema.
    """

    name: str
    version: str
    description: str
    author: str
    plugin_type: str  # 'source', 'filter', 'theme'
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'plugin_type': self.plugin_type,
            'enabled': self.enabled,
            'dependencies': json.dumps(self.dependencies),
            'capabilities': json.dumps(self.capabilities),
            'config_schema': json.dumps(self.config_schema)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        """Create from dictionary."""
        dependencies = data.get('dependencies', '[]')
        if isinstance(dependencies, str):
            dependencies = json.loads(dependencies)

        capabilities = data.get('capabilities', '[]')
        if isinstance(capabilities, str):
            capabilities = json.loads(capabilities)

        config_schema = data.get('config_schema', '{}')
        if isinstance(config_schema, str):
            config_schema = json.loads(config_schema)

        return cls(
            name=data['name'],
            version=data['version'],
            description=data['description'],
            author=data['author'],
            plugin_type=data['plugin_type'],
            enabled=data.get('enabled', True),
            dependencies=dependencies,
            capabilities=capabilities,
            config_schema=config_schema
        )


@dataclass
class SourceConfiguration:
    """
    Configuration for content sources.

    Contains connection details, authentication credentials, and source-specific settings.
    """

    name: str
    source_type: str  # 'rss', 'twitter', 'reddit', etc.
    url: Optional[str] = None
    enabled: bool = True
    fetch_interval: int = 300  # seconds
    tags: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)  # Source-specific configuration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'name': self.name,
            'source_type': self.source_type,
            'url': self.url,
            'enabled': self.enabled,
            'fetch_interval': self.fetch_interval,
            'tags': json.dumps(self.tags),
            'config': json.dumps(self.config)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceConfiguration':
        """Create from dictionary."""
        tags = data.get('tags', '[]')
        if isinstance(tags, str):
            tags = json.loads(tags)

        config = data.get('config', '{}')
        if isinstance(config, str):
            config = json.loads(config)

        return cls(
            name=data['name'],
            source_type=data['source_type'],
            url=data.get('url'),
            enabled=data.get('enabled', True),
            fetch_interval=data.get('fetch_interval', 300),
            tags=tags,
            config=config
        )


@dataclass
class SourceMetadata:
    """
    Runtime metadata and statistics for content sources.

    Tracks update history, success rates, and item counts (Requirement 3.6, 5.4).
    """

    source_id: str # Links to SourceConfiguration.name (or ID?)
    last_fetch_attempt: datetime
    last_fetch_success: Optional[datetime]
    last_item_count: int
    total_items_fetched: int
    error_count: int
    consecutive_errors: int
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'last_fetch_attempt': self.last_fetch_attempt.isoformat(),
            'last_fetch_success': self.last_fetch_success.isoformat() if self.last_fetch_success else None,
            'last_item_count': self.last_item_count,
            'total_items_fetched': self.total_items_fetched,
            'error_count': self.error_count,
            'consecutive_errors': self.consecutive_errors,
            'last_error': self.last_error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceMetadata':
        last_fetch_attempt = datetime.fromisoformat(data['last_fetch_attempt'])

        last_fetch_success = None
        if data.get('last_fetch_success'):
             last_fetch_success = datetime.fromisoformat(data['last_fetch_success'])

        return cls(
            source_id=data['source_id'],
            last_fetch_attempt=last_fetch_attempt,
            last_fetch_success=last_fetch_success,
            last_item_count=data.get('last_item_count', 0),
            total_items_fetched=data.get('total_items_fetched', 0),
            error_count=data.get('error_count', 0),
            consecutive_errors=data.get('consecutive_errors', 0),
            last_error=data.get('last_error')
        )