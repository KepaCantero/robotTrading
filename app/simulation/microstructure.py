"""
Market Microstructure Analysis - Larry Harris's Order Flow and Liquidity Models

This module implements market microstructure concepts from Harris,
Chapter 10: "Market Information and Price Discovery" and Chapter 11:
"Liquidity and Liquidity Risk."

Key concepts implemented:
1. Order flow analysis
2. Market depth profiling
3. Liquidity provision
4. Order imbalance indicators
5. Price impact functions

Reference:
    Harris, L. (2003). Trading and Exchanges, Chapters 10-11.
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Tuple

import numpy as np

from .order_book import LimitOrderBook, Order, OrderSide, Trade

logger = logging.getLogger(__name__)


class OrderFlowDirection(Enum):
    """Direction of order flow."""

    BUY_PRESSURE = "BUY_PRESSURE"  # Net buying pressure
    SELL_PRESSURE = "SELL_PRESSURE"  # Net selling pressure
    BALANCED = "BALANCED"  # Balanced flow


class LiquidityRegime(Enum):
    """Liquidity regime classification."""

    HIGH = "HIGH"  # High liquidity, tight spreads
    NORMAL = "NORMAL"  # Normal liquidity
    LOW = "LOW"  # Low liquidity, wide spreads
    DRY = "DRY"  # Very low liquidity, dangerous


@dataclass
class OrderImbalance:
    """
    Order imbalance metrics.

    Order imbalance is a key predictor of short-term price movements
    as discussed in Harris Chapter 10.

    Attributes:
        symbol: Trading symbol
        timestamp: Measurement timestamp
        buy_volume: Total buy volume
        sell_volume: Total sell volume
        imbalance: Order imbalance (buy - sell)
        imbalance_ratio: Imbalance as ratio of total volume
        normalized_imbalance: Normalized imbalance (-1 to +1)
        direction: Flow direction
    """

    symbol: str
    timestamp: datetime
    buy_volume: Decimal
    sell_volume: Decimal
    imbalance: Decimal
    imbalance_ratio: Decimal
    normalized_imbalance: Decimal
    direction: OrderFlowDirection

    @property
    def is_biased(self) -> bool:
        """Check if flow is significantly biased (>20% imbalance)."""
        return abs(self.normalized_imbalance) > 0.2

    @property
    def bias_strength(self) -> str:
        """Get strength of bias as string."""
        abs_imb = abs(self.normalized_imbalance)
        if abs_imb > 0.5:
            return "STRONG"
        elif abs_imb > 0.3:
            return "MODERATE"
        elif abs_imb > 0.1:
            return "WEAK"
        else:
            return "NEUTRAL"


@dataclass
class PriceImpactFunction:
    """
    Price impact function parameters.

    Models how order flow affects prices.

    Attributes:
        function_type: Type of impact function
        temporary_impact: Temporary impact coefficient
        permanent_impact: Permanent impact coefficient
        decay_rate: Decay rate of temporary impact
        nonlinearity: Nonlinearity exponent
        fit_quality: Quality of fit (R^2)
        estimated_at: When parameters were estimated
    """

    function_type: str
    temporary_impact: float
    permanent_impact: float
    decay_rate: float
    nonlinearity: float
    fit_quality: float
    estimated_at: datetime

    def calculate_impact(
        self,
        order_size: float,
        participation_rate: float,
        time_horizon: float = 0,
    ) -> Tuple[float, float]:
        """
        Calculate price impact for an order.

        Args:
            order_size: Order size in shares
            participation_rate: Participation rate (order/ADV)
            time_horizon: Time horizon for temporary impact decay

        Returns:
            (temporary_impact, permanent_impact) as fractions of price

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 11,
            "The Illiquidity of Large Trades"
        """
        # Permanent impact: depends on participation rate
        if self.function_type == "power_law":
            perm = self.permanent_impact * (participation_rate**self.nonlinearity)
        elif self.function_type == "linear":
            perm = self.permanent_impact * participation_rate
        else:  # square_root
            perm = self.permanent_impact * np.sqrt(participation_rate)

        # Temporary impact: decays with time
        temp = self.temporary_impact * (participation_rate**self.nonlinearity)
        if time_horizon > 0:
            temp *= np.exp(-self.decay_rate * time_horizon)

        return temp, perm


@dataclass
class MarketMicrostructureMetrics:
    """
    Comprehensive market microstructure metrics.

    Attributes:
        symbol: Trading symbol
        timestamp: Measurement timestamp
        order_imbalance: Current order imbalance
        liquidity_regime: Current liquidity regime
        market_depth: Depth at various price levels
        spread_metrics: Spread-related metrics
        flow_toxicity: Order flow toxicity (0-1)
        price_discovery: Price discovery efficiency (0-100)
        volatility_ratio: Current vs historical volatility
        trading_intensity: Trades per minute
        share_turnover: Share turnover rate
    """

    symbol: str
    timestamp: datetime
    order_imbalance: OrderImbalance
    liquidity_regime: LiquidityRegime
    market_depth: Dict[str, float]
    spread_metrics: Dict[str, float]
    flow_toxicity: float
    price_discovery: float
    volatility_ratio: float
    trading_intensity: float
    share_turnover: float

    @property
    def is_toxic(self) -> bool:
        """Check if order flow is toxic (>0.6 toxicity)."""
        return self.flow_toxicity > 0.6

    @property
    def is_illiquid(self) -> bool:
        """Check if market is illiquid."""
        return self.liquidity_regime in [LiquidityRegime.LOW, LiquidityRegime.DRY]


class OrderFlowAnalyzer:
    """
    Order Flow Analyzer.

    Analyzes order flow to predict short-term price movements and
    identify trading opportunities as described in Harris Chapter 10.

    Key concepts:
    1. Order imbalance as price predictor
    2. Flow toxicity (informed vs uninformed trading)
    3. Flow momentum and mean reversion
    4. Institutional vs retail flow patterns

    Attributes:
        symbol: Trading symbol
        window_size: Window for flow calculations
        flow_history: History of order flow observations
    """

    def __init__(self, symbol: str, window_size: int = 100):
        """
        Initialize the order flow analyzer.

        Args:
            symbol: Trading symbol
            window_size: Size of rolling window for calculations
        """
        self.symbol = symbol
        self.window_size = window_size

        self._flow_history: deque = deque(maxlen=window_size)
        self._imbalance_history: deque = deque(maxlen=window_size)

        logger.debug(f"Initialized OrderFlowAnalyzer for {symbol}")

    def add_order(self, order: Order) -> None:
        """
        Add an order to the flow analysis.

        Args:
            order: Order to add
        """
        self._flow_history.append(
            {
                "timestamp": datetime.utcnow(),
                "side": order.side,
                "quantity": order.quantity,
                "price": order.price,
            }
        )

    def add_trade(self, trade: Trade) -> None:
        """
        Add a trade to the flow analysis.

        Args:
            trade: Trade to add
        """
        # Treat trade as flow in direction of aggressor
        self._flow_history.append(
            {
                "timestamp": trade.timestamp,
                "side": OrderSide.BUY if trade.is_buy_aggressor else OrderSide.SELL,
                "quantity": trade.quantity,
                "price": trade.price,
            }
        )

    def calculate_order_imbalance(self) -> Optional[OrderImbalance]:
        """
        Calculate current order imbalance.

        Returns:
            OrderImbalance metrics or None if insufficient data

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 10,
            "Order Imbalance and Price Movements"
        """
        if len(self._flow_history) == 0:
            return None

        # Sum buy and sell volume in window
        buy_volume = Decimal("0")
        sell_volume = Decimal("0")

        for flow in self._flow_history:
            if flow["side"] == OrderSide.BUY:
                buy_volume += flow["quantity"]
            else:
                sell_volume += flow["quantity"]

        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return None

        # Calculate imbalance metrics
        imbalance = buy_volume - sell_volume
        imbalance_ratio = imbalance / total_volume
        normalized_imbalance = imbalance_ratio * 2  # Scale to [-1, 1]

        # Determine direction
        if normalized_imbalance > 0.1:
            direction = OrderFlowDirection.BUY_PRESSURE
        elif normalized_imbalance < -0.1:
            direction = OrderFlowDirection.SELL_PRESSURE
        else:
            direction = OrderFlowDirection.BALANCED

        return OrderImbalance(
            symbol=self.symbol,
            timestamp=datetime.utcnow(),
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            imbalance=imbalance,
            imbalance_ratio=imbalance_ratio,
            normalized_imbalance=normalized_imbalance,
            direction=direction,
        )

    def calculate_flow_toxicity(self) -> float:
        """
        Calculate order flow toxicity.

        Toxicity measures the proportion of informed trading (toxic flow)
        vs uninformed trading (noise trader flow).

        Higher toxicity indicates more informed traders are active,
        which can be dangerous for liquidity providers.

        Returns:
            Toxicity score (0-1, where 1 is highly toxic)

        Reference:
            Easley, D., Lopez de Prado, M., & O'Hara, M. (2012).
            "Flow Toxicity and Liquidity in a High-Frequency World."
        """
        if len(self._flow_history) < 10:
            return 0.5  # Neutral

        # Calculate price changes and flow direction
        price_changes = []
        flow_directions = []

        prev_price = None
        for flow in self._flow_history:
            if prev_price is not None and flow["price"] is not None:
                price_change = float(flow["price"] - prev_price) / float(prev_price)
                price_changes.append(price_change)
                flow_directions.append(1 if flow["side"] == OrderSide.BUY else -1)
            prev_price = flow["price"]

        if len(price_changes) < 5:
            return 0.5

        # Calculate correlation between flow and subsequent price changes
        # High positive correlation = toxic (informed) flow
        if len(price_changes) >= 2:
            correlations = []
            for i in range(len(price_changes) - 1):
                if flow_directions[i] * price_changes[i + 1] > 0:
                    correlations.append(1)
                else:
                    correlations.append(0)

            if correlations:
                toxicity = np.mean(correlations)
                return max(0, min(1, toxicity))

        return 0.5

    def detect_informed_trading(self) -> bool:
        """
        Detect potential informed trading activity.

        Returns:
            True if informed trading is suspected
        """
        imbalance = self.calculate_order_imbalance()
        if imbalance is None:
            return False

        # Signs of informed trading:
        # 1. Strong sustained imbalance
        # 2. High toxicity
        # 3. Large trades

        toxicity = self.calculate_flow_toxicity()

        return imbalance.is_biased and toxicity > 0.6


class MarketDepthAnalyzer:
    """
    Market Depth Analyzer.

    Analyzes the depth and liquidity of the order book as described in
    Harris Chapter 11.

    Key concepts:
    1. Depth profiling at multiple price levels
    2. Liquidity-weighted price impact
    3. Concentration of liquidity
    4. Price elasticity of demand/supply

    Attributes:
        order_book: Reference to order book
        depth_levels: Number of depth levels to analyze
    """

    def __init__(self, order_book: LimitOrderBook, depth_levels: int = 10):
        """
        Initialize the market depth analyzer.

        Args:
            order_book: Order book to analyze
            depth_levels: Number of depth levels to track
        """
        self.order_book = order_book
        self.depth_levels = depth_levels

        self._depth_history: deque = deque(maxlen=1000)

        logger.debug(f"Initialized MarketDepthAnalyzer for {order_book.symbol}")

    def analyze_depth(self) -> Dict[str, float]:
        """
        Analyze current market depth.

        Returns:
            Dictionary with depth metrics

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 11,
            "Depth and Liquidity"
        """
        snapshot = self.order_book.get_snapshot(depth=self.depth_levels)

        # Calculate cumulative depth
        cumulative_bid_depth = sum(qty for _, qty in snapshot.bids)
        cumulative_ask_depth = sum(qty for _, qty in snapshot.asks)

        # Calculate depth at each level
        bid_depths = [float(qty) for _, qty in snapshot.bids[:5]]
        ask_depths = [float(qty) for _, qty in snapshot.asks[:5]]

        # Calculate depth concentration (Herfindahl-Hirschman Index)
        if bid_depths:
            total_bid_vol = sum(bid_depths)
            bid_hhi = sum((d / total_bid_vol) ** 2 for d in bid_depths) if total_bid_vol > 0 else 0
        else:
            bid_hhi = 0

        if ask_depths:
            total_ask_vol = sum(ask_depths)
            ask_hhi = sum((d / total_ask_vol) ** 2 for d in ask_depths) if total_ask_vol > 0 else 0
        else:
            ask_hhi = 0

        # Calculate average depth
        avg_bid_depth = np.mean(bid_depths) if bid_depths else 0
        avg_ask_depth = np.mean(ask_depths) if ask_depths else 0

        # Calculate depth imbalance
        depth_imbalance = (
            (cumulative_bid_depth - cumulative_ask_depth)
            / (cumulative_bid_depth + cumulative_ask_depth)
            if (cumulative_bid_depth + cumulative_ask_depth) > 0
            else 0
        )

        return {
            "total_bid_depth": float(cumulative_bid_depth),
            "total_ask_depth": float(cumulative_ask_depth),
            "total_depth": float(cumulative_bid_depth + cumulative_ask_depth),
            "avg_bid_depth_5": avg_bid_depth,
            "avg_ask_depth_5": avg_ask_depth,
            "bid_concentration": bid_hhi,
            "ask_concentration": ask_hhi,
            "depth_imbalance": depth_imbalance,
            "spread_bps": (
                float(snapshot.spread / snapshot.mid_price * 10000)
                if snapshot.spread and snapshot.mid_price
                else 0
            ),
            "bid_levels": len(snapshot.bids),
            "ask_levels": len(snapshot.asks),
        }

    def estimate_price_impact(
        self,
        order_size: float,
        side: OrderSide,
    ) -> float:
        """
        Estimate price impact for a given order size.

        Uses current order book depth to estimate how much price will move.

        Args:
            order_size: Order size in shares
            side: Order side

        Returns:
            Estimated price impact as fraction of price

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 11,
            "The Illiquidity of Large Trades"
        """
        snapshot = self.order_book.get_snapshot(depth=self.depth_levels)
        remaining_size = order_size
        total_cost = 0.0
        notional_value = 0.0

        levels = snapshot.bids if side == OrderSide.SELL else snapshot.asks

        for price, qty in levels:
            if remaining_size <= 0:
                break

            qty_float = float(qty)
            qty_used = min(remaining_size, qty_float)

            total_cost += float(price) * qty_used
            notional_value += float(price) * qty_used
            remaining_size -= qty_used

        if notional_value > 0:
            avg_price = total_cost / (order_size - remaining_size)
            mid = float(snapshot.mid_price) if snapshot.mid_price else avg_price

            if side == OrderSide.BUY:
                impact = (avg_price - mid) / mid
            else:
                impact = (mid - avg_price) / mid

            return max(0, impact)

        return 0.0

    def classify_liquidity_regime(self) -> LiquidityRegime:
        """
        Classify current liquidity regime.

        Returns:
            LiquidityRegime classification

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 11,
            "Liquidity and Liquidity Risk"
        """
        depth = self.analyze_depth()

        # Classify based on:
        # 1. Total depth
        # 2. Spread
        # 3. Depth concentration

        total_depth = depth["total_depth"]
        spread_bps = depth["spread_bps"]
        concentration = (depth["bid_concentration"] + depth["ask_concentration"]) / 2

        if spread_bps > 50 or total_depth < 100:
            return LiquidityRegime.DRY
        elif spread_bps > 20 or total_depth < 1000:
            return LiquidityRegime.LOW
        elif spread_bps < 5 and total_depth > 10000 and concentration < 0.3:
            return LiquidityRegime.HIGH
        else:
            return LiquidityRegime.NORMAL


class LiquidityProvider:
    """
    Liquidity Provider Strategy.

    Simulates a liquidity provider as described in Harris Chapter 11.
    Liquidity providers profit from the bid-ask spread but face
    adverse selection risk from informed traders.

    Key concepts:
    1. Passive liquidity provision
    2. Spread capture
    3. Adverse selection management
    4. Inventory risk control

    Attributes:
        symbol: Trading symbol
        max_position: Maximum inventory position
        risk_tolerance: Risk tolerance parameter
        target_spread_bps: Target spread in basis points
        min_profit_bps: Minimum profit per trade
        adverse_selection_threshold: Toxicity threshold for pausing
    """

    def __init__(
        self,
        symbol: str,
        max_position: Decimal = Decimal("10000"),
        risk_tolerance: float = 0.02,
        target_spread_bps: float = 10.0,
        min_profit_bps: float = 2.0,
        adverse_selection_threshold: float = 0.6,
    ):
        """
        Initialize the liquidity provider.

        Args:
            symbol: Trading symbol
            max_position: Maximum position size
            risk_tolerance: Risk tolerance
            target_spread_bps: Target spread
            min_profit_bps: Minimum profit per trade
            adverse_selection_threshold: Toxicity threshold for pausing
        """
        self.symbol = symbol
        self.max_position = max_position
        self.risk_tolerance = Decimal(str(risk_tolerance))
        self.target_spread_bps = Decimal(str(target_spread_bps))
        self.min_profit_bps = Decimal(str(min_profit_bps))
        self.adverse_selection_threshold = adverse_selection_threshold

        self._position = Decimal("0")
        self._pnl = Decimal("0")

        logger.debug(f"Initialized LiquidityProvider for {symbol}")

    @property
    def position(self) -> Decimal:
        """Get current position."""
        return self._position

    @property
    def pnl(self) -> Decimal:
        """Get current P&L."""
        return self._pnl

    def should_provide_liquidity(
        self,
        current_toxicity: float,
        current_spread_bps: float,
    ) -> bool:
        """
        Decide whether to provide liquidity.

        Args:
            current_toxicity: Current flow toxicity
            current_spread_bps: Current spread in bps

        Returns:
            True if should provide liquidity

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 11,
            "The Profitability of Liquidity Provision"
        """
        # Don't provide liquidity if toxicity is too high
        if current_toxicity > self.adverse_selection_threshold:
            return False

        # Don't provide liquidity if spread is too small (not worth the risk)
        if current_spread_bps < float(self.min_profit_bps):
            return False

        # Don't provide liquidity if position is at max
        if abs(self._position) >= self.max_position:
            return False

        return True

    def calculate_quotes(
        self,
        mid_price: Decimal,
        volatility: float,
        order_imbalance: Optional[float] = None,
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Decimal]:
        """
        Calculate bid and ask quotes.

        Args:
            mid_price: Current mid price
            volatility: Current volatility
            order_imbalance: Order imbalance (-1 to +1)

        Returns:
            (bid_price, ask_price, quote_size) or (None, None, 0) if not quoting

        Reference:
            Harris, L. (2003). Trading and Exchanges, Chapter 11,
            "Quote Setting"
        """
        # Adjust spread for volatility
        vol_adjustment = Decimal(str(volatility * 100))
        half_spread = self.target_spread_bps / 2 + vol_adjustment

        # Adjust for inventory (skew quotes against position)
        inventory_adjustment = (
            (self._position / self.max_position) * self.risk_tolerance * mid_price
        )

        # Adjust for order imbalance (widen spread on side with pressure)
        flow_adjustment = Decimal("0")
        if order_imbalance is not None:
            flow_adjustment = Decimal(str(abs(order_imbalance) * 5))

        # Calculate quotes
        bid_price = (
            mid_price - (half_spread / 10000) * mid_price - inventory_adjustment - flow_adjustment
        )
        ask_price = (
            mid_price + (half_spread / 10000) * mid_price - inventory_adjustment + flow_adjustment
        )

        # Calculate quote size based on position
        base_size = Decimal("100")
        if self._position > 0:
            # Reduce bid size when long
            bid_size = base_size * max(
                Decimal("0.1"), Decimal("1") - self._position / self.max_position
            )
            ask_size = base_size
        elif self._position < 0:
            # Reduce ask size when short
            bid_size = base_size
            ask_size = base_size * max(
                Decimal("0.1"), Decimal("1") + self._position / self.max_position
            )
        else:
            bid_size = ask_size = base_size

        # Return None for side that can't increase position
        if self._position >= self.max_position:
            bid_price = None
        if self._position <= -self.max_position:
            ask_price = None

        return bid_price, ask_price, max(bid_size, ask_size)

    def on_trade_executed(
        self,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
    ) -> None:
        """
        Handle a trade execution.

        Args:
            side: Side of trade (from LP's perspective)
            quantity: Quantity traded
            price: Execution price
        """
        # Update position
        if side == OrderSide.BUY:
            self._position += quantity
        else:
            self._position -= quantity

        # P&L will be realized when position is closed
        logger.debug(
            f"LP trade: {side.value} {quantity} @ {price}, " f"new position: {self._position}"
        )

    def mark_to_market(self, current_mid: Decimal) -> Decimal:
        """
        Mark position to market.

        Args:
            current_mid: Current mid price

        Returns:
            Unrealized P&L
        """
        if self._position == 0:
            unrealized_pnl = Decimal("0")
        else:
            # Simple mark-to-market
            unrealized_pnl = self._position * current_mid

        return self._pnl + unrealized_pnl


class MarketMicrostructureAnalyzer:
    """
    Complete market microstructure analysis.

    Combines all microstructure analysis components into a unified interface.

    Attributes:
        symbol: Trading symbol
        order_flow_analyzer: Order flow analyzer
        depth_analyzer: Market depth analyzer
    """

    def __init__(
        self,
        symbol: str,
        order_book: LimitOrderBook,
        flow_window: int = 100,
        depth_levels: int = 10,
    ):
        """
        Initialize the microstructure analyzer.

        Args:
            symbol: Trading symbol
            order_book: Order book to analyze
            flow_window: Window for flow calculations
            depth_levels: Depth levels to analyze
        """
        self.symbol = symbol

        self.order_flow_analyzer = OrderFlowAnalyzer(
            symbol=symbol,
            window_size=flow_window,
        )

        self.depth_analyzer = MarketDepthAnalyzer(
            order_book=order_book,
            depth_levels=depth_levels,
        )

        self._impact_function: Optional[PriceImpactFunction] = None

        logger.info(f"Initialized MarketMicrostructureAnalyzer for {symbol}")

    def update(self, order: Optional[Order] = None, trade: Optional[Trade] = None) -> None:
        """Update with new order or trade."""
        if order:
            self.order_flow_analyzer.add_order(order)
        if trade:
            self.order_flow_analyzer.add_trade(trade)

    def get_comprehensive_metrics(self) -> MarketMicrostructureMetrics:
        """Get comprehensive microstructure metrics."""
        # Order flow
        order_imbalance = self.order_flow_analyzer.calculate_order_imbalance()
        if order_imbalance is None:
            # Create neutral imbalance
            order_imbalance = OrderImbalance(
                symbol=self.symbol,
                timestamp=datetime.utcnow(),
                buy_volume=Decimal("0"),
                sell_volume=Decimal("0"),
                imbalance=Decimal("0"),
                imbalance_ratio=Decimal("0"),
                normalized_imbalance=Decimal("0"),
                direction=OrderFlowDirection.BALANCED,
            )

        # Depth
        depth_metrics = self.depth_analyzer.analyze_depth()

        # Liquidity regime
        liquidity_regime = self.depth_analyzer.classify_liquidity_regime()

        # Flow toxicity
        flow_toxicity = self.order_flow_analyzer.calculate_flow_toxicity()

        # Spread metrics
        spread_metrics = {
            "spread_bps": depth_metrics.get("spread_bps", 0),
            "relative_spread": depth_metrics.get("spread_bps", 0) / 100,
        }

        # Price discovery (simplified)
        price_discovery = min(
            100, max(0, 100 * (1 - flow_toxicity) * (1 - abs(order_imbalance.normalized_imbalance)))
        )

        # Volatility ratio (would need historical data)
        volatility_ratio = 1.0

        # Trading intensity
        trading_intensity = len(self.order_flow_analyzer._flow_history) / max(
            1, self.order_flow_analyzer.window_size
        )

        # Share turnover
        total_volume = float(order_imbalance.buy_volume + order_imbalance.sell_volume)
        share_turnover = total_volume / 1000000  # Normalized by 1M shares

        return MarketMicrostructureMetrics(
            symbol=self.symbol,
            timestamp=datetime.utcnow(),
            order_imbalance=order_imbalance,
            liquidity_regime=liquidity_regime,
            market_depth=depth_metrics,
            spread_metrics=spread_metrics,
            flow_toxicity=flow_toxicity,
            price_discovery=price_discovery,
            volatility_ratio=volatility_ratio,
            trading_intensity=trading_intensity,
            share_turnover=share_turnover,
        )


def create_market_microstructure_analyzer(
    symbol: str,
    order_book: LimitOrderBook,
) -> MarketMicrostructureAnalyzer:
    """
    Factory function to create a MarketMicrostructureAnalyzer.

    Args:
        symbol: Trading symbol
        order_book: Order book to analyze

    Returns:
        Configured MarketMicrostructureAnalyzer instance

    Example:
        >>> from app.simulation.order_book import create_limit_order_book
        >>> book = create_limit_order_book("AAPL")
        >>> analyzer = create_market_microstructure_analyzer("AAPL", book)
        >>> metrics = analyzer.get_comprehensive_metrics()
        >>> print(f"Liquidity: {metrics.liquidity_regime.value}")
        >>> print(f"Toxicity: {metrics.flow_toxicity:.2f}")
    """
    return MarketMicrostructureAnalyzer(
        symbol=symbol,
        order_book=order_book,
    )
