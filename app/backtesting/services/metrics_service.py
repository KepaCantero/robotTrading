"""
Metrics Calculation Service

Handles calculation of improvements, comparisons, and evaluations
for baseline vs optimized strategy results.

Responsibilities:
- Calculate improvement metrics (sharpe, return, drawdown, win_rate)
- Generate baseline vs optimization comparisons
- Calculate parameter importance from optimization history
- Evaluate readiness for paper trading
- Generate recommendations
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd

from app.backtesting.services.models import BaselineOptimizationComparison, OptimizedStrategy
from app.core.models.input_profile import InputProfile

logger = logging.getLogger(__name__)

ConfigDict = Dict[str, Any]
MetricsDict = Dict[str, Any]
OptimizationHistoryEntry = Dict[str, Any]


class MetricsCalculationService:
    """
    Service for calculating metrics and comparisons.

    Handles all metric calculations including improvements between
    baseline and optimized results, parameter importance analysis,
    and readiness evaluation for paper trading.
    """

    def __init__(self, acceptance_criteria: ConfigDict):
        """
        Initialize metrics calculation service.

        Args:
            acceptance_criteria: Configuration dict with thresholds for evaluation
        """
        self.acceptance_criteria = acceptance_criteria

    def calculate_improvements(
        self, baseline: Dict[str, Any], optimized: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate improvement metrics between baseline and optimized results.

        Args:
            baseline: Baseline metrics dictionary
            optimized: Optimized metrics dictionary

        Returns:
            Dictionary with improvement percentages
        """
        # For drawdown, lower absolute value is better, so invert the calculation
        baseline_dd = abs(baseline.get("max_drawdown", 0))
        optimized_dd = abs(optimized.get("max_drawdown", 0))

        return {
            "sharpe_improvement": self._pct_improvement(
                baseline.get("sharpe_ratio", 0), optimized.get("sharpe_ratio", 0)
            ),
            "return_improvement": self._pct_improvement(
                baseline.get("return_pct", 0), optimized.get("return_pct", 0)
            ),
            "max_dd_improvement": -self._pct_improvement(
                baseline_dd, optimized_dd
            ),  # Invert because lower is better
            "win_rate_improvement": self._pct_improvement(
                baseline.get("win_rate", 0), optimized.get("win_rate", 0)
            ),
        }

    def _pct_improvement(self, baseline: float, optimized: float) -> float:
        """
        Calculate percentage improvement.

        Args:
            baseline: Baseline value
            optimized: Optimized value

        Returns:
            Percentage improvement
        """
        if baseline == 0:
            return 0.0
        return ((optimized - baseline) / abs(baseline)) * 100

    def generate_comparison(
        self, baseline: MetricsDict, optimized: MetricsDict, optuna_results: ConfigDict
    ) -> BaselineOptimizationComparison:
        """
        Generate baseline vs optimization comparison.

        Uses acceptance criteria from config for thresholds:
        - significance_threshold: Minimum % improvement for statistical significance
        - strong_significance_threshold: Minimum % improvement for strong significance
        - degradation_threshold: Maximum % improvement degradation to prefer baseline
        - confidence_high/medium/low: Confidence levels for recommendations

        Args:
            baseline: Baseline metrics
            optimized: Optimized metrics
            optuna_results: Results from Optuna optimization

        Returns:
            BaselineOptimizationComparison object
        """
        # Get thresholds from config
        significance_threshold = self.acceptance_criteria.get("significance_threshold", 5)
        strong_significance_threshold = self.acceptance_criteria.get(
            "strong_significance_threshold", 10
        )
        degradation_threshold = self.acceptance_criteria.get("degradation_threshold", -5)
        confidence_high = self.acceptance_criteria.get("confidence_high", 0.8)
        confidence_medium = self.acceptance_criteria.get("confidence_medium", 0.7)
        confidence_low = self.acceptance_criteria.get("confidence_low", 0.5)

        # Calculate improvements
        sharpe_imp = self._pct_improvement(
            baseline.get("sharpe_ratio", 0), optimized.get("sharpe_ratio", 0)
        )
        return_imp = self._pct_improvement(
            baseline.get("return_pct", 0), optimized.get("return_pct", 0)
        )

        # For drawdown, lower absolute value is better, so invert the calculation
        baseline_dd = abs(baseline.get("max_drawdown", 0))
        optimized_dd = abs(optimized.get("max_drawdown", 0))
        dd_imp = -self._pct_improvement(baseline_dd, optimized_dd)  # Invert because lower is better

        wr_imp = self._pct_improvement(baseline.get("win_rate", 0), optimized.get("win_rate", 0))

        # Statistical significance (simplified)
        sharpe_sig = sharpe_imp > significance_threshold
        return_sig = return_imp > significance_threshold

        # Parameter importance from Optuna
        history = optuna_results.get("history", [])
        param_importance = self.calculate_parameter_importance(history)

        # Recommendation using config-driven thresholds
        if sharpe_imp > strong_significance_threshold and sharpe_sig:
            recommended = "optimized"
            confidence = confidence_high
            reason = f"Optimized strategy shows {sharpe_imp:.1f}% Sharpe improvement with statistical significance"
        elif sharpe_imp < degradation_threshold:
            recommended = "baseline"
            confidence = confidence_medium
            reason = "Optimization degraded performance, baseline is preferred"
        else:
            recommended = "inconclusive"
            confidence = confidence_low
            reason = "Insufficient evidence to favor either configuration"

        return BaselineOptimizationComparison(
            sharpe_improvement=sharpe_imp,
            return_improvement=return_imp,
            max_dd_improvement=dd_imp,
            win_rate_improvement=wr_imp,
            sharpe_significant=sharpe_sig,
            return_significant=return_sig,
            parameter_importance=param_importance,
            recommended=recommended,
            confidence=confidence,
            reason=reason,
        )

    def calculate_parameter_importance(
        self, history: List[OptimizationHistoryEntry]
    ) -> Dict[str, float]:
        """
        Calculate parameter importance from optimization history.

        Args:
            history: List of optimization trial results

        Returns:
            Dictionary mapping parameter names to importance scores (0-1)
        """
        if not history:
            return {}

        # Simple correlation-based importance
        df = pd.DataFrame([{"value": h["value"], **h["params"]} for h in history])
        importance = {}
        for col in df.columns:
            if col != "value":
                corr = df[col].corr(df["value"])
                if not pd.isna(corr):
                    importance[col] = abs(corr)

        # Normalize to 0-1
        if importance:
            max_val = max(importance.values())
            if max_val > 0:
                importance = {k: v / max_val for k, v in importance.items()}

        return importance

    def evaluate_readiness(
        self, profile: InputProfile, optimized: OptimizedStrategy, improvements: Dict[str, float]
    ) -> tuple[bool, str]:
        """
        Evaluate if strategy is ready for paper trading.

        Args:
            profile: Input profile being tested
            optimized: Optimized strategy results
            improvements: Improvement metrics

        Returns:
            Tuple of (ready: bool, recommendation: str)
        """
        # Get thresholds from config
        min_sharpe = self.acceptance_criteria.get("min_sharpe", 1.0)
        min_return = self.acceptance_criteria.get("min_return", 0.10)
        max_dd = self.acceptance_criteria.get("max_drawdown", -0.25)
        revision_multiplier = self.acceptance_criteria.get("revision_multiplier", 0.8)

        sharpe = optimized.optimized_metrics.get("sharpe_ratio", 0)
        total_return = optimized.optimized_metrics.get("return_pct", 0)
        max_dd_value = optimized.optimized_metrics.get("max_drawdown", 0)

        # Check thresholds
        checks = [
            sharpe >= min_sharpe,
            total_return >= min_return,
            max_dd_value >= max_dd,
            optimized.ready_for_paper_trading,
        ]

        if all(checks):
            return True, "APPROVED: All acceptance criteria met"
        elif sharpe >= min_sharpe * revision_multiplier:
            return False, "REVISION: Marginal performance, review recommended"
        else:
            return False, "REJECTED: Insufficient performance"

    def generate_recommendation(
        self, comparison: BaselineOptimizationComparison, ready: bool
    ) -> str:
        """
        Generate final recommendation.

        Args:
            comparison: Baseline vs optimization comparison
            ready: Whether strategy is ready for paper trading

        Returns:
            Recommendation string
        """
        if not ready:
            return "NOT READY - Validation failed"
        if comparison.recommended == "optimized":
            return f"USE OPTIMIZED - {comparison.reason}"
        elif comparison.recommended == "baseline":
            return f"USE BASELINE - {comparison.reason}"
        else:
            return f"NEUTRAL - {comparison.reason}"
