from __future__ import annotations

"""
Tick-Level Order Flow Imbalance Processor.

This module processes tick-level data for OFI calculation, distinguishing
between aggressive trades (market orders) and passive limit orders.

At the tick level:
- Market buy (hits ask): +quantity to OFI
- Market sell (hits bid): -quantity to OFI
- Limit orders: Update order book, recalculate OFI

References:
- Hasbrouck, J. (1991) "Measuring the Information Content of Stock Trades"
- Johnson, B. (2010) "Algorithmic Trading & DMA"
"""

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from app.domain.market_analysis.microstructure.ofi.models import (
    OrderBookSnapshot,
    OrderSide,
    TickData,
)
from app.domain.market_analysis.microstructure.ofi.ofi_calculator import OFICalculator

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

logger = logging.getLogger(__name__)


class InvalidPriceError(ValueError):
    """Raised when an invalid price is provided."""


@dataclass
class TickOFIResult:
    """
    Result of tick-level OFI calculation.

    Attributes:
        timestamp: Timestamp of tick
        ofi: Current OFI value
        tick_ofi: OFI contribution from this tick
        market_buy_volume: Total market buy volume
        market_sell_volume: Total market sell volume
        aggressive_ratio: Ratio of aggressive to total volume
        order_book_depth: Current order book depth
    """

    timestamp: datetime
    ofi: float
    tick_ofi: float
    market_buy_volume: int
    market_sell_volume: int
    aggressive_ratio: float
    order_book_depth: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "ofi": self.ofi,
            "tick_ofi": self.tick_ofi,
            "market_buy_volume": self.market_buy_volume,
            "market_sell_volume": self.market_sell_volume,
            "aggressive_ratio": self.aggressive_ratio,
            "order_book_depth": self.order_book_depth,
        }


@dataclass
class OrderBookLevel:
    """
    Single level in the order book.

    Attributes:
        price: Price level
        quantity: Available quantity
        orders_count: Number of orders at this level
    """

    price: Decimal
    quantity: int
    orders_count: int = 1

    def __add__(self, other: OrderBookLevel) -> OrderBookLevel:
        """Combine two levels (same price)."""
        if self.price != other.price:
            raise ValueError("Cannot combine levels with different prices")
        return OrderBookLevel(
            price=self.price,
            quantity=self.quantity + other.quantity,
            orders_count=self.orders_count + other.orders_count,
        )


@dataclass
class OrderBookState:
    """
    Current state of the order book.

    Maintains bid and ask levels for tick-by-tick updates.

    Attributes:
        symbol: Trading symbol
        timestamp: Last update timestamp
        bids: Dictionary of price -> quantity for bids
        asks: Dictionary of price -> quantity for asks
        last_update: Type of last update
    """

    symbol: str
    timestamp: datetime
    bids: dict[Decimal, int] = field(default_factory=dict)
    asks: dict[Decimal, int] = field(default_factory=dict)
    last_update: str = "init"

    def _validate_price(self, price: Decimal) -> None:
        """
        Validate price for order book updates.

        Args:
            price: Price to validate

        Raises:
            InvalidPriceError: If price is invalid (negative, zero, or NaN)
        """
        # Check if price is negative
        if price < 0:
            raise InvalidPriceError(f"Price cannot be negative: {price}")

        # Check if price is zero
        if price == 0:
            raise InvalidPriceError("Price cannot be zero")

        # Check if price is NaN
        if math.isnan(price):
            raise InvalidPriceError(f"Price cannot be NaN: {price}")

    def update_bid(self, price: Decimal, quantity: int) -> None:
        """
        Update bid level.

        Args:
            price: Bid price
            quantity: Bid quantity

        Raises:
            InvalidPriceError: If price is invalid
        """
        self._validate_price(price)

        if quantity == 0:
            self.bids.pop(price, None)
        else:
            self.bids[price] = quantity

    def update_ask(self, price: Decimal, quantity: int) -> None:
        """
        Update ask level.

        Args:
            price: Ask price
            quantity: Ask quantity

        Raises:
            InvalidPriceError: If price is invalid
        """
        self._validate_price(price)

        if quantity == 0:
            self.asks.pop(price, None)
        else:
            self.asks[price] = quantity

    def get_best_bid(self) -> tuple[Decimal, int] | None:
        """Get best bid (highest price)."""
        if not self.bids:
            return None
        price = max(self.bids.keys())
        return (price, self.bids[price])

    def get_best_ask(self) -> tuple[Decimal, int] | None:
        """Get best ask (lowest price)."""
        if not self.asks:
            return None
        price = min(self.asks.keys())
        return (price, self.asks[price])

    def to_snapshot(self) -> OrderBookSnapshot:
        """Convert to OrderBookSnapshot."""
        bid_list = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
        ask_list = sorted(self.asks.items(), key=lambda x: x[0])
        return OrderBookSnapshot(
            symbol=self.symbol,
            timestamp=self.timestamp,
            bids=[(p, q) for p, q in bid_list],
            asks=[(p, q) for p, q in ask_list],
        )

    def get_depth(self, levels: int = 5) -> tuple[int, int]:
        """Get total depth at top N levels."""
        bid_prices = sorted(self.bids.keys(), reverse=True)[:levels]
        ask_prices = sorted(self.asks.keys())[:levels]

        bid_depth = sum(self.bids[p] for p in bid_prices)
        ask_depth = sum(self.asks[p] for p in ask_prices)

        return (bid_depth, ask_depth)


class TickLevelOFIProcessor:
    """
    Process tick-level data for OFI calculation.

    This processor distinguishes between:
    1. Aggressive trades (market orders hitting the book)
    2. Passive limit orders (adding to the book)
    3. Order cancellations (removing from the book)

    The tick-level OFI is calculated as:
        tick_OFI = (market_buys - market_sells) / total_volume

    Example:
        >>> processor = TickLevelOFIProcessor(window_size=100)
        >>> result = processor.process_tick(tick_data)
        >>> print(f"Tick OFI: {result.tick_ofi:.3f}")
    """

    def __init__(self, window_size: int = 100, calculator: OFICalculator | None = None):
        """
        Initialize tick-level OFI processor.

        Args:
            window_size: Size of rolling window for OFI calculation
            calculator: OFI calculator (creates new if None)
        """
        self.window_size = window_size
        self.calculator = calculator or OFICalculator()

        # Tick buffer
        self.tick_buffer: deque[TickData] = deque(maxlen=window_size)

        # Order book state
        self.order_book: OrderBookState | None = None

        # Aggressive trade tracking
        self.market_buy_volume: int = 0
        self.market_sell_volume: int = 0
        self.total_aggressive_volume: int = 0

        # OFI tracking
        self.current_ofi: float = 0.0
        self.ofi_history: deque[float] = deque(maxlen=window_size)

        logger.info(
            "TickLevelOFIProcessor initialized",
            extra={"window_size": window_size},
        )

    def process_tick(self, tick: TickData) -> TickOFIResult:
        """
        Process tick and return updated OFI.

        For aggressive trades:
        - Market buy: OFI increases by quantity / total_volume
        - Market sell: OFI decreases by quantity / total_volume

        For limit orders:
        - Update order book
        - Recalculate OFI from book state

        Args:
            tick: Tick data to process

        Returns:
            TickOFIResult with updated OFI values
        """
        # Initialize order book if needed
        if self.order_book is None:
            self.order_book = OrderBookState(symbol=tick.symbol, timestamp=tick.timestamp)

        # Add to buffer
        self.tick_buffer.append(tick)

        # Process based on tick type
        tick_ofi = 0.0

        if tick.is_market_buy:
            # Aggressive buy hitting ask
            tick_ofi = self._process_market_buy(tick)
        elif tick.is_market_sell:
            # Aggressive sell hitting bid
            tick_ofi = self._process_market_sell(tick)
        else:
            # Limit order - update book and recalculate
            tick_ofi = self._process_limit_order(tick)

        # Update OFI
        self.current_ofi = self._calculate_rolling_ofi()
        self.ofi_history.append(self.current_ofi)

        # Calculate aggressive ratio
        total_vol = self.market_buy_volume + self.market_sell_volume
        aggressive_ratio = self.total_aggressive_volume / total_vol if total_vol > 0 else 0.0

        # Get order book depth
        bid_depth, ask_depth = self.order_book.get_depth(5) if self.order_book else (0, 0)

        return TickOFIResult(
            timestamp=tick.timestamp,
            ofi=self.current_ofi,
            tick_ofi=tick_ofi,
            market_buy_volume=self.market_buy_volume,
            market_sell_volume=self.market_sell_volume,
            aggressive_ratio=aggressive_ratio,
            order_book_depth=bid_depth + ask_depth,
        )

    def _process_market_buy(self, tick: TickData) -> float:
        """
        Process aggressive market buy.

        Market buy hits the ask, removing liquidity.
        OFI contribution: +quantity / total_volume
        """
        # Update volume tracking
        self.market_buy_volume += tick.quantity
        self.total_aggressive_volume += tick.quantity

        # Remove from ask side of book
        if self.order_book and tick.price in self.order_book.asks:
            current_qty = self.order_book.asks[tick.price]
            new_qty = max(0, current_qty - tick.quantity)
            self.order_book.update_ask(tick.price, new_qty)

        # Calculate OFI contribution
        total_volume = self.market_buy_volume + self.market_sell_volume
        if total_volume == 0:
            return 0.0

        return tick.quantity / total_volume

    def _process_market_sell(self, tick: TickData) -> float:
        """
        Process aggressive market sell.

        Market sell hits the bid, removing liquidity.
        OFI contribution: -quantity / total_volume
        """
        # Update volume tracking
        self.market_sell_volume += tick.quantity
        self.total_aggressive_volume += tick.quantity

        # Remove from bid side of book
        if self.order_book and tick.price in self.order_book.bids:
            current_qty = self.order_book.bids[tick.price]
            new_qty = max(0, current_qty - tick.quantity)
            self.order_book.update_bid(tick.price, new_qty)

        # Calculate OFI contribution
        total_volume = self.market_buy_volume + self.market_sell_volume
        if total_volume == 0:
            return 0.0

        return -tick.quantity / total_volume

    def _process_limit_order(self, tick: TickData) -> float:
        """
        Process passive limit order.

        Limit order adds to the book.
        Recalculate OFI from current book state.
        """
        if not self.order_book:
            return 0.0

        # Update order book
        if tick.side in (OrderSide.BUY, OrderSide.BID):
            self.order_book.update_bid(tick.price, tick.quantity)
        else:
            self.order_book.update_ask(tick.price, tick.quantity)

        # Recalculate OFI from book
        snapshot = self.order_book.to_snapshot()
        result = self.calculator.calculate_ofi(snapshot)

        if result.is_valid:
            return result.ofi
        return 0.0

    def _calculate_rolling_ofi(self, window: int | None = None) -> float:
        """
        Calculate rolling OFI from recent tick contributions.

        Args:
            window: Window size (uses self.window_size if None)

        Returns:
            Rolling OFI value
        """
        window = window or self.window_size
        if len(self.ofi_history) < 2:
            return self.current_ofi

        # Exponential weighted moving average
        recent_ofi = list(self.ofi_history)[-window:]
        if not recent_ofi:
            return 0.0

        # Give more weight to recent ticks
        weights = np.exp(np.linspace(-1, 0, len(recent_ofi)))
        weights = weights / weights.sum()

        weighted_ofi = float(np.average(recent_ofi, weights=weights))
        return weighted_ofi

    def calculate_tick_ofi(self, ticks: list[TickData]) -> float:
        """
        Calculate OFI from a list of tick trades.

        OFI = sum(market_buys - market_sells) / total_volume

        Args:
            ticks: List of tick data

        Returns:
            OFI value
        """
        if not ticks:
            return 0.0

        market_buy_vol = sum(t.quantity for t in ticks if t.is_market_buy)
        market_sell_vol = sum(t.quantity for t in ticks if t.is_market_sell)
        total_vol = market_buy_vol + market_sell_vol

        if total_vol == 0:
            return 0.0

        return (market_buy_vol - market_sell_vol) / total_vol

    def update_order_book(
        self, tick: TickData, current_book: OrderBookSnapshot
    ) -> OrderBookSnapshot:
        """
        Update order book with limit order.

        Args:
            tick: Tick data representing limit order
            current_book: Current order book snapshot

        Returns:
            Updated order book snapshot
        """
        # Convert to dict for easier manipulation
        bids = dict(current_book.bids)
        asks = dict(current_book.asks)

        if tick.side in (OrderSide.BUY, OrderSide.BID):
            # Update bid side
            if tick.quantity == 0:
                bids.pop(tick.price, None)
            else:
                existing = bids.get(tick.price, 0)
                bids[tick.price] = existing + tick.quantity
        else:
            # Update ask side
            if tick.quantity == 0:
                asks.pop(tick.price, None)
            else:
                existing = asks.get(tick.price, 0)
                asks[tick.price] = existing + tick.quantity

        # Reconstruct snapshot
        return OrderBookSnapshot(
            symbol=current_book.symbol,
            timestamp=tick.timestamp,
            bids=sorted(bids.items(), key=lambda x: x[0], reverse=True),
            asks=sorted(asks.items(), key=lambda x: x[0]),
        )

    def get_aggressive_flow_ratio(self, window: int = 50) -> float:
        """
        Calculate ratio of aggressive buy to aggressive sell volume.

        Args:
            window: Window for calculation

        Returns:
            Ratio > 1: More buying pressure
            Ratio < 1: More selling pressure
        """
        if len(self.tick_buffer) < 2:
            return 1.0

        recent_ticks = list(self.tick_buffer)[-window:]

        buy_vol = sum(t.quantity for t in recent_ticks if t.is_market_buy)
        sell_vol = sum(t.quantity for t in recent_ticks if t.is_market_sell)

        if sell_vol == 0:
            return float("inf") if buy_vol > 0 else 1.0

        return buy_vol / sell_vol

    def detect_aggressive_surge(self, threshold: float = 2.0, window: int = 20) -> str | None:
        """
        Detect surge in aggressive trading activity.

        Args:
            threshold: Threshold for surge detection (std devs)
            window: Window for comparison

        Returns:
            "buy_surge", "sell_surge", or None
        """
        if len(self.tick_buffer) < window * 2:
            return None

        ticks = list(self.tick_buffer)

        # Calculate recent aggressive volume
        recent = ticks[-window:]
        recent_buy_vol = sum(t.quantity for t in recent if t.is_market_buy)
        recent_sell_vol = sum(t.quantity for t in recent if t.is_market_sell)
        recent_total = recent_buy_vol + recent_sell_vol

        # Calculate previous aggressive volume
        previous = ticks[-(window * 2) : -window]
        prev_buy_vol = sum(t.quantity for t in previous if t.is_market_buy)
        prev_sell_vol = sum(t.quantity for t in previous if t.is_market_sell)
        prev_total = prev_buy_vol + prev_sell_vol

        if prev_total == 0:
            return None

        # Check for surge
        ratio = recent_total / prev_total

        if ratio > threshold:
            if recent_buy_vol > recent_sell_vol:
                return "buy_surge"
            else:
                return "sell_surge"

        return None

    def reset(self) -> None:
        """Reset processor state."""
        self.tick_buffer.clear()
        self.order_book = None
        self.market_buy_volume = 0
        self.market_sell_volume = 0
        self.total_aggressive_volume = 0
        self.current_ofi = 0.0
        self.ofi_history.clear()
        logger.info(
            "TickLevelOFIProcessor reset",
            extra={"window_size": self.window_size},
        )

    def get_statistics(self) -> dict:
        """
        Get processor statistics.

        Returns:
            Dictionary with statistics
        """
        total_ticks = len(self.tick_buffer)
        if total_ticks == 0:
            return {
                "total_ticks": 0,
                "market_buy_volume": 0,
                "market_sell_volume": 0,
                "current_ofi": 0.0,
                "aggressive_ratio": 0.0,
            }

        total_vol = self.market_buy_volume + self.market_sell_volume

        return {
            "total_ticks": total_ticks,
            "market_buy_volume": self.market_buy_volume,
            "market_sell_volume": self.market_sell_volume,
            "total_volume": total_vol,
            "current_ofi": self.current_ofi,
            "aggressive_ratio": self.total_aggressive_volume / total_vol if total_vol > 0 else 0.0,
            "ofi_mean": float(np.mean(list(self.ofi_history))) if self.ofi_history else 0.0,
            "ofi_std": float(np.std(list(self.ofi_history))) if self.ofi_history else 0.0,
        }
