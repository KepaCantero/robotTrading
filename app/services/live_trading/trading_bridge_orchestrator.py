"""
T18.3.2: TradingBridgeOrchestrator - Alert-to-Trade Pipeline Orchestration

Coordinates the complete flow from alert trigger to order execution:
- Listens for alert events
- Maps alerts to trade signals
- Validates risk gates
- Executes orders
- Tracks and monitors execution
- Handles errors and recovery
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from itertools import islice
from typing import Deque, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from app.services.alerting_system import AlertEvent, AlertManager

from .alert_to_trade_mapper import AlertToTradeMapper, TradeSignal
from .broker_connector import BrokerConnector, OrderSide, OrderStatus, get_broker_connector
from .order_manager import OrderManager
from .risk_gates import RiskCheckResult, RiskGates, RiskLevel

logger = logging.getLogger(__name__)


class BridgeStatus(Enum):
    """Trading bridge operational status."""

    IDLE = "idle"
    MONITORING = "monitoring"
    ALERT_RECEIVED = "alert_received"
    SIGNAL_MAPPED = "signal_mapped"
    RISK_CHECK = "risk_check"
    EXECUTING = "executing"
    EXECUTED = "executed"
    ERROR = "error"


@dataclass
class AlertToTradeExecution:
    """Record of alert-triggered trade execution."""

    execution_id: str
    alert_id: str
    signal_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    execution_price: Decimal = Decimal("0")
    execution_status: OrderStatus = OrderStatus.PENDING
    risk_approved: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "alert_id": self.alert_id,
            "signal_id": self.signal_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": str(self.quantity),
            "execution_price": str(self.execution_price),
            "execution_status": self.execution_status.value,
            "risk_approved": self.risk_approved,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "error_message": self.error_message,
        }


class TradingBridgeOrchestrator:
    """
    Orchestrates complete alert-to-trade pipeline.

    Workflow:
    1. Receive alert event
    2. Check if alert should trigger trade (rule matching)
    3. Map alert to trade signal
    4. Validate risk gates
    5. Execute order via broker
    6. Monitor execution
    7. Record in audit trail
    8. Handle errors and recovery
    """

    def __init__(
        self,
        alert_manager: Optional[AlertManager] = None,
        broker: Optional[BrokerConnector] = None,
        order_manager: Optional[OrderManager] = None,
        risk_gates: Optional[RiskGates] = None,
    ):
        """
        Initialize trading bridge orchestrator.

        Args:
            alert_manager: Alert manager instance
            broker: Broker connector instance
            order_manager: Order manager instance
            risk_gates: Risk validation gates
        """
        self.alert_manager = alert_manager
        self.broker = broker or get_broker_connector()
        self.order_manager = order_manager or OrderManager(self.broker)
        self.risk_gates = risk_gates or RiskGates(self.broker)
        self.mapper = AlertToTradeMapper()

        # Tracking (deque with maxlen to prevent memory leaks)
        self.status = BridgeStatus.IDLE
        self.executions: Dict[str, AlertToTradeExecution] = {}
        self.execution_history: Deque[AlertToTradeExecution] = deque(maxlen=10000)
        self.errors: Dict[str, Tuple[AlertEvent, str]] = {}
        self.is_active = False

        # Idempotency: Track processed alert IDs to prevent duplicates
        self._processed_alert_ids: Set[str] = set()
        self._max_processed_ids = 50000  # Limit memory for processed IDs

        # CONCURRENCY: Lock for thread-safe order execution
        self._execution_lock = asyncio.Lock()

        logger.info("✅ TradingBridgeOrchestrator initialized with concurrency protection")

    async def start(self) -> bool:
        """
        Start monitoring for alert events.

        Returns:
            True if successfully started
        """
        if self.is_active:
            logger.warning("⚠️ Trading bridge already active")
            return False

        self.is_active = True
        self.status = BridgeStatus.MONITORING
        logger.info("✅ Trading bridge started and monitoring alerts")
        return True

    async def stop(self) -> bool:
        """
        Stop monitoring for alert events.

        Returns:
            True if successfully stopped
        """
        self.is_active = False
        self.status = BridgeStatus.IDLE
        logger.info("✅ Trading bridge stopped")
        return True

    async def process_alert(
        self,
        alert_event: AlertEvent,
    ) -> Optional[AlertToTradeExecution]:
        """
        Process alert event and potentially execute trade.

        Args:
            alert_event: Alert event to process

        Returns:
            AlertToTradeExecution if trade executed, None otherwise
        """
        if not self.is_active:
            logger.warning("⚠️ Trading bridge not active, ignoring alert")
            return None

        # CONCURRENCY: Acquire lock for thread-safe execution
        async with self._execution_lock:
            # IDEMPOTENCY CHECK: Prevent duplicate processing (inside lock)
            if alert_event.event_id in self._processed_alert_ids:
                logger.warning(f"⚠️ Alert already processed (idempotency): {alert_event.event_id}")
                # Return existing execution if available
                for exec_id, execution in self.executions.items():
                    if execution.alert_id == alert_event.event_id:
                        return execution
                return None

            try:
                self.status = BridgeStatus.ALERT_RECEIVED
                logger.info(f"🔔 Processing alert: {alert_event.event_id}")

                # Mark as processed BEFORE execution to prevent race conditions
                self._processed_alert_ids.add(alert_event.event_id)

                # Cleanup old processed IDs to prevent memory leak
                if len(self._processed_alert_ids) > self._max_processed_ids:
                    # Remove oldest half
                    to_remove = list(self._processed_alert_ids)[: self._max_processed_ids // 2]
                    for old_id in to_remove:
                        self._processed_alert_ids.discard(old_id)

                # Get broker account for portfolio value
                account = await self.broker.get_account_info()
                if not account:
                    logger.error("❌ Failed to get broker account info")
                    return None

                portfolio_value = await self.broker.calculate_portfolio_value()
                current_price = alert_event.metric_value or Decimal("100")

                # Map alert to trade signal
                self.status = BridgeStatus.SIGNAL_MAPPED
                signal = self.mapper.map_alert_to_signal(
                    alert_id=alert_event.event_id,
                    alert_rule_id=alert_event.rule_id,
                    symbol=alert_event.symbol or "SPY",
                    severity=alert_event.severity,
                    current_price=current_price,
                    portfolio_value=portfolio_value,
                )

                if not signal:
                    logger.warning(
                        f"⚠️ No trade signal generated for alert: {alert_event.event_id}"
                    )
                    return None

                # Validate risk gates
                self.status = BridgeStatus.RISK_CHECK
                risk_result = await self._validate_risk_gates(signal, account)

                if not risk_result.passed:
                    error_msg = f"Risk validation failed: {', '.join(risk_result.violations)}"
                    logger.error(f"❌ {error_msg}")
                    self.errors[alert_event.event_id] = (alert_event, error_msg)
                    return None

                if risk_result.risk_level == RiskLevel.HIGH:
                    logger.warning("⚠️ High risk trade - proceeding with caution")

                # Execute trade
                self.status = BridgeStatus.EXECUTING
                execution = await self._execute_trade(signal, alert_event)

                if execution:
                    self.status = BridgeStatus.EXECUTED
                    self.executions[execution.execution_id] = execution
                    self.execution_history.append(execution)
                    logger.info(
                        f"✅ Trade executed: {execution.execution_id} "
                        f"({execution.side.value} {execution.quantity} {execution.symbol})"
                    )
                    return execution
                else:
                    logger.error("❌ Trade execution failed")
                    return None

            except (ValueError, KeyError, AttributeError, IndexError, TypeError, ConnectionError, OSError) as e:
                self.status = BridgeStatus.ERROR
                logger.error(f"❌ Error processing alert: {str(e)}")
                if hasattr(alert_event, 'event_id'):
                    self.errors[alert_event.event_id] = (alert_event, str(e))
                return None

    async def _validate_risk_gates(
        self,
        signal: TradeSignal,
        account,
    ) -> RiskCheckResult:
        """
        Validate trade signal against risk gates.

        TRD-002: Delegates to RiskGates.validate_order() for complete validation
        including all 7 risk checks (position size, buying power, concentration,
        leverage, daily loss limit, drawdown limit, cash reserve).

        Args:
            signal: Trade signal to validate
            account: Broker account info

        Returns:
            RiskCheckResult with pass/fail status
        """
        # TRD-002: Use centralized risk validation via RiskGates.validate_order()
        # This ensures ALL 7 risk checks are performed, not just the 3 manual ones
        # that were previously implemented here.

        # Determine order price for validation
        order_price = signal.price
        if order_price is None:
            # For market orders, use a conservative estimate
            order_price = Decimal("100")

        try:
            # Delegate to RiskGates for complete risk validation
            # This performs: position size, buying power, concentration, leverage,
            # daily loss limit, drawdown limit, and cash reserve checks
            result = await self.risk_gates.validate_order(
                symbol=signal.symbol,
                side=signal.order_side,
                quantity=signal.quantity,
                price=order_price,
            )

            if not result.passed:
                logger.warning(
                    "Risk validation failed - trade rejected",
                    extra={
                        "signal_id": signal.signal_id,
                        "symbol": signal.symbol,
                        "side": signal.order_side.value,
                        "quantity": str(signal.quantity),
                        "price": str(order_price),
                        "risk_level": result.risk_level.value,
                        "violations": result.violations,
                        "warnings": result.warnings,
                    },
                )
            else:
                logger.info(
                    "Risk validation passed - trade approved",
                    extra={
                        "signal_id": signal.signal_id,
                        "symbol": signal.symbol,
                        "side": signal.order_side.value,
                        "quantity": str(signal.quantity),
                        "price": str(order_price),
                        "risk_level": result.risk_level.value,
                    },
                )

            return result

        except Exception as e:
            logger.error(
                "Risk validation error - failing closed",
                extra={
                    "signal_id": signal.signal_id,
                    "symbol": signal.symbol,
                    "error": str(e),
                },
                exc_info=True,
            )
            # Fail closed on any error during risk validation
            return RiskCheckResult(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                violations=[f"Risk validation error: {str(e)}"],
            )

    async def _execute_trade(
        self,
        signal: TradeSignal,
        alert_event: AlertEvent,
    ) -> Optional[AlertToTradeExecution]:
        """
        Execute trade based on signal.

        Args:
            signal: Trade signal with order parameters
            alert_event: Originating alert event

        Returns:
            AlertToTradeExecution if successful
        """
        try:
            # Place order with broker
            order = await self.broker.place_order(
                symbol=signal.symbol,
                side=signal.order_side,
                quantity=signal.quantity,
                order_type=signal.order_type,
                price=signal.price,
            )

            if not order:
                logger.error(f"❌ Failed to place order for signal: {signal.signal_id}")
                return None

            # Create execution record with unique UUID
            execution = AlertToTradeExecution(
                execution_id=f"exec_{uuid4().hex}",
                alert_id=signal.alert_id,
                signal_id=signal.signal_id,
                order_id=order.order_id,
                symbol=signal.symbol,
                side=signal.order_side,
                quantity=signal.quantity,
                execution_price=signal.price or Decimal("0"),
                execution_status=order.status,
                risk_approved=True,
            )

            # Monitor order status
            asyncio.create_task(self._monitor_order(execution))

            return execution

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.error(f"❌ Error executing trade: {str(e)}")
            return None

    async def _monitor_order(self, execution: AlertToTradeExecution) -> None:
        """
        Monitor order execution status.

        Args:
            execution: AlertToTradeExecution to monitor
        """
        max_checks = 30
        check_interval = 1  # second
        checks = 0

        while checks < max_checks:
            try:
                status = await self.broker.get_order_status(execution.order_id)
                if status in (OrderStatus.FILLED, OrderStatus.EXECUTED):
                    execution.execution_status = status
                    execution.executed_at = datetime.utcnow()
                    logger.info(
                        f"✅ Order filled: {execution.order_id} "
                        f"({execution.side.value} {execution.quantity} {execution.symbol})"
                    )
                    break
                elif status in (OrderStatus.CANCELED, OrderStatus.REJECTED):
                    execution.execution_status = status
                    execution.error_message = f"Order {status.value}"
                    logger.warning(f"⚠️ Order {status.value}: {execution.order_id}")
                    break

                checks += 1
                await asyncio.sleep(check_interval)

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"❌ Error monitoring order: {str(e)}")
                break

    def get_execution(self, execution_id: str) -> Optional[AlertToTradeExecution]:
        """
        Get execution record by ID.

        Args:
            execution_id: Execution ID

        Returns:
            AlertToTradeExecution or None
        """
        return self.executions.get(execution_id)

    def get_recent_executions(self, limit: int = 10) -> List[AlertToTradeExecution]:
        """
        Get recent trade executions.

        Args:
            limit: Maximum number to return

        Returns:
            List of recent AlertToTradeExecution
        """
        # Use islice for deque compatibility, then reverse to get most recent first
        recent = list(
            islice(self.execution_history, max(0, len(self.execution_history) - limit), None)
        )
        return list(reversed(recent))

    def get_bridge_statistics(self) -> dict:
        """
        Get trading bridge statistics.

        Returns:
            Statistics dictionary
        """
        successful = len(
            [e for e in self.execution_history if e.execution_status == OrderStatus.FILLED]
        )
        failed = len(
            [
                e
                for e in self.execution_history
                if e.execution_status in (OrderStatus.CANCELED, OrderStatus.REJECTED)
            ]
        )

        return {
            "status": self.status.value,
            "is_active": self.is_active,
            "total_executions": len(self.execution_history),
            "successful_trades": successful,
            "failed_trades": failed,
            "pending_orders": len(
                [
                    e
                    for e in self.executions.values()
                    if e.execution_status in (OrderStatus.PENDING, OrderStatus.SUBMITTED)
                ]
            ),
            "errors": len(self.errors),
            "mapped_signals": len(self.mapper.signal_history),
        }


# Singleton instance
_orchestrator_instance: Optional[TradingBridgeOrchestrator] = None


def get_trading_bridge_orchestrator() -> TradingBridgeOrchestrator:
    """Get or create the trading bridge orchestrator singleton.

    Returns:
        TradingBridgeOrchestrator: Shared orchestrator instance
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = TradingBridgeOrchestrator()

    return _orchestrator_instance
