#!/usr/bin/env python3
"""
Property-based tests for Number Station ContentItem schema compliance.

This module contains property-based tests that verify ContentItem schema compliance
across all valid inputs using the Hypothesis testing framework.
"""

import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json
import string

from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite

from src.models import ContentItem


# Custom strategies for generating test data
@composite
def valid_non_empty_string(draw, min_size=1, max_size=100):
    """Generate valid non-empty strings."""
    return draw(st.text(min_size=min_size, max_size=max_size).filter(lambda x: x.strip()))


@composite
def valid_url(draw):
    """Generate valid URL strings."""
    protocols = ["http", "https"]
    domains = ["example.com", "test.org", "sample.net", "demo.io"]
    paths = ["", "/path", "/path/to/resource", "/api/v1/data"]

    protocol = draw(st.sampled_from(protocols))
    domain = draw(st.sampled_from(domains))
    path = draw(st.sampled_from(paths))

    return f"{protocol}://{domain}{path}"


@composite
def valid_source_type(draw):
    """Generate valid source type strings."""
    source_types = ["rss", "twitter", "reddit", "custom", "hacker_news", "dev_to", "medium"]
    return draw(st.sampled_from(source_types))


@composite
def valid_datetime(draw):
    """Generate valid datetime objects."""
    return draw(st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2030, 12, 31)
    ))


@composite
def valid_tag_list(draw):
    """Generate valid tag lists."""
    return draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet=string.ascii_letters + string.digits + "-_"),
        min_size=0,
        max_size=10
    ))


@composite
def valid_media_url_list(draw):
    """Generate valid media URL lists."""
    return draw(st.lists(valid_url(), min_size=0, max_size=5))


@composite
def valid_metadata_dict(draw):
    """Generate valid metadata dictionaries."""
    keys = st.text(min_size=1, max_size=20, alphabet=string.ascii_letters + "_")
    values = st.one_of(
        st.text(max_size=100),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans()
    )
    return draw(st.dictionaries(keys, values, min_size=0, max_size=10))


@composite
def valid_content_item(draw):
    """Generate valid ContentItem instances."""
    return ContentItem(
        id=draw(valid_non_empty_string(min_size=1, max_size=50)),
        source=draw(valid_non_empty_string(min_size=1, max_size=50)),
        source_type=draw(valid_source_type()),
        title=draw(valid_non_empty_string(min_size=1, max_size=200)),
        content=draw(st.text(min_size=0, max_size=5000)),
        timestamp=draw(valid_datetime()),
        url=draw(valid_url()),
        author=draw(st.one_of(st.none(), valid_non_empty_string(max_size=100))),
        tags=draw(valid_tag_list()),
        media_urls=draw(valid_media_url_list()),
        metadata=draw(valid_metadata_dict())
    )


class TestContentItemSchemaCompliance:
    """
    Property-based tests for ContentItem schema compliance.

    **Feature: number-station, Property 32: ContentItem Schema Compliance**
    **Validates: Requirements 9.1, 9.3, 9.4**
    """

    @given(valid_content_item())
    @settings(max_examples=100)
    def test_content_item_has_required_metadata_fields(self, content_item: ContentItem):
        """
        Property: For any valid ContentItem, it must contain all required metadata fields.

        **Validates: Requirements 9.1, 9.3**
        - THE Number_Station SHALL define a standard Content_Item schema
        - THE Content_Item SHALL include metadata fields (source, timestamp, author, tags)
        """
        # Required metadata fields must be present and not None
        assert content_item.source is not None
        assert content_item.timestamp is not None
        assert content_item.tags is not None  # Can be empty list, but not None

        # Required metadata fields must not be empty strings (except author which can be None)
        assert content_item.source.strip() != ""
        assert isinstance(content_item.timestamp, datetime)
        assert isinstance(content_item.tags, list)

        # Author can be None or non-empty string
        if content_item.author is not None:
            assert isinstance(content_item.author, str)

    @given(valid_content_item())
    @settings(max_examples=100)
    def test_content_item_has_required_content_fields(self, content_item: ContentItem):
        """
        Property: For any valid ContentItem, it must contain all required content fields.

        **Validates: Requirements 9.1, 9.4**
        - THE Number_Station SHALL define a standard Content_Item schema
        - THE Content_Item SHALL include content fields (title, body, media URLs)
        """
        # Required content fields must be present and not None
        assert content_item.title is not None
        assert content_item.content is not None
        assert content_item.media_urls is not None

        # Required content fields must have correct types
        assert isinstance(content_item.title, str)
        assert isinstance(content_item.content, str)
        assert isinstance(content_item.media_urls, list)

        # Title must not be empty
        assert content_item.title.strip() != ""

        # Media URLs must be strings if present
        for url in content_item.media_urls:
            assert isinstance(url, str)

    @given(valid_content_item())
    @settings(max_examples=100)
    def test_content_item_preserves_source_url(self, content_item: ContentItem):
        """
        Property: For any valid ContentItem, the original source URL must be preserved.

        **Validates: Requirements 9.5**
        - THE Number_Station SHALL preserve original source URLs in Content_Items
        """
        # URL field must be present and not empty
        assert content_item.url is not None
        assert isinstance(content_item.url, str)
        assert content_item.url.strip() != ""

        # URL should be a valid URL format (basic check)
        assert content_item.url.startswith(("http://", "https://"))

    @given(valid_content_item())
    @settings(max_examples=100)
    def test_content_item_handles_missing_fields_gracefully(self, content_item: ContentItem):
        """
        Property: For any valid ContentItem, optional fields should have appropriate defaults.

        **Validates: Requirements 9.6**
        - THE Number_Station SHALL handle missing fields gracefully with default values
        """
        # Optional fields should have appropriate defaults when None
        if content_item.author is None:
            # This is acceptable - author can be None
            pass

        # Lists should never be None, should default to empty lists
        assert content_item.tags is not None
        assert isinstance(content_item.tags, list)

        assert content_item.media_urls is not None
        assert isinstance(content_item.media_urls, list)

        # Metadata should never be None, should default to empty dict
        assert content_item.metadata is not None
        assert isinstance(content_item.metadata, dict)

    @given(valid_content_item())
    @settings(max_examples=100)
    def test_content_item_serialization_roundtrip(self, content_item: ContentItem):
        """
        Property: For any valid ContentItem, serialization to dict and back should preserve all data.

        **Validates: Requirements 9.1, 9.3, 9.4**
        - Ensures schema compliance is maintained through serialization
        """
        # Convert to dict and back
        data_dict = content_item.to_dict()
        restored_item = ContentItem.from_dict(data_dict)

        # All fields should be preserved
        assert restored_item.id == content_item.id
        assert restored_item.source == content_item.source
        assert restored_item.source_type == content_item.source_type
        assert restored_item.title == content_item.title
        assert restored_item.content == content_item.content
        assert restored_item.author == content_item.author
        assert restored_item.timestamp == content_item.timestamp
        assert restored_item.url == content_item.url
        assert restored_item.tags == content_item.tags
        assert restored_item.media_urls == content_item.media_urls
        assert restored_item.metadata == content_item.metadata

    @given(
        id_val=st.one_of(st.just(""), st.just(None)),
        source=valid_non_empty_string(),
        source_type=valid_source_type(),
        title=valid_non_empty_string(),
        content=st.text(),
        timestamp=valid_datetime(),
        url=valid_url()
    )
    @settings(max_examples=50)
    def test_content_item_rejects_invalid_id(self, id_val, source, source_type, title, content, timestamp, url):
        """
        Property: ContentItem should reject invalid ID values.

        **Validates: Requirements 9.1**
        - Schema validation should prevent invalid data
        """
        with pytest.raises(ValueError, match="ContentItem id cannot be empty"):
            ContentItem(
                id=id_val,
                source=source,
                source_type=source_type,
                title=title,
                content=content,
                timestamp=timestamp,
                url=url
            )

    @given(
        id_val=valid_non_empty_string(),
        source=st.one_of(st.just(""), st.just(None)),
        source_type=valid_source_type(),
        title=valid_non_empty_string(),
        content=st.text(),
        timestamp=valid_datetime(),
        url=valid_url()
    )
    @settings(max_examples=50)
    def test_content_item_rejects_invalid_source(self, id_val, source, source_type, title, content, timestamp, url):
        """
        Property: ContentItem should reject invalid source values.

        **Validates: Requirements 9.1, 9.3**
        - Schema validation should prevent invalid metadata
        """
        with pytest.raises(ValueError, match="ContentItem source cannot be empty"):
            ContentItem(
                id=id_val,
                source=source,
                source_type=source_type,
                title=title,
                content=content,
                timestamp=timestamp,
                url=url
            )

    @given(
        id_val=valid_non_empty_string(),
        source=valid_non_empty_string(),
        source_type=st.one_of(st.just(""), st.just(None)),
        title=valid_non_empty_string(),
        content=st.text(),
        timestamp=valid_datetime(),
        url=valid_url()
    )
    @settings(max_examples=50)
    def test_content_item_rejects_invalid_source_type(self, id_val, source, source_type, title, content, timestamp, url):
        """
        Property: ContentItem should reject invalid source_type values.

        **Validates: Requirements 9.1, 9.3**
        - Schema validation should prevent invalid metadata
        """
        with pytest.raises(ValueError, match="ContentItem source_type cannot be empty"):
            ContentItem(
                id=id_val,
                source=source,
                source_type=source_type,
                title=title,
                content=content,
                timestamp=timestamp,
                url=url
            )

    @given(
        id_val=valid_non_empty_string(),
        source=valid_non_empty_string(),
        source_type=valid_source_type(),
        title=st.one_of(st.just(""), st.just(None)),
        content=st.text(),
        timestamp=valid_datetime(),
        url=valid_url()
    )
    @settings(max_examples=50)
    def test_content_item_rejects_invalid_title(self, id_val, source, source_type, title, content, timestamp, url):
        """
        Property: ContentItem should reject invalid title values.

        **Validates: Requirements 9.1, 9.4**
        - Schema validation should prevent invalid content fields
        """
        with pytest.raises(ValueError, match="ContentItem title cannot be empty"):
            ContentItem(
                id=id_val,
                source=source,
                source_type=source_type,
                title=title,
                content=content,
                timestamp=timestamp,
                url=url
            )

    @given(
        id_val=valid_non_empty_string(),
        source=valid_non_empty_string(),
        source_type=valid_source_type(),
        title=valid_non_empty_string(),
        content=st.text(),
        timestamp=valid_datetime(),
        url=st.one_of(st.just(""), st.just(None))
    )
    @settings(max_examples=50)
    def test_content_item_rejects_invalid_url(self, id_val, source, source_type, title, content, timestamp, url):
        """
        Property: ContentItem should reject invalid URL values.

        **Validates: Requirements 9.1, 9.5**
        - Schema validation should prevent invalid URLs
        """
        with pytest.raises(ValueError, match="ContentItem url cannot be empty"):
            ContentItem(
                id=id_val,
                source=source,
                source_type=source_type,
                title=title,
                content=content,
                timestamp=timestamp,
                url=url
            )

    @given(valid_content_item())
    @settings(max_examples=100)
    def test_content_item_normalizes_none_lists(self, content_item: ContentItem):
        """
        Property: ContentItem should normalize None values to empty lists for list fields.

        **Validates: Requirements 9.6**
        - THE Number_Station SHALL handle missing fields gracefully with default values
        """
        # Create a new item with None values for list fields
        item_data = content_item.to_dict()
        item_data['tags'] = None
        item_data['media_urls'] = None
        item_data['metadata'] = None

        # from_dict should handle None values gracefully
        restored = ContentItem.from_dict(item_data)

        assert restored.tags == []
        assert restored.media_urls == []
        assert restored.metadata == {}

    @given(valid_content_item())
    @settings(max_examples=100)
    def test_content_item_schema_completeness(self, content_item: ContentItem):
        """
        Property: For any valid ContentItem, all schema fields should be accessible and properly typed.

        **Validates: Requirements 9.1, 9.3, 9.4**
        - Complete schema compliance verification
        """
        # Verify all required fields exist and have correct types
        assert hasattr(content_item, 'id') and isinstance(content_item.id, str)
        assert hasattr(content_item, 'source') and isinstance(content_item.source, str)
        assert hasattr(content_item, 'source_type') and isinstance(content_item.source_type, str)
        assert hasattr(content_item, 'title') and isinstance(content_item.title, str)
        assert hasattr(content_item, 'content') and isinstance(content_item.content, str)
        assert hasattr(content_item, 'timestamp') and isinstance(content_item.timestamp, datetime)
        assert hasattr(content_item, 'url') and isinstance(content_item.url, str)

        # Verify optional fields exist and have correct types or are None
        assert hasattr(content_item, 'author')
        if content_item.author is not None:
            assert isinstance(content_item.author, str)

        assert hasattr(content_item, 'tags') and isinstance(content_item.tags, list)
        assert hasattr(content_item, 'media_urls') and isinstance(content_item.media_urls, list)
        assert hasattr(content_item, 'metadata') and isinstance(content_item.metadata, dict)

        # Verify list contents have correct types
        for tag in content_item.tags:
            assert isinstance(tag, str)

        for media_url in content_item.media_urls:
            assert isinstance(media_url, str)

        # Verify metadata values are JSON-serializable
        try:
            json.dumps(content_item.metadata)
        except (TypeError, ValueError):
            pytest.fail("Metadata should be JSON-serializable")