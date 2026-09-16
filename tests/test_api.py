from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["total_tickets"] == 500
    assert "llm_provider" in data


def test_api_query_endpoint():
    response = client.post("/api/query", json={"query": "How many tickets are currently open?"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["row_count"] == 1
    assert "111" in data["answer"] or 111 in [r.get("open_tickets_count") for r in data["data"]]


def test_api_anomalies_endpoint():
    response = client.get("/api/anomalies?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total_anomalies"] > 0
    assert len(data["anomalies"]) <= 10


def test_api_kpis_endpoint():
    response = client.get("/api/kpis")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tickets"] == 500
    assert data["resolution_rate_pct"] > 0
