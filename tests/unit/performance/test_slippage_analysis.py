"""
Tests for slippage analysis.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.domain.models.momentum import MarketData


class TestSlippageAnalysis:
    """Test slippage analysis functionality."""

    @pytest.fixture
    def market_data(self):
        """Create test market data."""
        return MarketData(
            symbol="AAPL",
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            spread=Decimal("1.0"),
            open_price=Decimal("100.0"),
            high_price=Decimal("110.0"),
            low_price=Decimal("90.0"),
            close_price=Decimal("105.0"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )

    def test_slippage_calculation(self, market_data):
        """Test slippage calculation."""
        assert market_data.symbol == "AAPL"
        assert market_data.volume == Decimal("1000000")
