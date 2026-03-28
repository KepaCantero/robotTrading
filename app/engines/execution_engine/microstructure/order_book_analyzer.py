"""
Order Book Depth Analyzer

Implements Harris Rule 6.1: Analyze order book before executing orders.

This module provides comprehensive order book analysis including:
- Bid-ask spread calculation
- Book imbalance (buying vs selling pressure)
- Effective spread for specific order sizes
- Liquidity depth analysis
- Slope analysis for market impact prediction
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class OrderBookLevel:
    """Single order book level."""

    price: Decimal
    size: Decimal
    num_orders: int = 1


@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot."""

    symbol: str
    timestamp: pd.Timestamp
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]

    @property
    def best_bid(self) -> Optional[Decimal]:
        """Best bid price."""
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[Decimal]:
        """Best ask price."""
        return self.asks[0].price if self.asks else None

    @property
    def mid_price(self) -> Optional[Decimal]:
        """Mid price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None

    @property
    def spread(self) -> Optional[Decimal]:
        """Bid-ask spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None

    @property
    def spread_bps(self) -> Optional[Decimal]:
        """Spread in basis points."""
        if self.mid_price and self.spread:
            return (self.spread / self.mid_price) * Decimal("10000")
        return None


@dataclass
class BookAnalysisResult:
    """Result of order book analysis."""

    symbol: str
    timestamp: pd.Timestamp

    # Basic metrics
    spread_bps: Decimal
    mid_price: Decimal
    imbalance: Decimal  # -1 to 1, +1 = all bids, -1 = all asks

    # Depth metrics
    total_bid_depth: Decimal
    total_ask_depth: Decimal
    depth_imbalance: Decimal

    # Effective spreads for different sizes
    effective_spread_100: Optional[Decimal]  # For 100 shares
    effective_spread_1000: Optional[Decimal]  # For 1000 shares
    effective_spread_5000: Optional[Decimal]  # For 5000 shares

    # Slope metrics (price impact per share)
    bid_slope: Optional[float]
    ask_slope: Optional[float]

    # Liquidity quality
    liquidity_score: float  # 0-100, higher = better
    can_execute_immediately: bool
    recommended_max_size: Decimal


class OrderBookAnalyzer:
    """
    Order Book Depth Analyzer (Harris Rule 6.1).

    Analyzes order book depth before executing orders to estimate market impact
    and execution quality.
    """

    def __init__(
        self,
        min_levels: int = 5,
        max_levels: int = 20,
        min_liquidity_threshold: Optional[Decimal] = None,
    ):
        """
        Initialize analyzer.

        Args:
            min_levels: Minimum book levels to analyze
            max_levels: Maximum book levels to analyze
            min_liquidity_threshold: Minimum liquidity for immediate execution
        """
        if min_liquidity_threshold is None:
            min_liquidity_threshold = Decimal("10000")
        self.min_levels = min_levels
        self.max_levels = max_levels
        self.min_liquidity_threshold = min_liquidity_threshold

        logger.info(f"OrderBookAnalyzer initialized with {min_levels}-{max_levels} levels")

    def analyze_order_book(
        self,
        snapshot: OrderBookSnapshot,
        target_sizes: Optional[List[Decimal]] = None,
    ) -> BookAnalysisResult:
        """
        Analyze order book depth and quality.

        Args:
            snapshot: Order book snapshot
            target_sizes: Order sizes to calculate effective spreads for

        Returns:
            BookAnalysisResult with comprehensive analysis
        """
        if target_sizes is None:
            target_sizes = [Decimal("100"), Decimal("1000"), Decimal("5000")]

        # Basic spread metrics
        if snapshot.mid_price is None or snapshot.spread is None:
            raise ValueError("Invalid order book: missing bid/ask")

        spread_bps = snapshot.spread_bps or Decimal("0")

        # Calculate book imbalance
        imbalance = self._calculate_imbalance(snapshot)

        # Calculate depth metrics
        total_bid_depth = sum(level.size for level in snapshot.bids)
        total_ask_depth = sum(level.size for level in snapshot.asks)

        if total_bid_depth + total_ask_depth > 0:
            depth_imbalance = (total_bid_depth - total_ask_depth) / (
                total_bid_depth + total_ask_depth
            )
        else:
            depth_imbalance = Decimal("0")

        # Calculate effective spreads
        effective_spreads = {}
        for size in target_sizes:
            eff_spread = self._calculate_effective_spread(snapshot, size)
            effective_spreads[size] = eff_spread

        # Calculate slopes (impact per share)
        bid_slope, ask_slope = self._calculate_slopes(snapshot)

        # Calculate liquidity score
        liquidity_score = self._calculate_liquidity_score(snapshot)

        # Determine if can execute immediately
        can_execute_immediately = total_bid_depth >= self.min_liquidity_threshold

        # Recommend max size
        recommended_max_size = self._calculate_max_size(snapshot)

        return BookAnalysisResult(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            spread_bps=spread_bps,
            mid_price=snapshot.mid_price,
            imbalance=imbalance,
            total_bid_depth=total_bid_depth,
            total_ask_depth=total_ask_depth,
            depth_imbalance=depth_imbalance,
            effective_spread_100=effective_spreads.get(Decimal("100")),
            effective_spread_1000=effective_spreads.get(Decimal("1000")),
            effective_spread_5000=effective_spreads.get(Decimal("5000")),
            bid_slope=bid_slope,
            ask_slope=ask_slope,
            liquidity_score=liquidity_score,
            can_execute_immediately=can_execute_immediately,
            recommended_max_size=recommended_max_size,
        )

    def _calculate_imbalance(self, snapshot: OrderBookSnapshot) -> Decimal:
        """
        Calculate order book imbalance.

        Returns value between -1 and 1:
        - +1: All volume on bid side (extreme buying pressure)
        - 0: Balanced
        - -1: All volume on ask side (extreme selling pressure)
        """
        total_bid_volume = float(sum(level.size for level in snapshot.bids[:5]))
        total_ask_volume = float(sum(level.size for level in snapshot.asks[:5]))

        if total_bid_volume + total_ask_volume == 0:
            return Decimal("0")

        imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)

        return Decimal(str(imbalance))

    def _calculate_effective_spread(
        self,
        snapshot: OrderBookSnapshot,
        quantity: Decimal,
    ) -> Optional[Decimal]:
        """
        Calculate effective spread for crossing the book.

        The effective spread is the actual cost to buy/sell a specific quantity,
        walking through the order book levels.

        Args:
            snapshot: Order book snapshot
            quantity: Order quantity

        Returns:
            Effective spread in bps, or None if insufficient liquidity
        """
        if quantity <= 0:
            return Decimal("0")

        # Calculate for buy side (crossing asks)
        remaining = float(quantity)
        total_cost = 0.0

        for level in snapshot.asks:
            if remaining <= 0:
                break

            fill = min(remaining, float(level.size))
            total_cost += float(level.price) * fill
            remaining -= fill

        if remaining > 0:
            # Insufficient liquidity
            return None

        avg_price = Decimal(str(total_cost / float(quantity)))

        # Effective spread = (avg_execution_price - mid_price) / mid_price
        if snapshot.mid_price and snapshot.mid_price > 0:
            effective_spread = ((avg_price - snapshot.mid_price) / snapshot.mid_price) * Decimal(
                "10000"
            )
            return effective_spread

        return None

    def _calculate_slopes(
        self,
        snapshot: OrderBookSnapshot,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate order book slopes.

        The slope measures how quickly prices deteriorate as you go deeper
        into the book. Higher slope = higher market impact.

        Returns:
            Tuple of (bid_slope, ask_slope) in price per share
        """
        if len(snapshot.bids) < 2 or len(snapshot.asks) < 2:
            return None, None

        try:
            # Bid slope: price decrease per additional share
            bid_prices = [float(level.price) for level in snapshot.bids[:10]]
            bid_sizes = [float(level.size) for level in snapshot.bids[:10]]

            # Cumulative sizes
            bid_cumsum = np.cumsum(bid_sizes)

            # Linear regression of price vs cumulative size
            if len(bid_cumsum) > 1:
                bid_slope = -np.polyfit(bid_cumsum, bid_prices, 1)[0]  # Negative slope
            else:
                bid_slope = None

            # Ask slope: price increase per additional share
            ask_prices = [float(level.price) for level in snapshot.asks[:10]]
            ask_sizes = [float(level.size) for level in snapshot.asks[:10]]
            ask_cumsum = np.cumsum(ask_sizes)

            if len(ask_cumsum) > 1:
                ask_slope = np.polyfit(ask_cumsum, ask_prices, 1)[0]  # Positive slope
            else:
                ask_slope = None

            return bid_slope, ask_slope

        except (ValueError, TypeError) as e:
            logger.warning(f"Error calculating slopes: {e}")
            return None, None

    def _calculate_liquidity_score(self, snapshot: OrderBookSnapshot) -> float:
        """
        Calculate overall liquidity score (0-100).

        Higher score = better liquidity.
        """
        score = 0.0

        # 1. Spread score (tighter spread = better)
        if snapshot.spread_bps:
            spread_score = max(0, 100 - float(snapshot.spread_bps) / 2)  # 200 bps = 0 score
            score += spread_score * 0.3

        # 2. Depth score (more depth = better)
        total_depth = sum(level.size for level in snapshot.bids + snapshot.asks)
        depth_score = min(100, float(total_depth) / 10000)  # 1M shares = 100 score
        score += depth_score * 0.4

        # 3. Balance score (more balanced = better)
        imbalance = abs(float(self._calculate_imbalance(snapshot)))
        balance_score = (1 - imbalance) * 100
        score += balance_score * 0.3

        return min(100, score)

    def _calculate_max_size(self, snapshot: OrderBookSnapshot) -> Decimal:
        """
        Calculate recommended maximum order size.

        Based on not moving the market more than 1% from the mid price.
        """
        max_size = Decimal("0")
        target_price = snapshot.mid_price * Decimal("1.01")  # 1% above mid

        for level in snapshot.asks:
            if level.price <= target_price:
                max_size += level.size
            else:
                break

        # Conservative: use 50% of available liquidity at 1% impact
        return max_size * Decimal("0.5")

    def detect_liquidity_regime(
        self,
        historical_snapshots: List[OrderBookSnapshot],
        window_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Detect current liquidity regime.

        Classifies market conditions into:
        - HIGH_LIQUIDITY: Tight spreads, deep books
        - NORMAL: Typical conditions
        - LOW_LIQUIDITY: Wide spreads, shallow books
        - STRESS: Extremely poor liquidity
        """
        if len(historical_snapshots) < window_size:
            return {"regime": "INSUFFICIENT_DATA", "confidence": 0.0}

        recent_snapshots = historical_snapshots[-window_size:]

        # Calculate metrics
        avg_spread = np.mean([float(s.spread_bps or 0) for s in recent_snapshots])
        avg_depth = np.mean(
            [sum(level.size for level in s.bids + s.asks) for s in recent_snapshots]
        )

        # Determine regime
        if avg_spread < 5 and avg_depth > 100000:
            regime = "HIGH_LIQUIDITY"
            confidence = 0.9
        elif avg_spread < 10 and avg_depth > 50000:
            regime = "NORMAL"
            confidence = 0.8
        elif avg_spread < 25 and avg_depth > 10000:
            regime = "LOW_LIQUIDITY"
            confidence = 0.7
        else:
            regime = "STRESS"
            confidence = 0.9

        return {
            "regime": regime,
            "confidence": confidence,
            "avg_spread_bps": avg_spread,
            "avg_depth": avg_depth,
        }


# Global singleton
_order_book_analyzer: OrderBookAnalyzer = None


def get_order_book_analyzer(
    min_levels: int = 5,
    max_levels: int = 20,
    min_liquidity_threshold: Optional[Decimal] = None,
) -> OrderBookAnalyzer:
    """Get or create global OrderBookAnalyzer instance."""
    if min_liquidity_threshold is None:
        min_liquidity_threshold = Decimal("10000")
    global _order_book_analyzer
    if _order_book_analyzer is None:
        _order_book_analyzer = OrderBookAnalyzer(
            min_levels=min_levels,
            max_levels=max_levels,
            min_liquidity_threshold=min_liquidity_threshold,
        )

    return _order_book_analyzer
