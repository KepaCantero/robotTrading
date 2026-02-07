"""
Optimization Pipeline Module

Orchestrates the complete optimization workflow.

Responsibilities:
- Coordinate optimization stages
- Generate comparisons between baseline and optimized results
- Provide unified interface for optimization workflow
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

from app.core.config.profile_config_loader import ProfileConfigLoader
from app.core.models.input_profile import InputProfile

from .bayesian_optimizer import BayesianOptimizer
from .optimization_validators import MonteCarloSimulator, OutOfSampleValidator, WalkForwardValidator

logger = logging.getLogger(__name__)


@dataclass
class BaselineOptimizationComparison:
    """Comparison between baseline and optimized results."""

    sharpe_improvement: float
    return_improvement: float
    max_dd_improvement: float
    win_rate_improvement: float
    sharpe_significant: bool
    return_significant: bool
    parameter_importance: Dict[str, float]
    recommended: str
    confidence: float
    reason: str


@dataclass
class OptimizedStrategy:
    """Result of optimization pipeline."""

    profile_id: str
    baseline_metrics: Dict[str, Any]
    optimized_metrics: Dict[str, Any]
    best_parameters: Dict[str, Any]
    optimization_history: list[Dict[str, Any]]
    walk_forward_results: Dict[str, Any] | None
    monte_carlo_results: Dict[str, Any] | None
    out_of_sample_results: Dict[str, Any] | None
    comparison: BaselineOptimizationComparison
    ready_for_paper_trading: bool
    recommendation: str


class OptimizationPipeline:
    """
    Orchestrates the complete optimization pipeline.

    Pipeline stages:
    1. Bayesian optimization with Optuna
    2. Walk-forward validation
    3. Monte Carlo simulation
    4. Out-of-sample validation
    5. Comparison and recommendation generation
    """

    def __init__(
        self,
        output_dir: Path,
        optimization_config: Dict[str, Any],
        validation_config: Dict[str, Any],
        acceptance_criteria: Dict[str, Any],
        profile_config_loader: ProfileConfigLoader | None = None,
    ):
        """
        Initialize optimization pipeline.

        Args:
            output_dir: Directory for temporary files
            optimization_config: Optimization configuration
            validation_config: Validation configuration
            acceptance_criteria: Acceptance criteria thresholds
            profile_config_loader: Profile config loader
        """
        self.output_dir = output_dir
        self.acceptance_criteria = acceptance_criteria

        # Initialize components
        self.bayesian_optimizer = BayesianOptimizer(
            output_dir, optimization_config, profile_config_loader
        )
        self.walk_forward_validator = WalkForwardValidator(
            output_dir, validation_config, profile_config_loader
        )
        self.monte_carlo_simulator = MonteCarloSimulator(
            output_dir, validation_config, profile_config_loader
        )
        self.out_of_sample_validator = OutOfSampleValidator(
            output_dir, validation_config, profile_config_loader
        )

    def run_optimization_pipeline(
        self,
        profile: InputProfile,
        config: Dict[str, Any],
        baseline_metrics: Dict[str, Any],
        multi_strategy: bool = False,
    ) -> OptimizedStrategy:
        """
        Run complete optimization pipeline.

        Args:
            profile: InputProfile
            config: Configuration dict
            baseline_metrics: Pre-computed baseline metrics
            multi_strategy: If True, use multi-strategy mode

        Returns:
            OptimizedStrategy with complete results
        """
        logger.info(
            f"Running optimization pipeline for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )

        # Extract combined metrics for multi-strategy
        baseline_for_comparison = (
            baseline_metrics.get("combined", baseline_metrics)
            if multi_strategy and "combined" in baseline_metrics
            else baseline_metrics
        )

        # Stage 1: Bayesian Optimization
        optuna_results = self.bayesian_optimizer.optimize(
            profile, config, multi_strategy=multi_strategy
        )
        best_params = optuna_results["best_params"]
        optimized_metrics = optuna_results["best_metrics"]

        # Stage 2: Walk-forward validation
        walk_forward_results = self.walk_forward_validator.validate(profile, config, best_params)

        # Stage 3: Monte Carlo
        monte_carlo_results = self.monte_carlo_simulator.simulate(profile, config, best_params)

        # Stage 4: Out-of-sample
        oos_results = self.out_of_sample_validator.validate(profile, config, best_params)

        # Generate comparison
        comparison = self._generate_comparison(
            baseline_for_comparison, optimized_metrics, optuna_results
        )

        # Determine readiness
        ready = all(
            [
                walk_forward_results.get("passed", False),
                monte_carlo_results.get("passed", False),
                oos_results.get("passed", False),
            ]
        )

        recommendation = self._generate_recommendation(comparison, ready)

        return OptimizedStrategy(
            profile_id=profile.input_id,
            baseline_metrics=baseline_for_comparison,
            optimized_metrics=optimized_metrics,
            best_parameters=best_params,
            optimization_history=optuna_results.get("history", []),
            walk_forward_results=walk_forward_results,
            monte_carlo_results=monte_carlo_results,
            out_of_sample_results=oos_results,
            comparison=comparison,
            ready_for_paper_trading=ready,
            recommendation=recommendation,
        )

    def _generate_comparison(
        self, baseline: Dict[str, Any], optimized: Dict[str, Any], optuna_results: Dict[str, Any]
    ) -> BaselineOptimizationComparison:
        """Generate baseline vs optimization comparison."""
        significance_threshold = self.acceptance_criteria.get("significance_threshold", 5)
        strong_significance_threshold = self.acceptance_criteria.get(
            "strong_significance_threshold", 10
        )
        degradation_threshold = self.acceptance_criteria.get("degradation_threshold", -5)

        # Calculate improvements
        sharpe_imp = self._pct_improvement(
            baseline.get("sharpe_ratio", 0), optimized.get("sharpe_ratio", 0)
        )
        return_imp = self._pct_improvement(
            baseline.get("return_pct", 0), optimized.get("return_pct", 0)
        )
        dd_imp = self._pct_improvement(
            abs(baseline.get("max_drawdown", 0)), abs(optimized.get("max_drawdown", 0))
        )
        wr_imp = self._pct_improvement(baseline.get("win_rate", 0), optimized.get("win_rate", 0))

        sharpe_sig = sharpe_imp > significance_threshold
        return_sig = return_imp > significance_threshold

        # Parameter importance
        history = optuna_results.get("history", [])
        param_importance = self._calculate_parameter_importance(history)

        # Recommendation
        if sharpe_imp > strong_significance_threshold and sharpe_sig:
            recommended = "optimized"
            confidence = 0.8
            reason = f"Optimized shows {sharpe_imp:.1f}% Sharpe improvement"
        elif sharpe_imp < degradation_threshold:
            recommended = "baseline"
            confidence = 0.7
            reason = "Optimization degraded performance"
        else:
            recommended = "inconclusive"
            confidence = 0.5
            reason = "Insufficient evidence"

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

    def _calculate_parameter_importance(self, history: list[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate parameter importance from optimization history."""
        if not history:
            return {}

        df = pd.DataFrame([{"value": h["value"], **h["params"]} for h in history])

        importance = {}
        for col in df.columns:
            if col != "value":
                corr = df[col].corr(df["value"])
                if not np.isnan(corr):
                    importance[col] = abs(corr)

        if importance:
            max_val = max(importance.values())
            if max_val > 0:
                importance = {k: v / max_val for k, v in importance.items()}

        return importance

    def _pct_improvement(self, baseline: float, optimized: float) -> float:
        """Calculate percentage improvement."""
        if baseline == 0:
            return 0.0
        return ((optimized - baseline) / abs(baseline)) * 100

    def _generate_recommendation(
        self, comparison: BaselineOptimizationComparison, ready: bool
    ) -> str:
        """Generate final recommendation."""
        if not ready:
            return "NOT READY - Validation failed"

        if comparison.recommended == "optimized":
            return f"USE OPTIMIZED - {comparison.reason}"
        elif comparison.recommended == "baseline":
            return f"USE BASELINE - {comparison.reason}"
        else:
            return f"NEUTRAL - {comparison.reason}"
