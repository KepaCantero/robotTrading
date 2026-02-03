"""
Max Drawdown Validator Service.

Validates the Maximum Drawdown criterion for strategy acceptance.
Follows Single Responsibility Principle (SOL-001).
"""

from dataclasses import dataclass

from app.backtesting.acceptance.models import CriterionResult


@dataclass
class DrawdownValidator:
    """
    Validates Maximum Drawdown criterion.

    Max Drawdown must be >= threshold (less negative is better).
    Default threshold is -0.25 (-25%).
    """

    max_drawdown_threshold: float = -0.25

    def validate(self, max_drawdown: float) -> CriterionResult:
        """
        Validate Max Drawdown against threshold.

        Args:
            max_drawdown: Actual Max Drawdown value (negative percentage)

        Returns:
            CriterionResult with validation outcome
        """
        # Less negative is better (e.g., -10% is better than -30%)
        passed = max_drawdown >= self.max_drawdown_threshold

        return CriterionResult(
            name="Max Drawdown",
            passed=passed,
            value=max_drawdown,
            threshold=self.max_drawdown_threshold,
            description=f"Max Drawdown must be < {abs(self.max_drawdown_threshold) * 100}%",
        )
