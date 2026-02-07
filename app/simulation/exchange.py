"""
Exchange Simulation - Order Matching and Trade Execution

This module implements the exchange simulation as described in Harris,
Chapter 4: "Market Structure" and Chapter 6: "Dealer Markets."

Key concepts implemented:
1. Order matching engine with price-time priority
2. Trade execution with quality metrics
3. Market maker strategies
4. Spread optimization
5. Execution quality analysis

Reference:
    Harris, L. (2003). Trading and Exchanges, Chapters 4-6.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from .market_mechanics import MarketMechanicsEngine
from .order_book import LimitOrderBook, Order, OrderSide, OrderStatus, OrderType, Trade

logger = logging.getLogger(__name__)


class OrderMatchingAlgorithm(Enum):
    """Order matching algorithm."""

    PRICE_TIME = "PRICE_TIME"  # FIFO at each price level
    PRO_RATA = "PRO_RATA"  # Proportional allocation at each price
    SIZE_PRIORITY = "SIZE_PRIORITY"  # Larger orders get priority


class SpreadStrategy(Enum):
    """Market maker spread strategy."""

    FIXED_TICK = "FIXED_TICK"  # Fixed spread in ticks
    FIXED_PERCENT = "FIXED_PERCENT"  # Fixed percentage spread
    ADAPTIVE_VOLATILITY = "ADAPTIVE_VOLATILITY"  # Spread based on volatility
    ADAPTIVE_INVENTORY = "ADAPTIVE_INVENTORY"  # Spread based on inventory risk
    ADAPTIVE_FLOW = "ADAPTIVE_FLOW"  # Spread based on order flow


@dataclass
class ExecutionQuality:
    """
    Execution quality metrics.

    Measures how well orders were executed relative to benchmarks.
    Based on Harris's discussion of execution quality in Chapter 5.

    Attributes:
        order_id: Order being measured
        execution_price: Actual execution price
        benchmark_price: Benchmark price (arrival price, VWAP, etc.)
        effective_spread: Effective half-spread paid
        realized_spread: Realized spread after impact
        price_improvement: Amount of price improvement
        timing_cost: Cost due to timing delay
        market_impact: Cost due to market impact
        fill_rate: Percentage of order filled
        slippage: Price slippage from decision to execution
    """

    order_id: str
    execution_price: Decimal
    benchmark_price: Decimal
    effective_spread: Decimal
    realized_spread: Optional[Decimal] = None
    price_improvement: Decimal = Decimal("0")
    timing_cost: Decimal = Decimal("0")
    market_impact: Decimal = Decimal("0")
    fill_rate: Decimal = Decimal("100")
    slippage: Decimal = Decimal("0")

    @property
    def total_cost(self) -> Decimal:
        """Total execution cost relative to benchmark."""
        return self.execution_price - self.benchmark_price

    @property
    def cost_bps(self) -> Decimal:
        """Cost in basis points."""
        return (self.total_cost / self.benchmark_price) * Decimal("10000")


@dataclass
class TradeExecution:
    """
    A trade execution record.

    Attributes:
        execution_id: Unique execution ID
        order_id: Order that was executed
        symbol: Trading symbol
        side: Buy or sell
        quantity: Quantity executed
        price: Execution price
        timestamp: Execution timestamp
        venue: Execution venue
        liquidity_taker: True if order took liquidity
        commission: Execution commission
        fees: Additional fees
    """

    execution_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    venue: str = "SIMULATED_EXCHANGE"
    liquidity_taker: bool = True
    commission: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")


class OrderMatchingEngine:
    """
    Order Matching Engine.

    The core matching engine that implements the continuous double auction
    with price-time priority matching.

    Responsibilities:
    - Accept and validate orders
    - Match compatible orders
    - Generate trades
    - Maintain order book state
    - Track executions

    Attributes:
        order_book: Underlying limit order book
        algorithm: Matching algorithm to use
        trade_callback: Callback function for trades
    """

    def __init__(
        self,
        order_book: LimitOrderBook,
        algorithm: OrderMatchingAlgorithm = OrderMatchingAlgorithm.PRICE_TIME,
        trade_callback: Optional[Callable[[Trade], None]] = None,
    ):
        """
        Initialize the matching engine.

        Args:
            order_book: Underlying limit order book
            algorithm: Matching algorithm
            trade_callback: Optional callback for trade events
        """
        self.order_book = order_book
        self.algorithm = algorithm
        self.trade_callback = trade_callback

        self._executions: List[TradeExecution] = []

        logger.debug(
            f"Initialized OrderMatchingEngine for {order_book.symbol} "
            f"with {algorithm.value} algorithm"
        )

    @property
    def executions(self) -> List[TradeExecution]:
        """Get all executions."""
        return list(self._executions)

    def submit_order(self, order: Order) -> List[TradeExecution]:
        """
        Submit an order for execution.

        Args:
            order: Order to submit

        Returns:
            List of trade executions

        Raises:
            ValueError: If order validation fails
        """
        # Validate order
        self._validate_order(order)

        # Submit to order book
        trades = self.order_book.submit_order(order)

        # Generate execution records
        executions = []
        for trade in trades:
            execution = TradeExecution(
                execution_id=str(uuid.uuid4()),
                order_id=trade.buy_order_id if trade.is_buy_aggressor else trade.sell_order_id,
                symbol=trade.symbol,
                side=OrderSide.BUY if trade.is_buy_aggressor else OrderSide.SELL,
                quantity=trade.quantity,
                price=trade.price,
                timestamp=trade.timestamp,
                liquidity_taker=True,  # Aggressor takes liquidity
            )
            executions.append(execution)
            self._executions.append(execution)

            # Notify callback if set
            if self.trade_callback:
                self.trade_callback(trade)

        logger.debug(
            f"Executed order {order.order_id}: {len(executions)} fills, "
            f"{sum(e.quantity for e in executions)} total quantity"
        )

        return executions

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        return self.order_book.cancel_order(order_id)

    def get_execution_quality(
        self,
        order: Order,
        benchmark_price: Decimal,
    ) -> ExecutionQuality:
        """
        Calculate execution quality for an order.

        Args:
            order: Order that was executed
            benchmark_price: Benchmark price (e.g., arrival price)

        Returns:
            ExecutionQuality metrics
        """
        if order.status not in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
            raise ValueError(f"Order {order.order_id} not filled")

        execution_price = order.avg_fill_price or Decimal("0")

        # Calculate effective spread
        # Effective spread = 2 * |execution_price - mid_price| / mid_price
        # For buys: effective spread = execution_price - mid_price
        # For sells: effective spread = mid_price - execution_price
        if self.order_book.mid_price:
            if order.is_buy:
                effective_spread = execution_price - self.order_book.mid_price
            else:
                effective_spread = self.order_book.mid_price - execution_price
        else:
            effective_spread = Decimal("0")

        # Calculate price improvement
        price_improvement = Decimal("0")
        if order.price:
            if order.is_buy:
                improvement = order.price - execution_price
            else:
                improvement = execution_price - order.price
            if improvement > 0:
                price_improvement = improvement

        # Calculate fill rate
        fill_rate = (order.filled_quantity / order.quantity) * Decimal("100")

        # Calculate slippage
        slippage = execution_price - benchmark_price

        return ExecutionQuality(
            order_id=order.order_id,
            execution_price=execution_price,
            benchmark_price=benchmark_price,
            effective_spread=effective_spread,
            price_improvement=price_improvement,
            fill_rate=fill_rate,
            slippage=slippage,
        )

    def _validate_order(self, order: Order) -> None:
        """Validate an order before submission."""
        if order.quantity <= 0:
            raise ValueError(f"Order quantity must be positive: {order.quantity}")

        if order.order_type == OrderType.LIMIT and order.price is None:
            raise ValueError("Limit orders must have a price")

        if order.order_type == OrderType.STOP_MARKET and order.stop_price is None:
            raise ValueError("Stop market orders must have a stop price")

        if order.order_type == OrderType.STOP_LIMIT:
            if order.price is None or order.stop_price is None:
                raise ValueError("Stop limit orders must have both price and stop price")


class MarketMakerStrategy:
    """
    Market Maker Strategy.

    Implements market making behavior as described in Harris Chapter 6.
    Market makers provide liquidity by continuously quoting bid and ask prices.

    Key components:
    1. Quote generation
    2. Inventory management
    3. Risk control
    4. Spread optimization

    Attributes:
        symbol: Trading symbol
        max_position: Maximum position size
        risk_tolerance: Risk tolerance parameter
        spread_strategy: Spread calculation strategy
        base_spread_bps: Base spread in basis points
        inventory_target: Target inventory level
        volatility_window: Window for volatility calculation
    """

    def __init__(
        self,
        symbol: str,
        max_position: Decimal = Decimal("10000"),
        risk_tolerance: float = 0.02,
        spread_strategy: SpreadStrategy = SpreadStrategy.ADAPTIVE_VOLATILITY,
        base_spread_bps: float = 10.0,
        inventory_target: Decimal = Decimal("0"),
        volatility_window: int = 100,
    ):
        """
        Initialize the market maker strategy.

        Args:
            symbol: Trading symbol
            max_position: Maximum position size
            risk_tolerance: Risk tolerance (fraction of capital)
            spread_strategy: Spread calculation strategy
            base_spread_bps: Base spread in basis points
            inventory_target: Target inventory (usually 0 for neutral)
            volatility_window: Window for volatility calculation
        """
        self.symbol = symbol
        self.max_position = max_position
        self.risk_tolerance = Decimal(str(risk_tolerance))
        self.spread_strategy = spread_strategy
        self.base_spread_bps = Decimal(str(base_spread_bps))
        self.inventory_target = inventory_target
        self.volatility_window = volatility_window

        # State
        self._current_position = Decimal("0")
        self._price_history: List[Tuple[datetime, Decimal]] = []

        logger.debug(f"Initialized MarketMakerStrategy for {symbol}")

    @property
    def current_position(self) -> Decimal:
        """Get current inventory position."""
        return self._current_position

    def calculate_spread(
        self,
        current_price: Decimal,
        volatility: Optional[float] = None,
        order_imbalance: Optional[float] = None,
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate optimal bid and ask quotes.

        Implements various spread strategies from Harris:
        1. Fixed tick spread
        2. Fixed percentage spread
        3. Volatility-adjusted spread
        4. Inventory-adjusted spread
        5. Order flow-adjusted spread

        Args:
            current_price: Current mid price
            volatility: Current volatility (for adaptive strategies)
            order_imbalance: Current order imbalance (for flow strategies)

        Returns:
            (bid_price, ask_price) tuple

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 6,
            "Dealer Markets"
        """
        half_spread = self._calculate_half_spread(current_price, volatility, order_imbalance)

        # Adjust for inventory risk
        inventory_adjustment = self._calculate_inventory_adjustment(current_price)

        bid_price = current_price - half_spread + inventory_adjustment
        ask_price = current_price + half_spread + inventory_adjustment

        return bid_price, ask_price

    def update_position(self, quantity: Decimal, side: OrderSide) -> None:
        """
        Update inventory position after a trade.

        Args:
            quantity: Quantity traded
            side: Side of the trade (from MM's perspective)
        """
        if side == OrderSide.BUY:
            self._current_position += quantity
        else:
            self._current_position -= quantity

        logger.debug(f"Updated position: {self._current_position} " f"({side.value} {quantity})")

    def should_quote(self) -> bool:
        """
        Determine if market maker should quote.

        Market makers may pause quoting when:
        1. Position is at maximum
        2. Risk limits are breached
        3. Volatility is too high

        Returns:
            True if should quote, False otherwise
        """
        # Check position limits
        if abs(self._current_position) >= self.max_position:
            return False

        return True

    def get_quote_size(
        self,
        side: OrderSide,
        default_size: Decimal = Decimal("100"),
    ) -> Decimal:
        """
        Get appropriate quote size based on inventory.

        Args:
            side: Quote side
            default_size: Default quote size

        Returns:
            Recommended quote size
        """
        # Reduce size when approaching position limits
        position_ratio = abs(self._current_position) / self.max_position

        if position_ratio > 0.8:
            # Near limit, reduce size
            size = default_size * Decimal("0.25")
        elif position_ratio > 0.5:
            # Halfway to limit, moderate size
            size = default_size * Decimal("0.5")
        else:
            # Normal size
            size = default_size

        # Adjust for inventory skew
        if side == OrderSide.BUY:
            # Reduce buys if already long
            if self._current_position > 0:
                size *= max(
                    Decimal("0.1"), Decimal("1") - (self._current_position / self.max_position)
                )
        else:
            # Reduce sells if already short
            if self._current_position < 0:
                size *= max(
                    Decimal("0.1"), Decimal("1") + (self._current_position / self.max_position)
                )

        return max(Decimal("1"), size)  # Minimum size of 1

    def _calculate_half_spread(
        self,
        current_price: Decimal,
        volatility: Optional[float],
        order_imbalance: Optional[float],
    ) -> Decimal:
        """Calculate half-spread based on strategy."""
        if self.spread_strategy == SpreadStrategy.FIXED_TICK:
            # Fixed spread in ticks
            tick_size = Decimal("0.01")
            return tick_size * Decimal("2")  # 2 tick spread

        elif self.spread_strategy == SpreadStrategy.FIXED_PERCENT:
            # Fixed percentage spread
            return current_price * (self.base_spread_bps / Decimal("20000"))

        elif self.spread_strategy == SpreadStrategy.ADAPTIVE_VOLATILITY:
            # Volatility-adjusted spread
            # Higher volatility -> wider spread to compensate for risk
            if volatility is None:
                volatility = 0.01  # Default

            # Spread = k * volatility * price
            # Where k is calibrated to risk tolerance
            k = float(self.risk_tolerance) * 2
            return current_price * Decimal(str(k * volatility))

        elif self.spread_strategy == SpreadStrategy.ADAPTIVE_INVENTORY:
            # Inventory-adjusted spread
            # Widen spread when inventory is skewed to encourage unwinding
            inventory_skew = abs(self._current_position - self.inventory_target)
            base_half_spread = current_price * (self.base_spread_bps / Decimal("20000"))

            # Adjust based on inventory risk
            risk_multiplier = Decimal("1") + (inventory_skew / self.max_position) * Decimal("2")

            return base_half_spread * risk_multiplier

        elif self.spread_strategy == SpreadStrategy.ADAPTIVE_FLOW:
            # Order flow-adjusted spread
            if order_imbalance is None:
                order_imbalance = 0

            base_half_spread = current_price * (self.base_spread_bps / Decimal("20000"))

            # Widen spread when imbalance is high
            imbalance_adjustment = Decimal(str(abs(order_imbalance) * 2))
            return base_half_spread * (Decimal("1") + imbalance_adjustment)

        else:
            # Default to fixed percent
            return current_price * (self.base_spread_bps / Decimal("20000"))

    def _calculate_inventory_adjustment(self, current_price: Decimal) -> Decimal:
        """
        Calculate price adjustment based on inventory.

        When long, lower both prices to encourage selling
        When short, raise both prices to encourage buying

        Returns:
            Price adjustment (negative for long, positive for short)
        """
        inventory_risk = self._current_position - self.inventory_target
        adjustment = (inventory_risk / self.max_position) * current_price * self.risk_tolerance
        return -adjustment


class Exchange:
    """
    Exchange Simulation.

    Complete exchange implementation combining all components:
    - Order matching engine
    - Market makers
    - Market mechanics (auctions, continuous trading)
    - Execution quality tracking

    The exchange simulates realistic market behavior as described in Harris.

    Attributes:
        name: Exchange name
        order_book: Underlying limit order book
        matching_engine: Order matching engine
        market_mechanics: Market mechanics engine
        market_makers: List of market maker strategies
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        tick_size: float = 0.01,
        enable_market_making: bool = True,
        num_market_makers: int = 3,
    ):
        """
        Initialize the exchange.

        Args:
            name: Exchange name
            symbol: Trading symbol
            tick_size: Minimum price increment
            enable_market_making: Whether to simulate market makers
            num_market_makers: Number of market makers to simulate
        """
        self.name = name
        self.symbol = symbol

        # Initialize order book
        self.order_book = LimitOrderBook(
            symbol=symbol,
            tick_size=Decimal(str(tick_size)),
        )

        # Initialize matching engine
        self.matching_engine = OrderMatchingEngine(
            order_book=self.order_book,
        )

        # Initialize market mechanics
        self.market_mechanics = MarketMechanicsEngine(
            symbol=symbol,
            tick_size=tick_size,
        )

        # Initialize market makers
        self.market_makers: List[MarketMakerStrategy] = []
        if enable_market_making:
            for i in range(num_market_makers):
                # Use different spread strategies for diversity
                strategies = [
                    SpreadStrategy.FIXED_TICK,
                    SpreadStrategy.ADAPTIVE_VOLATILITY,
                    SpreadStrategy.ADAPTIVE_INVENTORY,
                ]
                mm = MarketMakerStrategy(
                    symbol=symbol,
                    spread_strategy=strategies[i % len(strategies)],
                    base_spread_bps=5.0 + i * 2,  # Varying base spreads
                )
                self.market_makers.append(mm)

        self._trades: List[Trade] = []

        logger.info(f"Initialized exchange '{name}' for {symbol}")

    @property
    def best_bid(self) -> Optional[Decimal]:
        """Get current best bid."""
        return self.order_book.best_bid

    @property
    def best_ask(self) -> Optional[Decimal]:
        """Get current best ask."""
        return self.order_book.best_ask

    @property
    def spread(self) -> Optional[Decimal]:
        """Get current bid-ask spread."""
        return self.order_book.spread

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Get current mid price."""
        return self.order_book.mid_price

    def submit_order(self, order: Order) -> List[TradeExecution]:
        """
        Submit an order to the exchange.

        Args:
            order: Order to submit

        Returns:
            List of trade executions
        """
        # Route through matching engine
        executions = self.matching_engine.submit_order(order)

        # Update market makers
        for execution in executions:
            for mm in self.market_makers:
                # Check if MM was counterparty
                if execution.venue == "SIMULATED_EXCHANGE":
                    # Simple simulation: randomly assign to MM
                    import random

                    if random.random() < 0.3:  # 30% chance MM was counterparty
                        mm.update_position(
                            execution.quantity,
                            OrderSide.SELL if execution.side == OrderSide.BUY else OrderSide.BUY,
                        )

        self._trades.extend(self.order_book.trades[-len(executions) :])

        return executions

    def get_market_maker_quotes(self) -> List[Tuple[Decimal, Decimal, Decimal]]:
        """
        Get current market maker quotes.

        Returns:
            List of (bid_price, ask_price, size) tuples
        """
        quotes = []
        mid = self.mid_price or Decimal("100")

        for mm in self.market_makers:
            if mm.should_quote():
                bid, ask = mm.calculate_spread(mid)
                size = mm.get_quote_size(OrderSide.BUY)
                quotes.append((bid, ask, size))

        return quotes

    def get_execution_statistics(self) -> Dict[str, any]:
        """Get execution statistics."""
        if not self._trades:
            return {
                "total_trades": 0,
                "total_volume": Decimal("0"),
                "avg_trade_size": Decimal("0"),
                "vwap": None,
            }

        total_volume = sum(t.quantity for t in self._trades)
        vwap = sum(t.price * t.quantity for t in self._trades) / total_volume

        return {
            "total_trades": len(self._trades),
            "total_volume": total_volume,
            "avg_trade_size": total_volume / Decimal(str(len(self._trades))),
            "vwap": vwap,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
        }


def create_exchange(
    name: str,
    symbol: str,
    tick_size: float = 0.01,
    num_market_makers: int = 3,
) -> Exchange:
    """
    Factory function to create an Exchange.

    Args:
        name: Exchange name
        symbol: Trading symbol
        tick_size: Minimum price increment
        num_market_makers: Number of market makers to simulate

    Returns:
        Configured Exchange instance

    Example:
        >>> exchange = create_exchange("NYSE", "AAPL")
        >>> order = Order(
        ...     order_id="123",
        ...     symbol="AAPL",
        ...     side=OrderSide.BUY,
        ...     order_type=OrderType.LIMIT,
        ...     quantity=Decimal("100"),
        ...     price=Decimal("150.00"),
        ... )
        >>> executions = exchange.submit_order(order)
    """
    return Exchange(
        name=name,
        symbol=symbol,
        tick_size=tick_size,
        enable_market_making=True,
        num_market_makers=num_market_makers,
    )
