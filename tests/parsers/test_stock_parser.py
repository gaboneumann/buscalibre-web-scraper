from bs4 import BeautifulSoup
from core.parser_product import _parse_stock_quantity


def test_stock_quantity_plural():
    html = '<p class="stock">Quedan 66 unidades</p>'
    soup = BeautifulSoup(html, "lxml")
    assert _parse_stock_quantity(soup) == 66


def test_stock_quantity_singular():
    html = '<p class="stock">Queda 1 unidad</p>'
    soup = BeautifulSoup(html, "lxml")
    assert _parse_stock_quantity(soup) == 1


def test_stock_quantity_case_insensitive():
    html = '<p class="stock">QUEDAN 42 UNIDADES</p>'
    soup = BeautifulSoup(html, "lxml")
    assert _parse_stock_quantity(soup) == 42


def test_stock_quantity_large_number():
    html = '<p class="stock">Quedan 999 unidades</p>'
    soup = BeautifulSoup(html, "lxml")
    assert _parse_stock_quantity(soup) == 999


def test_stock_quantity_missing_element():
    html = '<div class="product">No stock info</div>'
    soup = BeautifulSoup(html, "lxml")
    assert _parse_stock_quantity(soup) == 0


def test_stock_quantity_out_of_stock_marker():
    html = '<div class="sin-stock">Agotado</div><p class="stock">Quedan 5 unidades</p>'
    soup = BeautifulSoup(html, "lxml")
    assert _parse_stock_quantity(soup) == 0


def test_stock_quantity_in_page_body():
    """Fallback: stock text appears somewhere in page, not in p.stock element."""
    html = '''
    <html>
        <body>
            <h1>Francisco Ackermann</h1>
            <p>Quedan 100 unidades disponibles en nuestro almacén</p>
        </body>
    </html>
    '''
    soup = BeautifulSoup(html, "lxml")
    assert _parse_stock_quantity(soup) == 100


def test_stock_quantity_in_div_with_stock_class():
    """Fallback: stock info in div[class*='stock'] instead of p.stock."""
    html = '<div class="product-stock">Quedan 50 unidades</div>'
    soup = BeautifulSoup(html, "lxml")
    assert _parse_stock_quantity(soup) == 50


def test_stock_quantity_multiple_numbers_takes_first_valid():
    """When text contains numbers, regex pattern match takes priority."""
    html = '<div class="info-stock">Código: 12345 | Quedan 75 unidades</div>'
    soup = BeautifulSoup(html, "lxml")
    # Should match "Quedan 75" pattern in fallback search
    assert _parse_stock_quantity(soup) == 75
