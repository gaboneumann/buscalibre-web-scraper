"""Unit tests for DownloadStrategy and implementations."""
import pytest
from pipelines.strategies import DownloadStrategy, AntiDetectionStrategy, NoOpStrategy
from unittest.mock import MagicMock, patch


class TestDownloadStrategyInterface:
    """Test DownloadStrategy abstract interface."""

    def test_download_strategy_is_abstract(self):
        """DownloadStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DownloadStrategy()

    def test_download_strategy_requires_download_method(self):
        """Subclasses must implement download(url, request_type) method."""
        class IncompleteStrategy(DownloadStrategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()


class TestAntiDetectionStrategy:
    """Test AntiDetectionStrategy wraps HTTPClient with anti-detection."""

    def test_init_stores_client(self):
        """AntiDetectionStrategy stores HTTPClient instance."""
        mock_client = MagicMock()
        strategy = AntiDetectionStrategy(mock_client)
        assert strategy._client is mock_client

    def test_download_delegates_to_client_get(self):
        """download() calls client.get() with same parameters."""
        mock_client = MagicMock()
        mock_client.get.return_value = "<html>content</html>"

        strategy = AntiDetectionStrategy(mock_client)
        result = strategy.download("https://example.com/page", "product")

        mock_client.get.assert_called_once_with("https://example.com/page", request_type="product")
        assert result == "<html>content</html>"

    def test_download_returns_none_on_block(self):
        """download() returns None when client.get() returns None."""
        mock_client = MagicMock()
        mock_client.get.return_value = None

        strategy = AntiDetectionStrategy(mock_client)
        result = strategy.download("https://example.com/blocked", "product")

        assert result is None

    def test_download_with_different_request_types(self):
        """download() passes request_type to client correctly."""
        mock_client = MagicMock()
        mock_client.get.return_value = "<html></html>"

        strategy = AntiDetectionStrategy(mock_client)

        strategy.download("https://example.com", "home")
        mock_client.get.assert_called_with("https://example.com", request_type="home")

        strategy.download("https://example.com", "category")
        mock_client.get.assert_called_with("https://example.com", request_type="category")

        strategy.download("https://example.com", "product")
        mock_client.get.assert_called_with("https://example.com", request_type="product")


class TestNoOpStrategy:
    """Test NoOpStrategy returns fixture data instantly."""

    def test_init_with_default_content(self):
        """NoOpStrategy initializes with default fixture HTML."""
        strategy = NoOpStrategy()
        assert strategy._fixture_html is not None
        assert isinstance(strategy._fixture_html, str)
        assert len(strategy._fixture_html) > 0

    def test_init_with_custom_content(self):
        """NoOpStrategy can be initialized with custom HTML."""
        custom_html = "<html><body>Custom fixture</body></html>"
        strategy = NoOpStrategy(fixture_html=custom_html)
        assert strategy._fixture_html == custom_html

    def test_download_returns_fixture_instantly(self):
        """download() returns fixture HTML immediately."""
        fixture = "<html><body>Test</body></html>"
        strategy = NoOpStrategy(fixture_html=fixture)

        result = strategy.download("https://example.com", "product")
        assert result == fixture

    def test_download_ignores_url_and_request_type(self):
        """download() returns same fixture regardless of URL or request_type."""
        fixture = "<html>Fixture</html>"
        strategy = NoOpStrategy(fixture_html=fixture)

        # All calls should return the same fixture
        assert strategy.download("https://url1.com", "home") == fixture
        assert strategy.download("https://url2.com", "category") == fixture
        assert strategy.download("https://url3.com/page", "product") == fixture

    def test_noop_strategy_has_no_delays(self):
        """NoOpStrategy does not introduce artificial delays."""
        strategy = NoOpStrategy()

        import time
        start = time.time()
        strategy.download("https://example.com", "product")
        elapsed = time.time() - start

        # Should complete in <100ms (no sleep delays)
        assert elapsed < 0.1

    def test_download_uses_default_if_fixture_none(self):
        """download() uses default fixture if fixture_html is None."""
        strategy = NoOpStrategy(fixture_html=None)
        result = strategy.download("https://example.com", "product")
        # Should use default fixture, not None
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
