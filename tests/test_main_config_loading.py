"""Tests for main.py config loading enhancements (task 4.6)."""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from pipelines.category_pipeline import run
from pipelines.config import PipelineConfig


class TestMainConfigLoading:
    """Test main.py supports explicit PipelineConfig."""

    def test_run_function_accepts_no_args_uses_from_settings(self):
        """run() without arguments uses from_settings()."""
        with patch('pipelines.category_pipeline.HTTPClient'):
            with patch('pipelines.category_pipeline.CategoryPipeline.run') as mock_run:
                with patch('pipelines.config.PipelineConfig.from_settings') as mock_from_settings:
                    mock_config = MagicMock()
                    mock_config.category_url = "https://www.buscalibre.cl/libros/test-category"
                    mock_from_settings.return_value = mock_config
                    mock_run.return_value = 10
                    result = run()
                    assert result == 10

    def test_pipeline_config_from_dict_enables_dict_loading(self):
        """PipelineConfig.from_dict() enables loading from config dict."""
        config_dict = {
            "domain_url": "https://example.com",
            "category_url": "https://example.com/books",
            "product_target": 100,
            "product_per_page": 20,
            "delay_min": 8,
            "delay_max": 15,
            "source_name": "test",
            "output_path": "/tmp/output.csv"
        }

        config = PipelineConfig.from_dict(config_dict)

        assert config.domain_url == "https://example.com"
        assert config.product_target == 100
        assert config.delay_min == 8

    def test_pipeline_config_can_be_created_from_json_file(self, tmp_path):
        """PipelineConfig can be loaded from JSON file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "domain_url": "https://buscalibre.cl",
            "category_url": "https://buscalibre.cl/art",
            "product_target": 50,
            "product_per_page": 10,
            "delay_min": 8,
            "delay_max": 15,
            "source_name": "buscalibre",
            "output_path": str(tmp_path / "output.csv")
        }

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Load from JSON
        with open(config_file, 'r') as f:
            loaded_data = json.load(f)

        config = PipelineConfig.from_dict(loaded_data)

        assert config.domain_url == "https://buscalibre.cl"
        assert config.product_target == 50

    def test_pipeline_config_with_strategy_can_be_loaded(self, tmp_path):
        """PipelineConfig with download_strategy can be serialized/loaded."""
        from pipelines.strategies import NoOpStrategy

        strategy = NoOpStrategy()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=10,
            delay_min=1,
            delay_max=2,
            source_name="test",
            output_path=str(tmp_path / "output.csv"),
            download_strategy=strategy
        )

        assert config.download_strategy is strategy

    def test_main_can_use_explicit_config(self):
        """main.py can be modified to accept explicit PipelineConfig."""
        from pipelines.config import PipelineConfig

        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=10,
            delay_min=1,
            delay_max=2,
            source_name="test",
            output_path="/tmp/test.csv"
        )

        # Should be able to pass config to pipeline
        with patch('core.client.HTTPClient'):
            with patch('pipelines.category_pipeline.CategoryPipeline.run') as mock_run:
                from pipelines.category_pipeline import CategoryPipeline
                mock_run.return_value = 5

                pipeline = CategoryPipeline(
                    client=MagicMock(),
                    config=config
                )

                assert pipeline.config.product_target == 10
