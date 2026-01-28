"""
Capital Value Object - Trading capital allocation

Capital represents the allocated trading capital with associated
tier and risk constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from .money import Money


class CapitalTier(Enum):
    """Capital tier enumeration."""

    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    INSTITUTIONAL = "institutional"


@dataclass(frozen=True)
class Capital:
    """
    Capital value object representing trading capital allocation.

    Capital is immutable and defined by amount, tier, and constraints.
    """

    amount: Decimal
    tier: CapitalTier
    currency: str = "USD"
    max_leverage: Decimal = Decimal('1')
    max_positions: int = 10
    enabled_strategies: tuple[Any, ...] = ()

    def __post_init__(self):
        """Validate capital invariants."""
        if self.amount <= 0:
            raise ValueError("Capital amount must be positive")
        if self.max_leverage <= 0:
            raise ValueError("Max leverage must be positive")
        if self.max_positions <= 0:
            raise ValueError("Max positions must be positive")

    def get_tier(self) -> CapitalTier:
        """Get capital tier."""
        return self.tier

    def get_amount(self) -> Money:
        """Get capital amount as Money."""
        return Money(amount=self.amount, currency=self.currency)

    def get_max_exposure(self) -> Decimal:
        """Calculate maximum exposure with leverage."""
        return self.amount * self.max_leverage

    def can_add_position(self, current_positions: int) -> bool:
        """Check if new position can be added."""
        return current_positions < self.max_positions

    def is_strategy_enabled(self, strategy: str) -> bool:
        """Check if strategy is enabled for this tier."""
        return strategy in self.enabled_strategies

    @classmethod
    def from_amount(cls, amount: Decimal, currency: str = "USD") -> Capital:
        """
        Create Capital instance and determine tier from amount.

        Args:
            amount: Capital amount
            currency: Currency code

        Returns:
            Capital instance with appropriate tier
        """
        # Tier determination thresholds
        if amount < 15000:
            tier = CapitalTier.MICRO
            max_positions = 5
            max_leverage = Decimal('1')
        elif amount < 50000:
            tier = CapitalTier.SMALL
            max_positions = 8
            max_leverage = Decimal('1.5')
        elif amount < 250000:
            tier = CapitalTier.MEDIUM
            max_positions = 15
            max_leverage = Decimal('2')
        elif amount < 1000000:
            tier = CapitalTier.LARGE
            max_positions = 20
            max_leverage = Decimal('2.5')
        else:
            tier = CapitalTier.INSTITUTIONAL
            max_positions = 50
            max_leverage = Decimal('3')

        return cls(
            amount=amount,
            tier=tier,
            currency=currency,
            max_leverage=max_leverage,
            max_positions=max_positions,
        )
