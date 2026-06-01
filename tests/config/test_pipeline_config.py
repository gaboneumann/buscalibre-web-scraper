"""Tests for PipelineConfig dependency injection class."""
import pytest
from pipelines.config import PipelineConfig
from pipelines.components import SessionRotationPolicy, BlockDetectionPolicy, DelayPolicy
from config import settings


class TestPipelineConfigFromSettings:
    """Test PipelineConfig.from_settings() classmethod."""

    def test_from_settings_returns_pipelineconfig_instance(self):
        """from_settings() returns a PipelineConfig instance."""
        config = PipelineConfig.from_settings(settings)
        assert isinstance(config, PipelineConfig)


class TestPipelineConfigEdgeCases:
    """Test PipelineConfig edge cases and error handling."""

    def test_from_settings_download_strategy_is_none(self):
        """from_settings() produces config with download_strategy=None."""
        config = PipelineConfig.from_settings(settings)
        assert config.download_strategy is None
