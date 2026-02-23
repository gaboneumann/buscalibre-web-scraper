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
        Dictionary containing title, author, price, and stock_status
    """
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    return {
        "title": _parse_title(soup),
        "author": _parse_author(soup),
        "price": _parse_price(soup),
        "stock_status": _parse_stock_status(soup)
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

def _parse_stock_status(soup: BeautifulSoup) -> str:
    """
    Determine if product is in stock by checking add-to-cart button.

    Returns: "in_stock" or "out_of_stock"
    """
    # If add-to-cart button exists and is not disabled, product is available
    buy_btn = soup.select_one("#btn-agregar-al-carrito, .btn-comprar, .comprar")
    if buy_btn and "disabled" not in buy_btn.get("class", []):
        return "in_stock"

    # Check for explicit out-of-stock markers
    if soup.select_one(".sin-stock, .agotado"):
        return "out_of_stock"

    # Default: use price as indicator (if price exists, item is available)
    return "in_stock" if _parse_price(soup) else "out_of_stock"