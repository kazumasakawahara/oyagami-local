"""Integration tests for the /api/dashboard endpoints."""


def test_stats_endpoint(client):
    resp = client.get("/api/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "client_count" in data
    assert "log_count_this_month" in data
    assert "renewal_alerts" in data


def test_alerts_endpoint(client):
    resp = client.get("/api/dashboard/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_activity_endpoint(client):
    resp = client.get("/api/dashboard/activity")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
