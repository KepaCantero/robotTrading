"""
Tests for Development Gates - Auto-Halt Functionality
"""

import os
from datetime import datetime
from decimal import Decimal
from tempfile import TemporaryDirectory

import pytest

from app.sre.error_budgets.development_gates import (
    DevelopmentGate,
    DevelopmentGateConfig,
    GateStatus,
    GateType,
)
from app.sre.error_budgets.error_budget_manager import (
    BudgetPeriod,
    ErrorBudgetConfig,
    ErrorBudgetManager,
)
from app.sre.error_budgets.slo_tracker import SLIMetric, SLIMetricType, SLOTracker


@pytest.fixture
async def gate_setup():
    """Setup for development gate tests."""
    with TemporaryDirectory() as tmpdir:
        budget_db = os.path.join(tmpdir, "budget.db")
        slo_db = os.path.join(tmpdir, "slo.db")

        # Create budget manager
        budget_config = ErrorBudgetConfig(
            target_slo=Decimal("0.995"),
            period=BudgetPeriod.MONTHLY,
            db_path=budget_db,
        )
        budget_manager = ErrorBudgetManager("test_service", budget_config)
        await budget_manager.initialize()

        # Create SLO tracker
        slo_tracker = SLOTracker("test_service", db_path=slo_db)
        await slo_tracker.initialize()

        # Create development gate
        gate_config = DevelopmentGateConfig(
            budget_exhausted_threshold_pct=Decimal("10"),
            budget_warning_threshold_pct=Decimal("25"),
            max_allowed_violations=0,
            slo_compliance_threshold=Decimal("0.95"),
            max_burn_rate=Decimal("2.0"),
            allow_override=True,
            override_approvers=["admin", "sre-team"],
        )

        gate = DevelopmentGate(
            service_name="test_service",
            error_budget_manager=budget_manager,
            slo_tracker=slo_tracker,
            config=gate_config,
        )

        yield {
            "gate": gate,
            "budget_manager": budget_manager,
            "slo_tracker": slo_tracker,
        }


@pytest.mark.asyncio
class TestDevelopmentGates:
    """Test development gate functionality."""

    async def test_deployment_allowed_when_healthy(self, gate_setup):
        """Test deployment is allowed when system is healthy."""
        gate = gate_setup["gate"]

        allowed, decisions, blocker = await gate.check_deployment_allowed()

        assert allowed is True
        assert blocker is None
        assert all(d.status != GateStatus.FAIL for d in decisions)

    async def test_deployment_blocked_when_budget_exhausted(self, gate_setup):
        """Test deployment is blocked when budget exhausted."""
        gate = gate_setup["gate"]
        budget_manager = gate_setup["budget_manager"]

        # Exhaust the budget
        state = await budget_manager.get_current_state()
        allowance = state.allowance
        await budget_manager.record_downtime(
            downtime_minutes=allowance.allowed_downtime_minutes,
            error_type="test",
            description="Exhaust budget",
        )

        # Check deployment
        allowed, decisions, blocker = await gate.check_deployment_allowed()

        assert allowed is False
        assert blocker is not None
        assert blocker.blocking_gate == GateType.ERROR_BUDGET

        # Should have a FAIL decision
        fail_decisions = [d for d in decisions if d.status == GateStatus.FAIL]
        assert len(fail_decisions) > 0

    async def test_deployment_blocked_with_slo_violations(self, gate_setup):
        """Test deployment is blocked with active SLO violations."""
        gate = gate_setup["gate"]
        slo_tracker = gate_setup["slo_tracker"]

        # Record failing SLO metrics
        for i in range(10):
            metric = SLIMetric(
                name="availability",
                value=Decimal("0"),  # All failures
                timestamp=datetime.utcnow(),
                metric_type=SLIMetricType.AVAILABILITY,
            )
            await slo_tracker.record_metric(metric)

        # Check deployment (should be blocked due to violations)
        allowed, decisions, blocker = await gate.check_deployment_allowed()

        # Should be blocked or warned
        has_fail_or_warn = any(d.status in (GateStatus.FAIL, GateStatus.WARN) for d in decisions)
        assert has_fail_or_warn

    async def test_deployment_warning_with_low_budget(self, gate_setup):
        """Test deployment warning when budget is low."""
        gate = gate_setup["gate"]
        budget_manager = gate_setup["budget_manager"]

        # Consume most of the budget (but not exhausted)
        state = await budget_manager.get_current_state()
        allowance = state.allowance
        await budget_manager.record_downtime(
            downtime_minutes=int(allowance.allowed_downtime_minutes * 0.8),
            error_type="test",
            description="Consume most budget",
        )

        # Check deployment
        allowed, decisions, blocker = await gate.check_deployment_allowed()

        # Should still be allowed but with warnings
        assert allowed is True
        assert any(d.status == GateStatus.WARN for d in decisions)

    async def test_override_allows_deployment(self, gate_setup):
        """Test that override allows deployment even when blocked."""
        gate = gate_setup["gate"]
        budget_manager = gate_setup["budget_manager"]

        # Exhaust the budget
        state = await budget_manager.get_current_state()
        allowance = state.allowance
        await budget_manager.record_downtime(
            downtime_minutes=allowance.allowed_downtime_minutes,
            error_type="test",
            description="Exhaust budget",
        )

        # Check deployment with override
        allowed, decisions, blocker = await gate.check_deployment_allowed(
            requesting_user="admin",
            reason="Emergency fix for critical bug",
        )

        # Override should allow it
        assert allowed is True
        assert blocker is None

    async def test_override_rejected_for_unauthorized_user(self, gate_setup):
        """Test that override is rejected for unauthorized users."""
        gate = gate_setup["gate"]
        budget_manager = gate_setup["budget_manager"]

        # Exhaust the budget
        state = await budget_manager.get_current_state()
        allowance = state.allowance
        await budget_manager.record_downtime(
            downtime_minutes=allowance.allowed_downtime_minutes,
            error_type="test",
            description="Exhaust budget",
        )

        # Try override with unauthorized user
        allowed, decisions, blocker = await gate.check_deployment_allowed(
            requesting_user="unauthorized_user",
            reason="Trying to bypass",
        )

        # Should still be blocked
        assert allowed is False
        assert blocker is not None

    async def test_multiple_gates_checked(self, gate_setup):
        """Test that all gates are checked."""
        gate = gate_setup["gate"]

        allowed, decisions, blocker = await gate.check_deployment_allowed()

        # Should have decisions for all gate types
        gate_types = {d.gate_type for d in decisions}

        assert GateType.ERROR_BUDGET in gate_types
        assert GateType.SLO_COMPLIANCE in gate_types
        assert GateType.ACTIVE_VIOLATIONS in gate_types
        assert GateType.BURN_RATE in gate_types

    async def test_gate_decision_details(self, gate_setup):
        """Test that gate decisions include proper details."""
        gate = gate_setup["gate"]

        allowed, decisions, blocker = await gate.check_deployment_allowed()

        for decision in decisions:
            assert decision.gate_type in GateType
            assert decision.status in GateStatus
            assert decision.message is not None
            assert decision.details is not None
            assert decision.timestamp is not None

    async def test_deployment_blocker_details(self, gate_setup):
        """Test deployment blocker details."""
        gate = gate_setup["gate"]
        budget_manager = gate_setup["budget_manager"]

        # Exhaust the budget
        state = await budget_manager.get_current_state()
        allowance = state.allowance
        await budget_manager.record_downtime(
            downtime_minutes=allowance.allowed_downtime_minutes,
            error_type="test",
            description="Exhaust budget",
        )

        # Get blocker
        allowed, decisions, blocker = await gate.check_deployment_allowed()

        assert blocker is not None
        assert blocker.block_reason is not None
        assert blocker.blocking_gate is not None
        assert blocker.blocked_at is not None

    async def test_clear_blocker(self, gate_setup):
        """Test clearing deployment blocker."""
        gate = gate_setup["gate"]
        budget_manager = gate_setup["budget_manager"]

        # Exhaust the budget
        state = await budget_manager.get_current_state()
        allowance = state.allowance
        await budget_manager.record_downtime(
            downtime_minutes=allowance.allowed_downtime_minutes,
            error_type="test",
            description="Exhaust budget",
        )

        # Should be blocked
        _, _, blocker1 = await gate.check_deployment_allowed()
        assert blocker1 is not None

        # Clear blocker
        cleared = await gate.clear_blocker()
        assert cleared is True

        # Should no longer have blocker
        blocker2 = await gate.get_current_blocker()
        assert blocker2 is None

    async def test_decision_history_tracking(self, gate_setup):
        """Test that gate decisions are tracked in history."""
        gate = gate_setup["gate"]

        # Make several decisions
        for i in range(3):
            await gate.check_deployment_allowed()

        history = await gate.get_decision_history()

        assert len(history) >= 3
        assert all(isinstance(d, GateStatus) for d in history)

    async def test_gate_summary(self, gate_setup):
        """Test gate summary generation."""
        gate = gate_setup["gate"]

        summary = await gate.get_gate_summary()

        assert "service" in summary
        assert "current_blocker" in summary
        assert "override_enabled" in summary
        assert "override_approvers" in summary
        assert "recent_decisions" in summary

    async def test_burn_rate_warning(self, gate_setup):
        """Test burn rate gate produces warnings."""
        gate = gate_setup["gate"]
        budget_manager = gate_setup["budget_manager"]

        # Record significant downtime to trigger high burn rate
        await budget_manager.record_downtime(
            downtime_minutes=120,
            error_type="test",
            description="High burn rate",
        )

        allowed, decisions, blocker = await gate.check_deployment_allowed()

        # Should have burn rate decision
        burn_rate_decisions = [d for d in decisions if d.gate_type == GateType.BURN_RATE]
        assert len(burn_rate_decisions) > 0


@pytest.mark.asyncio
class TestGateCombinations:
    """Test combinations of multiple gates."""

    async def test_budget_and_slo_both_failing(self, gate_setup):
        """Test when both budget and SLO gates are failing."""
        gate = gate_setup["gate"]
        budget_manager = gate_setup["budget_manager"]
        slo_tracker = gate_setup["slo_tracker"]

        # Exhaust budget
        state = await budget_manager.get_current_state()
        allowance = state.allowance
        await budget_manager.record_downtime(
            downtime_minutes=allowance.allowed_downtime_minutes,
            error_type="test",
            description="Exhaust budget",
        )

        # Create SLO violations
        for i in range(10):
            metric = SLIMetric(
                name="availability",
                value=Decimal("0"),
                timestamp=datetime.utcnow(),
                metric_type=SLIMetricType.AVAILABILITY,
            )
            await slo_tracker.record_metric(metric)

        # Check deployment
        allowed, decisions, blocker = await gate.check_deployment_allowed()

        # Should be blocked
        assert allowed is False

        # Should have multiple FAIL decisions
        fail_decisions = [d for d in decisions if d.status == GateStatus.FAIL]
        assert len(fail_decisions) >= 2

    async def test_all_gates_passing(self, gate_setup):
        """Test when all gates are passing."""
        gate = gate_setup["gate"]

        allowed, decisions, blocker = await gate.check_deployment_allowed()

        assert allowed is True
        assert blocker is None

        # All decisions should be PASS or WARN (no FAIL)
        assert all(d.status != GateStatus.FAIL for d in decisions)


@pytest.mark.asyncio
class TestGateConfiguration:
    """Test gate configuration options."""

    async def test_custom_thresholds(self):
        """Test custom gate thresholds."""
        with TemporaryDirectory() as tmpdir:
            budget_db = os.path.join(tmpdir, "budget.db")

            budget_config = ErrorBudgetConfig(
                target_slo=Decimal("0.999"),
                period=BudgetPeriod.MONTHLY,
                db_path=budget_db,
            )
            budget_manager = ErrorBudgetManager("test_service", budget_config)
            await budget_manager.initialize()

            gate_config = DevelopmentGateConfig(
                budget_exhausted_threshold_pct=Decimal("5"),  # Stricter
                budget_warning_threshold_pct=Decimal("20"),
                allow_override=False,  # No overrides
            )

            gate = DevelopmentGate(
                service_name="test_service",
                error_budget_manager=budget_manager,
                config=gate_config,
            )

            # Verify config is applied
            summary = await gate.get_gate_summary()
            assert summary["override_enabled"] is False

    async def test_no_override_configuration(self):
        """Test gate configuration with no overrides allowed."""
        with TemporaryDirectory() as tmpdir:
            budget_db = os.path.join(tmpdir, "budget.db")

            budget_config = ErrorBudgetConfig(
                target_slo=Decimal("0.995"),
                period=BudgetPeriod.MONTHLY,
                db_path=budget_db,
            )
            budget_manager = ErrorBudgetManager("test_service", budget_config)
            await budget_manager.initialize()

            gate_config = DevelopmentGateConfig(
                allow_override=False,
            )

            gate = DevelopmentGate(
                service_name="test_service",
                error_budget_manager=budget_manager,
                config=gate_config,
            )

            # Exhaust budget
            state = await budget_manager.get_current_state()
            allowance = state.allowance
            await budget_manager.record_downtime(
                downtime_minutes=allowance.allowed_downtime_minutes,
                error_type="test",
                description="Exhaust budget",
            )

            # Try override (should not work)
            allowed, decisions, blocker = await gate.check_deployment_allowed(
                requesting_user="admin",
                reason="Emergency",
            )

            assert allowed is False  # Override should not work
