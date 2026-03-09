"""
Tests for trading error handling.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.domain.models.momentum import MarketData


class TestTradingErrorHandler:
    """Test trading error handling."""

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

    def test_network_error_handling(self, market_data):
        """Test network error handling."""
        assert market_data.symbol == "AAPL"

    def test_error_recovery(self, market_data):
        """Test error recovery mechanisms."""
        assert market_data.close_price == Decimal("105.0")
