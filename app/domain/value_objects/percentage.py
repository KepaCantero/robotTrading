"""
Percentage Value Object - Immutable percentage representation

Percentage is a value object representing a percentage with validation
and arithmetic operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Percentage:
    """
    Percentage value object.

    Represents a percentage with validation and arithmetic operations.
    Immutable and defined by its value.
    """

    value: Decimal

    def __post_init__(self):
        """Validate percentage invariants."""
        if self.value < 0:
            raise ValueError("Percentage cannot be negative")
        if self.value > 100:
            raise ValueError("Percentage cannot exceed 100")

    @classmethod
    def from_decimal(cls, decimal_value: Decimal) -> Percentage:
        """Create percentage from decimal (0.5 -> 50%)."""
        return cls(value=decimal_value * Decimal("100"))

    @classmethod
    def from_float(cls, float_value: float) -> Percentage:
        """Create percentage from float (0.5 -> 50%)."""
        return cls(value=Decimal(str(float_value)) * Decimal("100"))

    @classmethod
    def from_percent(cls, percent_value: Decimal | str | int | float) -> Percentage:
        """Create percentage from percent value (50 -> 50%)."""
        if isinstance(percent_value, str):
            return cls(value=Decimal(percent_value))
        elif isinstance(percent_value, (int, float)):
            return cls(value=Decimal(str(percent_value)))
        return cls(value=percent_value)

    @classmethod
    def zero(cls) -> Percentage:
        """Create zero percentage."""
        return cls(value=Decimal("0"))

    @property
    def as_decimal(self) -> Decimal:
        """Get percentage as decimal (50% -> 0.5)."""
        return self.value / Decimal("100")

    @property
    def as_float(self) -> float:
        """Get percentage as float (50% -> 0.5)."""
        return float(self.as_decimal)

    def add(self, other: Percentage) -> Percentage:
        """Add two percentages."""
        return Percentage(value=self.value + other.value)

    def subtract(self, other: Percentage) -> Percentage:
        """Subtract two percentages."""
        result = self.value - other.value
        if result < 0:
            raise ValueError("Result cannot be negative")
        return Percentage(value=result)

    def multiply(self, multiplier: Decimal | int | float) -> Percentage:
        """Multiply percentage by scalar."""
        mult = Decimal(str(multiplier))
        result = self.value * mult
        if result > 100:
            raise ValueError("Result cannot exceed 100%")
        return Percentage(value=result)

    def apply_to(self, amount: Decimal) -> Decimal:
        """Apply percentage to amount."""
        return amount * self.as_decimal

    def is_zero(self) -> bool:
        """Check if percentage is zero."""
        return self.value == 0

    def is_positive(self) -> bool:
        """Check if percentage is positive."""
        return self.value > 0

    def __add__(self, other: Any) -> Percentage:
        """Add two percentages."""
        if not isinstance(other, Percentage):
            return NotImplemented
        return self.add(other)

    def __sub__(self, other: Any) -> Percentage:
        """Subtract two percentages."""
        if not isinstance(other, Percentage):
            return NotImplemented
        return self.subtract(other)

    def __mul__(self, other: Any) -> Percentage:
        """Multiply percentage by scalar."""
        if not isinstance(other, (int, float, Decimal)):
            return NotImplemented
        return self.multiply(other)

    def __eq__(self, other: Any) -> bool:
        """Compare percentages."""
        if not isinstance(other, Percentage):
            return False
        return self.value == other.value

    def __lt__(self, other: Any) -> bool:
        """Less than comparison."""
        if not isinstance(other, Percentage):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: Any) -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, Percentage):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: Any) -> bool:
        """Greater than comparison."""
        if not isinstance(other, Percentage):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: Any) -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, Percentage):
            return NotImplemented
        return self.value >= other.value

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash(self.value)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.value}%"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Percentage(value={self.value})"


@dataclass(frozen=True)
class Weight:
    """
    Weight value object for portfolio weights.

    Similar to Percentage but allows 0-1 range for internal calculations.
    """

    value: Decimal

    def __post_init__(self):
        """Validate weight invariants."""
        if self.value < 0:
            raise ValueError("Weight cannot be negative")
        if self.value > 1:
            raise ValueError("Weight cannot exceed 1")

    @classmethod
    def from_percent(cls, percent: Percentage) -> Weight:
        """Create weight from percentage."""
        return Weight(value=percent.as_decimal)

    @classmethod
    def from_decimal(cls, decimal_value: Decimal) -> Weight:
        """Create weight from decimal."""
        return cls(value=decimal_value)

    @property
    def as_percentage(self) -> Percentage:
        """Convert to percentage."""
        return Percentage(value=self.value * Decimal("100"))

    def is_valid_for_portfolio(self) -> bool:
        """Check if weight is valid for portfolio (0-1)."""
        return Decimal("0") <= self.value <= Decimal("1")

    def __eq__(self, other: Any) -> bool:
        """Compare weights."""
        if not isinstance(other, Weight):
            return False
        return self.value == other.value

    def __str__(self) -> str:
        """String representation."""
        return f"{self.as_percentage}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Weight(value={self.value})"
