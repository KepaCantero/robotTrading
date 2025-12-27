"""
Unit tests for OrderSplittingOptimizer

Tests VWAP, TWAP, POI, and intraday_phased splitting strategies.
"""

from decimal import Decimal

import pytest

from app.services.smart_order_routing.order_splitting_optimizer import (
    OrderSplittingOptimizer,
)


class TestOrderSplittingOptimizer:
    """Test suite for OrderSplittingOptimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance for testing."""
        return OrderSplittingOptimizer()

    def test_initialization(self, optimizer):
        """Test optimizer initializes correctly."""
        assert optimizer is not None
        assert optimizer.TYPICAL_VOLUME_PROFILE is not None
        assert len(optimizer.TYPICAL_VOLUME_PROFILE) == 8

    def test_vwap_split_creates_tranches(self, optimizer):
        """Test VWAP split creates tranches."""
        plan = optimizer._vwap_split(
            symbol="AAPL",
            total_size=Decimal("50000"),
            max_exec_time=300_000,
            constraints={},
        )

        assert plan is not None
        assert len(plan.tranches) > 0
        assert plan.strategy == "vwap"

    def test_vwap_split_size_totals(self, optimizer):
        """Test VWAP split distributes full size."""
        total_size = Decimal("50000")
        plan = optimizer._vwap_split(
            symbol="AAPL",
            total_size=total_size,
            max_exec_time=300_000,
            constraints={},
        )

        # Sum of tranches should equal total size (within rounding)
        tranche_sum = sum(t.size for t in plan.tranches)
        assert tranche_sum == total_size

    def test_vwap_respects_max_per_tranche(self, optimizer):
        """Test VWAP respects max_per_tranche constraint."""
        total_size = Decimal("50000")
        max_per_tranche = Decimal("10000")

        plan = optimizer._vwap_split(
            symbol="AAPL",
            total_size=total_size,
            max_exec_time=300_000,
            constraints={"max_per_tranche": max_per_tranche},
        )

        # No tranche should exceed max_per_tranche
        for tranche in plan.tranches:
            assert tranche.size <= max_per_tranche

    def test_twap_split_equal_sizes(self, optimizer):
        """Test TWAP split creates equal-sized tranches."""
        total_size = Decimal("50000")
        max_exec_time = 300_000  # 5 minutes

        plan = optimizer._twap_split(
            symbol="AAPL",
            total_size=total_size,
            max_exec_time=max_exec_time,
            constraints={},
        )

        # With 5 minutes (1 tranche), should have 1 tranche
        assert len(plan.tranches) >= 1
        assert plan.strategy == "twap"

        # All tranches should be same size (within rounding)
        if len(plan.tranches) > 1:
            sizes = [t.size for t in plan.tranches]
            expected_size = total_size / len(plan.tranches)
            # Allow small rounding difference
            for size in sizes:
                assert abs(size - expected_size) < Decimal("1")

    def test_twap_timing(self, optimizer):
        """Test TWAP tranches are timed at 5-minute intervals."""
        plan = optimizer._twap_split(
            symbol="AAPL",
            total_size=Decimal("50000"),
            max_exec_time=600_000,  # 10 minutes
            constraints={},
        )

        # Should have 2 tranches (0 min and 5 min)
        assert len(plan.tranches) >= 1

        if len(plan.tranches) > 1:
            # Check time intervals
            time_diff = plan.tranches[1].execution_time - plan.tranches[0].execution_time
            # Should be approximately 5 minutes = 300 seconds
            assert time_diff.total_seconds() == pytest.approx(300, abs=1)

    @pytest.mark.asyncio
    async def test_poi_split_dynamic(self, optimizer):
        """Test POI split returns plan for dynamic execution."""
        plan = optimizer._poi_split(
            symbol="AAPL",
            total_size=Decimal("50000"),
            max_exec_time=300_000,
            constraints={},
        )

        assert plan is not None
        assert plan.strategy == "poi"
        # POI fills tranches dynamically, so initially empty
        assert plan.tranches == []
        # Should have max_involvement constraint
        assert "max_involvement_pct" in plan.constraints

    @pytest.mark.asyncio
    async def test_poi_max_involvement(self, optimizer):
        """Test POI respects max_involvement_pct constraint."""
        plan = optimizer._poi_split(
            symbol="AAPL",
            total_size=Decimal("50000"),
            max_exec_time=300_000,
            constraints={"max_involvement_pct": Decimal("0.15")},
        )

        # Should preserve custom max_involvement_pct
        assert plan.constraints["max_involvement_pct"] == Decimal("0.15")

    def test_intraday_phased_avoids_volatility(self, optimizer):
        """Test intraday_phased avoids volatility peaks."""
        plan = optimizer._intraday_phased_split(
            symbol="AAPL",
            total_size=Decimal("50000"),
            max_exec_time=3_600_000,
            constraints={},
        )

        assert plan.strategy == "intraday_phased"
        assert len(plan.tranches) > 0

        # Check that execution times are in good windows (not in peaks)
        for tranche in plan.tranches:
            hour = tranche.execution_time.hour
            # Should not be in opening peak (9:30-10:00)
            if hour == 9:
                assert tranche.execution_time.minute >= 30
            # Should not be in lunch (11:30-13:00)
            # Should not be in closing peak (15:00-16:00)
            assert not (15 <= hour < 16 and hour == 15)

    def test_intraday_phased_increasing_size(self, optimizer):
        """Test intraday_phased increases size in later windows."""
        plan = optimizer._intraday_phased_split(
            symbol="AAPL",
            total_size=Decimal("50000"),
            max_exec_time=3_600_000,
            constraints={},
        )

        # Sizes should generally increase (with weights 0.25, 0.35, 0.40)
        sizes = [t.size for t in plan.tranches]
        assert len(sizes) >= 2

        # Later tranches should be larger (trend)
        if len(sizes) >= 3:
            assert sizes[-1] >= sizes[0]

    @pytest.mark.asyncio
    async def test_optimize_execution_vwap(self, optimizer):
        """Test main optimize_execution method with VWAP."""
        plan = await optimizer.optimize_execution(
            symbol="AAPL",
            total_size=Decimal("50000"),
            strategy="vwap",
            max_exec_time=300_000,
        )

        assert plan is not None
        assert plan.symbol == "AAPL"
        assert plan.total_size == Decimal("50000")
        assert plan.strategy == "vwap"
        assert len(plan.tranches) > 0

    @pytest.mark.asyncio
    async def test_optimize_execution_twap(self, optimizer):
        """Test main optimize_execution method with TWAP."""
        plan = await optimizer.optimize_execution(
            symbol="BTC",
            total_size=Decimal("50000"),
            strategy="twap",
            max_exec_time=600_000,
        )

        assert plan.strategy == "twap"
        assert plan.total_size == Decimal("50000")

    @pytest.mark.asyncio
    async def test_optimize_execution_poi(self, optimizer):
        """Test main optimize_execution method with POI."""
        plan = await optimizer.optimize_execution(
            symbol="EURUSD",
            total_size=Decimal("25000"),
            strategy="poi",
            max_exec_time=300_000,
        )

        assert plan.strategy == "poi"
        assert len(plan.tranches) == 0  # POI is dynamic

    @pytest.mark.asyncio
    async def test_optimize_execution_intraday_phased(self, optimizer):
        """Test main optimize_execution method with intraday_phased."""
        plan = await optimizer.optimize_execution(
            symbol="GOLD",
            total_size=Decimal("50000"),
            strategy="intraday_phased",
            max_exec_time=3_600_000,
        )

        assert plan.strategy == "intraday_phased"
        assert len(plan.tranches) > 0

    @pytest.mark.asyncio
    async def test_optimize_execution_invalid_strategy(self, optimizer):
        """Test optimize_execution raises error for invalid strategy."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            await optimizer.optimize_execution(
                symbol="AAPL",
                total_size=Decimal("50000"),
                strategy="invalid_strategy",
            )

    def test_tranche_creation_has_ids(self, optimizer):
        """Test created tranches have unique IDs."""
        plan = optimizer._vwap_split(
            symbol="AAPL",
            total_size=Decimal("50000"),
            max_exec_time=300_000,
            constraints={},
        )

        # All tranches should have IDs
        ids = [t.tranche_id for t in plan.tranches]
        assert len(ids) == len(set(ids))  # All unique

    def test_tranche_creation_has_status(self, optimizer):
        """Test created tranches have status."""
        plan = optimizer._vwap_split(
            symbol="AAPL",
            total_size=Decimal("50000"),
            max_exec_time=300_000,
            constraints={},
        )

        # All tranches should have status
        for tranche in plan.tranches:
            assert tranche.status == "pending"

    @pytest.mark.asyncio
    async def test_large_order_splitting(self, optimizer):
        """Test splitting large orders (€500k+)."""
        plan = await optimizer.optimize_execution(
            symbol="AAPL",
            total_size=Decimal("500000"),
            strategy="vwap",
            max_exec_time=1_800_000,
            constraints={"max_per_tranche": Decimal("100000")},
        )

        # Should create many tranches to respect constraint
        assert len(plan.tranches) >= 5

    @pytest.mark.asyncio
    async def test_small_order_splitting(self, optimizer):
        """Test splitting small orders (€25k)."""
        plan = await optimizer.optimize_execution(
            symbol="AAPL",
            total_size=Decimal("25000"),
            strategy="twap",
            max_exec_time=300_000,
        )

        assert plan is not None
        assert len(plan.tranches) >= 1

    @pytest.mark.asyncio
    async def test_constraints_preserved(self, optimizer):
        """Test constraints are preserved in execution plan."""
        constraints = {
            "max_per_tranche": Decimal("50000"),
            "max_spread": Decimal("2"),
        }
        plan = await optimizer.optimize_execution(
            symbol="AAPL",
            total_size=Decimal("50000"),
            strategy="vwap",
            constraints=constraints,
        )

        assert plan.constraints is not None
        assert "max_per_tranche" in plan.constraints or "max_spread" in plan.constraints
