"""
Sharpe Ratio Validator Service.

Validates the Sharpe Ratio criterion for strategy acceptance.
Follows Single Responsibility Principle (SOL-001).
"""

from dataclasses import dataclass

from app.backtesting.acceptance.models import CriterionResult


@dataclass
class SharpeValidator:
    """
    Validates Sharpe Ratio criterion.

    Sharpe Ratio must be >= minimum threshold (default 1.0).
    """

    min_sharpe: float = 1.0

    def validate(self, sharpe_ratio: float) -> CriterionResult:
        """
        Validate Sharpe Ratio against threshold.

        Args:
            sharpe_ratio: Actual Sharpe Ratio value

        Returns:
            CriterionResult with validation outcome
        """
        passed = sharpe_ratio >= self.min_sharpe

        return CriterionResult(
            name="Sharpe Ratio (OOS)",
            passed=passed,
            value=sharpe_ratio,
            threshold=self.min_sharpe,
            description=f"Sharpe Ratio must be >= {self.min_sharpe}",
        )
