"""Smoke test for the /health endpoint."""

from src.app import app


def test_health_endpoint():
    """Test that /health returns 200 with correct JSON."""
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "policy-rag-app"
