from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200 and response.json()["status"] == "ok"


def test_rejects_dates_outside_january_scope():
    with TestClient(app) as client:
        response = client.get("/api/overview?delivery_date=2026-02-01")
    assert response.status_code == 422
