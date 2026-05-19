"""Tests for PipelineConfig dependency injection class."""
import pytest
from pipelines.config import PipelineConfig
from pipelines.components import SessionRotationPolicy, BlockDetectionPolicy, DelayPolicy
from config import settings


class TestPipelineConfigFromSettings:
    """Test PipelineConfig.from_settings() classmethod."""

    def test_from_settings_wraps_global_settings(self):
        """
        GIVEN settings module with DOMAIN_URL, CATEGORY_URL, PRODUCT_TARGET, etc.
        WHEN PipelineConfig.from_settings(settings) is called
        THEN config object has all values from settings
        """
        config = PipelineConfig.from_settings(settings)

        assert config.domain_url == settings.DOMAIN_URL
        assert config.category_url == settings.CATEGORY_URL
        assert config.product_target == settings.PRODUCT_TARGET
        assert config.product_per_page == settings.PRODUCT_PER_PAGE
        assert config.delay_min == settings.DELAY_MIN
        assert config.delay_max == settings.DELAY_MAX
        assert config.source_name == settings.SOURCE_NAME
        assert config.output_path == settings.OUTPUT_PATH

    def test_from_settings_returns_pipelineconfig_instance(self):
        """from_settings() returns a PipelineConfig instance."""
        config = PipelineConfig.from_settings(settings)
        assert isinstance(config, PipelineConfig)


class TestPipelineConfigExplicitInit:
    """Test PipelineConfig direct instantiation."""

    def test_explicit_init_with_all_fields(self):
        """
        GIVEN explicit values for all fields
        WHEN PipelineConfig(domain_url=..., category_url=..., ...) is called
        THEN config is created with all values set
        """
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=50,
            product_per_page=25,
            delay_min=5.0,
            delay_max=10.0,
            source_name="test_source",
            output_path="test_output.csv"
        )

        assert config.domain_url == "https://example.com"
        assert config.category_url == "https://example.com/books"
        assert config.product_target == 50
        assert config.product_per_page == 25
        assert config.delay_min == 5.0
        assert config.delay_max == 10.0
        assert config.source_name == "test_source"
        assert config.output_path == "test_output.csv"

    def test_explicit_init_no_global_imports(self):
        """Explicit init doesn't import global settings."""
        # If this test passes, it means the config doesn't depend on globals
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=100,
            product_per_page=50,
            delay_min=8.0,
            delay_max=15.0,
            source_name="source",
            output_path="output.csv"
        )
        assert config is not None


class TestPipelineConfigFromDict:
    """Test PipelineConfig.from_dict() classmethod."""

    def test_from_dict_with_all_fields(self):
        """
        GIVEN dict with all fields
        WHEN PipelineConfig.from_dict(dict) is called
        THEN config is created with all values
        """
        data = {
            "domain_url": "https://example.com",
            "category_url": "https://example.com/books",
            "product_target": 75,
            "product_per_page": 30,
            "delay_min": 6.0,
            "delay_max": 12.0,
            "source_name": "dict_source",
            "output_path": "dict_output.csv"
        }
        config = PipelineConfig.from_dict(data)

        assert config.domain_url == "https://example.com"
        assert config.category_url == "https://example.com/books"
        assert config.product_target == 75
        assert config.product_per_page == 30
        assert config.delay_min == 6.0
        assert config.delay_max == 12.0
        assert config.source_name == "dict_source"
        assert config.output_path == "dict_output.csv"

    def test_from_dict_different_values(self):
        """Triangulation: from_dict with different domain and targets."""
        data = {
            "domain_url": "https://other-site.com",
            "category_url": "https://other-site.com/items",
            "product_target": 200,
            "product_per_page": 100,
            "delay_min": 3.0,
            "delay_max": 8.0,
            "source_name": "other_source",
            "output_path": "other_output.csv"
        }
        config = PipelineConfig.from_dict(data)

        assert config.domain_url == "https://other-site.com"
        assert config.product_target == 200
        assert config.product_per_page == 100
        assert config.delay_min == 3.0
        assert config.delay_max == 8.0


class TestPipelineConfigEdgeCases:
    """Test PipelineConfig edge cases and error handling."""

    def test_from_dict_missing_required_field(self):
        """from_dict() raises KeyError if required field is missing."""
        incomplete_data = {
            "domain_url": "https://example.com",
            "category_url": "https://example.com/books",
            # Missing product_target
            "product_per_page": 50,
            "delay_min": 8.0,
            "delay_max": 15.0,
            "source_name": "test",
            "output_path": "test.csv"
        }
        with pytest.raises(KeyError):
            PipelineConfig.from_dict(incomplete_data)

    def test_from_dict_extra_fields_ignored(self):
        """from_dict() ignores extra fields in dict."""
        data = {
            "domain_url": "https://example.com",
            "category_url": "https://example.com/books",
            "product_target": 50,
            "product_per_page": 25,
            "delay_min": 5.0,
            "delay_max": 10.0,
            "source_name": "test_source",
            "output_path": "test_output.csv",
            "extra_field": "ignored",
            "another_field": 12345
        }
        config = PipelineConfig.from_dict(data)
        assert config.domain_url == "https://example.com"
        # Should not have extra_field as attribute
        assert not hasattr(config, "extra_field")

    def test_explicit_init_preserves_zero_values(self):
        """Init preserves zero and boundary values."""
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=0,
            product_per_page=1,
            delay_min=0.0,
            delay_max=1.0,
            source_name="",
            output_path=""
        )
        assert config.product_target == 0
        assert config.delay_min == 0.0
        assert config.source_name == ""

    def test_explicit_init_preserves_large_values(self):
        """Init preserves large numeric values."""
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=1000000,
            product_per_page=9999,
            delay_min=999.0,
            delay_max=9999.0,
            source_name="large_source",
            output_path="/very/long/path/to/output.csv"
        )
        assert config.product_target == 1000000
        assert config.delay_max == 9999.0

    def test_explicit_init_with_session_policy(self):
        """PipelineConfig stores injected SessionRotationPolicy."""
        policy = SessionRotationPolicy(threshold=3)
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="test.csv",
            session_policy=policy,
        )
        assert config.session_policy is policy

    def test_explicit_init_with_block_policy(self):
        """PipelineConfig stores injected BlockDetectionPolicy."""
        policy = BlockDetectionPolicy(threshold=5)
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="test.csv",
            block_policy=policy,
        )
        assert config.block_policy is policy

    def test_explicit_init_with_delay_policy(self):
        """PipelineConfig stores injected DelayPolicy."""
        policy = DelayPolicy(delay_min=1.0, delay_max=2.0)
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="test.csv",
            delay_policy=policy,
        )
        assert config.delay_policy is policy

    def test_from_dict_without_policies_defaults_to_none(self):
        """from_dict() sets policy fields to None when absent from dict."""
        data = {
            "domain_url": "https://example.com",
            "category_url": "https://example.com/books",
            "product_target": 10,
            "product_per_page": 5,
            "delay_min": 1.0,
            "delay_max": 2.0,
            "source_name": "test",
            "output_path": "test.csv",
        }
        config = PipelineConfig.from_dict(data)
        assert config.session_policy is None
        assert config.block_policy is None
        assert config.delay_policy is None

    def test_from_settings_download_strategy_is_none(self):
        """from_settings() produces config with download_strategy=None."""
        config = PipelineConfig.from_settings(settings)
        assert config.download_strategy is None

    def test_from_dict_with_integer_delays(self):
        """from_dict() accepts integer delays (converted to float)."""
        data = {
            "domain_url": "https://example.com",
            "category_url": "https://example.com/books",
            "product_target": 100,
            "product_per_page": 50,
            "delay_min": 5,  # Integer, not float
            "delay_max": 10,
            "source_name": "test",
            "output_path": "test.csv"
        }
        config = PipelineConfig.from_dict(data)
        assert config.delay_min == 5
        assert config.delay_max == 10
