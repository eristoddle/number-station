
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.plugins import ServicePlugin, PluginMetadata
from src.database import get_database
from src.models import ScheduledPost, PostResult, ShareableContent

class SchedulerServicePlugin(ServicePlugin):
    """
    Service plugin to handle scheduled posts and recurring content.

    Validates Requirements 3.2, 3.3, 3.4:
    - Background thread for monitoring scheduled tasks
    - Execution via destination plugins
    - Retry logic with exponential backoff (simplified)
    - Recurring post support (daily/weekly)
    """

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()
        self._thread = None
        self._check_interval = 60 # Check every minute
        self._plugin_manager = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Scheduler Service",
            version="1.0.0",
            description="Executes scheduled posts and manages recurrence",
            author="Number Station Team",
            plugin_type="service",
            capabilities=["scheduling", "retries", "recurrence"],
            config_schema={
                "check_interval": "integer (optional, default=60)"
            }
        )

    def set_plugin_manager(self, pm):
        """Injected by PluginManager."""
        self._plugin_manager = pm

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        self._config = config
        self._check_interval = config.get("check_interval", 60)
        return True

    def start(self) -> bool:
        self.logger.info("Starting Scheduler Service")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> bool:
        self.logger.info("Stopping Scheduler Service")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        return True

    def _run_loop(self):
        self.logger.info("Scheduler loop started")
        while not self._stop_event.is_set():
            try:
                self._process_scheduled_posts()
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")

            self._stop_event.wait(self._check_interval)

    def _process_scheduled_posts(self):
        db = get_database()
        now = datetime.now()

        # Get pending posts
        all_pending = db.get_scheduled_posts(status="pending")
        # Filter those due now
        due_posts = [p for p in all_pending if p.scheduled_time <= now]

        if due_posts:
            self.logger.info(f"Processsing {len(due_posts)} due posts")

        for post in due_posts:
            self._execute_post(post)

    def _execute_post(self, post: ScheduledPost):
        db = get_database()
        self.logger.info(f"Executing scheduled post {post.id} to {post.destination_plugin}")

        # Update status to executing to prevent double processing
        post.status = "executing"
        post.updated_at = datetime.now()
        db.save_scheduled_post(post)

        try:
            if not self._plugin_manager:
                raise Exception("Service Error: PluginManager not injected")

            dest_plugin = self._plugin_manager.registry.get_plugin(post.destination_plugin)

            if not dest_plugin:
                raise Exception(f"Destination plugin '{post.destination_plugin}' not found or not loaded")

            # Execute posting
            result = dest_plugin.post_content(post.content)

            if result.success:
                post.status = "success"
                post.result_url = result.url
                self.logger.info(f"Successfully posted {post.id} to {post.destination_plugin}")

                # Handle Recurrence
                if post.recurrence:
                    self._schedule_next_occurrence(post)
            else:
                self._handle_failure(post, result.error)

        except Exception as e:
            self.logger.error(f"Execution error for post {post.id}: {e}")
            self._handle_failure(post, str(e))

        post.updated_at = datetime.now()
        db.save_scheduled_post(post)

    def _handle_failure(self, post: ScheduledPost, error: str):
        post.last_error = error
        post.retry_count += 1

        max_retries = 3
        if post.retry_count <= max_retries:
            post.status = "pending" # Will try again in the next loop
            # Increment scheduled time for a simple "backoff"
            post.scheduled_time = datetime.now() + timedelta(minutes=5 * post.retry_count)
            self.logger.warning(f"Post {post.id} failed, rescheduled for retry in {5 * post.retry_count}m: {error}")
        else:
            post.status = "failed"
            self.logger.error(f"Post {post.id} failed after {max_retries} retries: {error}")

    def _schedule_next_occurrence(self, post: ScheduledPost):
        next_time = None
        if post.recurrence == "daily":
            next_time = post.scheduled_time + timedelta(days=1)
        elif post.recurrence == "weekly":
            next_time = post.scheduled_time + timedelta(weeks=1)

        if next_time:
            new_post = ScheduledPost(
                id=str(uuid.uuid4()),
                destination_plugin=post.destination_plugin,
                content=post.content,
                scheduled_time=next_time,
                recurrence=post.recurrence,
                status="pending"
            )
            get_database().save_scheduled_post(new_post)
            self.logger.info(f"Scheduled next occurrence ({post.recurrence}) of {post.id} for {next_time}")
