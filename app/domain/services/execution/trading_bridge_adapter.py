"""
Trading Bridge Adapter for Task 12 - Trading Bridge Integration

This adapter bridges TradingBridgeOrchestrator with the ITradeExecutor protocol
used by ComplianceEngine, enabling live trading execution based on alerts.

Purpose: Integrate TradingBridge with ComplianceEngine for live trading execution
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.application.alerting import AlertEvent, AlertSeverity
from app.services.live_trading.trading_bridge_orchestrator import (
    TradingBridgeOrchestrator,
    get_trading_bridge_orchestrator,
)
from app.shared.protocols import ITradeExecutor

logger = logging.getLogger(__name__)


class TradingBridgeAdapter(ITradeExecutor):
    """
    Adapter that implements ITradeExecutor using TradingBridgeOrchestrator.

    This adapter connects the live trading orchestrator (TradingBridgeOrchestrator)
    with the coordinator layer (ComplianceEngine), providing:

    1. Alert-based trade execution
    2. Risk validation via RiskGates
    3. Alert-to-signal mapping
    4. Order execution monitoring

    Integration Points:
    - TradingBridgeOrchestrator: Provides live trading execution via alerts
    - ComplianceEngine: Uses ITradeExecutor for trade execution
    """

    def __init__(
        self,
        trading_bridge: Optional[TradingBridgeOrchestrator] = None,
        enable_logging: bool = False,
    ):
        """
        Initialize TradingBridgeAdapter.

        Args:
            trading_bridge: Optional TradingBridgeOrchestrator instance
                             (defaults to singleton instance)
            enable_logging: Enable detailed logging for execution events
        """
        self.trading_bridge = trading_bridge or get_trading_bridge_orchestrator()
        self.enable_logging = enable_logging
        self._order_mapping: Dict[str, str] = {}  # Maps order_id to execution_id

    async def execute_order(
        self,
        signal: "TradeSignal",
    ) -> "TradeResult":
        """
        Execute order using TradingBridgeOrchestrator.

        This method implements the ITradeExecutor protocol by converting
        a TradeSignal into an execution via TradingBridgeOrchestrator.

        The process:
        1. Extract signal data (symbol, side, quantity, price)
        2. Create a mock AlertEvent for the signal
        3. Process alert through trading bridge
        4. Return execution result as TradeResult

        Args:
            signal: TradeSignal containing:
                - symbol: Trading symbol
                - order_side: BUY or SELL
                - quantity: Order quantity
                - price: Signal price
                - order_type: MARKET or LIMIT
                - stop_loss: Optional stop loss price
                - take_profit: Optional take profit price

        Returns:
            TradeResult with execution details including:
                - order_id: Unique order identifier
                - symbol: Trading symbol
                - side: Order side
                - quantity: Executed quantity
                - execution_price: Price with slippage applied
                - status: FILL status
                - commission: Calculated commission
                - slippage_bps: Applied slippage in basis points
        """
        from dataclasses import dataclass

        @dataclass
        class TradeResult:
            """Result of trade execution via ITradeExecutor."""

            success: bool
            order_id: str
            symbol: str
            side: str
            quantity: Decimal
            execution_price: Decimal
            status: str
            commission: Decimal
            slippage_bps: Decimal
            signal_price: Decimal
            error: Optional[str] = None

        try:
            # Extract signal data
            symbol = signal.symbol
            side = signal.order_side.value
            quantity = signal.quantity
            signal_price = signal.price or Decimal("0")

            # Create mock alert event for the signal
            alert_event = AlertEvent(
                event_id=f"alert_{signal.signal_id if hasattr(signal, 'signal_id') else 'manual'}",
                rule_id="manual_trade",
                severity=AlertSeverity.WARNING,
                metric_value=signal_price,
                symbol=symbol,
            )

            # Process alert through trading bridge
            execution = await self.trading_bridge.process_alert(alert_event)

            if not execution:
                # Failed to execute
                return TradeResult(
                    success=False,
                    order_id="",
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    execution_price=Decimal("0"),
                    status="FAILED",
                    commission=Decimal("0"),
                    slippage_bps=Decimal("0"),
                    signal_price=signal_price,
                    error="Trading bridge did not return execution",
                )

            # Map order_id to execution_id
            self._order_mapping[execution.order_id] = execution.execution_id

            if self.enable_logging:
                logger.info(
                    f"TradingBridgeAdapter: {symbol} {side} {quantity} @ {execution.execution_price} "
                    f"(order_id: {execution.order_id}, execution_id: {execution.execution_id})"
                )

            return TradeResult(
                success=True,
                order_id=execution.order_id,
                symbol=execution.symbol,
                side=execution.side.value,
                quantity=execution.quantity,
                execution_price=execution.execution_price,
                status=execution.execution_status.value,
                commission=Decimal("0"),  # Commission handled by broker
                slippage_bps=Decimal("0"),  # Slippage handled by broker
                signal_price=signal_price,
            )

        except Exception as e:
            logger.error(f"TradingBridgeAdapter.execute_order failed: {e}")
            return TradeResult(
                success=False,
                order_id="",
                symbol=getattr(signal, "symbol", "UNKNOWN"),
                side=getattr(signal, "order_side", "BUY").value
                if hasattr(signal, "order_side")
                else "BUY",
                quantity=getattr(signal, "quantity", Decimal("0")),
                execution_price=Decimal("0"),
                status="FAILED",
                commission=Decimal("0"),
                slippage_bps=Decimal("0"),
                signal_price=Decimal("0"),
                error=str(e),
            )

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order via TradingBridgeOrchestrator.

        Args:
            order_id: Order identifier to cancel

        Returns:
            True if cancellation successful, False otherwise
        """
        try:
            if self.enable_logging:
                logger.debug(f"TradingBridgeAdapter.cancel_order: {order_id}")

            # The TradingBridgeOrchestrator doesn't have direct cancel
            # We need to cancel via the broker
            broker = self.trading_bridge.broker
            result = await broker.cancel_order(order_id)

            return result

        except Exception as e:
            logger.error(f"TradingBridgeAdapter.cancel_order failed: {e}")
            return False

    async def modify_order(self, order_id: str, new_price: Decimal) -> bool:
        """
        Modify order price via TradingBridgeOrchestrator.

        Args:
            order_id: Order identifier to modify
            new_price: New price for the order

        Returns:
            True if modification successful, False otherwise
        """
        try:
            if self.enable_logging:
                logger.debug(f"TradingBridgeAdapter.modify_order: {order_id} -> {new_price}")

            # The TradingBridgeOrchestrator doesn't have direct modify
            # We need to modify via the broker
            broker = self.trading_bridge.broker
            result = await broker.modify_order(order_id, new_price)

            return result

        except Exception as e:
            logger.error(f"TradingBridgeAdapter.modify_order failed: {e}")
            return False

    async def get_order_status(self, order_id: str) -> str:
        """
        Get order status via TradingBridgeOrchestrator.

        Args:
            order_id: Order identifier

        Returns:
            Order status: "FILLED", "PENDING", "CANCELLED", "UNKNOWN"
        """
        try:
            if self.enable_logging:
                logger.debug(f"TradingBridgeAdapter.get_order_status: {order_id}")

            broker = self.trading_bridge.broker
            status = await broker.get_order_status(order_id)

            return status.value if hasattr(status, "value") else str(status)

        except Exception as e:
            logger.error(f"TradingBridgeAdapter.get_order_status failed: {e}")
            return "UNKNOWN"

    async def get_open_orders(self) -> List:
        """
        Get open orders via TradingBridgeOrchestrator.

        Returns:
            List of open orders
        """
        try:
            if self.enable_logging:
                logger.debug("TradingBridgeAdapter.get_open_orders")

            broker = self.trading_bridge.broker
            open_orders = await broker.get_open_orders()

            return open_orders

        except Exception as e:
            logger.error(f"TradingBridgeAdapter.get_open_orders failed: {e}")
            return []

    # -------------------------------------------------------------------------
    # Additional methods for enhanced functionality
    # -------------------------------------------------------------------------

    def get_execution_history(self) -> List:
        """
        Get execution history from trading bridge.

        Returns:
            List of recent executions
        """
        return self.trading_bridge.get_recent_executions(limit=100)

    def get_bridge_statistics(self) -> Dict[str, Any]:
        """
        Get trading bridge statistics.

        Returns:
            Dictionary with bridge metrics
        """
        return self.trading_bridge.get_bridge_statistics()

    def get_order_mapping(self) -> Dict[str, str]:
        """
        Get order ID to execution ID mapping.

        Returns:
            Dictionary mapping order_id to execution_id
        """
        return self._order_mapping.copy()


def get_trading_bridge_adapter(
    enable_logging: bool = False,
) -> TradingBridgeAdapter:
    """
    Factory function to get TradingBridgeAdapter instance.

    Args:
        enable_logging: Enable detailed logging

    Returns:
        Configured TradingBridgeAdapter instance

    Example:
        >>> adapter = get_trading_bridge_adapter(enable_logging=True)
        >>> result = await adapter.execute_order(signal)
    """
    return TradingBridgeAdapter(enable_logging=enable_logging)
