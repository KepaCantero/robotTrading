"""
Unit tests for LargePositionBuilder

Tests position building strategies, execution window selection, and impact analysis.
"""

import asyncio
from decimal import Decimal

import pytest

from app.services.position_builder.large_position_builder import (
    IntraDayExecutionScheduler,
    LargePositionBuilder,
)


class TestIntraDayExecutionScheduler:
    """Test suite for IntraDayExecutionScheduler."""

    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance for testing."""
        return IntraDayExecutionScheduler()

    def test_initialization(self, scheduler):
        """Test scheduler initializes correctly."""
        assert scheduler is not None
        assert len(scheduler.GOOD_EXECUTION_WINDOWS) == 4

    def test_find_good_windows_default(self, scheduler):
        """Test finding default number of good windows."""
        windows = scheduler.find_good_windows()
        assert len(windows) > 0
        assert len(windows) <= 4

    def test_find_good_windows_custom_count(self, scheduler):
        """Test finding custom number of windows."""
        windows = scheduler.find_good_windows(num_windows=3)
        assert len(windows) == 3

    def test_find_good_windows_ordered(self, scheduler):
        """Test good windows are in chronological order."""
        windows = scheduler.find_good_windows(num_windows=4)
        start_times = [w.start for w in windows]
        # Check they're ordered
        assert start_times == sorted(start_times)

    def test_find_good_windows_avoids_peaks(self, scheduler):
        """Test good windows avoid volatility peaks."""
        windows = scheduler.find_good_windows(num_windows=4)

        for window in windows:
            # Check against known volatile periods
            start_hour = int(window.start.split(":")[0])

            # Should not be in opening peak (9:30-10:00)
            if start_hour == 9:
                start_min = int(window.start.split(":")[1])
                assert start_min >= 30

            # Should not be in lunch (11:30-13:00)
            assert not (11 < start_hour < 13)

            # Should not be in closing peak (15:00-16:00)
            assert not (15 <= start_hour < 16)

    def test_time_window_to_datetime(self, scheduler):
        """Test converting TimeWindow to datetime."""
        from app.services.smart_order_routing.models import TimeWindow

        window = TimeWindow(start="10:30", end="11:15", name="test")
        dt = scheduler.time_window_to_datetime(window)

        assert dt.hour == 10
        assert dt.minute == 30
        assert dt.second == 0

    def test_is_in_volatile_period(self, scheduler):
        """Test volatile period detection."""
        # Opening peak
        assert scheduler.is_in_volatile_period("09:45") is True

        # Lunch
        assert scheduler.is_in_volatile_period("12:00") is True

        # Closing peak
        assert scheduler.is_in_volatile_period("15:30") is True

        # Good window
        assert scheduler.is_in_volatile_period("10:30") is False


class TestLargePositionBuilder:
    """Test suite for LargePositionBuilder."""

    @pytest.fixture
    def builder(self):
        """Create builder instance for testing."""
        return LargePositionBuilder()

    @pytest.fixture
    def event_loop(self):
        """Create event loop for async tests."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    def test_initialization(self, builder):
        """Test builder initializes correctly."""
        assert builder is not None
        assert builder.scheduler is not None
        assert Decimal("25000") == builder.MIN_POSITION_SIZE

    @pytest.mark.asyncio
    async def test_build_position_basic(self, builder):
        """Test building a basic position."""
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
        )

        assert plan is not None
        assert plan.symbol == "AAPL"
        assert plan.total_size == Decimal("50000")
        assert plan.strategy == "intraday_phased"
        assert len(plan.tranches) > 0

    @pytest.mark.asyncio
    async def test_build_position_creates_tranches(self, builder):
        """Test build_position creates correct number of tranches."""
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
            num_tranches=4,
        )

        assert len(plan.tranches) == 4

    @pytest.mark.asyncio
    async def test_build_position_sum_equals_target(self, builder):
        """Test tranches sum to target size."""
        target = Decimal("50000")
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=target,
            num_tranches=4,
        )

        total_allocated = sum(t.size for t in plan.tranches)
        assert total_allocated == target

    @pytest.mark.asyncio
    async def test_build_position_too_small(self, builder):
        """Test build_position rejects orders too small."""
        with pytest.raises(ValueError, match="below minimum"):
            await builder.build_position(
                symbol="AAPL",
                target_size=Decimal("10000"),  # Too small
            )

    @pytest.mark.asyncio
    async def test_build_position_with_target_price(self, builder):
        """Test build_position with target price."""
        target_price = Decimal("150.25")
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
            target_avg_price=target_price,
        )

        # All tranches should have target price
        for tranche in plan.tranches:
            assert tranche.target_price == target_price

    @pytest.mark.asyncio
    async def test_build_position_default_tranches(self, builder):
        """Test default number of tranches is 4."""
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
        )

        # Default is 4 tranches
        assert len(plan.tranches) == 4

    @pytest.mark.asyncio
    async def test_build_position_custom_tranches(self, builder):
        """Test custom number of tranches."""
        # Only 4 good execution windows available, so test 1-4
        for num_tranches in [1, 2, 3, 4]:
            plan = await builder.build_position(
                symbol="AAPL",
                target_size=Decimal("50000"),
                num_tranches=num_tranches,
            )
            assert len(plan.tranches) == num_tranches

    @pytest.mark.asyncio
    async def test_build_position_invalid_tranche_count(self, builder):
        """Test invalid tranche count is rejected."""
        with pytest.raises(ValueError, match="between 1 and 5"):
            await builder.build_position(
                symbol="AAPL",
                target_size=Decimal("50000"),
                num_tranches=6,  # Invalid
            )

    @pytest.mark.asyncio
    async def test_build_position_tranches_increasing_size(self, builder):
        """Test tranches increase in size over time."""
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
            num_tranches=4,
        )

        sizes = [t.size for t in plan.tranches]

        # Later tranches should be larger or equal to earlier ones (trend)
        assert sizes[-1] >= sizes[0]

    @pytest.mark.asyncio
    async def test_build_position_all_tranches_have_ids(self, builder):
        """Test all tranches have unique IDs."""
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
            num_tranches=4,
        )

        ids = [t.tranche_id for t in plan.tranches]
        assert len(ids) == len(set(ids))  # All unique

    @pytest.mark.asyncio
    async def test_build_position_all_tranches_pending(self, builder):
        """Test all tranches start in pending status."""
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
            num_tranches=4,
        )

        for tranche in plan.tranches:
            assert tranche.status == "pending"

    @pytest.mark.asyncio
    async def test_build_position_execution_windows(self, builder):
        """Test tranches have execution windows assigned."""
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
            num_tranches=4,
        )

        for tranche in plan.tranches:
            assert tranche.execution_window is not None
            assert tranche.execution_window.start is not None
            assert tranche.execution_window.end is not None

    @pytest.mark.asyncio
    async def test_build_position_execution_times(self, builder):
        """Test tranches have execution times assigned."""
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
            num_tranches=4,
        )

        for tranche in plan.tranches:
            assert tranche.execution_time is not None

    def test_allocate_size_weights_4_tranches(self, builder):
        """Test size allocation weights for 4 tranches."""
        from app.services.smart_order_routing.models import TimeWindow

        windows = [
            TimeWindow(start="10:30", end="11:15", name="w1"),
            TimeWindow(start="13:00", end="14:15", name="w2"),
            TimeWindow(start="14:30", end="15:00", name="w3"),
            TimeWindow(start="16:00", end="16:30", name="w4"),
        ]

        tranches = builder._allocate_size_to_windows(
            symbol="AAPL",
            total_size=Decimal("100"),
            windows=windows,
        )

        # Expected weights: 0.20, 0.24, 0.26, 0.30
        assert abs(tranches[0].size - Decimal("20")) < Decimal("1")
        assert abs(tranches[1].size - Decimal("24")) < Decimal("1")
        assert abs(tranches[2].size - Decimal("26")) < Decimal("1")
        assert abs(tranches[3].size - Decimal("30")) < Decimal("1")

    def test_calculate_position_impact(self, builder):
        """Test position impact calculation."""
        impact = builder.calculate_position_impact(
            symbol="AAPL",
            position_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            num_tranches=4,
        )

        assert impact is not None
        assert "single_execution_impact" in impact
        assert "tranche_impacts_combined" in impact
        assert "impact_reduction_pct" in impact

        # Splitting should reduce impact
        assert impact["impact_reduction_pct"] > Decimal("0")

    def test_calculate_position_impact_no_split(self, builder):
        """Test position impact with no splitting (1 tranche)."""
        impact = builder.calculate_position_impact(
            symbol="AAPL",
            position_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            num_tranches=1,
        )

        # Single execution: no reduction
        assert impact["impact_reduction_pct"] == Decimal("0")

    def test_calculate_position_impact_more_tranches(self, builder):
        """Test impact reduction increases with more tranches."""
        impact_2 = builder.calculate_position_impact(
            symbol="AAPL",
            position_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            num_tranches=2,
        )

        impact_4 = builder.calculate_position_impact(
            symbol="AAPL",
            position_size=Decimal("50000"),
            daily_volume=Decimal("10000000"),
            num_tranches=4,
        )

        # More tranches = more impact reduction
        assert impact_4["impact_reduction_pct"] > impact_2["impact_reduction_pct"]

    def test_estimate_build_duration(self, builder):
        """Test estimating build duration."""
        duration, readable = builder.estimate_build_duration(
            symbol="AAPL",
            num_tranches=4,
        )

        assert duration is not None
        assert readable is not None
        assert "hour" in readable

    def test_estimate_build_duration_1_tranche(self, builder):
        """Test duration for single tranche."""
        duration_1, _ = builder.estimate_build_duration("AAPL", 1)
        duration_2, _ = builder.estimate_build_duration("AAPL", 2)

        # More tranches = longer duration
        assert duration_2 > duration_1

    @pytest.mark.asyncio
    async def test_build_large_position(self, builder):
        """Test building very large position."""
        # Maximum 4 tranches available (4 good execution windows)
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("500000"),
            num_tranches=4,
        )

        assert len(plan.tranches) == 4
        total = sum(t.size for t in plan.tranches)
        assert total == Decimal("500000")

    @pytest.mark.asyncio
    async def test_build_position_realistic_scenario(self, builder):
        """Test realistic position building scenario."""
        # Build €50k position over 6 hours in 4 tranches
        plan = await builder.build_position(
            symbol="AAPL",
            target_size=Decimal("50000"),
            target_avg_price=Decimal("150.50"),
            max_execution_hours=6,
            num_tranches=4,
        )

        # Verify plan structure
        assert len(plan.tranches) == 4
        assert sum(t.size for t in plan.tranches) == Decimal("50000")

        # Verify all tranches have required fields
        for tranche in plan.tranches:
            assert tranche.symbol == "AAPL"
            assert tranche.target_price == Decimal("150.50")
            assert tranche.execution_window is not None
            assert tranche.execution_time is not None
