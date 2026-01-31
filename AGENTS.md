# AGENTS.md - Number Station

## Project Overview

Number Station is a content aggregation dashboard built on a modular plugin architecture. It provides unified access to multiple content sources (RSS feeds, social networks, websites) through two distinct UI modes:

- **Stream Mode**: Chronological feed display similar to old Friendfeed
- **Board Mode**: Multi-column layout similar to Tweetdeck with customizable lanes

The system is implemented in Python using Streamlit with Docker containerization.

## Architecture

```
├── src/                    # Core application code
├── plugins/                # Plugin ecosystem
├── config/                 # Configuration files
├── tests/                  # Test suite
└── .kiro/specs/           # Specifications and design docs
```

### Core Components

| Component | Description |
|-----------|-------------|
| **Application Core** | Central orchestrator for plugin lifecycle, configuration, and UI state |
| **Plugin Manager** | Handles plugin discovery, loading, validation, and lifecycle |
| **Configuration Manager** | Persists user preferences, plugin settings, source configurations |
| **Content Aggregator** | Coordinates content collection, normalization, and scheduling |
| **UI Controller** | Manages dual-mode interface and theme integration |

## Plugin System

### Plugin Types

1. **SourcePlugin** - Content sources (RSS, social media, custom)
2. **FilterPlugin** - Content filtering and ranking
3. **ThemePlugin** - Visual styling and themes

### Plugin Lifecycle

`Initialize → Validate → Start → Run → Stop → Cleanup`

### Creating Plugins

Plugins must extend the appropriate base class:

```python
class SourcePlugin(ABC):
    @abstractmethod
    def fetch_content(self) -> List[ContentItem]: pass
    @abstractmethod
    def validate_config(self, config: Dict) -> bool: pass

class FilterPlugin(ABC):
    @abstractmethod
    def filter_content(self, items: List[ContentItem]) -> List[ContentItem]: pass

class ThemePlugin(ABC):
    @abstractmethod
    def apply_theme(self, ui_context: UIContext) -> None: pass
```

## Data Models

### ContentItem Schema

All content is normalized to this standard schema:

```python
@dataclass
class ContentItem:
    id: str
    source: str
    source_type: str  # 'rss', 'twitter', 'reddit', etc.
    title: str
    content: str
    author: Optional[str]
    timestamp: datetime
    url: str
    tags: List[str]
    media_urls: List[str]
    metadata: Dict[str, Any]
```

### Database (SQLite)

- `content_items` - Cached content for offline access
- `plugin_configs` - Plugin settings and enabled state
- `user_preferences` - User settings (theme, mode, intervals)

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use type hints for function signatures
- Document public APIs with docstrings

### Error Handling

- **Network Errors**: Implement exponential backoff; cache last successful content
- **Plugin Errors**: Isolate failures; continue with remaining plugins
- **Configuration Errors**: Validate inputs; fallback to defaults on corruption
- **API Rate Limits**: Use token bucket algorithm; queue requests during limits

### Testing

The project uses a dual testing approach:

1. **Unit Tests**: Specific examples, edge cases, integration points
2. **Property-Based Tests**: Universal properties with Hypothesis (min 100 iterations)

Run tests with:
```bash
pytest tests/
```

## Key Files

| File | Purpose |
|------|---------|
| `.kiro/specs/number-station/requirements.md` | User stories and acceptance criteria |
| `.kiro/specs/number-station/design.md` | Architecture and correctness properties |
| `.kiro/specs/number-station/tasks.md` | Implementation task list |

## Content Sources

### Implemented

- RSS feeds (feedparser)
- Web scraping (CSS selectors)
- Twitter/X API
- Reddit API
- Hacker News
- Dev.to

### Planned

- Medium
- Instagram
- TikTok
- Pinterest

## Configuration

Configuration is JSON-based and persisted locally:

- User preferences (UI mode, theme, update intervals)
- Plugin configurations (enabled state, settings)
- Source configurations (URLs, credentials, selectors)

Export/import functionality is available for backup and migration.

## UI Modes

### Stream Mode
- Single scrollable feed
- Chronological ordering
- Infinite scroll
- Real-time updates

### Board Mode
- Multiple customizable columns (lanes)
- Drag-and-drop organization
- Lane-specific filtering
- Configurable lane assignments

## Future AI Features

The architecture supports planned AI capabilities:

- Content ranking algorithms
- Automated content generation
- Social media auto-posting
- Content exploration/discovery
- User interaction tracking (read, repost, hide)
- ML feature extraction

## Docker

Build and run:
```bash
docker-compose up --build
```

The application runs on Streamlit's default port (8501).
