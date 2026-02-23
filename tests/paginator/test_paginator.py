from core.paginator import build_page

def test_build_page_url_appends_page_param():
    url = build_page(
        "https://www.buscalibre.cl/libros/arte",
        2
    )

    assert url == "https://www.buscalibre.cl/libros/arte?page=2"



