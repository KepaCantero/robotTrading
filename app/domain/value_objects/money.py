"""
Money Value Object - Immutable monetary value

Money is a value object representing a monetary amount with currency.
It is immutable and defined by its attributes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Money:
    """
    Money value object representing a monetary amount.

    Money is immutable and defined by amount and currency.
    All operations return new Money instances.
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        """Validate money invariants."""
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency cannot be empty")

    def __add__(self, other: Any) -> Money:
        """Add two Money instances."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: Any) -> Money:
        """Subtract two Money instances."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Result cannot be negative")
        return Money(amount=result, currency=self.currency)

    def __mul__(self, multiplier: Any) -> Money:
        """Multiply Money by a scalar."""
        if not isinstance(multiplier, (int, float, Decimal)):
            return NotImplemented
        result = self.amount * Decimal(str(multiplier))
        if result < 0:
            raise ValueError("Result cannot be negative")
        return Money(amount=result, currency=self.currency)

    def __truediv__(self, divisor: Any) -> Money:
        """Divide Money by a scalar."""
        if not isinstance(divisor, (int, float, Decimal)):
            return NotImplemented
        if divisor == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return Money(amount=self.amount / Decimal(str(divisor)), currency=self.currency)

    def __eq__(self, other: Any) -> bool:
        """Compare Money instances."""
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: Any) -> bool:
        """Less than comparison."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount < other.amount

    def __le__(self, other: Any) -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount <= other.amount

    def __gt__(self, other: Any) -> bool:
        """Greater than comparison."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount > other.amount

    def __ge__(self, other: Any) -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount >= other.amount

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash((self.amount, self.currency))

    def __str__(self) -> str:
        """String representation."""
        return f"{self.amount} {self.currency}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Money(amount={self.amount}, currency='{self.currency}')"

    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == 0

    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > 0

    def to_float(self) -> float:
        """Convert amount to float."""
        return float(self.amount)
