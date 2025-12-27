"""
T16.1.2: OrderManager - Order lifecycle management

Manages order placement, execution tracking, cancellation, and error handling.
Integrates with BrokerConnector for actual order operations.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import Depends

from .broker_connector import (
    BrokerConnector,
    BrokerOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    get_broker_connector,
)

logger = logging.getLogger(__name__)


@dataclass
class OrderExecution:
    """Record of order execution."""

    order_id: str
    symbol: str
    quantity: Decimal
    price: Decimal
    execution_time: datetime = field(default_factory=datetime.now)
    fees: Decimal = Decimal("0")
    net_proceeds: Decimal = Decimal("0")


@dataclass
class OrderError:
    """Order error information."""

    order_id: str
    symbol: str
    error_code: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3


class OrderManager:
    """
    Manages order lifecycle from placement to execution.

    Features:
    - Order placement and tracking
    - Execution monitoring
    - Cancellation handling
    - Order history
    - Error tracking and recovery
    - Order status polling
    """

    def __init__(self, broker: Optional[BrokerConnector] = None):
        """Initialize order manager."""
        self.broker = broker or get_broker_connector()
        self.pending_orders: Dict[str, BrokerOrder] = {}
        self.executed_orders: Dict[str, BrokerOrder] = {}
        self.order_history: List[BrokerOrder] = []
        self.order_errors: Dict[str, OrderError] = {}
        self.executions: List[OrderExecution] = []
        logger.info("✅ OrderManager initialized")

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        timeout_seconds: int = 60,
    ) -> Optional[BrokerOrder]:
        """
        Place order with broker.

        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Number of shares
            order_type: Type of order
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            timeout_seconds: Timeout for order placement

        Returns:
            BrokerOrder if successful
        """
        try:
            order = await self.broker.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                stop_price=stop_price,
            )

            if order:
                self.pending_orders[order.order_id] = order
                self.order_history.append(order)
                logger.info(f"✅ Order placed: {order.order_id} - {side.value} {quantity} {symbol}")
                return order
            else:
                logger.error(f"❌ Order placement failed for {symbol}")
                return None

        except Exception as e:
            logger.error(f"❌ Error placing order: {str(e)}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if canceled successfully
        """
        if order_id not in self.pending_orders:
            logger.warning(f"⚠️ Order not found in pending: {order_id}")
            return False

        try:
            success = await self.broker.cancel_order(order_id)
            if success:
                order = self.pending_orders.pop(order_id)
                order.status = OrderStatus.CANCELED
                order.updated_at = datetime.now()
                self.order_history.append(order)
                logger.info(f"✅ Order canceled: {order_id}")
            return success
        except Exception as e:
            logger.error(f"❌ Error canceling order: {str(e)}")
            return False

    async def cancel_all_orders(self) -> int:
        """
        Cancel all pending orders.

        Returns:
            Number of orders canceled
        """
        canceled_count = 0
        order_ids = list(self.pending_orders.keys())

        for order_id in order_ids:
            if await self.cancel_order(order_id):
                canceled_count += 1

        logger.info(f"✅ Canceled {canceled_count} orders")
        return canceled_count

    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Get current order status.

        Args:
            order_id: Order ID

        Returns:
            OrderStatus or None
        """
        # Check pending orders first
        if order_id in self.pending_orders:
            return self.pending_orders[order_id].status

        # Check executed orders
        if order_id in self.executed_orders:
            return self.executed_orders[order_id].status

        # Query broker
        return await self.broker.get_order_status(order_id)

    async def poll_order_status(self, order_id: str, max_polls: int = 60) -> Optional[BrokerOrder]:
        """
        Poll order status until execution or timeout.

        Args:
            order_id: Order ID to poll
            max_polls: Maximum number of polls

        Returns:
            Final BrokerOrder or None
        """
        for poll_count in range(max_polls):
            order = self.pending_orders.get(order_id)
            if not order:
                logger.warning(f"⚠️ Order not found: {order_id}")
                return None

            status = await self.get_order_status(order_id)
            if status in (
                OrderStatus.FILLED,
                OrderStatus.EXECUTED,
                OrderStatus.CANCELED,
                OrderStatus.REJECTED,
            ):
                # Move to executed
                self.pending_orders.pop(order_id, None)
                self.executed_orders[order_id] = order
                logger.info(f"✅ Order {order_id} reached terminal status: {status.value}")
                return order

            # Wait before next poll (exponential backoff would be better)
            if poll_count < max_polls - 1:
                await asyncio.sleep(1)

        logger.warning(f"⚠️ Order polling timeout for {order_id}")
        return None

    async def record_execution(
        self,
        order_id: str,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal = Decimal("0"),
    ) -> Optional[OrderExecution]:
        """
        Record order execution.

        Args:
            order_id: Order ID
            symbol: Stock symbol
            quantity: Executed quantity
            price: Execution price
            fees: Transaction fees

        Returns:
            OrderExecution record
        """
        net_proceeds = quantity * price - fees

        execution = OrderExecution(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            price=price,
            fees=fees,
            net_proceeds=net_proceeds,
        )

        self.executions.append(execution)
        logger.info(f"✅ Recorded execution: {order_id} - {quantity} {symbol} @ {price}")
        return execution

    async def get_pending_orders(self, symbol: Optional[str] = None) -> List[BrokerOrder]:
        """
        Get pending orders.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of pending BrokerOrder objects
        """
        orders = list(self.pending_orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def get_executed_orders(self, symbol: Optional[str] = None) -> List[BrokerOrder]:
        """
        Get executed orders.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of executed BrokerOrder objects
        """
        orders = list(self.executed_orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def get_order_history(self, symbol: Optional[str] = None) -> List[BrokerOrder]:
        """
        Get complete order history.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of all BrokerOrder objects
        """
        orders = self.order_history
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def get_execution_history(
        self,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[OrderExecution]:
        """
        Get execution history.

        Args:
            symbol: Filter by symbol
            since: Filter by date

        Returns:
            List of OrderExecution records
        """
        executions = self.executions

        if symbol:
            executions = [e for e in executions if e.symbol == symbol]

        if since:
            executions = [e for e in executions if e.execution_time >= since]

        return executions

    async def record_error(
        self,
        order_id: str,
        symbol: str,
        error_code: str,
        error_message: str,
    ) -> OrderError:
        """
        Record order error.

        Args:
            order_id: Order ID
            symbol: Stock symbol
            error_code: Error code
            error_message: Error message

        Returns:
            OrderError record
        """
        error = OrderError(
            order_id=order_id,
            symbol=symbol,
            error_code=error_code,
            error_message=error_message,
        )

        self.order_errors[order_id] = error
        logger.warning(f"⚠️ Order error {error_code}: {error_message}")
        return error

    async def get_order_errors(self, symbol: Optional[str] = None) -> List[OrderError]:
        """
        Get recorded order errors.

        Args:
            symbol: Filter by symbol

        Returns:
            List of OrderError records
        """
        errors = list(self.order_errors.values())
        if symbol:
            errors = [e for e in errors if e.symbol == symbol]
        return errors

    def get_total_executions(self) -> int:
        """Get total number of executions."""
        return len(self.executions)

    def get_pending_count(self) -> int:
        """Get number of pending orders."""
        return len(self.pending_orders)

    def get_executed_count(self) -> int:
        """Get number of executed orders."""
        return len(self.executed_orders)


# Import asyncio at module level for poll_order_status
import asyncio

# Singleton
_manager: Optional[OrderManager] = None


def get_order_manager(
    broker: BrokerConnector = Depends(get_broker_connector),
) -> OrderManager:
    """Get or create singleton OrderManager."""
    global _manager
    if _manager is None:

    return _manager
