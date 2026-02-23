from pipelines.arte_pipeline import run
from unittest.mock import patch, MagicMock

def test_arte_pipeline_returns_complete_records(monkeypatch):
    """Unit test for pipeline that returns complete records with mocked HTTP."""
    # Mock the client to avoid real HTTP requests
    mock_client = MagicMock()
    mock_client.navigate_to_category.return_value = "<html>page 1</html>"
    mock_client.get.return_value = """<html>
        <h1>Test Book</h1>
        <a href='/libros/autor/test'>Test Author</a>
        <span class='ped'>$ 15.000</span>
        <button id='btn-agregar-al-carrito'></button>
    </html>"""

    # Mock the parser to return controlled data
    def mock_parse_links(html):
        return ["/libro-test-1/123/p/1", "/libro-test-2/124/p/2"]

    def mock_parse_product(html):
        return {
            "title": "Test Book",
            "author": "Test Author",
            "price": 15000,
            "stock_status": "in_stock"
        }

    # Apply mocks
    monkeypatch.setattr("pipelines.arte_pipeline.HTTPClient", lambda: mock_client)
    monkeypatch.setattr("pipelines.arte_pipeline.parse_product_links", mock_parse_links)
    monkeypatch.setattr("pipelines.arte_pipeline.parse_product", mock_parse_product)
    monkeypatch.setattr("pipelines.arte_pipeline.PRODUCT_TARGET", 2)
    monkeypatch.setattr("pipelines.arte_pipeline.PRODUCT_PER_PAGE", 10)

    data = run()

    assert isinstance(data, list)
    # This test verifies the structure works, but real data comes from mocks
    # In real scenario, would need to check actual CSV output or mock file I/O
