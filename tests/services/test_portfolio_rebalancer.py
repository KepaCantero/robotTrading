"""
Comprehensive tests for Portfolio Rebalancer (TASK-REB-1 and REB-2).
"""

from datetime import datetime, timedelta
from decimal import Decimal


from app.services.portfolio_rebalancer import (
    DynamicCapitalAdjuster,
    PortfolioRebalancer,
    RebalancingTarget,
)


class TestRebalancingTarget:
    """Tests for TASK-REB-1: Rebalancing Target."""

    def test_initialization(self):
        """Test target initialization."""
        target = RebalancingTarget("momentum", Decimal("0.50"))

        assert target.strategy_name == "momentum"
        assert target.target_weight == Decimal("0.50")
        assert target.last_rebalance is None

    def test_needs_rebalance_no_previous_rebalance(self):
        """Test needs rebalance when no previous rebalance."""
        target = RebalancingTarget("momentum", Decimal("0.50"))

        assert target.needs_rebalance() is True

    def test_needs_rebalance_recent_rebalance(self):
        """Test needs rebalance with recent rebalance."""
        target = RebalancingTarget("momentum", Decimal("0.50"))
        target.update_last_rebalance()

        assert target.needs_rebalance() is False

    def test_needs_rebalance_old_rebalance(self):
        """Test needs rebalance with old rebalance."""
        target = RebalancingTarget("momentum", Decimal("0.50"))
        target.last_rebalance = datetime.utcnow() - timedelta(days=35)

        assert target.needs_rebalance(rebalance_frequency_days=30) is True


class TestDynamicCapitalAdjuster:
    """Tests for TASK-REB-2: Dynamic Capital Adjuster."""

    def test_initialization(self):
        """Test adjuster initialization."""
        adjuster = DynamicCapitalAdjuster()

        assert adjuster.min_allocation == Decimal("0.10")
        assert adjuster.max_allocation == Decimal("0.70")
        assert adjuster.adjustment_factor == Decimal("0.20")

    def test_calculate_adjusted_weight_no_losses(self):
        """Test adjusted weight with no losses."""
        adjuster = DynamicCapitalAdjuster()

        adjusted = adjuster.calculate_adjusted_weight(
            target_weight=Decimal("0.50"),
            consecutive_losses=0,
            recent_performance=Decimal("0.02"),  # Positive performance
        )

        assert adjusted == Decimal("0.50")

    def test_calculate_adjusted_weight_with_losses(self):
        """Test adjusted weight with losses."""
        adjuster = DynamicCapitalAdjuster()

        adjusted = adjuster.calculate_adjusted_weight(
            target_weight=Decimal("0.50"),
            consecutive_losses=2,
            recent_performance=Decimal("0.0"),
        )

        # Should be reduced by 2 * 20% = 40%
        assert adjusted < Decimal("0.50")
        assert adjusted >= Decimal("0.10")  # Above minimum

    def test_calculate_adjusted_weight_poor_performance(self):
        """Test adjusted weight with poor performance."""
        adjuster = DynamicCapitalAdjuster()

        adjusted = adjuster.calculate_adjusted_weight(
            target_weight=Decimal("0.50"),
            consecutive_losses=0,
            recent_performance=Decimal("-0.12"),  # Bad performance
        )

        # Should be reduced by 20% for poor performance
        assert adjusted < Decimal("0.50")
        assert adjusted == Decimal("0.40")  # 50% * 0.8

    def test_should_reduce_allocation_too_many_losses(self):
        """Test should reduce allocation with too many losses."""
        adjuster = DynamicCapitalAdjuster()

        should_reduce = adjuster.should_reduce_allocation(
            consecutive_losses=4,
            recent_performance=Decimal("0.0"),
            threshold_losses=3,
        )

        assert should_reduce is True

    def test_should_reduce_allocation_poor_performance(self):
        """Test should reduce allocation with poor performance."""
        adjuster = DynamicCapitalAdjuster()

        should_reduce = adjuster.should_reduce_allocation(
            consecutive_losses=0,
            recent_performance=Decimal("-0.20"),  # Very poor
        )

        assert should_reduce is True

    def test_calculate_adjusted_weight_enforces_min(self):
        """Test adjusted weight enforces minimum."""
        adjuster = DynamicCapitalAdjuster()

        # Try to reduce below minimum
        adjusted = adjuster.calculate_adjusted_weight(
            target_weight=Decimal("0.15"),
            consecutive_losses=10,
            recent_performance=Decimal("-0.20"),
        )

        assert adjusted >= Decimal("0.10")  # Minimum enforced


class TestPortfolioRebalancer:
    """Tests for TASK-REB-1: Portfolio Rebalancer."""

    def test_initialization(self):
        """Test rebalancer initialization."""
        rebalancer = PortfolioRebalancer()

        assert rebalancer.rebalance_frequency_days == 30
        assert rebalancer.drift_threshold == Decimal("0.05")

    def test_set_target_allocation(self):
        """Test setting target allocation."""
        rebalancer = PortfolioRebalancer()

        rebalancer.set_target_allocation("momentum", Decimal("0.50"))

        assert "momentum" in rebalancer.rebalancing_targets

    def test_calculate_rebalance_needs_no_drift(self):
        """Test rebalance needs with no drift."""
        rebalancer = PortfolioRebalancer()
        rebalancer.set_target_allocation("momentum", Decimal("0.50"))
        # Mark as recently rebalanced to prevent time-based rebalance
        rebalancer.rebalancing_targets["momentum"].update_last_rebalance()

        current_allocations = {"momentum": Decimal("50000")}
        rebalance_needs = rebalancer.calculate_rebalance_needs(
            current_allocations, Decimal("100000")
        )

        # Should not need rebalancing if current meets target and recent rebalance
        assert len(rebalance_needs) == 0 or all(v == Decimal("0") for v in rebalance_needs.values())

    def test_calculate_rebalance_needs_with_drift(self):
        """Test rebalance needs with drift."""
        rebalancer = PortfolioRebalancer()
        rebalancer.set_target_allocation("momentum", Decimal("0.50"))

        # Current is only 30%, target is 50%
        current_allocations = {"momentum": Decimal("30000")}
        rebalance_needs = rebalancer.calculate_rebalance_needs(
            current_allocations, Decimal("100000")
        )

        # Should need to add 20% (50k - 30k = 20k)
        assert "momentum" in rebalance_needs
        assert rebalance_needs["momentum"] > Decimal("0")

    def test_apply_rebalancing_no_losses(self):
        """Test applying rebalancing with no losses."""
        rebalancer = PortfolioRebalancer()
        rebalancer.set_target_allocation("momentum", Decimal("0.50"))

        current_allocations = {"momentum": Decimal("50000")}
        strategy_performance = {
            "momentum": {
                "consecutive_losses": 0,
                "recent_performance": Decimal("0.02"),
            }
        }

        new_allocations = rebalancer.apply_rebalancing(
            current_allocations,
            Decimal("100000"),
            strategy_performance,
        )

        assert "momentum" in new_allocations
        assert new_allocations["momentum"] == Decimal("50000")

    def test_apply_rebalancing_with_losses(self):
        """Test applying rebalancing with consecutive losses."""
        rebalancer = PortfolioRebalancer()
        rebalancer.set_target_allocation("momentum", Decimal("0.50"))

        current_allocations = {"momentum": Decimal("50000")}
        strategy_performance = {
            "momentum": {
                "consecutive_losses": 3,
                "recent_performance": Decimal("-0.08"),
            }
        }

        new_allocations = rebalancer.apply_rebalancing(
            current_allocations,
            Decimal("100000"),
            strategy_performance,
        )

        assert "momentum" in new_allocations
        # Should be reduced due to losses
        assert new_allocations["momentum"] < Decimal("50000")

    def test_get_rebalance_status(self):
        """Test getting rebalance status."""
        rebalancer = PortfolioRebalancer()
        rebalancer.set_target_allocation("momentum", Decimal("0.50"))

        status = rebalancer.get_rebalance_status()

        assert "momentum" in status
        assert status["momentum"]["target_weight"] == 0.50
