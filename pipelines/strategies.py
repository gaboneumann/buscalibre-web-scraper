"""Download strategy abstraction for pluggable HTTP handling.

Strategies enable different download behaviors: anti-detection (real browser,
delays, WAF bypass), testing (instant fixtures), or custom implementations.

Usage:
    strategy = AntiDetectionStrategy(HTTPClient())
    html = strategy.download("https://example.com/page", "product")

    # Or for testing:
    strategy = NoOpStrategy()
    html = strategy.download("https://example.com", "product")  # instant
"""
from abc import ABC, abstractmethod


class DownloadStrategy(ABC):
    """Abstract base class for download strategies.

    Enables pluggable HTTP handling: anti-detection (real delays),
    no-op (instant fixtures for testing), custom implementations.

    Implementers must define download(url, request_type) → str | None.
    """

    @abstractmethod
    def download(self, url: str, request_type: str) -> str | None:
        """Download content from URL.

        Args:
            url: Full URL to download.
            request_type: One of "home", "category", "product".
                Used by anti-detection strategies to set appropriate headers.

        Returns:
            HTML content as string, or None on block/error/timeout.
        """
        pass


class AntiDetectionStrategy(DownloadStrategy):
    """Downloads via HTTPClient with full anti-detection pipeline.

    Applies delays, session rotation, headers, all configured in HTTPClient.
    """

    def __init__(self, client):
        """Initialize with HTTPClient instance.

        Args:
            client: HTTPClient for making requests.
        """
        self._client = client

    def download(self, url: str, request_type: str) -> str | None:
        """Download via HTTPClient.get() with anti-detection.

        Args:
            url: Full URL to download.
            request_type: One of "home", "category", "product".

        Returns:
            HTML content or None if blocked (202, timeout, etc.).
        """
        return self._client.get(url, request_type=request_type)


class NoOpStrategy(DownloadStrategy):
    """Returns fixture HTML instantly (no delays, no network).

    Used for testing to run full pipeline in seconds.
    """

    def __init__(self, fixture_html: str | None = None):
        """Initialize with optional fixture HTML.

        Args:
            fixture_html: HTML to return. If None, uses default fixture.
        """
        self._fixture_html = fixture_html or self._default_fixture()

    @staticmethod
    def _default_fixture() -> str:
        """Return default fixture HTML with sample product links."""
        return """
        <html>
        <head><title>Test Category</title></head>
        <body>
            <h1>Category Page</h1>
            <div class="products">
                <a href="/p/test-product-1" class="product-link">Test Book 1</a>
                <a href="/p/test-product-2" class="product-link">Test Book 2</a>
                <a href="/p/test-product-3" class="product-link">Test Book 3</a>
            </div>
        </body>
        </html>
        """

    def download(self, url: str, request_type: str) -> str | None:
        """Return fixture HTML instantly.

        Args:
            url: Ignored (returns same fixture).
            request_type: Ignored (returns same fixture).

        Returns:
            Fixture HTML, or None if fixture is None.
        """
        return self._fixture_html
