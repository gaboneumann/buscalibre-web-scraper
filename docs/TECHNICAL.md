# Technical Documentation - BuscaLibre Web Scraper

Full architecture and implementation detail. See the project [README.md](../README.md) for an overview and quick start.

---

## Pipeline Architecture

The scraper runs a two-level nested pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│         LEVEL 1: Page Iteration (Category)                   │
│                                                               │
│  For each category page (up to PRODUCT_TARGET/50):           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Preventive browser context reset                 │   │
│  │  2. GET /libros/arte?page=N via Playwright           │   │
│  │  3. Parse HTML → Extract 50 product links            │   │
│  │  4. LAYER 7: Random shuffling                        │   │
│  │  5. → LEVEL 2 (see below)                            │   │
│  │  6. Delay between pages: 60–90s                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │    LEVEL 2: Product Iteration (Inner Loop)          │    │
│  │                                                      │    │
│  │  For each product on the page:                      │    │
│  │  ┌─────────────────────────────────────────────┐   │    │
│  │  │ • Verify deduplication (CSV checkpoint)     │   │    │
│  │  │ • LAYER 3: Context rotation (10–15 books)   │   │    │
│  │  │ • LAYER 6: Cascade nav (home→cat→prod)      │   │    │
│  │  │ • GET /libro-{id} via Playwright browser    │   │    │
│  │  │ • LAYER 4a: Jitter 2–5s before request      │   │    │
│  │  │ • LAYER 2: Random referer header            │   │    │
│  │  │ • Parse data (title, author, price, stock)  │   │    │
│  │  │ • STREAMING write: save_single_record()     │   │    │
│  │  │   (line-by-line to CSV immediately)         │   │    │
│  │  │ • Delay: 2–6s × multiplier (Layer 8)         │   │    │
│  │  │ • LAYER 4d: Coffee break every 10–15 books  │   │    │
│  │  │             (150–250s human-like pause)      │   │    │
│  │  │ • 202 handling: 45–70s + context reset      │   │    │
│  │  │ • Auto-stop if 3 consecutive blocks         │   │    │
│  │  └─────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

OUTPUT: CSV with incremental writing (append mode)
        Each record written immediately - crash-safe checkpoint
```

---

## Data Flow

```
main.py (Orchestrator)
        │
   Playwright: Navigate Home → Category (CAPTCHA if any)
        │
   Fetch category page → Paginate → Parse links
        │
   For each product:
   - Playwright: GET page
   - Parse data
   - Save to CSV (append)
   - Delay 2–6s × multiplier (Layer 8) + jitter
   - Coffee break each 10–15 books
        │
   storage/outputs/books_arte.csv
```

---

## Anti-Detection Systems (8 Layers)

### Layer 1: Real Browser Execution via Playwright

```python
# core/client.py
self._playwright = sync_playwright().start()
self._browser = self._playwright.chromium.launch(
    channel="chrome", headless=False,
    args=["--ozone-platform=x11", "--disable-blink-features=AutomationControlled", ...]
)
self._context = self._browser.new_context(no_viewport=True)  # native Chrome UA; no override
self._page = self._context.new_page()
```

- **Mechanism:** Real Google Chrome stable binary (via `channel="chrome"`) - genuine TLS, JS execution, cookies, fingerprint, and consistent `userAgentData.brands`. `navigator.webdriver` is suppressed by `--disable-blink-features=AutomationControlled`.
- **Why curl_cffi failed:** AWS WAF's `aws-waf-token` is cryptographically bound to the browser that generated it. Injecting it into a different HTTP client results in 405.
- **Result:** the consistent fingerprint keeps the WAF from serving a CAPTCHA on normal runs; if one does appear, it is solved once and the token is reused across all subsequent requests.

---

### Layer 2: Referer Randomization

```python
# core/client.py
if "/p/" in url or "libro-" in url:
    referers = [f"{DOMAIN_URL}libros/arte", "https://www.google.com/", DOMAIN_URL, "https://www.bing.com/"]
    self._page.set_extra_http_headers({"Referer": random.choice(referers)})
```

Playwright handles `sec-fetch-*` headers automatically. Only `Referer` is overridden to simulate organic discovery.

---

### Layer 3: Browser Context Rotation with WAF Token Persistence

```python
# core/client.py
def _rotate_context(self):
    if self._context is None:
        # First call: create the one and only window.
        self._context = self._browser.new_context(no_viewport=True)  # native Chrome UA
        self._page = self._context.new_page()
    else:
        # Subsequent rotations: fresh cookie jar, same window.
        self._context.clear_cookies()
    if self._waf_token:
        self._context.add_cookies([self._waf_token])  # Restore token
```

**Key insight:** The browser process stays alive - only the cookie jar is cleared on rotation (no new OS window). The WAF token is cached in `self._waf_token` and restored so a CAPTCHA, if it appears at all, is only solved **once** per run. Because `channel="chrome"` is used (real Google Chrome), every context naturally carries the native Chrome UA - no override is needed or applied.

---

### Layer 4: Multi-level Human Rate Limiting

Six randomness points, each independent:

| Sub-layer | Where | Timing |
|---|---|---|
| 4a: Warm-up jitter | `_initialize_session()` | 2–4s before navigating home |
| 4b: Pre-request jitter | `client.get()` | 2–5s before each `page.goto()` |
| 4c: Main delay | `category_pipeline.py` | 2–6s between products × Layer 8 multiplier (1.0–3.0) |
| 4d: Coffee break | `category_pipeline.py` | 150–250s every 10–15 books |
| 4e: Post-block recovery | `category_pipeline.py` | 45–70s after 202 |
| 4f: Page pause | `category_pipeline.py` | 60–90s between category pages |

Result: temporal pattern impossible to model.

---

### Layer 5: Consistent Browser Fingerprint via Real Chrome

```python
# core/client.py
self._browser = self._playwright.chromium.launch(
    channel="chrome", headless=False,
    args=[..., "--disable-blink-features=AutomationControlled"]
)
self._context = self._browser.new_context(no_viewport=True)  # no UA override
```

The browser binary is Google Chrome stable (`channel="chrome"`). No `user_agent=` override is set on the context - the UA string, `userAgentData.brands`, client-hints version, and TLS fingerprint are all natively consistent. `--disable-blink-features=AutomationControlled` ensures `navigator.webdriver === false` on every page.

---

### Layer 6: Cascade Navigation

```python
# core/client.py:_initialize_session()
self._page.goto(DOMAIN_URL, wait_until="networkidle")    # Home
self._page.goto(CATEGORY_URL, wait_until="networkidle")  # Category
```

WAF pattern detection:
- **Bot (rejected):** Home → Product (skips category)
- **Human (accepted):** Home → Category → Product

After every context rotation, the scraper re-visits the category page before the next product.

---

### Layer 7: Shuffling + Deduplication Checkpoint

```python
# category_pipeline.py
random.shuffle(links)  # Break sequential pattern

scraped_urls = get_scraped_urls()
if full_link in scraped_urls: continue  # Skip duplicates
success_count = len(scraped_urls)       # Resume from checkpoint
```

- **Shuffling:** Prevents "always extracts first 50 in order" WAF detection.
- **Checkpoint:** On crash, re-run skips already-scraped URLs. `success_count` starts from CSV length so the progress counter is accurate on resume.

---

### Layer 8: Adaptive Delay Backoff

```python
# pipelines/components.py - at the per-page batch boundary in WebCrawler.run()
total = blocks_in_batch + successful_in_batch
if total == 0:
    pass  # empty batch → HOLD (no signal)
else:
    block_rate = blocks_in_batch / total
    delay_policy.update_multiplier(block_rate)
```

After every category-page batch, the crawlercomputes a `block_rate` and adjusts the inter-request delay multiplier:

| Condition | Action |
|---|---|
| `block_rate > 0.2` | Escalate: `multiplier × 1.5`, capped at `3.0` |
| `block_rate == 0.0` | Decay: `multiplier × 0.9`, floored at `1.0` |
| `0.0 < block_rate ≤ 0.2` | HOLD (no change - avoid oscillation) |
| Both counters zero | HOLD (no signal - don't penalise empty pages) |

The multiplier scales only Layer 4c (`wait_between_products`). All other waits (4a, 4b, 4d, 4e, 4f) are untouched - no double-counting.

**Timing at peak (sustained high block rate, multiplier capped at 3.0):**
- Layer 4c: `uniform(2, 6) × 3.0` = **6–18 seconds** per product (base)
- Layer 4e: exponential backoff up to **180 seconds** on a single blocked request
- Worst-case combined: **~198 seconds per product** - this is intentional, not a bug

**Implementation:** `DelayPolicy` carries `_multiplier` as observable state. The `multiplier` property is publicly readable, enabling state-based assertions in tests without time mocking.

---

## File Structure

```
buscalibre-web-scraper/
│
├── config/
│   └── settings.py                    # Constants (URLs, timeouts, limits)
│
├── core/
│   ├── client.py                      # Playwright browser client (headed)
│   ├── parser.py                      # Extract URLs from category page
│   ├── parser_product.py              # Parse individual product data
│   └── paginator.py                   # Build pagination URLs
│
├── pipelines/
│   └── category_pipeline.py               # Orchestrator with human delays
│
├── storage/
│   └── outputs/                       # Generated CSV output files
│
├── tests/
│   ├── client/
│   ├── parsers/
│   │   ├── test_title_parser.py
│   │   ├── test_author_parser.py
│   │   ├── test_price_parser.py
│   │   └── test_stock_parser.py
│   ├── paginator/
│   │   └── test_paginator.py
│   ├── pipelines/
│   │   └── test_category_pipeline_integration.py
│   ├── fixtures/products/             # HTML fixtures for parser tests
│   ├── test_parser.py
│   └── test_product_integration.py
│
├── main.py
├── requirements.txt
└── pytest.ini
```

---

## Configuration Reference

`config/settings.py`:

```python
DOMAIN_URL = 'https://www.buscalibre.cl/'
CATEGORY_URL = 'https://www.buscalibre.cl/libros/arte'

PRODUCT_TARGET = 100          # Books to extract
REQUEST_TIMEOUT = 20          # Playwright uses timeout * 3000ms internally

DELAY_MIN = 2.0               # Minimum delay between products (seconds, base - Layer 8 scales up)
DELAY_MAX = 6.0               # Maximum delay between products (seconds, base - Layer 8 scales up)

OUTPUT_PATH = "storage/outputs/books_arte.csv"
```

**Output fields:** `title, author, price, stock, page_index, product_url`. The `stock` column holds the available stock (integer count of units in stock, parsed from "Quedan N unidades").

---

## Tests

```bash
pytest tests/ -v                              # All tests
pytest tests/ -m "not network"               # Skip network tests
pytest tests/ --cov=. --cov-report=term-missing
```

| Module | What's tested |
|--------|---------------|
| `core/parser.py` | Valid links, empty HTML, malformed HTML |
| `core/parser_product.py` | Title, author, price, stock extraction |
| `core/paginator.py` | Pagination URL construction |
| `pipelines/category_pipeline.py` | Full simulated flow |

`core/client.py` is not unit-tested - it requires a live Playwright browser. Covered by the pipeline integration test.

---

## Installation (full)

```bash
git clone https://github.com/gaboneumann/buscalibre-web-scraper.git
cd buscalibre-web-scraper

python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt

pytest tests/ -v
python main.py
```

> **Hard runtime dependency:** Google Chrome stable (version 149+) must be installed on the host **before** running `python main.py`. The scraper uses `channel="chrome"` - it launches the real Chrome binary, NOT Playwright's bundled Chromium. If Chrome is absent, startup fails immediately with a "channel chrome not found" error. Install from [google.com/chrome](https://www.google.com/chrome/).

> **WSL users:** Playwright runs headed (visible browser). WSLg or an X11 server is required.

A CAPTCHA rarely appears now that the fingerprint is consistent. If AWS does prompt one, solve it manually in the browser - the scraper detects resolution and continues automatically.

---

## Ethical use

This project limits itself to 100 books from a 25k+ catalog, uses multi-second delays, and stops automatically on repeated blocks. It is intended for educational and portfolio use. Verify compliance with local law and the site's ToS before running against any target.
