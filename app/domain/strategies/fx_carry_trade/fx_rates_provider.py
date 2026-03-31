"""
FX Rate Provider for Carry Trade Strategy.

This module defines the provider interface and implementations for accessing
FX market data including spot rates, forward rates, and interest rates.

The provider abstraction allows for multiple data sources:
- In-memory provider for testing and backtesting
- API-based providers for live trading (future extension)
- Database providers for historical analysis (future extension)
"""

from __future__ import annotations

import logging
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.domain.strategies.fx_carry_trade.models import FXPair, FXRateQuote, InterestRateQuote
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


# ============================================================================
# Protocols - Interface definitions for FX data providers
# ============================================================================


class FXDataSource(Protocol):
    """
    Protocol for FX market data sources.

    Defines the interface for raw FX market data including spot rates,
    forward rates, and interest rates. This is a lower-level abstraction
    than FXRateProvider, focusing on data retrieval rather than business logic.

    Methods:
        get_rate: Get FX rate for a currency pair
        get_forward_points: Get forward points for a currency pair
        get_interest_rate: Get interest rate for a currency

    Examples:
        >>> source = MockFXDataSource()
        >>> rate = source.get_rate("EUR/USD", date.today())
    """

    @abstractmethod
    def get_rate(self, pair: str, as_of: date) -> Decimal:
        """
        Get FX rate for a currency pair.

        Args:
            pair: Currency pair as string (e.g., "EUR/USD")
            as_of: Date for the rate

        Returns:
            FX rate as Decimal

        Raises:
            ValueError: If pair format is invalid
        """
        ...

    @abstractmethod
    def get_forward_points(self, pair: str, as_of: date, months: int) -> Decimal:
        """
        Get forward points for a currency pair.

        Args:
            pair: Currency pair as string (e.g., "EUR/USD")
            as_of: Date for the forward points
            months: Forward term in months

        Returns:
            Forward points as Decimal
        """
        ...

    @abstractmethod
    def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal:
        """
        Get interest rate for a currency.

        Args:
            currency: Currency code (ISO 4217)
            as_of: Date for the rate
            months: Term in months

        Returns:
            Interest rate as Decimal
        """
        ...


class FXInterestRateProviderProtocol(Protocol):
    """
    Protocol for interest rate data providers.

    Specialized protocol for accessing interest rate data used in
    carry trade calculations.

    Methods:
        get_quote: Get interest rate quote for currency and date

    Examples:
        >>> provider = FXInterestRateProvider()
        >>> quote = provider.get_quote("USD", date.today())
    """

    @abstractmethod
    def get_quote(self, currency: str, as_of: date, term: int) -> InterestRateQuote:
        """
        Get interest rate quote for a currency and date.

        Args:
            currency: Currency code (ISO 4217)
            as_of: Date for the quote
            term: Term in months

        Returns:
            InterestRateQuote with rate information

        Raises:
            ValueError: If rate not found
        """
        ...


# ============================================================================
# Existing protocol (kept for backward compatibility)
# ============================================================================


class FXRateProvider(Protocol):
    """
    Protocol for FX rate data providers.

    Defines the interface for accessing FX market data. Implementations
    can source data from APIs, databases, or in-memory storage.

    The protocol follows the dependency inversion principle - the strategy
    depends on abstractions rather than concrete implementations.

    Methods:
        get_spot_rate: Get current spot rate for a currency pair
        get_forward_rate: Get forward rate for a currency pair and term
        get_interest_rate: Get interest rate for a currency and term
        get_available_pairs: Get list of available currency pairs
        get_available_currencies: Get list of available currencies

    Examples:
        >>> provider = InMemoryFXRateProvider()
        >>> pair = FXPair("EUR", "USD")
        >>> rate = provider.get_spot_rate(pair, date.today())
        >>> print(f"EUR/USD: {rate}")
        EUR/USD: 1.0850
    """

    @abstractmethod
    def get_spot_rate(self, pair: FXPair, as_of: date) -> Decimal:
        """
        Get spot rate for a currency pair.

        Args:
            pair: Currency pair to query
            as_of: Date for the rate

        Returns:
            Spot rate (units of quote currency per 1 base currency)

        Raises:
            ValueError: If rate not found for the pair and date
        """
        ...

    @abstractmethod
    def get_forward_rate(self, pair: FXPair, as_of: date, months: int) -> Decimal:
        """
        Get forward rate for a currency pair.

        Args:
            pair: Currency pair to query
            as_of: Date for the forward quote
            months: Forward term in months

        Returns:
            Forward rate (units of quote currency per 1 base currency)

        Raises:
            ValueError: If forward rate not found
        """
        ...

    @abstractmethod
    def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal:
        """
        Get interest rate for a currency.

        Args:
            currency: Currency code (ISO 4217)
            as_of: Date for the rate
            months: Term in months

        Returns:
            Annualized interest rate as decimal (e.g., 0.05 for 5%)

        Raises:
            ValueError: If interest rate not found
        """
        ...

    @abstractmethod
    def get_available_pairs(self) -> list[FXPair]:
        """
        Get list of available currency pairs.

        Returns:
            List of FXPair objects with available data
        """
        ...

    @abstractmethod
    def get_available_currencies(self) -> list[str]:
        """
        Get list of available currencies.

        Returns:
            List of currency codes (ISO 4217)
        """
        ...


@dataclass
class InMemoryFXRateProvider:
    """
    In-memory implementation of FX rate provider.

    Stores FX rates and interest rates in memory for testing and
    backtesting purposes. Can be initialized with or without default data.

    This provider is thread-safe for read operations but not for
    concurrent writes.

    Attributes:
        _spot_rates: Dictionary of spot rates keyed by (base, quote, date)
        _forward_rates: Dictionary of forward rates keyed by (base, quote, date, months)
        _interest_rates: Dictionary of interest rates keyed by (currency, date, months)
        _auto_load_data: If True, automatically load default data on initialization

    Examples:
        >>> provider = InMemoryFXRateProvider()
        >>> provider.add_spot_rate(
        ...     FXPair("EUR", "USD"),
        ...     date.today(),
        ...     Decimal("1.0850")
        ... )
        >>> rate = provider.get_spot_rate(FXPair("EUR", "USD"), date.today())
        >>> print(rate)
        1.0850
    """

    # Use underscore-prefixed attributes as tests expect
    _spot_rates: dict[tuple[str, str, date], Decimal] = field(default_factory=dict)
    _forward_rates: dict[tuple[str, str, date, int], Decimal] = field(default_factory=dict)
    _interest_rates: dict[tuple[str, date, int], Decimal] = field(default_factory=dict)
    _auto_load_data: bool = field(default=True)

    # Aliases for backward compatibility
    @property
    def spot_rates(self) -> dict[tuple[FXPair, date], Decimal]:
        """Alias for _spot_rates with FXPair keys."""
        result = {}
        for (base, quote, as_of), rate in self._spot_rates.items():
            pair = FXPair(base, quote)
            result[(pair, as_of)] = rate
        return result

    @property
    def forward_rates(self) -> dict[tuple[FXPair, date, int], Decimal]:
        """Alias for _forward_rates with FXPair keys."""
        result = {}
        for (base, quote, as_of, months), rate in self._forward_rates.items():
            pair = FXPair(base, quote)
            result[(pair, as_of, months)] = rate
        return result

    @property
    def interest_rates(self) -> dict[tuple[str, date, int], Decimal]:
        """Alias for _interest_rates."""
        return self._interest_rates

    def __post_init__(self) -> None:
        """Initialize provider with default G10 currency data if auto_load is enabled."""
        if self._auto_load_data:
            self._load_default_data()
            logger.info(
                f"InMemoryFXRateProvider initialized with {len(self.get_available_pairs())} pairs"
            )

    def add_spot_rate(self, pair: FXPair | str, rate: Decimal, as_of: date) -> None:
        """
        Add a spot rate quote.

        Args:
            pair: Currency pair (FXPair or string like "USD/JPY")
            rate: Spot rate (must be positive)
            as_of: Quote date

        Raises:
            ValueError: If rate is not positive or pair format is invalid
        """
        if isinstance(pair, str):
            pair = self._parse_pair_string(pair)
        elif not isinstance(pair, FXPair):
            raise ValueError(f"pair must be FXPair or str, got {type(pair)}")

        if rate <= 0:
            raise ValueError(f"Rate must be positive, got {rate}")

        key = (pair.base_currency, pair.quote_currency, as_of)
        self._spot_rates[key] = rate

    def add_forward_rate(self, pair: str, rate: Decimal, as_of: date, months: int) -> None:
        """
        Add a forward rate quote.

        Args:
            pair: Currency pair as string (e.g., "USD/JPY")
            rate: Forward rate (must be positive)
            as_of: Quote date
            months: Forward term in months (must be 1, 3, 6, or 12)

        Raises:
            ValueError: If rate is not positive or months invalid
        """
        if months not in [1, 3, 6, 12]:
            raise ValueError(f"months must be 1, 3, 6, or 12, got {months}")

        if rate <= 0:
            raise ValueError(f"Rate must be positive, got {rate}")

        # Parse pair string to get base and quote
        base, quote = self._parse_pair(pair)
        key = (base, quote, as_of, months)
        self._forward_rates[key] = rate

    def add_interest_rate(self, currency: str, rate: Decimal, as_of: date, months: int) -> None:
        """
        Add an interest rate quote.

        Args:
            currency: Currency code (ISO 4217)
            rate: Annualized interest rate as decimal
            as_of: Quote date
            months: Term in months (must be 1, 3, 6, or 12)

        Raises:
            ValueError: If rate is negative, currency invalid, or months invalid
        """
        if not self._is_valid_currency(currency):
            raise ValueError(f"Invalid currency code: {currency}")

        if months not in [1, 3, 6, 12]:
            raise ValueError(f"months must be 1, 3, 6, or 12, got {months}")

        if rate < 0:
            raise ValueError(f"Interest rate cannot be negative, got {rate}")

        currency = currency.upper()
        key = (currency, as_of, months)
        self._interest_rates[key] = rate

    def _is_valid_currency(self, currency: str) -> bool:
        """Check if currency code is valid (3 alphabetic characters)."""
        return (
            currency is not None
            and len(currency) == 3
            and currency.isalpha()
            and len(currency.strip()) == 3
        )

    def _parse_pair(self, pair_str: str) -> tuple[str, str]:
        """
        Parse a currency pair string into tuple of (base, quote).

        This method is used internally for key generation.

        Args:
            pair_str: Pair string like "USD/JPY"

        Returns:
            Tuple of (base, quote) currency codes

        Raises:
            ValueError: If pair format is invalid
        """
        if not isinstance(pair_str, str):
            raise ValueError(f"Invalid pair format: expected string, got {type(pair_str)}")

        parts = pair_str.strip().upper().split("/")

        if len(parts) != 2:
            raise ValueError(f"Invalid pair format: {pair_str}. Expected format: BASE/QUOTE")

        base, quote = parts

        if len(base) != 3 or len(quote) != 3:
            raise ValueError(
                f"Invalid currency codes in pair: {pair_str}. Expected 3-character codes."
            )

        if not base.isalpha() or not quote.isalpha():
            raise ValueError(
                f"Invalid currency codes in pair: {pair_str}. Currency codes must be alphabetic."
            )

        return base, quote

    def _parse_pair_string(self, pair_str: str) -> FXPair:
        """
        Parse a currency pair string into FXPair.

        Args:
            pair_str: Pair string like "USD/JPY"

        Returns:
            FXPair object

        Raises:
            ValueError: If pair format is invalid
        """
        base, quote = self._parse_pair(pair_str)
        return FXPair(base_currency=base, quote_currency=quote)

    def get_spot_rate(self, pair: FXPair, as_of: date) -> Decimal:
        """
        Get spot rate for a currency pair.

        Args:
            pair: Currency pair to query
            as_of: Date for the rate

        Returns:
            Spot rate (units of quote currency per 1 base currency)

        Raises:
            ValueError: If rate not found for the pair and date
        """
        key = (pair.base_currency, pair.quote_currency, as_of)

        if key not in self._spot_rates:
            # Try to find the most recent rate before as_of
            available_dates = [
                d
                for (b, q, d) in self._spot_rates
                if b == pair.base_currency and q == pair.quote_currency and d <= as_of
            ]
            if available_dates:
                most_recent = max(available_dates)
                key = (pair.base_currency, pair.quote_currency, most_recent)
                logger.debug(f"Using spot rate from {most_recent} for {pair} on {as_of}")
            else:
                raise ValueError(f"Spot rate not found for {pair} on {as_of}")

        return self._spot_rates[key]

    def get_forward_rate(self, pair: FXPair, as_of: date, months: int) -> Decimal:
        """
        Get forward rate for a currency pair.

        Args:
            pair: Currency pair to query
            as_of: Date for the forward quote
            months: Forward term in months

        Returns:
            Forward rate (units of quote currency per 1 base currency)

        Raises:
            ValueError: If forward rate not found
        """
        if months <= 0:
            raise ValueError(f"Months must be positive, got {months}")

        key = (pair.base_currency, pair.quote_currency, as_of, months)

        if key not in self._forward_rates:
            # Try to find the most recent rate before as_of
            available_dates = [
                d
                for (b, q, d, m) in self._forward_rates
                if b == pair.base_currency
                and q == pair.quote_currency
                and m == months
                and d <= as_of
            ]
            if available_dates:
                most_recent = max(available_dates)
                key = (pair.base_currency, pair.quote_currency, most_recent, months)
                logger.debug(
                    f"Using forward rate from {most_recent} for {pair} ({months}M) on {as_of}"
                )
            else:
                raise ValueError(f"Forward rate not found for {pair} ({months}M) on {as_of}")

        return self._forward_rates[key]

    def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal:
        """
        Get interest rate for a currency.

        Args:
            currency: Currency code (ISO 4217)
            as_of: Date for the rate
            months: Term in months

        Returns:
            Annualized interest rate as decimal (e.g., 0.05 for 5%)

        Raises:
            ValueError: If interest rate not found
        """
        if months <= 0:
            raise ValueError(f"Months must be positive, got {months}")

        currency = currency.upper()
        key = (currency, as_of, months)

        if key not in self._interest_rates:
            # Try to find the most recent rate before as_of
            available_dates = [
                d
                for (c, d, m) in self._interest_rates
                if c == currency and m == months and d <= as_of
            ]
            if available_dates:
                most_recent = max(available_dates)
                key = (currency, most_recent, months)
                logger.debug(
                    f"Using interest rate from {most_recent} for {currency} ({months}M) on {as_of}"
                )
            else:
                raise ValueError(f"Interest rate not found for {currency} ({months}M) on {as_of}")

        return self._interest_rates[key]

    def get_available_pairs(self) -> list[FXPair]:
        """
        Get list of available currency pairs.

        Returns:
            List of FXPair objects with spot rate data
        """
        pairs_set = {FXPair(base, quote) for (base, quote, _) in self._spot_rates}
        return sorted(pairs_set, key=lambda p: (p.base_currency, p.quote_currency))

    def get_available_currencies(self) -> list[str]:
        """
        Get list of available currencies.

        Returns:
            Sorted list of currency codes (ISO 4217)
        """
        currencies_set = set()

        # Add currencies from spot rates
        for base, quote, _ in self._spot_rates:
            currencies_set.add(base)
            currencies_set.add(quote)

        # Add currencies from interest rates
        for currency, _, _ in self._interest_rates:
            currencies_set.add(currency)

        return sorted(currencies_set)

    def _load_default_data(self) -> None:
        """
        Load default G10 currency data.

        Populates the provider with sample data for major G10 currencies
        at realistic market rates. This provides a foundation for testing
        and backtesting.
        """
        today = date.today()

        # Sample spot rates (approximate market rates)
        spot_data = {
            ("EUR", "USD"): Decimal("1.0850"),
            ("GBP", "USD"): Decimal("1.2650"),
            ("USD", "JPY"): Decimal("149.50"),
            ("USD", "CHF"): Decimal("0.8820"),
            ("USD", "CAD"): Decimal("1.3580"),
            ("AUD", "USD"): Decimal("0.6520"),
            ("NZD", "USD"): Decimal("0.6120"),
            ("USD", "NOK"): Decimal("10.65"),
            ("USD", "SEK"): Decimal("10.42"),
        }

        # Sample forward rates (3-month)
        forward_data = {
            ("EUR", "USD", 3): Decimal("1.0875"),
            ("GBP", "USD", 3): Decimal("1.2700"),
            ("USD", "JPY", 3): Decimal("148.80"),
            ("USD", "CHF", 3): Decimal("0.8850"),
            ("USD", "CAD", 3): Decimal("1.3520"),
            ("AUD", "USD", 3): Decimal("0.6550"),
            ("NZD", "USD", 3): Decimal("0.6150"),
            ("USD", "NOK", 3): Decimal("10.58"),
            ("USD", "SEK", 3): Decimal("10.35"),
        }

        # Sample interest rates (3-month, annualized)
        interest_data = {
            ("USD", 3): Decimal("0.0525"),  # 5.25%
            ("EUR", 3): Decimal("0.0400"),  # 4.00%
            ("GBP", 3): Decimal("0.0510"),  # 5.10%
            ("JPY", 3): Decimal("0.0000"),  # 0.00%
            ("CHF", 3): Decimal("0.0150"),  # 1.50%
            ("CAD", 3): Decimal("0.0475"),  # 4.75%
            ("AUD", 3): Decimal("0.0425"),  # 4.25%
            ("NZD", 3): Decimal("0.0550"),  # 5.50%
            ("NOK", 3): Decimal("0.0400"),  # 4.00%
            ("SEK", 3): Decimal("0.0300"),  # 3.00%
        }

        # Load spot rates
        for (base, quote), rate in spot_data.items():
            pair = FXPair(base, quote)
            self.add_spot_rate(pair, rate, today)

        # Load forward rates
        for (base, quote, months), rate in forward_data.items():
            pair = FXPair(base, quote)
            self.add_forward_rate(str(pair), rate, today, months)

        # Load interest rates
        for (currency, months), rate in interest_data.items():
            self.add_interest_rate(currency, rate, today, months)

        logger.debug("Loaded default G10 currency data")

    def get_rate_quote(self, pair: FXPair, as_of: date) -> FXRateQuote:
        """
        Get a complete rate quote including spot and forward rates.

        Args:
            pair: Currency pair
            as_of: Quote date

        Returns:
            FXRateQuote with available rates

        Raises:
            ValueError: If spot rate not found
        """
        spot_rate = self.get_spot_rate(pair, as_of)

        # Try to get forward rate (optional)
        try:
            forward_rate = self.get_forward_rate(pair, as_of, months=3)
        except ValueError:
            forward_rate = None

        return FXRateQuote(
            pair=pair,
            spot_rate=spot_rate,
            forward_3m=forward_rate,
            timestamp=as_of,
        )

    def get_fx_summary(self, as_of: date) -> dict[str, dict[str, Decimal]]:
        """
        Get summary of all available FX rates.

        Args:
            as_of: Date for the rates

        Returns:
            Dictionary mapping pair strings to rate dictionaries
        """
        summary = {}

        for pair in self.get_available_pairs():
            try:
                spot = self.get_spot_rate(pair, as_of)
                pair_data = {"spot": spot}

                try:
                    forward_3m = self.get_forward_rate(pair, as_of, 3)
                    pair_data["forward_3m"] = forward_3m
                except ValueError:
                    pass

                summary[str(pair)] = pair_data
            except ValueError:
                pass

        return summary

    def get_interest_rate_summary(self, as_of: date) -> dict[str, dict[int, Decimal]]:
        """
        Get summary of all available interest rates.

        Args:
            as_of: Date for the rates

        Returns:
            Dictionary mapping currencies to term/rate dictionaries
        """
        summary = {}

        for currency in self.get_available_currencies():
            currency_rates = {}

            for months in [1, 3, 6, 12]:
                try:
                    rate = self.get_interest_rate(currency, as_of, months)
                    currency_rates[months] = rate
                except ValueError:
                    pass

            if currency_rates:
                summary[currency] = currency_rates

        return summary

    def clear_data(self) -> None:
        """Clear all stored data."""
        self._spot_rates.clear()
        self._forward_rates.clear()
        self._interest_rates.clear()
        logger.debug("Cleared all rate data")

    def __str__(self) -> str:
        """Return string representation of provider."""
        num_pairs = len(self.get_available_pairs())
        num_currencies = len(self.get_available_currencies())
        return f"InMemoryFXRateProvider(pairs={num_pairs}, currencies={num_currencies})"

    def __repr__(self) -> str:
        """Return detailed representation of provider."""
        return (
            f"InMemoryFXRateProvider("
            f"spot_rates={len(self._spot_rates)}, "
            f"forward_rates={len(self._forward_rates)}, "
            f"interest_rates={len(self._interest_rates)})"
        )


class CompositeFXRateProvider(FXRateProvider):
    """
    Composite provider that aggregates multiple rate providers.

    Queries multiple providers in sequence until data is found.
    Useful for combining different data sources with fallback logic.

    Attributes:
        providers: List of providers to query (in order)

    Examples:
        >>> primary = InMemoryFXRateProvider()
        >>> secondary = InMemoryFXRateProvider()
        >>> composite = CompositeFXRateProvider([primary, secondary])
    """

    def __init__(self, providers: list[FXRateProvider]) -> None:
        """
        Initialize composite provider.

        Args:
            providers: List of providers to query in order

        Raises:
            ValueError: If providers list is empty
        """
        if not providers:
            raise ValueError("At least one provider must be specified")

        self.providers = providers
        logger.info(f"CompositeFXRateProvider initialized with {len(providers)} providers")

    def get_spot_rate(self, pair: FXPair, as_of: date) -> Decimal:
        """Get spot rate from first provider that has it."""
        for _i, provider in enumerate(self.providers):
            try:
                return provider.get_spot_rate(pair, as_of)
            except ValueError:
                continue

        raise ValueError(f"No spot rate found for {pair} on {as_of} in any provider")

    def get_forward_rate(self, pair: FXPair, as_of: date, months: int) -> Decimal:
        """Get forward rate from first provider that has it."""
        for provider in self.providers:
            try:
                return provider.get_forward_rate(pair, as_of, months)
            except ValueError:
                continue

        raise ValueError(f"No forward rate found for {pair} ({months}M) on {as_of} in any provider")

    def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal:
        """Get interest rate from first provider that has it."""
        for provider in self.providers:
            try:
                return provider.get_interest_rate(currency, as_of, months)
            except ValueError:
                continue

        raise ValueError(
            f"No interest rate found for {currency} ({months}M) on {as_of} in any provider"
        )

    def get_available_pairs(self) -> list[FXPair]:
        """Get union of available pairs from all providers."""
        pairs_set = set()
        for provider in self.providers:
            pairs_set.update(provider.get_available_pairs())
        return sorted(pairs_set, key=lambda p: (p.base_currency, p.quote_currency))

    def get_available_currencies(self) -> list[str]:
        """Get union of available currencies from all providers."""
        currencies_set = set()
        for provider in self.providers:
            currencies_set.update(provider.get_available_currencies())
        return sorted(currencies_set)

    def __str__(self) -> str:
        """Return string representation."""
        return f"CompositeFXRateProvider(providers={len(self.providers)})"


# ============================================================================
# Mock Data Source for Testing
# ============================================================================


@dataclass
class MockFXDataSource:
    """
    Mock FX data source for testing.

    Provides a simple in-memory data source that generates realistic
    FX rates, forward points, and interest rates for testing.

    Attributes:
        base_date: Base date for rate calculations (defaults to today)
        _base_rates: Dictionary of base currency rates against USD
        _base_rates_interest: Dictionary of base interest rates

    Examples:
        >>> source = MockFXDataSource()
        >>> rate = source.get_rate("EUR/USD", date.today())
        >>> print(rate)
        1.0850
    """

    base_date: date = field(default_factory=date.today)

    # Base rates against USD (as of base_date)
    _base_rates: dict[str, Decimal] = field(
        default_factory=lambda: {
            "EUR": Decimal("1.0850"),  # EUR/USD
            "GBP": Decimal("1.2650"),  # GBP/USD
            "USD": Decimal("1.0"),  # USD/USD
            "JPY": Decimal("0.006688"),  # USD/JPY inverted
            "CHF": Decimal("1.134"),  # USD/CHF inverted
            "CAD": Decimal("0.7363"),  # USD/CAD inverted
            "AUD": Decimal("0.6520"),  # AUD/USD
            "NZD": Decimal("0.6120"),  # NZD/USD
            "NOK": Decimal("0.0939"),  # USD/NOK inverted
            "SEK": Decimal("0.0960"),  # USD/SEK inverted
        },
        init=False,
        repr=False,
    )

    # Base interest rates (annualized)
    _base_rates_interest: dict[str, Decimal] = field(
        default_factory=lambda: {
            "USD": Decimal("0.0525"),  # 5.25%
            "EUR": Decimal("0.0400"),  # 4.00%
            "GBP": Decimal("0.0510"),  # 5.10%
            "JPY": Decimal("0.0000"),  # 0.00%
            "CHF": Decimal("0.0150"),  # 1.50%
            "CAD": Decimal("0.0475"),  # 4.75%
            "AUD": Decimal("0.0425"),  # 4.25%
            "NZD": Decimal("0.0550"),  # 5.50%
            "NOK": Decimal("0.0400"),  # 4.00%
            "SEK": Decimal("0.0300"),  # 3.00%
        },
        init=False,
        repr=False,
    )

    def _parse_pair(self, pair: str) -> tuple[str, str]:
        """
        Parse a currency pair string.

        Args:
            pair: Currency pair string (e.g., "USD/JPY")

        Returns:
            Tuple of (base, quote) currency codes

        Raises:
            ValueError: If pair format is invalid (no slash)
        """
        if "/" not in pair:
            raise ValueError(f"Invalid pair format: {pair}")

        parts = pair.strip().upper().split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid pair format: {pair}")

        base, quote = parts
        return base, quote

    def get_rate(self, pair: str, as_of: date) -> Decimal:
        """
        Get FX rate for a currency pair.

        Args:
            pair: Currency pair string (e.g., "USD/JPY")
            as_of: Date for the rate

        Returns:
            FX rate as Decimal
        """
        base, quote = self._parse_pair(pair)

        # Get base rates against USD
        if base not in self._base_rates or quote not in self._base_rates:
            # Default to 1.0 for unknown currencies
            base_rate = self._base_rates.get(base, Decimal("1.0"))
            quote_rate = self._base_rates.get(quote, Decimal("1.0"))
        else:
            base_rate = self._base_rates[base]
            quote_rate = self._base_rates[quote]

        # Calculate cross rate
        rate = base_rate / quote_rate

        # Add time-based variation - use config values
        days_diff = (as_of - self.base_date).days if self.base_date else 0
        if days_diff != 0:
            tt = get_config().trading_thresholds
            # Add small random-like variation based on days
            variation = Decimal(str(days_diff * tt.fx_daily_variation_factor))
            rate = rate * (Decimal("1") + variation)

        return rate.quantize(Decimal(tt.fx_quantization_precision))

    def get_forward_points(self, pair: str, as_of: date, months: int) -> Decimal:
        """
        Get forward points for a currency pair.

        Args:
            pair: Currency pair string (e.g., "USD/JPY")
            as_of: Date for the forward points
            months: Forward term in months

        Returns:
            Forward points as Decimal
        """
        base, quote = self._parse_pair(pair)

        # Get interest rates - use config default
        tt = get_config().trading_thresholds
        default_rate = Decimal(str(tt.fx_default_interest_rate))
        base_rate = self._base_rates_interest.get(base, default_rate)
        quote_rate = self._base_rates_interest.get(quote, default_rate)

        # Calculate forward points using interest rate differential - use config
        tt = get_config().trading_thresholds
        spot = self.get_rate(pair, as_of)
        rate_diff = quote_rate - base_rate
        time_factor = Decimal(str(months)) / Decimal(str(tt.fx_months_per_year))

        points = spot * rate_diff * time_factor

        return points.quantize(Decimal(tt.fx_quantization_precision))

    def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal:
        """
        Get interest rate for a currency.

        Args:
            currency: Currency code (ISO 4217)
            as_of: Date for the rate
            months: Term in months

        Returns:
            Interest rate as Decimal
        """
        currency_upper = currency.upper()

        # Get base rate - use config default
        tt = get_config().trading_thresholds
        base_rate = self._base_rates_interest.get(
            currency_upper, Decimal(str(tt.fx_default_interest_rate))
        )

        # Add small time-based variation - use config value
        days_diff = (as_of - self.base_date).days if self.base_date else 0
        if days_diff != 0:
            variation = Decimal(str(days_diff * tt.fx_long_term_variation_factor))
            base_rate = base_rate + variation

        # Ensure non-negative
        if base_rate < 0:
            base_rate = Decimal("0")

        return base_rate.quantize(Decimal(tt.fx_quantization_precision))


# ============================================================================
# Cached Provider
# ============================================================================


class CachedFXRateProvider:
    """
    Cached FX rate provider that wraps another provider.

    Caches results from an underlying provider to reduce repeated lookups.
    Useful when the same rates are queried multiple times.

    Attributes:
        _underlying: Underlying rate provider
        _cache_ttl: Cache time-to-live in seconds
        _spot_cache: Cache for spot rates
        _forward_cache: Cache for forward rates
        _rate_cache: Cache for interest rates
        _cache_timestamps: Timestamps for cache entries

    Examples:
        >>> underlying = InMemoryFXRateProvider()
        >>> cached = CachedFXRateProvider(underlying, cache_ttl=3600)
        >>> rate = cached.get_spot_rate(FXPair("EUR", "USD"), date.today())
    """

    def __init__(self, underlying: FXRateProvider | None = None, cache_ttl: int = 3600) -> None:
        """
        Initialize cached provider.

        Args:
            underlying: Underlying rate provider (defaults to new InMemoryFXRateProvider)
            cache_ttl: Cache time-to-live in seconds (default 3600 = 1 hour)
        """
        if underlying is None:
            self._underlying: FXRateProvider = InMemoryFXRateProvider()
        else:
            self._underlying = underlying

        self._cache_ttl: int = cache_ttl
        self._spot_cache: dict = {}
        self._forward_cache: dict = {}
        self._rate_cache: dict = {}
        self._cache_timestamps: dict = {}

    def _is_cache_valid(self, key: tuple) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache_timestamps:
            return False

        timestamp = self._cache_timestamps[key]
        return bool((time.time() - timestamp) < self._cache_ttl)

    def get_spot_rate(self, pair: FXPair, as_of: date) -> Decimal:
        """Get spot rate, using cache if available."""
        key = ("spot", pair, as_of)

        if key in self._spot_cache and self._is_cache_valid(key):
            return Decimal(str(self._spot_cache[key]))

        rate = self._underlying.get_spot_rate(pair, as_of)
        self._spot_cache[key] = rate
        self._cache_timestamps[key] = time.time()

        return Decimal(str(rate))

    def get_forward_rate(self, pair: FXPair, as_of: date, months: int) -> Decimal:
        """Get forward rate, using cache if available."""
        key = ("forward", pair, as_of, months)

        if key in self._forward_cache and self._is_cache_valid(key):
            return Decimal(str(self._forward_cache[key]))

        rate = self._underlying.get_forward_rate(pair, as_of, months)
        self._forward_cache[key] = rate
        self._cache_timestamps[key] = time.time()

        return Decimal(str(rate))

    def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal:
        """Get interest rate, using cache if available."""
        key = ("rate", currency.upper(), as_of, months)

        if key in self._rate_cache and self._is_cache_valid(key):
            return Decimal(str(self._rate_cache[key]))

        rate = self._underlying.get_interest_rate(currency, as_of, months)
        self._rate_cache[key] = rate
        self._cache_timestamps[key] = time.time()

        return Decimal(str(rate))

    def get_available_pairs(self) -> list[FXPair]:
        """Get available pairs from underlying provider."""
        return self._underlying.get_available_pairs()

    def get_available_currencies(self) -> list[str]:
        """Get available currencies from underlying provider."""
        return self._underlying.get_available_currencies()

    def clear_cache(self) -> None:
        """Clear all cached values."""
        self._spot_cache.clear()
        self._forward_cache.clear()
        self._rate_cache.clear()
        self._cache_timestamps.clear()
        logger.debug("Cleared FX rate cache")

    def __str__(self) -> str:
        """Return string representation."""
        return f"CachedFXRateProvider(underlying={self._underlying})"


# ============================================================================
# FX Rate Provider Implementation with Mock Data Source
# ============================================================================


@dataclass
class FXRateProviderImpl:
    """
    FX Rate Provider implementation using a mock data source.

    This implementation wraps a MockFXDataSource to provide
    FX rate data through the FXRateProvider interface.

    Attributes:
        _data_source: Underlying mock data source

    Examples:
        >>> source = MockFXDataSource()
        >>> provider = FXRateProviderImpl(source)
        >>> rate = provider.get_spot_rate(FXPair("EUR", "USD"), date.today())
    """

    _data_source: MockFXDataSource

    def get_spot_rate(self, pair: FXPair, as_of: date) -> Decimal:
        """Get spot rate for a currency pair."""
        pair_str = str(pair)
        return self._data_source.get_rate(pair_str, as_of)

    def get_forward_rate(self, pair: FXPair, as_of: date, months: int) -> Decimal:
        """Get forward rate for a currency pair."""
        pair_str = str(pair)
        spot = self._data_source.get_rate(pair_str, as_of)
        points = self._data_source.get_forward_points(pair_str, as_of, months)
        return spot + points

    def get_interest_rate(self, currency: str, as_of: date, months: int) -> Decimal:
        """Get interest rate for a currency."""
        return self._data_source.get_interest_rate(currency, as_of, months)

    def get_available_pairs(self) -> list[FXPair]:
        """Get available currency pairs."""
        # Return common G10 pairs
        currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]
        pairs = []
        for base in currencies:
            for quote in currencies:
                if base != quote:
                    pairs.append(FXPair(base, quote))
        return pairs

    def get_available_currencies(self) -> list[str]:
        """Get available currencies."""
        return ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]


# ============================================================================
# FX Interest Rate Provider Implementation
# ============================================================================


class FXInterestRateProviderImpl:
    """
    FX Interest Rate Provider implementation using a mock data source.

    This implementation wraps a MockFXDataSource to provide
    interest rate quotes through the FXInterestRateProvider interface.

    Attributes:
        _data_source: Underlying mock data source

    Examples:
        >>> source = MockFXDataSource()
        >>> provider = FXInterestRateProviderImpl(source)
        >>> quote = provider.get_quote("USD", date.today())
    """

    def __init__(self, data_source: MockFXDataSource) -> None:
        """
        Initialize provider with data source.

        Args:
            data_source: Mock FX data source
        """
        self._data_source = data_source

    def get_quote(self, currency: str, as_of: date, term: int = 3) -> InterestRateQuote:
        """Get interest rate quote for a currency and date."""
        currency_upper = currency.upper()

        # Get rates for all terms
        rate_1m = self._data_source.get_interest_rate(currency_upper, as_of, 1)
        rate_3m = self._data_source.get_interest_rate(currency_upper, as_of, 3)
        rate_6m = self._data_source.get_interest_rate(currency_upper, as_of, 6)
        rate_12m = self._data_source.get_interest_rate(currency_upper, as_of, 12)

        return InterestRateQuote(
            currency=currency_upper,
            rate_1m=rate_1m,
            rate_3m=rate_3m,
            rate_6m=rate_6m,
            rate_12m=rate_12m,
            timestamp=as_of,
        )


# ============================================================================
# Type Alias for backward compatibility and test support
# ============================================================================

# FXInterestRateProvider is an alias to FXInterestRateProviderImpl for test compatibility
# This allows tests to use FXInterestRateProvider as a concrete class
# The protocol is available as FXInterestRateProviderProtocol
FXInterestRateProvider = FXInterestRateProviderImpl
