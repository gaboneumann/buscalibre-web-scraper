"""Approval tests for category_pipeline refactoring.

These tests capture the CURRENT behavior of category_pipeline.run() to ensure
that refactoring to inherit BasePipeline preserves existing functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pipelines.category_pipeline import CategoryPipeline
from pipelines.config import PipelineConfig
from pipelines.components import SessionRotationPolicy, BlockDetectionPolicy, DelayPolicy


class TestCategoryPipelineInterface:
    """Test that CategoryPipeline exposes the expected BasePipeline interface."""

    def test_category_pipeline_can_be_instantiated(self):
        """CategoryPipeline can be created with client."""
        mock_client = Mock()
        pipeline = CategoryPipeline(client=mock_client)
        assert pipeline is not None
        assert pipeline.client is mock_client

    def test_category_pipeline_has_run_method(self):
        """CategoryPipeline has run() method."""
        mock_client = Mock()
        pipeline = CategoryPipeline(client=mock_client)
        assert callable(getattr(pipeline, 'run', None))

    def test_category_pipeline_implements_abstract_methods(self):
        """CategoryPipeline implements all abstract BasePipeline methods."""
        mock_client = Mock()
        pipeline = CategoryPipeline(client=mock_client)

        assert callable(pipeline.collect_product_links)
        assert callable(pipeline.parse_product)
        assert callable(pipeline.get_csv_fields)

    def test_category_pipeline_get_csv_fields_returns_list(self):
        """get_csv_fields() returns expected field list."""
        mock_client = Mock()
        pipeline = CategoryPipeline(client=mock_client)
        fields = pipeline.get_csv_fields()

        assert isinstance(fields, list)
        assert len(fields) == 6
        assert "title" in fields
        assert "product_url" in fields
        assert "source" not in fields
        assert "category_url" not in fields


class TestCategoryPipelineCrawlerWiring:
    """Test that _create_crawler() correctly wires injected policies."""

    def _make_config(self, **kwargs):
        defaults = dict(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            delay_min=1.0,
            delay_max=2.0,
            output_path="/tmp/test_pipeline.csv",
        )
        defaults.update(kwargs)
        return PipelineConfig(**defaults)

    def test_create_crawler_uses_injected_session_policy(self):
        """_create_crawler() uses session_policy from config when provided."""
        policy = SessionRotationPolicy(threshold=7)
        config = self._make_config(session_policy=policy)
        pipeline = CategoryPipeline(client=Mock(), config=config)
        crawler = pipeline._create_crawler()
        assert crawler.session_policy is policy

    def test_create_crawler_uses_injected_block_policy(self):
        """_create_crawler() uses block_policy from config when provided."""
        policy = BlockDetectionPolicy(threshold=9)
        config = self._make_config(block_policy=policy)
        pipeline = CategoryPipeline(client=Mock(), config=config)
        crawler = pipeline._create_crawler()
        assert crawler.block_policy is policy

    def test_create_crawler_uses_injected_delay_policy(self):
        """_create_crawler() uses delay_policy from config when provided."""
        policy = DelayPolicy(delay_min=0.5, delay_max=1.0)
        config = self._make_config(delay_policy=policy)
        pipeline = CategoryPipeline(client=Mock(), config=config)
        crawler = pipeline._create_crawler()
        assert crawler.delay_policy is policy

    def test_create_crawler_falls_back_to_defaults_when_no_policy_injected(self):
        """_create_crawler() creates default policies when config has none."""
        config = self._make_config()
        pipeline = CategoryPipeline(client=Mock(), config=config)
        crawler = pipeline._create_crawler()
        assert isinstance(crawler.session_policy, SessionRotationPolicy)
        assert isinstance(crawler.block_policy, BlockDetectionPolicy)
        assert isinstance(crawler.delay_policy, DelayPolicy)

    def test_create_crawler_delay_policy_reads_config_delays_as_fallback(self):
        """Default delay_policy uses config.delay_min and config.delay_max."""
        config = self._make_config(delay_min=3.3, delay_max=7.7)
        pipeline = CategoryPipeline(client=Mock(), config=config)
        crawler = pipeline._create_crawler()
        assert crawler.delay_policy._delay_min == 3.3
        assert crawler.delay_policy._delay_max == 7.7
