#!/usr/bin/env python3
"""
Property-based tests for Number Station Plugin System Contracts.

This module contains property-based tests that verify plugin interface compliance,
lifecycle management, and fault tolerance as specified in the design document.
"""

import pytest
from unittest.mock import MagicMock
from typing import Dict, Any, List, Type
import logging

from hypothesis import given, strategies as st, settings, stateful
from hypothesis.stateful import rule, RuleBasedStateMachine, Bundle

from src.plugins import (
    PluginRegistry,
    SourcePlugin,
    FilterPlugin,
    ThemePlugin,
    PluginMetadata,
    UIContext,
    PluginValidationError
)
from src.plugin_manager import PluginManager
from src.models import ContentItem

# --- Strategies ---

@st.composite
def valid_plugin_metadata(draw):
    """Generate valid PluginMetadata."""
    return PluginMetadata(
        name=draw(st.text(min_size=1, max_size=50)),
        version=draw(st.text(min_size=1, max_size=10)),
        description=draw(st.text(max_size=100)),
        author=draw(st.text(max_size=50)),
        plugin_type=draw(st.sampled_from(['source', 'filter', 'theme'])),
        dependencies=draw(st.lists(st.text(min_size=1), max_size=5)),
        capabilities=draw(st.lists(st.text(min_size=1), max_size=5)),
        config_schema=draw(st.dictionaries(st.text(), st.text(), max_size=5))
    )

# --- Property 24: Plugin Interface Compliance ---

class TestPluginInterfaceCompliance:
    """
    Property-based tests for Plugin Interface Compliance.

    **Feature: number-station, Property 24: Plugin Interface Compliance**
    **Validates: Requirements 6.4, 6.5, 6.6, 7.3, 7.4, 7.5**
    """

    def create_mock_source_plugin(self, name="TestPlugin", valid=True):
        """Create a mock SourcePlugin class dynamically."""
        class MockSource(SourcePlugin):
            @property
            def metadata(self):
                return PluginMetadata(name, "1.0", "Desc", "Author", "source")

            def validate_config(self, config): return True
            def configure(self, config): return True
            def fetch_content(self): return []
            def test_connection(self): return True

        if not valid:
            # Remove a required method to make it invalid
            delattr(MockSource, 'fetch_content')

        return MockSource

    def create_mock_filter_plugin(self, name="TestFilter", valid=True):
        """Create a mock FilterPlugin class dynamically."""
        class MockFilter(FilterPlugin):
            @property
            def metadata(self):
                return PluginMetadata(name, "1.0", "Desc", "Author", "filter")

            def validate_config(self, config): return True
            def configure(self, config): return True
            def filter_content(self, items): return items

        if not valid:
            delattr(MockFilter, 'filter_content')

        return MockFilter

    def create_mock_theme_plugin(self, name="TestTheme", valid=True):
        """Create a mock ThemePlugin class dynamically."""
        class MockTheme(ThemePlugin):
            @property
            def metadata(self):
                return PluginMetadata(name, "1.0", "Desc", "Author", "theme")

            def validate_config(self, config): return True
            def configure(self, config): return True
            def apply_theme(self, ui_context): return {}
            def get_css(self): return ""
            def supports_mode(self, mode): return True

        if not valid:
            delattr(MockTheme, 'apply_theme')

        return MockTheme

    @given(st.sampled_from(['source', 'filter', 'theme']))
    @settings(max_examples=50)
    def test_registry_validates_plugin_interfaces(self, plugin_type):
        """
        Property: PluginRegistry should validate that plugins implement their required interfaces.
        """
        registry = PluginRegistry()

        if plugin_type == 'source':
            valid_plugin = self.create_mock_source_plugin(valid=True)
            invalid_plugin = self.create_mock_source_plugin(valid=False)
        elif plugin_type == 'filter':
            valid_plugin = self.create_mock_filter_plugin(valid=True)
            invalid_plugin = self.create_mock_filter_plugin(valid=False)
        else: # theme
            valid_plugin = self.create_mock_theme_plugin(valid=True)
            invalid_plugin = self.create_mock_theme_plugin(valid=False)

        # Should accept valid plugin
        assert registry._validate_plugin_class(valid_plugin) is True

        # Should reject invalid plugin
        assert registry._validate_plugin_class(invalid_plugin) is False

# --- Property 22: Plugin Lifecycle Management ---

class PluginLifecycleStateMachine(RuleBasedStateMachine):
    """
    State machine test for Plugin Lifecycle Management.

    **Feature: number-station, Property 22: Plugin Lifecycle Management**
    **Validates: Requirements 6.2, 7.2**
    """

    def __init__(self):
        super().__init__()
        self.mock_db = MagicMock()
        self.manager = PluginManager(self.mock_db)

        # Manually register a test plugin since we haven't loaded from disk
        self.plugin_name = "LifecycleTestPlugin"

        class TestPlugin(SourcePlugin):
            @property
            def metadata(self):
                return PluginMetadata("LifecycleTestPlugin", "1.0", "Desc", "Auth", "source")
            def validate_config(self, c): return True
            def configure(self, c): return True
            def fetch_content(self): return []
            def test_connection(self): return True

        self.manager.registry._plugins[self.plugin_name] = TestPlugin

        # Track expected state
        self.is_loaded = False
        self.is_enabled = False # Enabled implies started in Manager logic mostly, but let's track separately
        self.is_running = False

    @rule()
    def load_plugin(self):
        """Transition: Unloaded -> Loaded"""
        # Can be loaded if not already loaded (or if reloading which manager protects against)
        success = self.manager.load_plugin(self.plugin_name)
        if success:
            self.is_loaded = True
        # If already loaded, it stays loaded

    @rule()
    def start_plugin(self):
        """Transition: Loaded -> Running"""
        if not self.is_loaded:
            # Cannot start if not loaded
            assert self.manager.start_plugin(self.plugin_name) is False
            return

        success = self.manager.start_plugin(self.plugin_name)
        if success:
            self.is_running = True

    @rule()
    def stop_plugin(self):
        """Transition: Running -> Stopped (Loaded but not running)"""
        # Can stop even if not running (idempotent)
        success = self.manager.stop_plugin(self.plugin_name)
        if success:
            self.is_running = False

    @rule()
    def unload_plugin(self):
        """Transition: Loaded -> Unloaded"""
        success = self.manager.unload_plugin(self.plugin_name)
        if success:
            self.is_loaded = False
            self.is_running = False

    @stateful.invariant()
    def check_state_consistency(self):
        """Verify internal state matches manager state."""
        plugin = self.manager.registry.get_plugin(self.plugin_name)

        if self.is_loaded:
            assert plugin is not None
            # If running, enabled should be true
            if self.is_running:
                assert plugin.enabled is True
        else:
            assert plugin is None

    @stateful.invariant()
    def check_health_status(self):
        """Verify health status makes sense."""
        if self.is_running:
            # Should be healthy if running without errors
            # (Note: In this simple model we don't inject errors yet)
            assert self.manager.get_plugin_health(self.plugin_name) is True

# --- Property 25: Plugin Fault Tolerance ---

class TestPluginFaultTolerance:
    """
    Property-based tests for Plugin Fault Tolerance.

    **Feature: number-station, Property 25: Plugin Fault Tolerance**
    **Validates: Requirements 6.7**
    """

    def create_faulty_plugin(self, name, fail_on_init=False, fail_on_start=False, fail_on_stop=False):
        """Create a plugin that raises exceptions."""
        class FaultyPlugin(SourcePlugin):
            @property
            def metadata(self):
                return PluginMetadata(name, "1.0", "Desc", "Auth", "source")
            def validate_config(self, c): return True
            def configure(self, c): return True
            def fetch_content(self): return []
            def test_connection(self): return True

            def initialize(self):
                if fail_on_init: raise RuntimeError("Init Failed")
                return super().initialize()

            def start(self):
                if fail_on_start: raise RuntimeError("Start Failed")
                return super().start()

            def stop(self):
                if fail_on_stop: raise RuntimeError("Stop Failed")
                return super().stop()

        return FaultyPlugin

    @given(st.booleans(), st.booleans(), st.booleans())
    @settings(max_examples=50)
    def test_manager_handles_lifecycle_exceptions(self, fail_init, fail_start, fail_stop):
        """
        Property: PluginManager should catch and isolate exceptions during plugin lifecycle methods,
        ensuring the system does not crash and the plugin is marked unhealthy.
        """
        plugin_name = f"FaultyPlugin_{fail_init}_{fail_start}_{fail_stop}"
        FaultyClass = self.create_faulty_plugin(plugin_name, fail_init, fail_start, fail_stop)

        mock_db = MagicMock()
        manager = PluginManager(mock_db)

        # Inject faulty plugin
        manager.registry._plugins[plugin_name] = FaultyClass

        # Test Initialize
        with pytest.raises(Exception) if False else pytest.warns(None) as record:
            # We expect NO uncaught exceptions to propagate out of manager methods
            # load_plugin calls initialize()
            loaded = manager.load_plugin(plugin_name)

        if fail_init:
            assert loaded is False
            # Should record error
            assert len(manager.get_plugin_errors(plugin_name)) > 0
            # If init failed, we can't really start it, so we stop here
            return
        else:
            assert loaded is True

        # Test Start
        started = manager.start_plugin(plugin_name)
        if fail_start:
            assert started is False
            assert len(manager.get_plugin_errors(plugin_name)) > 0
            assert manager.get_plugin_health(plugin_name) is False
        else:
            assert started is True
            assert manager.get_plugin_health(plugin_name) is True

        # Test Stop (if started or loaded)
        stopped = manager.stop_plugin(plugin_name)
        if fail_stop and started:
            # Note: The implementation of stop might return False on failure,
            # OR it might catch and log. Let's assume it should return False on failure.
            # But wait, stop() is often best-effort.
            # Looking at PluginManager.stop_plugin implementation:
            # It catches Exception and returns False.
            assert stopped is False
            assert len(manager.get_plugin_errors(plugin_name)) > 0
        elif not started:
             # Stop on unstarted plugin might just return True (idempotent) or False depending on logic.
             # Logic says: if plugin loaded, call stop(). If stop() returns True, return True.
             pass
        else:
             assert stopped is True
