"""
Paper Trading Adapter - Simulates broker for testing/development.

Implements BrokerConnector interface without connecting to a real broker.
Used for:
- Development and testing
- Strategy backtesting
- Paper trading simulations
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import uuid4

from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
)

logger = logging.getLogger(__name__)


class PaperAdapter:
    """Adapter that simulates broker for paper trading."""

    def __init__(self, initial_cash: Decimal = Decimal("100000"), auto_fill_orders: bool = False):
        """Initialize paper trading adapter.

        Args:
            initial_cash: Starting cash balance (default $100,000)
            auto_fill_orders: Whether to automatically fill market orders (default False for testing)
        """
        self.account: Optional[BrokerAccount] = None
        self.positions: Dict[str, BrokerPosition] = {}
        self.orders: Dict[str, BrokerOrder] = {}
        self.is_connected = False
        self.initial_cash = initial_cash
        self.auto_fill_orders = auto_fill_orders

    async def connect(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Connect to paper trading (simulated).

        Args:
            api_key: Ignored for paper trading
            api_secret: Ignored for paper trading
            account_id: Optional account ID
            **kwargs: Additional arguments (ignored)

        Returns:
            bool: Always True for paper trading
        """
        self.account = BrokerAccount(
            account_id=account_id or f"paper_{uuid4().hex[:8]}",
            broker_type=BrokerType.PAPER,
            currency="USD",
            cash_available=self.initial_cash,
            portfolio_value=self.initial_cash,
            buying_power=self.initial_cash,
            equity=self.initial_cash,
            margin_used=Decimal("0"),
            multiplier=Decimal("1"),
            connected=True,  # Set connected to True
        )

        self.is_connected = True
        logger.info(f"✅ Paper trading connected (Account: {self.account.account_id})")

        return True

    async def disconnect(self) -> bool:
        """Disconnect from paper trading.

        Returns:
            bool: Always True
        """
        self.is_connected = False
        logger.info("✅ Paper trading disconnected")
        return True

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
    ) -> str:
        """Place an order in paper trading (simulated).

        Args:
            symbol: Stock symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            order_type: Order type
            price: Limit price if applicable
            stop_price: Stop price if applicable

        Returns:
            str: Order ID

        Raises:
            Exception: If order placement fails
        """
        if not self.is_connected:
            raise Exception("Not connected to paper trading")

        try:
            order_id = str(uuid4())

            # Create order
            order = BrokerOrder(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                status=OrderStatus.SUBMITTED,
                created_at=datetime.utcnow(),
            )

            # Cache order
            self.orders[order_id] = order

            # Simulate immediate execution for market orders if auto_fill is enabled
            if self.auto_fill_orders and order_type == OrderType.MARKET:
                order.status = OrderStatus.FILLED
                order.filled_quantity = quantity
                order.updated_at = datetime.utcnow()
                order.executed_at = datetime.utcnow()

                # Update positions
                self._update_position(symbol, side, quantity, price or Decimal("100"))

            logger.info(f"✅ Paper order placed: {symbol} {side.value} {quantity}")

            return order_id

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"❌ Paper order placement failed: {str(e)}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order in paper trading.

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if cancellation successful
        """
        if order_id in self.orders:
            order = self.orders[order_id]

            # Can only cancel non-filled orders
            if order.status not in (OrderStatus.FILLED, OrderStatus.CANCELED):
                order.status = OrderStatus.CANCELED
                order.updated_at = datetime.utcnow()
                logger.info(f"✅ Paper order {order_id} cancelled")
                return True

        logger.warning(f"⚠️  Cannot cancel order {order_id}")
        return False

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get order status in paper trading.

        Args:
            order_id: Order ID to query

        Returns:
            OrderStatus: Current order status
        """
        if order_id in self.orders:
            return self.orders[order_id].status

        return OrderStatus.PENDING

    async def get_account_info(self) -> Optional[BrokerAccount]:
        """Get account information from paper trading.

        Returns:
            BrokerAccount: Account information or None
        """
        if not self.account:
            return None

        # Recalculate portfolio value
        positions_value = sum(pos.market_value for pos in self.positions.values())
        self.account.portfolio_value = self.account.cash_available + positions_value

        return self.account

    async def get_positions(self) -> List[BrokerPosition]:
        """Get all open positions in paper trading.

        Returns:
            list: List of BrokerPosition objects
        """
        return list(self.positions.values())

    async def get_position(self, symbol: str) -> Optional[BrokerPosition]:
        """Get a specific position in paper trading.

        Args:
            symbol: Stock symbol

        Returns:
            BrokerPosition: Position info or None if not found
        """
        return self.positions.get(symbol)

    async def update_positions(self) -> Dict[str, BrokerPosition]:
        """Update all positions (alias for get_positions).

        Returns:
            dict: Dictionary of symbol -> BrokerPosition
        """
        return {pos.symbol: pos for pos in await self.get_positions()}

    async def sync_account_balance(self) -> bool:
        """Synchronize account balance (no-op for paper trading).

        Returns:
            bool: Always True
        """
        return True

    async def calculate_portfolio_value(self) -> Optional[Decimal]:
        """Calculate current portfolio value.

        Returns:
            Decimal: Portfolio value or None
        """
        account = await self.get_account_info()
        return account.portfolio_value if account else None

    # ==================== Helper Methods ====================

    def _update_position(
        self, symbol: str, side: OrderSide, quantity: Decimal, price: Decimal
    ) -> None:
        """Update position after order execution.

        Args:
            symbol: Stock symbol
            side: Order side
            quantity: Order quantity
            price: Execution price
        """
        if symbol not in self.positions:
            # Create new position
            if side == OrderSide.BUY:
                self.positions[symbol] = BrokerPosition(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=price,
                    current_price=price,
                    market_value=quantity * price,
                    unrealized_pl=Decimal("0"),
                    unrealized_pl_pct=Decimal("0"),
                )
        else:
            # Update existing position
            pos = self.positions[symbol]

            if side == OrderSide.BUY:
                # Add to position
                total_qty = pos.quantity + quantity
                new_avg_price = (pos.avg_price * pos.quantity + price * quantity) / total_qty
                pos.quantity = total_qty
                pos.avg_price = new_avg_price
            else:  # SELL
                # Reduce position
                pos.quantity = max(Decimal("0"), pos.quantity - quantity)
                if pos.quantity == 0:
                    del self.positions[symbol]
                    return

            # Update market values
            pos.market_value = pos.quantity * pos.current_price
            pos.unrealized_pl = (pos.current_price - pos.avg_price) * pos.quantity

            if pos.market_value != 0:
                pos.unrealized_pl_pct = (pos.unrealized_pl / pos.market_value) * Decimal("100")

        # Update account balance
        if self.account:
            cost = quantity * price
            if side == OrderSide.BUY:
                self.account.cash_available -= cost
            else:
                self.account.cash_available += cost

    # ==================== Status Methods ====================

    def is_paper_trading(self) -> bool:
        """Check if using paper trading mode.

        Returns:
            bool: Always True
        """
        return True

    def get_broker_type(self) -> BrokerType:
        """Get broker type.

        Returns:
            BrokerType: Paper broker type
        """
        return BrokerType.PAPER

    def __repr__(self) -> str:
        """String representation."""
        status = "🟢 Connected" if self.is_connected else "🔴 Disconnected"
        return f"PaperAdapter({status})"
