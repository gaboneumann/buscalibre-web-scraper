"""Tests for HTTPClient URL injection via constructor."""
import pytest
from unittest.mock import patch, MagicMock
from config.settings import DOMAIN_URL, CATEGORY_URL


def _make_wm_mock():
    """Return a MagicMock that satisfies the WindowsManager interface."""
    wm = MagicMock()
    wm.detect_secondary_monitor.return_value = None
    return wm


@patch('core.client.sync_playwright')
class TestHTTPClientUrlInjection:
    """Test that HTTPClient stores injected URLs as instance attributes."""

    def test_client_stores_injected_domain_url(self, mock_playwright):
        mock_playwright.return_value.start.return_value = MagicMock()
        from core.client import HTTPClient
        client = HTTPClient(domain_url="https://custom.com/", windows_manager=_make_wm_mock())
        assert client._domain_url == "https://custom.com/"

    def test_client_defaults_to_settings_domain_url(self, mock_playwright):
        mock_playwright.return_value.start.return_value = MagicMock()
        from core.client import HTTPClient
        client = HTTPClient(windows_manager=_make_wm_mock())
        assert client._domain_url == DOMAIN_URL

    def test_client_stores_injected_category_url(self, mock_playwright):
        mock_playwright.return_value.start.return_value = MagicMock()
        from core.client import HTTPClient
        client = HTTPClient(category_url="https://custom.com/cat", windows_manager=_make_wm_mock())
        assert client._category_url == "https://custom.com/cat"

    def test_wm_detect_secondary_monitor_called_on_init(self, mock_playwright):
        """WindowsManager.detect_secondary_monitor is called exactly once during construction."""
        mock_playwright.return_value.start.return_value = MagicMock()
        from core.client import HTTPClient
        wm = _make_wm_mock()
        HTTPClient(windows_manager=wm)
        wm.detect_secondary_monitor.assert_called_once()
