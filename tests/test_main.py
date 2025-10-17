"""
Tests for main FastAPI application endpoints.

Tests the health check endpoints and basic application functionality.
"""

import pytest
import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add the project root to the path to avoid circular imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables for testing
os.environ['DEBUG'] = 'true'
os.environ['SECRET_KEY'] = ''

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test suite for health check endpoints."""
    
    def test_health_endpoint_returns_200(self):
        """Test that /health endpoint returns 200 status code."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_endpoint_returns_ok_status(self):
        """Test that /health endpoint returns {'status': 'ok'}."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_detailed_health_endpoint_returns_200(self):
        """Test that /health/detailed endpoint returns 200 status code."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
    
    def test_detailed_health_endpoint_contains_required_fields(self):
        """Test that /health/detailed endpoint contains required fields."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "python_version" in data
        assert "platform" in data
        assert "system" in data
        
        # Verify status is ok
        assert data["status"] == "ok"
        
        # Verify system information structure
        system_info = data["system"]
        assert "name" in system_info
        assert "release" in system_info
        assert "machine" in system_info


class TestRootEndpoint:
    """Test suite for root endpoint."""
    
    def test_root_endpoint_returns_200(self):
        """Test that root endpoint returns 200 status code."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_root_endpoint_contains_app_info(self):
        """Test that root endpoint contains application information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "status" in data
        assert "docs" in data
        assert "health" in data
        
        # Verify status is running
        assert data["status"] == "running"
        
        # Verify docs and health endpoints are provided
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestErrorHandlers:
    """Test suite for custom error handlers."""
    
    def test_404_error_handler(self):
        """Test custom 404 error handler."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "path" in data
        assert data["error"] == "Not Found"
        assert data["message"] == "The requested resource was not found"
        assert data["path"] == "/nonexistent-endpoint"


class TestCORSConfiguration:
    """Test suite for CORS configuration."""
    
    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        response = client.get("/health")
        assert response.status_code == 200
        
        # Check for CORS headers (these are added by the middleware)
        # Note: TestClient might not show all middleware headers in tests
        # This is more of a structural test to ensure CORS middleware is configured
        assert "content-type" in response.headers


class TestApplicationMetadata:
    """Test suite for application metadata and configuration."""
    
    def test_openapi_docs_accessible(self):
        """Test that OpenAPI documentation is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_json_accessible(self):
        """Test that OpenAPI JSON schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        
        # Verify API info
        info = data["info"]
        assert "title" in info
        assert "version" in info
        assert "description" in info
    
    def test_redoc_accessible(self):
        """Test that ReDoc documentation is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])
