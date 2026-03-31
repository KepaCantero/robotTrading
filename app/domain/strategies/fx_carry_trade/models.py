"""
FX Carry Trade Models.

Data models for the FX Carry Trade strategy implementing
Antti Ilmanen's methodology from "Expected Returns" - Rule 12.9.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class CurrencyCode(str, Enum):
    """ISO 4217 currency codes for G10 currencies."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    NZD = "NZD"
    SEK = "SEK"
    NOK = "NOK"


_VALID_MONTHS = {1, 3, 6, 12}


@dataclass(frozen=True)
class FXPair:
    """
    Currency pair representation.

    Represents a currency pair for FX trading with base and quote currencies.

    Attributes:
        base_currency: The base currency code (e.g., "USD")
        quote_currency: The quote currency code (e.g., "JPY")

    Examples:
        >>> pair = FXPair("USD", "JPY")
        >>> str(pair)
        'USD/JPY'
    """

    base_currency: str
    quote_currency: str

    def __post_init__(self) -> None:
        """
        Validate currency codes.

        Raises:
            ValueError: If currency codes are invalid or the same.
        """
        # Normalize to uppercase
        base = self.base_currency.upper()
        quote = self.quote_currency.upper()
        # Use object.__setattr__ because the dataclass is frozen
        object.__setattr__(self, "base_currency", base)
        object.__setattr__(self, "quote_currency", quote)

        if len(base) != 3 or not base.isalpha():
            raise ValueError(f"Invalid base currency code: {base!r}")
        if len(quote) != 3 or not quote.isalpha():
            raise ValueError(f"Invalid quote currency code: {quote!r}")
        if base == quote:
            raise ValueError(f"Base and quote currencies cannot be the same: {base}")

    @property
    def inverse(self) -> FXPair:
        """Return the inverse pair (swap base and quote)."""
        return FXPair(base_currency=self.quote_currency, quote_currency=self.base_currency)

    def __str__(self) -> str:
        """Return string representation as BASE/QUOTE."""
        return f"{self.base_currency}/{self.quote_currency}"

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"FXPair({self.base_currency!r}, {self.quote_currency!r})"


@dataclass
class FXCarrySignal:
    """
    Complete carry trade signal for a currency pair.

    Contains all calculated components for a carry trade decision.

    Attributes:
        pair: Currency pair
        spot_rate: Current spot rate
        forward_rate: Forward rate for the term
        interest_rate_diff: Interest rate differential (r_base - r_quote)
        forward_premium: Forward premium ((F - S) / S)
        carry: Calculated carry value
        signal: Trading signal strength (-1 to 1)
        timestamp: Calculation date
        months: Forward term in months
    """

    pair: FXPair
    spot_rate: Decimal
    forward_rate: Decimal
    interest_rate_diff: Decimal
    forward_premium: Decimal
    carry: Decimal
    signal: Decimal
    timestamp: date
    months: int

    def __post_init__(self) -> None:
        """
        Validate signal values.

        Raises:
            ValueError: If rates are not positive or signal is out of range.
        """
        if self.spot_rate <= 0:
            raise ValueError(f"Spot rate must be positive, got {self.spot_rate}")
        if self.forward_rate <= 0:
            raise ValueError(f"Forward rate must be positive, got {self.forward_rate}")
        if self.signal < Decimal("-1") or self.signal > Decimal("1"):
            raise ValueError(f"Signal must be between -1 and 1, got {self.signal}")

    @property
    def is_long_signal(self) -> bool:
        """Check if signal suggests going long the base currency."""
        return self.signal > 0

    @property
    def is_long(self) -> bool:
        """Check if signal suggests going long the base currency."""
        return self.signal > 0

    @property
    def is_short(self) -> bool:
        """Check if signal suggests going short the base currency."""
        return self.signal < 0

    @property
    def is_neutral(self) -> bool:
        """Check if signal is neutral."""
        return self.signal == 0

    @property
    def signal_strength(self) -> str:
        """Return signal strength as string."""
        abs_signal = abs(self.signal)
        if abs_signal >= 0.7:
            return "VERY_STRONG"
        if abs_signal >= 0.5:
            return "STRONG"
        if abs_signal >= 0.3:
            return "MODERATE"
        if abs_signal > 0:
            return "WEAK"
        return "NEUTRAL"


class CarryTradeAction(str, Enum):
    """Actions for carry trade positions."""

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE = "close"
    HOLD = "hold"
    ROLL = "roll"


@dataclass
class FXCarryPosition:
    """
    Active carry trade position.

    Represents an open position in a carry trade strategy.

    Attributes:
        pair: Currency pair
        quantity: Position size (positive for long, negative for short)
        entry_price: Spot rate at position open
        current_price: Current market price
        carry_return: Accumulated carry return
        price_return: Return from price change
        total_return: Combined carry + price return
        entry_date: Position open date
        current_date: Current valuation date
    """

    pair: FXPair
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    carry_return: Decimal
    price_return: Decimal
    total_return: Decimal
    entry_date: date
    current_date: date

    def __post_init__(self) -> None:
        """
        Validate position values.

        Raises:
            ValueError: If prices are not positive or dates are invalid.
        """
        if self.entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {self.entry_price}")
        if self.current_price <= 0:
            raise ValueError(f"Current price must be positive, got {self.current_price}")
        if self.entry_date > self.current_date:
            raise ValueError(
                f"Entry date cannot be after current date: "
                f"entry={self.entry_date}, current={self.current_date}"
            )

    @property
    def is_long(self) -> bool:
        """Check if position is long base currency."""
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        """Check if position is short base currency."""
        return self.quantity < 0

    @property
    def unrealized_pnl(self) -> Decimal:
        """Calculate unrealized profit and loss."""
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def days_held(self) -> int:
        """Calculate number of days the position has been held."""
        return (self.current_date - self.entry_date).days


@dataclass
class FXCarryTradeConfig:
    """
    Configuration for FX Carry Trade strategy.

    Attributes:
        min_carry_threshold: Minimum carry to generate signal
        max_positions: Maximum simultaneous positions
        position_size: Default position size as fraction of portfolio (0, 1]
        forward_months: Forward contract term in months
        stop_loss: Stop loss percentage (0, 1)
        take_profit: Take profit percentage (0, 1)
        max_leverage: Maximum leverage multiplier (>= 1)
        min_liquidity: Minimum liquidity requirement (>= 0)
    """

    min_carry_threshold: Decimal = Decimal("0.01")
    max_positions: int = 10
    position_size: Decimal = Decimal("0.1")
    forward_months: int = 3
    stop_loss: Decimal = Decimal("0.05")
    take_profit: Decimal = Decimal("0.15")
    max_leverage: Decimal = Decimal("2.0")
    min_liquidity: Decimal = Decimal("1000000")

    def __post_init__(self) -> None:
        """
        Validate configuration values.

        Raises:
            ValueError: If any configuration value is invalid.
        """
        if self.min_carry_threshold < 0:
            raise ValueError(
                f"min_carry_threshold must be non-negative, got {self.min_carry_threshold}"
            )
        if self.max_positions <= 0:
            raise ValueError(f"max_positions must be positive, got {self.max_positions}")
        if self.position_size <= 0 or self.position_size > 1:
            raise ValueError(
                f"position_size must be between 0 and 1 (exclusive), got {self.position_size}"
            )
        if self.forward_months not in _VALID_MONTHS:
            raise ValueError(f"forward_months must be 1, 3, 6, or 12, got {self.forward_months}")
        if self.stop_loss <= 0 or self.stop_loss >= 1:
            raise ValueError(f"stop_loss must be between 0 and 1 (exclusive), got {self.stop_loss}")
        if self.take_profit <= 0 or self.take_profit >= 1:
            raise ValueError(
                f"take_profit must be between 0 and 1 (exclusive), got {self.take_profit}"
            )
        if self.max_leverage < 1:
            raise ValueError(f"max_leverage must be at least 1, got {self.max_leverage}")
        if self.min_liquidity < 0:
            raise ValueError(f"min_liquidity must be non-negative, got {self.min_liquidity}")


@dataclass
class FXRateQuote:
    """
    FX rate quote with spot and forward rates.

    Attributes:
        pair: Currency pair
        spot_rate: Current spot rate
        forward_1m: 1-month forward rate (optional)
        forward_3m: 3-month forward rate (optional)
        forward_6m: 6-month forward rate (optional)
        forward_12m: 12-month forward rate (optional)
        timestamp: Quote timestamp
    """

    pair: FXPair
    spot_rate: Decimal
    forward_1m: Decimal | None = None
    forward_3m: Decimal | None = None
    forward_6m: Decimal | None = None
    forward_12m: Decimal | None = None
    timestamp: date | None = None

    @property
    def has_forward_rates(self) -> bool:
        """Check if any forward rates are available."""
        return any([self.forward_1m, self.forward_3m, self.forward_6m, self.forward_12m])

    def get_forward_rate(self, months: int) -> Decimal | None:
        """
        Get forward rate for a specific term.

        Args:
            months: Forward term in months (1, 3, 6, or 12)

        Returns:
            Forward rate or None if not available

        Raises:
            ValueError: If months is not a valid forward period
        """
        if months not in _VALID_MONTHS:
            raise ValueError(f"Invalid forward period: {months}. Must be 1, 3, 6, or 12.")
        forward_map: dict[int, Decimal | None] = {
            1: self.forward_1m,
            3: self.forward_3m,
            6: self.forward_6m,
            12: self.forward_12m,
        }
        return forward_map[months]


@dataclass
class InterestRateQuote:
    """
    Interest rate quote for a currency.

    Attributes:
        currency: Currency code
        rate_1m: 1-month interest rate (optional)
        rate_3m: 3-month interest rate
        rate_6m: 6-month interest rate (optional)
        rate_12m: 12-month interest rate (optional)
        timestamp: Quote timestamp
    """

    currency: str
    rate_1m: Decimal | None = None
    rate_3m: Decimal = Decimal("0")
    rate_6m: Decimal | None = None
    rate_12m: Decimal | None = None
    timestamp: date | None = None

    @property
    def benchmark_rate(self) -> Decimal:
        """Return the benchmark (3M) rate."""
        return self.rate_3m

    def get_rate(self, months: int) -> Decimal | None:
        """
        Get interest rate for a specific term.

        Args:
            months: Term in months (1, 3, 6, or 12)

        Returns:
            Interest rate or None if not available

        Raises:
            ValueError: If months is not a valid period
        """
        if months not in _VALID_MONTHS:
            raise ValueError(f"Invalid period: {months}. Must be 1, 3, 6, or 12.")
        rate_map: dict[int, Decimal | None] = {
            1: self.rate_1m,
            3: self.rate_3m,
            6: self.rate_6m,
            12: self.rate_12m,
        }
        return rate_map[months]
