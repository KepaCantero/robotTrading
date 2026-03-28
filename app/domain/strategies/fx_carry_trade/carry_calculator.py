"""
Carry Trade Calculator for FX Strategy.

This module implements the core carry trade calculations based on Antti
Ilmanen's methodology from "Expected Returns" - Rule 12.9:

    carry = (r_base - r_quote) - ((F - S) / S)

Where:
    - r_base: Interest rate of base currency
    - r_quote: Interest rate of quote currency
    - F: Forward rate
    - S: Spot rate

The module provides:
- Forward premium calculation
- Carry calculation
- Signal generation with tanh saturation
- Signal filtering and ranking
- Opportunity identification
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from app.domain.strategies.fx_carry_trade.models import FXCarrySignal, FXPair

if TYPE_CHECKING:
    from collections.abc import Mapping

    from app.domain.strategies.fx_carry_trade.fx_rates_provider import FXRateProvider

logger = logging.getLogger(__name__)

# Valid forward contract months
VALID_MONTHS = {1, 3, 6, 12}


@dataclass
class CarryTradeOpportunity:
    """
    Identified carry trade opportunity.

    Represents a potential carry trade with expected returns and
    confidence metrics.

    Attributes:
        pair: Currency pair
        expected_carry: Expected carry return (annualized)
        forward_premium: Forward premium/discount
        signal: Trading signal strength
        confidence: Confidence score (0-100)

    Examples:
        >>> opp = CarryTradeOpportunity(
        ...     pair=FXPair("AUD", "JPY"),
        ...     expected_carry=Decimal("0.0473"),
        ...     forward_premium=Decimal("-0.0073"),
        ...     signal=Decimal("0.8"),
        ...     confidence=75.0
        ... )
        >>> opp.is_actionable
        True
    """

    pair: FXPair
    expected_carry: Decimal
    forward_premium: Decimal
    signal: Decimal
    confidence: float

    @property
    def is_actionable(self) -> bool:
        """
        Check if opportunity is actionable based on confidence threshold.

        Returns:
            True if confidence > 60, False otherwise
        """
        return self.confidence > 60.0


class CarryCalculator:
    """
    Calculator for FX carry trade signals and opportunities.

    Implements Ilmanen's carry trade methodology with configurable
    thresholds and signal multiplier for tanh saturation.

    Attributes:
        signal_threshold: Minimum absolute carry to generate a signal
        signal_multiplier: Multiplier for tanh function in signal calculation

    Examples:
        >>> calculator = CarryCalculator(
        ...     signal_threshold=Decimal("0.01"),
        ...     signal_multiplier=10.0
        ... )
    """

    def __init__(
        self,
        signal_threshold: Optional[Decimal] = None,
        signal_multiplier: float = 10.0,
    ) -> None:
        """
        Initialize the carry calculator.

        Args:
            signal_threshold: Minimum absolute carry for signal generation (non-negative)
            signal_multiplier: Multiplier for tanh function (positive)

        Raises:
            ValueError: If signal_threshold is negative or signal_multiplier is not positive
        """
        if signal_threshold is None:
            signal_threshold = Decimal("0.01")
        if signal_threshold < 0:
            raise ValueError(f"signal_threshold must be non-negative, got {signal_threshold}")

        if signal_multiplier <= 0:
            raise ValueError(f"signal_multiplier must be positive, got {signal_multiplier}")

        self.signal_threshold: Decimal = signal_threshold
        self.signal_multiplier: float = signal_multiplier

        logger.info(
            f"CarryCalculator initialized with "
            f"signal_threshold={signal_threshold:.2%}, "
            f"signal_multiplier={signal_multiplier}"
        )

    def calculate_forward_premium(self, spot_rate: Decimal, forward_rate: Decimal) -> Decimal:
        """
        Calculate forward premium from spot and forward rates.

        The forward premium represents the percentage difference between
        the forward rate and the spot rate.

        Formula: (forward_rate - spot_rate) / spot_rate

        Args:
            spot_rate: Current spot rate (must be positive)
            forward_rate: Forward rate (must be positive)

        Returns:
            Forward premium as decimal (positive = forward premium,
            negative = forward discount)

        Raises:
            ValueError: If rates are not positive

        Examples:
            >>> calculator = CarryCalculator()
            >>> premium = calculator.calculate_forward_premium(
            ...     spot_rate=Decimal("1.0850"),
            ...     forward_rate=Decimal("1.0875")
            ... )
            >>> premium
            Decimal('0.002304147')
        """
        if spot_rate <= 0:
            raise ValueError(f"spot_rate must be positive, got {spot_rate}")

        if forward_rate <= 0:
            raise ValueError(f"forward_rate must be positive, got {forward_rate}")

        forward_premium = (forward_rate - spot_rate) / spot_rate
        return forward_premium

    def calculate_carry(
        self,
        interest_rate_diff: Decimal,
        forward_premium: Decimal,
    ) -> Decimal:
        """
        Calculate carry trade return based on Ilmanen's formula.

        Formula: carry = interest_rate_diff - forward_premium

        Args:
            interest_rate_diff: Interest rate differential (r_base - r_quote)
            forward_premium: Forward premium ((F - S) / S)

        Returns:
            Carry value as decimal (positive = favorable for long base)

        Examples:
            >>> calculator = CarryCalculator()
            >>> carry = calculator.calculate_carry(
            ...     interest_rate_diff=Decimal("0.04"),
            ...     forward_premium=Decimal("-0.0073")
            ... )
            >>> carry
            Decimal('0.0473')
        """
        carry = interest_rate_diff - forward_premium
        return carry

    def calculate_signal(self, carry: Decimal) -> float:
        """
        Calculate trading signal from carry value using tanh saturation.

        Formula:
            - If abs(carry) <= signal_threshold: return 0.0
            - Otherwise: return tanh(carry * signal_multiplier)

        The tanh function provides saturation in [-1, 1], preventing
        extreme signal values.

        Args:
            carry: Calculated carry value

        Returns:
            Signal value as float in range [-1, 1]

        Examples:
            >>> calculator = CarryCalculator(
            ...     signal_threshold=Decimal("0.01"),
            ...     signal_multiplier=10.0
            ... )
            >>> signal = calculator.calculate_signal(Decimal("0.05"))
            >>> abs(signal) < 1.0
            True
        """
        # If carry is at or below threshold, return 0
        if abs(carry) <= self.signal_threshold:
            return 0.0

        # Apply tanh for saturation in [-1, 1]
        signal = math.tanh(float(carry) * self.signal_multiplier)
        return signal

    def calculate_signal_full(
        self,
        pair: FXPair,
        spot_rate: Decimal,
        forward_rate: Decimal,
        interest_rate_diff: Decimal,
        timestamp: date,
        months: int,
    ) -> FXCarrySignal:
        """
        Calculate a complete carry trade signal for a currency pair.

        This method computes all components of the carry trade signal:
        1. Forward premium
        2. Carry value
        3. Trading signal (using tanh saturation)

        Args:
            pair: Currency pair
            spot_rate: Current spot rate
            forward_rate: Forward rate for the term
            interest_rate_diff: Interest rate differential (r_base - r_quote)
            timestamp: Calculation date
            months: Forward term in months (must be 1, 3, 6, or 12)

        Returns:
            FXCarrySignal with all calculated components

        Raises:
            ValueError: If rates are invalid or months is not valid

        Examples:
            >>> calculator = CarryCalculator()
            >>> signal = calculator.calculate_signal_full(
            ...     pair=FXPair("USD", "JPY"),
            ...     spot_rate=Decimal("110.50"),
            ...     forward_rate=Decimal("110.20"),
            ...     interest_rate_diff=Decimal("0.025"),
            ...     timestamp=date(2024, 1, 15),
            ...     months=3
            ... )
        """
        # Validate inputs
        if spot_rate <= 0:
            raise ValueError(f"spot_rate must be positive, got {spot_rate}")

        if forward_rate <= 0:
            raise ValueError(f"forward_rate must be positive, got {forward_rate}")

        if months not in VALID_MONTHS:
            raise ValueError(f"months must be 1, 3, 6, or 12, got {months}")

        # Calculate forward premium
        forward_premium = self.calculate_forward_premium(spot_rate, forward_rate)

        # Calculate carry
        carry = self.calculate_carry(interest_rate_diff, forward_premium)

        # Calculate signal using tanh
        signal_value = self.calculate_signal(carry)

        # Convert signal to Decimal for FXCarrySignal
        signal_decimal = Decimal(str(signal_value))

        return FXCarrySignal(
            pair=pair,
            spot_rate=spot_rate,
            forward_rate=forward_rate,
            interest_rate_diff=interest_rate_diff,
            forward_premium=forward_premium,
            carry=carry,
            signal=signal_decimal,
            timestamp=timestamp,
            months=months,
        )

    def filter_signals(
        self,
        signals: Mapping[FXPair, FXCarrySignal],
        min_abs_signal: Decimal,
    ) -> dict[FXPair, FXCarrySignal]:
        """
        Filter signals by minimum absolute signal value.

        Args:
            signals: Dictionary of signals to filter
            min_abs_signal: Minimum absolute signal value

        Returns:
            Filtered dictionary of signals

        Examples:
            >>> calculator = CarryCalculator()
            >>> filtered = calculator.filter_signals(
            ...     signals,
            ...     min_abs_signal=Decimal("0.3")
            ... )
        """
        filtered = {
            pair: signal for pair, signal in signals.items() if abs(signal.signal) >= min_abs_signal
        }

        logger.debug(f"Filtered signals: {len(signals)} -> {len(filtered)}")
        return filtered

    def rank_signals(
        self,
        signals: Mapping[FXPair, FXCarrySignal],
    ) -> list[tuple[FXPair, FXCarrySignal]]:
        """
        Rank signals by absolute carry value (descending).

        Args:
            signals: Dictionary of signals to rank

        Returns:
            List of (pair, signal) tuples sorted by abs(carry) descending

        Examples:
            >>> calculator = CarryCalculator()
            >>> ranked = calculator.rank_signals(signals)
            >>> ranked[0]  # Highest carry signal
            (FXPair(...), FXCarrySignal(...))
        """
        ranked = sorted(
            signals.items(),
            key=lambda item: abs(float(item[1].carry)),
            reverse=True,
        )

        return ranked

    def calculate_signals_from_provider(
        self,
        pairs: list[FXPair],
        provider: FXRateProvider,
        as_of: date,
        months: int = 3,
    ) -> dict[FXPair, FXCarrySignal]:
        """
        Calculate carry signals for multiple pairs from a rate provider.

        Args:
            pairs: List of currency pairs to analyze
            provider: FX rate data provider
            as_of: Calculation date
            months: Forward term in months

        Returns:
            Dictionary mapping pairs to their signals

        Examples:
            >>> from app.domain.strategies.fx_carry_trade import InMemoryFXRateProvider
            >>> provider = InMemoryFXRateProvider()
            >>> calculator = CarryCalculator()
            >>> pairs = [FXPair("EUR", "USD"), FXPair("USD", "JPY")]
            >>> signals = calculator.calculate_signals_from_provider(
            ...     pairs=pairs,
            ...     provider=provider,
            ...     as_of=date.today(),
            ...     months=3
            ... )
        """
        signals = {}

        for pair in pairs:
            try:
                # Get rates from provider
                spot_rate = provider.get_spot_rate(pair, as_of)
                forward_rate = provider.get_forward_rate(pair, as_of, months)

                # Get interest rates
                base_rate = provider.get_interest_rate(pair.base_currency, as_of, months)
                quote_rate = provider.get_interest_rate(pair.quote_currency, as_of, months)

                # Calculate interest rate differential
                interest_rate_diff = base_rate - quote_rate

                # Calculate full signal
                signal = self.calculate_signal_full(
                    pair=pair,
                    spot_rate=spot_rate,
                    forward_rate=forward_rate,
                    interest_rate_diff=interest_rate_diff,
                    timestamp=as_of,
                    months=months,
                )

                signals[pair] = signal

            except ValueError as e:
                logger.warning(f"Could not calculate signal for {pair}: {e}")
                continue

        logger.info(f"Calculated {len(signals)} signals from provider")
        return signals

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"CarryCalculator("
            f"signal_threshold={self.signal_threshold}, "
            f"signal_multiplier={self.signal_multiplier})"
        )
