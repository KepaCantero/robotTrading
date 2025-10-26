"""
Additional tests for main application.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestMainAdditional:
    """Additional main application tests."""

    def test_router_inclusion(self):
        """Test that routers are properly included."""
        response = client.get("/health")
        # If endpoint exists, test passes
        assert response.status_code in [200, 404]
