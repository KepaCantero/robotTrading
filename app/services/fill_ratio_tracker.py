"""
TASK-MET-FILL-1: Order Fill Ratio Tracking Service.

Tracks order fill ratios to monitor execution quality and identify issues with order fills.
"""

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)


class FillMetrics:
    """Metrics for order fills."""

    def __init__(self, order_id: str, symbol: str):
        self.order_id = order_id
        self.symbol = symbol
        self.requested_quantity: Decimal = Decimal("0")
        self.filled_quantity: Decimal = Decimal("0")
        self.fill_ratio: float = 0.0
        self.requested_price: Decimal = Decimal("0")
        self.filled_price: Optional[Decimal] = None
        self.slippage: Optional[Decimal] = None
        self.status: OrderStatus = OrderStatus.PENDING
        self.timestamp: datetime = datetime.utcnow()
        self.fill_time_ms: Optional[float] = None


class FillRatioTracker:
    """
    TASK-MET-FILL-1: Tracks order fill ratios and execution quality.

    Monitors:
    - Fill ratio (filled quantity / requested quantity)
    - Slippage (difference between requested and filled price)
    - Fill times
    - Fill rates by symbol and order type
    """

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.fill_metrics: List[FillMetrics] = []
        self.metrics_by_symbol: Dict[str, List[FillMetrics]] = defaultdict(list)

    def track_order(self, order: Order) -> FillMetrics:
        """
        Track a new order and create metrics for it.

        Args:
            order: Order to track

        Returns:
            FillMetrics instance
        """
        metrics = FillMetrics(order.id, order.symbol)
        metrics.requested_quantity = order.quantity
        metrics.requested_price = order.price
        metrics.status = order.status

        self.fill_metrics.append(metrics)
        self.metrics_by_symbol[order.symbol].append(metrics)

        # Maintain history size
        if len(self.fill_metrics) > self.max_history:
            oldest = self.fill_metrics.pop(0)
            self.metrics_by_symbol[oldest.symbol] = [
                m for m in self.metrics_by_symbol[oldest.symbol] if m.order_id != oldest.order_id
            ]

        return metrics

    def record_fill(self, order_id: str, filled_quantity: Decimal, filled_price: Decimal) -> None:
        """
        Record fill for an order.

        Args:
            order_id: Order ID
            filled_quantity: Quantity filled
            filled_price: Price filled at
        """
        metrics = self.find_metrics(order_id)
        if metrics:
            metrics.filled_quantity = filled_quantity
            metrics.filled_price = filled_price
            metrics.fill_ratio = (
                float(filled_quantity / metrics.requested_quantity)
                if metrics.requested_quantity > 0
                else 0.0
            )

            if metrics.requested_price > 0:
                metrics.slippage = abs(filled_price - metrics.requested_price)
            metrics.status = OrderStatus.FILLED

    def record_partial_fill(
        self,
        order_id: str,
        filled_quantity: Decimal,
        filled_price: Decimal,
        new_status: OrderStatus,
    ) -> None:
        """
        Record partial fill for an order.

        Args:
            order_id: Order ID
            filled_quantity: Quantity filled
            filled_price: Price filled at
            new_status: New order status
        """
        metrics = self.find_metrics(order_id)
        if metrics:
            metrics.filled_quantity = filled_quantity
            metrics.filled_price = filled_price
            metrics.fill_ratio = (
                float(filled_quantity / metrics.requested_quantity)
                if metrics.requested_quantity > 0
                else 0.0
            )

            if metrics.requested_price > 0:
                metrics.slippage = abs(filled_price - metrics.requested_price)
            metrics.status = new_status

    def record_order_status(self, order_id: str, status: OrderStatus) -> None:
        """
        Update order status.

        Args:
            order_id: Order ID
            status: New status
        """
        metrics = self.find_metrics(order_id)
        if metrics:
            metrics.status = status

    def get_fill_ratio_stats(
        self, symbol: Optional[str] = None, last_n: int = 100
    ) -> Dict[str, Any]:
        """
        Get fill ratio statistics.

        Args:
            symbol: Optional symbol to filter by
            last_n: Number of recent orders to analyze

        Returns:
            Dictionary with fill ratio statistics
        """
        orders = self.metrics_by_symbol[symbol] if symbol else self.fill_metrics
        recent_orders = orders[-last_n:] if orders else []

        if not recent_orders:
            return {
                "total_orders": 0,
                "avg_fill_ratio": 0.0,
                "total_filled": 0,
                "total_partial": 0,
                "total_failed": 0,
                "avg_slippage": 0.0,
            }

        filled = [
            m
            for m in recent_orders
            if m.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]
        ]

        avg_fill_ratio = (
            sum(m.fill_ratio for m in recent_orders if m.fill_ratio > 0)
            / len([m for m in recent_orders if m.fill_ratio > 0])
            if any(m.fill_ratio > 0 for m in recent_orders)
            else 0.0
        )

        avg_slippage = (
            sum(float(m.slippage) for m in filled if m.slippage is not None)
            / len([m for m in filled if m.slippage is not None])
            if any(m.slippage is not None for m in filled)
            else 0.0
        )

        return {
            "total_orders": len(recent_orders),
            "avg_fill_ratio": round(avg_fill_ratio, 4),
            "total_filled": len([m for m in recent_orders if m.status == OrderStatus.FILLED]),
            "total_partial": len(
                [m for m in recent_orders if m.status == OrderStatus.PARTIALLY_FILLED]
            ),
            "total_rejected": len([m for m in recent_orders if m.status == OrderStatus.REJECTED]),
            "avg_slippage": round(avg_slippage, 6),
        }

    def find_metrics(self, order_id: str) -> Optional[FillMetrics]:
        """Find metrics for an order."""
        for metrics in reversed(self.fill_metrics):
            if metrics.order_id == order_id:
                return metrics
        return None


# Global tracker instance
_fill_tracker: Optional[FillRatioTracker] = None


def get_fill_ratio_tracker() -> FillRatioTracker:
    """Get global fill ratio tracker instance."""
    global _fill_tracker
    if _fill_tracker is None:
        _fill_tracker = FillRatioTracker()
    return _fill_tracker
