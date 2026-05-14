# Migration Guide: ETL Pipeline Architecture Refactor

## Overview

The Buscalibre Web Scraper has been refactored from a monolithic `arte_pipeline.py` into a modular ETL architecture with pluggable policies, configuration injection, and comprehensive testing support. **Backward compatibility is preserved** — existing code continues to work without changes.

## For Existing Users: No Action Required

If you're using the library as-is:

```python
from pipelines.arte_pipeline import run

# This still works unchanged
count = run()
```

The refactor is **100% backward compatible**. Your existing scripts will continue to function without modification.

## Upgrading to the New Architecture

If you want to leverage the new modular design for custom configurations, testing, or multi-target scrapers, follow these steps:

### Step 1: Use PipelineConfig Explicitly

Replace direct imports with configuration-driven setup:

**Before (Old Way):**
```python
from pipelines.arte_pipeline import run

# Hardcoded to config/settings.py
count = run()
```

**After (New Way):**
```python
from pipelines.config import PipelineConfig
from pipelines.arte_pipeline import SampleArtePipeline
from core.client import HTTPClient
from config import settings

# Load from settings (recommended)
config = PipelineConfig.from_settings(settings)
client = HTTPClient(download_strategy=None)  # None = use full anti-detection
pipeline = SampleArtePipeline(client=client, config=config)
count = pipeline.run()
```

### Step 2: Custom Configuration (JSON File)

To use a custom JSON config file:

```bash
python main.py --config /path/to/custom_config.json
```

Or programmatically:

```python
from pipelines.config import PipelineConfig
import json

with open('/path/to/config.json') as f:
    config_dict = json.load(f)
config = PipelineConfig.from_dict(config_dict)

# ... proceed with pipeline
```

**JSON Config Format:**
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

### Step 3: Testing with NoOp Strategy

To test your code without network delays (under 5 seconds):

```python
from pipelines.strategies import NoOpStrategy
from pipelines.config import PipelineConfig
from core.client import HTTPClient
from pipelines.arte_pipeline import SampleArtePipeline

# Use NoOpStrategy for instant test execution
config = PipelineConfig(
    domain_url="https://www.buscalibre.cl/",
    category_url="https://www.buscalibre.cl/libros/arte",
    product_target=10,
    product_per_page=50,
    delay_min=8.0,
    delay_max=15.0,
    source_name="test",
    output_path="test_output.csv",
    download_strategy=NoOpStrategy()  # Instant fixture returns
)

client = HTTPClient(download_strategy=NoOpStrategy())
pipeline = SampleArtePipeline(client=client, config=config)

# Runs in <5 seconds (no real network requests)
count = pipeline.run()
```

### Step 4: Multi-Target Scraping

Scrape multiple categories with shared client:

```python
from pipelines.config import PipelineConfig
from pipelines.arte_pipeline import SampleArtePipeline
from core.client import HTTPClient

client = HTTPClient()  # Shared client, handles session rotation

configs = [
    PipelineConfig.from_dict({
        "category_url": "https://www.buscalibre.cl/libros/arte",
        "output_path": "storage/outputs/arte.csv",
        "product_target": 50,
        ...
    }),
    PipelineConfig.from_dict({
        "category_url": "https://www.buscalibre.cl/libros/ficcion",
        "output_path": "storage/outputs/ficcion.csv",
        "product_target": 50,
        ...
    }),
]

for config in configs:
    pipeline = SampleArtePipeline(client=client, config=config)
    count = pipeline.run()
    print(f"Scraped {count} products")
```

### Step 5: Custom Download Strategy

Implement your own strategy for special handling:

```python
from pipelines.strategies import DownloadStrategy
from pipelines.config import PipelineConfig
from pipelines.arte_pipeline import SampleArtePipeline
from core.client import HTTPClient

class CacheStrategy(DownloadStrategy):
    """Caches responses in memory."""
    def __init__(self):
        self._cache = {}
    
    def download(self, url: str, request_type: str) -> str | None:
        if url in self._cache:
            return self._cache[url]
        # Fetch and cache
        result = None  # Your fetch logic here
        if result:
            self._cache[url] = result
        return result

config = PipelineConfig.from_settings(settings)
client = HTTPClient(download_strategy=CacheStrategy())
pipeline = SampleArtePipeline(client=client, config=config)
count = pipeline.run()
```

## Migration Checklist

- [ ] Existing `from pipelines.arte_pipeline import run` scripts tested and working ✓ (no changes needed)
- [ ] Review new `pipelines/strategies.py` for pluggable download options
- [ ] Consider using `PipelineConfig` for configuration-driven scrapers (recommended for new code)
- [ ] Test with `NoOpStrategy` for rapid iteration (complete pipeline in <5s)
- [ ] If using custom settings, migrate to JSON config file format for portability
- [ ] Update any documentation or runbooks that reference the old architecture

## Key Components

### `pipelines/config.py`
Configuration injection object replaces hardcoded `config/settings.py`. Enables testing and multi-target scraping.

### `pipelines/base_pipeline.py`
Abstract base class for pipeline patterns. `SampleArtePipeline` inherits to implement Buscalibre-specific logic.

### `pipelines/strategies.py`
Download strategy abstraction: `AntiDetectionStrategy` (production), `NoOpStrategy` (testing).

### `pipelines/components.py`
Modular policy objects: `SessionRotationPolicy`, `BlockDetectionPolicy`, `DelayPolicy`, `CheckpointManager`, `CSVSchema`.

### `core/client.py`
Updated to accept optional `download_strategy` for flexible HTTP handling.

### `main.py`
CLI now supports `--config` (JSON file) and `--target` (product count override) arguments.

## Troubleshooting

**Q: My existing script broke**  
A: The refactor is fully backward compatible. Verify you're importing from the same locations as before:
```python
from pipelines.arte_pipeline import run  # Should still work
```

**Q: How do I use the new PipelineConfig?**  
A: See "Step 1: Use PipelineConfig Explicitly" above.

**Q: Can I test without network requests?**  
A: Yes, use `NoOpStrategy` (Step 3). Complete pipeline runs in <5 seconds with fixture HTML.

**Q: How do I configure anti-detection delays?**  
A: Delays are set in `PipelineConfig` (or `config/settings.py` for defaults):
```python
config = PipelineConfig(
    ...,
    delay_min=8.0,       # Minimum 8 seconds between products
    delay_max=15.0,      # Maximum 15 seconds
    ...
)
```

**Q: Can I change the session rotation threshold?**  
A: Session rotation is handled by `SessionRotationPolicy` (2-4 products per session). To customize, use the modular policy system after creating a custom pipeline subclass.

## Anti-Detection Policy Constraints (Non-Negotiable)

The following thresholds are baked into the scraper and should **not be modified** without understanding WAF evasion:

- **Session rotation**: 2–4 products per session
- **Block detection**: 3 consecutive 202/405 failures → auto-stop
- **Inter-request delay**: 8–15 seconds
- **Coffee breaks**: Every 10–15 products, sleep 150–250 seconds
- **User-Agent**: Fixed Chrome 120 (do not randomize; breaks TLS fingerprint matching)

## Questions?

Refer to:
- **[../CLAUDE.md](../CLAUDE.md)** for project constraints and development workflow
- **[TECHNICAL.md](TECHNICAL.md)** for detailed architecture and anti-detection systems
- **[README.md](README.md)** for documentation index
