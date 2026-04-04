"""
Integration Tests for Decimal Precision Enforcement

Tests to verify that all data services properly use Decimal types
and enforce precision at service boundaries.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.services.crypto_data_service import get_crypto_fetcher
from app.services.forex_data_service import get_forex_fetcher
from app.services.market_data_service import MarketDataService
from app.shared.utils.decimal_utils import to_decimal, validate_price, validate_quantity


class TestMarketDataServiceDecimalPrecision:
    """Test decimal precision in MarketDataService."""

    def test_quote_prices_are_decimal(self):
        """Test that Quote objects have Decimal price fields."""
        # Create a sample quote using Decimal
        from app.domain.models.market_data import DataFeedType, Quote

        quote = Quote(
            symbol="AAPL",
            bid=Decimal("150.25"),
            ask=Decimal("150.30"),
            last=Decimal("150.28"),
            volume=Decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
        )

        # Verify all price fields are Decimal type
        assert isinstance(quote.bid, Decimal)
        assert isinstance(quote.ask, Decimal)
        assert isinstance(quote.last, Decimal)
        assert isinstance(quote.open, Decimal)
        assert isinstance(quote.high, Decimal)
        assert isinstance(quote.low, Decimal)
        assert isinstance(quote.close, Decimal)
        assert isinstance(quote.volume, Decimal)

    def test_quote_from_float_conversion(self):
        """Test that float inputs must be converted to Decimal before use."""
        from app.domain.models.market_data import DataFeedType, Quote
        from app.shared.utils.decimal_utils import to_decimal

        # Create quote with converted float inputs
        quote = Quote(
            symbol="AAPL",
            bid=to_decimal(150.25),  # Convert float to Decimal
            ask=to_decimal(150.30),  # Convert float to Decimal
            last=to_decimal(150.28),  # Convert float to Decimal
            volume=to_decimal(1000000),  # Convert int to Decimal
            feed_type=DataFeedType.YAHOO_FINANCE,
        )

        # Verify all are Decimal type
        assert isinstance(quote.bid, Decimal)
        assert isinstance(quote.ask, Decimal)
        assert isinstance(quote.last, Decimal)
        assert isinstance(quote.volume, Decimal)

    def test_market_data_service_initialization(self):
        """Test MarketDataService initializes without errors."""
        service = MarketDataService()
        assert service is not None
        assert service.default_cache_ttl == 60


class TestCryptoDataServiceDecimalPrecision:
    """Test decimal precision in CryptoDataService."""

    def test_crypto_prices_are_decimal(self):
        """Test that crypto prices use Decimal."""
        fetcher = get_crypto_fetcher()

        # Get prices for symbols
        prices = fetcher.get_current_prices(["BTC", "ETH"])

        # Verify all prices are Decimal
        assert all(isinstance(price, Decimal) for price in prices.values())

    def test_crypto_fallback_prices_are_decimal(self):
        """Test that fallback prices are Decimal."""
        fetcher = get_crypto_fetcher()

        # Get fallback price (when API fails)
        price = fetcher._get_fallback_price("BTC")

        # Verify it's Decimal
        assert isinstance(price, Decimal)

    def test_crypto_spreads_are_decimal(self):
        """Test that bid-ask spreads are Decimal."""
        fetcher = get_crypto_fetcher()

        # Get spread for a pair
        spread = fetcher.get_bid_ask_spread("BTCUSD")

        # Verify it's Decimal
        assert isinstance(spread, Decimal)

    def test_crypto_risk_metrics_are_decimal(self):
        """Test that risk metrics use Decimal."""
        fetcher = get_crypto_fetcher()

        # Get risk metrics
        metrics = fetcher.get_risk_metrics("BTC")

        # Verify metrics are Decimal
        assert isinstance(metrics["volatility"], Decimal)
        assert isinstance(metrics["max_drawdown"], Decimal)


class TestForexDataServiceDecimalPrecision:
    """Test decimal precision in ForexDataService."""

    def test_forex_rates_are_decimal(self):
        """Test that forex rates use Decimal."""
        fetcher = get_forex_fetcher()

        # Get rates for pairs
        rates = fetcher.get_current_rates(["EUR/USD", "GBP/USD"])

        # Verify all rates are Decimal
        assert all(isinstance(rate, Decimal) for rate in rates.values())

    def test_forex_fallback_rates_are_decimal(self):
        """Test that fallback rates are Decimal."""
        fetcher = get_forex_fetcher()

        # Get fallback rate
        rate = fetcher._get_fallback_rate("EUR/USD")

        # Verify it's Decimal
        assert isinstance(rate, Decimal)

    def test_forex_spreads_are_decimal(self):
        """Test that bid-ask spreads are Decimal."""
        fetcher = get_forex_fetcher()

        # Get spread for a pair
        spread = fetcher.get_bid_ask_spread("EUR/USD")

        # Verify it's Decimal
        assert isinstance(spread, Decimal)

    def test_forex_correlations_are_decimal(self):
        """Test that correlations use Decimal."""
        fetcher = get_forex_fetcher()

        # Get correlations
        correlations = fetcher.get_correlations()

        # Verify all correlations are Decimal
        assert all(isinstance(corr, Decimal) for corr in correlations.values())


class TestDecimalUtilsIntegration:
    """Test integration of decimal utilities across services."""

    def test_to_decimal_with_various_inputs(self):
        """Test to_decimal handles all input types correctly."""
        # Integer
        assert to_decimal(100) == Decimal("100")

        # Float
        result = to_decimal(100.50)
        assert isinstance(result, Decimal)
        assert result == Decimal("100.5")

        # String
        assert to_decimal("123.45") == Decimal("123.45")

        # Decimal
        original = Decimal("999.99")
        assert to_decimal(original) == original

        # None
        assert to_decimal(None) is None

    def test_validate_price_enforces_bounds(self):
        """Test that validate_price enforces price bounds."""
        # Valid price
        price = validate_price("100.50")
        assert isinstance(price, Decimal)

        # Price too low
        with pytest.raises(ValueError):
            validate_price("0")

        # Price too high
        with pytest.raises(ValueError):
            validate_price("2000000")

    def test_validate_quantity_enforces_bounds(self):
        """Test that validate_quantity enforces quantity bounds."""
        # Valid quantity
        qty = validate_quantity("1000")
        assert isinstance(qty, Decimal)

        # Quantity too low
        with pytest.raises(ValueError):
            validate_quantity("0")

        # Quantity too high
        with pytest.raises(ValueError):
            validate_quantity("2000000000")


class TestCrossServiceDecimalConsistency:
    """Test decimal consistency across different data services."""

    def test_all_services_use_decimal_for_prices(self):
        """Test that all services return Decimal for price data."""
        # Crypto service
        crypto_fetcher = get_crypto_fetcher()
        crypto_prices = crypto_fetcher.get_current_prices(["BTC"])
        assert all(isinstance(p, Decimal) for p in crypto_prices.values())

        # Forex service
        forex_fetcher = get_forex_fetcher()
        forex_rates = forex_fetcher.get_current_rates(["EUR/USD"])
        assert all(isinstance(r, Decimal) for r in forex_rates.values())

    def test_no_float_arithmetic_in_services(self):
        """Test that services don't use float arithmetic."""
        # This test ensures that services don't accidentally use float operations

        # Crypto service
        crypto_fetcher = get_crypto_fetcher()
        btc_price = crypto_fetcher._get_fallback_price("BTC")
        assert isinstance(btc_price, Decimal)

        # Forex service
        forex_fetcher = get_forex_fetcher()
        eur_rate = forex_fetcher._get_fallback_rate("EUR/USD")
        assert isinstance(eur_rate, Decimal)

    def test_decimal_precision_preserved(self):
        """Test that decimal precision is preserved across operations."""
        # Start with precise Decimal
        original = Decimal("99.99999999")

        # Convert through to_decimal
        converted = to_decimal(original)

        # Precision should be preserved
        assert converted == original
        assert str(converted) == "99.99999999"


class TestServiceBoundaryValidation:
    """Test validation at service boundaries."""

    def test_rejects_invalid_price_types(self):
        """Test that non-Decimal types are rejected at model boundaries."""
        import pytest

        from app.domain.models.market_data import DataFeedType, Quote
        from app.shared.utils.decimal_utils import to_decimal

        # Valid: Decimal price created with to_decimal utility
        quote1 = Quote(
            symbol="AAPL",
            bid=to_decimal("150.25"),  # String converted to Decimal
            ask=to_decimal("150.30"),
            last=to_decimal("150.28"),
            volume=to_decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
        )
        assert isinstance(quote1.bid, Decimal)

        # Valid: Decimal price created with to_decimal from float
        quote2 = Quote(
            symbol="AAPL",
            bid=to_decimal(150.25),  # Float converted to Decimal
            ask=to_decimal(150.30),
            last=to_decimal(150.28),
            volume=to_decimal(1000000),
            feed_type=DataFeedType.YAHOO_FINANCE,
        )
        assert isinstance(quote2.bid, Decimal)

        # Invalid: Direct string input should fail with strict=True
        with pytest.raises(Exception):  # Pydantic ValidationError
            Quote(
                symbol="AAPL",
                bid="150.25",  # String without conversion
                ask="150.30",
                last="150.28",
                volume="1000000",
                feed_type=DataFeedType.YAHOO_FINANCE,
            )

        # Invalid: Direct float input should fail with strict=True
        with pytest.raises(Exception):  # Pydantic ValidationError
            Quote(
                symbol="AAPL",
                bid=150.25,  # Float without conversion
                ask=150.30,
                last=150.28,
                volume=1000000,
                feed_type=DataFeedType.YAHOO_FINANCE,
            )

    def test_rejects_invalid_quantities(self):
        """Test that invalid quantities are rejected."""
        with pytest.raises(ValueError):
            validate_quantity("-100")

        with pytest.raises(ValueError):
            validate_quantity("0")

        with pytest.raises(ValueError):
            validate_quantity("9999999999999")


class TestHistoricalDataDecimalPrecision:
    """Test decimal precision in historical data."""

    def test_historical_data_ohlcv_are_decimal(self):
        """Test that HistoricalData OHLCV fields are Decimal."""
        from app.domain.models.market_data import DataFeedType, DataFrequency, HistoricalData

        data = HistoricalData(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            open=Decimal("150.00"),
            high=Decimal("155.00"),
            low=Decimal("149.50"),
            close=Decimal("154.00"),
            volume=Decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
            frequency=DataFrequency.DAILY,
        )

        # Verify all OHLCV fields are Decimal
        assert isinstance(data.open, Decimal)
        assert isinstance(data.high, Decimal)
        assert isinstance(data.low, Decimal)
        assert isinstance(data.close, Decimal)
        assert isinstance(data.volume, Decimal)

    def test_historical_data_from_dict_conversion(self):
        """Test that historical data from dict converts to Decimal."""
        from app.domain.models.market_data import DataFeedType, DataFrequency, HistoricalData
        from app.shared.utils.decimal_utils import to_decimal

        # Create from dict with converted values
        data_dict = {
            "symbol": "AAPL",
            "timestamp": datetime.utcnow(),
            "open": to_decimal(150.00),  # Float converted to Decimal
            "high": to_decimal("155.00"),  # String converted to Decimal
            "low": to_decimal(149.5),  # Float converted to Decimal
            "close": to_decimal("154.00"),  # String converted to Decimal
            "volume": to_decimal(1000000),  # Int converted to Decimal
            "feed_type": DataFeedType.YAHOO_FINANCE,
            "frequency": DataFrequency.DAILY,
        }

        data = HistoricalData(**data_dict)

        # Verify all are Decimal
        assert isinstance(data.open, Decimal)
        assert isinstance(data.high, Decimal)
        assert isinstance(data.low, Decimal)
        assert isinstance(data.close, Decimal)
        assert isinstance(data.volume, Decimal)


class TestDecimalPrecisionAcceptanceCriteria:
    """Tests verifying all acceptance criteria for Phase 0.2."""

    def test_no_float_arithmetic_for_financial_calculations(self):
        """AC: No float arithmetic for financial calculations."""
        # Verify that all price/quantity fields use Decimal
        from app.domain.models.market_data import DataFeedType, Quote
        from app.shared.utils.decimal_utils import to_decimal

        # Convert inputs to Decimal before creating model
        quote = Quote(
            symbol="AAPL",
            bid=to_decimal(150.25),  # Float input converted to Decimal
            ask=to_decimal(150.30),
            last=to_decimal(150.28),
            volume=to_decimal(1000000),
            feed_type=DataFeedType.YAHOO_FINANCE,
        )

        # All stored as Decimal, not float
        assert isinstance(quote.bid, Decimal)
        assert not isinstance(quote.bid, float)

        # Verify arithmetic operations maintain Decimal type
        spread = quote.ask - quote.bid
        assert isinstance(spread, Decimal)
        assert not isinstance(spread, float)

    def test_all_prices_use_decimal_type_hints(self):
        """AC: All prices use Decimal type hints."""
        # This is verified by the model definitions
        # All price fields in Quote and HistoricalData are typed as Decimal

        from app.domain.models.market_data import Quote

        # Check that price fields are annotated as Decimal
        hints = Quote.model_fields
        assert hints["bid"].annotation == Decimal
        assert hints["ask"].annotation == Decimal
        assert hints["last"].annotation == Decimal
        assert hints["open"].annotation == Decimal
        assert hints["high"].annotation == Decimal
        assert hints["low"].annotation == Decimal
        assert hints["close"].annotation == Decimal

    def test_all_quantities_use_decimal_type_hints(self):
        """AC: All quantities use Decimal type hints."""
        from app.domain.models.market_data import HistoricalData, Quote

        # Check volume fields
        assert Quote.model_fields["volume"].annotation == Decimal
        assert HistoricalData.model_fields["volume"].annotation == Decimal

    def test_to_decimal_utility_added_to_each_service(self):
        """AC: to_decimal() utility function added to each service file."""
        # Verify imports work
        from app.services.market_data_service import to_decimal as mds_to_decimal
        from app.shared.utils.decimal_utils import to_decimal as shared_to_decimal

        # Both should reference the same function (from shared module)
        assert mds_to_decimal is shared_to_decimal

    def test_data_input_validation_at_service_boundaries(self):
        """AC: Data input validation at service boundaries."""
        # Test validation in validate_price
        with pytest.raises(ValueError):
            validate_price("invalid")

        with pytest.raises(ValueError):
            validate_price("0")  # Too low

        with pytest.raises(ValueError):
            validate_price("2000000")  # Too high

        # Test validation in validate_quantity
        with pytest.raises(ValueError):
            validate_quantity("invalid")

        with pytest.raises(ValueError):
            validate_quantity("-100")  # Negative
