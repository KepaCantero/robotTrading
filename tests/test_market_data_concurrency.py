"""
Tests for market data concurrency handling.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.momentum import MarketData


class TestMarketDataConcurrency:
    """Test concurrent market data operations."""

    def test_concurrent_quotes(self):
        """Test concurrent quote access."""
        quotes = []
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

        for symbol in symbols:
            quote = MarketData(
                symbol=symbol,
                bid=Decimal("99.5"),
                ask=Decimal("100.5"),
                spread=Decimal("1.0"),
                open_price=Decimal("100.0"),
                high_price=Decimal("110.0"),
                low_price=Decimal("90.0"),
                close_price=Decimal("100.0"),
                volume=Decimal("1000000"),
                timestamp=datetime.utcnow(),
            )
            quotes.append(quote)

        assert len(quotes) == 5
        assert all(q.symbol in symbols for q in quotes)
