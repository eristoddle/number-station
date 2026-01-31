# Requirements Document: Content Sharing and Curation

## Introduction

This specification extends Number Station with content sharing, scheduling, and curation capabilities. Users can share discovered content to external platforms (Twitter, LinkedIn), schedule posts for future publication, preview content in expanded views, and curate collections of content for export as Jekyll-compatible markdown files with AI-generated introductions and summaries.

## Glossary

- **DestinationPlugin**: A plugin type for platforms that can receive/publish content
- **ShareableContent**: Content prepared and validated for sharing to a destination
- **ScheduledPost**: A post queued for future publication with timing and destination
- **ContentCollection**: A curated set of content items for export/publishing
- **MarkdownTemplate**: A Jinja2-based template for generating markdown files
- **Reshare**: Native platform resharing (e.g., Retweet) vs. sharing with link

## Requirements

### Requirement 1: Content Action Buttons

**User Story:** As a user, I want action buttons on each content item, so that I can quickly share, schedule, preview, or collect content.

#### Acceptance Criteria

1. WHEN viewing content in Stream or Board mode, THE Number_Station SHALL display action buttons on each content item
2. THE Number_Station SHALL provide a "Share" button to share content immediately
3. THE Number_Station SHALL provide a "Schedule" button to queue content for later
4. THE Number_Station SHALL provide a "Preview" button to view expanded content
5. THE Number_Station SHALL provide a "Collect" button to add content to a collection
6. THE Number_Station SHALL provide a selection checkbox for multi-select operations

### Requirement 2: Instant Content Sharing

**User Story:** As a user, I want to share content to external platforms immediately, so that I can distribute interesting content to my audience.

#### Acceptance Criteria

1. WHEN a user clicks Share, THE Number_Station SHALL display available destination platforms
2. THE Number_Station SHALL support native resharing where available (e.g., Retweet)
3. THE Number_Station SHALL support sharing with link and custom text
4. THE Number_Station SHALL validate content against platform limits before posting
5. THE Number_Station SHALL display character count and limit for text content
6. WHEN sharing succeeds, THE Number_Station SHALL display the post URL
7. WHEN sharing fails, THE Number_Station SHALL display an actionable error message

### Requirement 3: Scheduled Posting

**User Story:** As a user, I want to schedule content for future posting, so that I can plan my content distribution.

#### Acceptance Criteria

1. THE Number_Station SHALL allow users to select date and time for posting
2. THE Number_Station SHALL support recurring schedules (once, daily, weekly)
3. THE Number_Station SHALL process scheduled posts in the background
4. THE Number_Station SHALL retry failed posts with exponential backoff
5. THE Number_Station SHALL provide a scheduled posts management page
6. THE Number_Station SHALL allow users to edit or cancel scheduled posts
7. WHEN a scheduled post is processed, THE Number_Station SHALL update its status

### Requirement 4: Content Preview

**User Story:** As a user, I want to preview content in an expanded view, so that I can see full details before sharing.

#### Acceptance Criteria

1. WHEN a user clicks Preview, THE Number_Station SHALL display an expandable card
2. THE Preview SHALL show the full content text
3. THE Preview SHALL display all media in a gallery format
4. THE Preview SHALL show metadata (source, author, timestamp, tags)
5. THE Preview SHALL provide a link to open the original URL

### Requirement 5: Content Collections

**User Story:** As a user, I want to curate content into collections, so that I can group related items for export.

#### Acceptance Criteria

1. THE Number_Station SHALL allow users to create named collections
2. THE Number_Station SHALL allow users to add content items to collections
3. THE Number_Station SHALL allow users to remove items from collections
4. THE Number_Station SHALL display collections with item counts
5. THE Number_Station SHALL allow users to delete collections

### Requirement 6: AI-Generated Content

**User Story:** As a user, I want AI-generated introductions and summaries for my collections, so that curated posts have unique context.

#### Acceptance Criteria

1. THE Number_Station SHALL integrate with configurable AI providers
2. THE Number_Station SHALL support OpenAI, Anthropic, and Ollama providers
3. WHEN requested, THE Number_Station SHALL generate an introduction for a collection
4. WHEN requested, THE Number_Station SHALL generate a summary of collection items
5. THE Number_Station SHALL store generated content with the collection
6. THE Number_Station SHALL allow users to edit generated content

### Requirement 7: Markdown Export

**User Story:** As a user, I want to export collections as Jekyll-compatible markdown, so that I can publish curated posts to my static site.

#### Acceptance Criteria

1. THE Number_Station SHALL export collections as markdown files
2. THE markdown SHALL include YAML frontmatter compatible with Jekyll
3. THE frontmatter SHALL include title, date, and tags
4. THE markdown body SHALL include AI-generated intro and summary
5. THE markdown body SHALL include formatted content items with links
6. THE Number_Station SHALL allow template customization

### Requirement 8: Destination Plugin Architecture

**User Story:** As a developer, I want a DestinationPlugin interface, so that new sharing platforms can be added.

#### Acceptance Criteria

1. THE Number_Station SHALL define a DestinationPlugin abstract base class
2. THE DestinationPlugin SHALL require post_content() method
3. THE DestinationPlugin SHALL require validate_content() method
4. THE DestinationPlugin SHALL require get_capabilities() method
5. THE DestinationPlugin SHALL support native resharing via supports_reshare() and reshare()
6. THE PluginRegistry SHALL discover and load destination plugins
7. THE PluginManager SHALL provide get_destination_plugins() method

### Requirement 9: Twitter/X Destination

**User Story:** As a user, I want to share content to Twitter/X, so that I can reach my Twitter audience.

#### Acceptance Criteria

1. THE Number_Station SHALL provide a Twitter destination plugin
2. THE plugin SHALL support OAuth 1.0a authentication for posting
3. THE plugin SHALL validate 280 character limit
4. THE plugin SHALL support native Retweet for Twitter content
5. THE plugin SHALL support media attachments

### Requirement 10: LinkedIn Destination

**User Story:** As a user, I want to share content to LinkedIn, so that I can reach my professional network.

#### Acceptance Criteria

1. THE Number_Station SHALL provide a LinkedIn destination plugin
2. THE plugin SHALL support OAuth 2.0 authentication
3. THE plugin SHALL support posting to personal feed
4. THE plugin SHALL validate content against LinkedIn limits

### Requirement 11: Extended AI Plugin Interface

**User Story:** As a developer, I want extended AI plugin methods, so that AI features can generate text and summaries.

#### Acceptance Criteria

1. THE AIPlugin SHALL include generate_text(prompt, context) method
2. THE AIPlugin SHALL include summarize_items(items, style) method
3. THE Number_Station SHALL support multiple AI provider plugins
4. THE user SHALL be able to select which AI provider to use
