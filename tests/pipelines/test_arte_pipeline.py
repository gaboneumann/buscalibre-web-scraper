from core.client import HTTPClient
from pipelines.arte_pipeline import collect_product_links

def test_collect_product_links_pagination(monkeypatch):
    # --- Mock HTTP ---
    def fake_get(self, url, request_type=None):
        return "<html>mocked html</html>"

    # --- Mock Parser with state ---
    call_count = 0

    def fake_parse_unique_links(html):
        nonlocal call_count
        start_id = call_count * 49
        links = [f"product_{i}" for i in range(start_id, start_id + 49)]
        call_count += 1
        return links

    monkeypatch.setattr("core.client.HTTPClient.get", fake_get)
    monkeypatch.setattr(
        "pipelines.arte_pipeline.parse_product_links",
        fake_parse_unique_links
    )

    monkeypatch.setattr("pipelines.arte_pipeline.PRODUCT_TARGET", 100)
    monkeypatch.setattr("pipelines.arte_pipeline.PRODUCT_PER_PAGE", 49)

    client = HTTPClient()
    result_links = collect_product_links(client)

    assert len(result_links) >= 100
