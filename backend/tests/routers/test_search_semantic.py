"""Integration tests for the POST /api/search/semantic endpoint."""
from unittest.mock import AsyncMock, patch


def test_semantic_search_endpoint(client):
    mock_embedding = [0.1] * 768
    mock_results = [
        {
            "score": 0.95,
            "node": {"note": "パニック時はゆっくり話しかける", "date": "2024-01-01"},
        }
    ]

    with (
        patch(
            "app.routers.search.embed_text",
            new=AsyncMock(return_value=mock_embedding),
        ),
        patch(
            "app.routers.search.semantic_search",
            new=AsyncMock(return_value=mock_results),
        ),
    ):
        resp = client.post(
            "/api/search/semantic",
            json={
                "query": "パニック時の対応",
                "index_name": "support_log_embedding",
                "top_k": 5,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["score"] == 0.95
    assert data[0]["node_label"] == "Support Log"
    assert "note" in data[0]["properties"]


def test_semantic_search_empty_embedding(client):
    """Returns empty list when embed_text fails."""
    with patch(
        "app.routers.search.embed_text",
        new=AsyncMock(return_value=None),
    ):
        resp = client.post(
            "/api/search/semantic",
            json={"query": "test"},
        )

    assert resp.status_code == 200
    assert resp.json() == []


def test_semantic_search_validation_error(client):
    """Returns 422 for invalid request body."""
    resp = client.post("/api/search/semantic", json={})
    assert resp.status_code == 422
