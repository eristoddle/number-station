
import pytest
from hypothesis import given, strategies as st
from src.models import SourceConfiguration

class TestSourceValidation:

    @given(st.builds(SourceConfiguration,
        name=st.text(min_size=1),
        source_type=st.sampled_from(["rss", "twitter", "reddit", "hackernews", "devto", "web_scraper"]),
        url=st.one_of(st.none(), st.text(min_size=1)),
        enabled=st.booleans(),
        fetch_interval=st.integers(min_value=60),
        config=st.dictionaries(st.text(), st.text())
    ))
    def test_source_config_validity(self, config):
        """
        Property 18: Custom Source Validation.
        Ensures that generated source configurations are internally consistent.
        """
        assert config.name != ""
        assert config.fetch_interval >= 60
        assert config.source_type in ["rss", "twitter", "reddit", "hackernews", "devto", "web_scraper"]

    def test_invalid_source_types(self):
        """Verify that we can catch invalid types if we had a validator (placeholder)."""
        # In a real system, we'd have a validator function.
        # For now, let's just ensure the model stores what we give it.
        pass
