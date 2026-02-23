from bs4 import BeautifulSoup
from core.parser_product import _parse_author


def test_parse_author_from_product_html():
    html = """
    <html>
        <body>
            <section id="producto">
                <p class="font-weight-light margin-0 font-size-h1">
                    <a href="/libros/autor/courtney-summers">
                        Courtney Summers
                    </a>
                    (Autor)
                </p>
            </section>
        </body>
    </html>
    """

    soup = BeautifulSoup(html, "lxml")

    author = _parse_author(soup)

    assert isinstance(author, str)
    assert author == "Courtney Summers"
