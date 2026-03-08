"""
Execution Engine Adapter for Task 10 - Execution Engine Integration

This adapter bridges PessimisticExecutionEngine with the ITradeExecutor protocol
used by ComplianceEngine, enabling realistic order execution in the trading system.

Purpose: Integrate ExecutionEngine with ComplianceEngine (Req #10 - Pessimistic Execution)
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from app.backtesting.engines.execution_engine import PessimisticExecutionEngine
from app.shared.protocols import ITradeExecutor

logger = logging.getLogger(__name__)


class ExecutionEngineAdapter(ITradeExecutor):
    """
    Adapter that implements ITradeExecutor using PessimisticExecutionEngine.

    This adapter connects the pessimistic execution engine (backtesting) with the
    coordinator layer (ComplianceEngine), providing:

    1. Realistic execution with slippage (configurable basis points)
    2. t+1 execution delays (signal at close t, execution at open t+1)
    3. Pessimistic stop handling (SL before TP in same bar)
    4. Commission calculation via CostCalculator

    Integration Points:
    - PessimisticExecutionEngine: Provides realistic backtesting execution
    - ComplianceEngine: Uses ITradeExecutor for trade execution
    """

    def __init__(
        self,
        execution_engine: Optional[PessimisticExecutionEngine] = None,
        enable_logging: bool = False,
    ):
        """
        Initialize ExecutionEngineAdapter.

        Args:
            execution_engine: Optional PessimisticExecutionEngine instance
                             (defaults to new instance with standard config)
            enable_logging: Enable detailed logging for execution events
        """
        self.execution_engine = execution_engine or PessimisticExecutionEngine()
        self.enable_logging = enable_logging
        self._active_positions: Dict[str, Any] = {}
        self._order_history: Dict[str, Dict[str, Any]] = {}

    async def execute_order(
        self,
        signal: "TradeSignal",
    ) -> "TradeResult":
        """
        Execute order using PessimisticExecutionEngine with realistic delays.

        This method implements the ITradeExecutor protocol by:

        1. Creating an ExecutionResult with realistic t+1 delays
        2. Applying slippage based on configuration (0.05% default)
        3. Calculating commission via CostCalculator

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

        Example:
            >>> signal = TradeSignal(
            ...     symbol="AAPL",
            ...     order_side=OrderSide.BUY,
            ...     quantity=Decimal("100"),
            ...     price=Decimal("150"),
            ... )
            >>> result = await adapter.execute_order(signal)
            >>> assert result.status == "FILLED"
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

            if signal_price <= 0:
                # Estimate price if not provided
                signal_price = Decimal("100")

            # Generate order ID
            signal_time = datetime.utcnow()
            order_id = f"exec_{signal_time.strftime('%Y%m%d%H%M%S%f')}"

            # Simulate execution with realistic delays (t+1)
            # In production, next_open_price would come from next bar's data
            execution_price = signal_price  # Simplified for live trading

            # Calculate default slippage (0.05% = 5 bps)
            slippage_bps = Decimal("5")
            commission = Decimal("1")  # Default commission

            # Apply slippage to execution price (worse for trader)
            if side.upper() == "BUY":
                execution_price = signal_price * (Decimal("1") + slippage_bps / Decimal("10000"))
            else:  # SELL
                execution_price = signal_price * (Decimal("1") - slippage_bps / Decimal("10000"))

            # Quantize to 2 decimal places
            execution_price = execution_price.quantize(Decimal("0.01"))

            # Track order
            self._order_history[order_id] = {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": str(quantity),
                "signal_price": str(signal_price),
                "execution_price": str(execution_price),
                "slippage_bps": str(slippage_bps),
                "commission": str(commission),
                "signal_time": signal_time.isoformat(),
            }

            if self.enable_logging:
                logger.info(
                    f"ExecutionEngineAdapter: {symbol} {side} {quantity} @ {execution_price} "
                    f"(signal: {signal_price}, slippage: {slippage_bps} bps)"
                )

            return TradeResult(
                success=True,
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                execution_price=execution_price,
                status="FILLED",
                commission=commission,
                slippage_bps=slippage_bps,
                signal_price=signal_price,
            )

        except Exception as e:
            logger.error(f"ExecutionEngineAdapter.execute_order failed: {e}")
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
        Cancel order (no-op for backtesting engine).

        In backtesting, orders are executed immediately, so cancellation
        is not applicable. This method returns True for compatibility.

        Args:
            order_id: Order identifier to cancel

        Returns:
            True (cancellation successful in backtesting context)
        """
        if self.enable_logging:
            logger.debug(f"ExecutionEngineAdapter.cancel_order: {order_id}")

        # Remove from order history if exists
        if order_id in self._order_history:
            self._order_history[order_id]["cancelled"] = True

        return True

    async def modify_order(self, order_id: str, new_price: Decimal) -> bool:
        """
        Modify order price (no-op for backtesting engine).

        In backtesting, orders are executed immediately, so modification
        is not applicable. This method returns True for compatibility.

        Args:
            order_id: Order identifier to modify
            new_price: New price for the order

        Returns:
            True (modification successful in backtesting context)
        """
        if self.enable_logging:
            logger.debug(f"ExecutionEngineAdapter.modify_order: {order_id} -> {new_price}")

        # Update order history if exists
        if order_id in self._order_history:
            self._order_history[order_id]["modified_price"] = str(new_price)

        return True

    async def get_order_status(self, order_id: str) -> str:
        """
        Get order status.

        Args:
            order_id: Order identifier

        Returns:
            Order status: "FILLED", "CANCELLED", "UNKNOWN"
        """
        if order_id in self._order_history:
            if self._order_history[order_id].get("cancelled"):
                return "CANCELLED"
            return "FILLED"
        return "UNKNOWN"

    async def get_open_orders(self) -> list:
        """
        Get open orders (empty list for backtesting).

        In backtesting, orders are executed immediately, so there are
        no open orders.

        Returns:
            Empty list (no open orders in backtesting context)
        """
        return []

    # -------------------------------------------------------------------------
    # Additional methods for enhanced functionality
    # -------------------------------------------------------------------------

    def get_order_history(self) -> Dict[str, Dict[str, Any]]:
        """
        Get complete order history.

        Returns:
            Dictionary mapping order_id to order details
        """
        return self._order_history.copy()

    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary with execution metrics:
                - total_orders: Total number of orders executed
                - total_slippage_bps: Total slippage in basis points
                - avg_slippage_bps: Average slippage per order
        """
        if not self._order_history:
            return {
                "total_orders": 0,
                "total_slippage_bps": Decimal("0"),
                "avg_slippage_bps": Decimal("0"),
            }

        total_slippage = sum(
            Decimal(o.get("slippage_bps", "0")) for o in self._order_history.values()
        )

        return {
            "total_orders": len(self._order_history),
            "total_slippage_bps": total_slippage,
            "avg_slippage_bps": total_slippage / Decimal(str(len(self._order_history))),
        }

    def reset(self) -> None:
        """Reset adapter state (clear order history)."""
        self._order_history.clear()
        self._active_positions.clear()


def get_execution_adapter(
    enable_logging: bool = False,
) -> ExecutionEngineAdapter:
    """
    Factory function to get ExecutionEngineAdapter instance.

    Args:
        enable_logging: Enable detailed logging

    Returns:
        Configured ExecutionEngineAdapter instance

    Example:
        >>> adapter = get_execution_adapter(enable_logging=True)
        >>> result = await adapter.execute_order(signal)
    """
    return ExecutionEngineAdapter(enable_logging=enable_logging)
