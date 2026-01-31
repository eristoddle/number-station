# Design Document: Content Sharing and Curation

## Overview

This design extends Number Station's plugin architecture with content sharing, scheduling, and curation capabilities. The system introduces a new DestinationPlugin type for outbound content, extends AIPlugin for text generation, and adds UI components for managing shares, schedules, and collections.

## Architecture

### Extended Plugin Ecosystem

```
Plugin Types:
├── SourcePlugin (existing) - Fetch content from external sources
├── FilterPlugin (existing) - Filter and rank content
├── ThemePlugin (existing) - UI styling
├── AIPlugin (extended) - AI operations + text generation
├── ServicePlugin (existing) - Background services
└── DestinationPlugin (NEW) - Post content to external platforms
```

### Data Flow for Sharing

```
ContentItem → User Action → ShareableContent → DestinationPlugin → External Platform
                                    ↓
                              ScheduledPost (if scheduled)
                                    ↓
                           SchedulerService → DestinationPlugin → External Platform
```

### Data Flow for Curation

```
ContentItem(s) → Collection → AIPlugin (generate text) → MarkdownGenerator → .md file
```

## Components and Interfaces

### DestinationPlugin Interface

```python
class DestinationPlugin(ABC):
    @abstractmethod
    def post_content(self, content: ShareableContent) -> PostResult: pass

    @abstractmethod
    def validate_content(self, content: ShareableContent) -> ValidationResult: pass

    @abstractmethod
    def get_capabilities(self) -> DestinationCapabilities: pass

    @abstractmethod
    def supports_reshare(self, source_type: str) -> bool: pass

    @abstractmethod
    def reshare(self, item: ContentItem) -> PostResult: pass
```

### Extended AIPlugin Interface

```python
class AIPlugin(ABC):
    # Existing methods...

    @abstractmethod
    def generate_text(self, prompt: str, context: Optional[Dict] = None) -> str: pass

    @abstractmethod
    def summarize_items(self, items: List[ContentItem], style: str = "brief") -> str: pass
```

### Supporting Data Classes

```python
@dataclass
class ShareableContent:
    text: str
    url: Optional[str] = None
    media_urls: List[str] = field(default_factory=list)
    title: Optional[str] = None
    source_item_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PostResult:
    success: bool
    post_url: Optional[str] = None
    post_id: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    character_count: Optional[int] = None
    character_limit: Optional[int] = None

@dataclass
class DestinationCapabilities:
    max_text_length: int
    supports_media: bool
    max_media_count: int
    supports_scheduling: bool
    native_reshare_types: List[str]

@dataclass
class ScheduledPost:
    id: str
    content: ShareableContent
    destination_plugin: str
    scheduled_time: datetime
    status: str  # 'pending', 'processing', 'completed', 'failed'
    recurrence: Optional[str] = None  # 'daily', 'weekly'
    retry_count: int = 0
    result: Optional[PostResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class ContentCollection:
    id: str
    name: str
    description: Optional[str] = None
    item_ids: List[str] = field(default_factory=list)
    generated_intro: Optional[str] = None
    generated_summary: Optional[str] = None
    template_id: Optional[str] = None
    frontmatter: Optional[Dict[str, Any]] = None
    exported: bool = False
    export_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class MarkdownTemplate:
    id: str
    name: str
    frontmatter_template: str
    body_template: str
    intro_prompt: Optional[str] = None
    summary_prompt: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
```

## Database Schema

```sql
-- Scheduled posts queue
CREATE TABLE scheduled_posts (
    id TEXT PRIMARY KEY,
    content_text TEXT NOT NULL,
    content_url TEXT,
    content_media_urls TEXT,  -- JSON array
    content_title TEXT,
    content_source_item_id TEXT,
    content_metadata TEXT,  -- JSON object
    destination_plugin TEXT NOT NULL,
    scheduled_time DATETIME NOT NULL,
    status TEXT DEFAULT 'pending',
    recurrence TEXT,
    retry_count INTEGER DEFAULT 0,
    result TEXT,  -- JSON PostResult
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scheduled_posts_status_time ON scheduled_posts(status, scheduled_time);

-- Content collections
CREATE TABLE content_collections (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    item_ids TEXT,  -- JSON array
    template_id TEXT,
    generated_intro TEXT,
    generated_summary TEXT,
    frontmatter TEXT,  -- JSON object
    exported BOOLEAN DEFAULT FALSE,
    export_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Markdown templates
CREATE TABLE markdown_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    frontmatter_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    intro_prompt TEXT,
    summary_prompt TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## UI Components

### Content Action Buttons

- Rendered below each content card in Stream and Board modes
- Buttons: Share | Schedule | Preview | + Collect | [checkbox]
- Buttons trigger session state for modals/expandable sections
- Checkbox enables multi-select for batch operations

### Share Modal

- Destination selector dropdown (populated from available DestinationPlugins)
- Native reshare toggle (shown if destination supports reshare for content source)
- Text editor with live character count and limit indicator
- Media preview (if content has media)
- "Share Now" button with loading state
- Success: displays post URL with link
- Failure: displays actionable error message

### Schedule Modal

- Date picker for scheduled date
- Time picker for scheduled time
- Recurrence selector: Once | Daily | Weekly
- Content preview (text, media, destination)
- "Schedule" button
- Confirmation with scheduled time display

### Preview Component

- Expandable card (Streamlit expander, not modal due to limitations)
- Full content text (no truncation)
- Media gallery (grid layout, up to 4 images)
- Metadata section: source, author, timestamp, tags
- "Open Original" link button

### Collections Page

- Sidebar: list of collections with item counts
- Main area: selected collection detail
- "New Collection" button with name input
- Collection detail:
  - Name (editable)
  - Description (editable)
  - Item list with remove buttons
  - "Generate Intro" button
  - "Generate Summary" button
  - Generated text display with edit capability
  - "Export Markdown" button
  - "Delete Collection" button

### Scheduled Posts Page

- Table view of scheduled posts
- Columns: Content preview, Destination, Scheduled Time, Status, Actions
- Filter by status: All | Pending | Completed | Failed
- Filter by destination
- Edit button: opens edit modal
- Cancel button: removes pending post
- Status badges with color coding

## Correctness Properties

### Property S1: Share Content Validation

*For any* content being shared, validation must occur before posting. The system SHALL NOT post content that fails validation.

```python
# Invariant
def share_content(content, destination):
    result = destination.validate_content(content)
    if not result.valid:
        return ValidationError(result.errors)
    return destination.post_content(content)
```

### Property S2: Scheduled Post Execution

*For any* scheduled post with status 'pending' and scheduled_time <= now, the scheduler service SHALL process the post within the check interval (default 60 seconds).

### Property S3: Retry Backoff Pattern

*For any* failed post with retry_count < max_retries (default 3), the retry interval SHALL follow exponential backoff: `base_delay * (2 ** retry_count)` where base_delay = 60 seconds.

### Property S4: Collection Item Integrity

*For any* collection, all item_ids SHALL reference valid ContentItems in the database. When a ContentItem is deleted, it SHALL be removed from all collections containing it.

### Property S5: Markdown Template Rendering

*For any* valid collection with a template, export SHALL produce valid Jekyll-compatible markdown with:
- Valid YAML frontmatter (parseable by Jekyll)
- Required frontmatter fields: layout, title, date
- UTF-8 encoded content

### Property S6: AI Text Generation

*For any* AI generation request, the selected AI plugin SHALL be invoked. If the AI plugin fails, the system SHALL return an error without corrupting existing content.

## Error Handling

### Network Errors (Sharing)

- Timeout after 30 seconds
- Display user-friendly error with retry option
- Log detailed error for debugging

### API Rate Limits

- Detect rate limit responses (HTTP 429)
- Display time until reset if available
- For scheduled posts: automatically retry after rate limit window

### Plugin Errors

- Isolate plugin failures
- Continue with other operations
- Log error with plugin context

### Validation Errors

- Display all validation errors to user
- Highlight specific issues (character count, missing fields)
- Do not submit invalid content

## Security Considerations

### OAuth Token Storage

- Store tokens encrypted in database
- Never log tokens
- Support token refresh for OAuth 2.0

### Content Sanitization

- Sanitize user-edited content before posting
- Prevent injection in markdown templates

### Rate Limiting

- Respect platform rate limits
- Implement local rate limiting as safety net
