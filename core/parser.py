"""
Parser module for extracting product links from category pages.
"""

from bs4 import BeautifulSoup

def parse_product_links(html: str) -> list[str]:
    """
    Extract all product URLs from category listing page HTML.

    Args:
        html: Raw HTML content from category page

    Returns:
        List of unique product URLs found on the page
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    product_links: list[str] = []

    for a in soup.select("div.box-producto > a[href]"):
        href = a.get("href")

        if not href:
            continue

        # CRITICAL FILTER: only real book products (skip categories, filters, etc.)
        if "/libro-" not in href:
            continue

        product_links.append(href)

    # Remove duplicates and return
    return list(set(product_links))
