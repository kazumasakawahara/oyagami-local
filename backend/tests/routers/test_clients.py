"""Integration tests for the /api/clients endpoints."""


def test_clients_list(client):
    resp = client.get("/api/clients")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_clients_list_with_kana(client):
    resp = client.get("/api/clients?kana_prefix=あ")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
