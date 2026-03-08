"""
Order Manager Adapter for Task 11 - Order Manager Integration

This adapter bridges OrderManager with the ITradeExecutor protocol used by
ComplianceEngine, enabling live trading order management in the system.

Purpose: Integrate OrderManager with ComplianceEngine for live trading.
Connects order lifecycle management (placement, tracking, cancellation) with
the compliance coordinator layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.services.live_trading.broker_connector import OrderSide, OrderStatus
from app.services.live_trading.order_manager import OrderManager, get_order_manager
from app.shared.protocols import ITradeExecutor

logger = logging.getLogger(__name__)


class OrderManagerAdapter(ITradeExecutor):
    """
    Adapter that implements ITradeExecutor using OrderManager.

    This adapter connects the OrderManager (live trading order lifecycle management)
    with the coordinator layer (ComplianceEngine), providing:

    1. Order placement with risk gates validation
    2. Order cancellation and modification
    3. Order status tracking
    4. Pending orders retrieval
    5. Integration with broker connectors

    Integration Points:
    - OrderManager: Provides live trading order lifecycle management
    - ComplianceEngine: Uses ITradeExecutor for trade execution
    - BrokerConnector: Delegates actual broker operations
    - RiskGates: Pre-trade risk validation
    """

    def __init__(
        self,
        order_manager: Optional[OrderManager] = None,
        enable_logging: bool = False,
    ):
        """
        Initialize OrderManagerAdapter.

        Args:
            order_manager: Optional OrderManager instance
                          (defaults to singleton instance)
            enable_logging: Enable detailed logging for order operations
        """
        self.order_manager = order_manager  # Don't create here to avoid circular deps
        self.enable_logging = enable_logging
        self._signal_to_order_map: Dict[str, str] = {}  # signal_id -> order_id

    def _get_manager(self) -> OrderManager:
        """Get OrderManager instance (lazy initialization)."""
        if self.order_manager is None:
            self.order_manager = get_order_manager()
        return self.order_manager

    async def execute_order(
        self,
        signal: "TradeSignal",
    ) -> "TradeResult":
        """
        Execute order using OrderManager with risk gates validation.

        This method implements the ITradeExecutor protocol by:

        1. Placing order via OrderManager with risk validation
        2. Converting TradeSignal to OrderManager parameters
        3. Tracking order status and mapping
        4. Returning TradeResult with execution details

        Args:
            signal: TradeSignal containing:
                - symbol: Trading symbol
                - order_side: BUY or SELL
                - quantity: Order quantity
                - price: Signal price (optional for market orders)
                - order_type: MARKET or LIMIT
                - stop_loss: Optional stop loss price
                - take_profit: Optional take profit price
                - signal_id: Unique signal identifier

        Returns:
            TradeResult with execution details including:
                - order_id: Unique order identifier
                - symbol: Trading symbol
                - side: Order side
                - quantity: Order quantity
                - execution_price: Execution price (if filled)
                - status: Order status
                - error: Error message if failed

        Example:
            >>> signal = TradeSignal(
            ...     symbol="AAPL",
            ...     order_side=OrderSide.BUY,
            ...     quantity=Decimal("100"),
            ...     price=Decimal("150"),
            ...     signal_id="signal_123",
            ... )
            >>> result = await adapter.execute_order(signal)
            >>> assert result.success or result.error
        """

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
            manager = self._get_manager()

            # Extract signal data
            symbol = signal.symbol
            side = signal.order_side
            quantity = signal.quantity
            signal_price = signal.price or Decimal("0")
            signal_id = getattr(signal, "signal_id", f"signal_{datetime.now().timestamp()}")

            # Determine order type
            order_type = signal.order_type

            # Calculate stop and limit prices
            limit_price = signal.price
            stop_price = signal.stop_loss

            if self.enable_logging:
                logger.info(
                    f"OrderManagerAdapter: Placing {side.value} order for {quantity} {symbol} "
                    f"@ {limit_price} (signal: {signal_id})"
                )

            # Place order via OrderManager (includes risk gates validation)
            broker_order = await manager.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=limit_price,
                stop_price=stop_price,
                timeout_seconds=60,
            )

            if broker_order is None:
                # Order rejected by risk gates or placement failed
                error_msg = f"Order placement failed for {symbol} (rejected by risk gates)"
                if self.enable_logging:
                    logger.warning(f"OrderManagerAdapter: {error_msg}")

                return TradeResult(
                    success=False,
                    order_id="",
                    symbol=symbol,
                    side=side.value,
                    quantity=quantity,
                    execution_price=Decimal("0"),
                    status="REJECTED",
                    commission=Decimal("0"),
                    slippage_bps=Decimal("0"),
                    signal_price=signal_price,
                    error=error_msg,
                )

            # Map signal to order for tracking
            self._signal_to_order_map[signal_id] = broker_order.order_id

            # Get execution details
            execution_price = broker_order.avg_filled_price or (limit_price or Decimal("0"))

            # Calculate commission (simplified - would come from broker)
            commission = Decimal("1")  # Default commission

            # Calculate slippage (simplified)
            slippage_bps = Decimal("0")
            if signal_price > 0 and execution_price > 0:
                if side == OrderSide.BUY:
                    slippage_bps = ((execution_price - signal_price) / signal_price) * Decimal(
                        "10000"
                    )
                else:
                    slippage_bps = ((signal_price - execution_price) / signal_price) * Decimal(
                        "10000"
                    )

            # Map OrderStatus to string status
            status_map = {
                OrderStatus.FILLED: "FILLED",
                OrderStatus.PARTIALLY_FILLED: "PARTIALLY_FILLED",
                OrderStatus.PENDING: "PENDING",
                OrderStatus.SUBMITTED: "SUBMITTED",
                OrderStatus.REJECTED: "REJECTED",
                OrderStatus.CANCELED: "CANCELED",
            }
            status = status_map.get(broker_order.status, str(broker_order.status.value))

            if self.enable_logging:
                logger.info(
                    f"OrderManagerAdapter: Order {broker_order.order_id} {status} - "
                    f"{symbol} {side.value} {quantity} @ {execution_price}"
                )

            return TradeResult(
                success=broker_order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED),
                order_id=broker_order.order_id,
                symbol=symbol,
                side=side.value,
                quantity=broker_order.filled_quantity or quantity,
                execution_price=execution_price,
                status=status,
                commission=commission,
                slippage_bps=slippage_bps,
                signal_price=signal_price,
            )

        except Exception as e:
            logger.error(f"OrderManagerAdapter.execute_order failed: {e}")
            return TradeResult(
                success=False,
                order_id="",
                symbol=getattr(signal, "symbol", "UNKNOWN"),
                side=getattr(signal, "order_side", OrderSide.BUY).value,
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
        Cancel order via OrderManager.

        Args:
            order_id: Order identifier to cancel

        Returns:
            True if cancellation successful, False otherwise
        """
        try:
            manager = self._get_manager()

            if self.enable_logging:
                logger.info(f"OrderManagerAdapter: Cancelling order {order_id}")

            result = await manager.cancel_order(order_id)

            # Clean up mapping
            for signal_id, oid in list(self._signal_to_order_map.items()):
                if oid == order_id:
                    del self._signal_to_order_map[signal_id]

            if self.enable_logging:
                logger.info(f"OrderManagerAdapter: Cancel result for {order_id}: {result}")

            return result

        except Exception as e:
            logger.error(f"OrderManagerAdapter.cancel_order failed for {order_id}: {e}")
            return False

    async def modify_order(self, order_id: str, new_price: Decimal) -> bool:
        """
        Modify order price.

        Note: OrderManager doesn't have a native modify method, so we implement
        cancel + replace pattern.

        Args:
            order_id: Order identifier to modify
            new_price: New price for the order

        Returns:
            True if modification successful, False otherwise
        """
        try:
            manager = self._get_manager()

            if self.enable_logging:
                logger.info(f"OrderManagerAdapter: Modifying order {order_id} -> {new_price}")

            # OrderManager doesn't have native modify, so we use cancel + replace
            # First, check if order exists in pending
            pending_orders = await manager.get_pending_orders()
            target_order = None

            for order in pending_orders:
                if order.order_id == order_id:
                    target_order = order
                    break

            if target_order is None:
                logger.warning(
                    f"OrderManagerAdapter: Cannot modify - order {order_id} not found in pending"
                )
                return False

            # Cancel original order
            cancel_result = await manager.cancel_order(order_id)

            if not cancel_result:
                logger.warning(
                    f"OrderManagerAdapter: Failed to cancel order {order_id} for modification"
                )
                return False

            # Place new order with updated price
            new_order = await manager.place_order(
                symbol=target_order.symbol,
                side=target_order.side,
                quantity=target_order.quantity,
                order_type=target_order.order_type,
                price=new_price,
                stop_price=target_order.stop_price,
            )

            if self.enable_logging:
                if new_order:
                    logger.info(
                        f"OrderManagerAdapter: Order modified {order_id} -> {new_order.order_id}"
                    )
                else:
                    logger.warning("OrderManagerAdapter: Failed to place replacement order")

            return new_order is not None

        except Exception as e:
            logger.error(f"OrderManagerAdapter.modify_order failed for {order_id}: {e}")
            return False

    async def get_order_status(self, order_id: str) -> str:
        """
        Get order status.

        Args:
            order_id: Order identifier

        Returns:
            Order status: "FILLED", "PENDING", "CANCELLED", "UNKNOWN"
        """
        try:
            manager = self._get_manager()

            status = await manager.get_order_status(order_id)

            if status is None:
                return "UNKNOWN"

            # Map OrderStatus enum to string
            status_map = {
                OrderStatus.FILLED: "FILLED",
                OrderStatus.PARTIALLY_FILLED: "PARTIALLY_FILLED",
                OrderStatus.PENDING: "PENDING",
                OrderStatus.SUBMITTED: "SUBMITTED",
                OrderStatus.CANCELED: "CANCELED",
                OrderStatus.REJECTED: "REJECTED",
            }

            return status_map.get(status, str(status.value))

        except Exception as e:
            logger.error(f"OrderManagerAdapter.get_order_status failed for {order_id}: {e}")
            return "UNKNOWN"

    async def get_open_orders(self) -> List["TradeSignal"]:
        """
        Get open orders.

        Returns:
            List of TradeSignal objects representing open orders
        """
        try:
            manager = self._get_manager()

            # Get pending orders from OrderManager
            pending_orders = await manager.get_pending_orders()

            # Convert BrokerOrder to TradeSignal-like objects
            # Note: Returning TradeSignal objects for compatibility with protocol
            from app.services.live_trading.alert_to_trade_mapper import TradeSignal, TradeSignalType

            open_orders = []
            for order in pending_orders:
                signal = TradeSignal(
                    signal_id=f"order_{order.order_id}",
                    alert_id="",
                    alert_rule_id="",
                    symbol=order.symbol,
                    signal_type=TradeSignalType.LONG,  # Default
                    order_side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    price=order.price,
                )
                open_orders.append(signal)

            if self.enable_logging:
                logger.info(f"OrderManagerAdapter: {len(open_orders)} open orders")

            return open_orders

        except Exception as e:
            logger.error(f"OrderManagerAdapter.get_open_orders failed: {e}")
            return []

    # -------------------------------------------------------------------------
    # Additional methods for enhanced functionality
    # -------------------------------------------------------------------------

    def get_order_id_for_signal(self, signal_id: str) -> Optional[str]:
        """
        Get order ID for a given signal ID.

        Args:
            signal_id: Signal identifier

        Returns:
            Order ID or None if not found
        """
        return self._signal_to_order_map.get(signal_id)

    async def cancel_all_orders(self) -> int:
        """
        Cancel all pending orders.

        Returns:
            Number of orders cancelled
        """
        try:
            manager = self._get_manager()
            count = await manager.cancel_all_orders()

            # Clear all mappings
            self._signal_to_order_map.clear()

            if self.enable_logging:
                logger.info(f"OrderManagerAdapter: Cancelled {count} orders")

            return count

        except Exception as e:
            logger.error(f"OrderManagerAdapter.cancel_all_orders failed: {e}")
            return 0

    def get_mapping_stats(self) -> Dict[str, Any]:
        """
        Get signal-to-order mapping statistics.

        Returns:
            Dictionary with mapping statistics
        """
        return {
            "total_mappings": len(self._signal_to_order_map),
            "mappings": self._signal_to_order_map.copy(),
        }

    def reset(self) -> None:
        """Reset adapter state (clear signal-to-order mappings)."""
        self._signal_to_order_map.clear()


def get_order_manager_adapter(
    enable_logging: bool = False,
) -> OrderManagerAdapter:
    """
    Factory function to get OrderManagerAdapter instance.

    Args:
        enable_logging: Enable detailed logging

    Returns:
        Configured OrderManagerAdapter instance

    Example:
        >>> adapter = get_order_manager_adapter(enable_logging=True)
        >>> result = await adapter.execute_order(signal)
    """
    return OrderManagerAdapter(enable_logging=enable_logging)
