"""Integration tests for the /api/ecomap endpoints."""


def test_list_templates(client):
    resp = client.get("/api/ecomap/templates")
    assert resp.status_code == 200
    assert len(resp.json()) == 4
    ids = [t["id"] for t in resp.json()]
    assert "full_view" in ids
    assert "emergency" in ids


def test_get_ecomap(client):
    resp = client.get("/api/ecomap/テスト?template=full_view")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert data["template"] == "full_view"
    assert data["nodes"][0]["category"] == "client"


def test_get_colors(client):
    resp = client.get("/api/ecomap/colors")
    assert resp.status_code == 200
    colors = resp.json()
    assert "client" in colors
    assert "ngActions" in colors
    assert colors["ngActions"].startswith("#")
