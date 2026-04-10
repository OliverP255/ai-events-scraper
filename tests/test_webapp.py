from __future__ import annotations

from fastapi.testclient import TestClient


def test_api_without_database_url(monkeypatch):
    monkeypatch.setattr("ai_events.webapp.settings.database_url", lambda: None)
    import ai_events.webapp.db as wdb

    wdb._pool = None

    from ai_events.webapp.app import app

    with TestClient(app) as client:
        r = client.get("/api/events")
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["database_available"] is False

        h = client.get("/api/health")
        assert h.json()["database_configured"] is False
