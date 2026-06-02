"""
HTTP Client with Playwright-based browser automation.
Uses a real Chromium browser to solve AWS WAF JS challenges automatically.
Browser instance persists across session rotations — CAPTCHA only solved once.
"""

import logging
import time
import random
from typing import Tuple, Optional
from playwright.sync_api import sync_playwright
from config.settings import (
    DOMAIN_URL, CATEGORY_URL, REQUEST_TIMEOUT,
    DELAY_MIN, DELAY_MAX, DELAY_RECOVERY_MIN, DELAY_RECOVERY_MAX,
    CAPTCHA_SOLVE_TIMEOUT_MS
)
from config.headers import CHROME_120_UA
from urllib.parse import urljoin
from core.windows_manager import WindowsManager

logger = logging.getLogger(__name__)

# Stable WM_CLASS for the browser window. The GNOME "Auto Move Windows"
# extension matches this exact string (via a .desktop StartupWMClass) to pin
# the window to a fixed workspace. Keep in sync with that desktop entry.
BROWSER_WM_CLASS = "BuscaLibreScraper"


class HTTPClient:
    """
    HTTP client using Playwright headed Chromium.
    - Browser instance stays alive for the full scraping run.
    - Session rotation creates a new context (fresh cookies/identity) but
      preserves the aws-waf-token so the CAPTCHA is only solved once.
    """

    def __init__(
        self,
        timeout: int = REQUEST_TIMEOUT,
        download_strategy=None,
        domain_url: str | None = None,
        category_url: str | None = None,
        backoff_base_http: float = 6,
        windows_manager=None,
    ):
        # --- 1. Plain config (unchanged) ---
        self.timeout = timeout * 3000  # Convert seconds to ms for Playwright
        self._strategy = download_strategy
        self._domain_url = domain_url or DOMAIN_URL
        self._category_url = category_url or CATEGORY_URL
        self._backoff_base_http = backoff_base_http

        # --- 2. ALL Playwright/session attributes initialized FIRST (None or injected) ---
        #     Guarantees close()/reset_session() are AttributeError-safe on the skip path.
        self._playwright = None
        self._wm = windows_manager        # may stay None when browser is skipped
        self._browser = None
        self._context = None
        self._page = None
        self._waf_token = None  # Cached across session rotations
        self._in_recovery = False  # Track if we're in recovery mode (post-error)

        # --- 3. Single source of truth, evaluated once ---
        needs_browser = self._strategy is None or self._strategy.requires_browser

        # --- 4. Conditional browser bring-up ---
        if needs_browser:
            self._playwright = sync_playwright().start()
            self._wm = windows_manager or WindowsManager()

            # Auto-position browser on the secondary monitor (HP laptop screen)
            # so it doesn't pop up over whatever is on the primary monitor.
            # --start-maximized fills that monitor; verified to coexist with
            # --window-position under XWayland (--ozone-platform=x11).
            #
            # --class=BuscaLibreScraper pins a STABLE WM_CLASS on the window
            # (Playwright's default WM_CLASS embeds a random profile path, which
            # is unusable as a match key). The GNOME "Auto Move Windows"
            # extension matches this class and places the window on the
            # configured workspace at creation time. DO NOT change this string
            # without updating the extension's application-list rule.
            launch_args = ["--ozone-platform=x11", f"--class={BROWSER_WM_CLASS}"]
            secondary = self._wm.detect_secondary_monitor()
            if secondary and len(secondary) == 4:
                x, y, _, _ = secondary
                launch_args.append(f"--window-position={x},{y}")
                launch_args.append("--start-maximized")
                logger.info("Opening browser maximized on secondary monitor at x=%d, y=%d", x, y)

            self._browser = self._playwright.chromium.launch(headless=False, args=launch_args)
            self.reset_session()

    def _get_adaptive_delay(self) -> Tuple[float, float]:
        """
        Get adaptive delay range based on recovery state.
        - Normal: 4-8s (happy path)
        - Recovery: 15-25s (post-error backoff)
        """
        if self._in_recovery:
            return (DELAY_RECOVERY_MIN, DELAY_RECOVERY_MAX)
        return (DELAY_MIN, DELAY_MAX)

    def reset_session(self):
        """Rotate session identity (new context = new cookies/fingerprint).
        Reuses the cached aws-waf-token to skip CAPTCHA on subsequent rotations.
        No-op when the active strategy needs no browser.
        """
        if self._strategy is not None and not self._strategy.requires_browser:
            return
        self._rotate_context()
        self._initialize_session()

    def _rotate_context(self):
        """Close current context and open a fresh one, restoring the WAF token."""
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass

        # no_viewport=True lets the page fill the maximized window instead of
        # Playwright's default fixed 1280x720 viewport.
        self._context = self._browser.new_context(user_agent=CHROME_120_UA, no_viewport=True)
        self._page = self._context.new_page()

        # Workspace placement is handled by the GNOME Auto Move Windows
        # extension at window-creation time (matched via --class=BuscaLibreScraper).
        # No post-creation move here — that would cause appear-then-move flicker.

        # Restore WAF token so CAPTCHA doesn't re-trigger
        if self._waf_token:
            self._context.add_cookies([self._waf_token])

    def _initialize_session(self):
        """Visit home → category to warm up session.
        If CAPTCHA appears (first run or token expired), waits for user to solve it.
        """
        try:
            time.sleep(random.uniform(2, 4))
            self._page.goto(self._domain_url, wait_until="domcontentloaded", timeout=self.timeout)
            time.sleep(random.uniform(4, 6))

            self._page.goto(self._category_url, wait_until="domcontentloaded", timeout=self.timeout)

            if "Human Verification" in self._page.title():
                logger.warning("CAPTCHA detected — please solve it in the browser window...")
                self._wm.notify_captcha()
                logger.info("Waiting for CAPTCHA solution (timeout: %dms = %.1f min)...", CAPTCHA_SOLVE_TIMEOUT_MS, CAPTCHA_SOLVE_TIMEOUT_MS / 60000)
                self._page.wait_for_function(
                    "document.title !== 'Human Verification'",
                    timeout=CAPTCHA_SOLVE_TIMEOUT_MS
                )
                logger.info("CAPTCHA solved!")

            # Cache WAF token for next rotation
            cookies = self._context.cookies()
            waf = next((c for c in cookies if c["name"] == "aws-waf-token"), None)
            if waf:
                self._waf_token = waf

            logger.debug("Session initialized.")
        except Exception as e:
            logger.warning("Could not initialize session: %s", e)

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

        url = endpoint if endpoint.startswith("http") else urljoin(self._domain_url, endpoint)

        # Delegate to strategy if provided
        if self._strategy:
            return self._strategy.download(url, request_type)

        # Only set Referer for product pages — Playwright generates all other headers naturally
        if "/p/" in url or "libro-" in url:
            referers = [
                f"{self._domain_url}libros/arte",
                "https://www.google.com/",
                self._domain_url,
                "https://www.bing.com/"
            ]
            self._page.set_extra_http_headers({"Referer": random.choice(referers)})

        try:
            # Use adaptive delay: 4-8s normal, 15-25s if recovering from error
            delay_min, delay_max = self._get_adaptive_delay()
            time.sleep(random.uniform(delay_min, delay_max))

            response = self._page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

            # WAF challenge: exponential backoff with jitter
            max_retries = 3
            backoff_base = self._backoff_base_http
            for attempt in range(1, max_retries + 1):
                if response.status in (202, 405):
                    if attempt < max_retries:
                        wait_time = backoff_base * (2 ** (attempt - 1))
                        jitter = random.uniform(-0.2, 0.2) * wait_time
                        total_wait = wait_time + jitter
                        logger.warning("WAF challenge attempt %s/%s on %s — waiting %.1fs", attempt, max_retries, url, total_wait)
                        time.sleep(total_wait)
                        response = self._page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                    else:
                        logger.error("WAF BLOCKED (%s) on %s after %s retries. Giving up.", response.status, url, max_retries)
                        self._in_recovery = True  # Mark for recovery mode
                        return None
                else:
                    break

            if response.status == 200:
                self._in_recovery = False  # Reset recovery flag on success
                html = self._page.content()
                if len(html) < 1000:
                    logger.warning("Short response from %s", url)
                return html

            if response.status in (202, 405):
                logger.error("WAF BLOCKED (%s) on %s. Aborting.", response.status, url)
                self._in_recovery = True  # Mark for recovery mode
                return None

            logger.error("HTTP Error %s on %s", response.status, url)
            return None

        except Exception as e:
            logger.error("Connection error: %s", e)
            self._in_recovery = True  # Mark for recovery mode
            return None

    def close(self) -> None:
        """Release all Playwright resources (context, browser, playwright).

        Each step is wrapped defensively so a failure in one does not prevent
        the others from running. Safe to call with a None context.
        """
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass

        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass

        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    def navigate_to_category(self, category_url: str) -> str | None:
        """Cascade navigation: Home → Category."""
        try:
            logger.debug("[Cascade] Already at home")
            logger.debug("[Cascade] Navigating to category: %s", category_url)
            time.sleep(random.uniform(3, 6))
            return self.get(category_url, request_type="category")
        except Exception as e:
            logger.error("Cascade navigation error: %s", e)
            return None
