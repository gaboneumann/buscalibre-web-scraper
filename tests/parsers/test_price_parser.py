from bs4 import BeautifulSoup
from core.parser_product import _parse_price


def test_parse_discount_price():
    html = """
    <div class="opcionPrecio selected">
        <div class="colPrecio">
            <span class="pvp">$ 13.990</span>
            <span class="ped">$ 3.500</span>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")

    price = _parse_price(soup)

    assert price == 3500
