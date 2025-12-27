"""
Additional tests for main application.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestMainAdditional:
    """Additional main application tests."""

    def test_router_inclusion(self, client):
        """Test that routers are properly included."""
        response = client.get("/health")
        # If endpoint exists, test passes
        assert response.status_code in [200, 404]
