"""
Tests for Error Budget Manager - SRE Rule 20 Compliance
"""

import os
import tempfile
from datetime import datetime
from decimal import Decimal

import pytest

from app.sre.error_budgets.error_budget_manager import (
    BudgetAllowance,
    BudgetPeriod,
    BudgetStatus,
    ErrorBudgetConfig,
    ErrorBudgetManager,
    TimeWindow,
    get_error_budget_manager,
)


@pytest.fixture
def temp_db_path():
    """Create temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test_budget.db")


@pytest.fixture
async def budget_manager(temp_db_path):
    """Create test budget manager."""
    config = ErrorBudgetConfig(
        target_slo=Decimal("0.995"),
        period=BudgetPeriod.MONTHLY,
        db_path=temp_db_path,
    )

    manager = ErrorBudgetManager(
        service_name="test_service",
        config=config,
    )

    await manager.initialize()
    yield manager

    # Cleanup
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)


class TestBudgetAllowance:
    """Test BudgetAllowance value object."""

    def test_from_slo_calculation(self):
        """Test budget allowance calculation from SLO."""
        allowance = BudgetAllowance.from_slo(
            total_minutes=43200,  # 30 days
            slo_percentage=Decimal("0.995"),
            period=BudgetPeriod.MONTHLY,
        )

        assert allowance.total_minutes == 43200
        assert allowance.target_slo == Decimal("0.995")
        assert allowance.allowed_downtime_minutes == 216  # 3.6 hours
        assert allowance.allowed_downtime_seconds == 12960  # 216 minutes

    def test_high_slo_strict_budget(self):
        """Test that higher SLO results in stricter budget."""
        allowance_99 = BudgetAllowance.from_slo(
            total_minutes=43200,
            slo_percentage=Decimal("0.99"),
            period=BudgetPeriod.MONTHLY,
        )

        allowance_99_9 = BudgetAllowance.from_slo(
            total_minutes=43200,
            slo_percentage=Decimal("0.999"),
            period=BudgetPeriod.MONTHLY,
        )

        # 99.9% SLO should have smaller budget
        assert allowance_99_9.allowed_downtime_minutes < allowance_99.allowed_downtime_minutes


class TestTimeWindow:
    """Test TimeWindow value object."""

    def test_duration_calculation(self):
        """Test time window duration calculation."""
        start = datetime(2026, 1, 1, 0, 0, 0)
        end = datetime(2026, 1, 2, 0, 0, 0)

        window = TimeWindow(start, end)

        assert window.duration_minutes == 1440  # 24 hours
        assert window.duration_hours == 24.0

    def test_contains_timestamp(self):
        """Test timestamp containment check."""
        start = datetime(2026, 1, 1, 0, 0, 0)
        end = datetime(2026, 1, 2, 0, 0, 0)

        window = TimeWindow(start, end)

        # Inside window
        assert window.contains(datetime(2026, 1, 1, 12, 0, 0))

        # Outside window
        assert not window.contains(datetime(2026, 1, 3, 0, 0, 0))


class TestErrorBudgetManager:
    """Test ErrorBudgetManager core functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, budget_manager):
        """Test manager initialization creates state."""
        state = await budget_manager.get_current_state()

        assert state is not None
        assert state.service_name == "test_service"
        assert state.status == BudgetStatus.HEALTHY
        assert state.consumption.downtime_minutes == 0

    @pytest.mark.asyncio
    async def test_record_downtime(self, budget_manager):
        """Test recording downtime updates budget."""
        state = await budget_manager.record_downtime(
            downtime_minutes=10,
            error_type="test",
            description="Test downtime",
        )

        assert state.consumption.downtime_minutes == 10
        assert state.consumption.error_count == 1
        assert len(state.consumption.incidents) == 1

    @pytest.mark.asyncio
    async def test_budget_exhaustion_detection(self, budget_manager):
        """Test budget exhaustion is detected correctly."""
        # Record enough downtime to exhaust budget
        # Monthly budget for 99.5% SLO = 216 minutes
        await budget_manager.record_downtime(
            downtime_minutes=200,  # Close to exhaustion
            error_type="test",
            description="Major outage",
        )

        state = await budget_manager.get_current_state()

        # Should be exhausted or critical
        assert state.status in (BudgetStatus.CRITICAL, BudgetStatus.EXHAUSTED)
        assert state.remaining_percentage < Decimal("10")

    @pytest.mark.asyncio
    async def test_remaining_percentage_calculation(self, budget_manager):
        """Test remaining percentage calculation."""
        # Record 50% of budget
        allowance = budget_manager._current_state.allowance
        half_budget = allowance.allowed_downtime_minutes // 2

        await budget_manager.record_downtime(
            downtime_minutes=half_budget,
            error_type="test",
            description="Half budget consumed",
        )

        state = await budget_manager.get_current_state()

        # Should have ~50% remaining
        assert Decimal("45") < state.remaining_percentage < Decimal("55")

    @pytest.mark.asyncio
    async def test_actual_slo_calculation(self, budget_manager):
        """Test actual SLO calculation."""
        # Record some downtime
        await budget_manager.record_downtime(
            downtime_minutes=60,
            error_type="test",
            description="1 hour outage",
        )

        state = await budget_manager.get_current_state()

        # Actual SLO should be slightly below target
        assert state.actual_slo < state.allowance.target_slo
        assert state.actual_slo > Decimal("0.99")  # Still above 99%

    @pytest.mark.asyncio
    async def test_deployment_allowed_when_healthy(self, budget_manager):
        """Test deployment is allowed when budget is healthy."""
        allowed, reason = await budget_manager.check_deployment_allowed()

        assert allowed is True
        assert "allowed" in reason.lower()

    @pytest.mark.asyncio
    async def test_deployment_blocked_when_exhausted(self, budget_manager):
        """Test deployment is blocked when budget exhausted."""
        # Exhaust the budget
        allowance = budget_manager._current_state.allowance
        await budget_manager.record_downtime(
            downtime_minutes=allowance.allowed_downtime_minutes,
            error_type="test",
            description="Budget exhausted",
        )

        allowed, reason = await budget_manager.check_deployment_allowed()

        assert allowed is False
        assert "exhausted" in reason.lower()

    @pytest.mark.asyncio
    async def test_incident_persistence(self, budget_manager, temp_db_path):
        """Test incidents are persisted to database."""
        await budget_manager.record_downtime(
            downtime_minutes=15,
            error_type="database",
            description="Database outage",
            metadata={"region": "us-east-1"},
        )

        incidents = await budget_manager.get_incident_history()

        assert len(incidents) == 1
        assert incidents[0]["downtime_minutes"] == 15
        assert incidents[0]["error_type"] == "database"

    @pytest.mark.asyncio
    async def test_budget_summary(self, budget_manager):
        """Test budget summary generation."""
        await budget_manager.record_downtime(
            downtime_minutes=30,
            error_type="api",
            description="API downtime",
        )

        summary = await budget_manager.get_budget_summary()

        assert "service" in summary
        assert "state" in summary
        assert "thresholds" in summary
        assert summary["service"] == "test_service"

    @pytest.mark.asyncio
    async def test_state_reconstruction_from_db(self, budget_manager, temp_db_path):
        """Test state is correctly reconstructed from database."""
        # Record some downtime
        await budget_manager.record_downtime(
            downtime_minutes=45,
            error_type="test",
            description="Test outage",
        )

        # Create new manager (should load from DB)
        new_manager = ErrorBudgetManager(
            service_name="test_service",
            config=budget_manager.config,
        )

        await new_manager.initialize()

        # State should be preserved
        original_state = await budget_manager.get_current_state()
        loaded_state = await new_manager.get_current_state()

        assert (
            loaded_state.consumption.downtime_minutes == original_state.consumption.downtime_minutes
        )
        assert loaded_state.consumption.error_count == original_state.consumption.error_count


class TestErrorBudgetSingleton:
    """Test singleton pattern for budget managers."""

    def test_get_singleton_returns_same_instance(self):
        """Test that get_error_budget_manager returns singleton."""
        manager1 = get_error_budget_manager("service1")
        manager2 = get_error_budget_manager("service1")

        assert manager1 is manager2

    def test_different_services_different_managers(self):
        """Test that different services get different managers."""
        manager1 = get_error_budget_manager("service1")
        manager2 = get_error_budget_manager("service2")

        assert manager1 is not manager2
        assert manager1.service_name == "service1"
        assert manager2.service_name == "service2"


class TestBudgetStatusTransitions:
    """Test budget status transitions."""

    @pytest.mark.asyncio
    async def test_healthy_to_warning_transition(self, budget_manager):
        """Test transition from healthy to warning."""
        allowance = budget_manager._current_state.allowance

        # Consume just enough to trigger warning (>50% consumed)
        downtime = int(allowance.allowed_downtime_minutes * 0.6)
        await budget_manager.record_downtime(
            downtime_minutes=downtime,
            error_type="test",
            description="Trigger warning",
        )

        state = await budget_manager.get_current_state()
        assert state.status == BudgetStatus.WARNING

    @pytest.mark.asyncio
    async def test_warning_to_critical_transition(self, budget_manager):
        """Test transition from warning to critical."""
        allowance = budget_manager._current_state.allowance

        # Consume enough to trigger critical (>75% consumed)
        downtime = int(allowance.allowed_downtime_minutes * 0.8)
        await budget_manager.record_downtime(
            downtime_minutes=downtime,
            error_type="test",
            description="Trigger critical",
        )

        state = await budget_manager.get_current_state()
        assert state.status == BudgetStatus.CRITICAL

    @pytest.mark.asyncio
    async def test_critical_to_exhausted_transition(self, budget_manager):
        """Test transition from critical to exhausted."""
        allowance = budget_manager._current_state.allowance

        # Consume almost all budget
        downtime = int(allowance.allowed_downtime_minutes * 0.95)
        await budget_manager.record_downtime(
            downtime_minutes=downtime,
            error_type="test",
            description="Nearly exhausted",
        )

        state = await budget_manager.get_current_state()
        assert state.status == BudgetStatus.EXHAUSTED


@pytest.mark.integration
class TestErrorBudgetIntegration:
    """Integration tests for error budget system."""

    @pytest.mark.asyncio
    async def test_multiple_downtime_incidents(self, budget_manager):
        """Test handling multiple downtime incidents."""
        incidents = [
            (10, "database", "DB outage 1"),
            (5, "api", "API slowdown"),
            (15, "network", "Network issue"),
        ]

        for downtime, error_type, description in incidents:
            await budget_manager.record_downtime(
                downtime_minutes=downtime,
                error_type=error_type,
                description=description,
            )

        state = await budget_manager.get_current_state()

        assert state.consumption.error_count == 3
        assert state.consumption.downtime_minutes == 30
        assert len(state.consumption.incidents) == 3

    @pytest.mark.asyncio
    async def test_burn_rate_calculation(self, budget_manager):
        """Test burn rate is calculated correctly."""
        # Record downtime that would indicate high burn rate
        await budget_manager.record_downtime(
            downtime_minutes=60,
            error_type="test",
            description="High burn rate",
        )

        state = await budget_manager.get_current_state()

        # Burn rate should be calculated
        assert state.burn_rate is not None
        assert state.burn_rate > 0

    @pytest.mark.asyncio
    async def test_budget_rollover(self, budget_manager):
        """Test budget rollover to new period."""
        # This would require testing time-based rollover
        # For now, we test that time windows are correctly set up
        window = budget_manager.get_time_window(BudgetPeriod.MONTHLY)

        assert window.start < window.end
        assert window.duration_minutes > 0
