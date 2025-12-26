"""Unit tests for T8.1 LimitAdjuster component"""

import pytest
from decimal import Decimal
from app.services.portfolio_constructor import AllocationWeight
from app.services.risk_scaling_application.limit_adjuster import (
    LimitAdjuster, AdjustedLimit, LimitBreach,
)


def create_allocation(name, weight, capital=Decimal("30000")):
    """Helper to create AllocationWeight with required fields."""
    return AllocationWeight(
        module_name=name,
        weight_pct=weight,
        capital_allocation_eur=capital,
        rationale=f"Test allocation for {name}",
    )


class TestLimitAdjuster:
    """Test LimitAdjuster component."""

    def setup_method(self):
        """Setup test fixtures."""
        self.adjuster = LimitAdjuster(
            default_position_limit=Decimal("50000"),
            default_max_leverage=Decimal("2.0"),
            default_max_allocation=Decimal("25"),
        )

    def test_initialization(self):
        """Test adjuster initialization."""
        assert self.adjuster.default_position_limit == Decimal("50000")
        assert self.adjuster.default_max_leverage == Decimal("2.0")

    # Position Limit Adjustment Tests
    def test_adjust_position_limits_no_scaling(self):
        """Test position limits with 1.0x scaling."""
        allocations = [create_allocation("momentum", Decimal("30"))]
        adjusted = self.adjuster.adjust_position_limits(
            allocations, Decimal("1.0"), Decimal("100000")
        )
        assert len(adjusted) == 1
        assert adjusted[0].scaling_applied == Decimal("1.0")

    def test_adjust_position_limits_scaled_down(self):
        """Test position limits with <1.0x scaling."""
        allocations = [create_allocation("momentum", Decimal("30"))]
        adjusted = self.adjuster.adjust_position_limits(
            allocations, Decimal("0.75"), Decimal("100000")
        )
        assert len(adjusted) == 1
        assert adjusted[0].adjusted_limit < adjusted[0].original_limit

    def test_adjust_position_limits_respects_ceiling(self):
        """Test that adjusted limits never exceed portfolio value."""
        allocations = [create_allocation("test", Decimal("50"))]
        adjusted = self.adjuster.adjust_position_limits(
            allocations, Decimal("10.0"), Decimal("100000")
        )
        assert adjusted[0].adjusted_limit <= Decimal("100000")

    # Breach Detection Tests
    def test_detect_no_breaches(self):
        """Test when no positions breach limits."""
        limits = [AdjustedLimit(
            module_name="momentum",
            original_limit=Decimal("50000"),
            adjusted_limit=Decimal("40000"),
            scaling_applied=Decimal("0.8"),
            reason="Test",
        )]
        breaches = self.adjuster.detect_limit_breaches(
            {"momentum": Decimal("30000")}, limits
        )
        assert len(breaches) == 0

    def test_detect_warning_breach(self):
        """Test warning level breach detection."""
        limits = [AdjustedLimit(
            module_name="momentum",
            original_limit=Decimal("50000"),
            adjusted_limit=Decimal("40000"),
            scaling_applied=Decimal("0.8"),
            reason="Test",
        )]
        breaches = self.adjuster.detect_limit_breaches(
            {"momentum": Decimal("43000")}, limits
        )
        assert len(breaches) == 1
        assert breaches[0].severity == "warning"

    def test_detect_critical_breach(self):
        """Test critical level breach detection."""
        limits = [AdjustedLimit(
            module_name="momentum",
            original_limit=Decimal("50000"),
            adjusted_limit=Decimal("40000"),
            scaling_applied=Decimal("0.8"),
            reason="Test",
        )]
        breaches = self.adjuster.detect_limit_breaches(
            {"momentum": Decimal("55000")}, limits
        )
        assert len(breaches) == 1
        assert breaches[0].severity == "critical"

    # Leverage Adjustment Tests
    def test_adjust_leverage_normal_market(self):
        """Test leverage in normal market."""
        lev, _ = self.adjuster.apply_leverage_adjustment(
            Decimal("1.5"), Decimal("0.9"), "normal"
        )
        assert lev == Decimal("1.35")

    def test_adjust_leverage_bear_market(self):
        """Test leverage reduction in bear market."""
        lev, _ = self.adjuster.apply_leverage_adjustment(
            Decimal("1.5"), Decimal("1.0"), "bear"
        )
        assert lev == Decimal("1.2")

    def test_adjust_leverage_bull_market(self):
        """Test leverage increase in bull market."""
        lev, _ = self.adjuster.apply_leverage_adjustment(
            Decimal("1.5"), Decimal("1.0"), "bull"
        )
        assert lev == Decimal("1.65")

    def test_adjust_leverage_respects_limits(self):
        """Test leverage respects min/max limits."""
        lev, _ = self.adjuster.apply_leverage_adjustment(
            Decimal("2.0"), Decimal("2.0"), "normal"
        )
        assert lev <= self.adjuster.default_max_leverage

    # Validation Tests
    def test_validate_position_within_limits(self):
        """Test position validation when within limits."""
        limits = [AdjustedLimit(
            module_name="momentum",
            original_limit=Decimal("50000"),
            adjusted_limit=Decimal("40000"),
            scaling_applied=Decimal("0.8"),
            reason="Test",
        )]
        is_valid, _ = self.adjuster.validate_position_within_limits(
            "momentum", Decimal("35000"), limits
        )
        assert is_valid is True

    def test_validate_position_exceeds_limits(self):
        """Test position validation when exceeding limits."""
        limits = [AdjustedLimit(
            module_name="momentum",
            original_limit=Decimal("50000"),
            adjusted_limit=Decimal("40000"),
            scaling_applied=Decimal("0.8"),
            reason="Test",
        )]
        is_valid, _ = self.adjuster.validate_position_within_limits(
            "momentum", Decimal("45000"), limits
        )
        assert is_valid is False

    def test_validate_leverage_within_limits(self):
        """Test leverage validation."""
        is_valid, _ = self.adjuster.validate_leverage_within_limits(
            Decimal("1.5"), Decimal("2.0")
        )
        assert is_valid is True

    # Hard Stop Enforcement Tests
    def test_enforce_no_critical_breaches(self):
        """Test enforcement with no critical breaches."""
        should_cont, action = self.adjuster.enforce_hard_stops([])
        assert should_cont is True
        assert action["action"] == "none"

    def test_enforce_halt_on_critical(self):
        """Test HALT enforcement on critical breach."""
        breaches = [LimitBreach(
            module_name="momentum",
            current_position=Decimal("60000"),
            adjusted_limit=Decimal("40000"),
            excess=Decimal("20000"),
            severity="critical",
            recommendation="Reduce",
        )]
        should_cont, action = self.adjuster.enforce_hard_stops(breaches, "halt")
        assert should_cont is False
        assert action["action"] == "halt"

    def test_enforce_reduce_on_critical(self):
        """Test REDUCE enforcement on critical breach."""
        breaches = [LimitBreach(
            module_name="momentum",
            current_position=Decimal("60000"),
            adjusted_limit=Decimal("40000"),
            excess=Decimal("20000"),
            severity="critical",
            recommendation="Reduce",
        )]
        should_cont, action = self.adjuster.enforce_hard_stops(breaches, "reduce")
        assert should_cont is True
        assert action["action"] == "reduce"

    # Configuration Tests
    def test_set_position_limit(self):
        """Test setting position limit."""
        self.adjuster.set_position_limit(Decimal("75000"))
        assert self.adjuster.default_position_limit == Decimal("75000")

    def test_set_max_leverage(self):
        """Test setting max leverage."""
        self.adjuster.set_max_leverage(Decimal("3.0"))
        assert self.adjuster.default_max_leverage == Decimal("3.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
