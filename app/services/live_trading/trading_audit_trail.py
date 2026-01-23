"""
T18.3.4: TradingAuditTrail - Compliance and audit logging

Comprehensive audit trail for all alert-triggered trades:
- Immutable event logging
- Trade justification tracking
- Risk validation records
- Execution evidence
- Compliance reporting

PRODUCTION: SQLite persistence for MiFID II compliance.
MEMORY: Uses deque with maxlen to prevent unbounded memory growth.
UTC: All timestamps are timezone-aware UTC.
"""

import json
import logging
import sqlite3
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


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
    timestamp: datetime = field(default_factory=utc_now)
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
    generated_at: datetime = field(default_factory=utc_now)

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


class AuditPersistence:
    """
    SQLite persistence layer for audit trail.

    MiFID II COMPLIANCE: Immutable audit records stored on disk.
    PRODUCTION: WAL mode for concurrent access, thread-safe.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize audit persistence.

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path("data/audit_trail.db")
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_database()
        logger.info(f"✅ AuditPersistence initialized: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection with connection pooling."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row
            # WAL mode for concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.connection = conn
        return self._local.connection

    def _init_database(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                alert_id TEXT,
                order_id TEXT,
                symbol TEXT,
                quantity TEXT,
                user TEXT DEFAULT 'system',
                ip_address TEXT,
                details TEXT,
                is_compliant INTEGER DEFAULT 1,
                risk_level TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        # Indices for fast queries (MiFID II compliance queries)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_alert_id ON audit_events(alert_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_order_id ON audit_events(order_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_compliant ON audit_events(is_compliant)")
        conn.commit()

    def save_event(self, event: AuditEvent) -> bool:
        """
        Persist audit event to database.

        Args:
            event: AuditEvent to persist

        Returns:
            True if saved successfully
        """
        try:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO audit_events
                (event_id, event_type, timestamp, alert_id, order_id, symbol,
                 quantity, user, ip_address, details, is_compliant, risk_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.alert_id,
                    event.order_id,
                    event.symbol,
                    str(event.quantity) if event.quantity else None,
                    event.user,
                    event.ip_address,
                    json.dumps(event.details),
                    1 if event.is_compliant else 0,
                    event.risk_level,
                ),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to persist audit event: {e}")
            return False

    def get_events(
        self,
        limit: int = 1000,
        offset: int = 0,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get audit events from database.

        Args:
            limit: Maximum events to return
            offset: Offset for pagination
            event_type: Filter by event type
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of event dictionaries
        """
        try:
            conn = self._get_connection()
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get audit events: {e}")
            return []

    def get_event_count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get total event count for date range."""
        try:
            conn = self._get_connection()
            query = "SELECT COUNT(*) FROM audit_events WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to count audit events: {e}")
            return 0

    def get_non_compliant_events(self, limit: int = 100) -> List[Dict]:
        """Get non-compliant events for compliance review."""
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM audit_events WHERE is_compliant = 0 ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get non-compliant events: {e}")
            return []

    def close(self) -> None:
        """Close database connection and cleanup resources."""
        try:
            if hasattr(self._local, 'connection') and self._local.connection is not None:
                self._local.connection.close()
                self._local.connection = None
                logger.debug("AuditPersistence connection closed")
        except Exception as e:
            logger.warning(f"Error closing AuditPersistence connection: {e}")


# Singleton persistence instance
_audit_persistence: Optional[AuditPersistence] = None


def get_audit_persistence(db_path: Optional[Path] = None) -> AuditPersistence:
    """Get or create singleton AuditPersistence."""
    global _audit_persistence
    if _audit_persistence is None:
        _audit_persistence = AuditPersistence(db_path)
    return _audit_persistence


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
    - SQLite persistence for MiFID II compliance

    PRODUCTION: All events persisted to SQLite for crash recovery.
    MEMORY: Uses deque with maxlen to prevent unbounded memory growth.
    """

    def __init__(
        self,
        max_events: int = 10000,
        persistence: Optional[AuditPersistence] = None,
        db_path: Optional[Path] = None,
    ):
        """
        Initialize audit trail with persistence.

        Args:
            max_events: Maximum events to store in memory
            persistence: Optional persistence layer (will create if not provided)
            db_path: Optional path to database file
        """
        self.persistence = persistence or get_audit_persistence(db_path)
        # MEMORY: Use deque with maxlen to prevent unbounded growth
        self.events: Deque[AuditEvent] = deque(maxlen=max_events)
        self.max_events = max_events
        self._event_counter = 0

        # Load recent events from persistence on startup
        self._load_from_persistence()
        logger.info("✅ TradingAuditTrail initialized with SQLite persistence")

    def _load_from_persistence(self) -> None:
        """Load recent events from persistence layer on startup."""
        try:
            event_dicts = self.persistence.get_events(limit=self.max_events)
            for event_dict in reversed(event_dicts):  # Oldest first
                event = self._dict_to_audit_event(event_dict)
                if event:
                    self.events.append(event)
                    # Track highest event counter
                    if event.event_id.startswith("audit_"):
                        try:
                            counter = int(event.event_id.split("_")[1])
                            self._event_counter = max(self._event_counter, counter + 1)
                        except (ValueError, IndexError):
                            pass
            logger.info(f"Loaded {len(self.events)} audit events from persistence")
        except Exception as e:
            logger.error(f"Error loading from persistence: {e}")

    def _dict_to_audit_event(self, data: Dict) -> Optional[AuditEvent]:
        """Convert dictionary to AuditEvent."""
        try:
            # Parse timestamp
            timestamp = data.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            elif timestamp is None:
                timestamp = utc_now()

            # Parse quantity
            quantity = data.get('quantity')
            if quantity is not None and isinstance(quantity, str):
                quantity = Decimal(quantity)

            # Parse details
            details = data.get('details', {})
            if isinstance(details, str):
                details = json.loads(details)

            return AuditEvent(
                event_id=data['event_id'],
                event_type=AuditEventType(data['event_type']),
                timestamp=timestamp,
                alert_id=data.get('alert_id'),
                order_id=data.get('order_id'),
                symbol=data.get('symbol'),
                quantity=quantity,
                user=data.get('user', 'system'),
                ip_address=data.get('ip_address'),
                details=details,
                is_compliant=bool(data.get('is_compliant', 1)),
                risk_level=data.get('risk_level'),
            )
        except Exception as e:
            logger.warning(f"Failed to convert audit event data: {e}")
            return None

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
        # Generate unique event ID with counter
        event_id = f"audit_{self._event_counter}"
        self._event_counter += 1

        event = AuditEvent(
            event_id=event_id,
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

        # Add to in-memory deque (auto-evicts oldest if at maxlen)
        self.events.append(event)

        # Persist to SQLite for MiFID II compliance
        self.persistence.save_event(event)

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
        return list(reversed(list(self.events)[-limit:]))

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
        period_events = [e for e in self.events if start_date <= e.timestamp <= end_date]

        alert_events = [e for e in period_events if e.event_type == AuditEventType.ALERT_RECEIVED]
        trade_events = [e for e in period_events if e.event_type == AuditEventType.ORDER_PLACED]
        execution_events = [
            e for e in period_events if e.event_type == AuditEventType.ORDER_EXECUTED
        ]
        failed_risks = [
            e for e in period_events if e.event_type == AuditEventType.RISK_CHECK_FAILED
        ]
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
                    if (
                        exec_event.order_id == trade_event.order_id
                        and exec_event.timestamp > trade_event.timestamp
                    ):
                        time_diff = (exec_event.timestamp - trade_event.timestamp).total_seconds()
                        execution_times.append(time_diff)
            if execution_times:
                avg_execution_time = sum(execution_times) / len(execution_times)

        # Count critical and high risk
        critical_count = len([e for e in alert_events if e.details.get("severity") == "critical"])
        high_risk_count = len([e for e in trade_events if e.risk_level == "high"])

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
