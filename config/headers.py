# Chrome 120 Real Browser Headers (Standard Base Headers)
REAL_BROWSER_HEADERS = {
    "authority": "www.buscalibre.cl",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "es-419,es;q=0.9,en;q=0.8",
    "cache-control": "max-age=0",
    "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# Chrome 120 User-Agent - Fixed to maintain TLS handshake consistency
CHROME_120_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_dynamic_headers(request_type: str = "document"):
    """
    Generate dynamic HTTP headers based on request type context.
    This prevents Cloudflare/Akamai from detecting bot-like patterns.

    request_type options: "home", "category", "product"
    Returns: dict with context-specific sec-fetch headers
    """
    base_headers = REAL_BROWSER_HEADERS.copy()

    # Sec-Fetch headers vary based on navigation context to appear more human-like
    header_configs = {
        "home": {
            "sec-fetch-site": "none",
            "sec-fetch-mode": "navigate",
            "sec-fetch-dest": "document",
            "sec-fetch-user": "?1",
        },
        "category": {
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "navigate",
            "sec-fetch-dest": "document",
            "sec-fetch-user": "?1",
        },
        "product": {
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "navigate",
            "sec-fetch-dest": "document",
            "sec-fetch-user": "?0",  # Different for product detail pages
        }
    }

    config = header_configs.get(request_type, header_configs["home"])
    base_headers.update(config)

    return base_headers