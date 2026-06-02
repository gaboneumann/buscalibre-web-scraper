# BuscaLibre Web Scraper

> Python scraper that bypasses **AWS WAF** on BuscaLibre Chile using Playwright. Extracts books with **0 blocks** using a two-level web crawler, adaptive anti-detection policies, and pluggable download strategies.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Real%20Browser-45ba4b?logo=playwright&logoColor=white)
![AWS WAF](https://img.shields.io/badge/AWS%20WAF-CAPTCHA%20Bypass-FFA500)
![ETL Pipeline](https://img.shields.io/badge/ETL-Two--Level%20Web--Crawler-blueviolet)
![Anti-Detection](https://img.shields.io/badge/Anti--Detection-8%20Layers-brightgreen)
![Tests](https://img.shields.io/badge/Tests-158%20pytest-brightgreen?logo=pytest&logoColor=white)

---

## The Problem

BuscaLibre uses **AWS WAF** with two challenge types: `challenge.js` (auto-resolved JS) and `captcha.js` (visible CAPTCHA). The WAF token is cryptographically bound to the browser that solved it, so you can't extract and reuse it in a plain HTTP client.

**Solution:** Playwright launches a real Chromium browser. CAPTCHA is solved once manually. The `aws-waf-token` cookie is cached and restored across browser context rotations, so no re-solving is needed.

---

## Results

| Metric | Value |
| :------ | ----: |
| Books extracted | **600** across 5 categories |
| Categories tested | arte, tecnología, matemáticas, deportes, novela-gráfica |
| Success rate | **100%** |
| 202 blocks | **0** |
| Anti-detection layers | 8 |
| Web crawler execution | Sequential two-level (categories → products) |
| Adaptive behavior | Layer 8: Adaptive Delay Backoff (multiplier 1.0–3.0) |

---

**Multi-Category Capability**: The scraper is fully generic and tested across 5 distinct categories (art, technology, mathematics, sports, graphic novels). Target **any Buscalibre category** by changing `CATEGORY_URL` in config — same anti-detection robustness, zero blocks.

---

## Evolution: V1 → V2 → V3

| | V1 | V2 | **V3 (current)** |
|---|---|---|---|
| HTTP client | curl_cffi generic | `impersonate="chrome120"` | **Real Playwright browser** |
| WAF | Cloudflare (assumed) | Cloudflare (assumed) | **AWS WAF (confirmed)** |
| CAPTCHA | Not handled | Not handled | **Solved once, token cached** |
| Sec-Fetch headers | Static `"none"` | Dynamic by context | **Automatic (real browser)** |
| Context rotation | Every 50–100 (fixed) | Every 2–4 (random) | **Policy-based (10–15 products)** |
| Delays | 10–20s | 30–55s + jitter | **4–8s + coffee breaks (150–250s)** |
| Block handling | Fixed retry | Fixed wait | **Exponential backoff (45s → 90s → 180s)** |
| 202 rate | 70% | 0% | **0%** |

---

## Stack

- **Playwright**: headed Chromium for WAF bypass
- **BeautifulSoup4 + lxml**: HTML parsing (decoupled from HTTP client, fully testable)
- **pytest**: unit tests with HTML fixtures
- **curl-cffi**: HTTP impersonation fallback (reserved for future use)

---

## Project Architecture

```
buscalibre-web-scraper/
├── main.py                          # Entry point (CLI + config handling)
├── config/
│   ├── settings.py                  # Default configuration constants
│   ├── headers.py                   # Dynamic request headers (request-type aware)
│   └── logging_config.py            # Logging setup (levels, formatting)
├── core/
│   ├── client.py                    # HTTPClient (Playwright, session rotation, strategy injection)
│   ├── parser.py                    # Extract product links from category pages
│   ├── parser_product.py            # Extract title/author/price/stock from product pages
│   └── paginator.py                 # Build paginated category URLs
├── pipelines/
│   ├── base_pipeline.py             # Abstract base pipeline class
│   ├── category_pipeline.py         # Generic Buscalibre category scraper
│   ├── config.py                    # PipelineConfig (dependency injection container)
│   ├── schema.py                    # CSVSchema + CheckpointManager (checkpoint/resume)
│   ├── components.py                # Policies (SessionRotation, BlockDetection, Delay, Adaptive)
│   └── strategies.py                # DownloadStrategy (AntiDetection, NoOp)
├── storage/
│   └── outputs/                     # CSV output directory (auto-created)
├── tests/
│   ├── client/                      # HTTPClient unit tests + mocks
│   ├── components/                  # Policies & WebCrawler tests
│   ├── config/                      # PipelineConfig & ConfigLoading tests
│   ├── parsers/                     # Parser unit tests + fixtures
│   ├── paginator/                   # Paginator tests
│   ├── pipelines/                   # Pipeline integration tests
│   ├── strategies/                  # Strategy tests (NoOp, AntiDetection)
│   ├── fixtures/                    # HTML test data (reusable across test suites)
│   ├── test_e2e_with_noop_strategy.py      # Full E2E pipeline tests
│   └── test_regression_orchestrator_output.py # Regression suite
├── docs/
│   ├── TECHNICAL.md                 # Full architecture, 8 anti-detection layers, data flow
│   ├── MIGRATION.md                 # Web Crawler architecture refactor phases (1-6)
│   └── feature_update.md            # Feature changelog and updates
└── requirements.txt                 # Python dependencies
```

---

## Quick Start

```bash
git clone https://github.com/gaboneumann/buscalibre-web-scraper.git
cd buscalibre-web-scraper

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
# Linux only:
sudo python -m playwright install-deps chromium

pytest tests/ -m "not network" -v   # verify
python main.py                       # run (solve the CAPTCHA when the browser opens)
```

**Output:** CSV file with auto-generated name based on category (e.g., `storage/outputs/books_arte.csv`).

**Fields:** `title, author, price, stock, page_index, product_url, source, category_url`

---

## Configuration

### Via `config/settings.py` (default)

```python
DOMAIN_URL = "https://www.buscalibre.cl/"
CATEGORY_URL = "https://www.buscalibre.cl/libros/arte"
PRODUCT_TARGET = 100
DELAY_MIN = 4.0
DELAY_MAX = 8.0
SOURCE_NAME = "buscalibre_cl"
OUTPUT_PATH = "storage/outputs/books.csv"
```

### Via CLI flags

```bash
python main.py --target 200                          # Override product target
python main.py --config /path/to/config.json         # Load config from JSON file
python main.py --config config.json --target 150     # Combine both
```

### Config JSON format

```json
{
  "domain_url": "https://www.buscalibre.cl/",
  "category_url": "https://www.buscalibre.cl/libros/arte",
  "product_target": 100,
  "delay_min": 4.0,
  "delay_max": 8.0,
  "source_name": "buscalibre_cl",
  "output_path": "storage/outputs/books.csv"
}
```

---

## Two-Level Web Crawler Structure

The scraper implements a **two-level nested iteration** with intelligent batch-aware policies:

```
┌──────────────────────────────────────────────────────────────────┐
│                    WebCrawler.run()                              │
├──────────────────────────────────────────────────────────────────┤
│  OUTER LOOP: Category Pages (page_index = 1, 2, 3, ...)          │
│  ├─ Reset session (fresh cookies/fingerprint)                    │
│  ├─ Navigate: category?page=N                                    │
│  ├─ LEVEL 1 - Extract: collect_product_links(html) → List[url]  │
│  │                                                                │
│  │  INNER LOOP: Products on this page                            │
│  │  ├─ Skip if in checkpoint (deduplication)                     │
│  │  ├─ Check: should_rotate(books_in_session)?                   │
│  │  │   └─ If YES: reset_session() + rotation_wait()             │
│  │  │                                                             │
│  │  ├─ Fetch: client.get(product_url)                            │
│  │  │   └─ 202 block? → exponential_backoff() + retry            │
│  │  │                                                             │
│  │  ├─ LEVEL 2 - Transform: parse_product(html) → Dict           │
│  │  ├─ LEVEL 3 - Load: save_record() + checkpoint_mgr            │
│  │  ├─ wait_between_products() [4–8s + multiplier×]              │
│  │  ├─ Check: should_take_coffee_break()? → wait 150–250s        │
│  │  └─ Check: product_target reached? → STOP                     │
│  │                                                                │
│  ├─ [BATCH SUMMARY] blocks vs successes in this page             │
│  ├─ Layer 8: Adaptive Delay Backoff                              │
│  │   └─ block_rate = blocks / (blocks + successes)               │
│  │   └─ Update multiplier (1.0–3.0×) for next page delays        │
│  ├─ wait_between_pages()                                         │
│  └─ Reset batch counters → page_index++                          │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow: Extract → Transform → Load

1. **Extract** (Level 1): `extract_fn(html)` → finds all `<a href="/libro-...">` links on category page
2. **Transform** (Level 2): `transform_fn(html)` → parses title, author, price, stock from product page
3. **Load** (Level 3): `checkpoint_mgr.save_record()` → appends validated record to CSV + updates in-memory scraped_urls set

### Key Components

- **WebCrawler**: Orchestrates two-level iteration with **batch-aware policies**: after each category page (batch), analyzes block_rate and adjusts delay multiplier (Layer 8).
- **PipelineConfig**: Dependency injection container with `product_target` (hard cap on total products scraped), `category_url`, delays, and output path.
- **Policies** (pluggable, reusable):
  - **SessionRotationPolicy**: Tracks products per session; on threshold (10–15), rotates and waits 10–15s
  - **BlockDetectionPolicy**: Tracks consecutive 202s; exponential backoff (45s → 90s → 180s); auto-abort after 3 consecutive
  - **DelayPolicy**: Inter-request delays (4–8s), coffee breaks (150–250s every 10–15 products), multiplier-aware
- **Download Strategies**: Pluggable HTTP handlers (`AntiDetectionStrategy` with real browser; `NoOpStrategy` with instant fixtures)
- **CheckpointManager**: Reads existing CSV → extracts scraped URLs → prevents duplicate processing on resume
- **CSVSchema**: Validates parsed product data before writing

---

## Anti-Detection

### 8 Layers

| # | Layer | Purpose |
|---|---|---|
| 1 | **Real Browser Execution** | Playwright Chromium for genuine TLS, JS execution, and fingerprint |
| 2 | **Referer Randomization** | Simulate organic discovery from search engines and category pages |
| 3 | **Context Rotation + Token Persistence** | Rotate cookies/storage every 2–4 products; WAF token reused across rotations |
| 4 | **Multi-level Human Rate Limiting** | 6 independent timing jitters (warm-up, pre-request, main, coffee, recovery, page) |
| 5 | **Consistent User-Agent** | Chrome 120 UA matches Chromium binary (no TLS/UA mismatch) |
| 6 | **Cascade Navigation** | Home → Category → Product (avoids bot-pattern direct hits) |
| 7 | **Shuffling + Checkpoint** | Random link order + CSV deduplication on resume |
| 8 | **Adaptive Delay Backoff** | Per-batch block rate drives multiplier (1.0–3.0×) on the inter-request delay |

> Full implementation details with code samples: **[docs/TECHNICAL.md](docs/TECHNICAL.md)**

### Adaptive Policies

#### Session Rotation Policy
- **Threshold:** 10–15 products per session (randomized)
- **On rotation:** Wait 10–15 seconds before resuming
- **Purpose:** Randomize connection fingerprint

#### Block Detection Policy
- **Exponential backoff:** 45s → 90s → 180s (with ±20% jitter)
- **Threshold:** 3 consecutive failures → auto-abort
- **Purpose:** Respect rate limits and gracefully abort when blocked

#### Delay Policy
- **Inter-request:** 4–8 seconds (randomized)
- **Coffee breaks:** Every 10–15 products, sleep 150–250 seconds (2.5–4.2 min)
- **Purpose:** Human-like behavior, avoid pattern detection

#### Adaptive Delay Backoff (Layer 8)
- On block_rate > 20%: **Escalate multiplier × 1.5**, capped at 3.0×
- On block_rate == 0%: **Decay multiplier × 0.9**, floored at 1.0×
- On 0% < block_rate ≤ 20%: **Hold** (avoid oscillation)
- Base delay 4–8s; at 3.0× peak: 12–24s per product
- Purpose: Automatically back off under pressure, recover during clean runs

---

## Download Strategies

Pluggable HTTP handling for different execution contexts:

### AntiDetectionStrategy (default)

```python
from pipelines.strategies import AntiDetectionStrategy
from core.client import HTTPClient

client = HTTPClient()
strategy = AntiDetectionStrategy(client)
html = strategy.download("https://...", request_type="product")
```

Real browser, full delays, WAF bypass.

### NoOpStrategy (testing)

```python
from pipelines.strategies import NoOpStrategy
from pipelines.config import PipelineConfig

strategy = NoOpStrategy()  # Returns instant fixtures
config = PipelineConfig(..., download_strategy=strategy)
pipeline = CategoryPipeline(client=client, config=config)
pipeline.run()  # Completes in <5 seconds for testing
```

Instant fixture returns, no network, no delays. Ideal for CI/CD and local testing.

---

## Resume & Checkpoint

The scraper resumes from the last saved state:

1. **On startup**, `CheckpointManager` reads the CSV file
2. **Extracts already-scraped URLs** from the category
3. **Skips duplicates** during iteration
4. **Continues from the next product**

Example log:

```
Resuming from checkpoint: 45/100 already scraped.
```

If the scraper crashes after 45 products, restart `python main.py` and it will continue from product #46.

---

## Testing

```bash
# Run all unit tests (no network)
pytest tests/ -m "not network" -v

# Run a single test file
pytest tests/parsers/test_price_parser.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

Unit tests with HTML fixtures validate parser behavior deterministically. `core/client.py` requires a live Playwright browser and is covered by integration tests.

---

## Design Principles

- **Streaming writes over batch**: each product appended to CSV immediately. On crash, resume from checkpoint.
- **Anti-detection is baked in**: User-Agent fixed to Chrome 120 (matches TLS fingerprint), dynamic headers per request type, intentionally long delays.
- **Pluggable architecture**: strategies for HTTP, policies for behavior, configs for flexibility.
- **Testability**: decoupled parsers (BeautifulSoup only), fixture-based unit tests, no browser required for tests.
- **No random User-Agent**: randomization breaks TLS fingerprint matching and will be detected.

---

## Documentation

Comprehensive docs organized in [`docs/`](docs/):

- **[docs/TECHNICAL.md](docs/TECHNICAL.md)**: full architecture, 8 anti-detection layers, data flow

---

## Ethical Use

This project limits itself to a small subset of BuscaLibre's 25k+ catalog, uses multi-second delays between requests, and stops automatically on repeated blocks. It is intended for **educational and portfolio purposes**.

Verify compliance with local law and the site's Terms of Service before running against any target.

---

**Gabriel Neumann** · [LinkedIn](https://www.linkedin.com/in/gaboneumann/) · [GitHub](https://github.com/gaboneumann)
