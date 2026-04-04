from unittest.mock import MagicMock, patch


def test_list_meetings(client):
    with patch("app.lib.db_operations.run_query", return_value=[]):
        resp = client.get("/api/meetings/テスト太郎")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_meetings_with_records(client):
    mock_records = [
        {
            "date": "2025-01-01",
            "title": "初回面談",
            "duration": None,
            "transcript": "テスト文字起こし",
            "note": "メモ",
            "file_path": "/tmp/test.mp3",
            "client_name": "テスト太郎",
        }
    ]
    with patch("app.routers.meetings.run_query", return_value=mock_records):
        resp = client.get("/api/meetings/テスト太郎")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "初回面談"


def test_upload_meeting_unsupported_format(client):
    resp = client.post(
        "/api/meetings/upload",
        data={"client_name": "テスト太郎", "title": "テスト", "note": ""},
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert "Unsupported" in data["message"]
