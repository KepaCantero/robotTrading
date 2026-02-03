"""
Investment Horizon Value Object - Time period for investments

InvestmentHorizon represents the time period of an investment with validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HorizonCategory(str, Enum):
    """Investment horizon categories for classification."""

    VERY_SHORT_TERM = "very_short_term"  # < 6 months
    SHORT_TERM = "short_term"  # 6-12 months
    MEDIUM_TERM = "medium_term"  # 1-3 years
    LONG_TERM = "long_term"  # 3-10 years
    VERY_LONG_TERM = "very_long_term"  # > 10 years


@dataclass(frozen=True)
class InvestmentHorizon:
    """
    Investment horizon value object.

    Represents the time period for an investment with validation
    and categorization capabilities.
    """

    months: int

    def __post_init__(self):
        """Validate horizon invariants."""
        if self.months <= 0:
            raise ValueError("Investment horizon must be positive")
        if self.months > 600:  # 50 years max
            raise ValueError("Investment horizon cannot exceed 600 months (50 years)")

    @property
    def years(self) -> float:
        """Get horizon in years."""
        return round(self.months / 12, 2)

    @property
    def category(self) -> HorizonCategory:
        """Get horizon category for risk assessment."""
        if self.months < 6:
            return HorizonCategory.VERY_SHORT_TERM
        elif self.months < 12:
            return HorizonCategory.SHORT_TERM
        elif self.months < 36:
            return HorizonCategory.MEDIUM_TERM
        elif self.months < 120:
            return HorizonCategory.LONG_TERM
        else:
            return HorizonCategory.VERY_LONG_TERM

    @property
    def is_short_term(self) -> bool:
        """Check if horizon is short term (< 12 months)."""
        return self.months < 12

    @property
    def is_long_term(self) -> bool:
        """Check if horizon is long term (> 3 years)."""
        return self.months > 36

    def allows_high_risk(self) -> bool:
        """
        Determine if horizon allows for high-risk strategies.

        Longer horizons can tolerate more volatility.
        """
        return self.months >= 12

    def allows_very_high_risk(self) -> bool:
        """
        Determine if horizon allows for very high-risk strategies.

        Only very long horizons should use aggressive strategies.
        """
        return self.months >= 36

    @classmethod
    def from_months(cls, months: int) -> InvestmentHorizon:
        """Create from months."""
        return cls(months=months)

    @classmethod
    def from_years(cls, years: int | float) -> InvestmentHorizon:
        """Create from years."""
        months = int(years * 12)
        return cls(months=months)

    def __str__(self) -> str:
        """String representation."""
        if self.months < 12:
            return f"{self.months} months"
        else:
            return f"{self.years} years"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"InvestmentHorizon(months={self.months}, category='{self.category.value}')"
