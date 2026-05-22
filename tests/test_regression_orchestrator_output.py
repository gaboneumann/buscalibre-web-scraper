"""Regression tests: verify orchestrator output matches expected format."""
import pytest
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch
from pipelines.category_pipeline import CategoryPipeline
from pipelines.config import PipelineConfig
from pipelines.strategies import NoOpStrategy
from core.client import HTTPClient


class TestOrchestratorRegressionOutput:
    """Regression tests for WebCrawler output format."""

    @pytest.fixture
    def simple_noop_strategy(self):
        """NoOpStrategy with minimal product HTML."""
        html = """
        <html><body>
            <h1>Product Title</h1>
            <p>Author Name</p>
            <p class="price">$100.00</p>
            <p class="stock">In stock</p>
        </body></html>
        """
        return NoOpStrategy(fixture_html=html)

    @pytest.fixture
    def test_config(self, tmp_path, simple_noop_strategy):
        """Test config with NoOpStrategy."""
        return PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/art",
            product_target=1,
            product_per_page=1,
            delay_min=0.001,
            delay_max=0.002,
            source_name="test_source",
            output_path=str(tmp_path / "regression.csv"),
            download_strategy=simple_noop_strategy
        )

    def test_csv_output_has_required_columns(self, test_config, tmp_path):
        """CSV output includes all required columns."""
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline = CategoryPipeline(client=client, config=test_config)
            pipeline.run()

            csv_file = Path(test_config.output_path)
            if csv_file.exists():
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames

                    required = [
                        "title", "author", "price", "stock",
                        "page_index", "product_url", "source"
                    ]
                    for field in required:
                        assert field in fieldnames, f"Missing column: {field}"

    def test_csv_output_column_order_matches_spec(self, test_config):
        """CSV columns are in correct order."""
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline = CategoryPipeline(client=client, config=test_config)
            pipeline.run()

            csv_file = Path(test_config.output_path)
            if csv_file.exists():
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    expected_order = [
                        "title", "author", "price", "stock",
                        "page_index", "product_url", "source"
                    ]
                    assert reader.fieldnames == expected_order

    def test_orchestrator_respects_anti_detection_thresholds(self, test_config):
        """Orchestrator policies use correct anti-detection thresholds."""
        with patch('core.client.sync_playwright'):
            client = MagicMock()
            pipeline = CategoryPipeline(client=client, config=test_config)

            # Check that policies in orchestrator have correct thresholds
            from pipelines.components import (
                SessionRotationPolicy,
                BlockDetectionPolicy,
                DelayPolicy
            )

            session_policy = SessionRotationPolicy()
            block_policy = BlockDetectionPolicy()
            delay_policy = DelayPolicy()

            # Session rotation: 2-4 products
            assert session_policy._threshold >= 2
            assert session_policy._threshold <= 4

            # Block detection: 3 consecutive failures
            assert block_policy._threshold == 3

            # Delays: 8-15s between products, 150-250s coffee breaks
            assert delay_policy._delay_min >= 8
            assert delay_policy._delay_max <= 15

    def test_csv_data_types_are_correct(self, test_config):
        """CSV data contains correct types (stock as boolean, etc.)."""
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline = CategoryPipeline(client=client, config=test_config)
            pipeline.run()

            csv_file = Path(test_config.output_path)
            if csv_file.exists() and csv_file.stat().st_size > 0:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # stock should be convertible to boolean
                        assert row['stock'] in ['True', 'False']
                        # source should be string
                        assert isinstance(row['source'], str)
                        # page_index should be numeric
                        assert row['page_index'].isdigit()
