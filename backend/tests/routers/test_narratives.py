"""Integration tests for the /api/narratives endpoints."""


def test_validate_valid_graph(client):
    graph = {
        "nodes": [
            {"temp_id": "c1", "label": "Client", "properties": {"name": "テスト太郎"}},
        ],
        "relationships": [],
    }
    resp = client.post("/api/narratives/validate", json=graph)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True


def test_validate_invalid_label(client):
    graph = {
        "nodes": [{"temp_id": "x1", "label": "FakeLabel", "properties": {"name": "test"}}],
        "relationships": [],
    }
    resp = client.post("/api/narratives/validate", json=graph)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is False
