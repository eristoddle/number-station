
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.plugin_manager import PluginManager
from src.database import DatabaseManager
from src.models import ContentItem, SourceMetadata, SourceConfiguration
from src.plugins import SourcePlugin

class ContentAggregator:
    """
    Coordinator for fetching content from various sources plugins.

    Handles:
    - Scheduling (checking fetch intervals)
    - Plugin orchestration (configuring and invoking plugins)
    - Content persistence (saving to DB)
    - Deduplication (ignoring existing items)
    - Metadata tracking (updating source stats)

    Validates Requirements 3.2, 9.2, 9.5, 9.6.
    """

    def __init__(self, plugin_manager: PluginManager, db_manager: DatabaseManager):
        self.logger = logging.getLogger(__name__)
        self.plugin_manager = plugin_manager
        self.db = db_manager

    def fetch_all(self) -> Dict[str, int]:
        """
        Trigger fetch for all enabled source configurations that are due.

        Returns:
            Dict mapping source name to number of new items saved.
        """
        results = {}

        # 1. Get all enabled SourceConfigurations
        # Note: We need to iterate ALL types. We might need a method to get ALL source configs regardless of type,
        # or iterate known types.
        # DB Manager currently has get_source_configs_by_type.
        # But we don't know all types a priori easily without querying distinct types or assuming.
        # Let's add get_all_source_configs to DB or just iterate known plugins capabilities.
        # For now, let's fetch types based on loaded plugins?

        # Better: DatabaseManager.get_all_source_configs() would be ideal.
        # Since I cannot modify DB right now without another step, I will simulated it
        # by checking known types from loaded plugins.

        source_plugins = self.plugin_manager.get_source_plugins()
        source_types = set()
        for p in source_plugins:
            source_types.update(p.metadata.capabilities)
            # Also add the plugin name/type just in case convention varies
            # e.g. 'rss', 'twitter'

        # 2. Iterate types and get configs
        # This acts as discovery of what we SHOULD fetch.

        # We also need to handle "Default" sources if any?
        # Currently no default sources in DB unless added.
        # The Plugin configs (table plugin_configs) store "plugin level" config.
        # SourceConfigurations (table source_configurations) store "feed level" config.
        # Our aggregator focuses on SourceConfigurations.

        processed_sources = set()

        for p in source_plugins:
            # We try to match plugin to source configs
            # Convention: SourceConfiguration.source_type must be in Plugin.capabilities
            # Or we can iterate ALL source configs if we add that method.
            pass

        # Since I don't have get_all_source_configs, I will implement a fetch loop
        # that roughly does:
        # 1. Get all source plugins.
        # 2. For each plugin, find all SourceConfigs that match it.
        # 3. Process them.

        for plugin in source_plugins:
            matching_configs = []
            for cap in plugin.metadata.capabilities:
                configs = self.db.get_source_configs_by_type(cap)
                matching_configs.extend(configs)

            # Filter duplicates if multiple caps match same config type (unlikely but possible)
            # processing...
            for config in matching_configs:
                if config.name in processed_sources:
                    continue

                if not config.enabled:
                    continue

                count = self._process_source(config, plugin)
                if count is not None:
                     results[config.name] = count

                processed_sources.add(config.name)

        return results

    def _process_source(self, config: SourceConfiguration, plugin: SourcePlugin) -> Optional[int]:
        """
        Process a single source configuration using the provided plugin.
        Returns number of items saved, or None if skipped (not due).
        """
        try:
            # 1. Check scheduling
            metadata = self.db.get_source_metadata(config.name)

            # If no metadata, treat as never fetched (fetch now)
            # If metadata, check interval
            should_fetch = False
            last_fetch = 0

            if metadata:
                last_fetch = metadata.last_fetch_attempt.timestamp()
                next_fetch = last_fetch + config.fetch_interval
                # Logic: Is now >= next_fetch?
                if time.time() >= next_fetch:
                    should_fetch = True
            else:
                should_fetch = True

            if not should_fetch:
                return None

            self.logger.info(f"Fetching source: {config.name} ({config.source_type})")

            # 2. Configure Plugin (Stateful "Driver" Mode)
            # We merge SourceConfig.config (specifics) with SourceConfig properties (url)
            # RSSPlugin expects 'url', others might expect specific keys.
            # SourceConfiguration has 'url' field and 'config' dict.
            # We pass a synthesized config.
            plugin_config = config.config.copy()
            if config.url:
                plugin_config['url'] = config.url
            plugin_config['fetch_interval'] = config.fetch_interval

            if not plugin.configure(plugin_config):
                self.logger.error(f"Failed to configure plugin {plugin.metadata.name} for source {config.name}")
                return 0

            # 3. Force Fetch (reset internal rate limit if exists, trusting Aggregator schedule)
            # This is a bit invasive, but necessary if reusing plugin instance.
            if hasattr(plugin, '_last_fetch'):
                 plugin._last_fetch = 0

            # 4. Update Metadata (Start)
            now = datetime.now()
            # If metadata doesn't exist, create partial
            if not metadata:
                metadata = SourceMetadata(
                    source_id=config.name,
                    last_fetch_attempt=now,
                    last_fetch_success=None,
                    last_item_count=0,
                    total_items_fetched=0,
                    error_count=0,
                    consecutive_errors=0
                )
            else:
                metadata.last_fetch_attempt = now

            self.db.save_source_metadata(metadata)

            # 5. Fetch
            items = plugin.fetch_content()

            # 6. Save and Update Metadata (End)
            saved_count = self._save_items(items, config)

            metadata.last_fetch_success = now
            metadata.last_item_count = len(items)
            metadata.total_items_fetched += len(items) # Note: tracks fetched, not unique saved?
            # Let's track unique saved? Or just fetched? Requirement 3.6 implies "update history".
            # Let's keep total_items_fetched as raw fetch count.
            metadata.error_count = 0 # reset on success
            metadata.consecutive_errors = 0
            metadata.last_error = None

            self.db.save_source_metadata(metadata)

            return saved_count

        except Exception as e:
            self.logger.error(f"Error processing source {config.name}: {e}")
            # Update error stats
            if metadata:
                 metadata.error_count += 1
                 metadata.consecutive_errors += 1
                 metadata.last_error = str(e)
                 self.db.save_source_metadata(metadata)
            return 0

    def _save_items(self, items: List[ContentItem], config: SourceConfiguration) -> int:
        """
        Save items to database, handling deduplication.
        """
        count = 0
        for item in items:
            # Enforce Source Consistency
            # Ensure the item's source matches our config name?
            # Or trust plugin? Plugin usage might set source to 'RSS Source' or URL.
            # We typically want standardized source name in UI.
            # Overwrite source with friendly config name?
            # Requirement 3.6 implies "feed metadata... custom source management".
            # It's better if item.source refers to the 'feed name'.
            item.source = config.name

            # Save
            # Check existence to count "new" items accurately
            exists = self.db.get_content_item(item.id)
            if self.db.save_content_item(item):
                if not exists:
                    count += 1
        return count
