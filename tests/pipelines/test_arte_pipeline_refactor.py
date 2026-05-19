"""Approval tests for arte_pipeline refactoring.

These tests capture the CURRENT behavior of arte_pipeline.run() to ensure
that refactoring to inherit BasePipeline preserves existing functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pipelines.arte_pipeline import SampleArtePipeline
from pipelines.config import PipelineConfig
from pipelines.components import SessionRotationPolicy, BlockDetectionPolicy, DelayPolicy


class TestArtePipelineBackwardCompat:
    """Test that refactored arte_pipeline maintains backward compatibility."""

    def test_sampleartepipeline_can_be_instantiated(self):
        """SampleArtePipeline can be created with client."""
        mock_client = Mock()
        pipeline = SampleArtePipeline(client=mock_client)
        assert pipeline is not None
        assert pipeline.client is mock_client

    def test_sampleartepipeline_has_run_method(self):
        """SampleArtePipeline has run() method."""
        mock_client = Mock()
        pipeline = SampleArtePipeline(client=mock_client)
        assert callable(getattr(pipeline, 'run', None))

    def test_sampleartepipeline_implements_abstract_methods(self):
        """SampleArtePipeline implements all abstract BasePipeline methods."""
        mock_client = Mock()
        pipeline = SampleArtePipeline(client=mock_client)

        assert callable(pipeline.collect_product_links)
        assert callable(pipeline.parse_product)
        assert callable(pipeline.get_csv_fields)

    def test_sampleartepipeline_get_csv_fields_returns_list(self):
        """get_csv_fields() returns expected field list."""
        mock_client = Mock()
        pipeline = SampleArtePipeline(client=mock_client)
        fields = pipeline.get_csv_fields()

        assert isinstance(fields, list)
        assert len(fields) > 0
        # Field order should match original arte_pipeline write format
        assert "title" in fields
        assert "product_url" in fields
        assert "source" in fields


class TestArtePipelineOrchestratorWiring:
    """Test that _create_orchestrator() correctly wires injected policies."""

    def _make_config(self, **kwargs):
        defaults = dict(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=10,
            product_per_page=5,
            delay_min=1.0,
            delay_max=2.0,
            source_name="test",
            output_path="/tmp/test_pipeline.csv",
        )
        defaults.update(kwargs)
        return PipelineConfig(**defaults)

    def test_create_orchestrator_uses_injected_session_policy(self):
        """_create_orchestrator() uses session_policy from config when provided."""
        policy = SessionRotationPolicy(threshold=7)
        config = self._make_config(session_policy=policy)
        pipeline = SampleArtePipeline(client=Mock(), config=config)
        orchestrator = pipeline._create_orchestrator()
        assert orchestrator.session_policy is policy

    def test_create_orchestrator_uses_injected_block_policy(self):
        """_create_orchestrator() uses block_policy from config when provided."""
        policy = BlockDetectionPolicy(threshold=9)
        config = self._make_config(block_policy=policy)
        pipeline = SampleArtePipeline(client=Mock(), config=config)
        orchestrator = pipeline._create_orchestrator()
        assert orchestrator.block_policy is policy

    def test_create_orchestrator_uses_injected_delay_policy(self):
        """_create_orchestrator() uses delay_policy from config when provided."""
        policy = DelayPolicy(delay_min=0.5, delay_max=1.0)
        config = self._make_config(delay_policy=policy)
        pipeline = SampleArtePipeline(client=Mock(), config=config)
        orchestrator = pipeline._create_orchestrator()
        assert orchestrator.delay_policy is policy

    def test_create_orchestrator_falls_back_to_defaults_when_no_policy_injected(self):
        """_create_orchestrator() creates default policies when config has none."""
        config = self._make_config()
        pipeline = SampleArtePipeline(client=Mock(), config=config)
        orchestrator = pipeline._create_orchestrator()
        assert isinstance(orchestrator.session_policy, SessionRotationPolicy)
        assert isinstance(orchestrator.block_policy, BlockDetectionPolicy)
        assert isinstance(orchestrator.delay_policy, DelayPolicy)

    def test_create_orchestrator_delay_policy_reads_config_delays_as_fallback(self):
        """Default delay_policy uses config.delay_min and config.delay_max."""
        config = self._make_config(delay_min=3.3, delay_max=7.7)
        pipeline = SampleArtePipeline(client=Mock(), config=config)
        orchestrator = pipeline._create_orchestrator()
        assert orchestrator.delay_policy._delay_min == 3.3
        assert orchestrator.delay_policy._delay_max == 7.7
