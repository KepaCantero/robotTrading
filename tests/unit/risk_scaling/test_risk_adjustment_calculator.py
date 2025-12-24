"""
Tests for RiskAdjustmentCalculator (T8.1.1)

Tests position scaling, leverage adjustment, and stop loss calculations.
"""

import pytest
from decimal import Decimal

from app.services.risk_scaling.risk_adjustment_calculator import (
    RiskAdjustmentCalculator,
    get_risk_adjustment_calculator,
)


class TestRiskAdjustmentCalculator:
    """Test suite for RiskAdjustmentCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return RiskAdjustmentCalculator()

    # =========================================================================
    # TEST: Position Scaling
    # =========================================================================

    def test_high_feasibility_maintains_position(self, calculator):
        """Test high feasibility (>= 1.0) maintains 100% position."""
        position, reason = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("1.2"),
            base_position_size=Decimal("10000"),
            capital_tier="medium",
            risk_tolerance=4,
        )

        # Should maintain ~100% (may be slightly up with aggressive risk tolerance)
        assert position >= Decimal("9000"), "High feasibility should maintain position"
        assert "high" in reason.lower() or "1.20" in reason

    def test_marginal_feasibility_reduces_position(self, calculator):
        """Test marginal feasibility (0.7-1.0) reduces position."""
        position, reason = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("0.8"),
            base_position_size=Decimal("10000"),
            capital_tier="medium",
            risk_tolerance=4,
        )

        # Should reduce to ~80%
        assert Decimal("7000") <= position <= Decimal("9000"), "Should reduce position"
        assert "acceptable" in reason.lower() or "0.80" in reason

    def test_unviable_feasibility_minimizes_position(self, calculator):
        """Test unviable feasibility (< 0.5) minimizes position."""
        position, reason = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("0.3"),
            base_position_size=Decimal("10000"),
            capital_tier="medium",
            risk_tolerance=4,
        )

        # Should minimize position
        assert position <= Decimal("5000"), "Unviable should minimize position"
        assert "unviable" in reason.lower() or "0.30" in reason

    def test_micro_tier_conservative_scaling(self, calculator):
        """Test MICRO tier gets more conservative scaling."""
        position_micro, _ = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("1.0"),
            base_position_size=Decimal("10000"),
            capital_tier="micro",
            risk_tolerance=4,
        )

        position_large, _ = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("1.0"),
            base_position_size=Decimal("10000"),
            capital_tier="large",
            risk_tolerance=4,
        )

        # MICRO tier should be more conservative (lower position)
        assert position_micro < position_large, "MICRO tier should scale down more"

    def test_risk_tolerance_affects_scaling(self, calculator):
        """Test risk tolerance affects scaling within category."""
        # Conservative risk tolerance
        position_conservative, _ = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("0.8"),
            base_position_size=Decimal("10000"),
            capital_tier="medium",
            risk_tolerance=2,
        )

        # Aggressive risk tolerance
        position_aggressive, _ = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("0.8"),
            base_position_size=Decimal("10000"),
            capital_tier="medium",
            risk_tolerance=6,
        )

        # Same feasibility but different risk tolerance → different positions
        assert position_conservative <= position_aggressive, "Conservative should size down more"

    # =========================================================================
    # TEST: Leverage Adjustment
    # =========================================================================

    def test_leverage_reduced_for_low_feasibility(self, calculator):
        """Test leverage reduced when feasibility < 1.0."""
        leverage_good, _ = calculator.calculate_leverage_adjustment(
            feasibility_ratio=Decimal("1.2"),
            capital_tier="medium",
            market_volatility="normal",
        )

        leverage_poor, _ = calculator.calculate_leverage_adjustment(
            feasibility_ratio=Decimal("0.6"),
            capital_tier="medium",
            market_volatility="normal",
        )

        assert leverage_poor < leverage_good, "Poor feasibility should reduce leverage"

    def test_leverage_by_capital_tier(self, calculator):
        """Test leverage differs by capital tier."""
        leverage_micro, _ = calculator.calculate_leverage_adjustment(
            feasibility_ratio=Decimal("1.0"),
            capital_tier="micro",
            market_volatility="normal",
        )

        leverage_large, _ = calculator.calculate_leverage_adjustment(
            feasibility_ratio=Decimal("1.0"),
            capital_tier="large",
            market_volatility="normal",
        )

        # LARGE tier should have higher leverage
        assert leverage_large >= leverage_micro, "LARGE tier should allow more leverage"

    def test_leverage_reduced_for_volatility(self, calculator):
        """Test leverage reduced for high volatility."""
        leverage_normal, _ = calculator.calculate_leverage_adjustment(
            feasibility_ratio=Decimal("1.0"),
            capital_tier="medium",
            market_volatility="normal",
        )

        leverage_volatile, _ = calculator.calculate_leverage_adjustment(
            feasibility_ratio=Decimal("1.0"),
            capital_tier="medium",
            market_volatility="volatile",
        )

        leverage_stressed, _ = calculator.calculate_leverage_adjustment(
            feasibility_ratio=Decimal("1.0"),
            capital_tier="medium",
            market_volatility="stressed",
        )

        assert leverage_volatile < leverage_normal, "High vol should reduce leverage"
        assert leverage_stressed < leverage_volatile, "Stress should reduce leverage most"

    # =========================================================================
    # TEST: Stop Loss Adjustment
    # =========================================================================

    def test_stop_loss_tighter_for_low_risk_tolerance(self, calculator):
        """Test conservative profiles get tighter stops."""
        stop_conservative = calculator.calculate_stop_loss_adjustment(
            recommended_stop_loss_pct=Decimal("0.02"),
            risk_tolerance=1,
            volatility_multiplier=Decimal("1.0"),
        )

        stop_aggressive = calculator.calculate_stop_loss_adjustment(
            recommended_stop_loss_pct=Decimal("0.02"),
            risk_tolerance=7,
            volatility_multiplier=Decimal("1.0"),
        )

        # Conservative gets tighter stops
        assert stop_conservative < stop_aggressive, "Conservative should have tighter stops"

    def test_stop_loss_wider_for_high_volatility(self, calculator):
        """Test stops widen for high volatility."""
        stop_normal = calculator.calculate_stop_loss_adjustment(
            recommended_stop_loss_pct=Decimal("0.02"),
            risk_tolerance=4,
            volatility_multiplier=Decimal("1.0"),
        )

        stop_high_vol = calculator.calculate_stop_loss_adjustment(
            recommended_stop_loss_pct=Decimal("0.02"),
            risk_tolerance=4,
            volatility_multiplier=Decimal("1.5"),
        )

        assert stop_high_vol > stop_normal, "High volatility should widen stops"

    def test_stop_loss_capped_at_max(self, calculator):
        """Test stops capped at 10% maximum."""
        stop = calculator.calculate_stop_loss_adjustment(
            recommended_stop_loss_pct=Decimal("0.15"),  # Very wide
            risk_tolerance=7,
            volatility_multiplier=Decimal("2.0"),
        )

        assert stop <= Decimal("0.10"), "Stops should be capped at 10%"

    # =========================================================================
    # TEST: Comprehensive Calculation
    # =========================================================================

    def test_comprehensive_high_feasibility(self, calculator):
        """Test comprehensive calc for high feasibility scenario."""
        capital = Decimal("250000")
        result = calculator.calculate_position_and_leverage(
            feasibility_ratio=Decimal("1.3"),
            base_position_size=Decimal("50000"),
            capital=capital,
            capital_tier="large",
            risk_tolerance=5,
            market_volatility="normal",
        )

        # Should maintain good position and leverage
        assert result["position_size"] >= Decimal("45000"), "Should maintain position"
        assert result["leverage"] >= Decimal("1.5"), "Should allow good leverage"
        assert result["capital_at_risk"] <= capital * Decimal("2"), "Should not exceed 2x capital"

    def test_comprehensive_low_feasibility(self, calculator):
        """Test comprehensive calc for low feasibility scenario."""
        result = calculator.calculate_position_and_leverage(
            feasibility_ratio=Decimal("0.4"),
            base_position_size=Decimal("50000"),
            capital=Decimal("250000"),
            capital_tier="medium",
            risk_tolerance=3,
            market_volatility="stressed",
        )

        # Should reduce position and leverage significantly
        assert result["position_size"] <= Decimal("25000"), "Should reduce position"
        assert result["leverage"] <= Decimal("1.0"), "Should minimize leverage"
        assert (
            result["pct_capital_at_risk"] <= Decimal("0.25"),
            "Should limit risk to 25% capital"
        )

    def test_comprehensive_returns_all_fields(self, calculator):
        """Test comprehensive calculation returns all required fields."""
        result = calculator.calculate_position_and_leverage(
            feasibility_ratio=Decimal("1.0"),
            base_position_size=Decimal("50000"),
            capital=Decimal("250000"),
            capital_tier="medium",
            risk_tolerance=4,
        )

        assert "position_size" in result
        assert "leverage" in result
        assert "capital_at_risk" in result
        assert "pct_capital_at_risk" in result
        assert "position_reason" in result
        assert "leverage_reason" in result

    # =========================================================================
    # TEST: Singleton
    # =========================================================================

    def test_singleton_pattern(self):
        """Test get_risk_adjustment_calculator returns singleton."""
        calc1 = get_risk_adjustment_calculator()
        calc2 = get_risk_adjustment_calculator()

        assert calc1 is calc2, "Should return same instance"

    # =========================================================================
    # TEST: Edge Cases
    # =========================================================================

    def test_zero_feasibility_minimizes_position(self, calculator):
        """Test zero feasibility."""
        position, _ = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("0.0"),
            base_position_size=Decimal("10000"),
            capital_tier="medium",
            risk_tolerance=4,
        )

        assert position <= Decimal("5000"), "Zero feasibility should minimize"

    def test_very_high_feasibility_caps_scaling(self, calculator):
        """Test very high feasibility doesn't cause excessive scaling."""
        position, _ = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("5.0"),  # 5x target met
            base_position_size=Decimal("10000"),
            capital_tier="large",
            risk_tolerance=7,
        )

        # Should cap at reasonable multiple (1.5x max)
        assert position <= Decimal("15000"), "Should cap scaling at 1.5x"

    def test_decimal_precision_maintained(self, calculator):
        """Test Decimal precision is maintained."""
        position, _ = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("0.75"),
            base_position_size=Decimal("10000.50"),
            capital_tier="medium",
            risk_tolerance=4,
        )

        # Position should be Decimal with good precision
        assert isinstance(position, Decimal)
        assert position > Decimal("7000"), "Should scale correctly"

    def test_negative_feasibility_treated_as_zero(self, calculator):
        """Test negative feasibility (edge case)."""
        position, _ = calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("-0.5"),  # Invalid but test graceful handling
            base_position_size=Decimal("10000"),
            capital_tier="medium",
            risk_tolerance=4,
        )

        # Should treat as unviable
        assert position < Decimal("5000"), "Negative feasibility should minimize"
