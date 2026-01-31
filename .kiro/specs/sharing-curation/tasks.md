# Implementation Plan: Content Sharing and Curation

## Overview

This plan implements content sharing, scheduling, preview, and curation features for Number Station. Implementation follows a dependency-aware order: plugin API first, then data models, then plugins, then UI.

## Tasks

- [ ] 1. Extend Plugin Architecture
  - [ ] 1.1 Add DestinationPlugin base class to src/plugins.py
    - Define abstract methods: post_content, validate_content, get_capabilities, supports_reshare, reshare
    - Add lifecycle methods (initialize, start, stop, cleanup)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ] 1.2 Update PluginRegistry for destination plugins
    - Add 'destination' to valid plugin types
    - Update _validate_plugin_class() for DestinationPlugin methods
    - _Requirements: 8.6_

  - [ ] 1.3 Update PluginManager
    - Add get_destination_plugins() method
    - _Requirements: 8.7_

  - [ ] 1.4 Extend AIPlugin interface
    - Add generate_text(prompt, context) abstract method
    - Add summarize_items(items, style) abstract method
    - _Requirements: 11.1, 11.2_

- [ ] 2. Add Data Models
  - [ ] 2.1 Add sharing data models to src/models.py
    - ShareableContent dataclass
    - PostResult dataclass
    - ValidationResult dataclass
    - DestinationCapabilities dataclass
    - _Requirements: 2.4_

  - [ ] 2.2 Add scheduling data model
    - ScheduledPost dataclass with to_dict/from_dict
    - _Requirements: 3.1, 3.2_

  - [ ] 2.3 Add collection data models
    - ContentCollection dataclass
    - MarkdownTemplate dataclass
    - _Requirements: 5.1, 7.6_

- [ ] 3. Update Database
  - [ ] 3.1 Add scheduled_posts table
    - Schema with all ScheduledPost fields
    - Index on status and scheduled_time
    - _Requirements: 3.3_

  - [ ] 3.2 Add content_collections table
    - Schema with all ContentCollection fields
    - _Requirements: 5.2_

  - [ ] 3.3 Add markdown_templates table
    - Schema for template storage
    - _Requirements: 7.6_

  - [ ] 3.4 Add CRUD methods for new tables
    - save/get/delete for scheduled posts
    - save/get/delete for collections
    - save/get for templates
    - _Requirements: 3.5, 3.6, 5.3, 5.4, 5.5_

- [ ] 4. Checkpoint - Core infrastructure validation
  - Verify plugin API extensions work
  - Verify database tables created correctly
  - Run existing tests to ensure no regressions

- [ ] 5. Implement Destination Plugins
  - [ ] 5.1 Create Twitter destination plugin
    - OAuth 1.0a authentication
    - post_content() implementation
    - validate_content() with 280 char limit
    - supports_reshare() returns True for 'twitter'
    - reshare() for native Retweet
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ] 5.2 Create LinkedIn destination plugin
    - OAuth 2.0 authentication
    - post_content() implementation
    - validate_content() with LinkedIn limits
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [ ] 6. Implement AI Plugins
  - [ ] 6.1 Create OpenAI plugin
    - Implement generate_text() with GPT API
    - Implement summarize_items()
    - _Requirements: 6.2, 11.1, 11.2_

  - [ ] 6.2 Create Anthropic plugin
    - Implement generate_text() with Claude API
    - Implement summarize_items()
    - _Requirements: 6.2, 11.1, 11.2_

  - [ ] 6.3 Create Ollama plugin
    - Implement generate_text() with local LLM
    - Implement summarize_items()
    - _Requirements: 6.2, 11.1, 11.2_

- [ ] 7. Implement Scheduler Service
  - [ ] 7.1 Create scheduler service plugin
    - Background thread with check loop
    - Query pending posts due for execution
    - Execute via destination plugin
    - Update post status
    - _Requirements: 3.3, 3.4_

  - [ ] 7.2 Implement retry logic
    - Exponential backoff on failure
    - Max retry count tracking
    - Status update on final failure
    - _Requirements: 3.4_

  - [ ] 7.3 Implement recurring posts
    - Create next occurrence after success
    - Support daily and weekly recurrence
    - _Requirements: 3.2_

- [ ] 8. Checkpoint - Backend validation
  - Test posting to Twitter (with mock)
  - Test posting to LinkedIn (with mock)
  - Test scheduler executes due posts
  - Test AI text generation

- [ ] 9. Implement UI Components
  - [ ] 9.1 Add action buttons to content cards
    - Update render_content_card() in components.py
    - Add Share, Schedule, Preview, Collect buttons
    - Add selection checkbox
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ] 9.2 Create share modal component
    - Destination selector
    - Native reshare toggle
    - Text editor with char count
    - Share button with result feedback
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ] 9.3 Create schedule modal component
    - Date/time picker
    - Recurrence selector
    - Schedule button
    - _Requirements: 3.1, 3.2_

  - [ ] 9.4 Create preview component
    - Expandable card with full content
    - Media gallery
    - Metadata display
    - Link to original
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 10. Implement Collections UI
  - [ ] 10.1 Create collections page
    - List collections with counts
    - Create new collection form
    - _Requirements: 5.1, 5.4_

  - [ ] 10.2 Add collection detail view
    - Display items in collection
    - Remove item button
    - Delete collection button
    - _Requirements: 5.3, 5.5_

  - [ ] 10.3 Add collect modal to content cards
    - Select collection dropdown
    - Add to collection button
    - _Requirements: 5.2_

  - [ ] 10.4 Add AI generation to collections
    - Generate Intro button
    - Generate Summary button
    - Display/edit generated text
    - _Requirements: 6.3, 6.4, 6.5, 6.6_

- [ ] 11. Implement Markdown Export
  - [ ] 11.1 Create markdown generator module
    - Jinja2 template rendering
    - Jekyll frontmatter format
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ] 11.2 Add export button to collections
    - Generate markdown
    - Download as .md file
    - _Requirements: 7.4, 7.5_

  - [ ] 11.3 Add template customization
    - Template editor in settings
    - Save custom templates
    - _Requirements: 7.6_

- [ ] 12. Implement Scheduled Posts UI
  - [ ] 12.1 Create scheduled posts page
    - List scheduled posts with status
    - Filter by destination/status
    - _Requirements: 3.5_

  - [ ] 12.2 Add edit/cancel functionality
    - Edit scheduled post
    - Cancel pending post
    - _Requirements: 3.6_

- [ ] 13. Integration
  - [ ] 13.1 Update main.py navigation
    - Add Collections page
    - Add Scheduled Posts page
    - _Requirements: All_

  - [ ] 13.2 Wire action buttons in stream/board modes
    - Pass callbacks to content cards
    - Handle modal state
    - _Requirements: 1.1_

- [ ] 14. Testing
  - [ ] 14.1 Unit tests for DestinationPlugin interface
    - Test validation logic
    - Test capability reporting
    - _Requirements: 8.1-8.7_

  - [ ] 14.2 Integration tests for sharing flow
    - Mock external APIs
    - Verify end-to-end flow
    - _Requirements: 2.1-2.7_

  - [ ] 14.3 Integration tests for scheduling
    - Test scheduler service
    - Verify retry logic
    - _Requirements: 3.1-3.7_

  - [ ] 14.4 Integration tests for curation
    - Test collection CRUD
    - Test markdown export
    - _Requirements: 5.1-5.5, 7.1-7.6_

- [ ] 15. Final Checkpoint
  - All tests passing
  - Manual testing of complete workflows
  - Documentation updated

## Notes

- Twitter API v2 requires elevated access for posting (apply at developer.twitter.com)
- LinkedIn API requires app approval for posting to feed
- Ollama must be installed locally for local LLM support
- Jekyll frontmatter uses `layout: post` by default

## Verification Plan

1. **Plugin API**: Run `pytest tests/` after extending plugins.py
2. **Database**: Verify tables created with `sqlite3 data/number_station.db ".tables"`
3. **Sharing**: Test with Twitter API sandbox/mock
4. **Scheduling**: Create test post, advance time, verify execution
5. **Collections**: Create collection, add items, export markdown, verify format
6. **UI**: Manual testing of all action buttons and modals

## Critical Files

| File | Changes |
|------|---------|
| `src/plugins.py` | Add DestinationPlugin, extend AIPlugin |
| `src/models.py` | Add 6 new data models |
| `src/database.py` | Add 3 tables, CRUD methods |
| `src/plugin_manager.py` | Add get_destination_plugins() |
| `src/ui/components.py` | Action buttons, modals |
| `src/main.py` | Navigation updates |

## New Files

| File | Purpose |
|------|---------|
| `plugins/twitter_destination.py` | Twitter posting |
| `plugins/linkedin_destination.py` | LinkedIn posting |
| `plugins/scheduler_service.py` | Background scheduler |
| `plugins/openai_plugin.py` | OpenAI integration |
| `plugins/anthropic_plugin.py` | Anthropic integration |
| `plugins/ollama_plugin.py` | Local LLM |
| `src/markdown_generator.py` | MD file generation |
| `src/ui/collections.py` | Collection management |
| `src/ui/scheduled_posts.py` | Scheduled posts management |
