from core.parser import parse_product_links


def test_parse_product_links_empty_html():
    assert parse_product_links("") == []


def test_parse_product_links_no_products():
    html = """
    <html>
        <body>
            <div>No hay productos aquí</div>
        </body>
    </html>
    """
    result = parse_product_links(html)
    assert result == []


def test_parse_product_links_extracts_links():
    html = """
    <html>
        <body>
            <div class="box-producto">
                <a href="/libro-1/9780001/p/1">Book 1</a>
            </div>
            <div class="box-producto">
                <a href="/libro-2/9780002/p/2">Book 2</a>
            </div>
            <div class="box-producto">
                <a href="/libro-3/9780003/p/3">Book 3</a>
            </div>
        </body>
    </html>
    """

    result = parse_product_links(html)

    # Parser uses set() which removes duplicates but unorders, so check as set
    assert set(result) == {
        "/libro-1/9780001/p/1",
        "/libro-2/9780002/p/2",
        "/libro-3/9780003/p/3",
    }


def test_parse_product_links_ignores_missing_href():
    html = """
    <html>
        <body>
            <div class="box-producto">
                <a>No href</a>
            </div>
            <div class="box-producto">
                <a href="/libro-ok/9780004/p/4">Book OK</a>
            </div>
        </body>
    </html>
    """

    result = parse_product_links(html)

    assert result == ["/libro-ok/9780004/p/4"]
