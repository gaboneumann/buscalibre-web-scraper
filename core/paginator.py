"""
Pagination URL builder for BuscaLibre category pages.
"""

from urllib.parse import urlparse, urlencode, parse_qs, urlunparse


def build_page(base_url: str, page: int) -> str:
    """
    Build paginated URL for BuscaLibre category listing.

    Args:
        base_url: Category URL (e.g., https://www.buscalibre.cl/libros/arte)
        page: Page number (1-based)

    Returns:
        Fully formatted URL with page parameter

    Raises:
        ValueError: If base_url is empty or page < 1
    """
    if not base_url:
        raise ValueError("Base URL cannot be empty.")

    if page < 1:
        raise ValueError("Page number must be >= 1.")

    parsed = urlparse(base_url)
    query_params = parse_qs(parsed.query)

    # BuscaLibre uses 'page' parameter for category and search results
    query_params["page"] = [str(page)]  # parse_qs expects list of strings

    new_query = urlencode(query_params, doseq=True)

    return urlunparse(parsed._replace(query=new_query))