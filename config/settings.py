# config/settings.py
# Configuration constants for BuscaLibre web scraper
#
# RECOMMENDED: Use PipelineConfig.from_settings(settings) to load these values
# into a PipelineConfig instance rather than importing directly. This enables
# testability, config injection, and download_strategy support.
#
# Example:
#   from config import settings
#   from pipelines.config import PipelineConfig
#   config = PipelineConfig.from_settings(settings)
#   pipeline = CategoryPipeline(client=client, config=config)

DOMAIN_URL = "https://www.buscalibre.cl/"
CATEGORY_URL = "https://www.buscalibre.cl/libros/medicina"

# HTTP request settings
REQUEST_TIMEOUT = 20

# Rate limiting delays (in seconds) - ANTI-DETECTION: DO NOT REDUCE
# - Normal inter-request delay: 4-8 seconds (happy path)
# - Recovery delay after error (202/405): 15-25 seconds (post-error backoff)
# - Coffee breaks every 10-15 products (150-250 seconds)
# These delays are essential to avoid rate-limiting and detection.
DELAY_MIN = 4.0
DELAY_MAX = 8.0
DELAY_RECOVERY_MIN = 15.0
DELAY_RECOVERY_MAX = 25.0

# Scraping volume limits
# Optional stop cap: >0 stops the crawler after this many products; 0 = no cap (crawl until empty page).
PRODUCT_TARGET = 100
PRODUCT_PER_PAGE = 200

# Data export settings
SOURCE_NAME = "buscalibre_cl"
OUTPUT_PATH = "storage/outputs/books_arte.csv"

# Exponential backoff bases (Phase 1: Smart Retry)
BACKOFF_BASE_HTTP = 6  # HTTP retries: 6s → 12s → 24s
BACKOFF_BASE_POLICY = 45  # Block policy: 45s → 90s → 180s
