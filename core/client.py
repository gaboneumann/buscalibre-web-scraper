"""
HTTP Client with Playwright-based browser automation.
Uses a real Chromium browser to solve AWS WAF JS challenges automatically.
Browser instance persists across session rotations — CAPTCHA only solved once.
"""

import time
import random
from playwright.sync_api import sync_playwright
from config.settings import DOMAIN_URL, CATEGORY_URL, REQUEST_TIMEOUT
from config.headers import CHROME_120_UA
from urllib.parse import urljoin


class HTTPClient:
    """
    HTTP client using Playwright headed Chromium.
    - Browser instance stays alive for the full scraping run.
    - Session rotation creates a new context (fresh cookies/identity) but
      preserves the aws-waf-token so the CAPTCHA is only solved once.
    """

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout * 3000  # Convert seconds to ms for Playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=False)
        self._context = None
        self._page = None
        self._waf_token = None  # Cached across session rotations
        self.reset_session()

    def reset_session(self):
        """Rotate session identity (new context = new cookies/fingerprint).
        Reuses the cached aws-waf-token to skip CAPTCHA on subsequent rotations.
        """
        self._rotate_context()
        self._initialize_session()

    def _rotate_context(self):
        """Close current context and open a fresh one, restoring the WAF token."""
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass

        self._context = self._browser.new_context(user_agent=CHROME_120_UA)
        self._page = self._context.new_page()

        # Restore WAF token so CAPTCHA doesn't re-trigger
        if self._waf_token:
            self._context.add_cookies([self._waf_token])

    def _initialize_session(self):
        """Visit home → category to warm up session.
        If CAPTCHA appears (first run or token expired), waits for user to solve it.
        """
        try:
            time.sleep(random.uniform(2, 4))
            self._page.goto(DOMAIN_URL, wait_until="networkidle", timeout=self.timeout)
            time.sleep(random.uniform(4, 6))

            self._page.goto(CATEGORY_URL, wait_until="networkidle", timeout=self.timeout)

            if "Human Verification" in self._page.title():
                print("🧩 CAPTCHA detected — please solve it in the browser window...")
                self._page.wait_for_function(
                    "document.title !== 'Human Verification'",
                    timeout=180000
                )
                print("✅ CAPTCHA solved!")

            # Cache WAF token for next rotation
            cookies = self._context.cookies()
            waf = next((c for c in cookies if c["name"] == "aws-waf-token"), None)
            if waf:
                self._waf_token = waf

            print("✅ Session initialized.")
        except Exception as e:
            print(f"⚠️ WARNING: Could not initialize session: {e}")

    def get(self, endpoint: str, request_type: str = "product") -> str | None:
        """
        Navigate to URL using Playwright and return page HTML.

        Args:
            endpoint: Full URL or path
            request_type: One of "home", "category", "product"

        Returns:
            HTML content or None on error/block
        """
        if not endpoint:
            raise ValueError("Endpoint cannot be empty")

        url = endpoint if endpoint.startswith("http") else urljoin(DOMAIN_URL, endpoint)

        # Only set Referer for product pages — Playwright generates all other headers naturally
        if "/p/" in url or "libro-" in url:
            referers = [
                f"{DOMAIN_URL}libros/arte",
                "https://www.google.com/",
                DOMAIN_URL,
                "https://www.bing.com/"
            ]
            self._page.set_extra_http_headers({"Referer": random.choice(referers)})

        try:
            time.sleep(random.uniform(2.0, 5.0))

            response = self._page.goto(url, wait_until="networkidle", timeout=self.timeout)

            # WAF challenge: wait for JS token to settle, then retry once
            if response.status in (202, 405):
                print(f"🔑 WAF challenge on {url} — retrying with token...")
                time.sleep(random.uniform(6, 9))
                response = self._page.goto(url, wait_until="networkidle", timeout=self.timeout)

            if response.status == 200:
                html = self._page.content()
                if len(html) < 1000:
                    print(f"⚠️ Warning: Short response from {url}")
                return html

            if response.status in (202, 405):
                print(f"⛔ WAF BLOCKED ({response.status}) on {url}. Aborting.")
                return None

            print(f"❌ HTTP Error {response.status} on {url}")
            return None

        except Exception as e:
            print(f"❌ Connection error: {e}")
            return None

    def navigate_to_category(self, category_url: str) -> str | None:
        """Cascade navigation: Home → Category."""
        try:
            print("🏠 [Cascade] Already at home")
            print(f"📂 [Cascade] Navigating to category: {category_url}")
            time.sleep(random.uniform(3, 6))
            return self.get(category_url, request_type="category")
        except Exception as e:
            print(f"❌ Cascade navigation error: {e}")
            return None
