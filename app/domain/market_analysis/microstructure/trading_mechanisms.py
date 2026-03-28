"""
Trading Mechanisms Module

This module implements different trading mechanism models from Maureen O'Hara's
"Market Microstructure Theory" (Chapter 2-3).

Key Concepts:
- Dealer markets and inventory management
- Auction mechanisms (single and double auctions)
- Continuous trading dynamics
- Market design comparison
- Execution quality across mechanisms

References:
- O'Hara, M. (1995) "Market Microstructure Theory", Chapters 2-3
- Madhavan, A. (1992) "Trading Mechanisms in Securities Markets"
- Domowitz, I. (1990) "The Structure of Trading Discrete Markets"
"""
from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MarketMechanism(Enum):
    """Types of market trading mechanisms"""

    DEALER = "DEALER"  # Over-the-counter, dealer sets prices
    SINGLE_AUCTION = "SINGLE_AUCTION"  # Call auction at specific times
    DOUBLE_AUCTION = "DOUBLE_AUCTION"  # Continuous double auction
    CONTINUOUS_LIMIT_ORDER_BOOK = "CONTINUOUS_LIMIT_ORDER_BOOK"  # Electronic limit order book


class AuctionType(Enum):
    """Auction types"""

    CALL_AUCTION = "CALL_AUCTION"  # Single price at discrete times
    CONTINUOUS_AUCTION = "CONTINUOUS_AUCTION"  # Continuous trading
    SEAL_BID = "SEAL_BID"  # One-time sealed bid


class OrderPriority(Enum):
    """Order priority rules (O'Hara 3.3)"""

    PRICE_PRIORITY = "PRICE_PRIORITY"  # Best price first
    TIME_PRIORITY = "TIME_PRIORITY"  # Earlier orders first
    SIZE_PRIORITY = "SIZE_PRIORITY"  # Larger orders first
    DISPLAY_PRIORITY = "DISPLAY_PRIORITY"  # Displayed vs hidden


@dataclass
class LimitOrder:
    """
    Represents a limit order in the order book

    Attributes:
        order_id: Unique identifier
        timestamp: Submission time
        side: BUY or SELL
        price: Limit price
        size: Order quantity
        is_hidden: Whether order is hidden (iceberg)
        participant_id: Trader identifier
    """

    order_id: str
    timestamp: datetime
    side: str
    price: Decimal
    size: Decimal
    is_hidden: bool = False
    participant_id: str | None = None

    def __lt__(self, other):
        """For priority queue ordering"""
        if self.side == "BUY":
            # Bids: higher price first, then earlier time
            if self.price != other.price:
                return self.price > other.price
            return self.timestamp < other.timestamp
        else:
            # Asks: lower price first, then earlier time
            if self.price != other.price:
                return self.price < other.price
            return self.timestamp < other.timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'order_id': self.order_id,
            'timestamp': self.timestamp.isoformat(),
            'side': self.side,
            'price': str(self.price),
            'size': str(self.size),
            'is_hidden': self.is_hidden,
            'participant_id': self.participant_id,
        }


@dataclass
class AuctionResult:
    """
    Result of an auction execution

    Attributes:
        auction_time: Time of auction
        clearing_price: Price at which trades executed
        total_volume: Total volume traded
        matched_orders: List of (buy_order, sell_order, size) tuples
        unfilled_buys: Remaining buy orders
        unfilled_sells: Remaining sell orders
        execution_efficiency: Measure of execution quality
    """

    auction_time: datetime
    clearing_price: Decimal
    total_volume: Decimal
    matched_orders: list[tuple[str, str, Decimal]]
    unfilled_buys: list[LimitOrder]
    unfilled_sells: list[LimitOrder]
    execution_efficiency: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'auction_time': self.auction_time.isoformat(),
            'clearing_price': str(self.clearing_price),
            'total_volume': str(self.total_volume),
            'matched_orders': [(b, s, str(v)) for b, s, v in self.matched_orders],
            'unfilled_buys': len(self.unfilled_buys),
            'unfilled_sells': len(self.unfilled_sells),
            'execution_efficiency': self.execution_efficiency,
        }


@dataclass
class DealerInventoryState:
    """
    Inventory state for a dealer market maker

    Based on O'Hara Chapter 2 analysis of dealer inventory management

    Attributes:
        timestamp: State timestamp
        inventory: Current inventory position (positive = long, negative = short)
        inventory_value: Value of inventory at mid-market
        inventory_risk: Risk measure of current inventory
        optimal_quotes: Calculated optimal bid/ask quotes
    """

    timestamp: datetime
    inventory: Decimal
    inventory_value: Decimal
    inventory_risk: float
    optimal_quotes: tuple[Decimal, Decimal]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'inventory': str(self.inventory),
            'inventory_value': str(self.inventory_value),
            'inventory_risk': self.inventory_risk,
            'optimal_bid': str(self.optimal_quotes[0]),
            'optimal_ask': str(self.optimal_quotes[1]),
        }


@dataclass
class ExecutionQuality:
    """
    Measures execution quality across mechanisms

    Attributes:
        mechanism: Trading mechanism used
        execution_time: Time to execution
        price_improvement: Price improvement vs midpoint
        fill_rate: Proportion of order filled
        market_impact: Price impact of execution
        quality_score: Composite quality score (0-100)
    """

    mechanism: MarketMechanism
    execution_time: timedelta
    price_improvement: float  # In bps
    fill_rate: float
    market_impact: float  # In bps
    quality_score: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'mechanism': self.mechanism.value,
            'execution_time_ms': self.execution_time.total_seconds() * 1000,
            'price_improvement_bps': self.price_improvement,
            'fill_rate': self.fill_rate,
            'market_impact_bps': self.market_impact,
            'quality_score': self.quality_score,
        }


class CallAuction:
    """
    Implements a single (call) auction mechanism

    In a call auction, orders are batched and executed at a single clearing price
    that maximizes trading volume (O'Hara 2.2)

    Used at market open/close and for trading halts
    """

    def __init__(
        self,
        price_tick: Optional[Decimal] = None,
        min_price_increment: Optional[Decimal] = None,
    ):
        """
        Initialize call auction

        Args:
            price_tick: Minimum price variation
            min_price_increment: Minimum price increment for iteration
        """
        if price_tick is None:
            price_tick = Decimal('0.01')
        if min_price_increment is None:
            min_price_increment = Decimal('0.01')
        logger.debug(
            "Initializing CallAuction",
            extra={
                "price_tick": str(price_tick),
                "min_price_increment": str(min_price_increment),
            },
        )
        self.price_tick = price_tick
        self.min_price_increment = min_price_increment
        self.buy_orders: list[LimitOrder] = []
        self.sell_orders: list[LimitOrder] = []

    def submit_order(self, order: LimitOrder) -> None:
        """Submit order to auction"""
        if order.side == "BUY":
            heapq.heappush(self.buy_orders, order)
        else:
            heapq.heappush(self.sell_orders, order)

    def calculate_clearing_price(self) -> tuple[Decimal | None, Decimal]:
        """
        Calculate market-clearing price

        The clearing price maximizes executable volume

        Returns:
            Tuple of (clearing_price, executable_volume)
        """
        if not self.buy_orders or not self.sell_orders:
            return None, Decimal('0')

        # Get sorted unique prices
        buy_prices = sorted({o.price for o in self.buy_orders}, reverse=True)
        sell_prices = sorted({o.price for o in self.sell_orders})

        # Find price range where trades can occur
        min_trade_price = min(sell_prices)
        max_trade_price = max(buy_prices)

        if min_trade_price > max_trade_price:
            # No overlap
            return None, Decimal('0')

        # Iterate through price range to find volume-maximizing price
        best_price = None
        max_volume = Decimal('0')

        # Check at each buy price and sell price, plus midpoint
        test_prices = set()
        test_prices.update(buy_prices)
        test_prices.update(sell_prices)

        # Add midpoints
        for i in range(len(buy_prices) - 1):
            for sell_price in sell_prices:
                midpoint = (buy_prices[i] + sell_price) / 2
                test_prices.add(midpoint)

        for test_price in sorted(test_prices):
            buy_volume = self._calculate_buy_volume_at_price(test_price)
            sell_volume = self._calculate_sell_volume_at_price(test_price)
            executable = min(buy_volume, sell_volume)

            if executable > max_volume:
                max_volume = executable
                best_price = Decimal(str(test_price))

        return best_price, max_volume

    def _calculate_buy_volume_at_price(self, price: Decimal) -> Decimal:
        """Calculate total buy volume at or above price"""
        return sum((o.size for o in self.buy_orders if o.price >= price), Decimal('0'))

    def _calculate_sell_volume_at_price(self, price: Decimal) -> Decimal:
        """Calculate total sell volume at or below price"""
        return sum((o.size for o in self.sell_orders if o.price <= price), Decimal('0'))

    def execute_auction(self) -> AuctionResult:
        """
        Execute the auction

        Returns:
            AuctionResult with execution details
        """
        logger.debug(
            "Executing call auction",
            extra={
                "buy_orders": len(self.buy_orders),
                "sell_orders": len(self.sell_orders),
            },
        )
        clearing_price, total_volume = self.calculate_clearing_price()

        if clearing_price is None or total_volume == 0:
            logger.warning(
                "No clearing price found - auction failed",
                extra={
                    "buy_orders": len(self.buy_orders),
                    "sell_orders": len(self.sell_orders),
                },
            )
            return AuctionResult(
                auction_time=datetime.now(),
                clearing_price=Decimal('0'),
                total_volume=Decimal('0'),
                matched_orders=[],
                unfilled_buys=self.buy_orders.copy(),
                unfilled_sells=self.sell_orders.copy(),
                execution_efficiency=0.0,
            )

        # Match orders at clearing price
        matched_orders = []
        remaining_buys = [o for o in self.buy_orders if o.price >= clearing_price]
        remaining_sells = [o for o in self.sell_orders if o.price <= clearing_price]

        # Match using price-time priority
        buy_idx = 0
        sell_idx = 0

        while buy_idx < len(remaining_buys) and sell_idx < len(remaining_sells):
            buy_order = remaining_buys[buy_idx]
            sell_order = remaining_sells[sell_idx]

            match_size = min(buy_order.size, sell_order.size)

            if match_size > 0:
                matched_orders.append(
                    (
                        buy_order.order_id,
                        sell_order.order_id,
                        match_size,
                    )
                )

                # Update sizes
                remaining_buys[buy_idx] = LimitOrder(
                    order_id=buy_order.order_id,
                    timestamp=buy_order.timestamp,
                    side=buy_order.side,
                    price=buy_order.price,
                    size=buy_order.size - match_size,
                    is_hidden=buy_order.is_hidden,
                    participant_id=buy_order.participant_id,
                )

                remaining_sells[sell_idx] = LimitOrder(
                    order_id=sell_order.order_id,
                    timestamp=sell_order.timestamp,
                    side=sell_order.side,
                    price=sell_order.price,
                    size=sell_order.size - match_size,
                    is_hidden=sell_order.is_hidden,
                    participant_id=sell_order.participant_id,
                )

                if remaining_buys[buy_idx].size == 0:
                    buy_idx += 1
                if remaining_sells[sell_idx].size == 0:
                    sell_idx += 1

        # Calculate execution efficiency
        total_order_volume = sum(o.size for o in self.buy_orders + self.sell_orders)
        efficiency = float(total_volume / max(total_order_volume, Decimal('1'))) * 100

        logger.info(
            "Call auction executed",
            extra={
                "clearing_price": float(clearing_price),
                "total_volume": float(total_volume),
                "matched_orders": len(matched_orders),
                "execution_efficiency": efficiency,
            },
        )
        return AuctionResult(
            auction_time=datetime.now(),
            clearing_price=clearing_price,
            total_volume=total_volume,
            matched_orders=matched_orders,
            unfilled_buys=[o for o in remaining_buys if o.size > 0]
            + [o for o in self.buy_orders if o.price < clearing_price],
            unfilled_sells=[o for o in remaining_sells if o.size > 0]
            + [o for o in self.sell_orders if o.price > clearing_price],
            execution_efficiency=efficiency,
        )


class ContinuousDoubleAuction:
    """
    Implements a continuous double auction (CDA) mechanism

    In a CDA, trades occur whenever a buy and sell order match
    (O'Hara 2.3)

    This is the standard mechanism for electronic limit order books
    """

    def __init__(
        self,
        price_tick: Optional[Decimal] = None,
    ):
        """
        Initialize continuous double auction

        Args:
            price_tick: Minimum price variation
        """
        if price_tick is None:
            price_tick = Decimal('0.01')
        logger.debug(
            "Initializing ContinuousDoubleAuction",
            extra={"price_tick": str(price_tick)},
        )
        self.price_tick = price_tick
        self.buy_book: list[LimitOrder] = []
        self.sell_book: list[LimitOrder] = []
        self.trade_history: list[dict] = []

    def submit_limit_order(self, order: LimitOrder) -> list[dict]:
        """
        Submit limit order and immediately execute if possible

        Args:
            order: Limit order to submit

        Returns:
            List of executed trades
        """
        trades = []

        if order.side == "BUY":
            # Check if can match with existing sells
            while self.sell_book and self.sell_book[0].price <= order.price and order.size > 0:
                best_sell = self.sell_book[0]

                match_size = min(order.size, best_sell.size)
                trade_price = best_sell.price  # Passive side gets price

                trades.append(
                    {
                        'timestamp': datetime.now(),
                        'buy_order_id': order.order_id,
                        'sell_order_id': best_sell.order_id,
                        'price': trade_price,
                        'size': match_size,
                        'side': 'BUY',
                    }
                )

                # Update sizes
                order.size -= match_size
                if best_sell.size > match_size:
                    best_sell.size -= match_size
                else:
                    heapq.heappop(self.sell_book)

            # If remaining order size, add to book
            if order.size > 0:
                heapq.heappush(self.buy_book, order)

        else:  # SELL
            # Check if can match with existing buys
            while self.buy_book and self.buy_book[0].price >= order.price and order.size > 0:
                best_buy = self.buy_book[0]

                match_size = min(order.size, best_buy.size)
                trade_price = best_buy.price

                trades.append(
                    {
                        'timestamp': datetime.now(),
                        'buy_order_id': best_buy.order_id,
                        'sell_order_id': order.order_id,
                        'price': trade_price,
                        'size': match_size,
                        'side': 'SELL',
                    }
                )

                order.size -= match_size
                if best_buy.size > match_size:
                    best_buy.size -= match_size
                else:
                    heapq.heappop(self.buy_book)

            if order.size > 0:
                heapq.heappush(self.sell_book, order)

        self.trade_history.extend(trades)
        return trades

    def submit_market_order(
        self,
        side: str,
        size: Decimal,
        order_id: str,
    ) -> list[dict]:
        """
        Submit market order (executes immediately)

        Args:
            side: BUY or SELL
            size: Order size
            order_id: Order identifier

        Returns:
            List of executed trades
        """
        trades = []
        remaining_size = size

        if side == "BUY":
            while remaining_size > 0 and self.sell_book:
                best_sell = self.sell_book[0]

                match_size = min(remaining_size, best_sell.size)

                trades.append(
                    {
                        'timestamp': datetime.now(),
                        'buy_order_id': order_id,
                        'sell_order_id': best_sell.order_id,
                        'price': best_sell.price,
                        'size': match_size,
                        'side': 'BUY',
                    }
                )

                remaining_size -= match_size
                if best_sell.size > match_size:
                    best_sell.size -= match_size
                else:
                    heapq.heappop(self.sell_book)

        else:  # SELL
            while remaining_size > 0 and self.buy_book:
                best_buy = self.buy_book[0]

                match_size = min(remaining_size, best_buy.size)

                trades.append(
                    {
                        'timestamp': datetime.now(),
                        'buy_order_id': best_buy.order_id,
                        'sell_order_id': order_id,
                        'price': best_buy.price,
                        'size': match_size,
                        'side': 'SELL',
                    }
                )

                remaining_size -= match_size
                if best_buy.size > match_size:
                    best_buy.size -= match_size
                else:
                    heapq.heappop(self.buy_book)

        self.trade_history.extend(trades)
        return trades

    def get_market_state(self) -> dict:
        """
        Get current market state

        Returns:
            Dictionary with best bid, best ask, and depth
        """
        best_bid = self.buy_book[0].price if self.buy_book else None
        best_ask = self.sell_book[0].price if self.sell_book else None

        total_bid_depth = sum(o.size for o in self.buy_book)
        total_ask_depth = sum(o.size for o in self.sell_book)

        return {
            'best_bid': str(best_bid) if best_bid else None,
            'best_ask': str(best_ask) if best_ask else None,
            'spread_bps': (
                float((best_ask - best_bid) / ((best_bid + best_ask) / 2) * 10000)
                if (best_bid and best_ask)
                else None
            ),
            'total_bid_depth': str(total_bid_depth),
            'total_ask_depth': str(total_ask_depth),
            'buy_orders': len(self.buy_book),
            'sell_orders': len(self.sell_book),
        }


class DealerMarket:
    """
    Implements a dealer (market maker) mechanism

    In dealer markets, dealers quote bid and ask prices and trade
    with all counterparties (O'Hara 2.1)

    Key concepts:
    - Inventory management
    - Adverse selection risk
    - Optimal quote setting
    """

    def __init__(
        self,
        initial_capital: Decimal,
        risk_aversion: float = 0.5,
        inventory_limit: Optional[Decimal] = None,
    ):
        """
        Initialize dealer market

        Args:
            initial_capital: Dealer's initial capital
            risk_aversion: Risk aversion parameter (0-1)
            inventory_limit: Maximum inventory position
        """
        if inventory_limit is None:
            inventory_limit = Decimal('10000')
        logger.debug(
            "Initializing DealerMarket",
            extra={
                "initial_capital": str(initial_capital),
                "risk_aversion": risk_aversion,
                "inventory_limit": str(inventory_limit),
            },
        )
        self.capital = initial_capital
        self.risk_aversion = risk_aversion
        self.inventory_limit = inventory_limit
        self.inventory = Decimal('0')
        self.inventory_value = Decimal('0')
        self.trade_history: list[dict] = []

    def calculate_optimal_quotes(
        self,
        current_price: Decimal,
        volatility: float,
        order_flow_imbalance: float,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate optimal bid and ask quotes

        Based on Ho and Stoll (1981) dealer model:
        - Base spread compensates for order processing costs
        - Inventory adjustment based on current position
        - Adverse selection adjustment based on information risk

        Args:
            current_price: Current market price
            volatility: Price volatility
            order_flow_imbalance: Current order imbalance

        Returns:
            Tuple of (optimal_bid, optimal_ask)
        """
        # Base spread (order processing cost)
        # Typically 1-2 ticks for liquid stocks
        base_spread = current_price * Decimal('0.001')  # 10 bps

        # Inventory adjustment
        # If long inventory, lower both quotes to encourage selling
        # If short inventory, raise both quotes to encourage buying
        inventory_adjustment = (
            self.inventory * Decimal(str(volatility)) * Decimal(str(self.risk_aversion))
        )

        # Adverse selection adjustment
        # Widen spread when order flow imbalance suggests informed trading
        adverse_selection_adjustment = (
            Decimal(str(abs(order_flow_imbalance))) * current_price * Decimal('0.0005')
        )

        # Calculate optimal quotes
        half_spread = (base_spread + adverse_selection_adjustment) / 2

        optimal_bid = current_price - half_spread - inventory_adjustment
        optimal_ask = current_price + half_spread - inventory_adjustment

        # Round to ticks
        tick = Decimal('0.01')
        optimal_bid = (optimal_bid / tick).quantize(Decimal('1')) * tick
        optimal_ask = (optimal_ask / tick).quantize(Decimal('1')) * tick

        return optimal_bid, optimal_ask

    def execute_trade(
        self,
        side: str,
        size: Decimal,
        price: Decimal,
        counterparty: str,
    ) -> bool:
        """
        Execute trade as dealer

        Args:
            side: BUY (dealer buys) or SELL (dealer sells)
            size: Trade size
            price: Execution price
            counterparty: Counterparty identifier

        Returns:
            True if trade executed, False if rejected
        """
        # Check inventory limit
        if side == "BUY":
            new_inventory = self.inventory + size
        else:
            new_inventory = self.inventory - size

        if abs(new_inventory) > self.inventory_limit:
            return False  # Would exceed inventory limit

        # Update inventory
        self.inventory = new_inventory

        # Update capital
        if side == "BUY":
            self.capital -= price * size
        else:
            self.capital += price * size

        # Record trade
        self.trade_history.append(
            {
                'timestamp': datetime.now(),
                'side': side,
                'size': size,
                'price': price,
                'counterparty': counterparty,
                'inventory': self.inventory,
                'capital': self.capital,
            }
        )

        return True

    def get_inventory_state(
        self,
        current_price: Decimal,
        volatility: float,
        order_flow_imbalance: float,
    ) -> DealerInventoryState:
        """
        Get current inventory state with optimal quotes

        Args:
            current_price: Current market price
            volatility: Price volatility
            order_flow_imbalance: Order flow imbalance

        Returns:
            DealerInventoryState
        """
        # Calculate inventory value
        self.inventory_value = self.inventory * current_price

        # Calculate inventory risk (standard deviation of inventory value)
        inventory_risk = abs(float(self.inventory)) * volatility

        # Get optimal quotes
        optimal_quotes = self.calculate_optimal_quotes(
            current_price, volatility, order_flow_imbalance
        )

        return DealerInventoryState(
            timestamp=datetime.now(),
            inventory=self.inventory,
            inventory_value=self.inventory_value,
            inventory_risk=inventory_risk,
            optimal_quotes=optimal_quotes,
        )


class TradingMechanismComparator:
    """
    Compares execution quality across different trading mechanisms

    Based on O'Hara Chapter 3 analysis of market design
    """

    def __init__(self):
        """Initialize comparator"""
        self.execution_history: Dict[MarketMechanism, list[ExecutionQuality]] = {
            mechanism: [] for mechanism in MarketMechanism
        }

    def calculate_execution_quality(
        self,
        mechanism: MarketMechanism,
        order_size: Decimal,
        execution_time: timedelta,
        execution_price: Decimal,
        midpoint_price: Decimal,
        fill_size: Decimal,
        pre_trade_price: Decimal,
        post_trade_price: Decimal,
    ) -> ExecutionQuality:
        """
        Calculate execution quality metrics

        Args:
            mechanism: Trading mechanism used
            order_size: Original order size
            execution_time: Time to execution
            execution_price: Average execution price
            midpoint_price: Market midpoint at order submission
            fill_size: Size actually filled
            pre_trade_price: Price before trade
            post_trade_price: Price after trade

        Returns:
            ExecutionQuality with metrics
        """
        # Price improvement vs midpoint (in bps)
        if mechanism in [MarketMechanism.DEALER, MarketMechanism.SINGLE_AUCTION]:
            # For dealer/auction, compare to midpoint
            price_improvement = float((midpoint_price - execution_price) / midpoint_price * 10000)
            if execution_price > midpoint_price:
                price_improvement *= -1
        else:
            # For continuous, compare to aggressive side
            price_improvement = 0  # Neutral baseline

        # Fill rate
        fill_rate = float(fill_size / max(order_size, Decimal('1')))

        # Market impact (O'Hara 3.5)
        # Temporary impact: deviation from midpoint
        # Permanent impact: price change after trade
        if pre_trade_price > 0 and post_trade_price > 0:
            permanent_impact = float((post_trade_price - pre_trade_price) / pre_trade_price * 10000)
        else:
            permanent_impact = 0.0

        # Composite quality score
        # Higher is better: fast execution, good price, high fill rate, low impact
        time_score = max(0, 100 - execution_time.total_seconds() * 10)
        price_score = 50 + price_improvement  # 50 baseline + improvement
        fill_score = fill_rate * 50
        impact_penalty = abs(permanent_impact) * 2

        quality_score = min(
            100, max(0, time_score * 0.3 + price_score * 0.4 + fill_score * 0.3 - impact_penalty)
        )

        return ExecutionQuality(
            mechanism=mechanism,
            execution_time=execution_time,
            price_improvement=price_improvement,
            fill_rate=fill_rate,
            market_impact=permanent_impact,
            quality_score=quality_score,
        )

    def compare_mechanisms(
        self,
        order_size: Decimal,
        current_price: Decimal,
        volatility: float,
    ) -> dict:
        """
        Compare expected execution quality across mechanisms

        Based on O'Hara's analysis of when each mechanism is preferred

        Args:
            order_size: Order size to execute
            current_price: Current market price
            volatility: Current volatility

        Returns:
            Dictionary with comparison results
        """
        results: dict[str, dict[str, float | str]] = {}

        # Dealer market
        # Best for: small orders, illiquid stocks
        dealer_score = 70
        dealer_notes = "Good for small orders in illiquid conditions"
        results['dealer'] = {
            'quality_score': dealer_score,
            'expected_cost_bps': 5.0,
            'expected_time_seconds': 1.0,
            'notes': dealer_notes,
        }

        # Single auction
        # Best for: opening/closing, large orders, after halts
        auction_score = 80 if float(order_size) > 10000 else 60
        auction_notes = "Best for large orders at open/close"
        results['single_auction'] = {
            'quality_score': auction_score,
            'expected_cost_bps': 2.0,
            'expected_time_seconds': 300,
            'notes': auction_notes,
        }

        # Continuous double auction
        # Best for: normal trading, immediate execution
        cda_score = 75
        cda_notes = "Standard mechanism for continuous trading"
        results['continuous_double_auction'] = {
            'quality_score': cda_score,
            'expected_cost_bps': 3.0,
            'expected_time_seconds': 0.5,
            'notes': cda_notes,
        }

        # Find best mechanism
        best_mechanism = max(results.keys(), key=lambda k: results[k]['quality_score'])

        return {
            'comparison': results,
            'best_mechanism': best_mechanism,
            'recommendation': self._generate_mechanism_recommendation(
                order_size, volatility, results
            ),
        }

    def _generate_mechanism_recommendation(
        self,
        order_size: Decimal,
        volatility: float,
        comparison: dict,
    ) -> str:
        """Generate recommendation for mechanism selection"""
        size_value = float(order_size)

        if size_value > 50000:
            return f"Large order ({size_value:.0f} shares): Use SINGLE_AUCTION or split order"
        elif size_value > 10000:
            return "Medium-large order: Consider SINGLE_AUCTION or algorithmic execution"
        elif volatility > 0.03:
            return f"High volatility ({volatility:.2%}): Use CONTINUOUS_DOUBLE_AUCTION for speed"
        else:
            return "Normal conditions: CONTINUOUS_DOUBLE_AUCTION recommended"


# Singleton instances
_call_auction: CallAuction | None = None
_continuous_auction: ContinuousDoubleAuction | None = None
_dealer_market: DealerMarket | None = None
_mechanism_comparator: TradingMechanismComparator | None = None


def get_call_auction(
    price_tick: Optional[Decimal] = None,
) -> CallAuction:
    """Get or create CallAuction instance"""
    if price_tick is None:
        price_tick = Decimal('0.01')
    global _call_auction
    if _call_auction is None:
        _call_auction = CallAuction(price_tick=price_tick)
    return _call_auction


def get_continuous_double_auction(
    price_tick: Optional[Decimal] = None,
) -> ContinuousDoubleAuction:
    """Get or create ContinuousDoubleAuction instance"""
    if price_tick is None:
        price_tick = Decimal('0.01')
    global _continuous_auction
    if _continuous_auction is None:
        _continuous_auction = ContinuousDoubleAuction(price_tick=price_tick)
    return _continuous_auction


def get_dealer_market(
    initial_capital: Optional[Decimal] = None,
    risk_aversion: float = 0.5,
) -> DealerMarket:
    """Get or create DealerMarket instance"""
    if initial_capital is None:
        initial_capital = Decimal('1000000')
    global _dealer_market
    if _dealer_market is None:
        _dealer_market = DealerMarket(
            initial_capital=initial_capital,
            risk_aversion=risk_aversion,
        )
    return _dealer_market


def get_mechanism_comparator() -> TradingMechanismComparator:
    """Get or create TradingMechanismComparator instance"""
    global _mechanism_comparator
    if _mechanism_comparator is None:
        _mechanism_comparator = TradingMechanismComparator()
    return _mechanism_comparator


__all__ = [
    "MarketMechanism",
    "AuctionType",
    "OrderPriority",
    "LimitOrder",
    "AuctionResult",
    "DealerInventoryState",
    "ExecutionQuality",
    "CallAuction",
    "ContinuousDoubleAuction",
    "DealerMarket",
    "TradingMechanismComparator",
    "get_call_auction",
    "get_continuous_double_auction",
    "get_dealer_market",
    "get_mechanism_comparator",
]
