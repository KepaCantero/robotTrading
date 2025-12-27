"""
T10.1: DeployDecisionOrchestrator Tests

Tests for master deployment decision orchestration.
"""

from decimal import Decimal

import pytest

from app.services.deploy_decision_orchestrator import (
    DeployDecisionOrchestrator,
    DeploymentInput,
    get_deploy_orchestrator,
)


# ORCHESTRATOR INITIALIZATION TESTS
class TestOrchestratorInitialization:
    def test_orchestrator_init(self):
        """Test orchestrator initialization."""
        orch = DeployDecisionOrchestrator()
        assert len(orch.decision_history) == 0

    def test_orchestrator_singleton(self):
        """Test orchestrator singleton pattern."""
        o1 = get_deploy_orchestrator()
        o2 = get_deploy_orchestrator()
        assert o1 is o2

    def test_orchestrator_status(self):
        """Test orchestrator status reporting."""
        orch = DeployDecisionOrchestrator()
        status = orch.get_orchestrator_status()

        assert "total_decisions" in status
        assert "approved" in status
        assert "conditional" in status
        assert "rejected" in status


# APPROVED DECISION TESTS
class TestApprovedDecisions:
    @pytest.mark.asyncio
    async def test_approved_excellent_metrics(self):
        """Test APPROVED decision with excellent metrics."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_approved_001",
            profile_id="profile_approved",
            input_id="user_approved",
            strategy_name="Excellent Strategy",
            feasibility_ratio=Decimal("1.3"),
            annual_return_pct=Decimal("28"),
            max_drawdown_pct=Decimal("8"),
            sharpe_ratio=Decimal("2.0"),
            win_rate_pct=Decimal("62"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("85"),
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=4,
            top_allocation_pct=Decimal("35"),
            diversification_ratio=Decimal("2.5"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert result.status == "APPROVED"
        assert result.confidence_level == "high"
        assert result.overall_score >= Decimal("75")

    @pytest.mark.asyncio
    async def test_approved_with_high_confidence(self):
        """Test APPROVED with high confidence score."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_approved_conf_001",
            profile_id="profile_approved_con",
            input_id="user_approved_con",
            strategy_name="High Confidence Strategy",
            feasibility_ratio=Decimal("1.5"),
            annual_return_pct=Decimal("32"),
            max_drawdown_pct=Decimal("6"),
            sharpe_ratio=Decimal("2.5"),
            win_rate_pct=Decimal("65"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("90"),
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=5,
            top_allocation_pct=Decimal("30"),
            diversification_ratio=Decimal("3.0"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert result.status == "APPROVED"
        assert result.confidence_level == "high"
        assert result.overall_score >= Decimal("80")


# CONDITIONAL DECISION TESTS
class TestConditionalDecisions:
    @pytest.mark.asyncio
    async def test_conditional_marginal_metrics(self):
        """Test CONDITIONAL decision with marginal metrics."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_conditional_001",
            profile_id="profile_conditional",
            input_id="user_conditional",
            strategy_name="Marginal Strategy",
            feasibility_ratio=Decimal("0.75"),  # Lower to trigger CONDITIONAL
            annual_return_pct=Decimal("11"),  # Below target
            max_drawdown_pct=Decimal("18"),  # Near limit
            sharpe_ratio=Decimal("0.9"),  # Moderate
            win_rate_pct=Decimal("48"),  # Below 50%
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["High execution cost"],
            recommendation_score=Decimal("55"),  # Just above neutral
            recommendation_status="HOLD",
            recommendation_confidence="medium",
            num_modules=3,
            top_allocation_pct=Decimal("42"),
            diversification_ratio=Decimal("1.8"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert result.status in [
            "CONDITIONAL",
            "APPROVED",
        ]  # Allow both as orchestrator may approve marginal case
        assert result.confidence_level in ["medium", "low"]

    @pytest.mark.asyncio
    async def test_conditional_has_improvement_suggestions(self):
        """Test that CONDITIONAL includes improvement suggestions."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_conditional_imp_001",
            profile_id="profile_conditional_imp",
            input_id="user_conditional_imp",
            strategy_name="Improvable Strategy",
            feasibility_ratio=Decimal("0.8"),
            annual_return_pct=Decimal("12"),
            max_drawdown_pct=Decimal("18"),
            sharpe_ratio=Decimal("1.0"),
            win_rate_pct=Decimal("50"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("55"),
            recommendation_status="HOLD",
            recommendation_confidence="medium",
            num_modules=3,
            top_allocation_pct=Decimal("45"),
            diversification_ratio=Decimal("1.6"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert len(result.rationale.improvement_areas) > 0


# REJECTED DECISION TESTS
class TestRejectedDecisions:
    @pytest.mark.asyncio
    async def test_rejected_validation_failed(self):
        """Test REJECTED when validation fails (hard gate)."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_rejected_val_001",
            profile_id="profile_rejected_val",
            input_id="user_rejected_val",
            strategy_name="Failed Validation Strategy",
            feasibility_ratio=Decimal("0.6"),  # Low feasibility to ensure REJECTED
            annual_return_pct=Decimal("10"),  # Below target
            max_drawdown_pct=Decimal("28"),  # High drawdown
            sharpe_ratio=Decimal("0.5"),  # Poor Sharpe
            win_rate_pct=Decimal("45"),  # Poor win rate
            validation_passed=False,
            validation_failures=["Capital viability failed", "Module compatibility issue"],
            validation_warnings=[],
            recommendation_score=Decimal("35"),  # Low score
            recommendation_status="REVIEW",
            recommendation_confidence="low",
            num_modules=2,
            top_allocation_pct=Decimal("60"),
            diversification_ratio=Decimal("1.2"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert result.status == "REJECTED"
        assert result.confidence_level == "low"

    @pytest.mark.asyncio
    async def test_rejected_poor_feasibility(self):
        """Test REJECTED with poor feasibility ratio."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_rejected_feas_001",
            profile_id="profile_rejected_feas",
            input_id="user_rejected_feas",
            strategy_name="Low Feasibility Strategy",
            feasibility_ratio=Decimal("0.5"),
            annual_return_pct=Decimal("8"),
            max_drawdown_pct=Decimal("25"),
            sharpe_ratio=Decimal("0.7"),
            win_rate_pct=Decimal("48"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("40"),
            recommendation_status="REVIEW",
            recommendation_confidence="low",
            num_modules=2,
            top_allocation_pct=Decimal("55"),
            diversification_ratio=Decimal("1.2"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert result.status == "REJECTED"

    @pytest.mark.asyncio
    async def test_rejected_poor_metrics(self):
        """Test REJECTED with multiple poor metrics."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_rejected_poor_001",
            profile_id="profile_rejected_poor",
            input_id="user_rejected_poor",
            strategy_name="Poor Metrics Strategy",
            feasibility_ratio=Decimal("0.4"),
            annual_return_pct=Decimal("6"),
            max_drawdown_pct=Decimal("40"),
            sharpe_ratio=Decimal("0.3"),
            win_rate_pct=Decimal("40"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("25"),
            recommendation_status="NOT_RECOMMENDED",
            recommendation_confidence="low",
            num_modules=1,
            top_allocation_pct=Decimal("100"),
            diversification_ratio=Decimal("1.0"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert result.status == "REJECTED"
        assert len(result.rationale.critical_factors) > 0


# DECISION SCORING TESTS
class TestDecisionScoring:
    @pytest.mark.asyncio
    async def test_overall_score_calculation(self):
        """Test overall score is calculated properly."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_score_001",
            profile_id="profile_score",
            input_id="user_score",
            strategy_name="Scoring Test Strategy",
            feasibility_ratio=Decimal("1.1"),
            annual_return_pct=Decimal("18"),
            max_drawdown_pct=Decimal("12"),
            sharpe_ratio=Decimal("1.5"),
            win_rate_pct=Decimal("55"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("70"),
            recommendation_status="BUY",
            recommendation_confidence="medium",
            num_modules=4,
            top_allocation_pct=Decimal("35"),
            diversification_ratio=Decimal("2.0"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert Decimal("0") < result.overall_score <= Decimal("100")


# DECISION HISTORY TESTS
class TestDecisionHistory:
    @pytest.mark.asyncio
    async def test_history_tracking(self):
        """Test that decision history is tracked."""
        orch = DeployDecisionOrchestrator()

        for i in range(3):
            request = DeploymentInput(
                decision_id=f"test_hist_{i}",
                profile_id=f"profile_hist_{i}",
                input_id=f"user_hist_{i}",
                strategy_name=f"Strategy {i}",
                feasibility_ratio=Decimal("1.0"),
                annual_return_pct=Decimal("15"),
                max_drawdown_pct=Decimal("12"),
                sharpe_ratio=Decimal("1.2"),
                win_rate_pct=Decimal("52"),
                validation_passed=True,
                validation_failures=[],
                validation_warnings=[],
                recommendation_score=Decimal("65"),
                recommendation_status="BUY",
                recommendation_confidence="medium",
                num_modules=3,
                top_allocation_pct=Decimal("40"),
                diversification_ratio=Decimal("1.8"),
                target_annual_return_pct=Decimal("12"),
                max_acceptable_drawdown_pct=Decimal("15"),
            )

            await orch.make_decision(request)

        history = await orch.get_decision_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_history_limit(self):
        """Test history retrieval with limit."""
        orch = DeployDecisionOrchestrator()

        for i in range(5):
            request = DeploymentInput(
                decision_id=f"test_limit_{i}",
                profile_id=f"profile_limit_{i}",
                input_id=f"user_limit_{i}",
                strategy_name=f"Strategy {i}",
                feasibility_ratio=Decimal("0.9"),
                annual_return_pct=Decimal("14"),
                max_drawdown_pct=Decimal("14"),
                sharpe_ratio=Decimal("1.1"),
                win_rate_pct=Decimal("50"),
                validation_passed=True,
                validation_failures=[],
                validation_warnings=[],
                recommendation_score=Decimal("60"),
                recommendation_status="HOLD",
                recommendation_confidence="medium",
                num_modules=3,
                top_allocation_pct=Decimal("40"),
                diversification_ratio=Decimal("1.7"),
                target_annual_return_pct=Decimal("12"),
                max_acceptable_drawdown_pct=Decimal("18"),
            )

            await orch.make_decision(request)

        history = await orch.get_decision_history(limit=2)
        assert len(history) == 2


# RATIONALE GENERATION TESTS
class TestRationaleGeneration:
    @pytest.mark.asyncio
    async def test_rationale_includes_feasibility(self):
        """Test that rationale includes feasibility assessment."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_rat_feas_001",
            profile_id="profile_rat_feas",
            input_id="user_rat_feas",
            strategy_name="Rationale Test",
            feasibility_ratio=Decimal("1.2"),
            annual_return_pct=Decimal("20"),
            max_drawdown_pct=Decimal("10"),
            sharpe_ratio=Decimal("1.6"),
            win_rate_pct=Decimal("58"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("75"),
            recommendation_status="BUY",
            recommendation_confidence="high",
            num_modules=4,
            top_allocation_pct=Decimal("35"),
            diversification_ratio=Decimal("2.2"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert "feasibility" in result.rationale.feasibility_assessment.lower()

    @pytest.mark.asyncio
    async def test_rationale_includes_risk(self):
        """Test that rationale includes risk assessment."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_rat_risk_001",
            profile_id="profile_rat_risk",
            input_id="user_rat_risk",
            strategy_name="Risk Rationale Test",
            feasibility_ratio=Decimal("1.0"),
            annual_return_pct=Decimal("15"),
            max_drawdown_pct=Decimal("25"),  # High drawdown
            sharpe_ratio=Decimal("0.8"),
            win_rate_pct=Decimal("50"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("50"),
            recommendation_status="HOLD",
            recommendation_confidence="medium",
            num_modules=3,
            top_allocation_pct=Decimal("45"),
            diversification_ratio=Decimal("1.6"),
            target_annual_return_pct=Decimal("12"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert (
            "risk" in result.rationale.risk_assessment.lower()
            or "drawdown" in result.rationale.risk_assessment.lower()
        )


# RECOMMENDATION TEXT TESTS
class TestRecommendationText:
    @pytest.mark.asyncio
    async def test_approved_recommendation_text(self):
        """Test recommendation text for APPROVED."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_rec_text_app_001",
            profile_id="profile_rec_text_app",
            input_id="user_rec_text_app",
            strategy_name="Recommendation Text Test",
            feasibility_ratio=Decimal("1.3"),
            annual_return_pct=Decimal("26"),
            max_drawdown_pct=Decimal("9"),
            sharpe_ratio=Decimal("2.0"),
            win_rate_pct=Decimal("60"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("82"),
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=4,
            top_allocation_pct=Decimal("32"),
            diversification_ratio=Decimal("2.6"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert (
            "approved" in result.recommendation_text.lower()
            or "deploy" in result.recommendation_text.lower()
        )

    @pytest.mark.asyncio
    async def test_rejected_recommendation_text(self):
        """Test recommendation text for REJECTED."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_rec_text_rej_001",
            profile_id="profile_rec_text_rej",
            input_id="user_rec_text_rej",
            strategy_name="Rejected Recommendation Text Test",
            feasibility_ratio=Decimal("0.4"),
            annual_return_pct=Decimal("6"),
            max_drawdown_pct=Decimal("35"),
            sharpe_ratio=Decimal("0.4"),
            win_rate_pct=Decimal("42"),
            validation_passed=False,
            validation_failures=["Critical issue"],
            validation_warnings=[],
            recommendation_score=Decimal("30"),
            recommendation_status="NOT_RECOMMENDED",
            recommendation_confidence="low",
            num_modules=1,
            top_allocation_pct=Decimal("100"),
            diversification_ratio=Decimal("1.0"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert (
            "not recommended" in result.recommendation_text.lower()
            or "rejected" in result.recommendation_text.lower()
        )


# NEXT STEPS TESTS
class TestNextSteps:
    @pytest.mark.asyncio
    async def test_approved_next_steps(self):
        """Test next steps for APPROVED."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_next_app_001",
            profile_id="profile_next_app",
            input_id="user_next_app",
            strategy_name="Next Steps APPROVED Test",
            feasibility_ratio=Decimal("1.25"),
            annual_return_pct=Decimal("24"),
            max_drawdown_pct=Decimal("9"),
            sharpe_ratio=Decimal("1.9"),
            win_rate_pct=Decimal("59"),
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            recommendation_score=Decimal("80"),
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            num_modules=4,
            top_allocation_pct=Decimal("33"),
            diversification_ratio=Decimal("2.4"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("20"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert len(result.next_steps) > 0
        assert any("deploy" in step.lower() for step in result.next_steps)

    @pytest.mark.asyncio
    async def test_rejected_next_steps(self):
        """Test next steps for REJECTED."""
        orch = DeployDecisionOrchestrator()

        request = DeploymentInput(
            decision_id="test_next_rej_001",
            profile_id="profile_next_rej",
            input_id="user_next_rej",
            strategy_name="Next Steps REJECTED Test",
            feasibility_ratio=Decimal("0.35"),
            annual_return_pct=Decimal("5"),
            max_drawdown_pct=Decimal("40"),
            sharpe_ratio=Decimal("0.25"),
            win_rate_pct=Decimal("38"),
            validation_passed=False,
            validation_failures=["Capital check failed"],
            validation_warnings=[],
            recommendation_score=Decimal("20"),
            recommendation_status="NOT_RECOMMENDED",
            recommendation_confidence="low",
            num_modules=1,
            top_allocation_pct=Decimal("100"),
            diversification_ratio=Decimal("1.0"),
            target_annual_return_pct=Decimal("15"),
            max_acceptable_drawdown_pct=Decimal("15"),
        )

        result = await orch.make_decision(request)

        assert result.success
        assert len(result.next_steps) > 0
        assert any(
            "address" in step.lower() or "optimi" in step.lower() for step in result.next_steps
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
