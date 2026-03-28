"""
Market Mechanics - Larry Harris's Auction and Trading Session Models

This module implements the market mechanics described in Harris, Chapter 4:
"Market Structure" and Chapter 5: "Market Quality."

Key concepts implemented:
1. Call auction mechanics (opening/closing auctions)
2. Continuous double auction
3. Trading session management
4. Market phases (pre-market, opening, continuous, closing, post-market)
5. Price discovery in auctions
6. Volume and time-weighted average prices

Reference:
    Harris, L. (2003). Trading and Exchanges, Chapters 4-5.
"""
# mypy: ignore-errors

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .order_book import LimitOrderBook, Order, OrderType, Trade

logger = logging.getLogger(__name__)


class AuctionType(Enum):
    """Type of auction mechanism."""

    OPENING = "OPENING"  # Opening call auction
    CLOSING = "CLOSING"  # Closing call auction
    INTRADAY = "INTRADAY"  # Intraday call auction
    VOLATILITY = "VOLATILITY"  # Volatility interruption auction
    IMBALANCE = "IMBALANCE"  # Order imbalance auction


class MarketPhase(Enum):
    """Phase of the trading day."""

    PRE_MARKET = "PRE_MARKET"
    OPENING_AUCTION = "OPENING_AUCTION"
    CONTINUOUS_TRADING = "CONTINUOUS_TRADING"
    CLOSING_AUCTION = "CLOSING_AUCTION"
    POST_MARKET = "POST_MARKET"
    CLOSED = "CLOSED"


@dataclass
class AuctionResult:
    """
    Result of a call auction.

    Attributes:
        auction_type: Type of auction
        symbol: Trading symbol
        auction_price: Clearing price
        total_volume: Total volume matched
        buy_volume: Total buy volume matched
        sell_volume: Total sell volume matched
        matched_orders: Orders that were matched
        unmatched_orders: Orders that remain unmatched
        imbalance: Order imbalance (buy - sell)
        timestamp: Auction timestamp
        execution_quality: Quality metrics
    """

    auction_type: AuctionType
    symbol: str
    auction_price: Optional[Decimal]
    total_volume: Decimal
    buy_volume: Decimal
    sell_volume: Decimal
    matched_orders: List[str]
    unmatched_orders: List[str]
    imbalance: Decimal
    timestamp: datetime
    execution_quality: Dict[str, Decimal] = field(default_factory=dict)

    @property
    def is_matched(self) -> bool:
        """Check if auction produced matches."""
        return self.auction_price is not None and self.total_volume > 0

    @property
    def surplus(self) -> Decimal:
        """
        Calculate total trader surplus.

        Surplus = sum(buy_value_at_auction - buy_limit) +
                  sum(sell_limit - sell_value_at_auction)
        """
        # Simplified - would need order prices to calculate properly
        return Decimal("0")


@dataclass
class TradingSession:
    """
    A trading session definition.

    Attributes:
        name: Session name (e.g., "Regular", "Extended")
        start_time: Session start time
        end_time: Session end time
        opening_auction: Whether opening auction is conducted
        closing_auction: Whether closing auction is conducted
        is_continuous: Whether continuous trading occurs
    """

    name: str
    start_time: time
    end_time: time
    opening_auction: bool = True
    closing_auction: bool = True
    is_continuous: bool = True


@dataclass
class PhaseTransition:
    """
    Record of a market phase transition.

    Attributes:
        from_phase: Previous phase
        to_phase: New phase
        timestamp: Transition timestamp
        trigger: What triggered the transition
    """

    from_phase: MarketPhase
    to_phase: MarketPhase
    timestamp: datetime
    trigger: str


class AuctionMechanism:
    """
    Call Auction Mechanism.

    Implements the call auction mechanism as described in Harris Chapter 4.
    In a call auction, orders are batched and executed at a single clearing price
    that maximizes executable volume.

    The clearing price is determined by:
    1. Maximizing executable volume
    2. Minimizing imbalance
    3. Staying within the bid-ask spread (if continuous trading exists)

    Call auctions are used for:
    - Opening and closing prices
    - Trading halts and resumptions
    - Volatility interruptions
    - Order imbalance situations

    Attributes:
        symbol: Trading symbol
        auction_type: Type of auction
        order_book: Limit order book for reference
        orders: Orders collected for auction
        min_price: Minimum acceptable price
        max_price: Maximum acceptable price
        price_tick: Price increment for price discovery
        max_iterations: Maximum iterations for price discovery
    """

    def __init__(
        self,
        symbol: str,
        auction_type: AuctionType,
        order_book: Optional[LimitOrderBook] = None,
        price_tick: Optional[Decimal] = None,
        max_iterations: int = 100,
    ):
        """
        Initialize the auction mechanism.

        Args:
            symbol: Trading symbol
            auction_type: Type of auction
            order_book: Reference order book
            price_tick: Price increment
            max_iterations: Maximum search iterations
        """
        if price_tick is None:
            price_tick = Decimal("0.01")
        self.symbol = symbol
        self.auction_type = auction_type
        self.order_book = order_book
        self.price_tick = price_tick
        self.max_iterations = max_iterations

        self._buy_orders: Dict[Decimal, List[Order]] = {}
        self._sell_orders: Dict[Decimal, List[Order]] = {}

        logger.debug(f"Initialized {auction_type.value} auction for {symbol}")

    def submit_order(self, order: Order) -> None:
        """
        Submit an order to the auction.

        Args:
            order: Order to submit
        """
        if order.order_type != OrderType.LIMIT:
            raise ValueError(f"Auction only accepts limit orders, got {order.order_type}")

        if order.price is None:
            raise ValueError("Limit orders must have a price")

        if order.is_buy:
            if order.price not in self._buy_orders:
                self._buy_orders[order.price] = []
            self._buy_orders[order.price].append(order)
        else:
            if order.price not in self._sell_orders:
                self._sell_orders[order.price] = []
            self._sell_orders[order.price].append(order)

        logger.debug(
            f"Submitted {order.side.value} order to auction: " f"{order.quantity} @ {order.price}"
        )

    def get_auction_indicative_price(self) -> Optional[Decimal]:
        """
        Get current indicative clearing price (without executing).

        Returns:
            Indicative clearing price, or None if no orders
        """
        return self._find_clearing_price()[0]

    def get_auction_indicative_volume(self) -> Decimal:
        """
        Get current indicative volume at clearing price.

        Returns:
            Indicative executable volume
        """
        price, volume = self._find_clearing_price()
        return volume

    def get_order_imbalance(self) -> Decimal:
        """
        Calculate current order imbalance.

        Returns:
            Buy volume - sell volume
        """
        buy_vol = sum(
            sum(o.remaining_quantity for o in orders) for orders in self._buy_orders.values()
        )
        sell_vol = sum(
            sum(o.remaining_quantity for o in orders) for orders in self._sell_orders.values()
        )
        return buy_vol - sell_vol

    def execute_auction(self) -> AuctionResult:
        """
        Execute the auction and determine clearing price.

        The clearing price maximizes executable volume while minimizing imbalance.

        Algorithm:
        1. Collect all buy and sell orders
        2. Sort buys by price descending, sells by price ascending
        3. Find price that maximizes tradable volume
        4. Match orders at that price

        Returns:
            AuctionResult with execution details

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 4,
            "Call Auctions"
        """
        timestamp = datetime.utcnow()

        # Find clearing price
        clearing_price, executable_volume = self._find_clearing_price()

        if clearing_price is None or executable_volume == 0:
            # No matches possible
            logger.info(f"{self.auction_type.value} auction: No matches possible")
            return AuctionResult(
                auction_type=self.auction_type,
                symbol=self.symbol,
                auction_price=None,
                total_volume=Decimal("0"),
                buy_volume=Decimal("0"),
                sell_volume=Decimal("0"),
                matched_orders=[],
                unmatched_orders=[
                    o.order_id
                    for orders in list(self._buy_orders.values()) + list(self._sell_orders.values())
                    for o in orders
                ],
                imbalance=self.get_order_imbalance(),
                timestamp=timestamp,
            )

        # Match orders at clearing price
        matched_orders, trades, buy_vol, sell_vol = self._match_at_price(clearing_price)

        # Calculate execution quality
        execution_quality = self._calculate_execution_quality(
            clearing_price, executable_volume, trades
        )

        logger.info(
            f"{self.auction_type.value} auction executed: "
            f"price={clearing_price}, volume={executable_volume}"
        )

        return AuctionResult(
            auction_type=self.auction_type,
            symbol=self.symbol,
            auction_price=clearing_price,
            total_volume=executable_volume,
            buy_volume=buy_vol,
            sell_volume=sell_vol,
            matched_orders=matched_orders,
            unmatched_orders=[
                o.order_id
                for orders in list(self._buy_orders.values()) + list(self._sell_orders.values())
                for o in orders
                if o.order_id not in matched_orders
            ],
            imbalance=self.get_order_imbalance(),
            timestamp=timestamp,
            execution_quality=execution_quality,
        )

    def _find_clearing_price(self) -> Tuple[Optional[Decimal], Decimal]:
        """
        Find the clearing price that maximizes executable volume.

        The clearing price is the price at which buy and sell orders
        can be matched to maximize total volume.

        Returns:
            (clearing_price, executable_volume)

        Algorithm:
            1. For each price level, calculate cumulative buy and sell volume
            2. The clearing price maximizes min(cumulative_buy, cumulative_sell)
            3. If multiple prices give same volume, choose one that minimizes imbalance
        """
        if not self._buy_orders or not self._sell_orders:
            return None, Decimal("0")

        # Get sorted price levels
        buy_prices = sorted(self._buy_orders.keys(), reverse=True)
        sell_prices = sorted(self._sell_orders.keys())

        # Find price range
        min_price = sell_prices[0]
        max_price = buy_prices[0]

        if min_price > max_price:
            # No overlap possible
            return None, Decimal("0")

        # Calculate cumulative volumes at each price
        best_price = None
        best_volume = Decimal("0")
        best_imbalance = Decimal("999999999")

        # Search through price range
        current_price = min_price
        while current_price <= max_price:
            # Calculate executable volume at this price
            buy_vol = self._get_cumulative_buy_volume(current_price)
            sell_vol = self._get_cumulative_sell_volume(current_price)
            exec_vol = min(buy_vol, sell_vol)
            imbalance = abs(buy_vol - sell_vol)

            # Better if more volume, or same volume with less imbalance
            if exec_vol > best_volume or (exec_vol == best_volume and imbalance < best_imbalance):
                best_price = current_price
                best_volume = exec_vol
                best_imbalance = imbalance

            current_price += self.price_tick

        return best_price, best_volume

    def _get_cumulative_buy_volume(self, price: Decimal) -> Decimal:
        """Get cumulative buy volume at or above given price."""
        total = Decimal("0")
        for p, orders in self._buy_orders.items():
            if p >= price:
                total += sum(o.remaining_quantity for o in orders)
        return total

    def _get_cumulative_sell_volume(self, price: Decimal) -> Decimal:
        """Get cumulative sell volume at or below given price."""
        total = Decimal("0")
        for p, orders in self._sell_orders.items():
            if p <= price:
                total += sum(o.remaining_quantity for o in orders)
        return total

    def _match_at_price(self, price: Decimal) -> Tuple[List[str], List[Trade], Decimal, Decimal]:
        """
        Match orders at given price.

        Returns:
            (matched_order_ids, trades, buy_volume, sell_volume)
        """
        matched_ids = []
        trades = []

        # Get eligible orders
        eligible_buys = []
        for p, orders in self._buy_orders.items():
            if p >= price:
                eligible_buys.extend([(o, p) for o in orders])

        eligible_sells = []
        for p, orders in self._sell_orders.items():
            if p <= price:
                eligible_sells.extend([(o, p) for o in orders])

        # Sort by time priority (oldest first)
        eligible_buys.sort(key=lambda x: x[0].created_at)
        eligible_sells.sort(key=lambda x: x[0].created_at)

        # Match orders
        buy_idx = sell_idx = 0
        total_buy_vol = Decimal("0")
        total_sell_vol = Decimal("0")

        while buy_idx < len(eligible_buys) and sell_idx < len(eligible_sells):
            buy_order, buy_limit = eligible_buys[buy_idx]
            sell_order, sell_limit = eligible_sells[sell_idx]

            # Calculate trade quantity
            trade_qty = min(buy_order.remaining_quantity, sell_order.remaining_quantity)

            if trade_qty > 0:
                # Create trade
                trade = Trade(
                    trade_id=str(uuid.uuid4()),
                    symbol=self.symbol,
                    buy_order_id=buy_order.order_id,
                    sell_order_id=sell_order.order_id,
                    price=price,
                    quantity=trade_qty,
                )
                trades.append(trade)

                # Update orders
                buy_order.fill(trade_qty, price)
                sell_order.fill(trade_qty, price)

                if buy_order not in eligible_buys[:buy_idx]:
                    matched_ids.append(buy_order.order_id)
                if sell_order not in eligible_sells[:sell_idx]:
                    matched_ids.append(sell_order.order_id)

                total_buy_vol += trade_qty
                total_sell_vol += trade_qty

            # Move to next order if filled
            if buy_order.remaining_quantity == 0:
                buy_idx += 1
            if sell_order.remaining_quantity == 0:
                sell_idx += 1

        return matched_ids, trades, total_buy_vol, total_sell_vol

    def _calculate_execution_quality(
        self,
        price: Decimal,
        volume: Decimal,
        trades: List[Trade],
    ) -> Dict[str, Decimal]:
        """Calculate execution quality metrics."""
        if not trades or price is None:
            return {}

        # Calculate price improvement for buys and sells
        buy_improvement = Decimal("0")
        sell_improvement = Decimal("0")

        for trade in trades:
            buy_order = self._find_order(trade.buy_order_id)
            sell_order = self._find_order(trade.sell_order_id)

            if buy_order and buy_order.price:
                improvement = buy_order.price - price
                if improvement > 0:
                    buy_improvement += improvement * trade.quantity

            if sell_order and sell_order.price:
                improvement = price - sell_order.price
                if improvement > 0:
                    sell_improvement += improvement * trade.quantity

        return {
            "avg_trade_size": volume / Decimal(str(len(trades))) if trades else Decimal("0"),
            "total_buy_improvement": buy_improvement,
            "total_sell_improvement": sell_improvement,
            "avg_price_improvement": (
                (buy_improvement + sell_improvement) / (volume * 2) if volume > 0 else Decimal("0")
            ),
        }

    def _find_order(self, order_id: str) -> Optional[Order]:
        """Find an order by ID."""
        for orders in self._buy_orders.values():
            for order in orders:
                if order.order_id == order_id:
                    return order
        for orders in self._sell_orders.values():
            for order in orders:
                if order.order_id == order_id:
                    return order
        return None


class ContinuousTrading:
    """
    Continuous Double Auction Mechanism.

    In continuous trading, orders are matched immediately as they arrive
    if they are marketable against the existing order book.

    This is the standard mechanism for most equity trading during regular hours.

    The continuous double auction has these properties:
    1. Orders can arrive at any time
    2. Marketable orders execute immediately
    3. Non-marketable orders rest in the book
    4. Price-time priority determines execution order
    5. Bid-ask spread emerges naturally from order flow

    Attributes:
        order_book: Underlying limit order book
        is_active: Whether continuous trading is active
    """

    def __init__(self, order_book: LimitOrderBook):
        """
        Initialize continuous trading.

        Args:
            order_book: Underlying limit order book
        """
        self.order_book = order_book
        self._is_active = False

        logger.debug(f"Initialized continuous trading for {order_book.symbol}")

    @property
    def is_active(self) -> bool:
        """Check if continuous trading is active."""
        return self._is_active

    def start(self) -> None:
        """Start continuous trading."""
        self._is_active = True
        logger.info(f"Started continuous trading for {self.order_book.symbol}")

    def stop(self) -> None:
        """Stop continuous trading."""
        self._is_active = False
        logger.info(f"Stopped continuous trading for {self.order_book.symbol}")

    def submit_order(self, order: Order) -> List[Trade]:
        """
        Submit an order during continuous trading.

        Args:
            order: Order to submit

        Returns:
            List of trades generated

        Raises:
            RuntimeError: If continuous trading is not active
        """
        if not self._is_active:
            raise RuntimeError("Continuous trading is not active")

        return self.order_book.submit_order(order)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        return self.order_book.cancel_order(order_id)

    def get_best_bid(self) -> Optional[Decimal]:
        """Get current best bid."""
        return self.order_book.best_bid

    def get_best_ask(self) -> Optional[Decimal]:
        """Get current best ask."""
        return self.order_book.best_ask

    def get_spread(self) -> Optional[Decimal]:
        """Get current bid-ask spread."""
        return self.order_book.spread

    def get_mid_price(self) -> Optional[Decimal]:
        """Get current mid price."""
        return self.order_book.mid_price

    def calculate_vwap(self, window_ms: int = 1000) -> Optional[Decimal]:
        """
        Calculate volume-weighted average price over recent trades.

        Args:
            window_ms: Time window in milliseconds

        Returns:
            VWAP over the window, or None if no trades
        """
        if not self.order_book.trades:
            return None

        cutoff_time = datetime.utcnow().timestamp() - window_ms / 1000

        total_value = Decimal("0")
        total_volume = Decimal("0")

        for trade in reversed(self.order_book.trades):
            if trade.timestamp.timestamp() < cutoff_time:
                break
            total_value += trade.price * trade.quantity
            total_volume += trade.quantity

        if total_volume == 0:
            return None

        return total_value / total_volume

    def calculate_twap(self, window_ms: int = 1000) -> Optional[Decimal]:
        """
        Calculate time-weighted average price over recent trades.

        Args:
            window_ms: Time window in milliseconds

        Returns:
            TWAP over the window, or None if insufficient data
        """
        if not self.order_book.trades:
            return None

        cutoff_time = datetime.utcnow().timestamp() - window_ms / 1000

        trades_in_window = [
            t for t in self.order_book.trades if t.timestamp.timestamp() >= cutoff_time
        ]

        if not trades_in_window:
            return None

        # Simple average of trade prices (time-weighted by equal spacing)
        total_price = sum(t.price for t in trades_in_window)
        return total_price / Decimal(str(len(trades_in_window)))


class MarketMechanicsEngine:
    """
    Complete market mechanics engine.

    Manages the full trading day including:
    - Pre-market period
    - Opening auction
    - Continuous trading
    - Closing auction
    - Post-market period

    This orchestrates all the different mechanisms as described in Harris.

    Attributes:
        symbol: Trading symbol
        order_book: Underlying limit order book
        current_phase: Current market phase
        sessions: Trading session definitions
        phase_history: History of phase transitions
    """

    def __init__(
        self,
        symbol: str,
        tick_size: float = 0.01,
        regular_session: Optional[TradingSession] = None,
    ):
        """
        Initialize the market mechanics engine.

        Args:
            symbol: Trading symbol
            tick_size: Minimum price increment
            regular_session: Regular trading session definition
        """
        self.symbol = symbol

        # Initialize order book
        self.order_book = LimitOrderBook(
            symbol=symbol,
            tick_size=Decimal(str(tick_size)),
        )

        # Initialize mechanisms
        self._continuous_trading = ContinuousTrading(self.order_book)
        self._opening_auction = None
        self._closing_auction = None

        # Session management
        self.regular_session = regular_session or TradingSession(
            name="Regular",
            start_time=time(9, 30),
            end_time=time(16, 0),
            opening_auction=True,
            closing_auction=True,
            is_continuous=True,
        )

        # Phase tracking
        self._current_phase = MarketPhase.CLOSED
        self._phase_history: List[PhaseTransition] = []

        logger.info(f"Initialized MarketMechanicsEngine for {symbol}")

    @property
    def current_phase(self) -> MarketPhase:
        """Get current market phase."""
        return self._current_phase

    @property
    def phase_history(self) -> List[PhaseTransition]:
        """Get phase transition history."""
        return list(self._phase_history)

    def transition_to(self, phase: MarketPhase, trigger: str = "MANUAL") -> None:
        """
        Transition to a new market phase.

        Args:
            phase: New phase to transition to
            trigger: What triggered the transition
        """
        if phase == self._current_phase:
            return

        # Exit current phase
        self._exit_phase(self._current_phase)

        # Record transition
        self._phase_history.append(
            PhaseTransition(
                from_phase=self._current_phase,
                to_phase=phase,
                timestamp=datetime.utcnow(),
                trigger=trigger,
            )
        )

        # Enter new phase
        self._current_phase = phase
        self._enter_phase(phase)

        logger.info(f"Transitioned {self.symbol} to {phase.value} (trigger: {trigger})")

    def submit_order(self, order: Order) -> List[Trade]:
        """
        Submit an order to the current mechanism.

        Args:
            order: Order to submit

        Returns:
            List of trades generated

        Raises:
            RuntimeError: If market is closed
        """
        if self._current_phase == MarketPhase.CLOSED:
            raise RuntimeError("Market is closed, cannot submit order")

        if self._current_phase in [MarketPhase.OPENING_AUCTION, MarketPhase.CLOSING_AUCTION]:
            # Route to auction
            auction = (
                self._opening_auction
                if self._current_phase == MarketPhase.OPENING_AUCTION
                else self._closing_auction
            )
            if auction:
                auction.submit_order(order)
                return []  # No trades until auction executes
            else:
                raise RuntimeError(f"Auction not initialized for {self._current_phase.value}")

        elif self._current_phase in [
            MarketPhase.PRE_MARKET,
            MarketPhase.CONTINUOUS_TRADING,
            MarketPhase.POST_MARKET,
        ]:
            # Route to continuous trading
            return self._continuous_trading.submit_order(order)

        else:
            raise RuntimeError(f"Cannot submit orders in {self._current_phase.value}")

    def execute_opening_auction(self) -> Optional[AuctionResult]:
        """Execute the opening auction."""
        if self._opening_auction is None:
            logger.warning("Opening auction not initialized")
            return None

        result = self._opening_auction.execute_auction()

        # Transition to continuous trading if successful
        if result.is_matched:
            # Add trades to order book history
            for _matched_id in result.matched_orders:
                # Orders would be marked as filled by auction
                pass

        return result

    def execute_closing_auction(self) -> Optional[AuctionResult]:
        """Execute the closing auction."""
        if self._closing_auction is None:
            logger.warning("Closing auction not initialized")
            return None

        return self._closing_auction.execute_auction()

    def get_market_snapshot(self) -> Dict[str, Any]:
        """Get comprehensive market state snapshot."""
        book_snapshot = self.order_book.get_snapshot()

        return {
            "symbol": self.symbol,
            "phase": self._current_phase.value,
            "order_book": {
                "best_bid": book_snapshot.best_bid,
                "best_ask": book_snapshot.best_ask,
                "spread": book_snapshot.spread,
                "mid_price": book_snapshot.mid_price,
                "bid_depth": book_snapshot.bid_depth,
                "ask_depth": book_snapshot.ask_depth,
                "total_bid_qty": book_snapshot.total_bid_quantity,
                "total_ask_qty": book_snapshot.total_ask_quantity,
            },
            "auction": (
                {
                    "opening_indicative_price": (
                        self._opening_auction.get_auction_indicative_price()
                        if self._opening_auction
                        else None
                    ),
                    "opening_indicative_volume": (
                        self._opening_auction.get_auction_indicative_volume()
                        if self._opening_auction
                        else None
                    ),
                    "opening_imbalance": (
                        self._opening_auction.get_order_imbalance()
                        if self._opening_auction
                        else None
                    ),
                }
                if self._current_phase == MarketPhase.OPENING_AUCTION
                else None
            ),
            "vwap": (
                self._continuous_trading.calculate_vwap()
                if self._current_phase == MarketPhase.CONTINUOUS_TRADING
                else None
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _enter_phase(self, phase: MarketPhase) -> None:
        """Handle entering a phase."""
        if phase == MarketPhase.OPENING_AUCTION:
            self._opening_auction = AuctionMechanism(
                symbol=self.symbol,
                auction_type=AuctionType.OPENING,
                order_book=self.order_book,
            )

        elif phase == MarketPhase.CLOSING_AUCTION:
            self._closing_auction = AuctionMechanism(
                symbol=self.symbol,
                auction_type=AuctionType.CLOSING,
                order_book=self.order_book,
            )

        elif phase == MarketPhase.CONTINUOUS_TRADING:
            self._continuous_trading.start()

    def _exit_phase(self, phase: MarketPhase) -> None:
        """Handle exiting a phase."""
        if phase == MarketPhase.CONTINUOUS_TRADING:
            self._continuous_trading.stop()


def create_market_mechanics_engine(
    symbol: str,
    tick_size: float = 0.01,
    open_time: Tuple[int, int] = (9, 30),
    close_time: Tuple[int, int] = (16, 0),
) -> MarketMechanicsEngine:
    """
    Factory function to create a MarketMechanicsEngine.

    Args:
        symbol: Trading symbol
        tick_size: Minimum price increment
        open_time: Regular session open time (hour, minute)
        close_time: Regular session close time (hour, minute)

    Returns:
        Configured MarketMechanicsEngine instance

    Example:
        >>> engine = create_market_mechanics_engine("AAPL")
        >>> engine.transition_to(MarketPhase.OPENING_AUCTION)
        >>> result = engine.execute_opening_auction()
        >>> print(f"Opening price: {result.auction_price}")
    """
    session = TradingSession(
        name="Regular",
        start_time=time(*open_time),
        end_time=time(*close_time),
    )

    return MarketMechanicsEngine(
        symbol=symbol,
        tick_size=tick_size,
        regular_session=session,
    )
