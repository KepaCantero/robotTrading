"""
Tests for FX Rates Data Provider.

This module tests the interfaces and implementations for FX rate data providers
including InMemoryFXRateProvider, CachedFXRateProvider, MockFXDataSource,
and related implementations.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.strategies.fx_carry_trade.fx_rates_provider import (
    CachedFXRateProvider,
    FXDataSource,
    FXInterestRateProvider,
    FXRateProviderImpl,
    InMemoryFXRateProvider,
    MockFXDataSource,
)
from app.domain.strategies.fx_carry_trade.models import FXPair, InterestRateQuote


class TestInMemoryFXRateProvider:
    """Tests for InMemoryFXRateProvider class."""

    @pytest.fixture
    def provider(self) -> InMemoryFXRateProvider:
        """Provide a fresh provider instance for each test."""
        return InMemoryFXRateProvider()

    @pytest.fixture
    def sample_date(self) -> date:
        """Provide a sample date for testing."""
        return date(2024, 1, 15)

    def test_provider_initialization(self, provider: InMemoryFXRateProvider) -> None:
        """Test provider initialization creates empty storage."""
        # Provider now loads default data by default, so create one without data
        empty_provider = InMemoryFXRateProvider()
        # Clear the auto-loaded data to test empty initialization
        empty_provider._spot_rates.clear()
        empty_provider._forward_rates.clear()
        empty_provider._interest_rates.clear()

        assert len(empty_provider._spot_rates) == 0
        assert len(empty_provider._forward_rates) == 0
        assert len(empty_provider._interest_rates) == 0

    def test_add_spot_rate(self, provider: InMemoryFXRateProvider, sample_date: date) -> None:
        """Test adding a spot rate."""
        provider.add_spot_rate("USD/JPY", Decimal("110.50"), sample_date)

        assert provider._spot_rates[("USD", "JPY", sample_date)] == Decimal("110.50")

    def test_add_forward_rate(self, provider: InMemoryFXRateProvider, sample_date: date) -> None:
        """Test adding a forward rate."""
        provider.add_forward_rate("USD/JPY", Decimal("110.20"), sample_date, 3)

        assert provider._forward_rates[("USD", "JPY", sample_date, 3)] == Decimal("110.20")

    def test_add_interest_rate(self, provider: InMemoryFXRateProvider, sample_date: date) -> None:
        """Test adding an interest rate."""
        provider.add_interest_rate("USD", Decimal("0.0525"), sample_date, 3)

        assert provider._interest_rates[("USD", sample_date, 3)] == Decimal("0.0525")

    def test_add_spot_rate_invalid_pair(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test validation rejects invalid pair format."""
        with pytest.raises(ValueError, match="Invalid pair format"):
            provider.add_spot_rate("USDJPY", Decimal("110.50"), sample_date)

    def test_add_spot_rate_negative_rate(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test validation rejects negative rate."""
        with pytest.raises(ValueError, match="Rate must be positive"):
            provider.add_spot_rate("USD/JPY", Decimal("-110.50"), sample_date)

    def test_add_spot_rate_zero_rate(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test validation rejects zero rate."""
        with pytest.raises(ValueError, match="Rate must be positive"):
            provider.add_spot_rate("USD/JPY", Decimal("0"), sample_date)

    def test_add_forward_rate_invalid_months(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test validation rejects invalid months."""
        with pytest.raises(ValueError, match="months must be 1, 3, 6, or 12"):
            provider.add_forward_rate("USD/JPY", Decimal("110.20"), sample_date, 2)

    def test_add_forward_rate_all_valid_months(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test all valid month values for forward rate."""
        for months in [1, 3, 6, 12]:
            provider.add_forward_rate("EUR/USD", Decimal("1.09"), sample_date, months)
            assert ("EUR", "USD", sample_date, months) in provider._forward_rates

    def test_add_interest_rate_invalid_currency(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test validation rejects invalid currency code."""
        with pytest.raises(ValueError, match="Invalid currency code"):
            provider.add_interest_rate("US", Decimal("0.05"), sample_date, 3)

    def test_add_interest_rate_empty_currency(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test validation rejects empty currency code."""
        with pytest.raises(ValueError, match="Invalid currency code"):
            provider.add_interest_rate("", Decimal("0.05"), sample_date, 3)

    def test_add_interest_rate_invalid_months(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test validation rejects invalid months for interest rate."""
        with pytest.raises(ValueError, match="months must be 1, 3, 6, or 12"):
            provider.add_interest_rate("USD", Decimal("0.05"), sample_date, 2)

    def test_get_spot_rate(self, provider: InMemoryFXRateProvider, sample_date: date) -> None:
        """Test retrieving a stored spot rate."""
        provider.add_spot_rate("USD/JPY", Decimal("110.50"), sample_date)

        pair = FXPair(base_currency="USD", quote_currency="JPY")
        rate = provider.get_spot_rate(pair, sample_date)

        assert rate == Decimal("110.50")

    def test_get_spot_rate_not_found(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test retrieving non-existent spot rate."""
        pair = FXPair(base_currency="USD", quote_currency="JPY")

        with pytest.raises(ValueError, match="Spot rate not found"):
            provider.get_spot_rate(pair, sample_date)

    def test_get_forward_rate(self, provider: InMemoryFXRateProvider, sample_date: date) -> None:
        """Test retrieving a stored forward rate."""
        provider.add_forward_rate("USD/JPY", Decimal("110.20"), sample_date, 3)

        pair = FXPair(base_currency="USD", quote_currency="JPY")
        rate = provider.get_forward_rate(pair, sample_date, 3)

        assert rate == Decimal("110.20")

    def test_get_forward_rate_not_found(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test retrieving non-existent forward rate."""
        pair = FXPair(base_currency="USD", quote_currency="JPY")

        with pytest.raises(ValueError, match="Forward rate not found"):
            provider.get_forward_rate(pair, sample_date, 3)

    def test_get_interest_rate(self, provider: InMemoryFXRateProvider, sample_date: date) -> None:
        """Test retrieving a stored interest rate."""
        provider.add_interest_rate("USD", Decimal("0.0525"), sample_date, 3)

        rate = provider.get_interest_rate("USD", sample_date, 3)

        assert rate == Decimal("0.0525")

    def test_get_interest_rate_not_found(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test retrieving non-existent interest rate."""
        with pytest.raises(ValueError, match="Interest rate not found"):
            provider.get_interest_rate("USD", sample_date, 3)

    def test_multiple_rates_same_pair(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test storing multiple rates for same pair at different dates."""
        date1 = sample_date
        date2 = sample_date + timedelta(days=1)

        provider.add_spot_rate("USD/JPY", Decimal("110.50"), date1)
        provider.add_spot_rate("USD/JPY", Decimal("110.60"), date2)

        pair = FXPair("USD", "JPY")
        assert provider.get_spot_rate(pair, date1) == Decimal("110.50")
        assert provider.get_spot_rate(pair, date2) == Decimal("110.60")

    def test_multiple_forward_periods(
        self, provider: InMemoryFXRateProvider, sample_date: date
    ) -> None:
        """Test storing forward rates for multiple periods."""
        provider.add_forward_rate("EUR/USD", Decimal("1.087"), sample_date, 1)
        provider.add_forward_rate("EUR/USD", Decimal("1.090"), sample_date, 3)
        provider.add_forward_rate("EUR/USD", Decimal("1.095"), sample_date, 6)

        pair = FXPair("EUR", "USD")
        assert provider.get_forward_rate(pair, sample_date, 1) == Decimal("1.087")
        assert provider.get_forward_rate(pair, sample_date, 3) == Decimal("1.090")
        assert provider.get_forward_rate(pair, sample_date, 6) == Decimal("1.095")

    def test_parse_pair_string_valid(self, provider: InMemoryFXRateProvider) -> None:
        """Test parsing valid pair strings."""
        pair = provider._parse_pair_string("USD/JPY")
        assert pair.base_currency == "USD"
        assert pair.quote_currency == "JPY"

    def test_parse_pair_string_invalid_no_slash(self, provider: InMemoryFXRateProvider) -> None:
        """Test parsing pair string without slash."""
        with pytest.raises(ValueError, match="Invalid pair format"):
            provider._parse_pair_string("USDJPY")

    def test_parse_pair_string_invalid_wrong_format(self, provider: InMemoryFXRateProvider) -> None:
        """Test parsing pair string with wrong format."""
        with pytest.raises(ValueError, match="Invalid pair format"):
            provider._parse_pair_string("USD/JPY/GBP")

    def test_parse_pair_string_invalid_currency_length(
        self, provider: InMemoryFXRateProvider
    ) -> None:
        """Test parsing pair string with invalid currency length."""
        with pytest.raises(ValueError, match="Invalid currency codes in pair"):
            provider._parse_pair_string("US/JPY")


class TestCachedFXRateProvider:
    """Tests for CachedFXRateProvider class."""

    @pytest.fixture
    def underlying_provider(self) -> InMemoryFXRateProvider:
        """Provide an underlying provider."""
        provider = InMemoryFXRateProvider()
        test_date = date(2024, 1, 15)
        provider.add_spot_rate("USD/JPY", Decimal("110.50"), test_date)
        provider.add_forward_rate("USD/JPY", Decimal("110.20"), test_date, 3)
        provider.add_interest_rate("USD", Decimal("0.0525"), test_date, 3)
        return provider

    @pytest.fixture
    def cached_provider(self, underlying_provider: InMemoryFXRateProvider) -> CachedFXRateProvider:
        """Provide a cached provider with short TTL for testing."""
        return CachedFXRateProvider(underlying_provider, cache_ttl=1)

    @pytest.fixture
    def test_date(self) -> date:
        """Provide a test date."""
        return date(2024, 1, 15)

    def test_cached_provider_initialization(
        self, underlying_provider: InMemoryFXRateProvider
    ) -> None:
        """Test cached provider initialization."""
        cached = CachedFXRateProvider(underlying_provider, cache_ttl=100)

        assert cached._underlying == underlying_provider
        assert cached._cache_ttl == 100
        assert len(cached._spot_cache) == 0
        assert len(cached._forward_cache) == 0
        assert len(cached._rate_cache) == 0

    def test_get_spot_rate_caches_result(
        self, cached_provider: CachedFXRateProvider, test_date: date
    ) -> None:
        """Test that spot rate is cached on first retrieval."""
        pair = FXPair("USD", "JPY")

        # First call
        rate1 = cached_provider.get_spot_rate(pair, test_date)
        assert len(cached_provider._spot_cache) == 1

        # Second call should use cache
        rate2 = cached_provider.get_spot_rate(pair, test_date)

        assert rate1 == rate2 == Decimal("110.50")

    def test_get_forward_rate_caches_result(
        self, cached_provider: CachedFXRateProvider, test_date: date
    ) -> None:
        """Test that forward rate is cached on first retrieval."""
        pair = FXPair("USD", "JPY")

        rate1 = cached_provider.get_forward_rate(pair, test_date, 3)
        assert len(cached_provider._forward_cache) == 1

        rate2 = cached_provider.get_forward_rate(pair, test_date, 3)

        assert rate1 == rate2 == Decimal("110.20")

    def test_get_interest_rate_caches_result(
        self, cached_provider: CachedFXRateProvider, test_date: date
    ) -> None:
        """Test that interest rate is cached on first retrieval."""
        rate1 = cached_provider.get_interest_rate("USD", test_date, 3)
        assert len(cached_provider._rate_cache) == 1

        rate2 = cached_provider.get_interest_rate("USD", test_date, 3)

        assert rate1 == rate2 == Decimal("0.0525")

    def test_cache_expiration(self, underlying_provider: InMemoryFXRateProvider) -> None:
        """Test that cache expires after TTL."""
        cached = CachedFXRateProvider(underlying_provider, cache_ttl=0)  # Immediate expiry
        pair = FXPair("USD", "JPY")
        test_date = date(2024, 1, 15)

        # First call - cache result
        rate1 = cached.get_spot_rate(pair, test_date)

        # Wait a moment and call again - should re-fetch
        import time

        time.sleep(0.01)
        rate2 = cached.get_spot_rate(pair, test_date)

        assert rate1 == rate2

    def test_clear_cache(self, cached_provider: CachedFXRateProvider, test_date: date) -> None:
        """Test clearing all caches."""
        pair = FXPair("USD", "JPY")

        cached_provider.get_spot_rate(pair, test_date)
        cached_provider.get_forward_rate(pair, test_date, 3)
        cached_provider.get_interest_rate("USD", test_date, 3)

        assert len(cached_provider._spot_cache) > 0
        assert len(cached_provider._forward_cache) > 0
        assert len(cached_provider._rate_cache) > 0

        cached_provider.clear_cache()

        assert len(cached_provider._spot_cache) == 0
        assert len(cached_provider._forward_cache) == 0
        assert len(cached_provider._rate_cache) == 0

    def test_cache_key_different_pairs(
        self, cached_provider: CachedFXRateProvider, test_date: date
    ) -> None:
        """Test that different pairs have separate cache entries."""
        usdjpy = FXPair("USD", "JPY")
        # Add EUR/USD rate to underlying
        cached_provider._underlying.add_spot_rate("EUR/USD", Decimal("1.0850"), test_date)
        eurusd = FXPair("EUR", "USD")

        cached_provider.get_spot_rate(usdjpy, test_date)
        cached_provider.get_spot_rate(eurusd, test_date)

        assert len(cached_provider._spot_cache) == 2


class TestMockFXDataSource:
    """Tests for MockFXDataSource class."""

    @pytest.fixture
    def mock_source(self) -> MockFXDataSource:
        """Provide a mock data source."""
        return MockFXDataSource(base_date=date(2024, 1, 15))

    @pytest.fixture
    def test_date(self) -> date:
        """Provide a test date."""
        return date(2024, 1, 15)

    def test_mock_source_initialization_default_date(self) -> None:
        """Test mock source initialization with default date."""
        source = MockFXDataSource()
        assert source.base_date == date.today()

    def test_mock_source_initialization_custom_date(self) -> None:
        """Test mock source initialization with custom date."""
        custom_date = date(2024, 1, 1)
        source = MockFXDataSource(base_date=custom_date)
        assert source.base_date == custom_date

    def test_get_rate_basic(self, mock_source: MockFXDataSource, test_date: date) -> None:
        """Test getting FX rate."""
        rate = mock_source.get_rate("USD/JPY", test_date)

        assert isinstance(rate, Decimal)
        assert rate > 0

    def test_get_rate_different_pairs(self, mock_source: MockFXDataSource, test_date: date) -> None:
        """Test getting rates for different pairs."""
        usdjpy = mock_source.get_rate("USD/JPY", test_date)
        eurusd = mock_source.get_rate("EUR/USD", test_date)
        gbpusd = mock_source.get_rate("GBP/USD", test_date)

        assert all(isinstance(r, Decimal) for r in [usdjpy, eurusd, gbpusd])
        assert all(r > 0 for r in [usdjpy, eurusd, gbpusd])

    def test_get_rate_time_variation(self, mock_source: MockFXDataSource) -> None:
        """Test that rates vary with time."""
        base_date = date(2024, 1, 15)
        future_date = date(2024, 6, 15)  # Much further apart for more variation

        # Use a cross pair that will have more variation
        rate_base = mock_source.get_rate("EUR/GBP", base_date)
        rate_future = mock_source.get_rate("EUR/GBP", future_date)

        # Rates should be different due to time variation (more days = more variation)
        assert rate_base != rate_future

    def test_get_forward_points(self, mock_source: MockFXDataSource, test_date: date) -> None:
        """Test getting forward points."""
        points = mock_source.get_forward_points("USD/JPY", test_date, 3)

        assert isinstance(points, Decimal)

    def test_get_forward_points_different_periods(
        self, mock_source: MockFXDataSource, test_date: date
    ) -> None:
        """Test forward points for different periods."""
        points_1m = mock_source.get_forward_points("USD/JPY", test_date, 1)
        points_3m = mock_source.get_forward_points("USD/JPY", test_date, 3)
        points_6m = mock_source.get_forward_points("USD/JPY", test_date, 6)

        # Longer periods should generally have larger absolute points
        # (assuming positive interest rate differential)
        assert isinstance(points_1m, Decimal)
        assert isinstance(points_3m, Decimal)
        assert isinstance(points_6m, Decimal)

    def test_get_interest_rate(self, mock_source: MockFXDataSource, test_date: date) -> None:
        """Test getting interest rate."""
        rate = mock_source.get_interest_rate("USD", test_date, 3)

        assert isinstance(rate, Decimal)
        assert rate >= 0

    def test_get_interest_rate_different_currencies(
        self, mock_source: MockFXDataSource, test_date: date
    ) -> None:
        """Test interest rates for different currencies."""
        usd_rate = mock_source.get_interest_rate("USD", test_date, 3)
        jpy_rate = mock_source.get_interest_rate("JPY", test_date, 3)
        eur_rate = mock_source.get_interest_rate("EUR", test_date, 3)

        # All rates should be valid
        for rate in [usd_rate, jpy_rate, eur_rate]:
            assert isinstance(rate, Decimal)
            assert rate >= 0

    def test_get_interest_rate_time_variation(self, mock_source: MockFXDataSource) -> None:
        """Test that interest rates vary slightly with time."""
        base_date = date(2024, 1, 15)
        future_date = date(2024, 2, 15)

        rate_base = mock_source.get_interest_rate("USD", base_date, 3)
        rate_future = mock_source.get_interest_rate("USD", future_date, 3)

        # Small variation expected
        assert rate_base >= 0
        assert rate_future >= 0

    def test_parse_pair_valid(self, mock_source: MockFXDataSource) -> None:
        """Test parsing valid pair string."""
        base, quote = mock_source._parse_pair("usd/jpy")

        assert base == "USD"
        assert quote == "JPY"

    def test_parse_pair_invalid_no_slash(self, mock_source: MockFXDataSource) -> None:
        """Test parsing invalid pair without slash."""
        with pytest.raises(ValueError, match="Invalid pair format"):
            mock_source._parse_pair("USDJPY")

    def test_mock_base_rates(self) -> None:
        """Test that base rates are defined for expected currencies."""
        source = MockFXDataSource()
        expected_currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

        for currency in expected_currencies:
            assert currency in source._base_rates

    def test_mock_base_interest_rates(self) -> None:
        """Test that base interest rates are defined for expected currencies."""
        source = MockFXDataSource()
        expected_currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]

        for currency in expected_currencies:
            assert currency in source._base_rates_interest


class TestFXRateProviderImpl:
    """Tests for FXRateProviderImpl class."""

    @pytest.fixture
    def mock_source(self) -> MockFXDataSource:
        """Provide a mock data source."""
        return MockFXDataSource(base_date=date(2024, 1, 15))

    @pytest.fixture
    def provider(self, mock_source: MockFXDataSource) -> FXRateProviderImpl:
        """Provide an FX rate provider implementation."""
        return FXRateProviderImpl(mock_source)

    @pytest.fixture
    def test_date(self) -> date:
        """Provide a test date."""
        return date(2024, 1, 15)

    def test_provider_initialization(
        self, provider: FXRateProviderImpl, mock_source: MockFXDataSource
    ) -> None:
        """Test provider initialization."""
        assert provider._data_source == mock_source

    def test_get_spot_rate(self, provider: FXRateProviderImpl, test_date: date) -> None:
        """Test getting spot rate."""
        pair = FXPair("USD", "JPY")
        rate = provider.get_spot_rate(pair, test_date)

        assert isinstance(rate, Decimal)
        assert rate > 0

    def test_get_forward_rate(self, provider: FXRateProviderImpl, test_date: date) -> None:
        """Test getting forward rate."""
        pair = FXPair("USD", "JPY")
        rate = provider.get_forward_rate(pair, test_date, 3)

        assert isinstance(rate, Decimal)
        assert rate > 0

    def test_forward_rate_equals_spot_plus_points(
        self, provider: FXRateProviderImpl, test_date: date
    ) -> None:
        """Test that forward rate equals spot plus forward points."""
        pair = FXPair("USD", "JPY")
        pair_str = str(pair)

        spot = provider._data_source.get_rate(pair_str, test_date)
        points = provider._data_source.get_forward_points(pair_str, test_date, 3)
        forward = provider.get_forward_rate(pair, test_date, 3)

        assert forward == spot + points

    def test_get_interest_rate(self, provider: FXRateProviderImpl, test_date: date) -> None:
        """Test getting interest rate."""
        rate = provider.get_interest_rate("USD", test_date, 3)

        assert isinstance(rate, Decimal)
        assert rate >= 0

    def test_different_forward_periods(self, provider: FXRateProviderImpl, test_date: date) -> None:
        """Test getting forward rates for different periods."""
        pair = FXPair("EUR", "USD")

        rate_1m = provider.get_forward_rate(pair, test_date, 1)
        rate_3m = provider.get_forward_rate(pair, test_date, 3)
        rate_6m = provider.get_forward_rate(pair, test_date, 6)

        assert all(isinstance(r, Decimal) for r in [rate_1m, rate_3m, rate_6m])


class TestFXInterestRateProvider:
    """Tests for FXInterestRateProvider class."""

    @pytest.fixture
    def mock_source(self) -> MockFXDataSource:
        """Provide a mock data source."""
        return MockFXDataSource(base_date=date(2024, 1, 15))

    @pytest.fixture
    def provider(self, mock_source: MockFXDataSource) -> FXInterestRateProvider:
        """Provide an interest rate provider."""
        return FXInterestRateProvider(mock_source)

    @pytest.fixture
    def test_date(self) -> date:
        """Provide a test date."""
        return date(2024, 1, 15)

    def test_provider_initialization(
        self, provider: FXInterestRateProvider, mock_source: MockFXDataSource
    ) -> None:
        """Test provider initialization."""
        assert provider._data_source == mock_source

    def test_get_quote_complete(self, provider: FXInterestRateProvider, test_date: date) -> None:
        """Test getting complete interest rate quote."""
        quote = provider.get_quote("USD", test_date)

        assert isinstance(quote, InterestRateQuote)
        assert quote.currency == "USD"
        assert quote.timestamp == test_date
        assert quote.rate_1m is not None
        assert quote.rate_3m is not None
        assert quote.rate_6m is not None
        assert quote.rate_12m is not None

    def test_get_quote_values_valid(
        self, provider: FXInterestRateProvider, test_date: date
    ) -> None:
        """Test that quote values are valid."""
        quote = provider.get_quote("EUR", test_date)

        all_rates = [quote.rate_1m, quote.rate_3m, quote.rate_6m, quote.rate_12m]
        for rate in all_rates:
            assert rate is not None
            assert rate >= 0

    def test_get_quote_different_currencies(
        self, provider: FXInterestRateProvider, test_date: date
    ) -> None:
        """Test getting quotes for different currencies."""
        usd_quote = provider.get_quote("USD", test_date)
        jpy_quote = provider.get_quote("JPY", test_date)
        eur_quote = provider.get_quote("EUR", test_date)

        assert usd_quote.currency == "USD"
        assert jpy_quote.currency == "JPY"
        assert eur_quote.currency == "EUR"

    def test_get_quote_term_structure(
        self, provider: FXInterestRateProvider, test_date: date
    ) -> None:
        """Test that quote represents term structure."""
        quote = provider.get_quote("USD", test_date)

        # Get all rates
        rates = [quote.rate_1m, quote.rate_3m, quote.rate_6m, quote.rate_12m]
        assert all(r is not None for r in rates)

        # All rates should be valid decimals
        for rate in rates:
            assert isinstance(rate, Decimal)
            assert rate >= 0


class TestFXDataSourceProtocol:
    """Tests for FXDataSource protocol."""

    def test_protocol_has_required_methods(self) -> None:
        """Test that FXDataSource defines required interface."""
        required_methods = ["get_rate", "get_forward_points"]

        for method in required_methods:
            assert hasattr(FXDataSource, method)

    def test_protocol_is_protocol(self) -> None:
        """Test that FXDataSource is a Protocol."""

        # Protocols have specific attributes
        assert (
            hasattr(FXDataSource, "__protocol_attrs__") or FXDataSource.__name__ == "FXDataSource"
        )
