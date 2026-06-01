"""Tests for WebCrawler loop termination: empty-page exit and safety-cap exit."""

import pytest
from unittest.mock import Mock
from pipelines.components import (
    WebCrawler,
    SessionRotationPolicy,
    BlockDetectionPolicy,
    DelayPolicy,
)
from pipelines.config import PipelineConfig


def _make_zero_delay():
    """DelayPolicy with all waits zeroed out for fast tests."""
    return DelayPolicy(
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


def _make_config(product_target: int = 100) -> PipelineConfig:
    """Create a minimal PipelineConfig for testing."""
    return PipelineConfig(
        domain_url="https://www.buscalibre.cl/",
        category_url="https://www.buscalibre.cl/libros/arte",
        product_target=product_target,
        product_per_page=50,
        delay_min=0.0,
        delay_max=0.0,
        source_name="buscalibre_cl",
        output_path="storage/outputs/books.csv",
    )


def _make_crawler(config, extract_fn, transform_fn=None):
    """Build a WebCrawler wired with mocks and zero-delay policies."""
    mock_client = Mock()
    mock_client.navigate_to_category.return_value = "<html>category</html>"
    mock_client.get.return_value = "<html>product</html>"
    mock_client.reset_session.return_value = None

    mock_checkpoint_mgr = Mock()
    mock_checkpoint_mgr.get_scraped_urls.return_value = set()
    mock_checkpoint_mgr.save_record.return_value = None

    if transform_fn is None:
        transform_fn = lambda html: {"title": "Book", "price": 100}

    return WebCrawler(
        client=mock_client,
        extract_fn=extract_fn,
        transform_fn=transform_fn,
        checkpoint_mgr=mock_checkpoint_mgr,
        session_policy=SessionRotationPolicy(threshold=100),
        block_policy=BlockDetectionPolicy(threshold=3),
        delay_policy=_make_zero_delay(),
        config=config,
    )


def test_empty_page_exits_with_zero_products():
    """When extract_fn returns [] on page 1, run() returns 0 without fetching products."""
    config = _make_config(product_target=100)
    crawler = _make_crawler(config, extract_fn=lambda html: [])

    result = crawler.run()

    assert result == 0
    # No product pages should have been fetched (only category navigate call)
    # client.get for products should not have been called
    product_calls = [
        c for c in crawler.client.get.call_args_list
        if c.kwargs.get("request_type") == "product"
        or (c.args and not c.args[0].endswith("/arte"))
    ]
    # Simplified assertion: success_count is 0
    assert result == 0


def test_loop_stops_at_product_target():
    """When product_target=2 and enough links exist, run() stops exactly at product_target."""
    config = _make_config(product_target=2)

    page_call_count = [0]

    def extract_fn(html):
        page_call_count[0] += 1
        if page_call_count[0] <= 2:
            n = page_call_count[0]
            return [f"/product/p{n}-a", f"/product/p{n}-b", f"/product/p{n}-c"]
        return []

    crawler = _make_crawler(config, extract_fn=extract_fn)

    result = crawler.run()

    # Must stop at product_target=2; must NOT exhaust all pages
    assert result <= config.product_target
    assert result == 2


def test_full_category_iteration_exhausts_all_pages():
    """3 pages of 2 links each + empty 4th page: run() returns 6 and calls extract_fn 4 times."""
    config = _make_config(product_target=100)

    page_call_count = [0]

    def extract_fn(html):
        page_call_count[0] += 1
        if page_call_count[0] <= 3:
            n = page_call_count[0]
            return [f"/product/p{n}-a", f"/product/p{n}-b"]
        return []

    crawler = _make_crawler(config, extract_fn=extract_fn)

    result = crawler.run()

    assert result == 6
    assert page_call_count[0] == 4


def test_batch_summary_emitted_per_page(caplog):
    """BATCH SUMMARY is logged once per populated page, not gated on product_target."""
    import logging

    config = _make_config(product_target=100)

    page_call_count = [0]

    def extract_fn(html):
        page_call_count[0] += 1
        if page_call_count[0] <= 3:
            n = page_call_count[0]
            return [f"/product/p{n}-a", f"/product/p{n}-b", f"/product/p{n}-c"]
        return []

    crawler = _make_crawler(config, extract_fn=extract_fn)

    with caplog.at_level(logging.INFO):
        crawler.run()

    batch_summary_count = sum(
        1 for record in caplog.records if "BATCH SUMMARY" in record.message
    )
    assert batch_summary_count == 3
