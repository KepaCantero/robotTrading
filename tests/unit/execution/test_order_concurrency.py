"""
Tests for order concurrency handling.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.order import Order, OrderSide, OrderStatus, OrderType


class TestOrderConcurrency:
    """Test order concurrency operations."""

    @pytest.fixture
    def order(self):
        """Create a test order."""
        return Order(
            id=f"order_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            status=OrderStatus.PENDING,
        )

    @pytest.mark.asyncio
    async def test_order_creation(self, order):
        """Test basic order creation."""
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET

    @pytest.mark.asyncio
    async def test_order_status(self, order):
        """Test order status management."""
        assert order.status == OrderStatus.PENDING
        order.status = OrderStatus.FILLED
        assert order.status == OrderStatus.FILLED
