# BuscaLibre Web Scraper

> Python scraper that bypasses **AWS WAF** on BuscaLibre Chile using Playwright. Extracts books with 0 blocks using adaptive anti-detection policies and pluggable download strategies.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Real%20Browser-45ba4b?logo=playwright&logoColor=white)
![AWS WAF](https://img.shields.io/badge/AWS%20WAF-CAPTCHA%20Bypass-FFA500)
![ETL Pipeline](https://img.shields.io/badge/ETL-Two--Level%20Orchestrator-blueviolet)
![Anti-Detection](https://img.shields.io/badge/Anti--Detection-7%20Layers-brightgreen)

---

## The problem it solves

BuscaLibre uses **AWS WAF** with two challenge types: `challenge.js` (auto-resolved JS) and `captcha.js` (visible CAPTCHA). The WAF token is cryptographically bound to the browser that solved it — you can't extract and reuse it in a plain HTTP client.

**Solution:** Playwright launches a real Chromium browser. CAPTCHA is solved once manually. The `aws-waf-token` cookie is cached and restored across browser context rotations — no re-solving needed.

---

## Results

| Metric | Value |
| :------ | ----: |
| Success rate | **98%+** |
| Execution time | ~30–45 min (100 books) |
| 202 blocks | **0** |
| Anti-detection layers | 7 |
| Pipeline orchestration | Two-level (categories → products) |
| Adaptive behavior | Dynamic PRODUCT_PER_PAGE ±15%/+10% |

---

## Evolution: V1 → V2 → V3

| | V1 | V2 | **V3 (current)** |
|---|---|---|---|
| HTTP client | curl_cffi generic | `impersonate="chrome120"` | **Real Playwright browser** |
| WAF | Cloudflare (assumed) | Cloudflare (assumed) | **AWS WAF (confirmed)** |
| CAPTCHA | Not handled | Not handled | **Solved once, token cached** |
| Sec-Fetch headers | Static "none" | Dynamic by context | **Automatic (real browser)** |
| Context rotation | Every 50–100 (fixed) | Every 2–4 (random) | **Policy-based (10-15 products)** |
| Delays | 10–20s | 30–55s + jitter | **8–15s + coffee breaks (150-250s)** |
| Block handling | Fixed retry | Fixed wait | **Exponential backoff (45s → 90s → 180s)** |
| 202 rate | 70% | 0% | **0%** |

---

## Architecture: Two-Level ETL Pipeline

The scraper implements a **pluggable ETL architecture** with three layers:

```
┌─────────────────────────────────────────────────────────┐
│         PipelineOrchestrator (Main Orchestrator)        │
├─────────────────────────────────────────────────────────┤
│  Extract (collect_product_links)                        │
│  ↓                                                      │
│  Transform (parse_product)                              │
│  ↓                                                      │
│  Load (CheckpointManager.save_record + CSV append)      │
├─────────────────────────────────────────────────────────┤
│  Policies (pluggable):                                  │
│  • SessionRotationPolicy (10-15 products/session)       │
│  • BlockDetectionPolicy (exponential backoff)           │
│  • DelayPolicy (inter-request + coffee breaks)          │
├─────────────────────────────────────────────────────────┤
│  Strategies (pluggable):                                │
│  • AntiDetectionStrategy (real delays, WAF bypass)      │
│  • NoOpStrategy (instant fixtures for testing)          │
└─────────────────────────────────────────────────────────┘
```

### Key Components

- **PipelineOrchestrator**: Main orchestrator for two-level iteration (categories → products). Handles retry logic, block detection, session rotation, and dynamic adaptation.
- **PipelineConfig**: Dependency injection container. Replaces global settings, enables testability and multi-target scraping.
- **Download Strategies**: Pluggable HTTP handling (real browser vs. test fixtures).
- **Policies**: Reusable, configurable policies for sessions, blocks, and delays.
- **Checkpoint Manager**: Manages CSV state for resume capability and deduplication.
- **CSVSchema**: Validates parsed product data and normalizes fields.

---

## Stack

- **Playwright** — headed Chromium for WAF bypass
- **BeautifulSoup4 + lxml** — HTML parsing (decoupled from HTTP client, fully testable)
- **pytest** — Unit tests with HTML fixtures (integration tests removed for speed)
- **curl-cffi** — HTTP impersonation fallback (reserved for future use)

---

## Quick start

```bash
git clone https://github.com/gaboneumann/buscalibre-web-scraper.git
cd buscalibre-web-scraper

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

pytest tests/ -v   # verify (unit tests only, no network)
python main.py     # run — solve the CAPTCHA when the browser opens
```

**Output**: CSV file with auto-generated name based on category (e.g., `books_arte.csv`).

**Fields**: `title, author, price, stock, page_index, product_url, source, category_url`

---

## Configuration

### Via config/settings.py (default)

```python
DOMAIN_URL = "https://www.buscalibre.cl/"
CATEGORY_URL = "https://www.buscalibre.cl/libros/arte"
PRODUCT_TARGET = 100
DELAY_MIN = 8.0
DELAY_MAX = 15.0
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
  "product_per_page": 50,
  "delay_min": 8.0,
  "delay_max": 15.0,
  "source_name": "buscalibre_cl",
  "output_path": "storage/outputs/books.csv"
}
```

---

## Anti-Detection Features

### 1. **Session Rotation Policy**
- Threshold: 10–15 products per session (randomized)
- On rotation: Wait 10–15 seconds before resuming
- Purpose: Randomize connection fingerprint

### 2. **Block Detection Policy**
- **Exponential backoff**: 45s → 90s → 180s (with ±20% jitter)
- Threshold: 3 consecutive failures → auto-abort
- Purpose: Respect rate limits and gracefully abort when blocked

### 3. **Delay Policy**
- Inter-request: 8–15 seconds (randomized)
- Coffee breaks: Every 10–15 products, sleep 150–250 seconds (2.5–4.2 min)
- Purpose: Human-like behavior, avoid detection

### 4. **Dynamic PRODUCT_PER_PAGE Adaptation**
- On ≥2 blocks per batch: Reduce by 15% (0.85×)
- On ≥10 successes + 0 blocks: Increase by 10% (1.10×)
- Range: 5 (min) to original setting (max)
- Purpose: Self-tune scraping rate based on server response

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
pipeline = SampleArtePipeline(client=client, config=config)
pipeline.run()  # Completes in <5 seconds for testing
```
Instant fixture returns, no network, no delays — ideal for CI/CD and local testing.

---

## Resume & Checkpoint

The scraper resumes from the last saved state:

1. **On startup**, CheckpointManager reads the CSV file
2. **Extracts already-scraped URLs** from the category
3. **Skips duplicates** during iteration
4. **Continues from the next product**

Example:
```
📋 Resuming from checkpoint: 45/100 already scraped.
```

If the scraper crashes after 45 products, restart `python main.py` — it will continue from product #46.

---

## Documentation

Comprehensive docs organized in `docs/`:

- **[docs/README.md](docs/README.md)** — Documentation index
- **[docs/TECHNICAL.md](docs/TECHNICAL.md)** — Full architecture, 7 anti-detection layers, data flow
- **[docs/MIGRATION.md](docs/MIGRATION.md)** — ETL Pipeline Architecture Refactor (Phases 1-6)
- **[docs/PHASE_1_TASKS.md](docs/PHASE_1_TASKS.md)** — Phase 1: Smart Retry & Backoff (task breakdown)

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

**Note**: Integration tests requiring browser navigation were removed for speed (13-05-2026). Unit tests with HTML fixtures validate parser behavior deterministically.

---

## Project Structure

```
buscalibre-web-scraper/
├── main.py                      # Entry point (CLI + config handling)
├── config/
│   ├── settings.py              # Default configuration
│   └── headers.py               # Dynamic request headers (request-type aware)
├── core/
│   ├── client.py                # HTTPClient (Playwright + session rotation)
│   ├── parser.py                # Extract product links from category
│   ├── parser_product.py        # Extract title/author/price/stock
│   └── paginator.py             # Build paginated category URLs
├── pipelines/
│   ├── base_pipeline.py         # Abstract base pipeline class
│   ├── arte_pipeline.py         # BuscaLibre Art Books implementation
│   ├── config.py                # PipelineConfig (dependency injection)
│   ├── schema.py                # CSVSchema + CheckpointManager
│   ├── components.py            # Policies + PipelineOrchestrator
│   └── strategies.py            # DownloadStrategy implementations
├── storage/
│   └── outputs/                 # CSV output directory (auto-created)
├── tests/
│   ├── parsers/                 # Parser unit tests + fixtures
│   ├── pipelines/               # Pipeline tests
│   ├── fixtures/                # HTML test data
│   └── conftest.py              # Pytest configuration
├── docs/
│   ├── README.md                # Documentation index
│   ├── TECHNICAL.md             # Architecture & design
│   ├── MIGRATION.md             # Refactor phases
│   └── PHASE_1_TASKS.md         # Task breakdown
└── requirements.txt             # Dependencies
```

---

## Design Principles

- **Streaming writes over batch**: Each product appended to CSV immediately. On crash, resume from checkpoint.
- **Anti-detection is baked in**: User-Agent fixed to Chrome 120 (matches TLS fingerprint). Dynamic headers per request type. Delays intentionally long.
- **Pluggable architecture**: Strategies for HTTP, policies for behavior, configs for flexibility.
- **Testability**: Decoupled parsers (BeautifulSoup only), fixture-based unit tests, no browser required for tests.
- **No random User-Agent**: Randomization breaks curl_cffi TLS fingerprint matching and will be detected.

---

## Things Claude Should NOT Do

- Do not commit without running `pytest tests/ -m "not network" -v` first
- Do not remove or weaken anti-detection patterns (delays, headers, session rotation, User-Agent)
- Do not change `DELAY_MIN`/`DELAY_MAX` or `PRODUCT_TARGET` without explicit user request
- Do not use Playwright in place of curl_cffi for product detail requests (HTTP impersonation is lighter)
- Do not implement feature flags or backwards-compatibility shims for anti-detection changes

---

**Gabriel Neumann** · [LinkedIn](https://www.linkedin.com/in/gaboneumann/) · [GitHub](https://github.com/gaboneumann)
