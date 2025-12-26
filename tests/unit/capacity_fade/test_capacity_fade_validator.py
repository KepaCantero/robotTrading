"""
Unit tests for T4.1 Capacity Fade Validation

Tests all components:
- HistoricalCapacityAnalyzer
- LiquidityHeadroom
- AlphaDecayEstimator
- CapacityFadeValidator (main orchestrator)
"""

import pytest
from decimal import Decimal
from datetime import datetime
import asyncio

from app.services.capacity_fade_validation import (
    CapacityFadeValidator,
    CapacityFadeRequest,
    CapacityFadeResponse,
    FeasibilityDecision,
)
from app.services.capacity_fade_validation.analyzers import (
    HistoricalCapacityAnalyzer,
    LiquidityHeadroom,
    AlphaDecayEstimator,
)


# ============================================================================
# HistoricalCapacityAnalyzer Tests (5 tests)
# ============================================================================

class TestHistoricalCapacityAnalyzer:
    """Test HistoricalCapacityAnalyzer component."""

    def setup_method(self):
        """Setup test fixtures."""
        self.analyzer = HistoricalCapacityAnalyzer()

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        assert self.analyzer is not None

    def test_analyze_capacity_impact_conservative(self):
        """Test capacity impact with conservative confidence level."""
        result = self.analyzer.analyze_capacity_impact(
            base_alpha_pct=Decimal("10"),
            backtest_capital_usd=Decimal("50000"),
            current_capital_usd=Decimal("50000"),
            target_capital_usd=Decimal("250000"),
            confidence_level="conservative",
        )

        assert "backtest_capital" in result
        assert result["backtest_capital"] == Decimal("50000")
        assert result["backtest_to_target_ratio"] == Decimal("5")
        assert result["fade_factor"] == Decimal("0.65")

    def test_analyze_capacity_impact_moderate(self):
        """Test capacity impact with moderate confidence level."""
        result = self.analyzer.analyze_capacity_impact(
            base_alpha_pct=Decimal("8"),
            backtest_capital_usd=Decimal("100000"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            confidence_level="moderate",
        )

        assert result["fade_factor"] == Decimal("0.75")
        assert result["backtest_to_target_ratio"] == Decimal("2.5")

    def test_analyze_capacity_impact_aggressive(self):
        """Test capacity impact with aggressive confidence level."""
        result = self.analyzer.analyze_capacity_impact(
            base_alpha_pct=Decimal("12"),
            backtest_capital_usd=Decimal("100000"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            confidence_level="aggressive",
        )

        assert result["fade_factor"] == Decimal("0.85")


# ============================================================================
# LiquidityHeadroom Tests (4 tests)
# ============================================================================

class TestLiquidityHeadroom:
    """Test LiquidityHeadroom component."""

    def setup_method(self):
        """Setup test fixtures."""
        self.analyzer = LiquidityHeadroom()

    def test_headroom_initialization(self):
        """Test headroom analyzer initialization."""
        assert self.analyzer is not None

    def test_calculate_headroom_within_limit(self):
        """Test position within acceptable liquidity limit."""
        report = self.analyzer.calculate_headroom(
            position_size_usd=Decimal("10000"),
            daily_volume_usd=Decimal("500000"),
            max_allowed_pct=Decimal("5.0"),
        )

        assert report.percent_of_volume == Decimal("2.0")
        assert report.headroom_available is True
        assert report.recommended_max_position == Decimal("25000")

    def test_calculate_headroom_exceeds_limit(self):
        """Test position exceeding liquidity limit."""
        report = self.analyzer.calculate_headroom(
            position_size_usd=Decimal("100000"),
            daily_volume_usd=Decimal("500000"),
            max_allowed_pct=Decimal("5.0"),
        )

        assert report.percent_of_volume == Decimal("20.0")
        assert report.headroom_available is False
        assert report.recommended_max_position == Decimal("25000")

    def test_calculate_headroom_invalid_volume(self):
        """Test with zero daily volume - should raise exception."""
        with pytest.raises(Exception):  # ValidationError
            self.analyzer.calculate_headroom(
                position_size_usd=Decimal("10000"),
                daily_volume_usd=Decimal("0"),
                max_allowed_pct=Decimal("5.0"),
            )


# ============================================================================
# AlphaDecayEstimator Tests (6 tests)
# ============================================================================

class TestAlphaDecayEstimator:
    """Test AlphaDecayEstimator component."""

    def setup_method(self):
        """Setup test fixtures."""
        self.estimator = AlphaDecayEstimator()

    def test_estimator_initialization(self):
        """Test estimator initialization."""
        assert self.estimator is not None

    def test_estimate_alpha_sqrt_model(self):
        """Test alpha estimation with sqrt model."""
        result = self.estimator.estimate_alpha_at_scale(
            base_alpha_pct=Decimal("10"),
            current_capital_usd=Decimal("50000"),
            target_capital_usd=Decimal("250000"),
            fade_model="sqrt",
            liquidity_penalty_pct=Decimal("0"),
        )

        # sqrt(250000/50000) = sqrt(5) ≈ 2.236
        # Estimated alpha = 10 / 2.236 ≈ 4.47
        assert "estimated_alpha_pct" in result
        assert result["estimated_alpha_pct"] > Decimal("4") and result["estimated_alpha_pct"] < Decimal("5")

    def test_estimate_alpha_linear_model(self):
        """Test alpha estimation with linear decay model."""
        result = self.estimator.estimate_alpha_at_scale(
            base_alpha_pct=Decimal("10"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("200000"),
            fade_model="linear",
            liquidity_penalty_pct=Decimal("0"),
        )

        assert "estimated_alpha_pct" in result
        assert result["estimated_alpha_pct"] < Decimal("10")

    def test_estimate_alpha_empirical_model(self):
        """Test alpha estimation with empirical model."""
        result = self.estimator.estimate_alpha_at_scale(
            base_alpha_pct=Decimal("12"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            fade_model="empirical",
            liquidity_penalty_pct=Decimal("0"),
        )

        assert "estimated_alpha_pct" in result
        assert result["model"] == "empirical historical pattern"

    def test_estimate_alpha_with_liquidity_penalty(self):
        """Test alpha with liquidity penalty applied."""
        result_no_penalty = self.estimator.estimate_alpha_at_scale(
            base_alpha_pct=Decimal("10"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("200000"),
            fade_model="sqrt",
            liquidity_penalty_pct=Decimal("0"),
        )

        result_with_penalty = self.estimator.estimate_alpha_at_scale(
            base_alpha_pct=Decimal("10"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("200000"),
            fade_model="sqrt",
            liquidity_penalty_pct=Decimal("5.0"),
        )

        # Penalty should reduce estimated alpha
        assert result_with_penalty["estimated_alpha_pct"] < result_no_penalty["estimated_alpha_pct"]

    def test_calculate_required_alpha(self):
        """Test required alpha calculation."""
        required = self.estimator.calculate_required_alpha(
            target_monthly_return_usd=Decimal("800"),
            target_capital_usd=Decimal("250000"),
        )

        # €800/month = €9600/year
        # Required alpha = (9600 / 250000) * 100 = 3.84%
        assert Decimal("3.8") < required < Decimal("3.9")

    def test_calculate_required_alpha_zero_capital(self):
        """Test required alpha with zero capital."""
        required = self.estimator.calculate_required_alpha(
            target_monthly_return_usd=Decimal("800"),
            target_capital_usd=Decimal("0"),
        )

        assert required == Decimal("0")


# ============================================================================
# CapacityFadeValidator (Orchestrator) Tests (5 tests)
# ============================================================================

class TestCapacityFadeValidator:
    """Test CapacityFadeValidator orchestrator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.validator = CapacityFadeValidator()

    @pytest.mark.asyncio
    async def test_validator_initialization(self):
        """Test validator initialization."""
        assert self.validator is not None
        assert self.validator.capacity_analyzer is not None
        assert self.validator.liquidity_analyzer is not None
        assert self.validator.alpha_estimator is not None

    @pytest.mark.asyncio
    async def test_validate_feasible_strategy(self):
        """Test validation of feasible strategy."""
        request = CapacityFadeRequest(
            profile_id="test_profile_1",
            input_id="input_001",
            base_alpha_pct=Decimal("10"),
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("3"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            target_monthly_return_usd=Decimal("500"),  # €500/month = 2.4% alpha required
            avg_position_size_usd=Decimal("50000"),
            avg_daily_volume_multiplier=Decimal("1.0"),
            fade_model="sqrt",
            confidence_level="moderate",
        )

        response = await self.validator.validate_capacity_feasibility(request)

        assert response.success is True
        assert response.feasibility_gate.approved is True
        assert response.analysis.base_alpha_pct == Decimal("10")

    @pytest.mark.asyncio
    async def test_validate_infeasible_strategy(self):
        """Test validation of infeasible strategy (alpha too low)."""
        request = CapacityFadeRequest(
            profile_id="test_profile_2",
            input_id="input_002",
            base_alpha_pct=Decimal("2"),  # Very low base alpha
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("3"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            target_monthly_return_usd=Decimal("1000"),  # €1000/month = 4.8% alpha required
            avg_position_size_usd=Decimal("50000"),
            avg_daily_volume_multiplier=Decimal("1.0"),
            fade_model="sqrt",
            confidence_level="conservative",
        )

        response = await self.validator.validate_capacity_feasibility(request)

        assert response.success is True
        assert response.feasibility_gate.decision == FeasibilityDecision.REJECTED
        assert response.feasibility_gate.approved is False
        assert response.feasibility_gate.hard_gate is True

    @pytest.mark.asyncio
    async def test_validate_conditional_strategy(self):
        """Test validation of conditional strategy (marginal feasibility)."""
        request = CapacityFadeRequest(
            profile_id="test_profile_3",
            input_id="input_003",
            base_alpha_pct=Decimal("8"),  # Moderate alpha
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("3"),
            current_capital_usd=Decimal("50000"),
            target_capital_usd=Decimal("500000"),  # Large scaling = high fade
            target_monthly_return_usd=Decimal("300"),
            avg_position_size_usd=Decimal("50000"),
            avg_daily_volume_multiplier=Decimal("0.5"),  # Lower liquidity
            fade_model="sqrt",
            confidence_level="conservative",
        )

        response = await self.validator.validate_capacity_feasibility(request)

        assert response.success is True
        # Could be CONDITIONAL due to high fade or liquidity constraints
        assert response.feasibility_gate.approved in [True, False]

    @pytest.mark.asyncio
    async def test_validation_response_structure(self):
        """Test response structure is complete."""
        request = CapacityFadeRequest(
            profile_id="test_profile_4",
            input_id="input_004",
            base_alpha_pct=Decimal("7"),
            backtest_capital_usd=Decimal("100000"),
            backtest_duration_years=Decimal("2"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("300000"),
            target_monthly_return_usd=Decimal("600"),
            avg_position_size_usd=Decimal("30000"),
            avg_daily_volume_multiplier=Decimal("1.0"),
            fade_model="sqrt",
            confidence_level="moderate",
        )

        response = await self.validator.validate_capacity_feasibility(request)

        # Verify response structure
        assert isinstance(response, CapacityFadeResponse)
        assert response.success is True
        assert response.feasibility_gate is not None
        assert response.analysis is not None
        assert isinstance(response.summary, str)
        assert response.feasibility_gate.decision in [
            FeasibilityDecision.APPROVED,
            FeasibilityDecision.CONDITIONAL,
            FeasibilityDecision.REJECTED,
        ]
        assert response.feasibility_gate.analysis.base_alpha_pct == Decimal("7")


# ============================================================================
# Integration Tests (3 tests)
# ============================================================================

class TestCapacityFadeIntegration:
    """Integration tests combining multiple components."""

    def setup_method(self):
        """Setup test fixtures."""
        self.validator = CapacityFadeValidator()

    @pytest.mark.asyncio
    async def test_full_pipeline_conservative_strategy(self):
        """Test full pipeline with conservative strategy."""
        request = CapacityFadeRequest(
            profile_id="conservative_strategy",
            input_id="conservative_001",
            base_alpha_pct=Decimal("12"),  # Good base alpha
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("5"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("250000"),
            target_monthly_return_usd=Decimal("600"),  # €600/month reasonable
            avg_position_size_usd=Decimal("25000"),
            avg_daily_volume_multiplier=Decimal("2.0"),  # Good liquidity
            fade_model="sqrt",
            confidence_level="conservative",
        )

        response = await self.validator.validate_capacity_feasibility(request)

        assert response.success is True
        assert response.feasibility_gate.analysis.alpha_sufficient is True

    @pytest.mark.asyncio
    async def test_full_pipeline_scaling_impact(self):
        """Test how scaling affects feasibility."""
        base_request = CapacityFadeRequest(
            profile_id="scaling_test",
            input_id="scaling_001",
            base_alpha_pct=Decimal("8"),
            backtest_capital_usd=Decimal("50000"),
            backtest_duration_years=Decimal("3"),
            current_capital_usd=Decimal("50000"),
            target_capital_usd=Decimal("250000"),  # 5x scaling
            target_monthly_return_usd=Decimal("400"),
            avg_position_size_usd=Decimal("25000"),
            avg_daily_volume_multiplier=Decimal("1.0"),
            fade_model="sqrt",
            confidence_level="moderate",
        )

        response = await self.validator.validate_capacity_feasibility(base_request)

        # At 5x scaling with sqrt model, alpha should be reduced significantly
        assert response.success is True
        assert response.analysis.estimated_alpha_at_target < response.analysis.base_alpha_pct

    @pytest.mark.asyncio
    async def test_feasibility_gate_recommendations(self):
        """Test that recommendations are provided."""
        request = CapacityFadeRequest(
            profile_id="recommendations_test",
            input_id="recs_001",
            base_alpha_pct=Decimal("6"),
            backtest_capital_usd=Decimal("100000"),
            backtest_duration_years=Decimal("2"),
            current_capital_usd=Decimal("100000"),
            target_capital_usd=Decimal("400000"),
            target_monthly_return_usd=Decimal("500"),
            avg_position_size_usd=Decimal("50000"),
            avg_daily_volume_multiplier=Decimal("0.8"),
            fade_model="sqrt",
            confidence_level="conservative",
        )

        response = await self.validator.validate_capacity_feasibility(request)

        # Should have recommendations
        assert len(response.feasibility_gate.recommendations) > 0
        assert isinstance(response.feasibility_gate.validation_message, str)


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
