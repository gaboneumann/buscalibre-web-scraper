"""
Parser module for extracting detailed product information from product pages.
Extracts: title, author, price, stock status
"""

from bs4 import BeautifulSoup
from typing import Optional
import re

def parse_product(html: str) -> dict:
    """
    Extract all product data from product detail page HTML.

    Args:
        html: Raw HTML content from product page

    Returns:
        Dictionary containing title, author, price, and stock_quantity
    """
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    return {
        "title": _parse_title(soup),
        "author": _parse_author(soup),
        "price": _parse_price(soup),
        "stock_quantity": _parse_stock_quantity(soup)
    }

def _parse_title(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract book title from H1 tag.
    Removes subtitle (everything after " - ") to get clean title.
    """
    h1 = soup.select_one("h1")
    if not h1:
        return None
    return h1.get_text(strip=True).split(" - ", 1)[0].strip()

def _parse_author(soup: BeautifulSoup) -> str:
    """
    Extract author name from page HTML.
    Uses multiple fallback selectors to handle different page variations.

    Returns author name or "Anonymous" if not found
    """
    # Primary selector: author link in specific format
    author_tag = soup.select_one('a[href*="/libros/autor/"], p.font-size-h1 a.link-underline')

    if author_tag:
        return author_tag.get_text(strip=True)

    # Fallback: any link containing '/autor/' pattern
    fallback = soup.find('a', href=lambda x: x and '/autor/' in x)
    if fallback:
        return fallback.get_text(strip=True)

    return "Anonymous"

def _parse_price(soup: BeautifulSoup) -> Optional[int]:
    """
    Extract book price (in Chilean pesos).
    Looks for discounted price first, then regular price.

    Returns integer price or None if not found
    """
    # Priority: discounted price -> regular price -> other selectors
    # Check for discounted price first
    price_tag = soup.select_one(".opcionPrecio.selected .ped")

    # If no discounted price, check for regular price
    if not price_tag:
        price_tag = soup.select_one(".opcionPrecio.selected .pvp")

    # If still no price, check other selectors
    if not price_tag:
        price_tag = soup.select_one(".precioAhora, #precio-vta")

    if price_tag:
        # Remove all non-digit characters to extract numeric value
        clean_text = re.sub(r"[^\d]", "", price_tag.get_text())
        return int(clean_text) if clean_text else None
    return None

def _parse_stock_quantity(soup: BeautifulSoup) -> int:
    """
    Extract exact stock quantity from product page.

    Searches multiple patterns:
    1. <p class="stock">Quedan N unidades</p> (primary)
    2. Any text containing "Quedan/Queda ... unidad(es)" (fallback)
    3. Any element with class "stock" containing numbers (last resort)

    Returns: Non-negative int (0 if unavailable, unparseable, or out-of-stock marker found)
    """
    # Check for explicit out-of-stock markers first
    if soup.select_one(".sin-stock, .agotado"):
        return 0

    # Strategy 1: Look for <p class="stock"> specifically
    stock_elem = soup.select_one("p.stock")
    if stock_elem:
        stock_text = stock_elem.get_text(strip=True)
        match = re.search(r'(queda|quedan)\s+(\d+)\s+unidad(es)?', stock_text, re.IGNORECASE)
        if match:
            return int(match.group(2))

    # Strategy 2: Search entire page for "Queda/Quedan N unidad(es)" pattern
    page_text = soup.get_text()
    match = re.search(r'(queda|quedan)\s+(\d+)\s+unidad(es)?', page_text, re.IGNORECASE)
    if match:
        return int(match.group(2))

    # Strategy 3: Look for any element with class "stock" and extract numbers
    stock_by_class = soup.select_one("[class*='stock']")
    if stock_by_class:
        stock_text = stock_by_class.get_text(strip=True)
        # Try to find any consecutive digits (fallback when text structure differs)
        numbers = re.findall(r'\d+', stock_text)
        if numbers:
            # Return the first reasonably large number (stock quantities are typically >= 1)
            for num_str in numbers:
                num = int(num_str)
                if num >= 1:
                    return num

    return 0