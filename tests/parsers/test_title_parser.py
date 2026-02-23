from bs4 import BeautifulSoup
from core.parser_product import _parse_title

def test_parse_title_from_product_html():
    html = """
    <html>
        <body>
            <section id="producto">
                <h1>Sadie - Courtney Summers</h1>
            </section>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")

    title = _parse_title(soup)

    assert isinstance(title, str)
    assert title == "Sadie"