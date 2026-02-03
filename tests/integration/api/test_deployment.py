"""
Deployment API Endpoints Test Suite

Tests for deployment API endpoints.

Reference: API-004 - Test coverage for API endpoints.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.deployment import router
from app.models.deployment import DeploymentInput


class TestDeploymentAPIEndpoints:
    """Test deployment API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_deployment_input(self):
        """Create mock deployment input."""
        return DeploymentInput(
            decision_id=str(uuid4()),
            profile_id=str(uuid4()),
            input_id=str(uuid4()),
            strategy_name="momentum_strategy",
            feasibility_ratio=Decimal("1.1"),
            annual_return_pct=Decimal("15.5"),
            max_drawdown_pct=Decimal("-10.5"),
            sharpe_ratio=Decimal("1.8"),
            win_rate_pct=Decimal("58.0"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("75"),
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=5,
            top_allocation_pct=Decimal("25.0"),
            diversification_ratio=Decimal("0.85"),
            target_annual_return_pct=Decimal("20.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
        )

    @pytest.fixture
    def mock_deployment_decision(self):
        """Create mock deployment decision."""
        decision = MagicMock()
        decision.decision_id = str(uuid4())
        decision.profile_id = str(uuid4())
        decision.strategy_name = "momentum_strategy"
        decision.status = "APPROVED"
        decision.confidence_level = "HIGH"
        decision.overall_score = Decimal("82.5")
        decision.feasibility_score = Decimal("85.0")
        decision.validation_score = Decimal("80.0")
        decision.recommendation_score = Decimal("82.0")
        decision.risk_score = Decimal("75.0")
        decision.capacity_fade_score = Decimal("90.0")
        decision.recommendation_text = "Strategy approved for deployment."
        decision.next_steps = ["Deploy to paper trading", "Monitor performance"]
        decision.success = True

        # Create a mock rationale object
        rationale = MagicMock()
        rationale.feasibility_assessment = "High feasibility"
        rationale.validation_assessment = "Validated successfully"
        rationale.recommendation_assessment = "Strongly recommended"
        rationale.risk_assessment = "Moderate risk"
        rationale.overall_assessment = "Positive"
        rationale.critical_factors = ["High Sharpe ratio", "Low drawdown"]
        rationale.improvement_areas = ["Reduce slippage"]
        decision.rationale = rationale

        return decision

    @pytest.mark.asyncio
    async def test_validate_strategy_success(self, client, mock_deployment_input, mock_deployment_decision):
        """Test validate_strategy returns valid deployment decision."""
        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orch = MagicMock()
            mock_orch.make_decision = AsyncMock(return_value=mock_deployment_decision)
            mock_orchestrator.return_value = mock_orch

            response = client.post(
                "/deployment/validate-strategy",
                json={
                    "decision_id": mock_deployment_input.decision_id,
                    "profile_id": mock_deployment_input.profile_id,
                    "input_id": mock_deployment_input.input_id,
                    "strategy_name": mock_deployment_input.strategy_name,
                    "feasibility_ratio": 1.1,
                    "annual_return_pct": 15.5,
                    "max_drawdown_pct": -10.5,
                    "sharpe_ratio": 1.8,
                    "win_rate_pct": 58.0,
                    "validation_passed": True,
                    "validation_failures": [],
                    "validation_warnings": [],
                    "recommendation_score": 75,
                    "recommendation_status": "STRONG_BUY",
                    "recommendation_confidence": "high",
                    "num_modules": 5,
                    "top_allocation_pct": 25.0,
                    "diversification_ratio": 0.85,
                    "target_annual_return_pct": 20.0,
                    "max_acceptable_drawdown_pct": 25.0,
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["status"] == "APPROVED"
            assert "overall_score" in data
            assert "scores" in data
            assert "rationale" in data

    @pytest.mark.asyncio
    async def test_get_deployment_decision_success(self, client, mock_deployment_decision):
        """Test get_deployment_decision returns decision details."""
        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orch = MagicMock()
            mock_orch.decision_history = [mock_deployment_decision]
            mock_orchestrator.return_value = mock_orch

            response = client.get(f"/deployment/decision/{mock_deployment_decision.decision_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["decision_id"] == mock_deployment_decision.decision_id
            assert data["status"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_get_deployment_decision_not_found(self, client):
        """Test get_deployment_decision returns 404 for non-existent decision."""
        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orch = MagicMock()
            mock_orch.decision_history = []
            mock_orchestrator.return_value = mock_orch

            response = client.get(f"/deployment/decision/{uuid4()}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_deployment_decisions_success(self, client, mock_deployment_decision):
        """Test list_deployment_decisions returns paginated list."""
        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orch = MagicMock()
            mock_orch.decision_history = [mock_deployment_decision] * 15
            mock_orchestrator.return_value = mock_orch

            response = client.get("/deployment/decisions?limit=10&offset=0")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "total" in data
            assert "limit" in data
            assert "offset" in data
            assert "decisions" in data
            assert len(data["decisions"]) == 10

    @pytest.mark.asyncio
    async def test_list_deployment_decisions_with_offset(self, client, mock_deployment_decision):
        """Test list_deployment_decisions respects offset parameter."""
        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orch = MagicMock()
            mock_orch.decision_history = [mock_deployment_decision] * 15
            mock_orchestrator.return_value = mock_orch

            response = client.get("/deployment/decisions?limit=5&offset=10")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["decisions"]) == 5
            assert data["offset"] == 10

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client):
        """Test health_check returns healthy status when all services OK."""
        mock_health = MagicMock()
        mock_health.status = "healthy"
        mock_health.last_check = datetime.utcnow()
        mock_health.response_time_ms = 50
        mock_health.consecutive_failures = 0

        with patch("app.api.deployment.get_health_check_manager") as mock_health_manager:
            mock_manager = MagicMock()
            mock_manager.get_all_health_status.return_value = {
                "service1": mock_health,
                "service2": mock_health,
            }
            mock_manager.get_unhealthy_services.return_value = []
            mock_manager.get_degraded_services.return_value = []
            mock_health_manager.return_value = mock_manager

            response = client.get("/deployment/health")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert "services" in data
            assert "summary" in data

    @pytest.mark.asyncio
    async def test_health_check_degraded(self, client):
        """Test health_check returns degraded status with degraded services."""
        mock_healthy = MagicMock()
        mock_healthy.status = "healthy"
        mock_healthy.last_check = datetime.utcnow()
        mock_healthy.response_time_ms = 50
        mock_healthy.consecutive_failures = 0

        mock_degraded = MagicMock()
        mock_degraded.status = "degraded"
        mock_degraded.last_check = datetime.utcnow()
        mock_degraded.response_time_ms = 500
        mock_degraded.consecutive_failures = 0

        with patch("app.api.deployment.get_health_check_manager") as mock_health_manager:
            mock_manager = MagicMock()
            mock_manager.get_all_health_status.return_value = {
                "service1": mock_healthy,
                "service2": mock_degraded,
            }
            mock_manager.get_unhealthy_services.return_value = []
            mock_manager.get_degraded_services.return_value = ["service2"]
            mock_health_manager.return_value = mock_manager

            response = client.get("/deployment/health")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "degraded"
            assert data["summary"]["degraded_services"] == 1

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client):
        """Test health_check returns unhealthy status with failed services."""
        mock_healthy = MagicMock()
        mock_healthy.status = "healthy"
        mock_healthy.last_check = datetime.utcnow()
        mock_healthy.response_time_ms = 50
        mock_healthy.consecutive_failures = 0

        mock_unhealthy = MagicMock()
        mock_unhealthy.status = "unhealthy"
        mock_unhealthy.last_check = datetime.utcnow()
        mock_unhealthy.response_time_ms = 1000
        mock_unhealthy.consecutive_failures = 3

        with patch("app.api.deployment.get_health_check_manager") as mock_health_manager:
            mock_manager = MagicMock()
            mock_manager.get_all_health_status.return_value = {
                "service1": mock_healthy,
                "service2": mock_unhealthy,
            }
            mock_manager.get_unhealthy_services.return_value = ["service2"]
            mock_manager.get_degraded_services.return_value = []
            mock_health_manager.return_value = mock_manager

            response = client.get("/deployment/health")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["summary"]["unhealthy_services"] == 1

    @pytest.mark.asyncio
    async def test_deployment_status_success(self, client):
        """Test deployment_status returns system status."""
        mock_orch = MagicMock()
        mock_orch.decision_history = []
        # mock_orch is not None by default

        mock_health = MagicMock()
        mock_health.status = "healthy"
        mock_health.last_check = datetime.utcnow()
        mock_health.response_time_ms = 50
        mock_health.consecutive_failures = 0

        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orchestrator.return_value = mock_orch

            with patch("app.api.deployment.get_health_check_manager") as mock_health_manager:
                mock_manager = MagicMock()
                mock_manager.get_all_health_status.return_value = {"service1": mock_health}
                mock_manager.get_unhealthy_services.return_value = []
                mock_manager.get_degraded_services.return_value = []
                mock_health_manager.return_value = mock_manager

                response = client.get("/deployment/status")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "operational"
                assert "orchestrator" in data
                assert "health" in data

    @pytest.mark.asyncio
    async def test_deployment_status_with_decisions(self, client, mock_deployment_decision):
        """Test deployment_status counts decisions correctly."""
        approved_decision = MagicMock()
        approved_decision.status = "APPROVED"
        approved_decision.decision_id = str(uuid4())

        rejected_decision = MagicMock()
        rejected_decision.status = "REJECTED"
        rejected_decision.decision_id = str(uuid4())

        conditional_decision = MagicMock()
        conditional_decision.status = "CONDITIONAL"
        conditional_decision.decision_id = str(uuid4())

        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orch = MagicMock()
            mock_orch.decision_history = [approved_decision, rejected_decision, conditional_decision]
            mock_orchestrator.return_value = mock_orch

            with patch("app.api.deployment.get_health_check_manager") as mock_health_manager:
                mock_manager = MagicMock()
                mock_manager.get_all_health_status.return_value = {}
                mock_manager.get_unhealthy_services.return_value = []
                mock_manager.get_degraded_services.return_value = []
                mock_health_manager.return_value = mock_manager

                response = client.get("/deployment/status")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["orchestrator"]["decisions_approved"] == 1
                assert data["orchestrator"]["decisions_rejected"] == 1
                assert data["orchestrator"]["decisions_conditional"] == 1


class TestErrorHandling:
    """Test error handling in deployment API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_validate_strategy_timeout(self, client):
        """Test validate_strategy handles timeout errors."""
        import asyncio

        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orch = MagicMock()
            mock_orch.make_decision = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_orchestrator.return_value = mock_orch

            response = client.post(
                "/deployment/validate-strategy",
                json={
                    "decision_id": str(uuid4()),
                    "profile_id": str(uuid4()),
                    "input_id": str(uuid4()),
                    "strategy_name": "test_strategy",
                    "feasibility_ratio": 1.0,
                    "annual_return_pct": 10.0,
                },
            )
            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    @pytest.mark.asyncio
    async def test_get_deployment_decision_error(self, client):
        """Test get_deployment_decision handles errors correctly."""
        with patch("app.api.deployment.get_deploy_orchestrator") as mock_orchestrator:
            mock_orch = MagicMock()
            mock_orch.decision_history = []
            # Simulate error during retrieval
            type(mock_orch).decision_history = property(lambda self: [_ for _ in []])
            mock_orchestrator.return_value = mock_orch

            response = client.get(f"/deployment/decision/{uuid4()}")
            assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]

    @pytest.mark.asyncio
    async def test_list_deployment_decisions_invalid_limit(self, client):
        """Test list_deployment_decisions validates limit parameter."""
        response = client.get("/deployment/decisions?limit=150")
        # Should return validation error (422) for limit > 100
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_list_deployment_decisions_invalid_offset(self, client):
        """Test list_deployment_decisions validates offset parameter."""
        response = client.get("/deployment/decisions?offset=-1")
        # Should return validation error (422) for offset < 0
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, client):
        """Test health_check handles errors gracefully."""
        with patch("app.api.deployment.get_health_check_manager") as mock_health_manager:
            mock_manager = MagicMock()
            mock_manager.get_all_health_status.side_effect = Exception("Health check failed")
            mock_health_manager.return_value = mock_manager

            response = client.get("/deployment/health")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "error"
            assert "error" in data
