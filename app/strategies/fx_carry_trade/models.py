"""
Data Models for FX Carry Trade Strategy.

This module defines data models for currency pair trading including:
- Currency pair representation with validation
- FX rate quotes (spot and forward)
- Interest rate quotes
- Carry trade signals
- Position tracking
- Strategy configuration

References:
    Ilmanen, Antti. "Expected Returns: An Investor's Guide"
    Rule 12.9: Carry = (r_base - r_quote) - ((F - S) / S)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ISO 4217 currency codes for major currencies
G10_CURRENCIES = {
    "USD",  # United States Dollar
    "EUR",  # Euro
    "JPY",  # Japanese Yen
    "GBP",  # British Pound
    "CHF",  # Swiss Franc
    "CAD",  # Canadian Dollar
    "AUD",  # Australian Dollar
    "NZD",  # New Zealand Dollar
    "NOK",  # Norwegian Krone
    "SEK",  # Swedish Krona
}


class CurrencyCode(str, Enum):
    """
    ISO 4217 currency codes for G10 currencies.

    This enum inherits from both str and Enum, allowing the values to be
    used as strings while maintaining the benefits of an enum.

    Attributes:
        USD: United States Dollar
        EUR: Euro
        GBP: British Pound
        JPY: Japanese Yen
        CHF: Swiss Franc
        CAD: Canadian Dollar
        AUD: Australian Dollar
        NZD: New Zealand Dollar
        SEK: Swedish Krona
        NOK: Norwegian Krone

    Examples:
        >>> code = CurrencyCode.USD
        >>> print(code.value)
        USD
        >>> code == "USD"
        True
    """

    USD = "USD"  # United States Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    JPY = "JPY"  # Japanese Yen
    CHF = "CHF"  # Swiss Franc
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    NZD = "NZD"  # New Zealand Dollar
    SEK = "SEK"  # Swedish Krona
    NOK = "NOK"  # Norwegian Krone

    @classmethod
    def from_string(cls, value: str) -> "CurrencyCode":
        """
        Create CurrencyCode from string, case-insensitive.

        Args:
            value: Currency code string

        Returns:
            CurrencyCode enum member

        Raises:
            ValueError: If currency code is not a valid G10 currency
        """
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid currency code: {value}. " f"Must be one of {list(cls.__members__.keys())}"
            )


@dataclass(frozen=True)
class FXPair:
    """
    Foreign exchange currency pair.

    Represents a trading pair for currency carry trades with validation
    for ISO 4217 currency codes.

    Attributes:
        base_currency: Base currency code (ISO 4217, e.g., "EUR")
        quote_currency: Quote currency code (ISO 4217, e.g., "USD")

    Raises:
        ValueError: If currency codes are invalid or identical

    Examples:
        >>> pair = FXPair(base_currency="EUR", quote_currency="USD")
        >>> str(pair)
        'EUR/USD'
    """

    base_currency: str
    quote_currency: str

    def __post_init__(self) -> None:
        """Validate currency codes after initialization."""
        base = self.base_currency.upper()
        quote = self.quote_currency.upper()

        if base == quote:
            raise ValueError(f"Base and quote currency cannot be the same: {base}")

        if len(base) != 3 or not base.isalpha():
            raise ValueError(f"Invalid base currency code: {base}")

        if len(quote) != 3 or not quote.isalpha():
            raise ValueError(f"Invalid quote currency code: {quote}")

        # Update with normalized values
        object.__setattr__(self, "base_currency", base)
        object.__setattr__(self, "quote_currency", quote)

    def __str__(self) -> str:
        """Return string representation as BASE/QUOTE."""
        return f"{self.base_currency}/{self.quote_currency}"

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"FXPair(base='{self.base_currency}', quote='{self.quote_currency}')"

    @property
    def is_g10(self) -> bool:
        """Check if both currencies are G10 currencies."""
        return self.base_currency in G10_CURRENCIES and self.quote_currency in G10_CURRENCIES

    @property
    def inverse(self) -> "FXPair":
        """
        Get the inverse currency pair.

        Returns:
            New FXPair with swapped base and quote currencies

        Examples:
            >>> pair = FXPair("EUR", "USD")
            >>> pair.inverse
            FXPair(base='USD', quote='EUR')
        """
        return FXPair(base_currency=self.quote_currency, quote_currency=self.base_currency)


@dataclass(frozen=True)
class FXRateQuote:
    """
    FX rate quote including spot and forward rates.

    Contains current market rates for a currency pair at a specific point in time.

    Attributes:
        pair: Currency pair
        spot_rate: Current spot rate (units of quote per 1 base)
        forward_1m: 1-month forward rate (optional)
        forward_3m: 3-month forward rate (optional)
        forward_6m: 6-month forward rate (optional)
        forward_12m: 12-month forward rate (optional)
        timestamp: Quote timestamp (optional)

    Raises:
        ValueError: If rates are not positive

    Examples:
        >>> from datetime import date
        >>> pair = FXPair("EUR", "USD")
        >>> quote = FXRateQuote(
        ...     pair=pair,
        ...     spot_rate=Decimal("1.0850"),
        ...     forward_3m=Decimal("1.0900"),
        ...     timestamp=date.today()
        ... )
    """

    pair: FXPair
    spot_rate: Decimal
    forward_1m: Decimal | None = None
    forward_3m: Decimal | None = None
    forward_6m: Decimal | None = None
    forward_12m: Decimal | None = None
    timestamp: date | None = None

    def __post_init__(self) -> None:
        """Validate rate values."""
        if self.spot_rate <= 0:
            raise ValueError(f"Spot rate must be positive, got {self.spot_rate}")

        for name, value in [
            ("forward_1m", self.forward_1m),
            ("forward_3m", self.forward_3m),
            ("forward_6m", self.forward_6m),
            ("forward_12m", self.forward_12m),
        ]:
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")

    def get_forward_rate(self, months: int) -> Decimal | None:
        """
        Get forward rate for specified term.

        Args:
            months: Forward term in months (1, 3, 6, or 12)

        Returns:
            Forward rate for the term, or None if not available

        Raises:
            ValueError: If months is not valid

        Examples:
            >>> quote = FXRateQuote(
            ...     pair=FXPair("EUR", "USD"),
            ...     spot_rate=Decimal("1.0850"),
            ...     forward_3m=Decimal("1.0900")
            ... )
            >>> quote.get_forward_rate(3)
            Decimal('1.0900')
        """
        forward_map = {
            1: self.forward_1m,
            3: self.forward_3m,
            6: self.forward_6m,
            12: self.forward_12m,
        }

        if months not in forward_map:
            raise ValueError(f"Invalid forward period: {months}. Must be 1, 3, 6, or 12")

        return forward_map[months]


@dataclass(frozen=True)
class InterestRateQuote:
    """
    Interest rate quote for a specific currency and term.

    Represents the risk-free interest rate used in carry trade calculations.

    Attributes:
        currency: Currency code (ISO 4217)
        rate_1m: 1-month interest rate (optional)
        rate_3m: 3-month interest rate (optional)
        rate_6m: 6-month interest rate (optional)
        rate_12m: 12-month interest rate (optional)
        timestamp: Quote timestamp (optional)

    Raises:
        ValueError: If currency code is invalid or rates are negative

    Examples:
        >>> quote = InterestRateQuote(
        ...     currency="USD",
        ...     rate_3m=Decimal("0.0525")
        ... )
        >>> print(f"Rate: {quote.rate_3m:.2%}")
        Rate: 5.25%
    """

    currency: str
    rate_1m: Decimal | None = None
    rate_3m: Decimal | None = None
    rate_6m: Decimal | None = None
    rate_12m: Decimal | None = None
    timestamp: date | None = None

    def __post_init__(self) -> None:
        """Validate interest rate quote."""
        currency = self.currency.upper()

        if len(currency) != 3 or not currency.isalpha():
            raise ValueError(
                f"Currency code must be 3 alphabetic characters (ISO 4217): " f"got {currency}"
            )

        # Validate all rates are non-negative
        for name, value in [
            ("rate_1m", self.rate_1m),
            ("rate_3m", self.rate_3m),
            ("rate_6m", self.rate_6m),
            ("rate_12m", self.rate_12m),
        ]:
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative, got {value}")

        # Normalize currency code
        object.__setattr__(self, "currency", currency)

    def get_rate(self, months: int) -> Decimal | None:
        """
        Get interest rate for specified term.

        Args:
            months: Term in months (1, 3, 6, or 12)

        Returns:
            Interest rate for the term, or None if not available

        Raises:
            ValueError: If months is not valid

        Examples:
            >>> quote = InterestRateQuote(
            ...     currency="USD",
            ...     rate_3m=Decimal("0.0525")
            ... )
            >>> quote.get_rate(3)
            Decimal('0.0525')
        """
        rate_map = {
            1: self.rate_1m,
            3: self.rate_3m,
            6: self.rate_6m,
            12: self.rate_12m,
        }

        if months not in rate_map:
            raise ValueError(f"Invalid period: {months}. Must be 1, 3, 6, or 12")

        return rate_map[months]


@dataclass(frozen=True)
class FXCarrySignal:
    """
    FX carry trade signal calculated from rate differentials.

    Represents the carry trade opportunity for a currency pair based on
    Ilmanen's methodology:
        carry = (r_base - r_quote) - ((F - S) / S)

    Attributes:
        pair: Currency pair
        spot_rate: Current spot rate
        forward_rate: Forward rate for the term
        interest_rate_diff: Interest rate differential (r_base - r_quote)
        forward_premium: Forward premium ((F - S) / S)
        carry: Carry value (interest_rate_diff - forward_premium)
        signal: Trading signal (positive = long base, negative = short base)
        timestamp: Signal calculation timestamp
        months: Forward term in months

    Raises:
        ValueError: If spot_rate or forward_rate are not positive, or signal is outside [-1, 1]

    Examples:
        >>> signal = FXCarrySignal(
        ...     pair=FXPair("AUD", "JPY"),
        ...     spot_rate=Decimal("95.50"),
        ...     forward_rate=Decimal("94.80"),
        ...     interest_rate_diff=Decimal("0.04"),
        ...     forward_premium=Decimal("-0.0073"),
        ...     carry=Decimal("0.0473"),
        ...     signal=Decimal("0.0473"),
        ...     timestamp=date.today(),
        ...     months=3
        ... )
    """

    pair: FXPair
    spot_rate: Decimal
    forward_rate: Decimal
    interest_rate_diff: Decimal
    forward_premium: Decimal
    carry: Decimal
    signal: Decimal
    timestamp: date
    months: int = 3

    def __post_init__(self) -> None:
        """Validate signal values."""
        if self.spot_rate <= 0:
            raise ValueError(f"Spot rate must be positive, got {self.spot_rate}")

        if self.forward_rate <= 0:
            raise ValueError(f"Forward rate must be positive, got {self.forward_rate}")

        if not (-1 <= self.signal <= 1):
            raise ValueError(f"Signal must be between -1 and 1, got {self.signal}")

    @property
    def is_long(self) -> bool:
        """Check if signal indicates long position in base currency."""
        return self.signal > 0

    @property
    def is_short(self) -> bool:
        """Check if signal indicates short position in base currency."""
        return self.signal < 0

    @property
    def is_neutral(self) -> bool:
        """Check if signal is neutral (zero)."""
        return self.signal == 0

    @property
    def signal_strength(self) -> str:
        """Get signal strength category."""
        abs_signal = abs(float(self.signal))
        if abs_signal >= 0.75:
            return "VERY_STRONG"
        elif abs_signal >= 0.5:
            return "STRONG"
        elif abs_signal >= 0.2:
            return "MODERATE"
        else:
            return "WEAK"

    @property
    def strength(self) -> str:
        """Get signal strength category (backward compatibility)."""
        # Map to old naming
        strength_map = {
            "VERY_STRONG": "strong",
            "STRONG": "strong",
            "MODERATE": "moderate",
            "WEAK": "weak",
        }
        return strength_map.get(self.signal_strength, "none")

    def __str__(self) -> str:
        """Return string representation of signal."""
        direction = "LONG" if self.is_long else "SHORT"
        return (
            f"{self.pair} {direction} | "
            f"Carry: {self.carry:.2%} | "
            f"Signal: {self.signal:.2%} | "
            f"Strength: {self.strength}"
        )


@dataclass(frozen=False)
class FXCarryPosition:
    """
    Active position in an FX carry trade.

    Tracks an open carry trade position with return calculations
    broken down by carry and price components.

    Attributes:
        pair: Currency pair
        quantity: Position quantity (positive = long base, negative = short base)
        entry_price: Entry spot rate
        current_price: Current spot rate
        carry_return: Return from interest rate differential (decimal)
        price_return: Return from spot rate change (decimal)
        total_return: Total return (carry_return + price_return)
        entry_date: Position entry date
        current_date: Current position update date

    Raises:
        ValueError: If prices are not positive or entry_date is after current_date

    Examples:
        >>> position = FXCarryPosition(
        ...     pair=FXPair("EUR", "USD"),
        ...     quantity=Decimal("100000"),
        ...     entry_price=Decimal("1.0850"),
        ...     current_price=Decimal("1.0900"),
        ...     carry_return=Decimal("0.0125"),
        ...     price_return=Decimal("0.0046"),
        ...     total_return=Decimal("0.0171"),
        ...     entry_date=date(2024, 1, 1),
        ...     current_date=date(2024, 2, 1)
        ... )
        >>> print(f"Position is {'LONG' if position.is_long else 'SHORT'}")
        Position is LONG
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
        """Validate position values."""
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
    def value(self) -> Decimal:
        """Calculate current position value in quote currency."""
        return abs(self.quantity) * self.current_price

    @property
    def pnl(self) -> Decimal:
        """Calculate total P&L in quote currency."""
        return abs(self.quantity) * self.entry_price * self.total_return

    @property
    def unrealized_pnl(self) -> Decimal:
        """
        Calculate unrealized P&L in quote currency.

        For long position: (current_price - entry_price) * quantity
        For short position: (entry_price - current_price) * abs(quantity)

        Returns:
            Unrealized P&L (positive = profit, negative = loss)
        """
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def days_held(self) -> int:
        """Calculate number of days position has been held."""
        return (self.current_date - self.entry_date).days

    def __str__(self) -> str:
        """Return string representation of position."""
        direction = "LONG" if self.is_long else "SHORT"
        return (
            f"{self.pair} {direction} | "
            f"Qty: {self.quantity:,.0f} | "
            f"Total Return: {self.total_return:.2%} | "
            f"Days Held: {self.days_held}"
        )


class FXCarryTradeConfig(BaseModel):
    """
    Configuration for FX Carry Trade strategy.

    Defines all configurable parameters for the carry trade strategy
    including risk limits, position sizing, and signal thresholds.

    Attributes:
        min_carry_threshold: Minimum absolute carry to generate signal
        max_positions: Maximum number of concurrent positions
        position_size: Default position size as fraction of capital
        forward_months: Forward contract term in months
        stop_loss: Stop loss threshold as decimal (e.g., 0.05 for 5%)
        take_profit: Take profit threshold as decimal
        max_leverage: Maximum leverage multiplier
        min_liquidity: Minimum liquidity requirement
        base_currency: Base currency for portfolio valuation
        allow_g10_only: If True, only trade G10 currency pairs
        min_signal_confidence: Minimum signal confidence (0-100)

    Examples:
        >>> config = FXCarryTradeConfig(
        ...     min_carry_threshold=Decimal("0.02"),
        ...     max_positions=5,
        ...     position_size=Decimal("0.1")
        ... )
        >>> print(f"Min carry: {config.min_carry_threshold:.1%}")
        Min carry: 2.0%
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # Signal generation parameters
    min_carry_threshold: Decimal = Field(
        default=Decimal("0.01"),
        description="Minimum absolute carry to generate signal (decimal)",
    )
    max_positions: int = Field(
        default=10,
        description="Maximum number of concurrent positions",
    )
    position_size: Decimal = Field(
        default=Decimal("0.1"),
        description="Default position size as fraction of capital",
    )
    forward_months: int = Field(
        default=3,
        description="Forward contract term in months",
    )

    # Risk management parameters
    stop_loss: Decimal = Field(
        default=Decimal("0.05"),
        description="Stop loss threshold (decimal)",
    )
    take_profit: Decimal = Field(
        default=Decimal("0.15"),
        description="Take profit threshold (decimal)",
    )
    max_leverage: Decimal = Field(
        default=Decimal("2.0"),
        description="Maximum leverage multiplier",
    )
    min_liquidity: Decimal = Field(
        default=Decimal("1000000"),
        description="Minimum liquidity requirement (quote currency)",
    )

    # Currency filtering
    base_currency: str = Field(
        default="USD",
        description="Base currency for portfolio valuation",
    )
    allow_g10_only: bool = Field(
        default=True,
        description="If True, only trade G10 currency pairs",
    )
    min_signal_confidence: int = Field(
        default=50,
        description="Minimum signal confidence (0-100)",
    )

    @field_validator("min_carry_threshold")
    @classmethod
    def validate_min_carry_threshold(cls, v: Decimal) -> Decimal:
        """Validate min_carry_threshold is non-negative."""
        if v < 0:
            raise ValueError("min_carry_threshold must be non-negative")
        return v

    @field_validator("max_positions")
    @classmethod
    def validate_max_positions(cls, v: int) -> int:
        """Validate max_positions is positive."""
        if v <= 0:
            raise ValueError("max_positions must be positive")
        return v

    @field_validator("position_size")
    @classmethod
    def validate_position_size(cls, v: Decimal) -> Decimal:
        """Validate position_size is between 0 and 1 (exclusive)."""
        if v <= 0 or v > 1:
            raise ValueError("position_size must be between 0 and 1")
        return v

    @field_validator("forward_months")
    @classmethod
    def validate_forward_months(cls, v: int) -> int:
        """Validate forward_months is one of 1, 3, 6, or 12."""
        if v not in [1, 3, 6, 12]:
            raise ValueError("forward_months must be 1, 3, 6, or 12")
        return v

    @field_validator("stop_loss")
    @classmethod
    def validate_stop_loss(cls, v: Decimal) -> Decimal:
        """Validate stop_loss is between 0 and 1 (exclusive)."""
        if v <= 0 or v >= 1:
            raise ValueError("stop_loss must be between 0 and 1")
        return v

    @field_validator("take_profit")
    @classmethod
    def validate_take_profit(cls, v: Decimal) -> Decimal:
        """Validate take_profit is between 0 and 1 (exclusive)."""
        if v <= 0 or v >= 1:
            raise ValueError("take_profit must be between 0 and 1")
        return v

    @field_validator("max_leverage")
    @classmethod
    def validate_max_leverage(cls, v: Decimal) -> Decimal:
        """Validate max_leverage is at least 1."""
        if v < 1:
            raise ValueError("max_leverage must be at least 1")
        return v

    @field_validator("min_liquidity")
    @classmethod
    def validate_min_liquidity(cls, v: Decimal) -> Decimal:
        """Validate min_liquidity is non-negative."""
        if v < 0:
            raise ValueError("min_liquidity must be non-negative")
        return v

    @field_validator("base_currency")
    @classmethod
    def validate_base_currency(cls, v: str) -> str:
        """Validate base currency code."""
        v = v.upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError(f"Base currency must be 3 alphabetic characters (ISO 4217): {v}")
        return v

    def get_trading_pairs(self, currencies: list[str] | None = None) -> list[FXPair]:
        """
        Get list of valid trading pairs based on configuration.

        Args:
            currencies: List of currency codes (default: G10 currencies)

        Returns:
            List of FXPair objects for valid trading
        """
        if currencies is None:
            currencies = sorted(G10_CURRENCIES)

        if self.allow_g10_only:
            currencies = [c for c in currencies if c in G10_CURRENCIES]

        pairs = []
        for currency in currencies:
            if currency != self.base_currency:
                # Create pair with base_currency as quote
                pairs.append(FXPair(currency, self.base_currency))

        return pairs

    def __str__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"FXCarryTradeConfig("
            f"min_carry={self.min_carry_threshold:.2%}, "
            f"max_positions={self.max_positions}, "
            f"position_size={self.position_size:.1%}, "
            f"forward_months={self.forward_months}, "
            f"stop_loss={self.stop_loss:.1%}, "
            f"take_profit={self.take_profit:.1%})"
        )


class CarryTradeMetrics(BaseModel):
    """
    Performance metrics for carry trade strategy.

    Tracks historical performance and risk metrics for strategy evaluation.

    Attributes:
        total_trades: Total number of trades executed
        winning_trades: Number of profitable trades
        total_return: Total portfolio return
        sharpe_ratio: Sharpe ratio of returns
        max_drawdown: Maximum drawdown experienced
        avg_carry_per_trade: Average carry return per trade
        avg_price_return_per_trade: Average price return per trade
        win_rate: Percentage of profitable trades
        best_trade: Best single trade return
        worst_trade: Worst single trade return
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    total_trades: int = Field(default=0, ge=0, description="Total number of trades")
    winning_trades: int = Field(default=0, ge=0, description="Number of winners")
    total_return: Decimal = Field(default=Decimal("0"), description="Total portfolio return")
    sharpe_ratio: Optional[Decimal] = Field(None, description="Sharpe ratio of returns")
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum drawdown")
    avg_carry_per_trade: Decimal = Field(default=Decimal("0"), description="Average carry return")
    avg_price_return_per_trade: Decimal = Field(
        default=Decimal("0"), description="Average price return"
    )
    best_trade: Decimal = Field(default=Decimal("0"), description="Best trade return")
    worst_trade: Decimal = Field(default=Decimal("0"), description="Worst trade return")

    @property
    def win_rate(self) -> Decimal:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return Decimal("0")
        return Decimal(str(self.winning_trades)) / Decimal(str(self.total_trades))

    @property
    def profit_factor(self) -> Optional[Decimal]:
        """Calculate profit factor (gross wins / gross losses)."""
        # This would need trade-by-trade data to calculate properly
        # Placeholder for future implementation
        return None
