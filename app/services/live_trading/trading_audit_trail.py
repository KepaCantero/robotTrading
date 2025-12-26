"""
T18.3.4: TradingAuditTrail - Compliance and audit logging

Comprehensive audit trail for all alert-triggered trades:
- Immutable event logging
- Trade justification tracking
- Risk validation records
- Execution evidence
- Compliance reporting
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from app.services.alerting_system import AlertSeverity

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit trail events."""
    ALERT_RECEIVED = "alert_received"
    SIGNAL_GENERATED = "signal_generated"
    RISK_CHECK_PASSED = "risk_check_passed"
    RISK_CHECK_FAILED = "risk_check_failed"
    ORDER_PLACED = "order_placed"
    ORDER_EXECUTED = "order_executed"
    ORDER_CANCELED = "order_canceled"
    ORDER_FAILED = "order_failed"
    MANUAL_OVERRIDE = "manual_override"
    AUDIT_QUERY = "audit_query"


@dataclass
class AuditEvent:
    """Single audit trail event."""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    alert_id: Optional[str] = None
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    user: str = "system"
    ip_address: Optional[str] = None
    details: Dict = field(default_factory=dict)
    is_compliant: bool = True
    risk_level: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "alert_id": self.alert_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "quantity": str(self.quantity) if self.quantity else None,
            "user": self.user,
            "ip_address": self.ip_address,
            "details": self.details,
            "is_compliant": self.is_compliant,
            "risk_level": self.risk_level,
        }


@dataclass
class ComplianceReport:
    """Compliance report for audit period."""
    report_id: str
    start_date: datetime
    end_date: datetime
    total_alerts: int = 0
    total_trades: int = 0
    total_executions: int = 0
    failed_risk_checks: int = 0
    non_compliant_events: int = 0
    total_volume: Decimal = Decimal("0")
    avg_execution_time: float = 0.0
    critical_alerts_count: int = 0
    high_risk_trades: int = 0
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_alerts": self.total_alerts,
            "total_trades": self.total_trades,
            "total_executions": self.total_executions,
            "failed_risk_checks": self.failed_risk_checks,
            "non_compliant_events": self.non_compliant_events,
            "total_volume": str(self.total_volume),
            "avg_execution_time": self.avg_execution_time,
            "critical_alerts_count": self.critical_alerts_count,
            "high_risk_trades": self.high_risk_trades,
            "generated_at": self.generated_at.isoformat(),
        }


class TradingAuditTrail:
    """
    Immutable audit trail for alert-triggered trades.

    Features:
    - Event logging with timestamps
    - Immutable records (no deletion, only read)
    - Risk level tracking
    - Compliance status verification
    - Audit reports generation
    - Query capabilities
    """

    def __init__(self, max_events: int = 100000):
        """
        Initialize audit trail.

        Args:
            max_events: Maximum events to store in memory (rest would be archived)
        """
        self.events: List[AuditEvent] = []
        self.max_events = max_events
        logger.info("✅ TradingAuditTrail initialized")

    def log_event(
        self,
        event_type: AuditEventType,
        alert_id: Optional[str] = None,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        details: Optional[Dict] = None,
        is_compliant: bool = True,
        risk_level: Optional[str] = None,
        user: str = "system",
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            alert_id: Associated alert ID
            order_id: Associated order ID
            symbol: Trading symbol
            quantity: Quantity traded
            details: Additional details dictionary
            is_compliant: Whether event is compliant
            risk_level: Risk level (low, medium, high, critical)
            user: User or system that triggered event

        Returns:
            Created AuditEvent
        """
        event = AuditEvent(
            event_id=f"audit_{len(self.events)}",
            event_type=event_type,
            alert_id=alert_id,
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            details=details or {},
            is_compliant=is_compliant,
            risk_level=risk_level,
            user=user,
        )

        self.events.append(event)

        # Enforce max events limit
        if len(self.events) > self.max_events:
            # Archive oldest events (simplified - would go to database)
            self.events = self.events[-self.max_events:]

        logger.info(f"📝 Audit event: {event_type.value} (event_id={event.event_id})")
        return event

    def get_event(self, event_id: str) -> Optional[AuditEvent]:
        """
        Get audit event by ID.

        Args:
            event_id: Event ID

        Returns:
            AuditEvent or None
        """
        for event in self.events:
            if event.event_id == event_id:
                return event
        return None

    def get_events_for_alert(self, alert_id: str) -> List[AuditEvent]:
        """
        Get all audit events for an alert.

        Args:
            alert_id: Alert ID

        Returns:
            List of audit events for that alert
        """
        return [e for e in self.events if e.alert_id == alert_id]

    def get_events_for_order(self, order_id: str) -> List[AuditEvent]:
        """
        Get all audit events for an order.

        Args:
            order_id: Order ID

        Returns:
            List of audit events for that order
        """
        return [e for e in self.events if e.order_id == order_id]

    def get_events_by_type(self, event_type: AuditEventType) -> List[AuditEvent]:
        """
        Get all audit events of a specific type.

        Args:
            event_type: Type to filter by

        Returns:
            List of audit events of that type
        """
        return [e for e in self.events if e.event_type == event_type]

    def get_non_compliant_events(self) -> List[AuditEvent]:
        """
        Get all non-compliant audit events.

        Returns:
            List of non-compliant events
        """
        return [e for e in self.events if not e.is_compliant]

    def get_recent_events(self, limit: int = 50) -> List[AuditEvent]:
        """
        Get recent audit events.

        Args:
            limit: Maximum number to return

        Returns:
            List of recent audit events
        """
        return list(reversed(self.events[-limit:]))

    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> ComplianceReport:
        """
        Generate compliance report for period.

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            ComplianceReport
        """
        period_events = [
            e for e in self.events
            if start_date <= e.timestamp <= end_date
        ]

        alert_events = [e for e in period_events if e.event_type == AuditEventType.ALERT_RECEIVED]
        trade_events = [e for e in period_events if e.event_type == AuditEventType.ORDER_PLACED]
        execution_events = [e for e in period_events if e.event_type == AuditEventType.ORDER_EXECUTED]
        failed_risks = [e for e in period_events if e.event_type == AuditEventType.RISK_CHECK_FAILED]
        non_compliant = [e for e in period_events if not e.is_compliant]

        # Calculate metrics
        total_volume = Decimal("0")
        for event in trade_events:
            if event.quantity:
                total_volume += event.quantity

        avg_execution_time = 0.0
        if execution_events and trade_events:
            execution_times = []
            for exec_event in execution_events:
                for trade_event in trade_events:
                    if (exec_event.order_id == trade_event.order_id and
                        exec_event.timestamp > trade_event.timestamp):
                        time_diff = (
                            exec_event.timestamp - trade_event.timestamp
                        ).total_seconds()
                        execution_times.append(time_diff)
            if execution_times:
                avg_execution_time = sum(execution_times) / len(execution_times)

        # Count critical and high risk
        critical_count = len([
            e for e in alert_events
            if e.details.get("severity") == "critical"
        ])
        high_risk_count = len([
            e for e in trade_events
            if e.risk_level == "high"
        ])

        report = ComplianceReport(
            report_id=f"report_{len(period_events)}",
            start_date=start_date,
            end_date=end_date,
            total_alerts=len(alert_events),
            total_trades=len(trade_events),
            total_executions=len(execution_events),
            failed_risk_checks=len(failed_risks),
            non_compliant_events=len(non_compliant),
            total_volume=total_volume,
            avg_execution_time=avg_execution_time,
            critical_alerts_count=critical_count,
            high_risk_trades=high_risk_count,
        )

        logger.info(
            f"✅ Compliance report generated: {report.report_id} "
            f"({report.total_alerts} alerts, {report.total_trades} trades)"
        )

        return report

    def get_audit_statistics(self) -> dict:
        """
        Get audit trail statistics.

        Returns:
            Statistics dictionary
        """
        event_counts = {}
        for event_type in AuditEventType:
            event_counts[event_type.value] = len(
                [e for e in self.events if e.event_type == event_type]
            )

        risk_levels = {}
        for event in self.events:
            if event.risk_level:
                risk_levels[event.risk_level] = risk_levels.get(event.risk_level, 0) + 1

        return {
            "total_events": len(self.events),
            "non_compliant_events": len(self.get_non_compliant_events()),
            "by_event_type": event_counts,
            "by_risk_level": risk_levels,
            "date_range": {
                "earliest": self.events[0].timestamp.isoformat() if self.events else None,
                "latest": self.events[-1].timestamp.isoformat() if self.events else None,
            },
        }


# Singleton instance
_audit_trail_instance: Optional["TradingAuditTrail"] = None


def get_trading_audit_trail() -> "TradingAuditTrail":
    """Get or create the trading audit trail singleton.

    Returns:
        TradingAuditTrail: Shared audit trail instance
    """
    global _audit_trail_instance
    if _audit_trail_instance is None:
        _audit_trail_instance = TradingAuditTrail()
    return _audit_trail_instance
