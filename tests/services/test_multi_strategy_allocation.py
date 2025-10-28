"""
Comprehensive tests for Multi-Strategy Portfolio Allocation (TASK-PA-1, PA-2, PORT-SEL-1).
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.services.multi_strategy_allocation import (
    DynamicPortfolioSelector,
    MultiStrategyAllocationManager,
    StrategyCapitalAllocation,
)


class TestStrategyCapitalAllocation:
    """Tests for TASK-PA-1: Strategy Capital Allocation."""

    def test_initialization(self):
        """Test initializing strategy allocation."""
        allocation = StrategyCapitalAllocation(
            strategy_name="momentum",
            target_weight=Decimal("0.50"),
            min_weight=Decimal("0.30"),
            max_weight=Decimal("0.70"),
        )

        assert allocation.strategy_name == "momentum"
        assert allocation.target_weight == Decimal("0.50")
        assert allocation.min_weight == Decimal("0.30")
        assert allocation.max_weight == Decimal("0.70")
        assert allocation.current_weight == Decimal("0.50")

    def test_allocate_capital(self):
        """Test capital allocation calculation."""
        allocation = StrategyCapitalAllocation(
            strategy_name="momentum",
            target_weight=Decimal("0.50"),
            min_weight=Decimal("0.30"),
            max_weight=Decimal("0.70"),
        )

        allocated = allocation.allocate(Decimal("100000"))

        assert allocated == Decimal("50000")  # 50% of 100k
        assert allocation.allocated_capital == Decimal("50000")

    def test_update_weight_within_bounds(self):
        """Test updating weight within allowed bounds."""
        allocation = StrategyCapitalAllocation(
            strategy_name="momentum",
            target_weight=Decimal("0.50"),
            min_weight=Decimal("0.30"),
            max_weight=Decimal("0.70"),
        )

        allocation.update_weight(Decimal("0.60"))
        assert allocation.current_weight == Decimal("0.60")

    def test_update_weight_clamped_to_max(self):
        """Test weight clamped to maximum."""
        allocation = StrategyCapitalAllocation(
            strategy_name="momentum",
            target_weight=Decimal("0.50"),
            min_weight=Decimal("0.30"),
            max_weight=Decimal("0.70"),
        )

        allocation.update_weight(Decimal("0.80"))
        assert allocation.current_weight == Decimal("0.70")  # Clamped to max

    def test_update_weight_clamped_to_min(self):
        """Test weight clamped to minimum."""
        allocation = StrategyCapitalAllocation(
            strategy_name="momentum",
            target_weight=Decimal("0.50"),
            min_weight=Decimal("0.30"),
            max_weight=Decimal("0.70"),
        )

        allocation.update_weight(Decimal("0.20"))
        assert allocation.current_weight == Decimal("0.30")  # Clamped to min

    def test_add_performance_data(self):
        """Test adding performance data."""
        allocation = StrategyCapitalAllocation(
            strategy_name="momentum",
            target_weight=Decimal("0.50"),
            min_weight=Decimal("0.30"),
            max_weight=Decimal("0.70"),
        )

        allocation.add_performance_data(
            datetime.utcnow(), Decimal("1000"), Decimal("0.02")
        )

        assert len(allocation.performance_data) == 1
        assert allocation.performance_data[0]["pnl"] == Decimal("1000")

    def test_calculate_rolling_returns(self):
        """Test calculating rolling returns."""
        allocation = StrategyCapitalAllocation(
            strategy_name="momentum",
            target_weight=Decimal("0.50"),
            min_weight=Decimal("0.30"),
            max_weight=Decimal("0.70"),
        )

        # Add some performance data
        allocation.add_performance_data(
            datetime.utcnow() - timedelta(days=15), Decimal("500"), Decimal("0.01")
        )
        allocation.add_performance_data(
            datetime.utcnow() - timedelta(days=10), Decimal("300"), Decimal("0.01")
        )
        allocation.add_performance_data(
            datetime.utcnow() - timedelta(days=5), Decimal("200"), Decimal("0.01")
        )

        rolling_returns = allocation.calculate_rolling_returns(days=30)
        assert rolling_returns > Decimal("0")


class TestMultiStrategyAllocationManager:
    """Tests for TASK-PA-2: Multi-Strategy Allocation Manager."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = MultiStrategyAllocationManager(Decimal("100000"))

        assert manager.total_capital == Decimal("100000")
        assert len(manager.strategy_allocations) == 3
        assert "momentum" in manager.strategy_allocations
        assert "mean_reversion" in manager.strategy_allocations
        assert "pairs_trading" in manager.strategy_allocations

    def test_default_allocations(self):
        """Test default allocation weights."""
        manager = MultiStrategyAllocationManager(Decimal("100000"))

        momentum = manager.strategy_allocations["momentum"]
        mean_rev = manager.strategy_allocations["mean_reversion"]
        pairs = manager.strategy_allocations["pairs_trading"]

        assert momentum.target_weight == Decimal("0.50")  # 50%
        assert mean_rev.target_weight == Decimal("0.25")  # 25%
        assert pairs.target_weight == Decimal("0.25")  # 25%

        # Should sum to 1.0
        total = momentum.target_weight + mean_rev.target_weight + pairs.target_weight
        assert total == Decimal("1.00")

    def test_allocate_capital(self):
        """Test capital allocation."""
        manager = MultiStrategyAllocationManager(Decimal("100000"))

        allocations = manager.allocate_capital()

        assert allocations["momentum"] == Decimal("50000")  # 50% of 100k
        assert allocations["mean_reversion"] == Decimal("25000")  # 25% of 100k
        assert allocations["pairs_trading"] == Decimal("25000")  # 25% of 100k

        # Check total
        total = sum(allocations.values())
        assert total == Decimal("100000")

    def test_get_allocation_for_strategy(self):
        """Test getting allocation for specific strategy."""
        manager = MultiStrategyAllocationManager(Decimal("100000"))

        # Allocate capital first
        manager.allocate_capital()

        momentum_capital = manager.get_allocation_for_strategy("momentum")
        assert momentum_capital == Decimal("50000")

        unknown_capital = manager.get_allocation_for_strategy("unknown_strategy")
        assert unknown_capital == Decimal("0")

    def test_update_total_capital(self):
        """Test updating total capital."""
        manager = MultiStrategyAllocationManager(Decimal("100000"))

        manager.update_total_capital(Decimal("200000"))

        assert manager.total_capital == Decimal("200000")

        # Reallocate with new capital
        allocations = manager.allocate_capital()
        assert allocations["momentum"] == Decimal("100000")  # 50% of 200k


class TestDynamicPortfolioSelector:
    """Tests for TASK-PORT-SEL-1: Dynamic Portfolio Selector."""

    @pytest.fixture
    def manager(self):
        """Create a manager for testing."""
        return MultiStrategyAllocationManager(Decimal("100000"))

    @pytest.fixture
    def selector(self, manager):
        """Create a selector for testing."""
        return DynamicPortfolioSelector(manager)

    def test_initialization(self, selector):
        """Test selector initialization."""
        assert selector.allocation_manager is not None
        assert selector.rebalance_threshold == Decimal("0.05")

    def test_update_strategy_performance(self, selector):
        """Test updating strategy performance."""
        selector.update_strategy_performance(
            "momentum", datetime.utcnow(), Decimal("1000"), Decimal("0.02")
        )

        allocation = selector.allocation_manager.strategy_allocations["momentum"]
        assert len(allocation.performance_data) == 1

    def test_should_rebalance_no_drift(self, selector):
        """Test rebalancing check with no drift."""
        # No rebalancing needed if within threshold
        result = selector.should_rebalance()
        assert result is False

    def test_rebalance_allocations_basic(self, selector):
        """Test basic rebalancing."""
        # Add some performance data
        selector.update_strategy_performance(
            "momentum", datetime.utcnow() - timedelta(days=15), Decimal("1000"), Decimal("0.02")
        )
        selector.update_strategy_performance(
            "mean_reversion", datetime.utcnow() - timedelta(days=10), Decimal("500"), Decimal("0.01")
        )

        allocations = selector.rebalance_allocations()

        # Should return allocations for all strategies
        assert "momentum" in allocations
        assert "mean_reversion" in allocations
        assert "pairs_trading" in allocations

        # Allocations should sum to total capital
        total = sum(allocations.values())
        assert total == Decimal("100000")

    def test_rebalance_allocations_no_data(self, selector):
        """Test rebalancing when no performance data."""
        allocations = selector.rebalance_allocations()

        # Should use target weights when no data
        assert allocations["momentum"] == Decimal("50000")
        assert allocations["mean_reversion"] == Decimal("25000")
        assert allocations["pairs_trading"] == Decimal("25000")
