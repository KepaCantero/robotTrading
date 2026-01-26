"""
Tests for the health check endpoint.

This test module verifies that the /health endpoint properly checks:
- Database connection status
- Broker API connectivity
- Memory usage
- Active position count
"""

import pytest
from fastapi.testclient import TestClient

from app.api.health import router as health_router, HealthChecker
from app.main import app


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_health_endpoint_exists(self, client: TestClient):
        """Test that the health endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # Can be healthy or unhealthy

    def test_health_response_structure(self, client: TestClient):
        """Test that health response has correct structure."""
        response = client.get("/health")
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert "uptime_seconds" in data

        # Verify checks structure
        checks = data["checks"]
        assert "database" in checks
        assert "broker" in checks
        assert "memory" in checks
        assert "positions" in checks

    def test_health_status_values(self, client: TestClient):
        """Test that health status has valid values."""
        response = client.get("/health")
        data = response.json()

        # Overall status should be one of these
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

        # Each check should have a status
        for check_name, check_data in data["checks"].items():
            assert "status" in check_data
            assert check_data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_without_broker(self, client: TestClient):
        """Test health check when broker is not configured."""
        response = client.get("/health")
        data = response.json()

        # Broker check should be degraded when not configured
        broker_check = data["checks"]["broker"]
        assert broker_check["status"] in ["degraded", "unhealthy"]
        assert "not configured" in broker_check["message"].lower() or "error" in broker_check["message"].lower()

    def test_health_check_database(self, client: TestClient):
        """Test that database check works."""
        response = client.get("/health")
        data = response.json()

        db_check = data["checks"]["database"]
        assert "status" in db_check

        # Database should either be healthy or degraded
        assert db_check["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_check_memory(self, client: TestClient):
        """Test that memory check works."""
        response = client.get("/health")
        data = response.json()

        memory_check = data["checks"]["memory"]
        assert "status" in memory_check
        assert memory_check["status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_check_positions(self, client: TestClient):
        """Test that positions check works."""
        response = client.get("/health")
        data = response.json()

        positions_check = data["checks"]["positions"]
        assert "status" in positions_check
        assert "count" in positions_check


@pytest.mark.asyncio
class TestHealthChecker:
    """Test suite for HealthChecker class."""

    async def test_health_checker_creation(self):
        """Test that HealthChecker can be instantiated."""
        checker = HealthChecker()
        assert checker is not None
        assert checker.start_time is not None
        assert checker._db_path is None
        assert checker._broker is None

    async def test_health_checker_set_dependencies(self):
        """Test setting dependencies on HealthChecker."""
        checker = HealthChecker()

        # Set database path
        checker.set_dependencies(db_path="/tmp/test.db")
        assert checker._db_path == "/tmp/test.db"

        # Set broker
        mock_broker = object()
        checker.set_dependencies(broker=mock_broker)
        assert checker._broker is mock_broker

    async def test_health_checker_memory_check(self):
        """Test memory check method."""
        checker = HealthChecker()
        result = checker.check_memory()

        assert "status" in result
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
        assert "memory_mb" in result or "message" in result

    async def test_health_checker_database_check_no_db(self):
        """Test database check when no database configured."""
        checker = HealthChecker()
        result = await checker.check_database()

        assert result["status"] == "degraded"
        assert "not configured" in result["message"].lower()

    async def test_health_checker_broker_check_no_broker(self):
        """Test broker check when no broker configured."""
        checker = HealthChecker()
        result = await checker.check_broker()

        assert result["status"] == "degraded"
        assert "not configured" in result["message"].lower()

    async def test_health_checker_positions_check_no_broker(self):
        """Test positions check when no broker configured."""
        checker = HealthChecker()
        result = await checker.check_positions()

        assert result["status"] == "degraded"
        assert "count" in result
        assert result["count"] == 0

    async def test_health_checker_run_all_checks(self):
        """Test running all health checks."""
        checker = HealthChecker()
        result = await checker.run_all_checks()

        assert "status" in result
        assert "checks" in result
        assert "uptime_seconds" in result

        # Verify all checks are present
        assert "database" in result["checks"]
        assert "broker" in result["checks"]
        assert "memory" in result["checks"]
        assert "positions" in result["checks"]


class TestHealthIntegration:
    """Integration tests for health endpoint."""

    def test_health_http_status_healthy(self, client: TestClient):
        """Test that healthy status returns HTTP 200."""
        response = client.get("/health")

        # If status is healthy or degraded, should return 200
        data = response.json()
        if data["status"] in ["healthy", "degraded"]:
            assert response.status_code == 200

    def test_health_http_status_unhealthy(self, client: TestClient):
        """Test that unhealthy status returns HTTP 503."""
        response = client.get("/health")

        # If status is unhealthy, should return 503
        data = response.json()
        if data["status"] == "unhealthy":
            assert response.status_code == 503

    def test_health_timestamp_format(self, client: TestClient):
        """Test that timestamp is in ISO format."""
        response = client.get("/health")
        data = response.json()

        # Verify timestamp is present and in ISO format
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)

        # Should be parseable as ISO format
        from datetime import datetime
        try:
            datetime.fromisoformat(data["timestamp"])
        except ValueError:
            pytest.fail("Timestamp is not in ISO format")

    def test_health_uptime_positive(self, client: TestClient):
        """Test that uptime is positive."""
        response = client.get("/health")
        data = response.json()

        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0
