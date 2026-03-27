# Technical Documentation — BuscaLibre Web Scraper

Full architecture and implementation detail. For the summary, see [README.md](README.md).

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
│  │  │ • LAYER 3: Context rotation (2–4 books)     │   │    │
│  │  │ • LAYER 6: Cascade nav (home→cat→prod)      │   │    │
│  │  │ • GET /libro-{id} via Playwright browser    │   │    │
│  │  │ • LAYER 4a: Jitter 2–5s before request      │   │    │
│  │  │ • LAYER 2: Random referer header            │   │    │
│  │  │ • Parse data (title, author, price, stock)  │   │    │
│  │  │ • STREAMING write: save_single_record()     │   │    │
│  │  │   (line-by-line to CSV immediately)         │   │    │
│  │  │ • Delay: 8–15s + random jitter              │   │    │
│  │  │ • LAYER 4d: Coffee break every 10–15 books  │   │    │
│  │  │             (150–250s human-like pause)      │   │    │
│  │  │ • 202 handling: 45–70s + context reset      │   │    │
│  │  │ • Auto-stop if 3 consecutive blocks         │   │    │
│  │  └─────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

OUTPUT: CSV with incremental writing (append mode)
        Each record written immediately — crash-safe checkpoint
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
   - Delay 8–15s + jitter
   - Coffee break each 10–15 books
        │
   storage/outputs/books_arte.csv
```

---

## Anti-Detection Systems (7 Layers)

### Layer 1: Real Browser Execution via Playwright

```python
# core/client.py
self._playwright = sync_playwright().start()
self._browser = self._playwright.chromium.launch(headless=False)
self._context = self._browser.new_context(user_agent=CHROME_120_UA)
self._page = self._context.new_page()
```

- **Mechanism:** Real Chromium instance — genuine TLS, JS execution, cookies, fingerprint.
- **Why curl_cffi failed:** AWS WAF's `aws-waf-token` is cryptographically bound to the browser that generated it. Injecting it into a different HTTP client results in 405.
- **Result:** CAPTCHA solved once, token reused across all subsequent requests.

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
    if self._context:
        self._context.close()
    self._context = self._browser.new_context(user_agent=CHROME_120_UA)
    self._page = self._context.new_page()
    if self._waf_token:
        self._context.add_cookies([self._waf_token])  # Restore token

# arte_pipeline.py
if books_in_session >= reset_threshold:
    client.reset_session()
    books_in_session = 0
    reset_threshold = random.randint(2, 4)
```

**Key insight:** The browser process stays alive — only the context (cookies, storage, history) rotates. The WAF token is cached in `self._waf_token` and restored so CAPTCHA is only solved **once** per run. Rotation interval is random (2–4 products).

---

### Layer 4: Multi-level Human Rate Limiting

Six randomness points, each independent:

| Sub-layer | Where | Timing |
|---|---|---|
| 4a: Warm-up jitter | `_initialize_session()` | 2–4s before navigating home |
| 4b: Pre-request jitter | `client.get()` | 2–5s before each `page.goto()` |
| 4c: Main delay | `arte_pipeline.py` | 8–15s between products (PRIMARY) |
| 4d: Coffee break | `arte_pipeline.py` | 150–250s every 10–15 books |
| 4e: Post-block recovery | `arte_pipeline.py` | 45–70s after 202 |
| 4f: Page pause | `arte_pipeline.py` | 60–90s between category pages |

Result: temporal pattern impossible to model.

---

### Layer 5: User-Agent Consistent with Browser

```python
# config/headers.py
CHROME_120_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# core/client.py
self._context = self._browser.new_context(user_agent=CHROME_120_UA)
```

UA is set at context creation and matches the Chromium version — no TLS/UA/fingerprint inconsistencies.

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
# arte_pipeline.py
random.shuffle(links)  # Break sequential pattern

scraped_urls = get_scraped_urls()
if full_link in scraped_urls: continue  # Skip duplicates
success_count = len(scraped_urls)       # Resume from checkpoint
```

- **Shuffling:** Prevents "always extracts first 50 in order" WAF detection.
- **Checkpoint:** On crash, re-run skips already-scraped URLs. `success_count` starts from CSV length so the progress counter is accurate on resume.

---

## File Structure

```
buscalibre-web-scraper/
│
├── config/
│   ├── settings.py                    # Constants (URLs, timeouts, limits)
│   └── headers.py                     # Chrome 120 User-Agent constant
│
├── core/
│   ├── client.py                      # Playwright browser client (headed)
│   ├── parser.py                      # Extract URLs from category page
│   ├── parser_product.py              # Parse individual product data
│   └── paginator.py                   # Build pagination URLs
│
├── pipelines/
│   └── arte_pipeline.py               # Orchestrator with human delays
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
│   │   └── test_arte_pipeline_integration.py
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
PRODUCT_PER_PAGE = 50         # Items per category page
REQUEST_TIMEOUT = 20          # Playwright uses timeout * 3000ms internally

DELAY_MIN = 8.0               # Minimum delay between products (seconds)
DELAY_MAX = 15.0              # Maximum delay between products (seconds)

OUTPUT_PATH = "storage/outputs/books_arte.csv"
SOURCE_NAME = "buscalibre_cl"
```

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
| `pipelines/arte_pipeline.py` | Full simulated flow |

`core/client.py` is not unit-tested — it requires a live Playwright browser. Covered by the pipeline integration test.

---

## Installation (full)

```bash
git clone https://github.com/gaboneumann/buscalibre-web-scraper.git
cd buscalibre-web-scraper

python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
python -m playwright install chromium
sudo python -m playwright install-deps chromium   # Linux only

pytest tests/ -v
python main.py
```

> **WSL users:** Playwright runs headed (visible browser). WSLg or an X11 server is required.

When the browser opens, solve the CAPTCHA manually if prompted. The scraper detects resolution and continues automatically.

---

## Ethical use

This project limits itself to 100 books from a 25k+ catalog, uses multi-second delays, and stops automatically on repeated blocks. It is intended for educational and portfolio use. Verify compliance with local law and the site's ToS before running against any target.
