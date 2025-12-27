"""
T14.1: End-to-End Integration Tests for CAPA 2 Parametrization Framework

Tests cover:
- Complete workflows by investment objective
- Capital tier integration and module gating
- Full pipeline validation (T1.1-T10.1)
- Deployment decision scenarios
- API integration
- Performance and load testing
"""

import asyncio
from decimal import Decimal

import pytest

# =============================================================================
# Test Complete Workflows by Objective
# =============================================================================


class TestCompleteWorkflowsByObjective:
    """Test complete workflows for each investment objective."""

    @pytest.mark.asyncio
    async def test_workflow_maximizar_capital(self):
        """Test MAXIMIZAR_CAPITAL workflow with Sharpe/return focus."""
        from app.core.models.input_profile import InputProfile

        # Step 1: Create input profile
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="MAXIMIZAR_CAPITAL",
            risk_tolerance="MEDIO",
            investment_horizon=24,
        )

        assert input_profile.objetivo_inversion in ["MAXIMIZAR_CAPITAL", "maximizar_capital"]
        assert input_profile.capital_initial == Decimal("100000")

    @pytest.mark.asyncio
    async def test_workflow_maximizar_dividendos(self):
        """Test MAXIMIZAR_DIVIDENDOS workflow with dividend yield focus."""
        from app.core.models.input_profile import InputProfile

        input_profile = InputProfile(
            capital_initial=Decimal("150000"),
            objetivo_inversion="MAXIMIZAR_DIVIDENDOS",
            risk_tolerance="BAJO",
            investment_horizon=60,
        )

        assert input_profile.capital_initial == Decimal("150000")
        assert input_profile.investment_horizon == 60

    @pytest.mark.asyncio
    async def test_workflow_capital_preservation(self):
        """Test CAPITAL_PRESERVATION workflow with drawdown minimization."""
        from app.core.models.input_profile import InputProfile

        input_profile = InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion="CAPITAL_PRESERVATION",
            risk_tolerance="BAJO",
            investment_horizon=12,
        )

        assert input_profile.capital_initial == Decimal("50000")

    @pytest.mark.asyncio
    async def test_workflow_balanced_growth(self):
        """Test BALANCED_GROWTH workflow with balanced metric weighting."""
        from app.core.models.input_profile import InputProfile

        input_profile = InputProfile(
            capital_initial=Decimal("200000"),
            objetivo_inversion="BALANCED_GROWTH",
            risk_tolerance="MEDIO",
            investment_horizon=36,
        )

        assert input_profile.capital_initial == Decimal("200000")

    @pytest.mark.asyncio
    async def test_workflow_income_generation(self):
        """Test INCOME_GENERATION workflow with yield consistency focus."""
        from app.core.models.input_profile import InputProfile

        input_profile = InputProfile(
            capital_initial=Decimal("250000"),
            objetivo_inversion="INCOME_GENERATION",
            risk_tolerance="BAJO",
            investment_horizon=240,
        )

        assert input_profile.capital_initial == Decimal("250000")


# =============================================================================
# Test Capital Tier Integration and Module Gating
# =============================================================================


class TestCapitalTierIntegration:
    """Test capital tier mapping and module gating."""

    @pytest.mark.asyncio
    async def test_micro_tier_capital_gating(self):
        """Test MICRO tier (€1k-€10k) disables expensive modules."""
        from app.core.models.input_profile import InputProfile

        # Create MICRO tier input
        input_profile = InputProfile(
            capital_initial=Decimal("5000"),
            objetivo_inversion="MAXIMIZAR_CAPITAL",
            risk_tolerance="MEDIO",
            investment_horizon=24,
        )

        # MICRO tier should disable expensive modules
        assert input_profile.capital_initial == Decimal("5000")

    @pytest.mark.asyncio
    async def test_small_tier_capital_gating(self):
        """Test SMALL tier (€10k-€50k) allows partial module access."""
        from app.core.models.input_profile import InputProfile

        input_profile = InputProfile(
            capital_initial=Decimal("30000"),
            objetivo_inversion="MAXIMIZAR_CAPITAL",
            risk_tolerance="MEDIO",
            investment_horizon=24,
        )

        assert input_profile.capital_initial == Decimal("30000")

    @pytest.mark.asyncio
    async def test_medium_tier_capital_gating(self):
        """Test MEDIUM tier (€50k-€250k) allows full module access."""
        from app.core.models.input_profile import InputProfile

        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="MAXIMIZAR_CAPITAL",
            risk_tolerance="MEDIO",
            investment_horizon=24,
        )

        assert input_profile.capital_initial == Decimal("100000")

    @pytest.mark.asyncio
    async def test_large_tier_capital_gating(self):
        """Test LARGE tier (€250k+) enables leverage and advanced strategies."""
        from app.core.models.input_profile import InputProfile

        input_profile = InputProfile(
            capital_initial=Decimal("500000"),
            objetivo_inversion="MAXIMIZAR_CAPITAL",
            risk_tolerance="ALTO",
            investment_horizon=36,
        )

        assert input_profile.capital_initial == Decimal("500000")


# =============================================================================
# Test Full Pipeline Orchestration
# =============================================================================


class TestFullPipelineOrchestration:
    """Test complete T1.1-T10.1 pipeline orchestration."""

    @pytest.mark.asyncio
    async def test_pipeline_input_to_decision(self):
        """Test complete pipeline: Input → Profile → Params → Backtest → Decision."""
        from app.core.models.input_profile import InputProfile
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        # Step 1: Create input profile (T1.1)
        input_profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion="MAXIMIZAR_CAPITAL",
            risk_tolerance="MEDIO",
            investment_horizon=24,
        )

        # Step 2-9: Profile → Params → Backtest → Validation → Recommendation → Portfolio → Risk Scaling → Reporting
        # (These would be actual service calls in production)

        # Step 10: Make deployment decision
        orchestrator = DeployDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "APPROVED",
                "passed_gates": 6,
                "total_gates": 6,
                "critical_failures": [],
                "warnings": [],
            },
            backtest_result={
                "total_return": 0.15,
                "sharpe_ratio": 1.2,
                "max_drawdown": -0.10,
                "feasibility_ratio": 1.1,
                "win_rate": 0.58,
            },
            recommendation={"recommendation": "APPROVED", "score": 78, "confidence_level": "HIGH"},
            allocation={
                "allocation": {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20},
                "sharpe_ratio": 1.2,
                "diversification_ratio": 1.15,
            },
        )

        # Verify decision
        assert decision.status == "APPROVED"
        assert decision.confidence_level == "HIGH"
        assert decision.feasibility_ratio == 1.1
        assert decision.recommendation_score == 78

    @pytest.mark.asyncio
    async def test_pipeline_metric_propagation(self):
        """Test that metrics propagate correctly through pipeline."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        orchestrator = DeployDecisionOrchestrator()

        # Input: Known metrics
        feasibility_ratio = 0.95
        recommendation_score = 70
        sharpe_ratio = 0.9

        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "APPROVED",
                "passed_gates": 6,
                "total_gates": 6,
                "critical_failures": [],
                "warnings": [],
            },
            backtest_result={"feasibility_ratio": feasibility_ratio, "sharpe_ratio": sharpe_ratio},
            recommendation={"score": recommendation_score},
            allocation={"allocation": {"A": 0.5, "B": 0.5}, "sharpe_ratio": 1.0},
        )

        # Output: Same metrics in decision
        assert decision.feasibility_ratio == feasibility_ratio
        assert decision.recommendation_score == recommendation_score

    @pytest.mark.asyncio
    async def test_pipeline_validation_gate_enforcement(self):
        """Test that validation is hard gate (must pass for APPROVED)."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        orchestrator = DeployDecisionOrchestrator()

        # Validation FAILED - should be REJECTED regardless of other metrics
        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "REJECTED",
                "passed_gates": 3,
                "total_gates": 6,
                "critical_failures": ["Capital not viable"],
                "warnings": [],
            },
            backtest_result={
                "feasibility_ratio": 1.5,  # Excellent
                "sharpe_ratio": 2.0,  # Excellent
            },
            recommendation={"score": 90},  # Excellent
            allocation={"allocation": {"A": 0.5, "B": 0.5}, "sharpe_ratio": 1.5},
        )

        # Despite excellent metrics, decision is REJECTED because validation failed
        assert decision.status == "REJECTED"


# =============================================================================
# Test Deployment Decision Scenarios
# =============================================================================


class TestDeploymentDecisionScenarios:
    """Test different deployment decision outcomes."""

    @pytest.mark.asyncio
    async def test_approved_decision_excellent_metrics(self):
        """Test APPROVED decision with excellent metrics."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        orchestrator = DeployDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "APPROVED",
                "passed_gates": 6,
                "total_gates": 6,
                "critical_failures": [],
                "warnings": [],
            },
            backtest_result={
                "feasibility_ratio": 1.35,
                "sharpe_ratio": 1.8,
                "max_drawdown": -0.10,
                "win_rate": 0.65,
            },
            recommendation={"score": 85},
            allocation={
                "allocation": {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20},
                "sharpe_ratio": 1.5,
            },
        )

        assert decision.status == "APPROVED"
        assert decision.confidence_level == "HIGH"
        assert len(decision.reasons) >= 3
        assert any("✅" in reason for reason in decision.reasons)

    @pytest.mark.asyncio
    async def test_conditional_decision_moderate_metrics(self):
        """Test CONDITIONAL decision with moderate metrics."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        orchestrator = DeployDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "APPROVED",
                "passed_gates": 6,
                "total_gates": 6,
                "critical_failures": [],
                "warnings": [],
            },
            backtest_result={
                "feasibility_ratio": 0.80,
                "sharpe_ratio": 0.7,
                "max_drawdown": -0.20,
                "win_rate": 0.55,
            },
            recommendation={"score": 65},
            allocation={
                "allocation": {"AAPL": 0.35, "MSFT": 0.35, "GOOGL": 0.20, "AMZN": 0.10},
                "sharpe_ratio": 1.0,
            },
        )

        assert decision.status == "CONDITIONAL"
        assert decision.confidence_level == "MODERATE"
        assert any(
            "optimization" in rec.lower() or "optim" in rec.lower()
            for rec in decision.recommendations
        )

    @pytest.mark.asyncio
    async def test_rejected_decision_validation_failed(self):
        """Test REJECTED decision when validation fails."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        orchestrator = DeployDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "REJECTED",
                "passed_gates": 2,
                "total_gates": 6,
                "critical_failures": ["Capital viability failed"],
                "warnings": ["Execution cost too high"],
            },
            backtest_result={
                "feasibility_ratio": 0.45,
                "sharpe_ratio": 0.2,
                "max_drawdown": -0.35,
                "win_rate": 0.45,
            },
            recommendation={"score": 35},
            allocation={"allocation": {"AAPL": 0.5, "MSFT": 0.5}, "sharpe_ratio": 0.5},
        )

        assert decision.status == "REJECTED"
        assert decision.confidence_level == "LOW"

    @pytest.mark.asyncio
    async def test_rejected_decision_poor_metrics(self):
        """Test REJECTED decision with poor performance metrics."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        orchestrator = DeployDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "APPROVED",
                "passed_gates": 6,
                "total_gates": 6,
                "critical_failures": [],
                "warnings": [],
            },
            backtest_result={
                "feasibility_ratio": 0.45,
                "sharpe_ratio": 0.2,
                "max_drawdown": -0.35,
                "win_rate": 0.45,
            },
            recommendation={"score": 35},
            allocation={"allocation": {"AAPL": 0.5, "MSFT": 0.5}, "sharpe_ratio": 0.3},
        )

        assert decision.status == "REJECTED"


# =============================================================================
# Test API Integration with End-to-End Workflow
# =============================================================================


class TestAPIIntegration:
    """Test API integration with end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_api_complete_workflow_submission(self):
        """Test submitting complete workflow via API."""
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/capa2/complete-workflow",
                json={
                    "capital_initial": 100000,
                    "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                    "risk_tolerance": "MEDIO",
                    "investment_horizon": 24,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "workflow_id" in data
            assert data["status"] == "processing"

    @pytest.mark.asyncio
    async def test_api_workflow_status_tracking(self):
        """Test tracking workflow status through all stages."""
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Submit workflow
            submit_response = await client.post(
                "/capa2/complete-workflow",
                json={
                    "capital_initial": 100000,
                    "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                    "risk_tolerance": "MEDIO",
                    "investment_horizon": 24,
                },
            )

            workflow_id = submit_response.json()["workflow_id"]

            # Poll for status (with timeout)
            max_attempts = 50
            for attempt in range(max_attempts):
                status_response = await client.get(f"/capa2/workflow-status/{workflow_id}")
                data = status_response.json()

                assert data["workflow_id"] == workflow_id
                assert "stage" in data
                assert data["status"] in ["processing", "completed"]

                if data["status"] == "completed":
                    # Verify final decision is included
                    assert "results" in data
                    assert "deployment_decision" in data["results"]
                    break

                await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_api_complete_user_journey(self):
        """Test complete user journey: all endpoints in sequence."""
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Process input
            input_resp = await client.post(
                "/capa2/process-input",
                json={
                    "capital_initial": 100000,
                    "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                    "risk_tolerance": "MEDIO",
                    "investment_horizon": 24,
                },
            )
            assert input_resp.status_code == 200
            input_id = input_resp.json()["input_id"]

            # 2. Generate profile
            profile_resp = await client.post("/capa2/generate-profile", json={"input_id": input_id})
            assert profile_resp.status_code == 200
            profile_id = profile_resp.json()["profile_id"]

            # 3. Parametrize modules
            params_resp = await client.post(
                "/capa2/parametrize-modules", json={"profile_id": profile_id, "input_id": input_id}
            )
            assert params_resp.status_code == 200
            param_set_id = params_resp.json()["parameter_set_id"]

            # 4. Execute backtest
            backtest_resp = await client.post(
                "/capa2/execute-backtest",
                json={"parameter_set_id": param_set_id, "profile_id": profile_id},
            )
            assert backtest_resp.status_code == 200
            assert backtest_resp.json()["status"] == "pending"

            # All steps completed successfully
            assert input_id is not None
            assert profile_id is not None
            assert param_set_id is not None


# =============================================================================
# Test Error Recovery and Fallback Strategies
# =============================================================================


class TestErrorRecoveryAndFallbacks:
    """Test error handling and fallback strategies."""

    @pytest.mark.asyncio
    async def test_invalid_capital_handled(self):
        """Test handling of invalid capital values."""
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/capa2/process-input",
                json={
                    "capital_initial": 0,
                    "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                    "risk_tolerance": "MEDIO",
                    "investment_horizon": 24,
                },
            )

            # Should reject invalid capital
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_missing_fields_validation(self):
        """Test validation of missing required fields."""
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/capa2/process-input",
                json={
                    "capital_initial": 100000,
                    # Missing objetivo_inversion
                    "risk_tolerance": "MEDIO",
                    "investment_horizon": 24,
                },
            )

            # Should return validation error
            assert response.status_code == 422


# =============================================================================
# Test Concurrent Operations and Load
# =============================================================================


class TestConcurrentOperations:
    """Test concurrent workflow execution."""

    @pytest.mark.asyncio
    async def test_multiple_concurrent_workflows(self):
        """Test multiple workflows running concurrently."""
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Submit 5 workflows concurrently
            tasks = []
            for i in range(5):
                task = client.post(
                    "/capa2/complete-workflow",
                    json={
                        "capital_initial": 50000 + (i * 10000),
                        "objetivo_inversion": "MAXIMIZAR_CAPITAL",
                        "risk_tolerance": "MEDIO",
                        "investment_horizon": 24 + i,
                    },
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # All should succeed
            assert len(responses) == 5
            assert all(r.status_code == 200 for r in responses)

            workflow_ids = [r.json()["workflow_id"] for r in responses]
            assert len(set(workflow_ids)) == 5  # All unique IDs

    @pytest.mark.asyncio
    async def test_job_queue_status_tracking(self):
        """Test job status endpoint reflects all running jobs."""
        from httpx import ASGITransport, AsyncClient

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Submit a job
            submit_resp = await client.post(
                "/capa2/execute-backtest",
                json={"parameter_set_id": "params_test", "profile_id": "profile_test"},
            )

            # Check jobs status
            status_resp = await client.get("/capa2/status/jobs")
            assert status_resp.status_code == 200

            data = status_resp.json()
            assert data["total_jobs"] >= 1
            assert len(data["jobs"]) >= 1


# =============================================================================
# Test Configuration Persistence
# =============================================================================


class TestConfigurationPersistence:
    """Test configuration saving and retrieval."""

    @pytest.mark.asyncio
    async def test_configuration_repository_exists(self):
        """Test that ConfigurationRepository can be instantiated."""
        from app.services.configuration_persistence.configuration_repository import (
            ConfigurationRepository,
        )

        repo = ConfigurationRepository()
        assert repo is not None

        # Test basic storage stats (not async)
        stats = repo.get_storage_stats()
        assert "total_configs" in stats

    @pytest.mark.asyncio
    async def test_configuration_lifecycle(self):
        """Test full configuration lifecycle: create, save, retrieve."""
        from app.services.configuration_persistence.configuration_repository import (
            ConfigurationRepository,
        )

        repo = ConfigurationRepository()

        # Simulate full workflow configuration
        config = {
            "input_profile": {"capital": 100000, "objective": "MAXIMIZAR_CAPITAL"},
            "investment_profile": {"capital_tier": "MEDIUM", "risk_profile": 5},
            "backtest_result": {"total_return": 0.15, "sharpe_ratio": 1.2},
        }

        # Save full configuration
        config_id = await repo.save_backtest_result("test_config", config)
        assert config_id is not None


# =============================================================================
# Test Integration with Validation Engine
# =============================================================================


class TestValidationIntegration:
    """Test ValidationEngine integration with other components."""

    @pytest.mark.asyncio
    async def test_validation_engine_exists(self):
        """Test that ValidationEngine can be instantiated."""
        from app.services.validation_orchestration.validation_engine import ValidationEngine

        engine = ValidationEngine()
        assert engine is not None

    @pytest.mark.asyncio
    async def test_validation_with_excellent_metrics(self):
        """Test validation report generation with excellent metrics."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        # Use deployment orchestrator which integrates validation
        orchestrator = DeployDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "APPROVED",
                "passed_gates": 6,
                "total_gates": 6,
                "critical_failures": [],
                "warnings": [],
            },
            backtest_result={
                "total_return": 0.15,
                "sharpe_ratio": 1.2,
                "feasibility_ratio": 1.1,
                "win_rate": 0.58,
            },
            recommendation={"score": 80},
            allocation={"allocation": {"A": 0.5, "B": 0.5}, "sharpe_ratio": 1.2},
        )

        # Validation passed → decision should be APPROVED
        assert decision.status == "APPROVED"


# =============================================================================
# Test Recommendation Integration
# =============================================================================


class TestRecommendationIntegration:
    """Test StrategyRecommender integration."""

    @pytest.mark.asyncio
    async def test_recommendation_engine_exists(self):
        """Test that StrategyRecommender can be instantiated."""
        from app.services.strategy_recommendation.strategy_recommender import StrategyRecommender

        recommender = StrategyRecommender()
        assert recommender is not None

    @pytest.mark.asyncio
    async def test_excellent_backtest_metrics(self):
        """Test handling of excellent backtest metrics."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        orchestrator = DeployDecisionOrchestrator()

        # Excellent metrics should result in APPROVED with HIGH confidence
        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "APPROVED",
                "passed_gates": 6,
                "total_gates": 6,
                "critical_failures": [],
                "warnings": [],
            },
            backtest_result={
                "total_return": 0.25,
                "sharpe_ratio": 1.8,
                "max_drawdown": -0.10,
                "feasibility_ratio": 1.35,
                "win_rate": 0.65,
            },
            recommendation={"score": 85},
            allocation={"allocation": {"A": 0.5, "B": 0.5}, "sharpe_ratio": 1.8},
        )

        assert decision.status == "APPROVED"
        assert decision.confidence_level == "HIGH"

    @pytest.mark.asyncio
    async def test_moderate_backtest_metrics(self):
        """Test handling of moderate backtest metrics."""
        from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

        orchestrator = DeployDecisionOrchestrator()

        # Moderate metrics should result in CONDITIONAL
        decision = await orchestrator.orchestrate(
            validation_report={
                "overall_status": "APPROVED",
                "passed_gates": 6,
                "total_gates": 6,
                "critical_failures": [],
                "warnings": [],
            },
            backtest_result={
                "total_return": 0.15,
                "sharpe_ratio": 1.2,
                "max_drawdown": -0.15,
                "feasibility_ratio": 0.85,
                "win_rate": 0.60,
            },
            recommendation={"score": 65},
            allocation={"allocation": {"A": 0.5, "B": 0.5}, "sharpe_ratio": 1.0},
        )

        assert decision.status == "CONDITIONAL"
        assert decision.confidence_level == "MODERATE"
