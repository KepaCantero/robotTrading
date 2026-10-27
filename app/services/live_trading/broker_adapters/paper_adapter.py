"""
Paper Trading Adapter - Simulates broker for testing/development.

Implements BrokerConnector interface without connecting to a real broker.
Used for:
- Development and testing
- Strategy backtesting
- Paper trading simulations
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    BrokerQuote,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
)

logger = logging.getLogger(__name__)

#: Repo's own EOD history — the default paper price source (last close).
_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "historical"


def csv_last_close_source(symbol: str):
    """Default price source: last close of data/historical/<SYMBOL>.csv.

    Returns (Decimal price, datetime date) or None when the file is
    missing or malformed. A05: paper validates and fills at the last KNOWN
    real price, never an invented constant.
    """
    path = _DATA_DIR / f"{symbol.upper()}.csv"
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 512))
            tail = fh.read().decode("utf-8", errors="ignore").strip().splitlines()
        row = tail[-1].split(",")
        return Decimal(row[4]), datetime.strptime(row[0], "%Y-%m-%d")
    except (OSError, IndexError, ValueError, InvalidOperation):
        return None


class PaperAdapter:
    """Adapter that simulates broker for paper trading."""

    def __init__(
        self,
        initial_cash: Decimal | None = None,
        auto_fill_orders: bool = False,
        allow_shorting: bool = False,
        max_quote_age_days: int = 90,
        quote_stale_warn_days: int = 7,
    ):
        """Initialize paper trading adapter.

        Args:
            initial_cash: Starting cash balance (default €100,000)
            auto_fill_orders: Whether to automatically fill market orders (default False for testing)
            allow_shorting: Whether SELL orders without a held position are
                allowed (default False: reject instead of printing cash)
            max_quote_age_days: quotes older than this are REJECTED
                (abandoned data — never validate or fill on them).
            quote_stale_warn_days: quotes older than this (but within the
                hard limit) are still returned, loudly marked STALE: the
                last known real price is the best paper estimate, and the
                staleness is surfaced, never silent.
        """
        if initial_cash is None:
            initial_cash = Decimal("100000")
        self.account: BrokerAccount | None = None
        self.positions: dict[str, BrokerPosition] = {}
        self.orders: dict[str, BrokerOrder] = {}
        self.is_connected = False
        self.initial_cash = initial_cash
        self.auto_fill_orders = auto_fill_orders
        self.allow_shorting = allow_shorting
        self.max_quote_age_days = max_quote_age_days
        self.quote_stale_warn_days = quote_stale_warn_days
        # A05: injectable price source symbol -> (price, timestamp) | None.
        # Default: last close of the repo's own EOD CSV (see
        # csv_last_close_source); None-source symbols fail closed.
        self._price_source = csv_last_close_source

    def set_price_source(self, source) -> None:
        """Inject a price source: callable(symbol) -> (price, ts) | None."""
        self._price_source = source

    async def get_quote(self, symbol: str) -> BrokerQuote | None:
        """Real, timestamped quote for validation/execution (A05).

        Tiers: fresh (<= quote_stale_warn_days) normal; stale-but-usable
        (<= max_quote_age_days) returned marked STALE with a warning — the
        last known real price, surfaced honestly; older than the hard limit
        or missing/unparseable -> None (fail closed).
        """
        if self._price_source is None:
            return None
        reading = self._price_source(symbol)
        if not reading:
            return None
        price, timestamp = reading
        if not price or not price.is_finite() or price <= 0:
            return None
        age_days = (datetime.utcnow() - timestamp).days
        if age_days > self.max_quote_age_days:
            logger.warning(
                "Quote rejected for %s: %s days old exceeds hard limit %s "
                "(data abandoned — refresh it)",
                symbol,
                age_days,
                self.max_quote_age_days,
            )
            return None
        source = "paper-source"
        if age_days > self.quote_stale_warn_days:
            logger.warning(
                "STALE quote for %s: %s days old (usable, but refresh the data)",
                symbol,
                age_days,
            )
            source = "paper-source-STALE"
        return BrokerQuote(symbol=symbol, price=price, timestamp=timestamp, source=source)

    async def connect(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        account_id: str | None = None,
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
            # EUR: the user's IBKR paper account (DU9811225) is EUR-based;
            # every € the dashboard prints must be the account's own currency.
            currency="EUR",
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
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        client_order_id: str | None = None,
    ) -> str:
        """Place an order in paper trading (simulated).

        SEC-005: Supports client_order_id for idempotency. If an order with
        the same client_order_id already exists, returns the existing order_id
        instead of creating a duplicate.

        Args:
            symbol: Stock symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            order_type: Order type
            price: Limit price if applicable
            stop_price: Stop price if applicable
            client_order_id: Optional client order ID for idempotency

        Returns:
            str: Order ID

        Raises:
            ConnectionError: If not connected to paper trading
            ValueError: If selling more than the held position without shorting enabled
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to paper trading")

        try:
            # Fail-closed: reject SELLs that exceed the held position unless
            # shorting is explicitly enabled. Without this check a SELL with no
            # position just credited cash (inflating the account).
            if side == OrderSide.SELL and not self.allow_shorting:
                held = self.positions[symbol].quantity if symbol in self.positions else Decimal("0")
                if quantity > held:
                    raise ValueError(
                        f"insufficient position: cannot sell {quantity} of {symbol}, held {held}"
                    )

            # SEC-005: Check for duplicate client_order_id
            if client_order_id:
                for existing_order_id, existing_order in self.orders.items():
                    if existing_order.client_order_id == client_order_id:
                        logger.info(
                            "Duplicate order detected - returning existing order",
                            extra={
                                "existing_order_id": existing_order_id,
                                "client_order_id": client_order_id,
                            },
                        )
                        return existing_order_id

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
                client_order_id=client_order_id,  # SEC-005: Store client_order_id
            )

            # Cache order
            self.orders[order_id] = order

            # Simulate immediate execution for market orders if auto_fill is enabled
            if self.auto_fill_orders and order_type == OrderType.MARKET:
                # A05: fill at the order price or a REAL quote — the old
                # `price or Decimal("100")` invented money-moving prices.
                execution_price = price
                if execution_price is None:
                    quote = await self.get_quote(symbol)
                    execution_price = quote.price if quote else None
                if execution_price is None:
                    order.status = OrderStatus.REJECTED
                    order.error_message = "No valid quote available for paper fill"
                    order.updated_at = datetime.utcnow()
                    logger.error("Paper MARKET fill rejected: no valid quote for %s", symbol)
                    raise ValueError(
                        f"No valid quote to fill {symbol} MARKET order (stale or missing)"
                    )
                order.price = execution_price
                order.status = OrderStatus.FILLED
                order.filled_quantity = quantity
                order.updated_at = datetime.utcnow()
                order.executed_at = datetime.utcnow()

                # Update positions
                self._update_position(symbol, side, quantity, execution_price)

            logger.info(f"✅ Paper order placed: {symbol} {side.value} {quantity}")

            return order_id

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"❌ Paper order placement failed: {e!s}")
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

    async def get_account_info(self) -> BrokerAccount | None:
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

    async def get_positions(self) -> list[BrokerPosition]:
        """Get all open positions in paper trading.

        Returns:
            list: List of BrokerPosition objects
        """
        return list(self.positions.values())

    async def get_position(self, symbol: str) -> BrokerPosition | None:
        """Get a specific position in paper trading.

        Args:
            symbol: Stock symbol

        Returns:
            BrokerPosition: Position info or None if not found
        """
        return self.positions.get(symbol)

    async def update_positions(self) -> dict[str, BrokerPosition]:
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

    async def calculate_portfolio_value(self) -> Decimal | None:
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
                    # A10: a full close STILL credits the sale proceeds —
                    # returning before the cash update destroyed the money
                    # (buy@100 + sell@100 left the account 100 poorer).
                    if self.account:
                        self.account.cash_available += quantity * price
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
