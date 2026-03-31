"""
Order Pattern Analyzer for Regulatory Compliance.

Detects manipulative trading patterns that violate regulations:
- Layering: Multiple orders at same price to create false appearance
- Spoofing: Orders with intent to cancel before execution
- Excessive cancellation: High order-to-trade ratio
- Marking the close: Trading near close to influence closing price
- Momentum ignition: Rapid trading to trigger price movements

These patterns are prohibited under:
- USA: Dodd-Frank Act, SEC Rule 610
- EU: MiFID II Article 15 (market abuse)
- Spain: CNMV regulations

Reference:
    https://www.sec.gov/marketstructure
    https://www.esma.europa.eu/
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


@dataclass
class OrderRecord:
    """Record of an order for pattern analysis."""

    order_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: Decimal
    price: Decimal
    order_type: str  # MARKET, LIMIT, STOP, etc.
    timestamp: datetime
    cancelled: bool = False
    filled: bool = False
    fill_quantity: Optional[Decimal] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "order_type": self.order_type,
            "timestamp": self.timestamp.isoformat(),
            "cancelled": self.cancelled,
            "filled": self.filled,
            "fill_quantity": str(self.fill_quantity) if self.fill_quantity else None,
        }


@dataclass
class PatternAlert:
    """Alert for detected manipulative pattern."""

    pattern_type: str
    severity: str  # INFO, WARNING, CRITICAL
    symbol: str
    timestamp: datetime
    description: str
    orders_involved: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "pattern_type": self.pattern_type,
            "severity": self.severity,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "orders_involved": self.orders_involved,
        }


class OrderPatternAnalyzer:
    """
    Analyze order patterns for manipulative behavior.

    Detects:
    - Layering: Multiple orders at same price to create false appearance
    - Spoofing: Orders with intent to cancel before execution
    - Excessive cancellation: High order-to-trade ratio
    - Marking the close: Trading near close to influence closing price
    - Momentum ignition: Rapid trading to trigger price movements

    Usage:
        analyzer = OrderPatternAnalyzer()

        # Analyze order for suspicious patterns
        patterns = analyzer.analyze_order(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
        )

        if patterns:
            logger.warning(f"Suspicious patterns detected: {patterns}")

        # Record order for ongoing analysis
        analyzer.record_order(
            order_id="12345",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            order_type="LIMIT",
        )
    """

    # Thresholds for pattern detection
    LAYERING_THRESHOLD = 3  # Orders at same price level
    CANCELLATION_RATE_THRESHOLD = 0.8  # 80% cancellation rate
    RAPID_ORDER_THRESHOLD = 10  # Orders in 60 seconds
    CLOSE_PERIOD_MINUTES = 30  # Minutes before market close

    def __init__(self, lookback_orders: int = 1000):
        """
        Initialize order pattern analyzer.

        Args:
            lookback_orders: Number of orders to keep in memory
        """
        self.lookback_orders = lookback_orders

        # Order history
        self._orders: deque[OrderRecord] = deque(maxlen=lookback_orders)
        self._orders_by_symbol: dict[str, deque[OrderRecord]] = {}

        # Alert history
        self._alerts: list[PatternAlert] = []

        logger.info("OrderPatternAnalyzer initialized")

    def analyze_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        order_type: str,
    ) -> list[str]:
        """
        Analyze order for suspicious patterns.

        Args:
            symbol: Symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Order price
            order_type: Order type (MARKET, LIMIT, STOP, etc.)

        Returns:
            List of suspicious pattern names

        Examples:
            >>> analyzer = OrderPatternAnalyzer()
            >>> patterns = analyzer.analyze_order(
            ...     symbol="AAPL",
            ...     side="BUY",
            ...     quantity=Decimal("100"),
            ...     price=Decimal("150"),
            ...     order_type="LIMIT",
            ... )
            >>> patterns
            []
        """
        patterns = []

        # Check for layering
        if self._detect_layering(symbol, side, price):
            patterns.append("layering")

        # Check for excessive cancellation
        if self._detect_excessive_cancellation(symbol):
            patterns.append("excessive_cancellation")

        # Check for marking the close
        if self._detect_marking_close():
            patterns.append("marking_close")

        # Check for rapid ordering
        if self._detect_rapid_ordering(symbol):
            patterns.append("rapid_ordering")

        # Check for momentum ignition
        if self._detect_momentum_ignition(symbol):
            patterns.append("momentum_ignition")

        if patterns:
            logger.warning(f"Suspicious order patterns detected for {symbol}: {patterns}")

        return patterns

    def record_order(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        order_type: str,
    ) -> None:
        """
        Record order for pattern analysis.

        Args:
            order_id: Unique order identifier
            symbol: Symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Order price
            order_type: Order type
        """
        order = OrderRecord(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type,
            timestamp=utc_now(),
        )

        self._orders.append(order)

        # Update symbol index
        if symbol not in self._orders_by_symbol:
            self._orders_by_symbol[symbol] = deque(maxlen=self.lookback_orders)
        self._orders_by_symbol[symbol].append(order)

        logger.debug(f"Recorded order: {order_id} - {side} {quantity} {symbol} @ {price}")

    def record_cancellation(self, order_id: str) -> None:
        """
        Record that an order was cancelled.

        Args:
            order_id: Order ID that was cancelled
        """
        for order in self._orders:
            if order.order_id == order_id:
                order.cancelled = True
                logger.debug(f"Order cancelled: {order_id}")
                break

    def record_fill(
        self,
        order_id: str,
        fill_quantity: Decimal,
    ) -> None:
        """
        Record that an order was filled.

        Args:
            order_id: Order ID that was filled
            fill_quantity: Quantity filled
        """
        for order in self._orders:
            if order.order_id == order_id:
                order.filled = True
                order.fill_quantity = fill_quantity
                logger.debug(f"Order filled: {order_id} - {fill_quantity}")
                break

    def get_order_to_trade_ratio(self, symbol: Optional[str] = None) -> Decimal:
        """
        Calculate order-to-trade ratio.

        Args:
            symbol: Optional symbol filter

        Returns:
            Ratio of orders to fills
        """
        orders = list(self._orders_by_symbol.get(symbol, [])) if symbol else list(self._orders)

        if not orders:
            return Decimal("0")

        filled_count = sum(1 for o in orders if o.filled)
        cancelled_count = sum(1 for o in orders if o.cancelled)

        if filled_count == 0:
            return Decimal("1")  # All cancelled

        return Decimal(cancelled_count) / Decimal(len(orders))

    def get_alerts(
        self,
        pattern_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
    ) -> list[PatternAlert]:
        """
        Get pattern alerts.

        Args:
            pattern_type: Optional pattern type filter
            start_time: Optional start time filter

        Returns:
            List of pattern alerts
        """
        alerts = self._alerts

        if pattern_type:
            alerts = [a for a in alerts if a.pattern_type == pattern_type]

        if start_time:
            alerts = [a for a in alerts if a.timestamp >= start_time]

        return alerts

    def _detect_layering(
        self,
        symbol: str,
        side: str,
        price: Decimal,
        price_tolerance: Optional[Decimal] = None,
    ) -> bool:
        """
        Detect layering pattern.

        Layering: Multiple orders at same price level to create
        false appearance of demand/supply.

        Args:
            symbol: Symbol
            side: Order side
            price: Order price
            price_tolerance: Price tolerance for matching

        Returns:
            True if layering detected
        """
        if price_tolerance is None:
            price_tolerance = Decimal("0.01")
        symbol_orders = list(self._orders_by_symbol.get(symbol, []))

        if len(symbol_orders) < self.LAYERING_THRESHOLD:
            return False

        # Count orders at same price/side/symbol in recent history
        similar_count = 0

        for order in reversed(symbol_orders[-20:]):  # Last 20 orders
            if order.side == side:
                price_diff = abs(order.price - price)
                if price_diff <= price_tolerance:
                    similar_count += 1

        return similar_count >= self.LAYERING_THRESHOLD

    def _detect_spoofing(self, symbol: str) -> bool:
        """
        Detect spoofing pattern.

        Spoofing: Orders placed with intent to cancel before execution.

        Args:
            symbol: Symbol

        Returns:
            True if spoofing detected
        """
        symbol_orders = list(self._orders_by_symbol.get(symbol, []))

        if len(symbol_orders) < 10:
            return False

        # Look for high cancellation rate on large orders
        large_orders = [
            o for o in symbol_orders if o.quantity > Decimal("100")  # Arbitrary threshold
        ]

        if not large_orders:
            return False

        cancelled_large = sum(1 for o in large_orders if o.cancelled)

        return len(large_orders) > 5 and cancelled_large / len(large_orders) > 0.7

    def _detect_excessive_cancellation(self, symbol: str) -> bool:
        """
        Detect excessive order cancellation.

        Args:
            symbol: Symbol

        Returns:
            True if excessive cancellation detected
        """
        symbol_orders = list(self._orders_by_symbol.get(symbol, []))

        if len(symbol_orders) < 10:
            return False

        # Calculate cancellation rate
        cancelled = sum(1 for o in symbol_orders if o.cancelled)
        rate = Decimal(cancelled) / Decimal(len(symbol_orders))

        return rate > Decimal(str(self.CANCELLATION_RATE_THRESHOLD))

    def _detect_marking_close(self) -> bool:
        """
        Detect marking the close pattern.

        Marking the close: Trading near market close to influence
        the closing price.

        Returns:
            True if marking close detected
        """
        now = utc_now()
        current_time = now.time()

        # Check if near market close (last 30 minutes)
        # US market closes at 4:00 PM Eastern (21:00 UTC)
        if current_time.hour == 20 and current_time.minute >= 30:
            # Look for orders in last 5 minutes
            recent_orders = [o for o in self._orders if (now - o.timestamp).total_seconds() < 300]
            return len(recent_orders) > 5

        return False

    def _detect_rapid_ordering(self, symbol: str) -> bool:
        """
        Detect rapid ordering pattern.

        Args:
            symbol: Symbol

        Returns:
            True if rapid ordering detected
        """
        now = utc_now()
        symbol_orders = self._orders_by_symbol.get(symbol, [])

        # Count orders in last 60 seconds
        if not symbol_orders:
            return False

        # Count how many consecutive recent orders (within 60s) from the end
        recent_orders = list(reversed(symbol_orders))
        cutoff_idx = len(recent_orders)
        for i, order in enumerate(recent_orders):
            if (now - order.timestamp).total_seconds() > 60:
                cutoff_idx = i
                break

        return cutoff_idx > self.RAPID_ORDER_THRESHOLD

    def _detect_momentum_ignition(self, symbol: str) -> bool:
        """
        Detect momentum ignition pattern.

        Momentum ignition: Rapid trading to trigger price movements
        and automated responses.

        Args:
            symbol: Symbol

        Returns:
            True if momentum ignition detected
        """
        symbol_orders = list(self._orders_by_symbol.get(symbol, []))

        if len(symbol_orders) < 10:
            return False

        # Look for alternating buy/sell orders in rapid succession
        # This is simplified - real detection more complex
        recent = symbol_orders[-10:]
        side_changes = 0

        for i in range(1, len(recent)):
            if recent[i].side != recent[i - 1].side:
                side_changes += 1

        # High side changes with rapid ordering
        return side_changes >= 5 and self._detect_rapid_ordering(symbol)

    def reset(self) -> None:
        """Reset all tracking (for testing)."""
        self._orders.clear()
        self._orders_by_symbol.clear()
        self._alerts.clear()

        logger.info("OrderPatternAnalyzer reset")
