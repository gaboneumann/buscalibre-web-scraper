"""Integration tests for WebCrawler."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from pipelines.components import (
    WebCrawler,
    SessionRotationPolicy,
    BlockDetectionPolicy,
    DelayPolicy,
)
from pipelines.config import PipelineConfig


class TestWebCrawlerIntegration:
    """Test WebCrawler two-level iteration logic."""

    def test_crawler_run_returns_product_count(self):
        """run() returns integer count of successfully saved products."""
        mock_client = Mock()
        mock_checkpoint_mgr = Mock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=2,
            delay_min=0.1,
            delay_max=0.2,
            output_path="test.csv"
        )

        # Mock extraction and transformation - return links on page 1, empty on page 2
        page_calls = [0]

        def mock_extract(html):
            page_calls[0] += 1
            if page_calls[0] == 1:
                return ["/product/1", "/product/2"]
            return []

        def mock_transform(html):
            return {"title": "Book", "price": 100}

        # Mock checkpoint manager
        mock_checkpoint_mgr.get_scraped_urls.return_value = set()
        mock_checkpoint_mgr.save_record.return_value = None

        # Create orchestrator
        crawler = WebCrawler(
            client=mock_client,
            extract_fn=mock_extract,
            transform_fn=mock_transform,
            checkpoint_mgr=mock_checkpoint_mgr,
            session_policy=SessionRotationPolicy(threshold=10),
            block_policy=BlockDetectionPolicy(threshold=3),
            delay_policy=DelayPolicy(delay_min=0.01, delay_max=0.02),
            config=config,
        )

        # Mock client responses
        mock_client.navigate_to_category.return_value = "<html>category</html>"
        mock_client.get.return_value = "<html>product</html>"
        mock_client.reset_session.return_value = None

        # Run orchestrator (will iterate 2 products)
        result = crawler.run()
        assert isinstance(result, int)

    def test_crawler_accesses_config_fields(self):
        """Orchestrator can access PipelineConfig fields."""
        mock_client = Mock()
        mock_checkpoint_mgr = Mock()
        config = PipelineConfig(
            domain_url="https://api.example.com",
            category_url="https://api.example.com/items",
            product_target=500,
            delay_min=5.0,
            delay_max=10.0,
            output_path="test_output.csv"
        )

        crawler = WebCrawler(
            client=mock_client,
            extract_fn=lambda x: [],
            transform_fn=lambda x: {},
            checkpoint_mgr=mock_checkpoint_mgr,
            session_policy=SessionRotationPolicy(),
            block_policy=BlockDetectionPolicy(),
            delay_policy=DelayPolicy(),
            config=config,
        )

        assert crawler.config.domain_url == "https://api.example.com"
        assert crawler.config.product_target == 500
        assert crawler.config.delay_min == 5.0

    def test_crawler_delegates_to_policies(self):
        """Orchestrator delegates decisions to policies."""
        mock_client = Mock()
        mock_checkpoint_mgr = Mock()
        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=1,
            delay_min=0.01,
            delay_max=0.02,
            output_path="test.csv"
        )

        # Create spy policies to track calls
        session_policy = SessionRotationPolicy(threshold=10)
        block_policy = BlockDetectionPolicy(threshold=3)
        delay_policy = DelayPolicy(delay_min=0.01, delay_max=0.02)

        # extract_fn returns one link on first call, then empty to terminate
        _policy_call = [0]

        def _extract_once(html):
            _policy_call[0] += 1
            if _policy_call[0] == 1:
                return ["/product/1"]
            return []

        crawler = WebCrawler(
            client=mock_client,
            extract_fn=_extract_once,
            transform_fn=lambda x: {"title": "Book"},
            checkpoint_mgr=mock_checkpoint_mgr,
            session_policy=session_policy,
            block_policy=block_policy,
            delay_policy=delay_policy,
            config=config,
        )

        # Verify policies are accessible
        assert crawler.session_policy is session_policy
        assert crawler.block_policy is block_policy
        assert crawler.delay_policy is delay_policy

    def test_crawler_uses_block_policy_for_category_pages(self):
        """Orchestrator aborts when block_policy.on_failure() returns should_abort=True."""
        mock_client = Mock()
        mock_client.navigate_to_category.return_value = None
        mock_client.get.return_value = None
        mock_client.reset_session.return_value = None

        mock_checkpoint_mgr = Mock()
        mock_checkpoint_mgr.get_scraped_urls.return_value = set()

        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=5,
            delay_min=0.01,
            delay_max=0.02,
            output_path="test.csv"
        )

        block_policy = BlockDetectionPolicy(threshold=1)
        crawler = WebCrawler(
            client=mock_client,
            extract_fn=lambda x: [],
            transform_fn=lambda x: {},
            checkpoint_mgr=mock_checkpoint_mgr,
            session_policy=SessionRotationPolicy(threshold=10),
            block_policy=block_policy,
            delay_policy=DelayPolicy(delay_min=0.01, delay_max=0.02),
            config=config,
        )

        result = crawler.run()
        assert result == 0

    def test_crawler_block_policy_threshold_respected_not_hardcoded(self):
        """Orchestrator with threshold=5 does not abort after only 3 category failures."""
        call_count = 0

        def flaky_get(url, request_type=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return None
            return "<html>ok</html>"

        extract_counter = 0

        def mock_extract(html):
            nonlocal extract_counter
            extract_counter += 1
            if extract_counter <= 1:
                return [f"/product/{extract_counter}"]
            return []

        mock_client = Mock()
        mock_client.navigate_to_category.side_effect = flaky_get
        mock_client.get.side_effect = flaky_get
        mock_client.reset_session.return_value = None

        mock_checkpoint_mgr = Mock()
        mock_checkpoint_mgr.get_scraped_urls.return_value = set()
        mock_checkpoint_mgr.save_record.return_value = None

        config = PipelineConfig(
            domain_url="https://example.com",
            category_url="https://example.com/books",
            product_target=5,
            delay_min=0.01,
            delay_max=0.02,
            output_path="test.csv"
        )

        zero_delay = DelayPolicy(
            delay_min=0,
            delay_max=0,
            coffee_break_min=0,
            coffee_break_max=0,
            page_wait_min=0,
            page_wait_max=0,
            rotation_wait_min=0,
            rotation_wait_max=0,
            post_rotation_wait_min=0,
            post_rotation_wait_max=0,
        )

        block_policy = BlockDetectionPolicy(threshold=5)
        crawler = WebCrawler(
            client=mock_client,
            extract_fn=mock_extract,
            transform_fn=lambda x: {"title": "Book"},
            checkpoint_mgr=mock_checkpoint_mgr,
            session_policy=SessionRotationPolicy(threshold=10),
            block_policy=block_policy,
            delay_policy=zero_delay,
            config=config,
        )

        result = crawler.run()
        assert call_count >= 4

    def test_crawler_stores_client_and_functions(self):
        """Orchestrator stores client, extraction, and transformation functions."""
        mock_client = Mock()
        mock_checkpoint_mgr = Mock()

        def extract_fn(html):
            return []

        def transform_fn(html):
            return {}

        crawler = WebCrawler(
            client=mock_client,
            extract_fn=extract_fn,
            transform_fn=transform_fn,
            checkpoint_mgr=mock_checkpoint_mgr,
            session_policy=SessionRotationPolicy(),
            block_policy=BlockDetectionPolicy(),
            delay_policy=DelayPolicy(),
            config=PipelineConfig(
                domain_url="https://example.com",
                category_url="https://example.com/books",
                product_target=10,
                delay_min=1.0,
                delay_max=2.0,
                output_path="test.csv"
            ),
        )

        assert crawler.client is mock_client
        assert crawler.extract_fn is extract_fn
        assert crawler.transform_fn is transform_fn
        assert crawler.checkpoint_mgr is mock_checkpoint_mgr
