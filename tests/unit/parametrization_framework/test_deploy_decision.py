"""
T10.1: Unit Tests for DeployDecisionOrchestrator

Tests cover:
- APPROVED decisions (all gates passed, strong metrics)
- CONDITIONAL decisions (passed but needs optimization)
- REJECTED decisions (failed validation or poor metrics)
- Decision matrix logic
- Risk identification
- Recommendations generation
"""

import pytest
from app.services.deployment import (
    DeployDecisionOrchestrator,
)


@pytest.fixture
def orchestrator():
    """Create DeployDecisionOrchestrator instance."""
    return DeployDecisionOrchestrator()


@pytest.fixture
def sample_validation_approved():
    """Sample approved validation report."""
    return {
        "overall_status": "APPROVED",
        "passed_gates": 6,
        "total_gates": 6,
        "critical_failures": [],
        "warnings": [],
    }


@pytest.fixture
def sample_validation_rejected():
    """Sample rejected validation report."""
    return {
        "overall_status": "REJECTED",
        "passed_gates": 4,
        "total_gates": 6,
        "critical_failures": ["Capital viability check failed"],
        "warnings": ["Execution cost too high"],
    }


@pytest.fixture
def sample_backtest_excellent():
    """Excellent backtest results."""
    return {
        "strategy_name": "momentum",
        "total_return": 0.25,
        "sharpe_ratio": 1.8,
        "max_drawdown": -0.10,
        "feasibility_ratio": 1.35,
        "win_rate": 0.65,
    }


@pytest.fixture
def sample_backtest_moderate():
    """Moderate backtest results."""
    return {
        "strategy_name": "mean_reversion",
        "total_return": 0.08,
        "sharpe_ratio": 0.7,
        "max_drawdown": -0.20,
        "feasibility_ratio": 0.80,
        "win_rate": 0.55,
    }


@pytest.fixture
def sample_backtest_poor():
    """Poor backtest results."""
    return {
        "strategy_name": "poor",
        "total_return": 0.02,
        "sharpe_ratio": 0.2,
        "max_drawdown": -0.35,
        "feasibility_ratio": 0.45,
        "win_rate": 0.45,
    }


@pytest.fixture
def sample_recommendation_strong():
    """Strong recommendation."""
    return {
        "recommendation": "APPROVED",
        "score": 85,
        "confidence_level": "HIGH",
    }


@pytest.fixture
def sample_recommendation_moderate():
    """Moderate recommendation."""
    return {
        "recommendation": "CONDITIONAL",
        "score": 65,
        "confidence_level": "MODERATE",
    }


@pytest.fixture
def sample_recommendation_weak():
    """Weak recommendation."""
    return {
        "recommendation": "REJECTED",
        "score": 35,
        "confidence_level": "LOW",
    }


@pytest.fixture
def sample_allocation_good():
    """Good portfolio allocation."""
    return {
        "allocation": {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.20, "AMZN": 0.20},
        "sharpe_ratio": 1.5,
        "diversification_ratio": 1.2,
    }


# =============================================================================
# Test APPROVED Decisions
# =============================================================================

class TestApprovedDecisions:
    """Test APPROVED deployment decisions."""

    @pytest.mark.asyncio
    async def test_approved_excellent_metrics(
        self, orchestrator, sample_validation_approved,
        sample_backtest_excellent, sample_recommendation_strong, sample_allocation_good
    ):
        """Test APPROVED decision with excellent metrics."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_excellent,
            sample_recommendation_strong,
            sample_allocation_good
        )

        assert decision.status == "APPROVED"
        assert decision.confidence_level == "HIGH"
        assert decision.validation_passed is True
        assert decision.feasibility_ratio == 1.35
        assert decision.recommendation_score == 85
        assert len(decision.reasons) > 0
        assert len(decision.next_steps) > 0

    @pytest.mark.asyncio
    async def test_approved_has_reasons(
        self, orchestrator, sample_validation_approved,
        sample_backtest_excellent, sample_recommendation_strong, sample_allocation_good
    ):
        """Test that APPROVED decision includes reasons."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_excellent,
            sample_recommendation_strong,
            sample_allocation_good
        )

        assert any("✅" in reason for reason in decision.reasons)
        assert str(f"{decision.feasibility_ratio:.2f}") in decision.reasons[1]

    @pytest.mark.asyncio
    async def test_approved_has_next_steps(
        self, orchestrator, sample_validation_approved,
        sample_backtest_excellent, sample_recommendation_strong, sample_allocation_good
    ):
        """Test that APPROVED decision includes deployment steps."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_excellent,
            sample_recommendation_strong,
            sample_allocation_good
        )

        assert any("Deploy" in step or "deployment" in step.lower() for step in decision.next_steps)


# =============================================================================
# Test CONDITIONAL Decisions
# =============================================================================

class TestConditionalDecisions:
    """Test CONDITIONAL deployment decisions."""

    @pytest.mark.asyncio
    async def test_conditional_moderate_metrics(
        self, orchestrator, sample_validation_approved,
        sample_backtest_moderate, sample_recommendation_moderate, sample_allocation_good
    ):
        """Test CONDITIONAL decision with moderate metrics."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_moderate,
            sample_recommendation_moderate,
            sample_allocation_good
        )

        assert decision.status == "CONDITIONAL"
        assert decision.confidence_level == "MODERATE"
        assert decision.feasibility_ratio == 0.80
        assert decision.recommendation_score == 65

    @pytest.mark.asyncio
    async def test_conditional_has_optimization_recommendations(
        self, orchestrator, sample_validation_approved,
        sample_backtest_moderate, sample_recommendation_moderate, sample_allocation_good
    ):
        """Test that CONDITIONAL includes optimization recommendations."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_moderate,
            sample_recommendation_moderate,
            sample_allocation_good
        )

        assert any("optimization" in rec.lower() or "optimize" in rec.lower()
                   for rec in decision.recommendations)

    @pytest.mark.asyncio
    async def test_conditional_suggests_testing(
        self, orchestrator, sample_validation_approved,
        sample_backtest_moderate, sample_recommendation_moderate, sample_allocation_good
    ):
        """Test that CONDITIONAL suggests testing."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_moderate,
            sample_recommendation_moderate,
            sample_allocation_good
        )

        assert any("test" in step.lower() or "smaller" in step.lower()
                   for step in decision.next_steps)


# =============================================================================
# Test REJECTED Decisions
# =============================================================================

class TestRejectedDecisions:
    """Test REJECTED deployment decisions."""

    @pytest.mark.asyncio
    async def test_rejected_validation_failed(
        self, orchestrator, sample_validation_rejected,
        sample_backtest_excellent, sample_recommendation_strong, sample_allocation_good
    ):
        """Test REJECTED decision when validation fails (hard gate)."""
        decision = await orchestrator.orchestrate(
            sample_validation_rejected,
            sample_backtest_excellent,
            sample_recommendation_strong,
            sample_allocation_good
        )

        # Should be REJECTED due to failed validation (hard gate)
        assert decision.status == "REJECTED"
        assert decision.confidence_level == "LOW"
        assert decision.validation_passed is False

    @pytest.mark.asyncio
    async def test_rejected_poor_metrics(
        self, orchestrator, sample_validation_approved,
        sample_backtest_poor, sample_recommendation_weak, sample_allocation_good
    ):
        """Test REJECTED decision with poor metrics."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_poor,
            sample_recommendation_weak,
            sample_allocation_good
        )

        assert decision.status == "REJECTED"
        assert decision.feasibility_ratio == 0.45
        assert decision.recommendation_score == 35

    @pytest.mark.asyncio
    async def test_rejected_has_improvement_steps(
        self, orchestrator, sample_validation_approved,
        sample_backtest_poor, sample_recommendation_weak, sample_allocation_good
    ):
        """Test that REJECTED includes improvement steps."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_poor,
            sample_recommendation_weak,
            sample_allocation_good
        )

        assert any("optim" in step.lower() or "review" in step.lower() or "rerun" in step.lower()
                   for step in decision.next_steps)


# =============================================================================
# Test Decision Matrix Logic
# =============================================================================

class TestDecisionMatrix:
    """Test decision matrix thresholds."""

    @pytest.mark.asyncio
    async def test_decision_boundaries_approved(
        self, orchestrator, sample_validation_approved, sample_allocation_good
    ):
        """Test boundary conditions for APPROVED."""
        # Exactly at threshold
        backtest = {
            "sharpe_ratio": 1.0,
            "feasibility_ratio": 1.0,  # Exactly at approved threshold
        }
        recommendation = {"score": 75}  # Exactly at approved threshold

        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            backtest,
            recommendation,
            sample_allocation_good
        )

        assert decision.status == "APPROVED"

    @pytest.mark.asyncio
    async def test_decision_boundaries_conditional(
        self, orchestrator, sample_validation_approved, sample_allocation_good
    ):
        """Test boundary conditions for CONDITIONAL."""
        # At conditional threshold
        backtest = {
            "sharpe_ratio": 0.5,
            "feasibility_ratio": 0.7,  # At conditional threshold
        }
        recommendation = {"score": 60}  # At conditional threshold

        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            backtest,
            recommendation,
            sample_allocation_good
        )

        assert decision.status == "CONDITIONAL"


# =============================================================================
# Test Risk Identification
# =============================================================================

class TestRiskIdentification:
    """Test risk identification."""

    @pytest.mark.asyncio
    async def test_identify_low_feasibility_risk(
        self, orchestrator, sample_validation_approved,
        sample_backtest_poor, sample_recommendation_weak, sample_allocation_good
    ):
        """Test that low feasibility ratio is identified as risk."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_poor,
            sample_recommendation_weak,
            sample_allocation_good
        )

        assert any("feasibility" in risk.lower() for risk in decision.risks)

    @pytest.mark.asyncio
    async def test_identify_poor_sharpe_risk(
        self, orchestrator, sample_validation_approved,
        sample_allocation_good
    ):
        """Test that poor Sharpe ratio is identified as risk."""
        backtest = {
            "sharpe_ratio": 0.1,
            "feasibility_ratio": 0.8,
        }
        recommendation = {"score": 50}

        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            backtest,
            recommendation,
            sample_allocation_good
        )

        assert any("risk-adjusted" in risk.lower() or "volatility" in risk.lower() for risk in decision.risks)

    @pytest.mark.asyncio
    async def test_identify_concentration_risk(
        self, orchestrator, sample_validation_approved,
        sample_backtest_moderate, sample_recommendation_moderate
    ):
        """Test that portfolio concentration is identified as risk."""
        concentrated_allocation = {
            "allocation": {"AAPL": 0.70, "MSFT": 0.20, "GOOGL": 0.10},
            "sharpe_ratio": 1.0,
        }

        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_moderate,
            sample_recommendation_moderate,
            concentrated_allocation
        )

        assert any("concentration" in risk.lower() for risk in decision.risks)


# =============================================================================
# Test Decision Attributes
# =============================================================================

class TestDecisionAttributes:
    """Test that decision has all required attributes."""

    @pytest.mark.asyncio
    async def test_decision_has_all_fields(
        self, orchestrator, sample_validation_approved,
        sample_backtest_excellent, sample_recommendation_strong, sample_allocation_good
    ):
        """Test that decision includes all required fields."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_excellent,
            sample_recommendation_strong,
            sample_allocation_good
        )

        assert hasattr(decision, "status")
        assert hasattr(decision, "decision_id")
        assert hasattr(decision, "confidence_level")
        assert hasattr(decision, "feasibility_ratio")
        assert hasattr(decision, "validation_passed")
        assert hasattr(decision, "recommendation_score")
        assert hasattr(decision, "portfolio_sharpe")
        assert hasattr(decision, "reasons")
        assert hasattr(decision, "risks")
        assert hasattr(decision, "recommendations")
        assert hasattr(decision, "next_steps")

    @pytest.mark.asyncio
    async def test_decision_status_values(
        self, orchestrator, sample_validation_approved,
        sample_backtest_excellent, sample_recommendation_strong, sample_allocation_good
    ):
        """Test that decision status is one of valid values."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_excellent,
            sample_recommendation_strong,
            sample_allocation_good
        )

        assert decision.status in ["APPROVED", "CONDITIONAL", "REJECTED"]
        assert decision.confidence_level in ["HIGH", "MODERATE", "LOW"]


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for orchestrator."""

    @pytest.mark.asyncio
    async def test_full_orchestration_workflow_approved(
        self, orchestrator, sample_validation_approved,
        sample_backtest_excellent, sample_recommendation_strong, sample_allocation_good
    ):
        """Test complete orchestration workflow for APPROVED."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_excellent,
            sample_recommendation_strong,
            sample_allocation_good
        )

        assert decision.status == "APPROVED"
        assert len(decision.reasons) >= 3
        assert len(decision.next_steps) >= 4
        assert decision.decision_id is not None

    @pytest.mark.asyncio
    async def test_full_orchestration_workflow_conditional(
        self, orchestrator, sample_validation_approved,
        sample_backtest_moderate, sample_recommendation_moderate, sample_allocation_good
    ):
        """Test complete orchestration workflow for CONDITIONAL."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_moderate,
            sample_recommendation_moderate,
            sample_allocation_good
        )

        assert decision.status == "CONDITIONAL"
        assert len(decision.risks) >= 0
        assert len(decision.recommendations) >= 1
        assert decision.decision_id is not None

    @pytest.mark.asyncio
    async def test_full_orchestration_workflow_rejected(
        self, orchestrator, sample_validation_approved,
        sample_backtest_poor, sample_recommendation_weak, sample_allocation_good
    ):
        """Test complete orchestration workflow for REJECTED."""
        decision = await orchestrator.orchestrate(
            sample_validation_approved,
            sample_backtest_poor,
            sample_recommendation_weak,
            sample_allocation_good
        )

        assert decision.status == "REJECTED"
        assert any("❌" in reason for reason in decision.reasons)
        assert decision.decision_id is not None
