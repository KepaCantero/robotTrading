"""
PHASE 1: Unit Tests for Absolute Return Optimizer (T1.2)

Tests:
- Target alpha calculation
- Capacity fade analysis
- Parameter optimization
- Feasibility validation
"""

import pytest
from decimal import Decimal

from app.maestro.phase_1 import (
    AbsoluteReturnTarget,
    TargetAlphaCalculator,
    CapacityFadeAnalyzer,
    ParameterOptimizer,
    FeasibilityValidator,
)


class TestTargetAlphaCalculation:
    """Test target alpha calculation."""

    def test_simple_target_calculation(self):
        """Test basic target to alpha conversion."""
        calculator = TargetAlphaCalculator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("800"),
            capital=Decimal("250000"),
            time_horizon_months=24,
            tax_rate=Decimal("0.19"),
            commission_per_trade=Decimal("10"),
            expected_trades_per_month=10,
        )
        alpha = calculator.calculate_required_alpha(target)
        # Should be approximately 5.2% annual (accounting for commissions)
        assert alpha >= Decimal("4.5")
        assert alpha <= Decimal("6.0")

    def test_micro_capital_high_alpha_required(self):
        """Test MICRO capital requires high alpha."""
        calculator = TargetAlphaCalculator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("200"),
            capital=Decimal("10000"),
            time_horizon_months=12,
        )
        alpha = calculator.calculate_required_alpha(target)
        # High capital-to-target ratio requires high alpha
        assert alpha > Decimal("20")

    def test_large_capital_low_alpha_required(self):
        """Test LARGE capital requires lower alpha."""
        calculator = TargetAlphaCalculator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("800"),
            capital=Decimal("1000000"),
            time_horizon_months=12,
        )
        alpha = calculator.calculate_required_alpha(target)
        # Lower target relative to capital requires less alpha
        assert alpha < Decimal("2")

    def test_small_target_requires_low_alpha(self):
        """Test small target requires minimal alpha."""
        calculator = TargetAlphaCalculator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("10"),
            capital=Decimal("100000"),
            time_horizon_months=12,
            commission_per_trade=Decimal("0"),
            expected_trades_per_month=0,
        )
        alpha = calculator.calculate_required_alpha(target)
        # €10/month = €120/year = 0.12% alpha
        assert alpha >= Decimal("0.10")
        assert alpha <= Decimal("0.15")

    def test_tax_rate_increases_required_alpha(self):
        """Test higher tax rate increases required alpha."""
        calculator = TargetAlphaCalculator()
        target_low_tax = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("500"),
            capital=Decimal("100000"),
            time_horizon_months=12,
            tax_rate=Decimal("0.1"),
            commission_per_trade=Decimal("0"),
            expected_trades_per_month=0,
        )
        target_high_tax = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("500"),
            capital=Decimal("100000"),
            time_horizon_months=12,
            tax_rate=Decimal("0.4"),
            commission_per_trade=Decimal("0"),
            expected_trades_per_month=0,
        )
        alpha_low = calculator.calculate_required_alpha(target_low_tax)
        alpha_high = calculator.calculate_required_alpha(target_high_tax)
        assert alpha_high > alpha_low

    def test_monthly_to_annual_conversion(self):
        """Test monthly to annual alpha conversion."""
        calculator = TargetAlphaCalculator()
        monthly = Decimal("500")
        capital = Decimal("100000")
        annual_alpha = calculator.monthly_to_annual_alpha_pct(monthly, capital)
        # €500/month = €6000/year = 6% of €100k
        assert annual_alpha == Decimal("6.00")


class TestCapacityFadeAnalysis:
    """Test capacity fade estimation."""

    def test_no_fade_at_baseline(self):
        """Test no fade at €10k baseline."""
        analyzer = CapacityFadeAnalyzer()
        base_alpha = Decimal("8")
        faded = analyzer.estimate_capacity_fade(Decimal("10000"), base_alpha)
        # Should be 100% of base
        assert faded == base_alpha

    def test_fade_at_50k(self):
        """Test 5% fade at €50k."""
        analyzer = CapacityFadeAnalyzer()
        base_alpha = Decimal("8")
        faded = analyzer.estimate_capacity_fade(Decimal("50000"), base_alpha)
        # Should be ~95% of base (5% fade)
        expected = base_alpha * Decimal("0.95")
        assert faded == expected

    def test_fade_at_250k(self):
        """Test 15% fade at €250k."""
        analyzer = CapacityFadeAnalyzer()
        base_alpha = Decimal("8")
        faded = analyzer.estimate_capacity_fade(Decimal("250000"), base_alpha)
        # Should be ~85% of base (15% fade)
        expected = base_alpha * Decimal("0.85")
        assert faded == expected

    def test_fade_at_1m(self):
        """Test 25% fade at €1M."""
        analyzer = CapacityFadeAnalyzer()
        base_alpha = Decimal("8")
        faded = analyzer.estimate_capacity_fade(Decimal("1000000"), base_alpha)
        # Should be ~75% of base (25% fade)
        expected = base_alpha * Decimal("0.75")
        assert faded == expected

    def test_fade_is_monotonic(self):
        """Test fade increases monotonically with capital."""
        analyzer = CapacityFadeAnalyzer()
        base_alpha = Decimal("8")
        capitals = [Decimal("10000"), Decimal("50000"), Decimal("250000"), Decimal("1000000")]
        faded_alphas = [analyzer.estimate_capacity_fade(c, base_alpha) for c in capitals]
        # Each should be less than previous (fade increases)
        for i in range(1, len(faded_alphas)):
            assert faded_alphas[i] <= faded_alphas[i - 1]


class TestParameterOptimization:
    """Test position sizing and leverage optimization."""

    def test_position_sizing_micro_tier(self):
        """Test position sizing for MICRO tier."""
        optimizer = ParameterOptimizer()
        result = optimizer.optimize_position_sizing(
            capital=Decimal("10000"),
            target_alpha_pct=Decimal("3"),
            expected_signal_return_pct=Decimal("2"),
        )
        assert "position_size_pct" in result
        assert "num_concurrent_positions" in result
        assert result["position_size_pct"] <= Decimal("0.02")  # MICRO max

    def test_position_sizing_large_tier(self):
        """Test position sizing for LARGE tier."""
        optimizer = ParameterOptimizer()
        result = optimizer.optimize_position_sizing(
            capital=Decimal("500000"),
            target_alpha_pct=Decimal("3"),
            expected_signal_return_pct=Decimal("2"),
        )
        assert result["position_size_pct"] <= Decimal("0.15")  # LARGE max

    def test_position_size_in_eur(self):
        """Test position size is calculated in EUR."""
        optimizer = ParameterOptimizer()
        capital = Decimal("100000")
        result = optimizer.optimize_position_sizing(
            capital=capital,
            target_alpha_pct=Decimal("4"),
            expected_signal_return_pct=Decimal("2"),
        )
        expected_eur = capital * result["position_size_pct"]
        assert result["position_size_eur"] == expected_eur

    def test_leverage_not_needed_when_alpha_sufficient(self):
        """Test no leverage needed when alpha already sufficient."""
        optimizer = ParameterOptimizer()
        leverage = optimizer.optimize_leverage(
            capital=Decimal("100000"),
            target_alpha_pct=Decimal("3"),
            achievable_alpha_without_leverage=Decimal("5"),  # Already exceeds target
        )
        assert leverage == Decimal("1.0")  # No leverage needed

    def test_leverage_applied_when_needed(self):
        """Test leverage applied when necessary."""
        optimizer = ParameterOptimizer()
        leverage = optimizer.optimize_leverage(
            capital=Decimal("100000"),
            target_alpha_pct=Decimal("8"),
            achievable_alpha_without_leverage=Decimal("4"),  # Need 2x
        )
        assert leverage > Decimal("1.0")
        assert leverage <= Decimal("1.5")  # MEDIUM tier max

    def test_leverage_capped_at_tier_maximum(self):
        """Test leverage is capped at tier maximum."""
        optimizer = ParameterOptimizer()
        leverage = optimizer.optimize_leverage(
            capital=Decimal("10000"),  # MICRO tier, max 0x
            target_alpha_pct=Decimal("10"),
            achievable_alpha_without_leverage=Decimal("2"),
        )
        assert leverage <= Decimal("0")  # MICRO tier can't use leverage

    def test_invalid_signal_return_raises_error(self):
        """Test invalid signal return raises error."""
        optimizer = ParameterOptimizer()
        with pytest.raises(ValueError):
            optimizer.optimize_position_sizing(
                capital=Decimal("100000"),
                target_alpha_pct=Decimal("3"),
                expected_signal_return_pct=Decimal("0"),  # Invalid
            )

    def test_concurrent_positions_calculated(self):
        """Test concurrent positions are calculated."""
        optimizer = ParameterOptimizer()
        result = optimizer.optimize_position_sizing(
            capital=Decimal("100000"),
            target_alpha_pct=Decimal("2"),
            expected_signal_return_pct=Decimal("2"),
        )
        assert result["num_concurrent_positions"] >= Decimal("1")
        assert "total_exposure_pct" in result


class TestFeasibilityValidation:
    """Test feasibility validation."""

    def test_feasible_250k_800_monthly(self):
        """Test €250k/€800 monthly is feasible."""
        validator = FeasibilityValidator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("800"),
            capital=Decimal("250000"),
            time_horizon_months=24,
        )
        result = validator.validate_target(target)
        assert result.is_feasible is True
        assert result.confidence_level in ["HIGH", "MEDIUM"]

    def test_infeasible_10k_500_monthly(self):
        """Test €10k/€500 monthly is not feasible."""
        validator = FeasibilityValidator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("500"),
            capital=Decimal("10000"),
            time_horizon_months=12,
        )
        result = validator.validate_target(target)
        assert result.is_feasible is False

    def test_recommendation_text_provided(self):
        """Test recommendation text is provided."""
        validator = FeasibilityValidator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("200"),
            capital=Decimal("50000"),
            time_horizon_months=12,
        )
        result = validator.validate_target(target)
        assert len(result.recommendation) > 0
        assert "€" in result.recommendation or "capital" in result.recommendation.lower()

    def test_monthly_costs_calculated(self):
        """Test monthly costs are calculated."""
        validator = FeasibilityValidator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("500"),
            capital=Decimal("100000"),
            time_horizon_months=12,
            tax_rate=Decimal("0.19"),
            commission_per_trade=Decimal("10"),
            expected_trades_per_month=10,
        )
        result = validator.validate_target(target)
        assert "commissions" in result.monthly_costs
        assert "taxes_on_profit" in result.monthly_costs
        assert "total" in result.monthly_costs
        assert result.monthly_costs["commissions"] == Decimal("100")  # 10*10
        assert result.monthly_costs["taxes_on_profit"] == Decimal("95")  # 500*0.19

    def test_confidence_high_when_easy_target(self):
        """Test confidence is HIGH for easy targets."""
        validator = FeasibilityValidator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("100"),  # Easy target
            capital=Decimal("500000"),  # Large capital
            time_horizon_months=24,
        )
        result = validator.validate_target(target)
        assert result.confidence_level == "HIGH"

    def test_confidence_low_when_hard_target(self):
        """Test confidence is LOW for difficult targets."""
        validator = FeasibilityValidator()
        target = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("2000"),  # Hard target
            capital=Decimal("50000"),  # Smaller capital
            time_horizon_months=12,
        )
        result = validator.validate_target(target)
        if not result.is_feasible:
            assert result.confidence_level == "LOW"

    def test_minimal_target_always_feasible(self):
        """Test minimal target is always feasible."""
        validator = FeasibilityValidator()
        for capital in [Decimal("10000"), Decimal("50000"), Decimal("500000")]:
            target = AbsoluteReturnTarget(
                target_euros_monthly=Decimal("1"),
                capital=capital,
                time_horizon_months=12,
                commission_per_trade=Decimal("0"),
                expected_trades_per_month=0,
            )
            result = validator.validate_target(target)
            assert result.is_feasible is True

    def test_capacity_fade_affects_feasibility(self):
        """Test capacity fade impacts feasibility assessment."""
        validator = FeasibilityValidator()
        # Same target, different capitals (different fade)
        target_small = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("500"),
            capital=Decimal("50000"),
            time_horizon_months=12,
            commission_per_trade=Decimal("0"),
            expected_trades_per_month=0,
        )
        target_large = AbsoluteReturnTarget(
            target_euros_monthly=Decimal("500"),
            capital=Decimal("500000"),
            time_horizon_months=12,
            commission_per_trade=Decimal("0"),
            expected_trades_per_month=0,
        )
        result_small = validator.validate_target(target_small)
        result_large = validator.validate_target(target_large)
        # Large capital should be more feasible due to less aggressive target ratio
        assert result_large.is_feasible is True
