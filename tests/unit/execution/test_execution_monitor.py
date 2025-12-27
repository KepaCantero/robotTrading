"""
Unit tests for ExecutionCostMonitor

Tests cost tracking, overrun detection, and monitoring functionality.
"""

from decimal import Decimal

import pytest

from app.services.smart_order_routing.execution_cost_monitor import ExecutionCostMonitor


class TestExecutionCostMonitor:
    """Test suite for ExecutionCostMonitor."""

    @pytest.fixture
    def monitor(self):
        """Create monitor instance for testing."""
        return ExecutionCostMonitor()

    def test_initialization(self, monitor):
        """Test monitor initializes correctly."""
        assert monitor is not None
        assert monitor.executions == {}
        assert monitor.tranche_costs == {}

    def test_start_monitoring(self, monitor):
        """Test starting monitoring of new execution."""
        execution_id = "exec_001"
        planned_cost = Decimal("1000")
        total_tranches = 4

        monitoring = monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=planned_cost,
            total_tranches=total_tranches,
        )

        assert monitoring is not None
        assert monitoring.execution_id == execution_id
        assert monitoring.planned_cost == planned_cost
        assert monitoring.tranches_total == total_tranches
        assert monitoring.actual_costs == Decimal("0")
        assert monitoring.tranches_completed == 0

    def test_start_monitoring_stores_execution(self, monitor):
        """Test start_monitoring stores execution in monitor."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=4,
        )

        assert execution_id in monitor.executions

    def test_record_tranche_execution_basic(self, monitor):
        """Test recording tranche execution."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )

        cost, record = monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.50"),
            commission_cost=Decimal("10"),
        )

        assert cost == Decimal("510.00")  # (150.50 - 150) * 1000 + 10 = 500 + 10

    def test_record_tranche_updates_costs(self, monitor):
        """Test recording tranche updates cumulative costs."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=2,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.50"),
            commission_cost=Decimal("10"),
        )

        monitoring = monitor.get_monitoring_status(execution_id)
        assert monitoring.actual_costs == Decimal("510.00")
        assert monitoring.tranches_completed == 1

    def test_record_tranche_increments_counter(self, monitor):
        """Test recording tranches increments counter."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=3,
        )

        for i in range(3):
            monitor.record_tranche_execution(
                execution_id=execution_id,
                tranche_id=f"tranche_{i:03d}",
                symbol="AAPL",
                executed_size=Decimal("100"),
                target_price=Decimal("150"),
                executed_price=Decimal("150.10"),
                commission_cost=Decimal("1"),
            )

        monitoring = monitor.get_monitoring_status(execution_id)
        assert monitoring.tranches_completed == 3

    def test_tranche_cost_breakdown(self, monitor):
        """Test tranche cost is properly broken down."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )

        cost, record = monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("151"),  # 1 bps impact
            commission_cost=Decimal("5"),
        )

        assert record["slippage_cost"] == Decimal("1000")
        assert record["commission_cost"] == Decimal("5")
        assert record["total_cost"] == Decimal("1005")

    def test_slippage_bps_calculation(self, monitor):
        """Test slippage in basis points is calculated correctly."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )

        cost, record = monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("100000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.50"),
            commission_cost=Decimal("0"),
        )

        # 0.50 / 150 = 0.00333... ≈ 33.3 bps
        expected_bps = (Decimal("50000") / Decimal("100000")) * Decimal("10000")
        assert record["slippage_bps"] == expected_bps

    def test_cost_overrun_detection(self, monitor):
        """Test cost overrun is detected."""
        execution_id = "exec_001"
        planned_cost = Decimal("500")
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=planned_cost,
            total_tranches=1,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.70"),  # Higher slippage
            commission_cost=Decimal("100"),
        )

        monitoring = monitor.get_monitoring_status(execution_id)
        assert monitoring.actual_costs > monitoring.planned_cost
        assert monitoring.cost_overrun > Decimal("0")

    def test_cost_overrun_percentage(self, monitor):
        """Test cost overrun percentage is calculated."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("151"),
            commission_cost=Decimal("100"),
        )

        monitoring = monitor.get_monitoring_status(execution_id)
        # Cost: 1000 + 100 = 1100, overrun = 100, % = 10%
        assert monitoring.cost_overrun_pct == Decimal("10")

    def test_within_budget_true(self, monitor):
        """Test is_within_budget when costs are under budget."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.10"),
            commission_cost=Decimal("50"),
        )

        monitoring = monitor.get_monitoring_status(execution_id)
        assert monitoring.is_within_budget is True

    def test_within_budget_false(self, monitor):
        """Test is_within_budget when costs exceed budget."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("500"),
            total_tranches=1,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("151"),
            commission_cost=Decimal("100"),
        )

        monitoring = monitor.get_monitoring_status(execution_id)
        assert monitoring.is_within_budget is False

    def test_complete_execution(self, monitor):
        """Test completing execution."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.50"),
            commission_cost=Decimal("10"),
        )

        final_monitoring = monitor.complete_execution(execution_id)
        assert final_monitoring.completed_at is not None

    def test_get_monitoring_status_unknown_execution(self, monitor):
        """Test getting status for unknown execution raises error."""
        with pytest.raises(ValueError, match="not found"):
            monitor.get_monitoring_status("unknown_id")

    def test_get_cost_breakdown(self, monitor):
        """Test getting cost breakdown."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=2,
        )

        for i in range(2):
            monitor.record_tranche_execution(
                execution_id=execution_id,
                tranche_id=f"tranche_{i:03d}",
                symbol="AAPL",
                executed_size=Decimal("500"),
                target_price=Decimal("150"),
                executed_price=Decimal("150.10"),
                commission_cost=Decimal("10"),
            )

        breakdown = monitor.get_cost_breakdown(execution_id)
        assert breakdown["execution_id"] == execution_id
        assert breakdown["tranches_completed"] == 2
        assert "total_slippage" in breakdown
        assert "total_commission" in breakdown

    def test_compare_to_estimate(self, monitor):
        """Test comparing actual to estimated costs."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("100000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.50"),
            commission_cost=Decimal("0"),
        )

        comparison = monitor.compare_to_estimate(
            execution_id=execution_id,
            estimated_slippage_bps=Decimal("33"),
            estimated_slippage_usd=Decimal("50000"),
        )

        assert comparison["execution_id"] == execution_id
        assert "variance_pct" in comparison
        assert "estimate_accuracy" in comparison

    def test_estimate_remaining_budget(self, monitor):
        """Test estimating remaining budget."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=2,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.25"),
            commission_cost=Decimal("100"),
        )

        remaining, estimated_total = monitor.estimate_remaining_budget(execution_id)

        assert remaining > Decimal("0")
        assert estimated_total > Decimal("0")

    def test_should_abort_execution_normal(self, monitor):
        """Test should_abort_execution returns False for normal costs."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=2,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.10"),
            commission_cost=Decimal("10"),
        )

        should_abort, reason = monitor.should_abort_execution(execution_id)
        assert should_abort is False

    def test_should_abort_execution_critical_overrun(self, monitor):
        """Test should_abort_execution returns True for critical overrun."""
        execution_id = "exec_001"
        monitor.start_monitoring(
            execution_id=execution_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )

        monitor.record_tranche_execution(
            execution_id=execution_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("151.50"),  # 150 bps slippage
            commission_cost=Decimal("500"),
        )

        should_abort, reason = monitor.should_abort_execution(execution_id)
        assert should_abort is True

    def test_multiple_executions_tracked_independently(self, monitor):
        """Test multiple executions are tracked independently."""
        exec_1_id = "exec_001"
        exec_2_id = "exec_002"

        monitor.start_monitoring(
            execution_id=exec_1_id,
            planned_cost_budget=Decimal("1000"),
            total_tranches=1,
        )
        monitor.start_monitoring(
            execution_id=exec_2_id,
            planned_cost_budget=Decimal("2000"),
            total_tranches=1,
        )

        monitor.record_tranche_execution(
            execution_id=exec_1_id,
            tranche_id="tranche_001",
            symbol="AAPL",
            executed_size=Decimal("1000"),
            target_price=Decimal("150"),
            executed_price=Decimal("150.10"),
            commission_cost=Decimal("10"),
        )

        status_1 = monitor.get_monitoring_status(exec_1_id)
        status_2 = monitor.get_monitoring_status(exec_2_id)

        assert status_1.tranches_completed == 1
        assert status_2.tranches_completed == 0
