"""
Tests for T4.1: Capacity Fade Validator

Comprehensive tests for:
- HistoricalCapacityAnalyzer
- LiquidityHeadroom
- AlphaDecayEstimator
- CapacityFadeValidator (orchestrator)
"""

import pytest
from decimal import Decimal

from app.services.capacity_fade_validation import (
    CapacityFadeValidator,
    CapacityFadeRequest,
    FeasibilityDecision,
)
from app.services.capacity_fade_validation.analyzers import (
    HistoricalCapacityAnalyzer,
    LiquidityHeadroom,
    AlphaDecayEstimator,
)


class TestHistoricalCapacityAnalyzer:
    """Tests for HistoricalCapacityAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        return HistoricalCapacityAnalyzer()

    def test_analyze_capacity_impact_conservative(self, analyzer):
        """Test capacity impact analysis with conservative settings."""
        result = analyzer.analyze_capacity_impact(
            base_alpha_pct=Decimal("10.0"),
            backtest_capital_usd=Decimal("50000"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            confidence_level="conservative",
        )

        assert result["target_capital"] == Decimal("250000")
        assert result["backtest_to_target_ratio"] == Decimal("5")
        assert result["fade_factor"] == Decimal("0.65")

    def test_analyze_capacity_impact_moderate(self, analyzer):
        """Test with moderate confidence level."""
        result = analyzer.analyze_capacity_impact(
            base_alpha_pct=Decimal("10.0"),
            backtest_capital_usd=Decimal("50000"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            confidence_level="moderate",
        )

        assert result["fade_factor"] == Decimal("0.75")

    def test_analyze_capacity_impact_aggressive(self, analyzer):
        """Test with aggressive confidence level."""
        result = analyzer.analyze_capacity_impact(
            base_alpha_pct=Decimal("10.0"),
            backtest_capital_usd=Decimal("50000"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            confidence_level="aggressive",
        )

        assert result["fade_factor"] == Decimal("0.85")


class TestLiquidityHeadroom:
    """Tests for LiquidityHeadroom."""

    @pytest.fixture
    def calculator(self):
        return LiquidityHeadroom()

    def test_calculate_headroom_sufficient(self, calculator):
        """Test with sufficient liquidity headroom."""
        report = calculator.calculate_headroom(
            position_size_usd=Decimal("100000"),
            daily_volume_usd=Decimal("10000000"),
            max_allowed_pct=Decimal("5.0"),
        )

        assert report.position_size_usd == Decimal("100000")
        assert report.percent_of_volume == Decimal("1.0")
        assert report.headroom_available is True

    def test_calculate_headroom_insufficient(self, calculator):
        """Test with insufficient liquidity headroom."""
        report = calculator.calculate_headroom(
            position_size_usd=Decimal("1000000"),
            daily_volume_usd=Decimal("10000000"),
            max_allowed_pct=Decimal("5.0"),
        )

        assert report.percent_of_volume == Decimal("10.0")
        assert report.headroom_available is False


class TestAlphaDecayEstimator:
    """Tests for AlphaDecayEstimator."""

    @pytest.fixture
    def estimator(self):
        return AlphaDecayEstimator()

    def test_estimate_alpha_sqrt_model(self, estimator):
        """Test alpha decay using sqrt(capacity) model."""
        result = estimator.estimate_alpha_at_scale(
            base_alpha_pct=Decimal("10.0"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("400000"),
            fade_model="sqrt",
            liquidity_penalty_pct=Decimal("0"),
        )

        assert result["capital_scaling_ratio"] == Decimal("4")
        assert result["estimated_alpha_pct"] == Decimal("5.0")
        assert result["model"] == "sqrt(capacity) scaling"

    def test_estimate_alpha_linear_model(self, estimator):
        """Test alpha decay using linear model."""
        result = estimator.estimate_alpha_at_scale(
            base_alpha_pct=Decimal("10.0"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("200000"),
            fade_model="linear",
            liquidity_penalty_pct=Decimal("0"),
        )

        assert result["model"] == "linear decay"
        assert result["estimated_alpha_pct"] < Decimal("10.0")

    def test_calculate_required_alpha_for_monthly_target(self, estimator):
        """Test calculation of required alpha for target monthly return."""
        required = estimator.calculate_required_alpha(
            target_monthly_return_usd=Decimal("800"),
            target_capital_usd=Decimal("250000"),
        )

        assert required == Decimal("3.84")


class TestCapacityFadeValidator:
    """Tests for CapacityFadeValidator orchestrator."""

    @pytest.fixture
    def validator(self):
        return CapacityFadeValidator()

    @pytest.mark.asyncio
    async def test_validate_capacity_feasibility_approved(self, validator):
        """Test validation resulting in APPROVED decision."""
        request = CapacityFadeRequest(
            profile_id="test_profile_1",
            input_id="input_1",
            base_alpha_pct=Decimal("15.0"),
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("3"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            target_monthly_return_usd=Decimal("800"),
            avg_position_size_usd=Decimal("10000"),
            avg_daily_volume_multiplier=Decimal("2.0"),
            fade_model="sqrt",
            confidence_level="conservative",
        )

        response = await validator.validate_capacity_feasibility(request)

        assert response.success is True
        assert response.feasibility_gate.decision == FeasibilityDecision.APPROVED

    @pytest.mark.asyncio
    async def test_validate_capacity_feasibility_rejected(self, validator):
        """Test validation resulting in REJECTED decision."""
        request = CapacityFadeRequest(
            profile_id="test_profile_2",
            input_id="input_2",
            base_alpha_pct=Decimal("2.0"),
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("3"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            target_monthly_return_usd=Decimal("800"),
            avg_position_size_usd=Decimal("10000"),
            avg_daily_volume_multiplier=Decimal("1.0"),
            fade_model="sqrt",
            confidence_level="conservative",
        )

        response = await validator.validate_capacity_feasibility(request)

        assert response.success is True
        assert response.feasibility_gate.decision == FeasibilityDecision.REJECTED
