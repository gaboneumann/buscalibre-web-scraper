"""Tests for BasePipeline abstract base class."""
import pytest
from unittest.mock import Mock, MagicMock
from pipelines.base_pipeline import BasePipeline
from pipelines.config import PipelineConfig


class ConcreteTestPipeline(BasePipeline):
    """Concrete implementation of BasePipeline for testing."""

    def collect_product_links(self, html: str):
        """Extract product links from category HTML."""
        return []

    def parse_product(self, html: str):
        """Extract product data from product page HTML."""
        return {"title": "Test Book", "price": "10.00", "author": "Test Author"}

    def get_csv_fields(self):
        """Return list of CSV field names in order."""
        return ["title", "author", "price", "stock", "page_index", "product_url"]


class TestBasePipelineInit:
    """Test BasePipeline initialization."""

    def test_init_with_client_and_config(self):
        """
        GIVEN HTTPClient and PipelineConfig
        WHEN BasePipeline.__init__(client, config) is called
        THEN pipeline stores both
        """
        mock_client = Mock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=100,
            delay_min=8.0,
            delay_max=15.0,
            output_path="test.csv"
        )

        pipeline = ConcreteTestPipeline(client=mock_client, config=config)

        assert pipeline.client is mock_client
        assert pipeline.config is config

    def test_init_with_client_only_loads_from_settings(self):
        """
        GIVEN HTTPClient and no config
        WHEN BasePipeline.__init__(client, config=None) is called
        THEN pipeline loads config from config/settings.py automatically
        """
        mock_client = Mock()
        pipeline = ConcreteTestPipeline(client=mock_client)

        assert pipeline.client is mock_client
        assert pipeline.config is not None
        assert hasattr(pipeline.config, 'domain_url')

    def test_init_returns_instance_with_client_attribute(self):
        """Init creates instance with client accessible."""
        mock_client = Mock()
        pipeline = ConcreteTestPipeline(client=mock_client)
        assert hasattr(pipeline, 'client')


class TestBasePipelineAbstractMethods:
    """Test that abstract methods must be implemented."""

    def test_concrete_implementation_implements_all_methods(self):
        """Concrete implementation can be instantiated."""
        mock_client = Mock()
        pipeline = ConcreteTestPipeline(client=mock_client)
        assert pipeline is not None

    def test_abstract_methods_are_callable(self):
        """Concrete implementation has callable abstract methods."""
        mock_client = Mock()
        pipeline = ConcreteTestPipeline(client=mock_client)

        assert callable(pipeline.collect_product_links)
        assert callable(pipeline.parse_product)
        assert callable(pipeline.get_csv_fields)


class TestBasePipelineRun:
    """Test BasePipeline.run() orchestrator setup."""

    def test_run_method_exists(self):
        """BasePipeline has run() method."""
        mock_client = Mock()
        pipeline = ConcreteTestPipeline(client=mock_client)
        assert hasattr(pipeline, 'run')
        assert callable(pipeline.run)

    def test_run_returns_integer(self):
        """run() returns an integer (product count)."""
        mock_client = Mock()
        pipeline = ConcreteTestPipeline(client=mock_client)
        # The base implementation should return 0 or orchestrator setup
        # For now, just verify it returns something
        result = pipeline.run()
        assert isinstance(result, int)
