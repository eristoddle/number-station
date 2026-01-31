#!/usr/bin/env python3
"""
Number Station - Plugin Architecture

This module defines the plugin base classes, interfaces, and registry system
for the Number Station application. It provides the foundation for extensible
content sources, filters, and themes.

Validates Requirements 6.4, 6.5, 6.6, 7.3, 7.4, 7.5:
- Standardized plugin API for content sources
- Standardized plugin API for content filters
- Standardized plugin API for UI components
- Standard interfaces for content source plugins
- Standard interfaces for filter plugins
- Standard interfaces for UI theme plugins
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, Set
from dataclasses import dataclass
import logging
import importlib
import importlib.util
import inspect
from pathlib import Path
import json

from .models import (
    ContentItem, PluginMetadata, ShareableContent, PostResult,
    ValidationResult, DestinationCapabilities
)


class PluginValidationError(Exception):
    """Raised when plugin validation fails."""
    pass


class PluginCompatibilityError(Exception):
    """Raised when plugin compatibility check fails."""
    pass


@dataclass
class UIContext:
    """
    UI context information passed to theme plugins.

    Contains information about the current UI state, mode, and configuration
    that theme plugins need to apply appropriate styling.
    """
    mode: str  # 'stream' or 'board'
    theme_name: str
    user_preferences: Dict[str, Any]
    content_count: int
    active_sources: List[str]


class SourcePlugin(ABC):
    """
    Abstract base class for content source plugins.

    Source plugins are responsible for fetching content from external sources
    (RSS feeds, social media APIs, websites, etc.) and normalizing it into
    the standard ContentItem format.

    Validates Requirements 6.4, 7.3:
    - Standardized plugin API for content sources
    - Standard interfaces for content source plugins
    """

    def __init__(self):
        """Initialize the source plugin."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._config: Dict[str, Any] = {}
        self._enabled: bool = True

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Returns:
            PluginMetadata: Plugin information including name, version, capabilities
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid, False otherwise

        Raises:
            PluginValidationError: If configuration is invalid with details
        """
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the plugin with provided settings.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        pass

    @abstractmethod
    def fetch_content(self) -> List[ContentItem]:
        """
        Fetch content from the source.

        Returns:
            List[ContentItem]: List of normalized content items

        Raises:
            Exception: If content fetching fails
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to the content source.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        pass

    def initialize(self) -> bool:
        """
        Initialize the plugin.

        Called during plugin loading. Override to perform initialization tasks.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.logger.info(f"Initializing plugin {self.metadata.name}")
        return True

    def start(self) -> bool:
        """
        Start the plugin.

        Called when the plugin is activated. Override to start background tasks.

        Returns:
            bool: True if start was successful, False otherwise
        """
        self.logger.info(f"Starting plugin {self.metadata.name}")
        self._enabled = True
        return True

    def stop(self) -> bool:
        """
        Stop the plugin.

        Called when the plugin is deactivated. Override to stop background tasks.

        Returns:
            bool: True if stop was successful, False otherwise
        """
        self.logger.info(f"Stopping plugin {self.metadata.name}")
        self._enabled = False
        return True

    def cleanup(self) -> bool:
        """
        Clean up plugin resources.

        Called during plugin unloading. Override to clean up resources.

        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        self.logger.info(f"Cleaning up plugin {self.metadata.name}")
        return True

    @property
    def config(self) -> Dict[str, Any]:
        """Get current plugin configuration."""
        return self._config.copy()

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled


class FilterPlugin(ABC):
    """
    Abstract base class for content filter plugins.

    Filter plugins process and rank content based on various criteria,
    allowing users to customize how content is filtered and prioritized.

    Validates Requirements 6.5, 7.4:
    - Standardized plugin API for content filters
    - Standard interfaces for filter plugins
    """

    def __init__(self):
        """Initialize the filter plugin."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._config: Dict[str, Any] = {}
        self._enabled: bool = True

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Returns:
            PluginMetadata: Plugin information including name, version, capabilities
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid, False otherwise

        Raises:
            PluginValidationError: If configuration is invalid with details
        """
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the plugin with provided settings.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        pass

    @abstractmethod
    def filter_content(self, items: List[ContentItem]) -> List[ContentItem]:
        """
        Filter and rank content items.

        Args:
            items: List of content items to filter

        Returns:
            List[ContentItem]: Filtered and ranked content items
        """
        pass

    def initialize(self) -> bool:
        """
        Initialize the plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.logger.info(f"Initializing filter plugin {self.metadata.name}")
        return True

    def start(self) -> bool:
        """
        Start the plugin.

        Returns:
            bool: True if start was successful, False otherwise
        """
        self.logger.info(f"Starting filter plugin {self.metadata.name}")
        self._enabled = True
        return True

    def stop(self) -> bool:
        """
        Stop the plugin.

        Returns:
            bool: True if stop was successful, False otherwise
        """
        self.logger.info(f"Stopping filter plugin {self.metadata.name}")
        self._enabled = False
        return True

    def cleanup(self) -> bool:
        """
        Clean up plugin resources.

        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        self.logger.info(f"Cleaning up filter plugin {self.metadata.name}")
        return True

    @property
    def config(self) -> Dict[str, Any]:
        """Get current plugin configuration."""
        return self._config.copy()

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled


class ThemePlugin(ABC):
    """
    Abstract base class for theme plugins.

    Theme plugins customize the visual appearance of the Number Station UI,
    providing different styling options for both Stream and Board modes.

    Validates Requirements 6.6, 7.5:
    - Standardized plugin API for UI components
    - Standard interfaces for UI theme plugins
    """

    def __init__(self):
        """Initialize the theme plugin."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._config: Dict[str, Any] = {}
        self._enabled: bool = True

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Return plugin metadata.

        Returns:
            PluginMetadata: Plugin information including name, version, capabilities
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid, False otherwise

        Raises:
            PluginValidationError: If configuration is invalid with details
        """
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the plugin with provided settings.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        pass

    @abstractmethod
    def apply_theme(self, ui_context: UIContext) -> Dict[str, Any]:
        """
        Apply theme styling to the UI.

        Args:
            ui_context: Current UI context and state information

        Returns:
            Dict[str, Any]: Theme configuration for the UI framework
        """
        pass

    @abstractmethod
    def get_css(self) -> str:
        """
        Get CSS styles for the theme.

        Returns:
            str: CSS stylesheet content
        """
        pass

    @abstractmethod
    def supports_mode(self, mode: str) -> bool:
        """
        Check if theme supports a specific UI mode.

        Args:
            mode: UI mode ('stream' or 'board')

        Returns:
            bool: True if mode is supported, False otherwise
        """
        pass

    def initialize(self) -> bool:
        """
        Initialize the plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.logger.info(f"Initializing theme plugin {self.metadata.name}")
        return True

    def start(self) -> bool:
        """
        Start the plugin.

        Returns:
            bool: True if start was successful, False otherwise
        """
        self.logger.info(f"Starting theme plugin {self.metadata.name}")
        self._enabled = True
        return True

    def stop(self) -> bool:
        """
        Stop the plugin.

        Returns:
            bool: True if stop was successful, False otherwise
        """
        self.logger.info(f"Stopping theme plugin {self.metadata.name}")
        self._enabled = False
        return True

    def cleanup(self) -> bool:
        """
        Clean up plugin resources.

        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        self.logger.info(f"Cleaning up theme plugin {self.metadata.name}")
        return True

    @property
    def config(self) -> Dict[str, Any]:
        """Get current plugin configuration."""
        return self._config.copy()

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled


class AIPlugin(ABC):
    """
    Abstract base class for AI/ML plugins.
    Used for content ranking, summarization, and automated actions.

    Validates Requirements 11.1, 11.2, 11.3, 11.5.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._config: Dict[str, Any] = {}
        self._enabled: bool = True

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata: pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool: pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool: pass

    @abstractmethod
    def rank_items(self, items: List[ContentItem]) -> List[ContentItem]:
        """Rank or score items using AI models."""
        pass

    @abstractmethod
    def process_item(self, item: ContentItem) -> ContentItem:
        """Apply AI transformations to a single item (e.g. summarization)."""
        pass

    @abstractmethod
    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate text using AI model.

        Args:
            prompt: Text prompt for generation
            context: Optional context information

        Returns:
            str: Generated text
        """
        pass

    @abstractmethod
    def summarize_items(self, items: List[ContentItem], style: str = "concise") -> str:
        """
        Summarize multiple items into a single text.

        Args:
            items: List of content items to summarize
            style: Summary style (concise, detailed, etc.)

        Returns:
            str: Summarized text
        """
        pass

    def initialize(self) -> bool: return True
    def start(self) -> bool: return True
    def stop(self) -> bool: return True
    def cleanup(self) -> bool: return True

    @property
    def config(self) -> Dict[str, Any]: return self._config.copy()
    @property
    def enabled(self) -> bool: return self._enabled

class ServicePlugin(ABC):
    """
    Abstract base class for background service plugins.
    Used for long-running tasks like synchronization, maintenance, or monitoring.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self._config: Dict[str, Any] = {}
        self._enabled: bool = True

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata: pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool: pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool: pass

    def initialize(self) -> bool: return True
    def start(self) -> bool: return True
    def stop(self) -> bool: return True
    def cleanup(self) -> bool: return True

    @property
    def config(self) -> Dict[str, Any]: return self._config.copy()
    @property
    def enabled(self) -> bool: return self._enabled

class DestinationPlugin(ABC):
    """
    Abstract base class for destination plugins.

    Destination plugins are responsible for posting content to external platforms
    (Twitter, LinkedIn, Mastodon, etc.).

    Validates Requirements 8.1, 8.2, 8.3, 8.4, 8.5:
    - Standardized plugin API for destinations
    - Content posting and validation
    - Capability reporting
    - Native reshare support
    """

    def __init__(self):
        """Initialize the destination plugin."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._config: Dict[str, Any] = {}
        self._enabled: bool = True

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the plugin."""
        pass

    @abstractmethod
    def post_content(self, content: ShareableContent) -> PostResult:
        """
        Post content to the destination.

        Args:
            content: Content to post

        Returns:
            PostResult: Result of the posting operation
        """
        pass

    @abstractmethod
    def validate_content(self, content: ShareableContent) -> ValidationResult:
        """
        Validate content against destination limits.

        Args:
            content: Content to validate

        Returns:
            ValidationResult: Validation details
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> DestinationCapabilities:
        """
        Return destination capabilities (length limits, media support, etc.).

        Returns:
            DestinationCapabilities: Description of what this destination supports
        """
        pass

    @abstractmethod
    def supports_reshare(self, source_type: str) -> bool:
        """
        Check if destination supports native reshare for a source type.

        Args:
            source_type: Type of the original content source

        Returns:
            bool: True if native reshare is supported
        """
        pass

    @abstractmethod
    def reshare(self, content_item: ContentItem) -> PostResult:
        """
        Perform native reshare (e.g., Retweet).

        Args:
            content_item: Original content item to reshare

        Returns:
            PostResult: Result of the reshare operation
        """
        pass

    def initialize(self) -> bool:
        """Initialize the plugin."""
        self.logger.info(f"Initializing destination plugin {self.metadata.name}")
        return True

    def start(self) -> bool:
        """Start the plugin."""
        self.logger.info(f"Starting destination plugin {self.metadata.name}")
        self._enabled = True
        return True

    def stop(self) -> bool:
        """Stop the plugin."""
        self.logger.info(f"Stopping destination plugin {self.metadata.name}")
        self._enabled = False
        return True

    def cleanup(self) -> bool:
        """Clean up plugin resources."""
        self.logger.info(f"Cleaning up destination plugin {self.metadata.name}")
        return True

    @property
    def config(self) -> Dict[str, Any]:
        """Get current plugin configuration."""
        return self._config.copy()

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled


class PluginRegistry:
    """
    Plugin registry system with discovery mechanisms.

    Manages plugin discovery, loading, validation, and lifecycle management.
    Provides a centralized registry for all available plugins.

    Validates Requirements 6.1, 7.1:
    - Plugin registry system
    - Plugin registration endpoints
    """

    def __init__(self):
        """Initialize the plugin registry."""
        self.logger = logging.getLogger(__name__)
        self._plugins: Dict[str, Type] = {}
        self._loaded_plugins: Dict[str, object] = {}
        self._plugin_metadata: Dict[str, PluginMetadata] = {}

    def discover_plugins(self, plugin_dirs: List[Path]) -> List[str]:
        """
        Discover plugins in specified directories.

        Args:
            plugin_dirs: List of directories to search for plugins

        Returns:
            List[str]: List of discovered plugin names
        """
        discovered = []

        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                self.logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue

            self.logger.info(f"Discovering plugins in {plugin_dir}")

            # Look for Python files in the plugin directory
            for plugin_file in plugin_dir.glob("*.py"):
                if plugin_file.name.startswith("__"):
                    continue

                try:
                    plugin_name = plugin_file.stem
                    self.logger.debug(f"Attempting to load plugin: {plugin_name}")

                    # Import the plugin module
                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Find plugin classes in the module
                        plugin_classes = self._find_plugin_classes(module)

                        for plugin_class in plugin_classes:
                            class_name = f"{plugin_name}.{plugin_class.__name__}"
                            self._plugins[class_name] = plugin_class
                            discovered.append(class_name)
                            self.logger.info(f"Discovered plugin: {class_name}")

                except Exception as e:
                    self.logger.error(f"Error discovering plugin {plugin_name}: {e}")

        return discovered

    def _find_plugin_classes(self, module) -> List[Type]:
        """
        Find plugin classes in a module.

        Args:
            module: Python module to search

        Returns:
            List[Type]: List of plugin class types
        """
        plugin_classes = []

        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip imported classes
            if obj.__module__ != module.__name__:
                continue

            # Check if class inherits from plugin base classes
            if (issubclass(obj, SourcePlugin) or
                issubclass(obj, FilterPlugin) or
                issubclass(obj, ThemePlugin) or
                issubclass(obj, AIPlugin) or
                issubclass(obj, ServicePlugin) or
                issubclass(obj, DestinationPlugin)) and obj not in [SourcePlugin, FilterPlugin, ThemePlugin, AIPlugin, ServicePlugin, DestinationPlugin]:
                plugin_classes.append(obj)

        return plugin_classes

    def register_plugin(self, plugin_class: Type, plugin_name: Optional[str] = None) -> bool:
        """
        Register a plugin class.

        Args:
            plugin_class: Plugin class to register
            plugin_name: Optional custom name for the plugin

        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            name = plugin_name or f"{plugin_class.__module__}.{plugin_class.__name__}"

            # Validate plugin class
            if not self._validate_plugin_class(plugin_class):
                raise PluginValidationError(f"Plugin class validation failed: {name}")

            self._plugins[name] = plugin_class
            self.logger.info(f"Registered plugin: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Error registering plugin {plugin_class}: {e}")
            return False

    def _validate_plugin_class(self, plugin_class: Type) -> bool:
        """
        Validate that a plugin class implements required interfaces.

        Args:
            plugin_class: Plugin class to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Check if it's a valid plugin type
        if not (issubclass(plugin_class, SourcePlugin) or
                issubclass(plugin_class, FilterPlugin) or
                issubclass(plugin_class, ThemePlugin) or
                issubclass(plugin_class, AIPlugin) or
                issubclass(plugin_class, ServicePlugin) or
                issubclass(plugin_class, DestinationPlugin)):
            return False

        # Check required methods are implemented
        required_methods = ['metadata', 'validate_config', 'configure']

        if issubclass(plugin_class, SourcePlugin):
            required_methods.extend(['fetch_content', 'test_connection'])
        elif issubclass(plugin_class, FilterPlugin):
            required_methods.extend(['filter_content'])
        elif issubclass(plugin_class, ThemePlugin):
            required_methods.extend(['apply_theme', 'get_css', 'supports_mode'])
        elif issubclass(plugin_class, AIPlugin):
            required_methods.extend(['rank_items', 'process_item', 'generate_text', 'summarize_items'])
        elif issubclass(plugin_class, DestinationPlugin):
            required_methods.extend(['post_content', 'validate_content', 'get_capabilities', 'supports_reshare', 'reshare'])

        for method_name in required_methods:
            if not hasattr(plugin_class, method_name):
                self.logger.error(f"Plugin {plugin_class} missing required method: {method_name}")
                return False

            attr = getattr(plugin_class, method_name)

            # special case for metadata which is a property
            if method_name == 'metadata':
                if not isinstance(attr, property) and not callable(attr):
                    self.logger.error(f"Plugin {plugin_class} attribute {method_name} is not a property or callable")
                    return False
                # Check for abstract property
                if isinstance(attr, property) and getattr(attr.fget, "__isabstractmethod__", False):
                     self.logger.error(f"Plugin {plugin_class} property {method_name} is abstract")
                     return False
            else:
                if not callable(attr):
                    self.logger.error(f"Plugin {plugin_class} method {method_name} is not callable")
                    return False
                # Check for abstract method
                if getattr(attr, "__isabstractmethod__", False):
                    self.logger.error(f"Plugin {plugin_class} method {method_name} is abstract")
                    return False

        return True

    def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load and initialize a plugin.

        Args:
            plugin_name: Name of the plugin to load
            config: Optional configuration for the plugin

        Returns:
            bool: True if loading was successful, False otherwise
        """
        if plugin_name not in self._plugins:
            raise PluginValidationError(f"Plugin not found: {plugin_name}")

        if plugin_name in self._loaded_plugins:
            self.logger.warning(f"Plugin already loaded: {plugin_name}")
            return True

        plugin_class = self._plugins[plugin_name]
        plugin_instance = plugin_class()

        # Store metadata
        self._plugin_metadata[plugin_name] = plugin_instance.metadata

        # Validate compatibility
        if not self._check_compatibility(plugin_instance.metadata):
             raise PluginCompatibilityError(f"Plugin compatibility check failed: {plugin_name}")

        # Configure plugin if config provided
        if config:
            if not plugin_instance.validate_config(config):
                raise PluginValidationError(f"Plugin configuration validation failed: {plugin_name}")

            if not plugin_instance.configure(config):
                raise PluginValidationError(f"Plugin configuration failed: {plugin_name}")

        # Initialize plugin
        if not plugin_instance.initialize():
            raise PluginValidationError(f"Plugin initialization failed: {plugin_name}")

        self._loaded_plugins[plugin_name] = plugin_instance
        self.logger.info(f"Loaded plugin: {plugin_name}")
        return True

    def _check_compatibility(self, metadata: PluginMetadata) -> bool:
        """
        Check plugin compatibility with the system.

        Args:
            metadata: Plugin metadata to check

        Returns:
            bool: True if compatible, False otherwise
        """
        # Check plugin type is valid
        valid_types = ['source', 'filter', 'theme', 'ai', 'service', 'destination']
        if metadata.plugin_type not in valid_types:
            self.logger.error(f"Invalid plugin type: {metadata.plugin_type}")
            return False

        # Check dependencies (can be either other plugins or Python packages)
        for dependency in metadata.dependencies:
            # Check if it's a registered/loaded plugin
            is_plugin = dependency in self._plugins or dependency in self._loaded_plugins

            # Check if it's a loadable Python module
            is_module = importlib.util.find_spec(dependency) is not None

            if not is_plugin and not is_module:
                 self.logger.warning(f"Plugin dependency not available: {dependency}")

        return True

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            bool: True if unloading was successful, False otherwise
        """
        try:
            if plugin_name not in self._loaded_plugins:
                self.logger.warning(f"Plugin not loaded: {plugin_name}")
                return True

            plugin_instance = self._loaded_plugins[plugin_name]

            # Stop and cleanup plugin
            plugin_instance.stop()
            plugin_instance.cleanup()

            # Remove from loaded plugins
            del self._loaded_plugins[plugin_name]
            if plugin_name in self._plugin_metadata:
                del self._plugin_metadata[plugin_name]

            self.logger.info(f"Unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False

    def get_plugin(self, plugin_name: str) -> Optional[object]:
        """
        Get a loaded plugin instance.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance if loaded, None otherwise
        """
        return self._loaded_plugins.get(plugin_name)

    def get_plugins_by_type(self, plugin_type: str) -> List[object]:
        """
        Get all loaded plugins of a specific type.

        Args:
            plugin_type: Type of plugins to retrieve ('source', 'filter', 'theme')

        Returns:
            List of plugin instances
        """
        plugins = []
        for plugin_name, plugin_instance in self._loaded_plugins.items():
            if plugin_name in self._plugin_metadata:
                metadata = self._plugin_metadata[plugin_name]
                if metadata.plugin_type == plugin_type and plugin_instance.enabled:
                    plugins.append(plugin_instance)
        return plugins

    def list_available_plugins(self) -> List[str]:
        """
        List all available (registered) plugins.

        Returns:
            List of plugin names
        """
        return list(self._plugins.keys())

    def list_loaded_plugins(self) -> List[str]:
        """
        List all loaded plugins.

        Returns:
            List of loaded plugin names
        """
        return list(self._loaded_plugins.keys())

    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get metadata for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginMetadata if available, None otherwise
        """
        return self._plugin_metadata.get(plugin_name)