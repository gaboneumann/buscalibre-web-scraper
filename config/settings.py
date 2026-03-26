# config/settings.py
# Configuration constants for BuscaLibre web scraper

DOMAIN_URL = 'https://www.buscalibre.cl/'
CATEGORY_URL = 'https://www.buscalibre.cl/libros/arte'

# HTTP request settings
REQUEST_TIMEOUT = 10

# Rate limiting delays (in seconds)
DELAY_MIN = 30.0
DELAY_MAX = 55.0

# Scraping volume limits
PRODUCT_TARGET = 100
PRODUCT_PER_PAGE = 50

# Data export settings
SOURCE_NAME = "buscalibre_cl"
OUTPUT_PATH = "storage/outputs/books_arte.csv" 