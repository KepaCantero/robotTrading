"""
Profit Factor Validator Service.

Validates the Profit Factor criterion for strategy acceptance.
Follows Single Responsibility Principle (SOL-001).
"""

from dataclasses import dataclass

from app.backtesting.acceptance.models import CriterionResult


@dataclass
class ProfitFactorValidator:
    """
    Validates Profit Factor criterion.

    Profit Factor must be >= minimum threshold (default 1.3).
    """

    min_profit_factor: float = 1.3

    def validate(self, profit_factor: float) -> CriterionResult:
        """
        Validate Profit Factor against threshold.

        Args:
            profit_factor: Actual Profit Factor value

        Returns:
            CriterionResult with validation outcome
        """
        passed = profit_factor >= self.min_profit_factor

        return CriterionResult(
            name="Profit Factor",
            passed=passed,
            value=profit_factor,
            threshold=self.min_profit_factor,
            description=f"Profit Factor must be >= {self.min_profit_factor}",
        )
