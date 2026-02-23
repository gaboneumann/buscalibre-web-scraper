from pathlib import Path
from core.parser_product import parse_product

HTML_PRODUCT = Path(
    "tests/fixtures/products/elcaminodelartista.html"
).read_text(encoding="utf-8")

def test_parse_product_integration():
    result = parse_product(HTML_PRODUCT)

    assert isinstance(result, dict)

    assert result["title"] == "El camino del artista"
    assert result["author"] == "Julia Cameron"
    assert result["price"] == 18630  # Correct price from the fixture file
    assert result["stock_status"] in {"in_stock", "out_of_stock"}