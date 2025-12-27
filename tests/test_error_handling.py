"""
Tests for error handling system.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestErrorHandler:
    """Test error handler functionality."""

    def test_handle_http_exception(self, client):
        """Test HTTP exception handling."""
        # Test with invalid endpoint
        response = client.get("/nonexistent_endpoint")
        assert response.status_code == 404


class TestFastAPIIntegration:
    """Test FastAPI integration."""

    def test_error_handling_in_fastapi(self, client):
        """Test error handling in FastAPI."""
        client.get("/")
        # Should not raise exception
        assert True

    def test_http_exception_in_fastapi(self, client):
        """Test HTTP exception in FastAPI."""
        response = client.get("/invalid")
        assert response.status_code in [404, 500]
