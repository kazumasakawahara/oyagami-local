"""Integration tests for the /api/system endpoints."""


def test_system_status(client):
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ollama_available" in data
    assert "neo4j_available" in data
    assert "loaded_models" in data
