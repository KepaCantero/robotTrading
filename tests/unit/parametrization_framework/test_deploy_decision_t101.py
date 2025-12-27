"""
BATCH G - T10.1: Unit Tests for DeployDecisionOrchestrator (Master Decision Maker)

Tests:
- Deployment decision synthesis from all sources
- Feasibility ratio assessment (APPROVED/CONDITIONAL/REJECTED)
- Validation gate integration
- Recommendation score weighting
- Risk assessment scoring
- Overall score calculation
- Confidence level determination
- Detailed rationale generation
- Edge cases and boundary conditions
- History tracking and status reporting
"""

from decimal import Decimal

import pytest

from app.services.deploy_decision_orchestrator.deploy_decision_orchestrator import (
    DeployDecisionOrchestrator,
    get_deploy_orchestrator,
)
from app.services.deploy_decision_orchestrator.models import DeploymentInput


@pytest.fixture
def orchestrator():
    """Create DeployDecisionOrchestrator instance for tests."""
    return DeployDecisionOrchestrator()


class TestBasicDeploymentDecision:
    """Test basic deployment decision making."""

    @pytest.mark.asyncio
    async def test_approve_strong_strategy(self, orchestrator):
        """Test APPROVED decision for strong strategy."""
        deployment_input = DeploymentInput(
            decision_id="DEC-001",
            profile_id="PROF-001",
            input_id="INPUT-001",
            strategy_name="strong_momentum",
            feasibility_ratio=Decimal("1.35"),  # Well above 1.0
            annual_return_pct=Decimal("18"),
            max_drawdown_pct=Decimal("12"),
            sharpe_ratio=Decimal("1.8"),
            win_rate_pct=Decimal("62"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("82"),
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=3,
            top_allocation_pct=Decimal("35"),
            diversification_ratio=Decimal("1.4"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision is not None
        assert decision.success is True
        assert decision.status == "APPROVED"
        assert decision.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_reject_failed_validation(self, orchestrator):
        """Test REJECTED decision when validation fails."""
        deployment_input = DeploymentInput(
            decision_id="DEC-002",
            profile_id="PROF-002",
            input_id="INPUT-002",
            strategy_name="invalid_strategy",
            feasibility_ratio=Decimal("0.9"),
            annual_return_pct=Decimal("11"),
            max_drawdown_pct=Decimal("18"),
            sharpe_ratio=Decimal("1.0"),
            win_rate_pct=Decimal("50"),
            validation_passed=False,  # Validation failed (hard gate)
            validation_failures=["Capital insufficient for learning modules"],
            validation_warnings=[],
            recommendation_score=Decimal("55"),
            recommendation_status="HOLD",
            recommendation_confidence="medium",
            num_modules=2,
            top_allocation_pct=Decimal("50"),
            diversification_ratio=Decimal("1.0"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.success is True
        assert decision.status == "REJECTED"

    @pytest.mark.asyncio
    async def test_conditional_marginal_feasibility(self, orchestrator):
        """Test CONDITIONAL decision for marginal feasibility."""
        deployment_input = DeploymentInput(
            decision_id="DEC-003",
            profile_id="PROF-003",
            input_id="INPUT-003",
            strategy_name="marginal_strategy",
            feasibility_ratio=Decimal("0.82"),  # Between 0.7 and 1.0
            annual_return_pct=Decimal("9.84"),
            max_drawdown_pct=Decimal("16"),
            sharpe_ratio=Decimal("1.1"),
            win_rate_pct=Decimal("52"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["Low Sharpe ratio"],
            recommendation_score=Decimal("68"),
            recommendation_status="BUY",
            recommendation_confidence="medium",
            num_modules=3,
            top_allocation_pct=Decimal("38"),
            diversification_ratio=Decimal("1.3"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.success is True
        assert decision.status == "CONDITIONAL"


class TestFeasibilityAssessment:
    """Test feasibility ratio assessment."""

    @pytest.mark.asyncio
    async def test_high_feasibility_ratio(self, orchestrator):
        """Test high feasibility ratio (>1.5)."""
        deployment_input = DeploymentInput(
            decision_id="DEC-004",
            profile_id="PROF-004",
            input_id="INPUT-004",
            strategy_name="excellent_feasibility",
            feasibility_ratio=Decimal("1.8"),  # Excellent
            annual_return_pct=Decimal("21.6"),
            max_drawdown_pct=Decimal("10"),
            sharpe_ratio=Decimal("2.2"),
            win_rate_pct=Decimal("65"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("88"),
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=4,
            top_allocation_pct=Decimal("32"),
            diversification_ratio=Decimal("1.5"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.status == "APPROVED"
        assert decision.feasibility_score > Decimal("80")

    @pytest.mark.asyncio
    async def test_low_feasibility_ratio(self, orchestrator):
        """Test low feasibility ratio (<0.7)."""
        deployment_input = DeploymentInput(
            decision_id="DEC-005",
            profile_id="PROF-005",
            input_id="INPUT-005",
            strategy_name="poor_feasibility",
            feasibility_ratio=Decimal("0.5"),  # Below minimum
            annual_return_pct=Decimal("6"),
            max_drawdown_pct=Decimal("22"),
            sharpe_ratio=Decimal("0.7"),
            win_rate_pct=Decimal("45"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["Low Sharpe ratio", "High drawdown"],
            recommendation_score=Decimal("45"),
            recommendation_status="REVIEW",
            recommendation_confidence="low",
            num_modules=2,
            top_allocation_pct=Decimal("55"),
            diversification_ratio=Decimal("0.9"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.status == "REJECTED"


class TestRecommendationWeighting:
    """Test recommendation score weighting."""

    @pytest.mark.asyncio
    async def test_strong_buy_recommendation(self, orchestrator):
        """Test strong buy recommendation weighting."""
        deployment_input = DeploymentInput(
            decision_id="DEC-006",
            profile_id="PROF-006",
            input_id="INPUT-006",
            strategy_name="strong_buy",
            feasibility_ratio=Decimal("1.2"),
            annual_return_pct=Decimal("14.4"),
            max_drawdown_pct=Decimal("14"),
            sharpe_ratio=Decimal("1.6"),
            win_rate_pct=Decimal("58"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("85"),  # Strong recommendation
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=3,
            top_allocation_pct=Decimal("35"),
            diversification_ratio=Decimal("1.3"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.recommendation_score == Decimal("85")

    @pytest.mark.asyncio
    async def test_hold_recommendation(self, orchestrator):
        """Test hold recommendation."""
        deployment_input = DeploymentInput(
            decision_id="DEC-007",
            profile_id="PROF-007",
            input_id="INPUT-007",
            strategy_name="hold",
            feasibility_ratio=Decimal("1.0"),
            annual_return_pct=Decimal("12"),
            max_drawdown_pct=Decimal("18"),
            sharpe_ratio=Decimal("0.95"),
            win_rate_pct=Decimal("50"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["Moderate Sharpe ratio"],
            recommendation_score=Decimal("50"),  # Hold
            recommendation_status="HOLD",
            recommendation_confidence="medium",
            num_modules=3,
            top_allocation_pct=Decimal("40"),
            diversification_ratio=Decimal("1.2"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.status in ["CONDITIONAL", "APPROVED"]


class TestRiskAssessment:
    """Test risk assessment scoring."""

    @pytest.mark.asyncio
    async def test_high_risk_strategy(self, orchestrator):
        """Test high-risk strategy assessment."""
        deployment_input = DeploymentInput(
            decision_id="DEC-008",
            profile_id="PROF-008",
            input_id="INPUT-008",
            strategy_name="high_risk",
            feasibility_ratio=Decimal("1.5"),
            annual_return_pct=Decimal("18"),
            max_drawdown_pct=Decimal("35"),  # Very high drawdown
            sharpe_ratio=Decimal("1.2"),
            win_rate_pct=Decimal("48"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["High drawdown"],
            recommendation_score=Decimal("70"),
            recommendation_status="BUY",
            recommendation_confidence="medium",
            num_modules=2,
            top_allocation_pct=Decimal("60"),  # High concentration
            diversification_ratio=Decimal("0.8"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.risk_score < Decimal("70")  # Risk score should be lower

    @pytest.mark.asyncio
    async def test_low_risk_strategy(self, orchestrator):
        """Test low-risk strategy assessment."""
        deployment_input = DeploymentInput(
            decision_id="DEC-009",
            profile_id="PROF-009",
            input_id="INPUT-009",
            strategy_name="low_risk",
            feasibility_ratio=Decimal("1.1"),
            annual_return_pct=Decimal("13.2"),
            max_drawdown_pct=Decimal("8"),  # Low drawdown
            sharpe_ratio=Decimal("1.8"),
            win_rate_pct=Decimal("60"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("75"),
            recommendation_status="BUY",
            recommendation_confidence="high",
            num_modules=4,
            top_allocation_pct=Decimal("30"),  # Balanced allocation
            diversification_ratio=Decimal("1.4"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.risk_score > Decimal("70")  # Risk score should be higher


class TestConfidenceLevel:
    """Test confidence level determination."""

    @pytest.mark.asyncio
    async def test_high_confidence_decision(self, orchestrator):
        """Test high confidence decision."""
        deployment_input = DeploymentInput(
            decision_id="DEC-010",
            profile_id="PROF-010",
            input_id="INPUT-010",
            strategy_name="high_confidence",
            feasibility_ratio=Decimal("1.5"),  # Strong
            annual_return_pct=Decimal("18"),
            max_drawdown_pct=Decimal("10"),
            sharpe_ratio=Decimal("2.0"),  # Excellent
            win_rate_pct=Decimal("65"),  # High
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("88"),  # High score
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=4,
            top_allocation_pct=Decimal("30"),
            diversification_ratio=Decimal("1.5"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_low_confidence_decision(self, orchestrator):
        """Test low confidence decision."""
        deployment_input = DeploymentInput(
            decision_id="DEC-011",
            profile_id="PROF-011",
            input_id="INPUT-011",
            strategy_name="low_confidence",
            feasibility_ratio=Decimal("0.75"),  # Marginal
            annual_return_pct=Decimal("9"),
            max_drawdown_pct=Decimal("24"),  # High
            sharpe_ratio=Decimal("0.7"),  # Low
            win_rate_pct=Decimal("42"),  # Low
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["Low Sharpe", "High drawdown"],
            recommendation_score=Decimal("48"),  # Low score
            recommendation_status="HOLD",
            recommendation_confidence="low",
            num_modules=2,
            top_allocation_pct=Decimal("55"),
            diversification_ratio=Decimal("0.9"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        assert decision.confidence_level == "low"


class TestOverallScoring:
    """Test overall score calculation."""

    @pytest.mark.asyncio
    async def test_overall_score_calculation(self, orchestrator):
        """Test overall score is calculated correctly."""
        deployment_input = DeploymentInput(
            decision_id="DEC-012",
            profile_id="PROF-012",
            input_id="INPUT-012",
            strategy_name="scoring_test",
            feasibility_ratio=Decimal("1.2"),
            annual_return_pct=Decimal("14.4"),
            max_drawdown_pct=Decimal("14"),
            sharpe_ratio=Decimal("1.5"),
            win_rate_pct=Decimal("58"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("75"),
            recommendation_status="BUY",
            recommendation_confidence="high",
            num_modules=3,
            top_allocation_pct=Decimal("35"),
            diversification_ratio=Decimal("1.3"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        decision = await orchestrator.make_decision(deployment_input)

        # Overall score should be positive
        assert decision.overall_score > Decimal("0")
        assert decision.overall_score <= Decimal("100")


class TestDecisionHistory:
    """Test decision history tracking."""

    @pytest.mark.asyncio
    async def test_decision_history_tracked(self, orchestrator):
        """Test decisions are tracked in history."""
        deployment_input = DeploymentInput(
            decision_id="DEC-013",
            profile_id="PROF-013",
            input_id="INPUT-013",
            strategy_name="history_test",
            feasibility_ratio=Decimal("1.1"),
            annual_return_pct=Decimal("13.2"),
            max_drawdown_pct=Decimal("15"),
            sharpe_ratio=Decimal("1.3"),
            win_rate_pct=Decimal("55"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("70"),
            recommendation_status="BUY",
            recommendation_confidence="medium",
            num_modules=3,
            top_allocation_pct=Decimal("35"),
            diversification_ratio=Decimal("1.3"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        await orchestrator.make_decision(deployment_input)

        history = await orchestrator.get_decision_history()
        assert len(history) > 0
        assert history[-1].decision_id == "DEC-013"


class TestSingletonPattern:
    """Test singleton pattern."""

    def test_singleton_instance(self):
        """Test singleton pattern."""
        instance1 = get_deploy_orchestrator()
        instance2 = get_deploy_orchestrator()

        assert instance1 is instance2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
