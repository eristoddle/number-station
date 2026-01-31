#!/usr/bin/env python3
"""
Number Station - Command Line Interface

Simple CLI utility to interact with the Number Station database.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_database
from src.models import ContentItem, UserPreferences, SourceConfiguration
from src.migrations import run_migrations, get_migration_status


def cmd_init(args):
    """Initialize database and run migrations."""
    print("Initializing Number Station database...")

    db = get_database()
    success = run_migrations(db)

    if success:
        print("✅ Database initialized successfully")

        # Show migration status
        status = get_migration_status(db)
        print(f"Applied migrations: {status['applied_count']}")
        print(f"Current version: {status['current_version']}")
    else:
        print("❌ Database initialization failed")
        sys.exit(1)


def cmd_status(args):
    """Show database status and statistics."""
    db = get_database()

    print("📊 Number Station Database Status")
    print("=" * 40)

    # Migration status
    migration_status = get_migration_status(db)
    print(f"Migration Status:")
    print(f"  Applied: {migration_status['applied_count']}")
    print(f"  Pending: {migration_status['pending_count']}")
    print(f"  Current Version: {migration_status['current_version']}")
    print(f"  Latest Version: {migration_status['latest_version']}")
    print()

    # Database statistics
    stats = db.get_database_stats()
    print("Content Statistics:")
    print(f"  Content Items: {stats.get('content_items', 0)}")
    print(f"  Source Configs: {stats.get('source_configurations', 0)}")
    print(f"  Plugin Configs: {stats.get('plugin_configs', 0)}")
    print(f"  User Preferences: {stats.get('user_preferences', 0)}")
    print(f"  Plugin Metadata: {stats.get('plugin_metadata', 0)}")


def cmd_add_content(args):
    """Add sample content to the database."""
    db = get_database()

    sample_content = ContentItem(
        id=f"cli-sample-{datetime.now().timestamp()}",
        source=args.source or "CLI Sample",
        source_type=args.type or "cli",
        title=args.title or "Sample Content from CLI",
        content=args.content or "This is sample content added via the CLI utility.",
        author=args.author,
        timestamp=datetime.now(),
        url=args.url or "https://example.com/cli-sample",
        tags=args.tags.split(",") if args.tags else ["cli", "sample"],
        media_urls=[],
        metadata={"added_via": "cli"}
    )

    if db.save_content_item(sample_content):
        print(f"✅ Added content item: {sample_content.title}")
        print(f"   ID: {sample_content.id}")
        print(f"   Source: {sample_content.source}")
        print(f"   Type: {sample_content.source_type}")
    else:
        print("❌ Failed to add content item")
        sys.exit(1)


def cmd_list_content(args):
    """List content items from the database."""
    db = get_database()

    items = db.get_content_items(
        source_type=args.type,
        limit=args.limit,
        offset=args.offset
    )

    if not items:
        print("No content items found.")
        return

    print(f"📝 Content Items ({len(items)} found)")
    print("=" * 60)

    for item in items:
        print(f"ID: {item.id}")
        print(f"Title: {item.title}")
        print(f"Source: {item.source} ({item.source_type})")
        print(f"Author: {item.author or 'Unknown'}")
        print(f"Timestamp: {item.timestamp}")
        print(f"URL: {item.url}")
        if item.tags:
            print(f"Tags: {', '.join(item.tags)}")
        print(f"Content: {item.content[:100]}...")
        print("-" * 60)


def cmd_set_preferences(args):
    """Set user preferences."""
    db = get_database()

    # Get current preferences
    current = db.get_user_preferences()

    # Update with provided values
    new_prefs = UserPreferences(
        ui_mode=args.ui_mode or current.ui_mode,
        theme=args.theme or current.theme,
        update_interval=args.update_interval or current.update_interval,
        auto_refresh=args.auto_refresh if args.auto_refresh is not None else current.auto_refresh
    )

    if db.save_user_preferences(new_prefs):
        print("✅ User preferences updated")
        print(f"   UI Mode: {new_prefs.ui_mode}")
        print(f"   Theme: {new_prefs.theme}")
        print(f"   Update Interval: {new_prefs.update_interval}s")
        print(f"   Auto Refresh: {new_prefs.auto_refresh}")
    else:
        print("❌ Failed to update preferences")
        sys.exit(1)


def cmd_cleanup(args):
    """Clean up old content."""
    db = get_database()

    deleted_count = db.cleanup_old_content(days=args.days)
    print(f"🧹 Cleaned up {deleted_count} old content items (older than {args.days} days)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Number Station CLI - Database management utility"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize database')
    init_parser.set_defaults(func=cmd_init)

    # Status command
    status_parser = subparsers.add_parser('status', help='Show database status')
    status_parser.set_defaults(func=cmd_status)

    # Add content command
    add_parser = subparsers.add_parser('add', help='Add sample content')
    add_parser.add_argument('--title', help='Content title')
    add_parser.add_argument('--content', help='Content body')
    add_parser.add_argument('--source', help='Content source')
    add_parser.add_argument('--type', help='Source type')
    add_parser.add_argument('--author', help='Content author')
    add_parser.add_argument('--url', help='Content URL')
    add_parser.add_argument('--tags', help='Comma-separated tags')
    add_parser.set_defaults(func=cmd_add_content)

    # List content command
    list_parser = subparsers.add_parser('list', help='List content items')
    list_parser.add_argument('--type', help='Filter by source type')
    list_parser.add_argument('--limit', type=int, default=10, help='Number of items to show')
    list_parser.add_argument('--offset', type=int, default=0, help='Number of items to skip')
    list_parser.set_defaults(func=cmd_list_content)

    # Set preferences command
    prefs_parser = subparsers.add_parser('prefs', help='Set user preferences')
    prefs_parser.add_argument('--ui-mode', choices=['stream', 'board'], help='UI mode')
    prefs_parser.add_argument('--theme', choices=['default', 'dark', 'light'], help='Theme')
    prefs_parser.add_argument('--update-interval', type=int, help='Update interval in seconds')
    prefs_parser.add_argument('--auto-refresh', type=bool, help='Enable auto refresh')
    prefs_parser.set_defaults(func=cmd_set_preferences)

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old content')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete content older than N days')
    cleanup_parser.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()