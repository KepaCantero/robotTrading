"""
Tests for Pydantic V2 migration.
"""

from datetime import datetime
from decimal import Decimal

from app.models.momentum import MarketData


class TestPydanticV2Migration:
    """Test Pydantic V2 migration compatibility."""

    def test_market_data_v2_validation(self):
        """Test market data validation with Pydantic V2."""
        market_data = MarketData(
            symbol="AAPL",
            bid=Decimal("149.5"),
            ask=Decimal("150.5"),
            spread=Decimal("1.0"),
            open_price=Decimal("150.0"),
            high_price=Decimal("151.0"),
            low_price=Decimal("149.0"),
            close_price=Decimal("150.0"),
            volume=Decimal("1000000"),
            timestamp=datetime.utcnow(),
        )
        assert market_data.symbol == "AAPL"
        assert market_data.volume == Decimal("1000000")
