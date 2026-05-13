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
#   pipeline = SampleArtePipeline(client=client, config=config)

DOMAIN_URL = 'https://www.buscalibre.cl/'
CATEGORY_URL = 'https://www.buscalibre.cl/libros/arte'

# HTTP request settings
REQUEST_TIMEOUT = 20

# Rate limiting delays (in seconds) - ANTI-DETECTION: DO NOT REDUCE
# - Minimum delay between product requests (8-15 seconds)
# - Coffee breaks every 10-15 products (150-250 seconds)
# These delays are essential to avoid rate-limiting and detection.
DELAY_MIN = 8.0
DELAY_MAX = 15.0

# Scraping volume limits
PRODUCT_TARGET = 100
PRODUCT_PER_PAGE = 50

# Data export settings
SOURCE_NAME = "buscalibre_cl"
OUTPUT_PATH = "storage/outputs/books_arte.csv" 