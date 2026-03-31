"""
Covered Call Strategy Models.

Pydantic models for the covered call strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class Moneyness(str, Enum):
    """Option moneyness classification."""

    ITM = "in_the_money"
    ATM = "at_the_money"
    OTM = "out_of_the_money"
    DEEP_ITM = "deep_in_the_money"
    DEEP_OTM = "deep_out_of_the_money"


class AssignmentProbability(str, Enum):
    """Probability of option assignment."""

    VERY_LOW = "very_low"  # < 10%
    LOW = "low"  # 10-25%
    MODERATE = "moderate"  # 25-50%
    HIGH = "high"  # 50-75%
    VERY_HIGH = "very_high"  # > 75%


class RollType(str, Enum):
    """Types of covered call roll operations."""

    ROLL_OUT = "roll_out"  # Extend to later expiry
    ROLL_UP = "roll_up"  # Roll to higher strike
    ROLL_DOWN = "roll_down"  # Roll to lower strike
    ROLL_OUT_UP = "roll_out_up"  # Extend expiry and higher strike
    ROLL_OUT_DOWN = "roll_out_down"  # Extend expiry and lower strike
    CLOSE = "close"  # Close position without rolling


@dataclass
class OptionGreeks:
    """
    Option Greeks (sensitivities).

    Attributes:
        delta: Price sensitivity to underlying
        gamma: Delta sensitivity to underlying
        theta: Price sensitivity to time (daily decay)
        vega: Price sensitivity to volatility
        rho: Price sensitivity to interest rate
    """

    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal
    rho: Decimal = Decimal("0")


@dataclass
class CallOption:
    """
    Call option data for covered call screening.

    Attributes:
        symbol: Underlying symbol
        strike: Strike price
        expiry: Expiration date
        bid: Bid price
        ask: Ask price
        mid_price: Mid price (bid+ask)/2
        implied_volatility: Implied volatility
        delta: Option delta
        days_to_expiry: Days until expiration
        underlying_price: Current underlying price
    """

    symbol: str
    strike: Decimal
    expiry: date
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid_price: Decimal | None = None
    implied_volatility: Decimal | None = None
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    volume: int | None = None
    open_interest: int | None = None
    days_to_expiry: int = 0
    underlying_price: Decimal | None = None
    moneyness: Moneyness = Moneyness.ATM
    expiry_date: date | None = None  # Alias for expiry

    def __post_init__(self):
        """Set expiry_date alias if not provided."""
        if self.expiry_date is None:
            self.expiry_date = self.expiry

    @property
    def is_itm(self) -> bool:
        """Check if option is in the money."""
        if self.underlying_price is None:
            return False
        return self.strike < self.underlying_price

    @property
    def is_otm(self) -> bool:
        """Check if option is out of the money."""
        if self.underlying_price is None:
            return False
        return self.strike > self.underlying_price


@dataclass
class CoveredCallConfig:
    """
    Configuration for covered call strategy.

    Attributes:
        max_position_size: Maximum position size as fraction
        max_contracts_per_position: Maximum contracts per position
        min_shares_required: Minimum shares to write a call
        target_dte: Target days to expiry
        target_otm_pct: Target OTM percentage
        min_premium_pct: Minimum premium to collect
        roll_threshold_days: Days before recommending roll
        roll_threshold_itm: Threshold ITM for recommending roll
        roll_threshold_otm: Threshold OTM for recommending roll
        assignment_probability_threshold: Assignment probability threshold
        auto_roll: Enable automatic rolling
        avoid_earnings: Avoid positions before earnings
    """

    max_position_size: Decimal = Decimal("0.10")
    max_contracts_per_position: int = 10
    min_shares_required: int = 100
    target_dte: int = 30
    target_otm_pct: Decimal = Decimal("0.03")
    min_premium_pct: Decimal = Decimal("0.01")
    roll_threshold_days: int = 7
    roll_threshold_itm: Decimal = Decimal("0.02")
    roll_threshold_otm: Decimal = Decimal("0.05")
    assignment_probability_threshold: AssignmentProbability = AssignmentProbability.HIGH
    auto_roll: bool = False
    avoid_earnings: bool = True


@dataclass
class CoveredCallPosition:
    """
    Active covered call position.

    Attributes:
        symbol: Underlying symbol
        shares_owned: Number of shares owned
        average_cost: Average cost per share
        call_option: Call option sold
        contracts_sold: Number of contracts sold
        premium_received: Premium received per share
        total_premium: Total premium collected
        opened_at: Date position opened
        assignment_probability: Probability of assignment
        current_price: Current underlying price
    """

    symbol: str
    shares_owned: int
    average_cost: Decimal
    call_option: CallOption
    contracts_sold: int
    premium_received: Decimal
    total_premium: Decimal
    opened_at: date
    assignment_probability: AssignmentProbability = AssignmentProbability.LOW
    current_price: Decimal | None = None
    current_option_price: Decimal | None = None
    current_delta: Decimal | None = None
    expected_return: Decimal | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def break_even_price(self) -> Decimal:
        """Calculate break-even price."""
        return self.average_cost - self.premium_received

    @property
    def return_if_unchanged(self) -> Decimal:
        """Calculate return if price unchanged."""
        if self.current_price is None or self.current_price == Decimal("0"):
            return Decimal("0")
        return self.premium_received / self.current_price

    @property
    def net_cost(self) -> Decimal:
        """Calculate net cost of the position (average cost minus premium received)."""
        return self.average_cost - self.premium_received

    @property
    def total_value(self) -> Decimal | None:
        """Calculate total value of the position based on current price."""
        if self.current_price is None:
            return None
        return self.current_price * self.shares_owned + self.total_premium


@dataclass
class RollDecision:
    """
    Decision on whether to roll a covered call position.

    Attributes:
        should_roll: Whether to roll the position
        roll_type: Type of roll to execute
        new_strike: New strike price (if rolling)
        new_expiry: New expiration date (if rolling)
        confidence: Confidence in the decision (0-100)
        reason: Reasoning behind the decision
    """

    should_roll: bool
    roll_type: RollType | None = None
    new_strike: Decimal | None = None
    new_expiry: date | None = None
    new_option: CallOption | None = None
    additional_premium: Decimal | None = None
    confidence: Decimal = Decimal("0")
    reason: str = ""


@dataclass
class RollOpportunity:
    """
    Roll opportunity for a covered call position.

    Attributes:
        position: Current covered call position
        new_option: New option to roll into
        roll_type: Type of roll
        additional_premium: Additional premium from roll
        days_to_expiry_new: Days to new expiry
        reason: Reason for this roll opportunity
        expected_benefit: Expected benefit description
        probability_delta: Change in probability
    """

    position: CoveredCallPosition
    new_option: CallOption
    roll_type: RollType
    additional_premium: Decimal
    days_to_expiry_new: int
    reason: str = ""
    expected_benefit: str = ""
    probability_delta: str = ""


@dataclass
class OptionScreeningCriteria:
    """
    Screening criteria for covered call options.

    Attributes:
        min_days_to_expiry: Minimum days to expiry
        max_days_to_expiry: Maximum days to expiry
        min_moneyness: Minimum moneyness (as OTM %)
        max_moneyness: Maximum moneyness (as OTM %)
        min_premium: Minimum premium (as % of underlying)
        min_open_interest: Minimum open interest
        min_volume: Minimum daily volume
    """

    min_days_to_expiry: int = 30
    max_days_to_expiry: int = 45
    min_moneyness: Decimal = Decimal("0.02")  # 2% OTM minimum
    max_moneyness: Decimal = Decimal("0.05")  # 5% OTM maximum
    min_premium: Decimal = Decimal("0.01")  # 1% premium minimum
    min_open_interest: int = 100
    min_volume: int = 10
    target_delta: Decimal | None = None
    max_theta_decay: Decimal | None = None
    avoid_earnings: bool = True
    avoid_events: bool = True


@dataclass
class OptionScreenerResult:
    """
    Result of option screening operation.

    Attributes:
        symbol: Underlying symbol
        underlying_price: Current price
        options_passed: Options that passed screening
        options_failed: Options that failed with reasons
        total_evaluated: Total options evaluated
        screening_time_ms: Screening time in milliseconds
        criteria: Criteria used for screening
    """

    symbol: str
    underlying_price: Decimal
    options_passed: list[CallOption]
    options_failed: dict[str, list[str]]
    total_evaluated: int
    screening_time_ms: float
    criteria: OptionScreeningCriteria

    @property
    def pass_rate(self) -> float:
        """Calculate the percentage of options that passed screening."""
        if self.total_evaluated == 0:
            return 0.0
        return (len(self.options_passed) / self.total_evaluated) * 100.0

    @property
    def best_option(self) -> CallOption | None:
        """Get the best option from passed options."""
        if not self.options_passed:
            return None
        return max(self.options_passed, key=lambda opt: opt.mid_price or Decimal("0"))
