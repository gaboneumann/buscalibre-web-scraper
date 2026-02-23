"""
HTTP Client with TLS Fingerprinting and Anti-Detection Features
Uses curl_cffi to simulate Chrome 120 for Cloudflare WAF evasion
"""

import time
import random
from curl_cffi import requests
from config.settings import DOMAIN_URL, REQUEST_TIMEOUT
from config.headers import REAL_BROWSER_HEADERS, CHROME_120_UA, get_dynamic_headers
from urllib.parse import urljoin

class HTTPClient:
    """
    HTTP client with advanced anti-detection capabilities.
    Implements:
    - TLS fingerprinting (impersonate Chrome 120)
    - Dynamic context-aware headers
    - Session rotation every 2-4 requests
    - Human-like jitter delays
    """

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self.session = None
        self.reset_session()  # Initialize session on object creation

    def reset_session(self):
        """Rotate session identity (TLS + Cookies + User-Agent)."""
        # print("♻️ Rotating client identity (TLS + Cookies + User-Agent)...")  # Uncomment for debugging
        self.session = requests.Session()

        # Force consistent Chrome 120 User-Agent (no variation to avoid TLS inconsistencies)
        headers = get_dynamic_headers("home")
        headers["User-Agent"] = CHROME_120_UA

        # Update base headers
        self.session.headers.update(headers)

        self._initialize_session()

    def _initialize_session(self):
        """Visit home page to warm up cookies and establish TLS handshake."""
        try:
            # Initial jitter to avoid looking automated
            time.sleep(random.uniform(2, 4))

            # Use impersonate to match exact Chrome 120 TLS handshake
            self.session.get(
                DOMAIN_URL,
                timeout=self.timeout,
                impersonate="chrome120"
            )
        except Exception as e:
            print(f"⚠️ WARNING: Could not initialize session at home: {e}")

    def get(self, endpoint: str, request_type: str = "product") -> str | None:
        """
        Perform GET request with dynamic headers and status handling.

        Args:
            endpoint: URL endpoint or path
            request_type: One of "home", "category", "product"

        Returns:
            HTML response text or None on error
        """
        if not endpoint:
            raise ValueError("Endpoint cannot be empty")

        url = endpoint if endpoint.startswith("http") else urljoin(DOMAIN_URL, endpoint)

        # --- ANTI-DETECTION LAYER 1: DYNAMIC HEADERS BASED ON CONTEXT ---
        headers = get_dynamic_headers(request_type)
        headers["User-Agent"] = CHROME_120_UA
        self.session.headers.update(headers)

        # --- ANTI-DETECTION LAYER 2: RANDOM REFERER ROTATION ---
        referers = [
            f"{DOMAIN_URL}libros/arte",
            "https://www.google.com/",
            DOMAIN_URL,
            "https://www.bing.com/"
        ]

        # Simulate random navigation origin for product requests
        if "/p/" in url or "libro-" in url:
            self.session.headers.update({"Referer": random.choice(referers)})

        try:
            # Human-like delay before request
            time.sleep(random.uniform(2.0, 5.0))

            # Request with TLS fingerprinting (chrome120)
            response = self.session.get(
                url,
                timeout=self.timeout,
                impersonate="chrome120"
            )

            if response.status_code == 200:
                if len(response.text) < 1000:
                    print(f"⚠️ Warning: Short response from {url}")
                return response.text

            if response.status_code == 202:
                print(f"⛔ 202 BLOCKED detected on {url}. Aborting.")
                return None

            print(f"❌ HTTP Error {response.status_code} on {url}")
            return None

        except Exception as e:
            print(f"❌ Connection error: {e}")
            return None

    def navigate_to_category(self, category_url: str) -> str | None:
        """
        Cascade navigation: Home → Category (more human-like).
        Simulates user interest in the category before exploring products.

        Args:
            category_url: Full category URL or path

        Returns:
            Category page HTML or None on error
        """
        try:
            # Step 1: Already visited home in reset_session()
            print("🏠 [Cascade] Already at home")

            # Step 2: Navigate to category
            print(f"📂 [Cascade] Navigating to category: {category_url}")
            time.sleep(random.uniform(3, 6))  # Browsing time before clicking category

            return self.get(category_url, request_type="category")

        except Exception as e:
            print(f"❌ Cascade navigation error: {e}")
            return None