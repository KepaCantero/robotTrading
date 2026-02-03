"""
Monte Carlo Validator Service.

Validates the Monte Carlo P5 Return criterion for strategy acceptance.
Follows Single Responsibility Principle (SOL-001).
"""

from dataclasses import dataclass
from typing import Optional

from app.backtesting.acceptance.models import CriterionResult


@dataclass
class MonteCarloValidator:
    """
    Validates Monte Carlo 5th Percentile Return criterion.

    Monte Carlo P5 Return must be >= minimum threshold (default -0.20 or -20%).
    """

    min_monte_carlo_p5: float = -0.20

    def validate(self, monte_carlo_p5_return: Optional[float]) -> CriterionResult:
        """
        Validate Monte Carlo P5 Return against threshold.

        Args:
            monte_carlo_p5_return: Monte Carlo 5th percentile return value.
                                  None is treated as 0.0 (worst case).

        Returns:
            CriterionResult with validation outcome
        """
        # Treat None as 0.0 (worst case - fails validation)
        actual_value = monte_carlo_p5_return if monte_carlo_p5_return is not None else 0.0
        passed = actual_value >= self.min_monte_carlo_p5

        return CriterionResult(
            name="Monte Carlo P5 Return",
            passed=passed,
            value=actual_value,
            threshold=self.min_monte_carlo_p5,
            description="Monte Carlo 5th percentile must be >= -20%",
        )
