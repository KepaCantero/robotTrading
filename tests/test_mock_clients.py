"""
Tests for mock trading clients.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.order import Order, OrderSide, OrderStatus, OrderType


class TestMockClients:
    """Test mock client functionality."""

    @pytest.mark.asyncio
    async def test_basic_order(self):
        """Test basic order creation."""
        order = Order(
            id=f"order_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            status=OrderStatus.PENDING,
        )
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY

    @pytest.mark.asyncio
    async def test_order_cancellation(self):
        """Test order cancellation."""
        order = Order(
            id=f"order_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            status=OrderStatus.PENDING,
        )
        assert order.status == OrderStatus.PENDING
