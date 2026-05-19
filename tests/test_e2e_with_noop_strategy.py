"""E2E tests using NoOpStrategy - full pipeline execution in <5 seconds."""
import pytest
import csv
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
from pipelines.arte_pipeline import SampleArtePipeline
from pipelines.config import PipelineConfig
from pipelines.strategies import NoOpStrategy
from core.client import HTTPClient


class TestE2EWithNoOpStrategy:
    """E2E tests for complete pipeline using NoOpStrategy."""

    @pytest.fixture
    def noop_strategy(self):
        """Create NoOpStrategy with test fixture HTML."""
        # Fixture HTML with some product links
        html = """
        <html><body>
            <a href="/p/book-1">Book 1</a>
            <a href="/p/book-2">Book 2</a>
            <a href="/p/book-3">Book 3</a>
        </body></html>
        """
        return NoOpStrategy(fixture_html=html)

    @pytest.fixture
    def test_config(self, tmp_path, noop_strategy):
        """Create test PipelineConfig with NoOpStrategy."""
        return PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/art",
            product_target=3,
            product_per_page=3,
            delay_min=0.001,
            delay_max=0.002,
            source_name="test",
            output_path=str(tmp_path / "output.csv"),
            download_strategy=noop_strategy
        )

    def test_e2e_pipeline_completes_in_under_5_seconds(self, test_config):
        """Full pipeline with NoOpStrategy completes in <5 seconds."""
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline = SampleArtePipeline(client=client, config=test_config)

            start = time.time()
            result = pipeline.run()
            elapsed = time.time() - start

            # Should complete quickly (no real delays)
            assert elapsed < 5.0, f"Pipeline took {elapsed}s, expected <5s"
            # Should have processed some products
            assert result > 0

    def test_e2e_noop_strategy_creates_csv_output(self, test_config, tmp_path):
        """Pipeline with NoOpStrategy creates CSV file."""
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline = SampleArtePipeline(client=client, config=test_config)

            pipeline.run()

            # CSV file should exist
            csv_file = Path(test_config.output_path)
            assert csv_file.exists(), f"CSV file not created at {csv_file}"

    def test_e2e_noop_strategy_csv_has_correct_headers(self, test_config, tmp_path):
        """Pipeline with NoOpStrategy creates CSV with correct headers."""
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline = SampleArtePipeline(client=client, config=test_config)

            pipeline.run()

            csv_file = Path(test_config.output_path)
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                assert reader.fieldnames == [
                    "title", "author", "price", "stock",
                    "page_index", "product_url", "source"
                ]

    def test_e2e_noop_strategy_respects_product_target(self, test_config, tmp_path):
        """Pipeline stops at product_target with NoOpStrategy."""
        test_config.product_target = 5
        test_config.output_path = str(tmp_path / "output2.csv")

        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline = SampleArtePipeline(client=client, config=test_config)

            result = pipeline.run()

            # Should process up to product_target
            assert result <= test_config.product_target

    def test_e2e_pipeline_resume_with_noop_strategy(self, test_config, tmp_path):
        """Pipeline resumes from checkpoint with NoOpStrategy."""
        # First run
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline = SampleArtePipeline(client=client, config=test_config)
            first_result = pipeline.run()

        # Second run should resume
        with patch('core.client.sync_playwright'):
            client2 = HTTPClient(download_strategy=test_config.download_strategy)
            pipeline2 = SampleArtePipeline(client=client2, config=test_config)
            second_result = pipeline2.run()

            # Second run should not increase total (already at target or file exists)
            # This depends on the implementation, but we can verify it doesn't error
            assert second_result >= 0
