"""
Tests for LimitAdjuster (T8.1.2)

Tests dynamic limit adjustments for volatility, drawdown, and position sizing.
"""

import pytest
from decimal import Decimal

from app.services.risk_scaling.limit_adjuster import (
    LimitAdjuster,
    TradingLimits,
    get_limit_adjuster,
)


class TestLimitAdjuster:
    """Test suite for LimitAdjuster."""

    @pytest.fixture
    def adjuster(self):
        """Create adjuster instance."""
        return LimitAdjuster()

    # =========================================================================
    # TEST: Base Limits
    # =========================================================================

    def test_base_limits_micro_tier(self, adjuster):
        """Test MICRO tier gets conservative limits."""
        limits = adjuster.get_base_limits("micro")

        assert limits.stop_loss_pct == Decimal("0.02"), "MICRO: 2% stops"
        assert limits.max_portfolio_leverage == Decimal("1.0"), "MICRO: no leverage"
        assert limits.min_margin_requirement == Decimal("0.50"), "MICRO: 50% margin"

    def test_base_limits_large_tier(self, adjuster):
        """Test LARGE tier gets more permissive limits."""
        limits = adjuster.get_base_limits("large")

        assert limits.stop_loss_pct == Decimal("0.035"), "LARGE: 3.5% stops"
        assert limits.max_portfolio_leverage == Decimal("2.0"), "LARGE: 2x leverage"
        assert limits.min_margin_requirement == Decimal("0.20"), "LARGE: 20% margin"

    def test_limits_progression_by_tier(self, adjuster):
        """Test limits progress from conservative to aggressive by tier."""
        micro = adjuster.get_base_limits("micro")
        large = adjuster.get_base_limits("large")

        # LARGE should have more generous limits
        assert large.stop_loss_pct > micro.stop_loss_pct
        assert large.daily_loss_limit > micro.daily_loss_limit
        assert large.max_position_size > micro.max_position_size
        assert large.max_portfolio_leverage > micro.max_portfolio_leverage

    # =========================================================================
    # TEST: Volatility Adjustment
    # =========================================================================

    def test_volatility_expansion_in_calm_markets(self, adjuster):
        """Test limits expand when volatility low."""
        base = adjuster.get_base_limits("medium")

        adjusted, reason = adjuster.adjust_limits_for_volatility(
            base,
            current_volatility=Decimal("0.5"),  # Half of average
            average_volatility=Decimal("1.0"),
        )

        # Should expand limits
        assert adjusted.stop_loss_pct > base.stop_loss_pct, "Should widen stops"
        assert adjusted.max_position_size > base.max_position_size, "Should allow larger positions"
        assert "very_low" in reason.lower() or "1.2" in reason

    def test_volatility_contraction_in_volatile_markets(self, adjuster):
        """Test limits contract when volatility high."""
        base = adjuster.get_base_limits("medium")

        adjusted, reason = adjuster.adjust_limits_for_volatility(
            base,
            current_volatility=Decimal("2.0"),  # Double average
            average_volatility=Decimal("1.0"),
        )

        # Should contract limits
        assert adjusted.stop_loss_pct < base.stop_loss_pct, "Should tighten stops"
        assert adjusted.max_position_size < base.max_position_size, "Should reduce positions"
        assert "extreme" in reason.lower() or "0.5" in reason

    def test_volatility_extreme_severely_contracts_limits(self, adjuster):
        """Test extreme volatility severely contracts limits."""
        base = adjuster.get_base_limits("medium")

        adjusted, reason = adjuster.adjust_limits_for_volatility(
            base,
            current_volatility=Decimal("3.0"),  # 3x average
            average_volatility=Decimal("1.0"),
        )

        # Should severely contract
        assert adjusted.max_position_size < base.max_position_size * Decimal("0.6")
        assert "extreme" in reason.lower() or "0.5" in reason

    def test_volatility_zero_average_handled_gracefully(self, adjuster):
        """Test zero average volatility handled gracefully."""
        base = adjuster.get_base_limits("medium")

        adjusted, reason = adjuster.adjust_limits_for_volatility(
            base,
            current_volatility=Decimal("1.0"),
            average_volatility=Decimal("0"),  # Edge case
        )

        # Should return original limits unchanged
        assert adjusted.stop_loss_pct == base.stop_loss_pct
        assert "cannot calculate" in reason.lower()

    # =========================================================================
    # TEST: Drawdown Adjustment
    # =========================================================================

    def test_drawdown_healthy_maintains_limits(self, adjuster):
        """Test healthy drawdown (< 5%) maintains limits."""
        base = adjuster.get_base_limits("medium")

        adjusted, reason = adjuster.adjust_limits_for_drawdown(
            base,
            current_drawdown_pct=Decimal("0.03"),  # 3% drawdown
        )

        # Should maintain limits
        assert adjusted.stop_loss_pct == base.stop_loss_pct
        assert "healthy" in reason.lower() or "1.0" in reason

    def test_drawdown_caution_reduces_limits(self, adjuster):
        """Test caution drawdown (5-10%) reduces limits."""
        base = adjuster.get_base_limits("medium")

        adjusted, reason = adjuster.adjust_limits_for_drawdown(
            base,
            current_drawdown_pct=Decimal("0.07"),  # 7% drawdown
        )

        # Should reduce limits
        assert adjusted.max_position_size < base.max_position_size
        assert "caution" in reason.lower() or "0.8" in reason

    def test_drawdown_warning_significantly_reduces_limits(self, adjuster):
        """Test warning drawdown (10-15%) significantly reduces limits."""
        base = adjuster.get_base_limits("medium")

        adjusted, reason = adjuster.adjust_limits_for_drawdown(
            base,
            current_drawdown_pct=Decimal("0.12"),  # 12% drawdown
        )

        # Should significantly reduce
        assert adjusted.max_position_size < base.max_position_size * Decimal("0.7")
        assert "warning" in reason.lower() or "0.6" in reason

    def test_drawdown_halt_zeros_position_limit(self, adjuster):
        """Test critical drawdown halts trading (zero positions)."""
        base = adjuster.get_base_limits("medium")

        adjusted, reason = adjuster.adjust_limits_for_drawdown(
            base,
            current_drawdown_pct=Decimal("0.25"),  # 25% drawdown
        )

        # Should halt trading
        assert adjusted.max_position_size == Decimal("0")
        assert adjusted.max_portfolio_leverage == Decimal("0")
        assert "halt" in reason.lower()

    # =========================================================================
    # TEST: Dynamic Stop Loss Calculation
    # =========================================================================

    def test_dynamic_stop_loss_basic(self, adjuster):
        """Test basic dynamic stop loss calculation."""
        stop = adjuster.calculate_dynamic_stop_loss(
            position_entry_price=Decimal("100"),
            position_size=Decimal("10000"),  # €10k position
            capital=Decimal("100000"),        # €100k capital
            risk_per_trade_pct=Decimal("0.02"),  # 2% risk per trade
        )

        # Risk = 100k × 2% = €2000
        # Distance = 2000 / 10000 = 0.20
        # Stop = 100 - 0.20 = 99.80
        assert Decimal("99.70") < stop < Decimal("99.90"), "Stop should be ~99.80"

    def test_dynamic_stop_loss_with_volatility_adjustment(self, adjuster):
        """Test stop loss adjusted for volatility."""
        stop_normal = adjuster.calculate_dynamic_stop_loss(
            position_entry_price=Decimal("100"),
            position_size=Decimal("10000"),
            capital=Decimal("100000"),
            risk_per_trade_pct=Decimal("0.02"),
            volatility_adjustment=Decimal("1.0"),
        )

        stop_high_vol = adjuster.calculate_dynamic_stop_loss(
            position_entry_price=Decimal("100"),
            position_size=Decimal("10000"),
            capital=Decimal("100000"),
            risk_per_trade_pct=Decimal("0.02"),
            volatility_adjustment=Decimal("1.5"),  # 50% higher vol
        )

        # Higher vol should push stop further away
        assert stop_high_vol < stop_normal, "Higher vol should allow wider stop"

    def test_dynamic_stop_loss_zero_entry_price(self, adjuster):
        """Test edge case: zero entry price."""
        stop = adjuster.calculate_dynamic_stop_loss(
            position_entry_price=Decimal("0"),
            position_size=Decimal("10000"),
            capital=Decimal("100000"),
            risk_per_trade_pct=Decimal("0.02"),
        )

        assert stop == Decimal("0"), "Should handle zero entry price"

    # =========================================================================
    # TEST: Limit Checks
    # =========================================================================

    def test_daily_loss_within_limit(self, adjuster):
        """Test check when daily loss within limit."""
        is_within = adjuster.is_within_daily_limit(
            current_daily_loss=Decimal("-1000"),  # -€1000 loss
            daily_loss_limit=Decimal("0.05"),     # 5% limit
            capital=Decimal("100000"),
        )

        # 5% of 100k = 5000, so -1000 is within limit
        assert is_within is True

    def test_daily_loss_exceeds_limit(self, adjuster):
        """Test check when daily loss exceeds limit."""
        is_within = adjuster.is_within_daily_limit(
            current_daily_loss=Decimal("-10000"),  # -€10000 loss
            daily_loss_limit=Decimal("0.05"),      # 5% limit = €5000
            capital=Decimal("100000"),
        )

        assert is_within is False, "Should flag excessive daily loss"

    def test_leverage_within_limit(self, adjuster):
        """Test leverage check when within limit."""
        is_within = adjuster.is_within_leverage_limit(
            total_capital_deployed=Decimal("150000"),  # 1.5x deployed
            capital=Decimal("100000"),
            leverage_limit=Decimal("2.0"),
        )

        assert is_within is True

    def test_leverage_exceeds_limit(self, adjuster):
        """Test leverage check when exceeding limit."""
        is_within = adjuster.is_within_leverage_limit(
            total_capital_deployed=Decimal("250000"),  # 2.5x deployed
            capital=Decimal("100000"),
            leverage_limit=Decimal("2.0"),            # 2x limit
        )

        assert is_within is False, "Should flag excessive leverage"

    def test_position_size_within_limit(self, adjuster):
        """Test position size check when within limit."""
        is_within = adjuster.is_within_position_size_limit(
            position_size=Decimal("15000"),      # €15k position
            max_position_size_pct=Decimal("0.20"),  # 20% limit
            capital=Decimal("100000"),           # €100k capital (20% = €20k)
        )

        assert is_within is True

    def test_position_size_exceeds_limit(self, adjuster):
        """Test position size check when exceeding limit."""
        is_within = adjuster.is_within_position_size_limit(
            position_size=Decimal("25000"),      # €25k position
            max_position_size_pct=Decimal("0.20"),  # 20% limit = €20k
            capital=Decimal("100000"),
        )

        assert is_within is False, "Should flag oversized position"

    # =========================================================================
    # TEST: Comprehensive Limits
    # =========================================================================

    def test_comprehensive_limits_healthy_scenario(self, adjuster):
        """Test comprehensive limits in healthy market scenario."""
        limits = adjuster.get_comprehensive_limits(
            capital_tier="medium",
            capital=Decimal("250000"),
            current_volatility=Decimal("1.0"),
            average_volatility=Decimal("1.0"),
            current_drawdown_pct=Decimal("0.03"),  # 3% drawdown (healthy)
        )

        # Should be normal limits
        assert limits["stop_loss_pct"] == Decimal("0.03")
        assert limits["max_leverage"] == Decimal("1.5")
        assert limits["max_position_eur"] == Decimal("50000")  # 20% of 250k

    def test_comprehensive_limits_stressed_scenario(self, adjuster):
        """Test comprehensive limits in stressed market scenario."""
        limits = adjuster.get_comprehensive_limits(
            capital_tier="medium",
            capital=Decimal("250000"),
            current_volatility=Decimal("2.0"),       # 2x average vol
            average_volatility=Decimal("1.0"),
            current_drawdown_pct=Decimal("0.15"),    # 15% drawdown (critical)
        )

        # Should be severely restricted
        assert limits["stop_loss_pct"] < Decimal("0.03")
        assert limits["max_leverage"] < Decimal("1.5")
        assert limits["max_position_eur"] < Decimal("50000")

    def test_comprehensive_limits_includes_all_fields(self, adjuster):
        """Test comprehensive limits returns all required fields."""
        limits = adjuster.get_comprehensive_limits(
            capital_tier="large",
            capital=Decimal("500000"),
            current_volatility=Decimal("1.5"),
            average_volatility=Decimal("1.0"),
            current_drawdown_pct=Decimal("0.05"),
        )

        assert "stop_loss_pct" in limits
        assert "daily_loss_limit_pct" in limits
        assert "max_position_pct" in limits
        assert "max_leverage" in limits
        assert "margin_requirement" in limits
        assert "max_drawdown_pct" in limits
        assert "daily_loss_limit_eur" in limits
        assert "max_position_eur" in limits
        assert "volatility_adjustment" in limits
        assert "drawdown_adjustment" in limits

    # =========================================================================
    # TEST: Singleton
    # =========================================================================

    def test_singleton_pattern(self):
        """Test get_limit_adjuster returns singleton."""
        adj1 = get_limit_adjuster()
        adj2 = get_limit_adjuster()

        assert adj1 is adj2, "Should return same instance"
