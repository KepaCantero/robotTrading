"""
T18.3.1: AlertToTradeMapper - Maps alerts to trading actions

Translates alert triggers into trading actions based on rules:
- Alert severity → Position size
- Alert type → Order type and direction
- Symbol-specific rules
- Risk-adjusted quantities
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from app.services.alerting_system import AlertEvent, AlertSeverity
from .broker_connector import OrderSide, OrderType

logger = logging.getLogger(__name__)


class TradeSignalType(Enum):
    """Types of trade signals from alerts."""
    LONG = "long"
    SHORT = "short"
    REDUCE_POSITION = "reduce_position"
    CLOSE_POSITION = "close_position"
    LIQUIDATE = "liquidate"


@dataclass
class AlertToTradeRule:
    """Rule mapping alert to trade action."""
    rule_id: str
    alert_rule_id: str
    enabled: bool = True
    signal_type: TradeSignalType = TradeSignalType.LONG
    base_quantity: Decimal = Decimal("100")
    # Severity-based scaling
    severity_multipliers: Dict[AlertSeverity, Decimal] = field(
        default_factory=lambda: {
            AlertSeverity.INFO: Decimal("0.5"),
            AlertSeverity.WARNING: Decimal("1.0"),
            AlertSeverity.CRITICAL: Decimal("2.0"),
        }
    )
    # Risk adjustments
    max_position_size: Decimal = Decimal("50000")
    use_limit_orders: bool = False
    limit_price_offset: Decimal = Decimal("0.01")  # 1% offset
    # Time-based rules
    quiet_period_minutes: int = 0  # Cooldown between trades
    last_triggered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradeSignal:
    """Trade signal generated from alert."""
    signal_id: str
    alert_id: str
    alert_rule_id: str
    symbol: str
    signal_type: TradeSignalType
    order_side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    reason: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "signal_id": self.signal_id,
            "alert_id": self.alert_id,
            "alert_rule_id": self.alert_rule_id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "order_side": self.order_side.value,
            "order_type": self.order_type.value,
            "quantity": str(self.quantity),
            "price": str(self.price) if self.price else None,
            "stop_loss": str(self.stop_loss) if self.stop_loss else None,
            "take_profit": str(self.take_profit) if self.take_profit else None,
            "severity": self.severity.value,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


class AlertToTradeMapper:
    """
    Maps alert events to trade signals.

    Features:
    - Alert severity-based position sizing
    - Cooldown period enforcement
    - Risk-aware quantity calculation
    - Multiple signal types (long, short, reduce, close, liquidate)
    - Symbol-specific routing
    """

    def __init__(self):
        """Initialize mapper."""
        self.rules: Dict[str, AlertToTradeRule] = {}
        self.signals: Dict[str, TradeSignal] = {}
        self.signal_history: List[TradeSignal] = []
        logger.info("✅ AlertToTradeMapper initialized")

    def register_rule(self, rule: AlertToTradeRule) -> None:
        """
        Register alert-to-trade mapping rule.

        Args:
            rule: AlertToTradeRule configuration
        """
        self.rules[rule.rule_id] = rule
        logger.info(f"✅ Registered trade rule: {rule.rule_id} → {rule.signal_type.value}")

    def unregister_rule(self, rule_id: str) -> bool:
        """
        Unregister trade rule.

        Args:
            rule_id: Rule ID to remove

        Returns:
            True if removed, False if not found
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"✅ Unregistered trade rule: {rule_id}")
            return True
        return False

    def map_alert_to_signal(
        self,
        alert_id: str,
        alert_rule_id: str,
        symbol: str,
        severity: AlertSeverity,
        current_price: Decimal,
        portfolio_value: Decimal,
    ) -> Optional[TradeSignal]:
        """
        Map alert to trade signal.

        Args:
            alert_id: Alert event ID
            alert_rule_id: Alert rule ID
            symbol: Asset symbol
            severity: Alert severity level
            current_price: Current market price
            portfolio_value: Total portfolio value

        Returns:
            TradeSignal if mapping successful, None otherwise
        """
        # Find matching rule
        rule = None
        for r in self.rules.values():
            if r.alert_rule_id == alert_rule_id and r.enabled:
                rule = r
                break

        if not rule:
            logger.warning(f"⚠️ No trade rule found for alert: {alert_rule_id}")
            return None

        # Check quiet period
        if rule.last_triggered_at:
            from datetime import timedelta
            time_since_trigger = (
                datetime.utcnow() - rule.last_triggered_at
            ).total_seconds() / 60  # minutes
            if time_since_trigger < rule.quiet_period_minutes:
                logger.warning(
                    f"⚠️ Trade rule in quiet period: {rule.rule_id}"
                )
                return None

        # Calculate quantity based on severity
        severity_multiplier = rule.severity_multipliers.get(
            severity, Decimal("1.0")
        )
        quantity = rule.base_quantity * severity_multiplier

        # Apply risk-based limits
        position_value = quantity * current_price
        if position_value > rule.max_position_size:
            # Scale down to respect position size limit
            quantity = rule.max_position_size / current_price

        # Ensure integer shares
        quantity = Decimal(int(quantity))

        if quantity <= 0:
            logger.warning(
                f"⚠️ Calculated quantity too small: {quantity}"
            )
            return None

        # Determine order parameters
        order_side = OrderSide.BUY if rule.signal_type == TradeSignalType.LONG else OrderSide.SELL
        order_type = (
            OrderType.LIMIT if rule.use_limit_orders
            else OrderType.MARKET
        )

        # Calculate limit price if needed
        limit_price = None
        if rule.use_limit_orders:
            offset = current_price * rule.limit_price_offset / Decimal("100")
            if rule.signal_type == TradeSignalType.LONG:
                limit_price = current_price - offset
            else:
                limit_price = current_price + offset

        # Create signal
        signal = TradeSignal(
            signal_id=f"signal_{len(self.signals)}",
            alert_id=alert_id,
            alert_rule_id=alert_rule_id,
            symbol=symbol,
            signal_type=rule.signal_type,
            order_side=order_side,
            order_type=order_type,
            quantity=quantity,
            price=limit_price,
            severity=severity,
            reason=f"Alert {alert_id} triggered {rule.signal_type.value} signal",
        )

        # Store signal
        self.signals[signal.signal_id] = signal
        self.signal_history.append(signal)
        rule.last_triggered_at = datetime.utcnow()

        logger.info(
            f"✅ Mapped alert to signal: {signal.signal_id} "
            f"({order_side.value} {quantity} {symbol})"
        )

        return signal

    def get_signal(self, signal_id: str) -> Optional[TradeSignal]:
        """
        Get trade signal by ID.

        Args:
            signal_id: Signal ID

        Returns:
            TradeSignal or None
        """
        return self.signals.get(signal_id)

    def get_pending_signals(self, alert_rule_id: Optional[str] = None) -> List[TradeSignal]:
        """
        Get all pending (unmapped to orders) trade signals.

        Args:
            alert_rule_id: Optional filter by alert rule ID

        Returns:
            List of pending TradeSignal objects
        """
        pending = [
            s for s in self.signals.values()
            if not hasattr(s, 'order_id') or not s.order_id
        ]

        if alert_rule_id:
            pending = [s for s in pending if s.alert_rule_id == alert_rule_id]

        return pending

    def get_signal_statistics(self) -> dict:
        """
        Get signal generation statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_signals": len(self.signal_history),
            "active_rules": len([r for r in self.rules.values() if r.enabled]),
            "pending_signals": len(self.get_pending_signals()),
            "by_signal_type": {
                st.value: len([s for s in self.signal_history if s.signal_type == st])
                for st in TradeSignalType
            },
            "by_severity": {
                sev.value: len([s for s in self.signal_history if s.severity == sev])
                for sev in AlertSeverity
            },
        }
