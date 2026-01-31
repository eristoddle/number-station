
import os
import logging
import threading
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import dropbox
from dropbox.files import WriteMode
from src.plugins import ServicePlugin, PluginMetadata

class DropboxSyncPlugin(ServicePlugin):
    """
    Service plugin to sync Number Station configuration and database to Dropbox.

    This plugin periodically uploads the local SQLite database and configuration JSONs
    to a designated Dropbox App folder.
    """

    def __init__(self):
        super().__init__()
        self._access_token = None
        self._sync_interval = 600  # Default 10 minutes
        self._stop_event = threading.Event()
        self._sync_thread = None
        self._db_path = Path("data/number_station.db")
        self._config_dir = Path("config")
        self._remote_base = "/number_station"

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Dropbox Sync",
            version="1.0.0",
            description="Syncs database and config to Dropbox App folder",
            author="Number Station Team",
            plugin_type="service",
            dependencies=["dropbox"],
            config_schema={
                "access_token": "string (Required)",
                "sync_interval": "integer (optional, default=600)",
                "remote_path": "string (optional, default='/number_station')"
            }
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        if "access_token" not in config:
            self.logger.error("Dropbox Sync requires 'access_token'")
            return False
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        if not self.validate_config(config):
            return False
        self._config = config
        self._access_token = config["access_token"]
        self._sync_interval = config.get("sync_interval", 600)
        self._remote_base = config.get("remote_path", "/number_station")
        return True

    def start(self) -> bool:
        if not self._access_token:
            self.logger.error("Dropbox Sync token not set. Starting disabled.")
            return False

        self.logger.info("Starting Dropbox Sync service")
        self._stop_event.clear()
        self._sync_thread = threading.Thread(target=self._run_sync_loop, daemon=True)
        self._sync_thread.start()
        return True

    def stop(self) -> bool:
        self.logger.info("Stopping Dropbox Sync service")
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        return True

    def _run_sync_loop(self):
        self.logger.info("Dropbox Sync loop started")
        while not self._stop_event.is_set():
            try:
                self.sync_now()
            except Exception as e:
                self.logger.error(f"Error during Dropbox sync: {e}")

            # Wait for next sync or stop event
            self._stop_event.wait(self._sync_interval)

    def sync_now(self):
        """Force a synchronization cycle."""
        self.logger.info("Starting sync cycle...")
        dbx = dropbox.Dropbox(self._access_token)

        # 1. Sync Database
        if self._db_path.exists():
            remote_db = f"{self._remote_base}/number_station.db"
            self._upload_file(dbx, self._db_path, remote_db)

        # 2. Sync Config Directory
        if self._config_dir.exists():
            for config_file in self._config_dir.glob("*.json"):
                remote_config = f"{self._remote_base}/config/{config_file.name}"
                self._upload_file(dbx, config_file, remote_config)

        self.logger.info("Sync cycle completed.")

    def _upload_file(self, dbx: dropbox.Dropbox, local_path: Path, remote_path: str):
        with open(local_path, "rb") as f:
            data = f.read()
            # Basic upload with overwrite
            dbx.files_upload(data, remote_path, mode=WriteMode.overwrite)
            self.logger.debug(f"Uploaded {local_path} to {remote_path}")
