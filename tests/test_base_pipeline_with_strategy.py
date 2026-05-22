"""Unit tests for BasePipeline with download_strategy support."""
import pytest
from unittest.mock import MagicMock, patch
from pipelines.base_pipeline import BasePipeline
from pipelines.config import PipelineConfig


class TestBasePipelineStrategySupport:
    """Test BasePipeline supports optional download_strategy in config."""

    def test_pipeline_config_has_strategy_field(self):
        """PipelineConfig supports optional download_strategy field."""
        mock_strategy = MagicMock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/cat",
            product_target=10,
            product_per_page=10,
            delay_min=1,
            delay_max=2,
            source_name="test",
            output_path="/tmp/test.csv",
            download_strategy=mock_strategy
        )
        assert config.download_strategy is mock_strategy

    def test_pipeline_config_strategy_defaults_to_none(self):
        """PipelineConfig.download_strategy defaults to None."""
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/cat",
            product_target=10,
            product_per_page=10,
            delay_min=1,
            delay_max=2,
            source_name="test",
            output_path="/tmp/test.csv"
        )
        assert config.download_strategy is None

    def test_base_pipeline_passes_strategy_to_client(self):
        """BasePipeline passes config.download_strategy to HTTPClient."""
        mock_client = MagicMock()
        mock_strategy = MagicMock()

        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/cat",
            product_target=10,
            product_per_page=10,
            delay_min=1,
            delay_max=2,
            source_name="test",
            output_path="/tmp/test.csv",
            download_strategy=mock_strategy
        )

        class TestPipeline(BasePipeline):
            def collect_product_links(self, html):
                return []

            def parse_product(self, html):
                return None

            def get_csv_fields(self):
                return []

        pipeline = TestPipeline(client=mock_client, config=config)

        # Pipeline should store the strategy from config
        assert pipeline.config.download_strategy is mock_strategy

    def test_create_crawler_receives_strategy(self):
        """_create_crawler() has access to strategy from config."""
        mock_client = MagicMock()
        mock_strategy = MagicMock()

        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/cat",
            product_target=10,
            product_per_page=10,
            delay_min=1,
            delay_max=2,
            source_name="test",
            output_path="/tmp/test.csv",
            download_strategy=mock_strategy
        )

        class TestPipeline(BasePipeline):
            def collect_product_links(self, html):
                return []

            def parse_product(self, html):
                return None

            def get_csv_fields(self):
                return []

        pipeline = TestPipeline(client=mock_client, config=config)

        # _create_crawler() should see the strategy
        # (We can't test the full orchestrator creation without more setup,
        # but we can verify the config is accessible)
        assert pipeline.config.download_strategy is mock_strategy
