"""
Bonferroni Correction for Multiple Hypothesis Testing

This module implements Bonferroni correction as described in Ernest Chan's
"Quantitative Trading" (Chapter 2).

When testing multiple strategies or parameters simultaneously, the chance of
false positives (Type I errors) increases. Bonferroni correction adjusts
significance levels to maintain the overall error rate.

Key Features:
- Family-wise error rate control
- Adjusted p-value calculation
- Holm-Bonferroni method (less conservative)
- False discovery rate estimation

Reference:
    "Quantitative Trading" by Ernest P. Chan
    Chapter 2: Basic Statistical Strategies
    Section: Multiple Testing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class HypothesisTest:
    """A single hypothesis test result."""

    test_name: str
    null_hypothesis: str
    p_value: float
    test_statistic: float
    is_significant_uncorrected: bool
    is_significant_corrected: bool
    corrected_p_value: float
    corrected_alpha: float


@dataclass
class MultipleTestResult:
    """Result of multiple hypothesis testing with correction."""

    family_wise_error_rate: float  # Desired alpha
    num_tests: int
    num_significant_uncorrected: int
    num_significant_corrected: int
    tests: list[HypothesisTest]
    correction_method: str  # 'bonferroni', 'holm', 'bh'
    false_discovery_rate: float | None  # Estimated FDR


@dataclass
class ParameterTestResult:
    """Result of testing multiple parameter combinations."""

    best_parameters: dict[str, Any]
    best_sharpe_ratio: float
    is_significant_after_correction: bool
    num_parameters_tested: int
    corrected_significance_level: float
    all_results: list[dict[str, Any]]


class BonferroniCorrector:
    """
    Implements Bonferroni correction for multiple hypothesis testing.

    The Bonferroni correction controls the family-wise error rate (FWER)
    when performing multiple statistical tests simultaneously.

    Principle:
        If performing n tests at significance level alpha,
        the corrected significance level is alpha/n.

    This prevents the accumulation of Type I errors (false positives)
    when testing many strategies or parameter combinations.
    """

    def __init__(self, family_wise_error_rate: float = 0.05):
        """
        Initialize the Bonferroni corrector.

        Args:
            family_wise_error_rate: Desired overall significance level (default 0.05)
        """
        self.family_wise_error_rate = family_wise_error_rate
        logger.info(f"BonferroniCorrector initialized with FWER={family_wise_error_rate}")

    def correct_p_values(
        self,
        p_values: list[float],
        test_names: list[str] | None = None,
        method: str = "bonferroni",
    ) -> MultipleTestResult:
        """
        Apply multiple testing correction to p-values.

        Args:
            p_values: List of p-values from multiple tests
            test_names: Optional names for each test
            method: Correction method ('bonferroni', 'holm', 'bh')

        Returns:
            MultipleTestResult with corrected p-values
        """
        try:
            num_tests = len(p_values)
            if num_tests == 0:
                logger.warning("No p-values provided for correction")
                return self._create_empty_result()

            # Calculate corrected significance level
            corrected_alpha = self.family_wise_error_rate / num_tests

            tests = []
            num_significant_uncorrected = 0
            num_significant_corrected = 0

            if method == "bonferroni":
                # Standard Bonferroni correction
                corrected_p_values = self._bonferroni_correction(p_values)
            elif method == "holm":
                # Holm-Bonferroni (step-down procedure, less conservative)
                corrected_p_values = self._holm_correction(p_values)
            elif method == "bh":
                # Benjamini-Hochberg (controls FDR, not FWER)
                corrected_p_values = self._benjamini_hochberg(p_values)
            else:
                raise ValueError(f"Unknown correction method: {method}")

            # Create test results
            for i, p_value in enumerate(p_values):
                test_name = test_names[i] if test_names else f"test_{i}"

                is_sig_uncorrected = p_value < self.family_wise_error_rate
                is_sig_corrected = corrected_p_values[i] < self.family_wise_error_rate

                if is_sig_uncorrected:
                    num_significant_uncorrected += 1
                if is_sig_corrected:
                    num_significant_corrected += 1

                test = HypothesisTest(
                    test_name=test_name,
                    null_hypothesis=f"No effect for {test_name}",
                    p_value=p_value,
                    test_statistic=0.0,  # Not provided in this simplified version
                    is_significant_uncorrected=is_sig_uncorrected,
                    is_significant_corrected=is_sig_corrected,
                    corrected_p_value=corrected_p_values[i],
                    corrected_alpha=corrected_alpha,
                )
                tests.append(test)

            # Estimate false discovery rate
            fdr = self._estimate_fdr(corrected_p_values)

            result = MultipleTestResult(
                family_wise_error_rate=self.family_wise_error_rate,
                num_tests=num_tests,
                num_significant_uncorrected=num_significant_uncorrected,
                num_significant_corrected=num_significant_corrected,
                tests=tests,
                correction_method=method,
                false_discovery_rate=fdr,
            )

            logger.info(
                f"Multiple testing correction ({method}): "
                f"{num_significant_uncorrected} significant uncorrected, "
                f"{num_significant_corrected} significant corrected, "
                f"FWER={self.family_wise_error_rate}, "
                f"corrected alpha={corrected_alpha:.6f}"
            )

            return result

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error correcting p-values: {e}")
            return self._create_empty_result()

    def test_strategy_significance(
        self,
        sharpe_ratios: dict[str, float],
        null_sharpe: float = 0.0,
        num_observations: int = 252,
        method: str = "bonferroni",
    ) -> MultipleTestResult:
        """
        Test significance of multiple strategy Sharpe ratios.

        This implements Ernest Chan's recommendation to correct for
        multiple testing when evaluating many strategies.

        Args:
            sharpe_ratios: Dictionary mapping strategy names to Sharpe ratios
            null_sharpe: Sharpe ratio under null hypothesis (usually 0)
            num_observations: Number of observations (trading days, etc.)
            method: Correction method

        Returns:
            MultipleTestResult with significance tests
        """
        try:
            # Calculate p-values for each strategy
            p_values = []
            test_names = []

            for strategy_name, sharpe in sharpe_ratios.items():
                # Calculate t-statistic for Sharpe ratio
                # t = Sharpe * sqrt(T) where T is number of observations
                t_stat = sharpe * np.sqrt(num_observations)

                # Two-tailed p-value
                p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=num_observations - 1))

                p_values.append(p_value)
                test_names.append(strategy_name)

            # Apply correction
            result = self.correct_p_values(p_values, test_names, method)

            logger.info(
                f"Tested {len(sharpe_ratios)} strategies: "
                f"{result.num_significant_corrected} significant after correction"
            )

            return result

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error testing strategy significance: {e}")
            return self._create_empty_result()

    def test_parameter_combinations(
        self,
        backtest_results: list[dict[str, Any]],
        metric: str = "sharpe_ratio",
        method: str = "bonferroni",
    ) -> ParameterTestResult:
        """
        Test significance of multiple parameter combinations.

        When optimizing parameters, it's crucial to correct for multiple
        testing to avoid false positives.

        Args:
            backtest_results: List of backtest result dictionaries
            metric: Metric to test (default: sharpe_ratio)
            method: Correction method

        Returns:
            ParameterTestResult with best parameters and significance
        """
        try:
            num_params = len(backtest_results)

            # Extract metric values
            metrics = [result.get(metric, 0.0) for result in backtest_results]

            # Find best parameters
            best_idx = np.argmax(metrics)
            best_result = backtest_results[best_idx]
            best_metric = metrics[best_idx]

            # Calculate p-values (simplified - in practice use proper statistical test)
            # Here we assume all strategies are tested against same null hypothesis
            num_observations = best_result.get("num_trades", 252)

            # Calculate p-values for all parameter combinations
            p_values = []
            for m in metrics:
                t_stat = m * np.sqrt(num_observations)
                p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=num_observations - 1))
                p_values.append(p_value)

            # Apply correction
            corrected_alpha = self.family_wise_error_rate / num_params
            corrected_p_values = self._bonferroni_correction(p_values)

            # Check if best is significant after correction
            best_p_value = p_values[best_idx]
            best_corrected_p = corrected_p_values[best_idx]
            is_significant = best_corrected_p < self.family_wise_error_rate

            result = ParameterTestResult(
                best_parameters=best_result.get("parameters", {}),
                best_sharpe_ratio=best_metric,
                is_significant_after_correction=is_significant,
                num_parameters_tested=num_params,
                corrected_significance_level=corrected_alpha,
                all_results=backtest_results,
            )

            logger.info(
                f"Parameter testing: Best metric={best_metric:.4f}, "
                f"p-value={best_p_value:.4f}, "
                f"corrected p={best_corrected_p:.4f}, "
                f"significant={is_significant}"
            )

            return result

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error testing parameter combinations: {e}")
            return ParameterTestResult(
                best_parameters={},
                best_sharpe_ratio=0.0,
                is_significant_after_correction=False,
                num_parameters_tested=0,
                corrected_significance_level=1.0,
                all_results=[],
            )

    def _bonferroni_correction(self, p_values: list[float]) -> list[float]:
        """Apply standard Bonferroni correction."""
        num_tests = len(p_values)
        return [min(p * num_tests, 1.0) for p in p_values]

    def _holm_correction(self, p_values: list[float]) -> list[float]:
        """
        Apply Holm-Bonferroni correction (step-down procedure).

        Less conservative than standard Bonferroni while still
        controlling family-wise error rate.
        """
        num_tests = len(p_values)

        # Sort p-values and keep track of original indices
        sorted_indices = sorted(range(num_tests), key=lambda i: p_values[i])
        sorted_p_values = [p_values[i] for i in sorted_indices]

        # Apply step-down correction
        corrected_sorted = []
        for rank, p_value in enumerate(sorted_p_values):
            corrected = p_value * (num_tests - rank)
            corrected_sorted.append(min(corrected, 1.0))

        # Unsort to original order
        corrected_p_values = [0.0] * num_tests
        for original_idx, corrected_p in zip(sorted_indices, corrected_sorted):
            corrected_p_values[original_idx] = corrected_p

        return corrected_p_values

    def _benjamini_hochberg(self, p_values: list[float]) -> list[float]:
        """
        Apply Benjamini-Hochberg correction.

        Controls False Discovery Rate (FDR) rather than FWER.
        Less conservative, more powerful for large-scale testing.
        """
        num_tests = len(p_values)

        # Sort p-values
        sorted_indices = sorted(range(num_tests), key=lambda i: p_values[i])
        sorted_p_values = [p_values[i] for i in sorted_indices]

        # Calculate BH critical values
        corrected_sorted = []
        for rank, p_value in enumerate(sorted_p_values):
            corrected = p_value * num_tests / (rank + 1)
            corrected_sorted.append(min(corrected, 1.0))

        # Apply monotonicity constraint
        for i in range(len(corrected_sorted) - 2, -1, -1):
            corrected_sorted[i] = min(corrected_sorted[i], corrected_sorted[i + 1])

        # Unsort to original order
        corrected_p_values = [0.0] * num_tests
        for original_idx, corrected_p in zip(sorted_indices, corrected_sorted):
            corrected_p_values[original_idx] = corrected_p

        return corrected_p_values

    def _estimate_fdr(self, corrected_p_values: list[float]) -> float:
        """
        Estimate false discovery rate from corrected p-values.

        FDR = expected proportion of false positives among all positives
        """
        try:
            # Count significant results at original FWER level
            significant_count = sum(p < self.family_wise_error_rate for p in corrected_p_values)

            if significant_count == 0:
                return 0.0

            # Rough estimate: assume FDR = corrected_alpha / original_alpha
            # This is simplified; in practice use more sophisticated methods
            avg_corrected_p = np.mean(
                [p for p in corrected_p_values if p < self.family_wise_error_rate]
            )

            fdr = (
                avg_corrected_p / self.family_wise_error_rate
                if self.family_wise_error_rate > 0
                else 0.0
            )

            return min(fdr, 1.0)

        except (ValueError, ZeroDivisionError):
            return 0.0

    def _create_empty_result(self) -> MultipleTestResult:
        """Create empty result for error cases."""
        return MultipleTestResult(
            family_wise_error_rate=self.family_wise_error_rate,
            num_tests=0,
            num_significant_uncorrected=0,
            num_significant_corrected=0,
            tests=[],
            correction_method="bonferroni",
            false_discovery_rate=0.0,
        )


def correct_for_multiple_testing(
    p_values: list[float],
    family_wise_error_rate: float = 0.05,
    method: str = "bonferroni",
) -> list[float]:
    """
    Convenience function to correct p-values for multiple testing.

    Args:
        p_values: List of p-values
        family_wise_error_rate: Desired FWER (default 0.05)
        method: Correction method ('bonferroni', 'holm', 'bh')

    Returns:
        List of corrected p-values
    """
    corrector = BonferroniCorrector(family_wise_error_rate)
    result = corrector.correct_p_values(p_values, method=method)

    return [test.corrected_p_value for test in result.tests]


def is_strategy_significant(
    sharpe_ratio: float,
    num_strategies_tested: int,
    num_observations: int = 252,
    alpha: float = 0.05,
) -> bool:
    """
    Check if a strategy's Sharpe ratio is significant after Bonferroni correction.

    Args:
        sharpe_ratio: Strategy's Sharpe ratio
        num_strategies_tested: Total number of strategies tested
        num_observations: Number of observations
        alpha: Family-wise error rate

    Returns:
        True if significant after correction
    """
    # Calculate t-statistic
    t_stat = sharpe_ratio * np.sqrt(num_observations)

    # Calculate p-value
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=num_observations - 1))

    # Apply Bonferroni correction
    corrected_p = p_value * num_strategies_tested

    # Check significance
    return bool(corrected_p < alpha)
