"""
Tests for Ernest Chan Execution Algorithms Implementation
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from app.services.execution_algorithms import (
    VWAPExecutor,
    TWAPExecutor,
    ImplementationShortfallExecutor,
    POVExecutor,
    create_execution_plan,
    ExecutionPlan,
    ExecutionSlice,
)


class TestVWAPExecutor:
    """Test VWAP executor."""

    def test_initialization(self):
        """Test VWAP executor initialization."""
        executor = VWAPExecutor()

        assert executor.typical_volume_profile is not None
        assert '09:30-10:00' in executor.typical_volume_profile

    def test_custom_volume_profile(self):
        """Test with custom volume profile."""
        custom_profile = {
            "morning": 0.4,
            "afternoon": 0.6,
        }

        executor = VWAPExecutor(typical_volume_profile=custom_profile)

        assert executor.typical_volume_profile == custom_profile

    def test_create_execution_plan(self):
        """Test VWAP execution plan creation."""
        executor = VWAPExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
        )

        assert isinstance(plan, ExecutionPlan)
        assert plan.symbol == "AAPL"
        assert plan.total_quantity == 10000
        assert plan.side == "buy"
        assert plan.algorithm == "vwap"
        assert len(plan.execution_slices) > 0
        assert plan.start_time is not None
        assert plan.end_time is not None

    def test_vwap_slices_distribution(self):
        """Test that VWAP slices follow volume profile."""
        executor = VWAPExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
        )

        # Verify slices sum to total quantity
        total_slice_qty = sum(slice.quantity for slice in plan.execution_slices)
        assert abs(total_slice_qty - 10000) < 1  # Allow small rounding error

        # Verify each slice has positive quantity
        assert all(slice.quantity > 0 for slice in plan.execution_slices)

    def test_vwap_with_constraints(self):
        """Test VWAP with custom constraints."""
        executor = VWAPExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            max_slices=5,
            min_slice_pct=0.10,
        )

        assert len(plan.execution_slices) <= 5

    def test_market_impact_calculation(self):
        """Test market impact calculation."""
        executor = VWAPExecutor()

        impact = executor._calculate_market_impact(
            quantity=50000,
            symbol="AAPL",
            side="buy",
            daily_volume=1_000_000,
            price=150.0,
        )

        assert impact > 0
        assert isinstance(impact, float)

    def test_timing_risk_calculation(self):
        """Test timing risk calculation."""
        executor = VWAPExecutor()

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=4)

        timing_risk = executor._calculate_timing_risk(
            quantity=10000,
            start_time=start_time,
            end_time=end_time,
            daily_volatility=0.02,
        )

        assert timing_risk > 0
        assert isinstance(timing_risk, float)


class TestTWAPExecutor:
    """Test TWAP executor."""

    def test_initialization(self):
        """Test TWAP executor initialization."""
        executor = TWAPExecutor()
        assert executor is not None

    def test_create_execution_plan(self):
        """Test TWAP execution plan creation."""
        executor = TWAPExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            duration_minutes=60,
            num_slices=12,
        )

        assert isinstance(plan, ExecutionPlan)
        assert plan.symbol == "AAPL"
        assert plan.algorithm == "twap"
        assert len(plan.execution_slices) == 12

    def test_twap_equal_slices(self):
        """Test that TWAP creates approximately equal slices."""
        executor = TWAPExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            duration_minutes=60,
            num_slices=10,
        )

        quantities = [slice.quantity for slice in plan.execution_slices]

        # All slices should be approximately equal
        mean_qty = np.mean(quantities)
        assert all(abs(q - mean_qty) < 100 for q in quantities)

    def test_twap_with_randomization(self):
        """Test TWAP with timing randomization."""
        executor = TWAPExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            duration_minutes=60,
            num_slices=10,
            randomize_timing=True,
            randomization_pct=0.3,
        )

        assert len(plan.execution_slices) == 10

        # Check that times are not perfectly evenly spaced
        intervals = []
        for i in range(1, len(plan.execution_slices)):
            interval = (
                plan.execution_slices[i].target_time -
                plan.execution_slices[i-1].target_time
            ).total_seconds()
            intervals.append(interval)

        # Intervals should vary due to randomization
        assert max(intervals) != min(intervals)

    def test_twap_duration(self):
        """Test that TWAP respects duration."""
        executor = TWAPExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            duration_minutes=120,
            num_slices=12,
        )

        # Execution should span approximately 120 minutes
        actual_duration = (
            plan.end_time - plan.start_time
        ).total_seconds() / 60

        assert abs(actual_duration - 120) < 5  # Allow small tolerance


class TestImplementationShortfallExecutor:
    """Test Implementation Shortfall executor."""

    def test_initialization(self):
        """Test IS executor initialization."""
        from app.services.execution_algorithms import MarketImpactModel

        impact_model = MarketImpactModel(
            permanent_impact_coef=0.1,
            temporary_impact_coef=1.0,
            volatility_impact_coef=1.0,
            daily_volume=1_000_000,
            spread=0.01,
        )

        executor = ImplementationShortfallExecutor(impact_model=impact_model)

        assert executor.impact_model == impact_model

    def test_create_execution_plan(self):
        """Test IS execution plan creation."""
        executor = ImplementationShortfallExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            urgency=0.5,
        )

        assert isinstance(plan, ExecutionPlan)
        assert plan.symbol == "AAPL"
        assert plan.algorithm == "implementation_shortfall"
        assert plan.urgency == 0.5
        assert len(plan.execution_slices) > 0

    def test_urgency_affects_duration(self):
        """Test that urgency affects execution duration."""
        executor = ImplementationShortfallExecutor()

        # Low urgency (patient) - should have longer duration
        patient_plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            urgency=0.1,
        )

        # High urgency (urgent) - should have shorter duration
        urgent_plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            urgency=0.9,
        )

        patient_duration = (patient_plan.end_time - patient_plan.start_time).total_seconds()
        urgent_duration = (urgent_plan.end_time - urgent_plan.start_time).total_seconds()

        assert patient_duration > urgent_duration

    def test_optimal_duration_calculation(self):
        """Test optimal duration calculation."""
        executor = ImplementationShortfallExecutor()

        duration = executor._calculate_optimal_duration(
            quantity=50000,
            urgency=0.5,
            daily_volume=1_000_000,
            daily_volatility=0.02,
        )

        assert duration > 0
        assert isinstance(duration, float)

    def test_trajectory_calculation(self):
        """Test optimal trajectory calculation."""
        executor = ImplementationShortfallExecutor()

        trajectory = executor._calculate_optimal_trajectory(
            quantity=10000,
            duration_minutes=60,
            n_slices=10,
            urgency=0.5,
        )

        assert len(trajectory) == 10
        assert all(q > 0 for q in trajectory)
        assert abs(sum(trajectory) - 10000) < 1  # Sums to total quantity

    def test_front_loaded_trajectory(self):
        """Test front-loaded trajectory for high urgency."""
        executor = ImplementationShortfallExecutor()

        trajectory = executor._calculate_optimal_trajectory(
            quantity=10000,
            duration_minutes=60,
            n_slices=10,
            urgency=0.8,  # High urgency
        )

        # First few slices should be larger than last few
        first_half_avg = np.mean(trajectory[:5])
        second_half_avg = np.mean(trajectory[5:])

        assert first_half_avg > second_half_avg


class TestPOVExecutor:
    """Test POV executor."""

    def test_initialization(self):
        """Test POV executor initialization."""
        executor = POVExecutor()
        assert executor is not None

    def test_create_execution_plan(self):
        """Test POV execution plan creation."""
        executor = POVExecutor()

        plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            participation_rate=0.10,
        )

        assert isinstance(plan, ExecutionPlan)
        assert plan.symbol == "AAPL"
        assert plan.algorithm == "pov"

        # Check that slices have participation_rate set
        for slice in plan.execution_slices:
            assert slice.participation_rate == 0.10

    def test_participation_rate_affects_duration(self):
        """Test that participation rate affects duration."""
        executor = POVExecutor()

        # Low participation rate - longer duration
        low_pov_plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            participation_rate=0.05,
        )

        # High participation rate - shorter duration
        high_pov_plan = executor.create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            participation_rate=0.20,
        )

        low_pov_duration = (low_pov_plan.end_time - low_pov_plan.start_time).total_seconds()
        high_pov_duration = (high_pov_plan.end_time - high_pov_plan.start_time).total_seconds()

        assert low_pov_duration > high_pov_duration

    def test_duration_estimate(self):
        """Test duration estimation."""
        executor = POVExecutor()

        duration = executor._estimate_duration(
            quantity=100000,
            participation_rate=0.10,
            max_duration_minutes=240,
            daily_volume=5_000_000,
        )

        assert duration > 0
        assert duration <= 240  # Should be capped at max


class TestHighLevelFunction:
    """Test high-level execution planning function."""

    def test_create_vwap_plan(self):
        """Test creating VWAP plan via high-level function."""
        plan = create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            algorithm="vwap",
        )

        assert plan.algorithm == "vwap"

    def test_create_twap_plan(self):
        """Test creating TWAP plan via high-level function."""
        plan = create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            algorithm="twap",
            duration_minutes=60,
        )

        assert plan.algorithm == "twap"

    def test_create_is_plan(self):
        """Test creating IS plan via high-level function."""
        plan = create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            algorithm="is",
            urgency=0.5,
        )

        assert plan.algorithm == "implementation_shortfall"

    def test_create_pov_plan(self):
        """Test creating POV plan via high-level function."""
        plan = create_execution_plan(
            symbol="AAPL",
            quantity=10000,
            side="buy",
            algorithm="pov",
            participation_rate=0.10,
        )

        assert plan.algorithm == "pov"

    def test_invalid_algorithm(self):
        """Test with invalid algorithm."""
        with pytest.raises(ValueError):
            create_execution_plan(
                symbol="AAPL",
                quantity=10000,
                side="buy",
                algorithm="invalid_algo",
            )


class TestExecutionPlanValidation:
    """Test ExecutionPlan validation."""

    def test_execution_plan_structure(self):
        """Test ExecutionPlan has all required fields."""
        from app.services.execution_algorithms import ExecutionPlan, ExecutionSlice

        slices = [
            ExecutionSlice(
                slice_number=0,
                quantity=5000,
                target_time=datetime.now(),
                limit_price=None,
                execution_algorithm="vwap",
            )
        ]

        plan = ExecutionPlan(
            symbol="AAPL",
            side="buy",
            total_quantity=10000,
            execution_slices=slices,
            algorithm="vwap",
            urgency=0.5,
            expected_market_impact=5.0,
            expected_timing_risk=10.0,
            estimated_slippage=15.0,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=1),
        )

        assert plan.symbol == "AAPL"
        assert plan.side == "buy"
        assert plan.total_quantity == 10000
        assert len(plan.execution_slices) == 1
