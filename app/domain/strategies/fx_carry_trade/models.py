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

    def __init__(self, base_currency: str, quote_currency: str) -> None:
        """
        Initialize FXPair.

        Args:
            base_currency: Base currency code (3-letter ISO)
            quote_currency: Quote currency code (3-letter ISO)
        """
        self.base_currency = base_currency.upper()
        self.quote_currency = quote_currency.upper()

    def __str__(self) -> str:
        """Return string representation as BASE/QUOTE."""
        return f"{self.base_currency}/{self.quote_currency}"

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"FXPair({self.base_currency!r}, {self.quote_currency!r})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another FXPair."""
        if not isinstance(other, FXPair):
            return NotImplemented
        return (
            self.base_currency == other.base_currency
            and self.quote_currency == other.quote_currency
        )

    def __hash__(self) -> int:
        """Return hash for use in sets and dicts."""
        return hash((self.base_currency, self.quote_currency))


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

    @property
    def is_long_signal(self) -> bool:
        """Check if signal suggests going long the base currency."""
        return self.signal > 0

    @property
    def signal_strength(self) -> str:
        """Return signal strength as string."""
        abs_signal = abs(self.signal)
        if abs_signal >= 0.7:
            return "STRONG"
        if abs_signal >= 0.4:
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
        direction: Position direction (LONG or SHORT base currency)
        size: Position size in base currency units
        entry_spot: Spot rate at position open
        entry_forward: Forward rate at position open
        carry_rate: Carry rate at entry
        opened_at: Position open date
        target_carry: Target carry to realize
        stop_loss: Stop loss level (as spot rate)
        take_profit: Take profit level (as spot rate)
    """

    pair: FXPair
    direction: str
    size: Decimal
    entry_spot: Decimal
    entry_forward: Decimal
    carry_rate: Decimal
    opened_at: date
    target_carry: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None

    @property
    def is_long(self) -> bool:
        """Check if position is long base currency."""
        return self.direction.upper() == "LONG"


@dataclass
class FXCarryTradeConfig:
    """
    Configuration for FX Carry Trade strategy.

    Attributes:
        signal_threshold: Minimum carry to generate signal
        signal_multiplier: Multiplier for tanh function
        min_confidence: Minimum confidence for actionable signals
        max_positions: Maximum simultaneous positions
        position_size: Default position size as % of portfolio
        stop_loss_pct: Stop loss percentage
        take_profit_pct: Take profit percentage
    """

    signal_threshold: Decimal = Decimal("0.01")
    signal_multiplier: float = 10.0
    min_confidence: float = 60.0
    max_positions: int = 5
    position_size: Decimal = Decimal("0.05")
    stop_loss_pct: Decimal = Decimal("0.05")
    take_profit_pct: Decimal = Decimal("0.10")


@dataclass
class FXRateQuote:
    """
    FX rate quote with spot and forward rates.

    Attributes:
        pair: Currency pair
        spot_rate: Current spot rate
        forward_3m: 3-month forward rate (optional)
        forward_6m: 6-month forward rate (optional)
        forward_12m: 12-month forward rate (optional)
        timestamp: Quote timestamp
    """

    pair: FXPair
    spot_rate: Decimal
    forward_3m: Decimal | None = None
    forward_6m: Decimal | None = None
    forward_12m: Decimal | None = None
    timestamp: date | None = None

    @property
    def has_forward_rates(self) -> bool:
        """Check if any forward rates are available."""
        return any([self.forward_3m, self.forward_6m, self.forward_12m])


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
