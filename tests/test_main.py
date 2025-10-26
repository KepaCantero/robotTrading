"""
Tests for main FastAPI application.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint_returns_ok_status(self):
        """Test health endpoint returns OK status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()
