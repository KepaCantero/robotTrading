"""Unit tests for T8.1 RealTimeMonitor component"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from app.services.portfolio_constructor import AllocationWeight
from app.services.risk_scaling_application.limit_adjuster import (
    AdjustedLimit,
    LimitBreach,
)
from app.services.risk_scaling_application.realtime_monitor import (
    RealTimeMonitor,
    PositionSnapshot,
    MonitoringAlert,
)


def create_allocation(name, weight, capital=Decimal("30000")):
    """Helper to create AllocationWeight with required fields."""
    return AllocationWeight(
        module_name=name,
        weight_pct=weight,
        capital_allocation_eur=capital,
        rationale=f"Test allocation for {name}",
    )


class TestRealTimeMonitor:
    """Test RealTimeMonitor component."""

    def setup_method(self):
        """Setup test fixtures."""
        self.monitor = RealTimeMonitor()

    def test_initialization(self):
        """Test monitor initialization."""
        assert len(self.monitor.position_history) == 0
        assert len(self.monitor.current_positions) == 0
        assert len(self.monitor.breach_state) == 0

    # Position Monitoring Tests
    def test_update_positions_creates_snapshots(self):
        """Test position update creates snapshots."""
        positions = {"momentum": Decimal("35000"), "mean_reversion": Decimal("25000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            ),
            AdjustedLimit(
                module_name="mean_reversion",
                original_limit=Decimal("30000"),
                adjusted_limit=Decimal("30000"),
                scaling_applied=Decimal("1.0"),
                reason="Test",
            ),
        ]

        snapshots, _ = self.monitor.update_positions(positions, limits)

        assert len(snapshots) == 2
        assert snapshots[0].module_name == "momentum"
        assert snapshots[0].position_value == Decimal("35000")
        assert snapshots[0].limit == Decimal("40000")

    def test_update_positions_ok_status(self):
        """Test position status when within acceptable range."""
        positions = {"momentum": Decimal("30000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        snapshots, _ = self.monitor.update_positions(positions, limits)
        assert snapshots[0].status == "ok"
        assert snapshots[0].percent_of_limit == Decimal("75")

    def test_update_positions_warning_status(self):
        """Test position status when approaching limit."""
        positions = {"momentum": Decimal("38000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        snapshots, _ = self.monitor.update_positions(positions, limits)
        assert snapshots[0].status == "warning"
        assert snapshots[0].percent_of_limit == Decimal("95")

    def test_update_positions_critical_status(self):
        """Test position status when exceeding limit."""
        positions = {"momentum": Decimal("45000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        snapshots, _ = self.monitor.update_positions(positions, limits)
        assert snapshots[0].status == "critical"
        assert snapshots[0].percent_of_limit == Decimal("112.5")

    def test_update_positions_tracks_history(self):
        """Test that position history is tracked."""
        positions = {"momentum": Decimal("35000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        self.monitor.update_positions(positions, limits)
        assert "momentum" in self.monitor.position_history
        assert len(self.monitor.position_history["momentum"]) == 1

    # State Transition Tests
    def test_state_transition_ok_to_warning(self):
        """Test alert generated on transition from OK to warning."""
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        # First update: OK status
        self.monitor.update_positions({"momentum": Decimal("30000")}, limits)

        # Second update: Warning status
        _, alerts = self.monitor.update_positions({"momentum": Decimal("38000")}, limits)

        assert len(alerts) > 0
        assert alerts[0].severity == "warning"
        assert alerts[0].alert_type == "breach_detected"

    def test_state_transition_warning_to_critical(self):
        """Test alert generated on transition from warning to critical."""
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        # First update: Warning status
        self.monitor.update_positions({"momentum": Decimal("38000")}, limits)

        # Second update: Critical status
        _, alerts = self.monitor.update_positions({"momentum": Decimal("45000")}, limits)

        assert len(alerts) > 0
        assert alerts[0].severity == "critical"

    def test_state_transition_critical_to_ok(self):
        """Test alert generated on recovery to OK status."""
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        # First update: Critical status
        self.monitor.update_positions({"momentum": Decimal("45000")}, limits)

        # Second update: Recovery to OK
        _, alerts = self.monitor.update_positions({"momentum": Decimal("30000")}, limits)

        assert len(alerts) > 0
        assert alerts[0].alert_type == "recovery"

    # Breach Detection Tests
    def test_detect_new_critical_breach(self):
        """Test detection of new critical breach."""
        breaches = [
            LimitBreach(
                module_name="momentum",
                current_position=Decimal("55000"),
                adjusted_limit=Decimal("40000"),
                excess=Decimal("15000"),
                severity="critical",
                recommendation="Reduce position",
            )
        ]

        alerts = self.monitor.detect_new_breaches(breaches)

        assert len(alerts) == 1
        assert alerts[0].severity == "critical"
        assert alerts[0].alert_type == "breach_detected"

    def test_detect_new_warning_breach(self):
        """Test detection of new warning breach."""
        breaches = [
            LimitBreach(
                module_name="momentum",
                current_position=Decimal("42000"),
                adjusted_limit=Decimal("40000"),
                excess=Decimal("2000"),
                severity="warning",
                recommendation="Monitor position",
            )
        ]

        alerts = self.monitor.detect_new_breaches(breaches)

        assert len(alerts) == 1
        assert alerts[0].severity == "warning"

    def test_detect_recovery(self):
        """Test detection of position recovery."""
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        # Set breach state to warning
        self.monitor.breach_state["momentum"] = "warning"

        # Detect recovery
        alerts = self.monitor.detect_recovery({"momentum": Decimal("35000")}, limits)

        assert len(alerts) == 1
        assert alerts[0].alert_type == "recovery"
        assert alerts[0].severity == "info"

    # Scaling Recommendation Tests
    def test_recommend_scaling_multiple_critical(self):
        """Test scaling recommendation with multiple critical breaches."""
        breaches = [
            LimitBreach(
                module_name="momentum",
                current_position=Decimal("55000"),
                adjusted_limit=Decimal("40000"),
                excess=Decimal("15000"),
                severity="critical",
                recommendation="Reduce",
            ),
            LimitBreach(
                module_name="ml_basic",
                current_position=Decimal("35000"),
                adjusted_limit=Decimal("30000"),
                excess=Decimal("5000"),
                severity="critical",
                recommendation="Reduce",
            ),
        ]

        alert = self.monitor.recommend_scaling_adjustment(
            breaches, Decimal("1.0")
        )

        assert alert is not None
        assert alert.severity == "critical"
        assert alert.alert_type == "scaling_recommended"
        assert "0.80" in alert.recommended_action

    def test_recommend_scaling_one_critical_multiple_warnings(self):
        """Test scaling recommendation with 1 critical and multiple warnings."""
        breaches = [
            LimitBreach(
                module_name="momentum",
                current_position=Decimal("55000"),
                adjusted_limit=Decimal("40000"),
                excess=Decimal("15000"),
                severity="critical",
                recommendation="Reduce",
            ),
            LimitBreach(
                module_name="ml_basic",
                current_position=Decimal("32000"),
                adjusted_limit=Decimal("30000"),
                excess=Decimal("2000"),
                severity="warning",
                recommendation="Monitor",
            ),
            LimitBreach(
                module_name="ensemble",
                current_position=Decimal("28500"),
                adjusted_limit=Decimal("28000"),
                excess=Decimal("500"),
                severity="warning",
                recommendation="Monitor",
            ),
        ]

        alert = self.monitor.recommend_scaling_adjustment(
            breaches, Decimal("1.0")
        )

        assert alert is not None
        assert alert.severity == "warning"
        assert "0.90" in alert.recommended_action

    def test_no_scaling_recommendation_with_no_breaches(self):
        """Test no recommendation when no breaches detected."""
        alert = self.monitor.recommend_scaling_adjustment([], Decimal("1.0"))
        assert alert is None

    # Monitoring Report Tests
    def test_generate_monitoring_report(self):
        """Test monitoring report generation."""
        start_time = datetime.utcnow()
        positions = {"momentum": Decimal("35000"), "mean_reversion": Decimal("25000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            ),
            AdjustedLimit(
                module_name="mean_reversion",
                original_limit=Decimal("30000"),
                adjusted_limit=Decimal("30000"),
                scaling_applied=Decimal("1.0"),
                reason="Test",
            ),
        ]

        self.monitor.update_positions(positions, limits)

        alerts = []
        end_time = datetime.utcnow() + timedelta(seconds=1)

        report = self.monitor.generate_monitoring_report(start_time, end_time, alerts)

        assert report.monitoring_start == start_time
        assert report.monitoring_end == end_time
        assert report.positions_monitored == 2
        assert report.alerts_generated == 0

    def test_monitoring_report_with_alerts(self):
        """Test monitoring report includes alerts."""
        start_time = datetime.utcnow()
        alert = MonitoringAlert(
            alert_type="breach_detected",
            severity="warning",
            module_name="momentum",
            current_position=Decimal("42000"),
            adjusted_limit=Decimal("40000"),
            excess_amount=Decimal("2000"),
            excess_pct=Decimal("5"),
            timestamp=start_time,
            message="Test breach",
            recommended_action="Reduce",
        )

        end_time = datetime.utcnow() + timedelta(seconds=1)
        report = self.monitor.generate_monitoring_report(start_time, end_time, [alert])

        assert report.alerts_generated == 1
        assert report.breaches_detected == 1

    # Status Query Tests
    def test_get_monitor_status(self):
        """Test monitor status query."""
        positions = {"momentum": Decimal("35000"), "mean_reversion": Decimal("25000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            ),
            AdjustedLimit(
                module_name="mean_reversion",
                original_limit=Decimal("30000"),
                adjusted_limit=Decimal("30000"),
                scaling_applied=Decimal("1.0"),
                reason="Test",
            ),
        ]

        self.monitor.update_positions(positions, limits)
        status = self.monitor.get_monitor_status()

        assert status["positions_tracked"] == 2
        assert "breach_state_distribution" in status
        assert "critical_modules" in status

    # History Management Tests
    def test_reset_history(self):
        """Test history reset."""
        positions = {"momentum": Decimal("35000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        self.monitor.update_positions(positions, limits)
        assert len(self.monitor.position_history) > 0

        self.monitor.reset_history()
        assert len(self.monitor.position_history) == 0
        assert len(self.monitor.breach_state) == 0

    # Multiple Position Tracking Tests
    def test_multiple_positions_independent_tracking(self):
        """Test that multiple positions are tracked independently."""
        positions = {
            "momentum": Decimal("30000"),
            "mean_reversion": Decimal("20000"),
            "ensemble": Decimal("20000"),
        }
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            ),
            AdjustedLimit(
                module_name="mean_reversion",
                original_limit=Decimal("30000"),
                adjusted_limit=Decimal("30000"),
                scaling_applied=Decimal("1.0"),
                reason="Test",
            ),
            AdjustedLimit(
                module_name="ensemble",
                original_limit=Decimal("25000"),
                adjusted_limit=Decimal("25000"),
                scaling_applied=Decimal("1.0"),
                reason="Test",
            ),
        ]

        snapshots, _ = self.monitor.update_positions(positions, limits)

        assert len(snapshots) == 3
        # All positions should be below 80% of limit = "ok" status
        assert snapshots[0].status == "ok"  # 30000/40000 = 75%
        assert snapshots[1].status == "ok"  # 20000/30000 = 66.67%
        assert snapshots[2].status == "ok"  # 20000/25000 = 80% (still ok at threshold)

    def test_position_percent_calculation(self):
        """Test position percentage of limit calculation."""
        positions = {"momentum": Decimal("25000")}
        limits = [
            AdjustedLimit(
                module_name="momentum",
                original_limit=Decimal("50000"),
                adjusted_limit=Decimal("40000"),
                scaling_applied=Decimal("0.8"),
                reason="Test",
            )
        ]

        snapshots, _ = self.monitor.update_positions(positions, limits)

        # 25000 / 40000 = 62.5%
        assert snapshots[0].percent_of_limit == Decimal("62.5")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
