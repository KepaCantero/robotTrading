"""
Portfolio Optimization Entity - Domain Layer

This entity represents a portfolio optimization result.
It's a pure domain entity with no infrastructure dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class PortfolioOptimization:
    """
    Portfolio optimization result.

    This is a domain entity that contains the results of portfolio
    optimization combining multiple methodologies (Chan, Narang, Hull).

    Invariant: weights must sum to approximately 1.0 (portfolio constraint).
    """

    weights: dict[str, Decimal]
    expected_return: float
    expected_risk: float
    sharpe_ratio: float

    # Ernest Chan - Regime information
    regime: str = "UNKNOWN"

    # Narang - Factor exposures
    factor_exposures: dict[str, float] = field(default_factory=dict)

    # Hull - Risk metrics
    var_95: float | None = None

    def __post_init__(self) -> None:
        """
        Validate portfolio weights sum to approximately 1.0.

        Raises:
            ValueError: If weights are empty or don't sum to 1.0 (±0.01 tolerance).

        This enforces the fundamental portfolio constraint that all weights
        must sum to 100% of the portfolio allocation.
        """
        if not self.weights:
            raise ValueError("Portfolio weights cannot be empty")

        total_weight = sum(self.weights.values())

        # Allow small tolerance for floating point arithmetic
        tolerance = Decimal("0.01")
        if abs(total_weight - Decimal("1.0")) > tolerance:
            raise ValueError(
                f"Portfolio weights must sum to 1.0 (±{tolerance}), " f"got {total_weight:.4f}"
            )

    def get_weight_summary(self) -> dict[str, str]:
        """Get a formatted summary of portfolio weights."""
        return {symbol: f"{weight:.4f}" for symbol, weight in self.weights.items()}

    def get_top_positions(self, n: int = 5) -> list[tuple[str, Decimal]]:
        """Get the top N positions by weight."""
        sorted_positions = sorted(self.weights.items(), key=lambda x: x[1], reverse=True)
        return sorted_positions[:n]

    def get_risk_metrics(self) -> dict[str, float]:
        """Get all risk metrics in one summary."""
        return {
            "expected_return": self.expected_return,
            "expected_risk": self.expected_risk,
            "sharpe_ratio": self.sharpe_ratio,
            "var_95": self.var_95 or 0.0,
        }

    def get_regime_info(self) -> dict[str, Any]:
        """Get regime-related information."""
        return {
            "regime": self.regime,
            "factor_exposures": self.factor_exposures,
        }

    def is_efficient(self) -> bool:
        """Check if the portfolio is efficient (high Sharpe ratio)."""
        return self.sharpe_ratio >= 1.0

    def is_diversified(self) -> bool:
        """Check if the portfolio is adequately diversified."""
        if not self.weights:
            return False

        # Check that no single position exceeds 30% of portfolio
        max_weight = max(self.weights.values())
        return max_weight <= Decimal("0.3")
