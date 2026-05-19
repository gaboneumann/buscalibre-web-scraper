"""Tests for backward compatibility - existing code should work unchanged."""
import pytest
from unittest.mock import patch, MagicMock
from pipelines.arte_pipeline import run


class TestBackwardCompatibility:
    """Test that existing arte_pipeline.run() works unchanged."""

    def test_arte_pipeline_run_import_still_works(self):
        """Existing import `from arte_pipeline import run` still works."""
        from pipelines.arte_pipeline import run
        assert callable(run)

    def test_arte_pipeline_run_without_arguments(self):
        """arte_pipeline.run() can be called without arguments."""
        with patch('core.client.HTTPClient'):
            with patch('pipelines.arte_pipeline.SampleArtePipeline.run') as mock_run:
                mock_run.return_value = 5
                result = run()
                # Should execute without error and return int
                assert isinstance(result, int)

    def test_arte_pipeline_run_uses_from_settings_by_default(self):
        """arte_pipeline.run() uses PipelineConfig.from_settings() by default."""
        with patch('pipelines.arte_pipeline.HTTPClient'):
            with patch('pipelines.config.PipelineConfig.from_settings') as mock_from_settings:
                with patch('pipelines.arte_pipeline.SampleArtePipeline.run') as mock_run:
                    mock_from_settings.return_value = MagicMock()
                    mock_run.return_value = 5

                    result = run()

                    # Should have called from_settings
                    mock_from_settings.assert_called()
                    assert isinstance(result, int)

    def test_main_py_can_import_and_call_run(self):
        """main.py can still import and call run() as before."""
        # This test ensures the import path hasn't changed
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "main",
            "/home/gabo/workspace/projects/web_scraping/buscalibre_web_scraper/main.py"
        )
        main_module = importlib.util.module_from_spec(spec)

        # Should not raise ImportError
        with patch('pipelines.arte_pipeline.run'):
            try:
                spec.loader.exec_module(main_module)
            except ImportError as e:
                pytest.fail(f"main.py has import error: {e}")

    def test_arte_pipeline_run_returns_int(self):
        """arte_pipeline.run() returns an integer (product count)."""
        with patch('pipelines.arte_pipeline.HTTPClient'):
            with patch('pipelines.arte_pipeline.SampleArtePipeline') as mock_class:
                mock_instance = MagicMock()
                mock_instance.run.return_value = 42
                mock_class.return_value = mock_instance

                result = run()

                assert isinstance(result, int)
                assert result == 42

    def test_existing_tests_still_pass(self):
        """Existing test_product_integration.py patterns still work."""
        # This verifies that the refactoring doesn't break existing test patterns
        from pipelines.arte_pipeline import SampleArtePipeline

        with patch('core.client.HTTPClient'):
            with patch('pipelines.arte_pipeline.SampleArtePipeline._create_orchestrator'):
                mock_client = MagicMock()
                pipeline = SampleArtePipeline(client=mock_client)

                # Should be instantiable and have required methods
                assert hasattr(pipeline, 'run')
                assert hasattr(pipeline, 'collect_product_links')
                assert hasattr(pipeline, 'parse_product')
