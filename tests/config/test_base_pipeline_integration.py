"""Integration tests for BasePipeline with mocked HTTPClient."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pipelines.base_pipeline import BasePipeline
from pipelines.config import PipelineConfig


class ConcreteTestPipeline(BasePipeline):
    """Concrete implementation of BasePipeline for testing."""

    def collect_product_links(self, html: str):
        """Extract product links from HTML."""
        if html and "link1" in html:
            return ["/product/1", "/product/2"]
        return []

    def parse_product(self, html: str):
        """Extract product data from HTML."""
        if html and "title" in html:
            return {"title": "Test Book", "price": "19.99"}
        return None

    def get_csv_fields(self):
        """Return CSV field names."""
        return ["title", "price"]


class TestBasePipelineWithMockedClient:
    """Test BasePipeline orchestration with mocked HTTPClient."""

    def test_pipeline_delegates_to_mocked_client(self):
        """
        GIVEN mocked HTTPClient
        WHEN pipeline methods are called
        THEN they delegate to client correctly
        """
        mock_client = Mock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="test.csv"
        )

        pipeline = ConcreteTestPipeline(client=mock_client, config=config)

        # Pipeline should have access to client
        assert pipeline.client is mock_client

    def test_pipeline_collect_links_with_mocked_html(self):
        """collect_product_links() processes mocked HTML correctly."""
        mock_client = Mock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="test.csv"
        )

        pipeline = ConcreteTestPipeline(client=mock_client, config=config)

        # Test with HTML containing links
        html_with_links = "<html>link1</html>"
        links = pipeline.collect_product_links(html_with_links)
        assert links == ["/product/1", "/product/2"]

        # Test with HTML without links
        html_without_links = "<html>no links</html>"
        links = pipeline.collect_product_links(html_without_links)
        assert links == []

    def test_pipeline_parse_product_with_mocked_html(self):
        """parse_product() processes mocked HTML correctly."""
        mock_client = Mock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="test.csv"
        )

        pipeline = ConcreteTestPipeline(client=mock_client, config=config)

        # Test with HTML containing product data
        html_with_data = "<html>title: Test Book</html>"
        data = pipeline.parse_product(html_with_data)
        assert data == {"title": "Test Book", "price": "19.99"}

        # Test with HTML without product data
        html_without_data = "<html>no data</html>"
        data = pipeline.parse_product(html_without_data)
        assert data is None

    def test_pipeline_get_csv_fields_returns_ordered_list(self):
        """get_csv_fields() returns fields in consistent order."""
        mock_client = Mock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="test.csv"
        )

        pipeline = ConcreteTestPipeline(client=mock_client, config=config)
        fields = pipeline.get_csv_fields()

        assert fields == ["title", "price"]
        assert isinstance(fields, list)
        assert len(fields) == 2

    def test_pipeline_config_accessible_to_concrete_implementation(self):
        """Concrete pipeline can access config fields."""
        mock_client = Mock()
        config = PipelineConfig(
            domain_url="https://api.example.com",
            category_url="https://api.example.com/items",
            product_target=500,
            product_per_page=100,
            delay_min=5.0,
            delay_max=10.0,
            source_name="api_source",
            output_path="api_output.csv"
        )

        pipeline = ConcreteTestPipeline(client=mock_client, config=config)

        assert pipeline.config.domain_url == "https://api.example.com"
        assert pipeline.config.product_target == 500
        assert pipeline.config.delay_min == 5.0
        assert pipeline.config.source_name == "api_source"

    def test_pipeline_run_returns_zero_from_base_implementation(self):
        """BasePipeline.run() returns 0 (stub for orchestrator setup)."""
        mock_client = Mock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="test.csv"
        )

        pipeline = ConcreteTestPipeline(client=mock_client, config=config)
        result = pipeline.run()

        # Base implementation returns 0
        assert isinstance(result, int)
        assert result == 0

    def test_pipeline_can_be_instantiated_without_config(self):
        """Pipeline can be instantiated with client only (config loads from settings)."""
        mock_client = Mock()
        pipeline = ConcreteTestPipeline(client=mock_client)

        assert pipeline.client is mock_client
        assert pipeline.config is not None
        assert hasattr(pipeline.config, "domain_url")
        assert hasattr(pipeline.config, "product_target")


class TestBasePipelineAbstractEnforcement:
    """Test that BasePipeline correctly enforces abstract methods."""

    def test_cannot_instantiate_basepipeline_directly(self):
        """Cannot instantiate BasePipeline without implementing abstract methods."""
        mock_client = Mock()
        with pytest.raises(TypeError):
            BasePipeline(client=mock_client)

    def test_missing_one_abstract_method_prevents_instantiation(self):
        """Missing even one abstract method prevents instantiation."""
        mock_client = Mock()

        class IncompleteTestPipeline(BasePipeline):
            def collect_product_links(self, html: str):
                return []

            def parse_product(self, html: str):
                return None

            # Missing get_csv_fields() implementation

        with pytest.raises(TypeError):
            IncompleteTestPipeline(client=mock_client)

    def test_all_abstract_methods_required(self):
        """All three abstract methods are required."""
        mock_client = Mock()

        # Valid: all three methods implemented
        class ValidPipeline(BasePipeline):
            def collect_product_links(self, html: str):
                return []

            def parse_product(self, html: str):
                return None

            def get_csv_fields(self):
                return []

        pipeline = ValidPipeline(client=mock_client)
        assert pipeline is not None
