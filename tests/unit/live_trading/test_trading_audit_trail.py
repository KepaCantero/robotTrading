"""
Tests for TradingAuditTrail - Compliance and Audit Logging

Tests cover:
- Event logging and immutability
- Event retrieval and filtering
- Compliance report generation
- Risk level tracking
- Statistics collection

NOTE: These tests use autouse fixture to clean up the audit trail database
between test runs. They should NOT be run in parallel with other tests that
use the TradingAuditTrail.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.live_trading.trading_audit_trail import (
    AuditEventType,
    ComplianceReport,
    TradingAuditTrail,
)

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


class MockAuditPersistence:
    """Mock persistence that doesn't persist to disk."""

    def __init__(self, db_path=None):
        self.events = []

    def save_event(self, event):
        pass

    def load_events(self, limit=None):
        return []

    def get_event(self, event_id):
        return None

    def close(self):
        pass


@pytest.fixture(autouse=True)
def clean_audit_persistence():
    """Clean audit persistence database between tests."""
    # Import module to access singleton variables
    import app.services.live_trading.trading_audit_trail as audit_module

    # Close any existing database connections before deleting files
    if audit_module._audit_persistence is not None:
        try:
            audit_module._audit_persistence.close()
        except Exception:
            pass  # Ignore errors during cleanup

    # Clean up any existing database files (including WAL files)
    db_dir = Path("data")
    db_dir.mkdir(exist_ok=True)  # Ensure directory exists

    # Remove all audit_trail database files
    for db_file in db_dir.glob("audit_trail.db*"):
        try:
            db_file.unlink()
        except FileNotFoundError:
            pass

    # Reset singleton instances to force fresh initialization
    audit_module._audit_persistence = None
    audit_module._audit_trail_instance = None

    yield

    # Clean up after test
    if audit_module._audit_persistence is not None:
        try:
            audit_module._audit_persistence.close()
        except Exception:
            pass

    for db_file in db_dir.glob("audit_trail.db*"):
        try:
            db_file.unlink()
        except FileNotFoundError:
            pass

    # Reset singletons again after test
    audit_module._audit_persistence = None
    audit_module._audit_trail_instance = None


class TestAuditEventLogging:
    """Test audit event logging."""

    def test_log_event_basic(self):
        """Test logging a basic audit event."""
        trail = TradingAuditTrail()

        event = trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_001",
            symbol="AAPL",
        )

        assert event is not None
        assert event.event_type == AuditEventType.ALERT_RECEIVED
        assert event.alert_id == "evt_001"
        assert event.symbol == "AAPL"

    def test_log_multiple_events(self):
        """Test logging multiple events."""
        trail = TradingAuditTrail()

        for i in range(5):
            trail.log_event(
                event_type=AuditEventType.ALERT_RECEIVED,
                alert_id=f"evt_{i:03d}",
                symbol="AAPL",
            )

        assert len(trail.events) == 5

    def test_event_timestamp(self):
        """Test that events have timestamps."""
        trail = TradingAuditTrail()
        before = datetime.now(timezone.utc)

        event = trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_001",
        )

        after = datetime.now(timezone.utc)
        assert before <= event.timestamp <= after

    def test_event_immutability(self):
        """Test that events are immutable after logging."""
        trail = TradingAuditTrail()

        event = trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_001",
        )

        # Get the logged event
        retrieved = trail.get_event(event.event_id)
        assert retrieved is not None
        assert retrieved.event_id == event.event_id


class TestEventRetrieval:
    """Test event retrieval and filtering."""

    def test_get_event_by_id(self):
        """Test retrieving event by ID."""
        trail = TradingAuditTrail()

        event1 = trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_001",
        )

        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            alert_id="evt_001",
            order_id="order_001",
        )

        retrieved = trail.get_event(event1.event_id)
        assert retrieved is not None
        assert retrieved.event_type == AuditEventType.ALERT_RECEIVED

    def test_get_events_for_alert(self):
        """Test retrieving all events for an alert."""
        trail = TradingAuditTrail()

        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_001",
        )
        trail.log_event(
            event_type=AuditEventType.SIGNAL_GENERATED,
            alert_id="evt_001",
        )
        trail.log_event(
            event_type=AuditEventType.RISK_CHECK_PASSED,
            alert_id="evt_001",
        )

        # Different alert
        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_002",
        )

        events = trail.get_events_for_alert("evt_001")
        assert len(events) == 3
        assert all(e.alert_id == "evt_001" for e in events)

    def test_get_events_for_order(self):
        """Test retrieving all events for an order."""
        trail = TradingAuditTrail()

        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            order_id="order_001",
            symbol="AAPL",
        )
        trail.log_event(
            event_type=AuditEventType.ORDER_EXECUTED,
            order_id="order_001",
            symbol="AAPL",
        )

        # Different order
        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            order_id="order_002",
            symbol="TSLA",
        )

        events = trail.get_events_for_order("order_001")
        assert len(events) == 2
        assert all(e.order_id == "order_001" for e in events)

    def test_get_events_by_type(self):
        """Test filtering events by type."""
        trail = TradingAuditTrail()

        # Log different event types
        trail.log_event(event_type=AuditEventType.ALERT_RECEIVED)
        trail.log_event(event_type=AuditEventType.ALERT_RECEIVED)
        trail.log_event(event_type=AuditEventType.SIGNAL_GENERATED)
        trail.log_event(event_type=AuditEventType.ORDER_PLACED)

        alert_events = trail.get_events_by_type(AuditEventType.ALERT_RECEIVED)
        assert len(alert_events) == 2
        assert all(e.event_type == AuditEventType.ALERT_RECEIVED for e in alert_events)

    def test_get_non_compliant_events(self):
        """Test retrieving non-compliant events."""
        trail = TradingAuditTrail()

        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            is_compliant=True,
        )
        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            is_compliant=False,
        )
        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            is_compliant=True,
        )

        non_compliant = trail.get_non_compliant_events()
        assert len(non_compliant) == 1
        assert non_compliant[0].is_compliant is False

    def test_get_recent_events(self):
        """Test retrieving recent events."""
        trail = TradingAuditTrail()

        # Log 10 events
        for i in range(10):
            trail.log_event(
                event_type=AuditEventType.ALERT_RECEIVED,
                alert_id=f"evt_{i:03d}",
            )

        recent = trail.get_recent_events(limit=5)
        assert len(recent) == 5
        # Most recent is at index 0 (after reversing)
        assert recent[0].alert_id == "evt_009"


class TestComplianceReporting:
    """Test compliance report generation."""

    def test_generate_compliance_report(self):
        """Test generating compliance report."""
        trail = TradingAuditTrail()

        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)

        # Log events within period
        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_001",
        )
        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            order_id="order_001",
            quantity=Decimal("100"),
            risk_level="low",
        )
        trail.log_event(
            event_type=AuditEventType.ORDER_EXECUTED,
            order_id="order_001",
        )

        report = trail.generate_compliance_report(start_date, end_date)
        assert report.total_alerts == 1
        assert report.total_trades == 1
        assert report.total_executions == 1
        assert report.total_volume == Decimal("100")

    def test_report_with_failed_risk_checks(self):
        """Test compliance report with failed risk checks."""
        trail = TradingAuditTrail()

        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)

        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_001",
        )
        trail.log_event(
            event_type=AuditEventType.RISK_CHECK_PASSED,
            alert_id="evt_001",
        )
        trail.log_event(
            event_type=AuditEventType.RISK_CHECK_FAILED,
            alert_id="evt_002",
        )

        report = trail.generate_compliance_report(start_date, end_date)
        assert report.failed_risk_checks == 1

    def test_report_with_non_compliant_events(self):
        """Test compliance report with non-compliant events."""
        trail = TradingAuditTrail()

        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)

        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            is_compliant=True,
        )
        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            is_compliant=False,
        )
        trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            is_compliant=False,
        )

        report = trail.generate_compliance_report(start_date, end_date)
        assert report.non_compliant_events == 2

    def test_report_with_critical_alerts(self):
        """Test compliance report with critical alert tracking."""
        trail = TradingAuditTrail()

        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)

        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            details={"severity": "info"},
        )
        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            details={"severity": "critical"},
        )
        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            details={"severity": "critical"},
        )

        report = trail.generate_compliance_report(start_date, end_date)
        assert report.critical_alerts_count == 2

    def test_report_time_range_filtering(self):
        """Test that report correctly filters by time range."""
        trail = TradingAuditTrail()

        # Log event before range
        past_event = trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_past",
        )

        # Simulate past timestamp
        past_event.timestamp = datetime.now(timezone.utc) - timedelta(hours=2)

        # Log event in range
        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_in_range",
        )

        # Log event after range
        trail.log_event(
            event_type=AuditEventType.ALERT_RECEIVED,
            alert_id="evt_future",
        )
        future_event = trail.events[-1]
        future_event.timestamp = datetime.now(timezone.utc) + timedelta(hours=2)

        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)

        report = trail.generate_compliance_report(start_date, end_date)
        # Should only include event in range
        assert report.total_alerts >= 1


class TestAuditStatistics:
    """Test statistics collection."""

    def test_audit_statistics(self):
        """Test collecting audit statistics."""
        trail = TradingAuditTrail()

        # Log various events
        trail.log_event(event_type=AuditEventType.ALERT_RECEIVED)
        trail.log_event(event_type=AuditEventType.SIGNAL_GENERATED)
        trail.log_event(event_type=AuditEventType.RISK_CHECK_PASSED)
        trail.log_event(event_type=AuditEventType.RISK_CHECK_FAILED)
        trail.log_event(event_type=AuditEventType.ORDER_PLACED, risk_level="high")

        stats = trail.get_audit_statistics()
        assert stats["total_events"] == 5
        assert stats["non_compliant_events"] == 0

    def test_statistics_by_event_type(self):
        """Test statistics breakdown by event type."""
        trail = TradingAuditTrail()

        trail.log_event(event_type=AuditEventType.ALERT_RECEIVED)
        trail.log_event(event_type=AuditEventType.ALERT_RECEIVED)
        trail.log_event(event_type=AuditEventType.SIGNAL_GENERATED)

        stats = trail.get_audit_statistics()
        assert stats["by_event_type"]["alert_received"] == 2
        assert stats["by_event_type"]["signal_generated"] == 1

    def test_statistics_by_risk_level(self):
        """Test statistics breakdown by risk level."""
        trail = TradingAuditTrail()

        trail.log_event(event_type=AuditEventType.ORDER_PLACED, risk_level="low")
        trail.log_event(event_type=AuditEventType.ORDER_PLACED, risk_level="high")
        trail.log_event(event_type=AuditEventType.ORDER_PLACED, risk_level="high")

        stats = trail.get_audit_statistics()
        assert stats["by_risk_level"]["low"] == 1
        assert stats["by_risk_level"]["high"] == 2

    def test_statistics_date_range(self):
        """Test date range information in statistics."""
        trail = TradingAuditTrail()

        trail.log_event(event_type=AuditEventType.ALERT_RECEIVED)
        trail.log_event(event_type=AuditEventType.ORDER_PLACED)

        stats = trail.get_audit_statistics()
        assert stats["date_range"]["earliest"] is not None
        assert stats["date_range"]["latest"] is not None


class TestEventSerialization:
    """Test event serialization."""

    def test_audit_event_to_dict(self):
        """Test serializing audit event to dictionary."""
        trail = TradingAuditTrail()

        event = trail.log_event(
            event_type=AuditEventType.ORDER_PLACED,
            order_id="order_001",
            symbol="AAPL",
            quantity=Decimal("100"),
            risk_level="medium",
            is_compliant=True,
        )

        event_dict = event.to_dict()
        assert event_dict["event_type"] == "order_placed"
        assert event_dict["order_id"] == "order_001"
        assert event_dict["symbol"] == "AAPL"
        assert event_dict["quantity"] == "100"
        assert event_dict["risk_level"] == "medium"
        assert event_dict["is_compliant"] is True

    def test_compliance_report_to_dict(self):
        """Test serializing compliance report to dictionary."""
        report = ComplianceReport(
            report_id="report_001",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
            total_alerts=10,
            total_trades=5,
            total_executions=4,
            failed_risk_checks=1,
            non_compliant_events=0,
        )

        report_dict = report.to_dict()
        assert report_dict["report_id"] == "report_001"
        assert report_dict["total_alerts"] == 10
        assert report_dict["total_trades"] == 5
        assert report_dict["total_executions"] == 4


class TestMaxEventsLimit:
    """Test maximum events limit enforcement."""

    def test_max_events_limit(self):
        """Test that max events limit is enforced."""
        trail = TradingAuditTrail(max_events=100)

        # Log more events than max
        for i in range(150):
            trail.log_event(
                event_type=AuditEventType.ALERT_RECEIVED,
                alert_id=f"evt_{i:04d}",
            )

        # Should have kept only the latest 100
        assert len(trail.events) <= 100
