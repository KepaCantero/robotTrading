"""
Tests for market data integration.
"""

from datetime import datetime
from decimal import Decimal

from app.models.momentum import MarketData


class TestMarketDataModels:
    """Tests for market data models."""

    def test_quote_model_validation(self):
        """Test MarketData model validation."""
        market_data = MarketData(
            symbol="TEST_SYMBOL",
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            spread=Decimal("1.0"),
            open_price=Decimal("149.50"),
            high_price=Decimal("150.50"),
            low_price=Decimal("149.00"),
            close_price=Decimal("150.00"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )
        assert market_data.symbol == "TEST_SYMBOL"
        assert market_data.close_price == Decimal("150.00")
