# BuscaLibre Web Scraper

> Python scraper that bypasses **AWS WAF** on BuscaLibre Chile using Playwright. Extracts 100 books with 0 blocks.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Real%20Browser-45ba4b?logo=playwright&logoColor=white)
![AWS WAF](https://img.shields.io/badge/AWS%20WAF-CAPTCHA%20Bypass-FFA500)
![Tests](https://img.shields.io/badge/Tests-9%2B%20passed-brightgreen?logo=pytest&logoColor=white)

---

## The problem it solves

BuscaLibre uses **AWS WAF** with two challenge types: `challenge.js` (auto-resolved JS) and `captcha.js` (visible CAPTCHA). The WAF token is cryptographically bound to the browser that solved it — you can't extract and reuse it in a plain HTTP client.

**Solution:** Playwright launches a real Chromium browser. CAPTCHA is solved once manually. The `aws-waf-token` cookie is cached and restored across browser context rotations — no re-solving needed.

---

## Results

| Metric | Value |
| :------ | ----: |
| Books extracted | 100 |
| Success rate | **98%+** |
| Execution time | ~30–45 min |
| 202 blocks | **0** |
| Tests | 9+ passing |
| Anti-detection layers | 7 |

---

## Evolution: V1 → V2 → V3

| | V1 | V2 | **V3 (current)** |
|---|---|---|---|
| HTTP client | curl_cffi generic | `impersonate="chrome120"` | **Real Playwright browser** |
| WAF | Cloudflare (assumed) | Cloudflare (assumed) | **AWS WAF (confirmed)** |
| CAPTCHA | Not handled | Not handled | **Solved once, token cached** |
| Sec-Fetch headers | Static "none" | Dynamic by context | **Automatic (real browser)** |
| Context rotation | Every 50–100 (fixed) | Every 2–4 (random) | **Context rotates, token persists** |
| Delays | 10–20s | 30–55s + jitter | **8–15s + 6 randomness points** |
| 202 rate | 70% | 0% | **0%** |

---

## Stack

- **Playwright** — headed Chromium for WAF bypass
- **BeautifulSoup4 + lxml** — HTML parsing (decoupled from HTTP client, fully testable)
- **pytest** — TDD, 9+ tests with HTML fixtures

---

## Quick start

```bash
git clone https://github.com/gaboneumann/buscalibre-web-scraper.git
cd buscalibre-web-scraper

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

pytest tests/ -v   # verify
python main.py     # run — solve the CAPTCHA when the browser opens
```

Output: `storage/outputs/books_arte.csv` — fields: `title, author, price, stock, url`

To change category or volume, edit `config/settings.py`.

---

## Deep dive

Architecture, anti-detection layer breakdown, data flow, and configuration reference: **[TECHNICAL.md](TECHNICAL.md)**

---

**Gabriel Neumann** · [LinkedIn](https://www.linkedin.com/in/gaboneumann/) · [GitHub](https://github.com/gaboneumann)
