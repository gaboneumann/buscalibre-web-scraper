from bs4 import BeautifulSoup
from core.parser_product import _parse_stock_status


def test_stock_in_stock():
    html = """
    <div class="opcionPrecio selected">
        <span class="ped">$ 3.500</span>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")

    assert _parse_stock_status(soup) == "in_stock"


def test_stock_out_of_stock():
    html = "<p>Producto agotado</p>"
    soup = BeautifulSoup(html, "lxml")

    assert _parse_stock_status(soup) == "out_of_stock"
