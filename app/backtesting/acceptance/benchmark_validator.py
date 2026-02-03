"""
Benchmark Comparison Validator Service.

Validates the excess return vs benchmark criterion for strategy acceptance.
Follows Single Responsibility Principle (SOL-001).
"""

from dataclasses import dataclass

from app.backtesting.acceptance.models import CriterionResult


@dataclass
class BenchmarkComparisonValidator:
    """
    Validates Excess Return vs Benchmark criterion.

    Strategy must outperform benchmark by minimum threshold (default 0.03 or 3%).
    """

    min_excess_return: float = 0.03

    def validate(self, strategy_return: float, benchmark_return: float) -> CriterionResult:
        """
        Validate excess return against threshold.

        Args:
            strategy_return: Strategy total return
            benchmark_return: Benchmark total return

        Returns:
            CriterionResult with validation outcome
        """
        excess_return = strategy_return - benchmark_return
        passed = excess_return >= self.min_excess_return

        return CriterionResult(
            name="Excess Return vs Benchmark",
            passed=passed,
            value=excess_return,
            threshold=self.min_excess_return,
            description=f"Must outperform benchmark by >= {self.min_excess_return * 100}%",
        )

    def get_excess_return(self, strategy_return: float, benchmark_return: float) -> float:
        """
        Calculate excess return.

        Args:
            strategy_return: Strategy total return
            benchmark_return: Benchmark total return

        Returns:
            Excess return (strategy - benchmark)
        """
        return strategy_return - benchmark_return
