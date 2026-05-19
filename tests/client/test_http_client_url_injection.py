"""Tests for HTTPClient URL injection via constructor."""
import pytest
from unittest.mock import patch, MagicMock
from config.settings import DOMAIN_URL, CATEGORY_URL


@patch('core.client.sync_playwright')
class TestHTTPClientUrlInjection:
    """Test that HTTPClient stores injected URLs as instance attributes."""

    def test_client_stores_injected_domain_url(self, mock_playwright):
        mock_playwright.return_value.start.return_value = MagicMock()
        from core.client import HTTPClient
        client = HTTPClient(domain_url="https://custom.com/")
        assert client._domain_url == "https://custom.com/"

    def test_client_defaults_to_settings_domain_url(self, mock_playwright):
        mock_playwright.return_value.start.return_value = MagicMock()
        from core.client import HTTPClient
        client = HTTPClient()
        assert client._domain_url == DOMAIN_URL

    def test_client_stores_injected_category_url(self, mock_playwright):
        mock_playwright.return_value.start.return_value = MagicMock()
        from core.client import HTTPClient
        client = HTTPClient(category_url="https://custom.com/cat")
        assert client._category_url == "https://custom.com/cat"
