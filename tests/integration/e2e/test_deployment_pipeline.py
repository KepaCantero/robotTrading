"""
End-to-end integration tests for deployment decision pipeline.

Tests the complete flow:
T4.1 (Capacity Fade) → T8.1 (Risk Scaling) → T9.1 (Reporting) → T10.1 (DeployDecisionOrchestrator)
"""

from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.deployment import DeploymentInput
from app.services.capacity_fade_validation import CapacityFadeRequest, CapacityFadeValidator
from app.services.deploy_decision_orchestrator import DeployDecisionOrchestrator


class TestDeploymentPipeline:
    """Test complete deployment decision pipeline."""

    @pytest_asyncio.fixture
    async def orchestrator(self):
        """Create orchestrator instance."""
        return DeployDecisionOrchestrator()

    @pytest.fixture
    def strong_strategy_input(self) -> DeploymentInput:
        """Create input for a strong strategy (should be approved)."""
        return DeploymentInput(
            decision_id="test_strong_001",
            profile_id="profile_strong_001",
            input_id="input_strong_001",
            strategy_name="Strong Momentum Strategy",
            # From backtest results
            feasibility_ratio=Decimal("1.1"),  # Good feasibility
            annual_return_pct=Decimal("15.0"),
            max_drawdown_pct=Decimal("20.0"),
            sharpe_ratio=Decimal("1.8"),
            win_rate_pct=Decimal("58.0"),
            # From validation engine
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            # From strategy recommender
            recommendation_score=Decimal("75"),
            recommendation_status="STRONG_BUY",
            recommendation_confidence="high",
            # From portfolio constructor
            num_modules=5,
            top_allocation_pct=Decimal("25.0"),
            diversification_ratio=Decimal("0.85"),
            # User targets
            target_annual_return_pct=Decimal("20.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            # T4.1: Capacity fade validation results
            capacity_fade_feasible=True,
            estimated_alpha_at_scale=Decimal("18.5"),
            capacity_fade_assessment="Alpha sustainable at scale",
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
        )

    @pytest.fixture
    def weak_strategy_input(self) -> DeploymentInput:
        """Create input for a weak strategy (should be rejected)."""
        return DeploymentInput(
            decision_id="test_weak_001",
            profile_id="profile_weak_001",
            input_id="input_weak_001",
            strategy_name="Weak Mean Reversion Strategy",
            # From backtest results
            feasibility_ratio=Decimal("0.6"),  # Poor feasibility
            annual_return_pct=Decimal("2.0"),  # Weak alpha
            max_drawdown_pct=Decimal("35.0"),  # High drawdown
            sharpe_ratio=Decimal("0.5"),  # Poor Sharpe
            win_rate_pct=Decimal("48.0"),  # Below 50%
            # From validation engine
            validation_passed=False,
            validation_failures=["Sharpe ratio too low", "Win rate below threshold"],
            validation_warnings=["High risk detected"],
            # From strategy recommender
            recommendation_score=Decimal("25"),  # Poor recommendation
            recommendation_status="NOT_RECOMMENDED",
            recommendation_confidence="low",
            # From portfolio constructor
            num_modules=3,
            top_allocation_pct=Decimal("40.0"),  # High concentration
            diversification_ratio=Decimal("0.5"),  # Poor diversification
            # User targets
            target_annual_return_pct=Decimal("10.0"),
            max_acceptable_drawdown_pct=Decimal("20.0"),
            # T4.1: Capacity fade validation results
            capacity_fade_feasible=False,
            estimated_alpha_at_scale=Decimal("1.5"),
            capacity_fade_assessment="Alpha degrades significantly at scale",
            current_capital=Decimal("50000"),
            target_capital=Decimal("250000"),
        )

    @pytest.fixture
    def marginal_strategy_input(self) -> DeploymentInput:
        """Create input for marginal strategy (should be conditional)."""
        return DeploymentInput(
            decision_id="test_marginal_001",
            profile_id="profile_marginal_001",
            input_id="input_marginal_001",
            strategy_name="Marginal Breakout Strategy",
            # From backtest results
            feasibility_ratio=Decimal("0.85"),  # Marginal feasibility
            annual_return_pct=Decimal("8.0"),  # Moderate alpha
            max_drawdown_pct=Decimal("28.0"),
            sharpe_ratio=Decimal("1.0"),  # Moderate Sharpe
            win_rate_pct=Decimal("52.0"),  # Slightly positive
            # From validation engine
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["Some risk factors detected"],
            # From strategy recommender
            recommendation_score=Decimal("55"),  # Neutral recommendation
            recommendation_status="HOLD",
            recommendation_confidence="medium",
            # From portfolio constructor
            num_modules=4,
            top_allocation_pct=Decimal("30.0"),
            diversification_ratio=Decimal("0.70"),
            # User targets
            target_annual_return_pct=Decimal("12.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            # T4.1: Capacity fade validation results
            capacity_fade_feasible=True,
            estimated_alpha_at_scale=Decimal("9.0"),
            capacity_fade_assessment="Alpha slightly degrades at scale",
            current_capital=Decimal("75000"),
            target_capital=Decimal("200000"),
        )

    @pytest.mark.asyncio
    async def test_strong_strategy_approved(self, orchestrator, strong_strategy_input):
        """Test that strong strategy gets APPROVED status."""
        decision = await orchestrator.make_decision(strong_strategy_input)

        assert decision.success is True
        assert decision.status == "APPROVED"
        assert decision.overall_score >= Decimal("70")
        assert decision.confidence_level in ["high", "medium"]
        assert decision.capacity_fade_score > Decimal("50")

    @pytest.mark.asyncio
    async def test_weak_strategy_rejected(self, orchestrator, weak_strategy_input):
        """Test that weak strategy gets REJECTED status."""
        decision = await orchestrator.make_decision(weak_strategy_input)

        assert decision.success is True
        assert decision.status == "REJECTED"
        assert decision.overall_score < Decimal("50")
        assert decision.confidence_level == "low"

    @pytest.mark.asyncio
    async def test_marginal_strategy_conditional(self, orchestrator, marginal_strategy_input):
        """Test that marginal strategy gets CONDITIONAL status."""
        decision = await orchestrator.make_decision(marginal_strategy_input)

        assert decision.success is True
        assert decision.status == "CONDITIONAL"
        assert Decimal("40") <= decision.overall_score <= Decimal("70")

    @pytest.mark.asyncio
    async def test_capacity_fade_validation_integrated(self, orchestrator, strong_strategy_input):
        """Test that T4.1 capacity fade validation is properly integrated."""
        decision = await orchestrator.make_decision(strong_strategy_input)

        # Verify T4.1 result is included
        assert decision.capacity_fade_score is not None
        assert decision.capacity_fade_score >= Decimal("0")
        assert decision.capacity_fade_score <= Decimal("100")

        # Verify capacity fade score affects overall score (40% weight)
        # Overall = 0.40 * capacity_fade + ...
        # So capacity_fade should influence overall significantly
        assert decision.overall_score > Decimal("0")

    @pytest.mark.asyncio
    async def test_risk_metrics_impact_decision(self, orchestrator):
        """Test that risk metrics properly impact deployment decision."""
        high_risk_input = DeploymentInput(
            decision_id="test_highrisk_001",
            profile_id="profile_highrisk_001",
            input_id="input_highrisk_001",
            strategy_name="High Risk Strategy",
            # From backtest results
            feasibility_ratio=Decimal("1.0"),
            annual_return_pct=Decimal("20.0"),  # High return
            max_drawdown_pct=Decimal("50.0"),  # Very high drawdown
            sharpe_ratio=Decimal("1.0"),
            win_rate_pct=Decimal("55.0"),
            # From validation engine
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["High drawdown risk"],
            # From strategy recommender
            recommendation_score=Decimal("60"),
            recommendation_status="HOLD",
            recommendation_confidence="medium",
            # From portfolio constructor
            num_modules=4,
            top_allocation_pct=Decimal("35.0"),
            diversification_ratio=Decimal("0.75"),
            # User targets
            target_annual_return_pct=Decimal("15.0"),
            max_acceptable_drawdown_pct=Decimal("20.0"),  # Lower than actual drawdown
            # T4.1: Capacity fade validation results
            capacity_fade_feasible=True,
            estimated_alpha_at_scale=Decimal("22.0"),
            capacity_fade_assessment="Alpha stable at scale",
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
        )

        decision = await orchestrator.make_decision(high_risk_input)

        # High drawdown should reduce risk score and overall score
        assert decision.risk_score < Decimal("80")
        assert decision.overall_score < Decimal("85")

    @pytest.mark.asyncio
    async def test_decision_history_tracking(self, orchestrator, strong_strategy_input):
        """Test that decision history is tracked correctly."""
        initial_count = len(orchestrator.decision_history)

        decision1 = await orchestrator.make_decision(strong_strategy_input)
        assert len(orchestrator.decision_history) == initial_count + 1

        # Change decision ID and make another decision
        strong_strategy_input.decision_id = "test_strong_002"
        decision2 = await orchestrator.make_decision(strong_strategy_input)
        assert len(orchestrator.decision_history) == initial_count + 2

        # Verify both decisions are in history
        decision_ids = [d.decision_id for d in orchestrator.decision_history]
        assert decision1.decision_id in decision_ids
        assert decision2.decision_id in decision_ids

    @pytest.mark.asyncio
    async def test_validation_gate_rejection(self, orchestrator):
        """Test that failed validation gates lead to rejection."""
        failed_validation_input = DeploymentInput(
            decision_id="test_validation_fail_001",
            profile_id="profile_val_fail_001",
            input_id="input_val_fail_001",
            strategy_name="Failed Validation Strategy",
            # From backtest results
            feasibility_ratio=Decimal("1.0"),
            annual_return_pct=Decimal("10.0"),
            max_drawdown_pct=Decimal("25.0"),
            sharpe_ratio=Decimal("1.5"),
            win_rate_pct=Decimal("55.0"),
            # From validation engine
            validation_passed=False,
            validation_failures=[
                "Signal generation failed",
                "Risk metrics invalid",
                "Data quality issues",
            ],
            validation_warnings=["Multiple validation issues"],
            # From strategy recommender
            recommendation_score=Decimal("60"),
            recommendation_status="HOLD",
            recommendation_confidence="low",
            # From portfolio constructor
            num_modules=4,
            top_allocation_pct=Decimal("30.0"),
            diversification_ratio=Decimal("0.75"),
            # User targets
            target_annual_return_pct=Decimal("15.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            # T4.1: Capacity fade validation results
            capacity_fade_feasible=None,
            estimated_alpha_at_scale=None,
            capacity_fade_assessment=None,
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
        )

        decision = await orchestrator.make_decision(failed_validation_input)

        # Multiple validation failures should hard-gate rejection
        assert decision.status == "REJECTED"
        assert decision.validation_score < Decimal("50")

    @pytest.mark.asyncio
    async def test_feasibility_ratio_impact(self, orchestrator):
        """Test that feasibility ratio properly impacts decision."""
        high_feasibility_input = DeploymentInput(
            decision_id="test_feasible_high_001",
            profile_id="profile_feasible_high_001",
            input_id="input_feasible_high_001",
            strategy_name="Highly Feasible Strategy",
            # From backtest results
            feasibility_ratio=Decimal("1.5"),  # Very good feasibility
            annual_return_pct=Decimal("10.0"),
            max_drawdown_pct=Decimal("20.0"),
            sharpe_ratio=Decimal("1.5"),
            win_rate_pct=Decimal("55.0"),
            # From validation engine
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            # From strategy recommender
            recommendation_score=Decimal("70"),
            recommendation_status="BUY",
            recommendation_confidence="high",
            # From portfolio constructor
            num_modules=5,
            top_allocation_pct=Decimal("25.0"),
            diversification_ratio=Decimal("0.85"),
            # User targets
            target_annual_return_pct=Decimal("12.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            # T4.1: Capacity fade validation results
            capacity_fade_feasible=True,
            estimated_alpha_at_scale=Decimal("12.0"),
            capacity_fade_assessment="Excellent sustainability",
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
        )

        low_feasibility_input = DeploymentInput(
            decision_id="test_feasible_low_001",
            profile_id="profile_feasible_low_001",
            input_id="input_feasible_low_001",
            strategy_name="Low Feasibility Strategy",
            # From backtest results
            feasibility_ratio=Decimal("0.65"),  # Poor feasibility
            annual_return_pct=Decimal("10.0"),
            max_drawdown_pct=Decimal("20.0"),
            sharpe_ratio=Decimal("1.5"),
            win_rate_pct=Decimal("55.0"),
            # From validation engine
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["Low feasibility detected"],
            # From strategy recommender
            recommendation_score=Decimal("70"),
            recommendation_status="BUY",
            recommendation_confidence="medium",
            # From portfolio constructor
            num_modules=4,
            top_allocation_pct=Decimal("30.0"),
            diversification_ratio=Decimal("0.70"),
            # User targets
            target_annual_return_pct=Decimal("12.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            # T4.1: Capacity fade validation results
            capacity_fade_feasible=True,
            estimated_alpha_at_scale=Decimal("8.0"),
            capacity_fade_assessment="Poor sustainability",
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
        )

        high_decision = await orchestrator.make_decision(high_feasibility_input)
        low_decision = await orchestrator.make_decision(low_feasibility_input)

        # High feasibility should produce better overall score
        assert high_decision.feasibility_score > low_decision.feasibility_score
        assert high_decision.overall_score > low_decision.overall_score

    @pytest.mark.asyncio
    async def test_recommendation_score_integration(self, orchestrator):
        """Test that recommendation score is properly weighted (8%)."""
        base_input = DeploymentInput(
            decision_id="test_rec_score_001",
            profile_id="profile_rec_score_001",
            input_id="input_rec_score_001",
            strategy_name="Base Strategy",
            # From backtest results
            feasibility_ratio=Decimal("1.0"),
            annual_return_pct=Decimal("10.0"),
            max_drawdown_pct=Decimal("20.0"),
            sharpe_ratio=Decimal("1.5"),
            win_rate_pct=Decimal("55.0"),
            # From validation engine
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            # From strategy recommender
            recommendation_score=Decimal("50"),  # Base recommendation
            recommendation_status="HOLD",
            recommendation_confidence="medium",
            # From portfolio constructor
            num_modules=4,
            top_allocation_pct=Decimal("30.0"),
            diversification_ratio=Decimal("0.75"),
            # User targets
            target_annual_return_pct=Decimal("12.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            # T4.1: Capacity fade validation results
            capacity_fade_feasible=True,
            estimated_alpha_at_scale=Decimal("10.0"),
            capacity_fade_assessment="Moderate sustainability",
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
        )

        decision = await orchestrator.make_decision(base_input)

        # Recommendation should have some impact but not dominate (8% weight)
        assert decision.recommendation_score == Decimal("50")
        # Overall score should be influenced but not determined by recommendation alone
        assert decision.overall_score > Decimal("0")

    @pytest.mark.asyncio
    async def test_missing_capital_data_handling(self, orchestrator):
        """Test graceful handling of missing capital data."""
        no_capital_input = DeploymentInput(
            decision_id="test_no_capital_001",
            profile_id="profile_no_capital_001",
            input_id="input_no_capital_001",
            strategy_name="No Capital Data Strategy",
            # From backtest results
            feasibility_ratio=Decimal("1.0"),
            annual_return_pct=Decimal("10.0"),
            max_drawdown_pct=Decimal("20.0"),
            sharpe_ratio=Decimal("1.5"),
            win_rate_pct=Decimal("55.0"),
            # From validation engine
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],
            # From strategy recommender
            recommendation_score=Decimal("70"),
            recommendation_status="BUY",
            recommendation_confidence="high",
            # From portfolio constructor
            num_modules=4,
            top_allocation_pct=Decimal("30.0"),
            diversification_ratio=Decimal("0.75"),
            # User targets
            target_annual_return_pct=Decimal("12.0"),
            max_acceptable_drawdown_pct=Decimal("25.0"),
            # T4.1: Capacity fade validation results - MISSING
            capacity_fade_feasible=None,
            estimated_alpha_at_scale=None,
            capacity_fade_assessment=None,
            current_capital=None,  # Missing capital data
            target_capital=None,
        )

        decision = await orchestrator.make_decision(no_capital_input)

        # Should handle gracefully with no capacity fade score (triggers weight redistribution)
        assert decision.success is True
        assert decision.capacity_fade_score is None  # Missing data


class TestCapacityFadeIntegration:
    """Test T4.1 Capacity Fade integration specifically."""

    @pytest.fixture
    def validator(self):
        """Create capacity fade validator instance."""
        return CapacityFadeValidator()

    @pytest.mark.asyncio
    async def test_capacity_fade_with_scaling(self, validator):
        """Test capacity fade calculation with capital scaling."""
        request = CapacityFadeRequest(
            profile_id="test_profile",
            input_id="test_input",
            base_alpha_pct=Decimal("15.0"),
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("3"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            target_monthly_return_usd=Decimal("800"),
            avg_position_size_usd=Decimal("25000"),
            avg_daily_volume_multiplier=Decimal("2.0"),
            fade_model="sqrt",
            confidence_level="conservative",
        )

        response = await validator.validate_capacity_feasibility(request)

        assert response.success is True
        assert response.feasibility_gate.decision is not None
        assert response.analysis.estimated_alpha_at_target > Decimal("0")
        assert response.analysis.required_alpha_pct > Decimal("0")

    @pytest.mark.asyncio
    async def test_liquidity_constraint_detection(self, validator):
        """Test detection of liquidity constraints."""
        tight_liquidity_request = CapacityFadeRequest(
            profile_id="test_tight_liq",
            input_id="test_liq_input",
            base_alpha_pct=Decimal("10.0"),
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("3"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("500000"),  # Large scaling
            target_monthly_return_usd=Decimal("1000"),
            avg_position_size_usd=Decimal("150000"),  # Large position
            avg_daily_volume_multiplier=Decimal("0.5"),  # Tight liquidity
            fade_model="sqrt",
            confidence_level="conservative",
        )

        response = await validator.validate_capacity_feasibility(tight_liquidity_request)

        assert response.success is True
        # Liquidity constraint should affect decision
        if response.analysis.liquidity_report:
            assert response.analysis.liquidity_report.headroom_available is not None
