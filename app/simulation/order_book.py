"""
Order Book Simulation - Larry Harris's Limit Order Book Dynamics

This module implements the limit order book simulation as described in Harris,
Chapter 3: "Orders and Order Properties" and Chapter 4: "Market Structure."

Key concepts implemented:
1. Limit order book with price-time priority
2. Order queue simulation at each price level
3. Price formation through order interaction
4. Depth and liquidity metrics
5. Order book dynamics and evolution

Reference:
    Harris, L. (2003). Trading and Exchanges, Chapters 3-4.
"""
# mypy: ignore-errors
# pylint: disable=unsupported-binary-operation  # For Python 3.10+ union syntax

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple  # noqa: F401
import numpy as np

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Side of an order in the order book."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Type of order."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    ICEBERG = "ICEBERG"


class OrderStatus(Enum):
    """Status of an order."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    """
    An order in the limit order book.

    Attributes:
        order_id: Unique identifier for the order
        symbol: Trading symbol
        side: Buy or sell
        order_type: Market, limit, stop, etc.
        quantity: Order quantity
        price: Limit price (None for market orders)
        stop_price: Stop price (for stop orders)
        status: Current order status
        filled_quantity: Quantity that has been filled
        remaining_quantity: Quantity remaining to be filled
        avg_fill_price: Average price of fills
        created_at: Order creation timestamp
        updated_at: Last update timestamp
        client_id: Optional client identifier
        time_in_force: TIF instruction (GTC, IOC, FOK, etc.)
        display_quantity: For iceberg orders, visible quantity
        hidden_quantity: For iceberg orders, hidden quantity
    """

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    client_id: Optional[str] = None
    time_in_force: str = "GTC"
    display_quantity: Optional[Decimal] = None
    hidden_quantity: Optional[Decimal] = None

    @property
    def remaining_quantity(self) -> Decimal:
        """Get quantity remaining to be filled."""
        return self.quantity - self.filled_quantity

    def fill(self, quantity: Decimal, price: Decimal) -> None:
        """
        Fill the order with given quantity at given price.

        Args:
            quantity: Quantity to fill
            price: Fill price
        """
        if quantity > self.remaining_quantity:
            raise ValueError(
                f"Fill quantity {quantity} exceeds remaining {self.remaining_quantity}"
            )

        # Update fill information
        new_filled_qty = self.filled_quantity + quantity
        object.__setattr__(self, 'filled_quantity', new_filled_qty)

        # Update average fill price
        if self.avg_fill_price is None:
            object.__setattr__(self, 'avg_fill_price', price)
        else:
            total_value = self.avg_fill_price * (new_filled_qty - quantity) + price * quantity
            object.__setattr__(self, 'avg_fill_price', total_value / new_filled_qty)

        # Update status
        if self.remaining_quantity == 0:
            object.__setattr__(self, 'status', OrderStatus.FILLED)
        elif self.filled_quantity > 0:
            object.__setattr__(self, 'status', OrderStatus.PARTIALLY_FILLED)

        object.__setattr__(self, 'updated_at', datetime.utcnow())

    def cancel(self) -> None:
        """Cancel the order."""
        if self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel order with status {self.status}")
        object.__setattr__(self, 'status', OrderStatus.CANCELLED)
        object.__setattr__(self, 'updated_at', datetime.utcnow())

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy order."""
        return self.side == OrderSide.BUY

    @property
    def is_sell(self) -> bool:
        """Check if this is a sell order."""
        return self.side == OrderSide.SELL

    @property
    def is_active(self) -> bool:
        """Check if order is active in the book."""
        return self.status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]

    @property
    def is_marketable(self) -> bool:
        """Check if order can be immediately executed against existing book."""
        return self.order_type == OrderType.MARKET


@dataclass
class PriceLevel:
    """
    A price level in the order book containing multiple orders.

    Implements price-time priority: orders are matched FIFO within each price level.

    Attributes:
        price: Price level
        orders: Queue of orders at this price (FIFO)
        total_quantity: Total quantity at this price level
    """

    price: Decimal
    orders: deque = field(default_factory=deque)
    total_quantity: Decimal = Decimal("0")

    def add_order(self, order: Order) -> None:
        """
        Add an order to this price level.

        Args:
            order: Order to add
        """
        if order.price != self.price:
            raise ValueError(f"Order price {order.price} doesn't match level {self.price}")
        self.orders.append(order)
        object.__setattr__(self, 'total_quantity', self.total_quantity + order.remaining_quantity)

    def remove_order(self, order_id: str) -> Optional[Order]:
        """
        Remove an order from this price level.

        Args:
            order_id: ID of order to remove

        Returns:
            The removed order, or None if not found
        """
        for i, order in enumerate(self.orders):
            if order.order_id == order_id:
                # Convert deque to list, remove, then back to deque
                orders_list = list(self.orders)
                removed = orders_list.pop(i)
                object.__setattr__(self, 'orders', deque(orders_list))
                object.__setattr__(
                    self, 'total_quantity', self.total_quantity - removed.remaining_quantity
                )
                return removed
        return None

    def get_quantity(self) -> Decimal:
        """Get total quantity at this price level."""
        return self.total_quantity

    def get_order_count(self) -> int:
        """Get number of orders at this price level."""
        return len(self.orders)

    def is_empty(self) -> bool:
        """Check if price level is empty."""
        return len(self.orders) == 0


@dataclass
class Trade:
    """
    A trade that occurred from order matching.

    Attributes:
        trade_id: Unique trade identifier
        symbol: Trading symbol
        buy_order_id: Buy order ID
        sell_order_id: Sell order ID
        price: Trade price
        quantity: Trade quantity
        timestamp: Trade timestamp
        is_buy_aggressor: True if buy order was aggressor
    """

    trade_id: str
    symbol: str
    buy_order_id: str
    sell_order_id: str
    price: Decimal
    quantity: Decimal
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_buy_aggressor: bool = True


@dataclass
class OrderBookSnapshot:
    """
    Snapshot of the order book state.

    Attributes:
        symbol: Trading symbol
        timestamp: Snapshot timestamp
        bids: List of (price, quantity) tuples for bids
        asks: List of (price, quantity) tuples for asks
        best_bid: Best bid price
        best_ask: Best ask price
        spread: Bid-ask spread
        mid_price: Mid price
        total_bid_quantity: Total quantity on bid side
        total_ask_quantity: Total quantity on ask side
        bid_depth: Number of bid levels
        ask_depth: Number of ask levels
    """

    symbol: str
    timestamp: datetime
    bids: List[Tuple[Decimal, Decimal]]
    asks: List[Tuple[Decimal, Decimal]]
    best_bid: Optional[Decimal]
    best_ask: Optional[Decimal]
    spread: Optional[Decimal]
    mid_price: Optional[Decimal]
    total_bid_quantity: Decimal
    total_ask_quantity: Decimal
    bid_depth: int
    ask_depth: int

    @property
    def is_empty(self) -> bool:
        """Check if order book is empty."""
        return self.bid_depth == 0 and self.ask_depth == 0


class LimitOrderBook:
    """
    Limit Order Book (LOB) simulation.

    Implements Harris's model of order book dynamics with:
    - Price-time priority (FIFO at each price level)
    - Bid and ask sides
    - Instantaneous matching of marketable orders
    - Depth tracking and liquidity metrics

    The LOB is the fundamental data structure in continuous double auction markets,
    as described in Harris Chapter 4.

    Attributes:
        symbol: Trading symbol
        tick_size: Minimum price increment
        max_depth: Maximum depth to track
        bids: Buy side (bid) price levels sorted descending
        asks: Sell side (ask) price levels sorted ascending
        trades: List of executed trades
    """

    def __init__(
        self,
        symbol: str,
        tick_size: Decimal = Decimal("0.01"),
        max_depth: int = 100,
    ):
        """
        Initialize the limit order book.

        Args:
            symbol: Trading symbol
            tick_size: Minimum price increment
            max_depth: Maximum number of price levels to track
        """
        self.symbol = symbol
        self.tick_size = tick_size
        self.max_depth = max_depth

        # Price levels: price -> PriceLevel
        self._bids: Dict[Decimal, PriceLevel] = {}
        self._asks: Dict[Decimal, PriceLevel] = {}

        # Sorted price lists for efficient iteration
        self._bid_prices: List[Decimal] = []
        self._ask_prices: List[Decimal] = []

        # Orders: order_id -> Order
        self._orders: Dict[str, Order] = {}

        # Trade history
        self._trades: List[Trade] = []

        logger.info(f"Initialized LimitOrderBook for {symbol} with tick_size={tick_size}")

    @property
    def bids(self) -> Dict[Decimal, PriceLevel]:
        """Get all bid price levels."""
        return self._bids

    @property
    def asks(self) -> Dict[Decimal, PriceLevel]:
        """Get all ask price levels."""
        return self._asks

    @property
    def best_bid(self) -> Optional[Decimal]:
        """Get best bid price (highest bid)."""
        return self._bid_prices[0] if self._bid_prices else None

    @property
    def best_ask(self) -> Optional[Decimal]:
        """Get best ask price (lowest ask)."""
        return self._ask_prices[0] if self._ask_prices else None

    @property
    def spread(self) -> Optional[Decimal]:
        """Get current bid-ask spread."""
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Get mid price."""
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return None

    @property
    def trades(self) -> List[Trade]:
        """Get all trades."""
        return list(self._trades)

    def get_snapshot(self, depth: Optional[int] = None) -> OrderBookSnapshot:
        """
        Get a snapshot of the current order book state.

        Args:
            depth: Number of price levels to include (None for all)

        Returns:
            OrderBookSnapshot with current state
        """
        snapshot_depth = depth or self.max_depth

        # Get bids
        bids = []
        for price in self._bid_prices[:snapshot_depth]:
            level = self._bids[price]
            bids.append((price, level.total_quantity))

        # Get asks
        asks = []
        for price in self._ask_prices[:snapshot_depth]:
            level = self._asks[price]
            asks.append((price, level.total_quantity))

        # Calculate totals
        total_bid_qty = (
            Decimal(sum(level.total_quantity for level in self._bids.values()))
            if self._bids
            else Decimal("0")
        )
        total_ask_qty = (
            Decimal(sum(level.total_quantity for level in self._asks.values()))
            if self._asks
            else Decimal("0")
        )

        return OrderBookSnapshot(
            symbol=self.symbol,
            timestamp=datetime.utcnow(),
            bids=bids,
            asks=asks,
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            spread=self.spread,
            mid_price=self.mid_price,
            total_bid_quantity=total_bid_qty,
            total_ask_quantity=total_ask_qty,
            bid_depth=len(self._bid_prices),
            ask_depth=len(self._ask_prices),
        )

    def submit_order(self, order: Order) -> List[Trade]:
        """
        Submit an order to the book.

        If marketable, will immediately match against existing orders.
        If not marketable, will be added to the book.

        Args:
            order: Order to submit

        Returns:
            List of trades generated from matching

        Raises:
            ValueError: If order parameters are invalid
        """
        if order.symbol != self.symbol:
            raise ValueError(f"Order symbol {order.symbol} doesn't match book {self.symbol}")

        if order.quantity <= 0:
            raise ValueError(f"Order quantity must be positive, got {order.quantity}")

        # Validate price for limit orders
        if order.order_type == OrderType.LIMIT and order.price is None:
            raise ValueError("Limit orders must have a price")

        # Round to tick size
        if order.price is not None:
            order_price = self._round_to_tick(order.price)
            object.__setattr__(order, 'price', order_price)

        # Store order
        self._orders[order.order_id] = order
        object.__setattr__(order, 'status', OrderStatus.OPEN)

        # For market orders, set price to opposite side's best price
        if order.order_type == OrderType.MARKET:
            if order.is_buy:
                object.__setattr__(order, 'price', self.best_ask)
            else:
                object.__setattr__(order, 'price', self.best_bid)

        # Match order if marketable
        trades = self._match_order(order)

        logger.debug(
            f"Submitted {order.side.value} order {order.order_id}: "
            f"{order.quantity} @ {order.price}, generated {len(trades)} trades"
        )

        return trades

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: ID of order to cancel

        Returns:
            True if order was cancelled, False if not found
        """
        order = self._orders.get(order_id)
        if order is None:
            return False

        if not order.is_active:
            return False

        # Remove from price level
        if order.is_buy and order.price in self._bids:
            level = self._bids[order.price]
            level.remove_order(order_id)
            if level.is_empty():
                self._remove_bid_level(order.price)
        elif order.is_sell and order.price in self._asks:
            level = self._asks[order.price]
            level.remove_order(order_id)
            if level.is_empty():
                self._remove_ask_level(order.price)

        # Cancel order
        order.cancel()
        logger.debug(f"Cancelled order {order_id}")

        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        return self._orders.get(order_id)

    def get_market_depth(self, side: Optional[OrderSide] = None) -> Dict[str, int]:
        """
        Get market depth metrics.

        Args:
            side: Order side (None for both sides)

        Returns:
            Dictionary with depth metrics
        """
        if side is None or side == OrderSide.BUY:
            bid_levels = len(self._bid_prices)
            bid_orders = sum(len(level.orders) for level in self._bids.values())
        else:
            bid_levels = bid_orders = 0

        if side is None or side == OrderSide.SELL:
            ask_levels = len(self._ask_prices)
            ask_orders = sum(len(level.orders) for level in self._asks.values())
        else:
            ask_levels = ask_orders = 0

        return {
            "bid_levels": bid_levels,
            "ask_levels": ask_levels,
            "total_levels": bid_levels + ask_levels,
            "bid_orders": bid_orders,
            "ask_orders": ask_orders,
            "total_orders": bid_orders + ask_orders,
        }

    def get_liquidity_metrics(self) -> Dict[str, Decimal]:
        """
        Get liquidity metrics for the order book.

        Returns:
            Dictionary with liquidity metrics
        """
        snapshot = self.get_snapshot()

        # Calculate depth-weighted spreads at different levels
        spreads = []
        for i in range(min(len(snapshot.bids), len(snapshot.asks), 5)):
            bid_price, _ = snapshot.bids[i]
            ask_price, _ = snapshot.asks[i]
            spreads.append(ask_price - bid_price)

        avg_spread = np.mean(spreads) if spreads else Decimal("0")

        # Calculate cumulative depth
        cumulative_bid_depth = sum(qty for _, qty in snapshot.bids[:10])
        cumulative_ask_depth = sum(qty for _, qty in snapshot.asks[:10])

        return {
            "best_bid": snapshot.best_bid or Decimal("0"),
            "best_ask": snapshot.best_ask or Decimal("0"),
            "spread": snapshot.spread or Decimal("0"),
            "mid_price": snapshot.mid_price or Decimal("0"),
            "avg_spread_5_levels": avg_spread,
            "total_bid_quantity": snapshot.total_bid_quantity,
            "total_ask_quantity": snapshot.total_ask_quantity,
            "bid_ask_ratio": (
                snapshot.total_bid_quantity / snapshot.total_ask_quantity
                if snapshot.total_ask_quantity > 0
                else Decimal("0")
            ),
            "cumulative_bid_depth_10": cumulative_bid_depth,
            "cumulative_ask_depth_10": cumulative_ask_depth,
        }

    def _round_to_tick(self, price: Decimal) -> Decimal:
        """Round price to tick size."""
        return (price / self.tick_size).quantize(Decimal("1")) * self.tick_size

    def _match_order(self, order: Order) -> List[Trade]:
        """
        Match an order against the book.

        Implements price-time priority matching:
        1. For buy orders: match against asks from lowest to highest
        2. For sell orders: match against bids from highest to lowest
        3. Match at the limit price or better (for limit orders)
        4. FIFO within each price level

        Args:
            order: Order to match

        Returns:
            List of trades generated
        """
        trades = []
        remaining_qty = order.remaining_quantity

        if remaining_qty == 0:
            return trades

        if order.is_buy:
            # Match against asks
            while (
                remaining_qty > 0
                and self._ask_prices
                and (order.order_type == OrderType.MARKET or self._ask_prices[0] <= order.price)
            ):  # type: ignore
                best_ask_price = self._ask_prices[0]
                ask_level = self._asks[best_ask_price]

                # Get first order in queue (FIFO)
                resting_order = ask_level.orders[0]

                # Determine trade quantity
                trade_qty = min(remaining_qty, resting_order.remaining_quantity)

                # Create trade
                trade = Trade(
                    trade_id=str(uuid.uuid4()),
                    symbol=self.symbol,
                    buy_order_id=order.order_id,
                    sell_order_id=resting_order.order_id,
                    price=best_ask_price,
                    quantity=trade_qty,
                    is_buy_aggressor=True,
                )
                trades.append(trade)
                self._trades.append(trade)

                # Fill orders
                order.fill(trade_qty, best_ask_price)
                resting_order.fill(trade_qty, best_ask_price)
                remaining_qty = order.remaining_quantity

                # Update or remove resting order
                if not resting_order.is_active:
                    ask_level.orders.popleft()
                    if ask_level.is_empty():
                        self._remove_ask_level(best_ask_price)
                else:
                    object.__setattr__(
                        ask_level, 'total_quantity', ask_level.total_quantity - trade_qty
                    )

        else:  # Sell order
            # Match against bids
            while (
                remaining_qty > 0
                and self._bid_prices
                and (order.order_type == OrderType.MARKET or self._bid_prices[0] >= order.price)
            ):  # type: ignore
                best_bid_price = self._bid_prices[0]
                bid_level = self._bids[best_bid_price]

                # Get first order in queue (FIFO)
                resting_order = bid_level.orders[0]

                # Determine trade quantity
                trade_qty = min(remaining_qty, resting_order.remaining_quantity)

                # Create trade
                trade = Trade(
                    trade_id=str(uuid.uuid4()),
                    symbol=self.symbol,
                    buy_order_id=resting_order.order_id,
                    sell_order_id=order.order_id,
                    price=best_bid_price,
                    quantity=trade_qty,
                    is_buy_aggressor=False,
                )
                trades.append(trade)
                self._trades.append(trade)

                # Fill orders
                order.fill(trade_qty, best_bid_price)
                resting_order.fill(trade_qty, best_bid_price)
                remaining_qty = order.remaining_quantity

                # Update or remove resting order
                if not resting_order.is_active:
                    bid_level.orders.popleft()
                    if bid_level.is_empty():
                        self._remove_bid_level(best_bid_price)
                else:
                    object.__setattr__(
                        bid_level, 'total_quantity', bid_level.total_quantity - trade_qty
                    )

        # Add remaining quantity to book if any
        if remaining_qty > 0 and order.order_type == OrderType.LIMIT:
            self._add_to_book(order)

        return trades

    def _add_to_book(self, order: Order) -> None:
        """Add an order to the book."""
        price = order.price

        if order.is_buy:
            if price not in self._bids:
                # Create new price level
                self._add_bid_level(price)
            self._bids[price].add_order(order)
        else:
            if price not in self._asks:
                # Create new price level
                self._add_ask_level(price)
            self._asks[price].add_order(order)

    def _add_bid_level(self, price: Decimal) -> None:
        """Add a new bid price level."""
        self._bids[price] = PriceLevel(price=price)
        # Insert in sorted position (descending)
        import bisect

        prices = [-float(p) for p in self._bid_prices]
        bisect.insort(prices, -float(price))
        self._bid_prices = [Decimal(str(-p)) for p in prices]

    def _add_ask_level(self, price: Decimal) -> None:
        """Add a new ask price level."""
        self._asks[price] = PriceLevel(price=price)
        # Insert in sorted position (ascending)
        import bisect

        bisect.insort(self._ask_prices, float(price))
        self._ask_prices = [Decimal(str(p)) for p in self._ask_prices]

    def _remove_bid_level(self, price: Decimal) -> None:
        """Remove a bid price level."""
        self._bid_prices.remove(price)
        del self._bids[price]

    def _remove_ask_level(self, price: Decimal) -> None:
        """Remove an ask price level."""
        self._ask_prices.remove(price)
        del self._asks[price]


def create_limit_order_book(
    symbol: str,
    tick_size: float = 0.01,
    max_depth: int = 100,
) -> LimitOrderBook:
    """
    Factory function to create a LimitOrderBook.

    Args:
        symbol: Trading symbol
        tick_size: Minimum price increment
        max_depth: Maximum depth to track

    Returns:
        Configured LimitOrderBook instance

    Example:
        >>> book = create_limit_order_book("AAPL", tick_size=0.01)
        >>> snapshot = book.get_snapshot(depth=10)
        >>> print(f"Best bid: {snapshot.best_bid}, Best ask: {snapshot.best_ask}")
    """
    return LimitOrderBook(
        symbol=symbol,
        tick_size=Decimal(str(tick_size)),
        max_depth=max_depth,
    )
