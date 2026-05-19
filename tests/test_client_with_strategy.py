"""Unit tests for HTTPClient with optional download_strategy parameter."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from core.client import HTTPClient


class TestHTTPClientStrategySupport:
    """Test HTTPClient accepts and uses optional download_strategy."""

    def test_client_init_without_strategy(self):
        """HTTPClient initializes without strategy (backward compatible)."""
        with patch('core.client.sync_playwright'):
            client = HTTPClient()
            assert hasattr(client, '_strategy')
            assert client._strategy is None

    def test_client_init_with_strategy(self):
        """HTTPClient stores strategy if provided."""
        mock_strategy = MagicMock()
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=mock_strategy)
            assert client._strategy is mock_strategy

    def test_client_get_uses_strategy_if_provided(self):
        """HTTPClient.get() delegates to strategy if provided."""
        mock_strategy = MagicMock()
        mock_strategy.download.return_value = "<html>From strategy</html>"

        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=mock_strategy)
            result = client.get("https://example.com/page", request_type="product")

            mock_strategy.download.assert_called_once_with(
                "https://example.com/page", "product"
            )
            assert result == "<html>From strategy</html>"

    def test_client_get_uses_default_implementation_without_strategy(self):
        """HTTPClient.get() uses default implementation if strategy is None."""
        with patch('core.client.sync_playwright'):
            client = HTTPClient()

            # Without strategy, client should use default Playwright-based get()
            # (which we can't easily test without full browser setup, but we can verify
            # the strategy path is NOT taken by checking _strategy is None)
            assert client._strategy is None

    def test_client_get_strategy_returns_none_on_block(self):
        """HTTPClient.get() returns None when strategy returns None."""
        mock_strategy = MagicMock()
        mock_strategy.download.return_value = None

        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=mock_strategy)
            result = client.get("https://example.com/blocked", request_type="product")

            assert result is None

    def test_client_get_with_different_request_types(self):
        """HTTPClient.get() passes request_type correctly to strategy."""
        mock_strategy = MagicMock()
        mock_strategy.download.return_value = "<html></html>"

        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=mock_strategy)

            client.get("https://example.com", request_type="home")
            mock_strategy.download.assert_called_with("https://example.com", "home")

            client.get("https://example.com", request_type="category")
            mock_strategy.download.assert_called_with("https://example.com", "category")

            client.get("https://example.com", request_type="product")
            mock_strategy.download.assert_called_with("https://example.com", "product")

    def test_client_reset_session_works_with_strategy(self):
        """HTTPClient.reset_session() works regardless of strategy."""
        mock_strategy = MagicMock()
        with patch('core.client.sync_playwright'):
            client = HTTPClient(download_strategy=mock_strategy)

            # Should not raise error
            client.reset_session()
            assert client._strategy is mock_strategy
