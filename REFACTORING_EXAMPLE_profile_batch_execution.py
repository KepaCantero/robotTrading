"""
Profile Batch Execution Module.

This module contains execution logic for running backtests, optimization,
and validation for investment profiles.

Clean Architecture Principles:
- Business logic isolated from infrastructure
- Dependency inversion: depend on interfaces
- Single Responsibility: each class has one reason to change
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
import optuna
import pandas as pd
import yaml

from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.backtesting.profile_batch_config import (
    AcceptanceCriteriaConfig,
    BacktestConfig,
    BaselineOptimizationComparison,
    OptimizedStrategy,
    OptimizationConfig,
    ProfileResult,
    ValidationConfig,
)
from app.core.models.input_profile import InputProfile
from app.core.tier_mapper import map_profile_tier_to_config

logger = logging.getLogger(__name__)


# ============================================================================
# Execution Pipeline
# ============================================================================


class ProfileBatchExecutor:
    """
    Execute backtests and optimization for profiles.

    This class is responsible for:
    - Running baseline backtests
    - Running optimization pipeline
    - Executing backtests with specific parameters
    - Coordinating with validation components

    It depends on configuration interfaces, not concrete implementations.
    """

    def __init__(
        self,
        config: BacktestConfig,
        optimization_config: OptimizationConfig,
        validation_config: ValidationConfig,
        acceptance_criteria: AcceptanceCriteriaConfig,
        output_dir: Path,
        profile_config_loader: Optional[Any] = None,
    ):
        """
        Initialize executor.

        Args:
            config: Base backtest configuration
            optimization_config: Optimization parameter configuration
            validation_config: Validation threshold configuration
            acceptance_criteria: Acceptance criteria configuration
            output_dir: Directory for output files
            profile_config_loader: Optional ProfileConfigLoader for parameter ranges
        """
        self.base_config = config
        self.optimization_config = optimization_config
        self.validation_config = validation_config
        self.acceptance_criteria = acceptance_criteria
        self.output_dir = output_dir
        self.profile_config_loader = profile_config_loader

        # Initialize validator (depends on executor)
        from app.backtesting.profile_batch_validation import ProfileBatchValidator
        self.validator = ProfileBatchValidator(validation_config)

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_baseline(
        self, profile: InputProfile, config: BacktestConfig, multi_strategy: bool = False
    ) -> Dict[str, Any]:
        """
        Run baseline backtest with default parameters.

        Args:
            profile: InputProfile
            config: BacktestConfig for this profile
            multi_strategy: If True, use multi-strategy backtest mode

        Returns:
            Baseline metrics (single strategy or multi-strategy combined)
        """
        logger.info(
            f"Running baseline for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )

        # Create temporary config file
        temp_config_path = self.output_dir / f"temp_{profile.input_id}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(config.to_dict(), f)

        try:
            # Use ComprehensiveBacktestRunner
            runner = ComprehensiveBacktestRunner(str(temp_config_path))

            if multi_strategy:
                # Multi-strategy execution
                logger.info("Executing multi-strategy baseline backtest")
                multi_strategy_results = runner.run_multi_strategy_backtest()

                # Aggregate results across strategies
                from app.backtesting.profile_batch_aggregation import ProfileBatchAggregator
                aggregator = ProfileBatchAggregator(self.acceptance_criteria)
                baseline_results = aggregator.aggregate_multi_strategy_results(
                    multi_strategy_results, profile
                )

                # Extract per-strategy results for reporting
                per_strategy = {}
                for result in multi_strategy_results:
                    strategy_name = result.get("strategy_name", "unknown")
                    if strategy_name != "combined":
                        per_strategy[strategy_name] = {
                            "total_pnl": result.get("total_pnl", 0.0),
                            "return_pct": result.get("return_pct", 0.0),
                            "sharpe_ratio": result.get("sharpe_ratio", 0.0),
                            "max_drawdown": result.get("max_drawdown", 0.0),
                            "win_rate": result.get("win_rate", 0.0),
                            "total_trades": result.get("total_trades", 0),
                            "final_capital": result.get("final_capital", 0.0),
                            "capital_weight": result.get("capital_weight", 0.0),
                        }

                baseline_results["per_strategy_results"] = per_strategy
                baseline_results["per_strategy_raw"] = multi_strategy_results

                logger.info(
                    f"Multi-strategy baseline complete: "
                    f"Combined Sharpe={baseline_results.get('sharpe_ratio', 0):.2f}, "
                    f"Per-strategy results: {len(per_strategy)}"
                )
            else:
                # Single strategy execution
                baseline_results_list = runner.run_baseline_backtest()

                # Safe extraction with proper validation
                baseline_results = self.validator.safe_extract_first_result(
                    baseline_results_list,
                    context=f"baseline backtest for {profile.objetivo_inversion.value}"
                )

                # Add combined field for consistency
                baseline_results["combined"] = baseline_results

            return baseline_results

        except Exception as e:
            logger.error(f"Baseline backtest failed: {e}", exc_info=True)
            return self.validator.get_empty_metrics()

        finally:
            # Clean up temp file
            if temp_config_path.exists():
                temp_config_path.unlink()

    def run_optimization_pipeline(
        self,
        profile: InputProfile,
        config: BacktestConfig,
        baseline_metrics: Optional[Dict[str, Any]] = None,
        multi_strategy: bool = False
    ) -> OptimizedStrategy:
        """
        Run complete optimization pipeline.

        Pipeline:
        1. Baseline with default params (passed in to avoid duplicate execution)
        2. Bayesian optimization with Optuna
        3. Walk-forward validation
        4. Monte Carlo simulation
        5. Out-of-sample validation

        Args:
            profile: InputProfile
            config: BacktestConfig
            baseline_metrics: Pre-computed baseline metrics (optional)
            multi_strategy: If True, use multi-strategy optimization mode

        Returns:
            OptimizedStrategy with complete results
        """
        logger.info(
            f"Running optimization pipeline for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )

        # PHASE 1: Baseline (use provided metrics or compute if not available)
        if baseline_metrics is None:
            baseline_metrics = self.run_baseline(profile, config, multi_strategy=multi_strategy)

        # Extract combined metrics for multi-strategy
        baseline_for_comparison = (
            baseline_metrics.get("combined", baseline_metrics)
            if multi_strategy and "combined" in baseline_metrics
            else baseline_metrics
        )

        # PHASE 2: Bayesian Optimization
        optuna_results = self.run_bayesian_optimization(
            profile, config, multi_strategy=multi_strategy
        )
        best_params = optuna_results["best_params"]
        optimized_metrics = optuna_results["best_metrics"]

        # Initialize validator component
        from app.backtesting.profile_batch_validation import ProfileBatchValidator
        validator = ProfileBatchValidator(self.validation_config)

        # PHASE 3: Walk-forward validation
        walk_forward_results = validator.run_walk_forward(
            profile, config, best_params, self, multi_strategy=multi_strategy
        )

        # PHASE 4: Monte Carlo
        monte_carlo_results = validator.run_monte_carlo(
            profile, config, best_params, self, multi_strategy=multi_strategy
        )

        # PHASE 5: Out-of-sample
        oos_results = validator.run_out_of_sample(
            profile, config, best_params, self, multi_strategy=multi_strategy
        )

        # Generate comparison
        from app.backtesting.profile_batch_aggregation import ProfileBatchAggregator
        aggregator = ProfileBatchAggregator(self.acceptance_criteria)
        comparison = aggregator.generate_comparison(
            baseline_for_comparison, optimized_metrics, optuna_results
        )

        # Determine readiness
        ready = all([
            walk_forward_results.get("passed", False),
            monte_carlo_results.get("passed", False),
            oos_results.get("passed", False),
        ])

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

    def run_bayesian_optimization(
        self, profile: InputProfile, config: BacktestConfig, multi_strategy: bool = False
    ) -> Dict[str, Any]:
        """
        Run Bayesian optimization using Optuna.

        Args:
            profile: InputProfile
            config: BacktestConfig
            multi_strategy: If True, use multi-strategy optimization mode

        Returns:
            Optimization results with best parameters
        """
        logger.info(
            f"Running Bayesian optimization for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )

        n_trials = self.optimization_config.n_trials
        timeout = self.optimization_config.timeout

        # Get parameter ranges from configuration
        rsi_buy_min = self.optimization_config.rsi_buy_min
        rsi_buy_max = self.optimization_config.rsi_buy_max
        vol_min = self.optimization_config.volume_min
        vol_max = self.optimization_config.volume_max

        def objective(trial: optuna.Trial) -> float:
            """Objective function for optimization."""
            # Define search space using config-driven ranges
            params = {
                "rsi_threshold": trial.suggest_int("rsi_threshold", rsi_buy_min, rsi_buy_max),
                "ema_short": trial.suggest_int("ema_short", 5, 20),
                "ema_long": trial.suggest_int("ema_long", 20, 50),
                "volume_threshold": trial.suggest_float("volume_threshold", vol_min, vol_max),
                "stop_loss": trial.suggest_float("stop_loss", 0.01, 0.05),
                "take_profit": trial.suggest_float("take_profit", 0.05, 0.20),
            }

            # Run backtest with these parameters
            try:
                metrics = self.run_backtest_with_params(
                    profile, config, params, multi_strategy=multi_strategy
                )
                # Maximize Sharpe ratio
                if multi_strategy and "combined" in metrics:
                    return metrics["combined"].get("sharpe_ratio", -1.0)
                return metrics.get("sharpe_ratio", -1.0)
            except Exception as e:
                logger.warning(f"Trial failed: {e}")
                return -1.0

        # Create study
        study = optuna.create_study(
            direction="maximize",
            study_name=f"{profile.objetivo_inversion.value}_{profile.input_id[:8]}",
        )

        # Optimize
        study.optimize(objective, n_trials=n_trials, timeout=timeout)

        # Extract results
        best_params = study.best_params
        best_value = study.best_value

        # Get metrics for best params
        best_metrics = self.run_backtest_with_params(profile, config, best_params)

        # Optimization history
        history = [
            {"trial": t.number, "value": t.value, "params": t.params}
            for t in study.trials
        ]

        logger.info(
            f"Optimization complete: Best Sharpe={best_value:.2f} with params={best_params}"
        )

        return {
            "best_params": best_params,
            "best_metrics": best_metrics,
            "best_value": best_value,
            "history": history,
            "n_trials": len(study.trials),
        }

    def run_backtest_with_params(
        self,
        profile: InputProfile,
        config: BacktestConfig,
        params: Dict[str, Any],
        multi_strategy: bool = False
    ) -> Dict[str, Any]:
        """
        Run backtest with specific parameters.

        Args:
            profile: InputProfile
            config: BacktestConfig
            params: Strategy parameters to test
            multi_strategy: If True, use multi-strategy backtest mode

        Returns:
            Backtest metrics (single or multi-strategy)
        """
        # Update config with params
        config_dict = config.to_dict()
        config_dict["strategy"].update(params)

        # Create temp config
        temp_config_path = self.output_dir / f"temp_{uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(config_dict, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))

            if multi_strategy:
                # Multi-strategy execution
                results = runner.run_multi_strategy_backtest()

                # Aggregate results
                from app.backtesting.profile_batch_aggregation import ProfileBatchAggregator
                aggregator = ProfileBatchAggregator(self.acceptance_criteria)
                aggregated = aggregator.aggregate_multi_strategy_results(results, profile)

                # Add per-strategy results
                per_strategy = {}
                for result in results:
                    strategy_name = result.get("strategy_name", "unknown")
                    if strategy_name != "combined":
                        per_strategy[strategy_name] = {
                            "total_pnl": result.get("total_pnl", 0.0),
                            "return_pct": result.get("return_pct", 0.0),
                            "sharpe_ratio": result.get("sharpe_ratio", 0.0),
                            "max_drawdown": result.get("max_drawdown", 0.0),
                            "win_rate": result.get("win_rate", 0.0),
                            "total_trades": result.get("total_trades", 0),
                        }

                aggregated["per_strategy_results"] = per_strategy
                aggregated["combined"] = aggregated

                return aggregated
            else:
                # Single strategy execution
                results = runner.run_baseline_backtest()

                # Safe extraction with proper validation
                return self.validator.safe_extract_first_result(
                    results,
                    context=f"backtest with params for {profile.objetivo_inversion.value}"
                )

        except Exception as e:
            logger.error(f"Backtest with params failed: {e}", exc_info=True)
            return self.validator.get_empty_metrics()

        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    def _generate_recommendation(self, comparison: BaselineOptimizationComparison, ready: bool) -> str:
        """Generate recommendation from comparison and readiness."""
        if not ready:
            return "REJECTED - Validation tests failed"

        if comparison.recommended == "optimized":
            return f"APPROVED - Optimized configuration ({comparison.reason})"
        elif comparison.recommended == "baseline":
            return f"APPROVED - Baseline configuration ({comparison.reason})"
        else:
            return f"INCONCLUSIVE - {comparison.reason}"


# ============================================================================
# Parallel Execution Coordinator
# ============================================================================


class ParallelExecutionCoordinator:
    """
    Coordinate parallel execution of profiles.

    This class handles the coordination of running multiple profiles
    in parallel while managing database write operations to avoid
    race conditions.
    """

    def __init__(self, config_path: str, max_workers: int = 20):
        """
        Initialize coordinator.

        Args:
            config_path: Path to configuration file
            max_workers: Maximum number of parallel workers
        """
        self.config_path = config_path
        self.max_workers = max_workers

    def run_parallel(
        self,
        profiles: List[InputProfile],
        executor_factory,
    ) -> Dict[str, ProfileResult]:
        """
        Run profiles in parallel using ProcessPoolExecutor.

        Results are collected in parallel and stored sequentially to avoid
        database race conditions with SQLite.

        Args:
            profiles: List of InputProfile objects to execute
            executor_factory: Factory function to create executor instances

        Returns:
            Dictionary mapping profile_id to ProfileResult
        """
        results = {}

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_profile = {
                executor.submit(self._run_profile_worker, self.config_path, profile): profile
                for profile in profiles
            }

            for future in as_completed(future_to_profile):
                profile = future_to_profile[future]
                try:
                    result = future.result()
                    profile_id = result.profile_id
                    results[profile_id] = result
                    logger.info(f"Completed {profile_id} ({len(results)}/{len(profiles)})")
                except Exception as e:
                    logger.error(f"Profile {profile} failed: {e}", exc_info=True)

        return results

    def run_sequential(
        self,
        profiles: List[InputProfile],
        executor_factory,
    ) -> Dict[str, ProfileResult]:
        """
        Run profiles sequentially.

        Args:
            profiles: List of InputProfile objects to execute
            executor_factory: Factory function to create executor instances

        Returns:
            Dictionary mapping profile_id to ProfileResult
        """
        results = {}

        for i, profile in enumerate(profiles, 1):
            try:
                # Create executor for this profile
                executor = executor_factory()
                result = self._run_single_profile(executor, profile)
                results[result.profile_id] = result
                logger.info(f"Completed {i}/{len(profiles)}: {result.profile_id}")
            except Exception as e:
                logger.error(f"Profile {profile} failed: {e}", exc_info=True)

        return results

    @staticmethod
    def _run_profile_worker(config_path: str, profile: InputProfile) -> ProfileResult:
        """
        Worker function for parallel execution.

        This static method is picklable for multiprocessing.
        """
        # Import here to avoid pickling issues
        from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
        backtester = ProfileBatchBacktester(config_path)
        return backtester.run_single_profile(profile)

    def _run_single_profile(self, executor: Any, profile: InputProfile) -> ProfileResult:
        """
        Run a single profile using the provided executor.

        Args:
            executor: ProfileBatchExecutor instance
            profile: InputProfile to run

        Returns:
            ProfileResult
        """
        # This would delegate to the executor's run_optimization_pipeline
        # Implementation depends on the executor interface
        pass


# ============================================================================
# Fallback Metrics Tracker
# ============================================================================


class FallbackMetricsTracker:
    """
    Track fallback metrics for configuration loading.

    This class provides thread-safe tracking of how often the system
    falls back to default behaviors when configuration components
    are unavailable.
    """

    def __init__(self):
        """Initialize tracker with zero counts."""
        self._profile_config_loader_fallback_count = 0
        self._profile_strategy_mapper_fallback_count = 0
        self._config_key_mismatch_count = 0
        import threading
        self._lock = threading.Lock()

    def increment_fallback_counter(self, fallback_type: str) -> None:
        """
        Thread-safe increment of fallback counter.

        Args:
            fallback_type: Type of fallback ("profile_config_loader",
                          "profile_strategy_mapper", "config_key_mismatch")
        """
        with self._lock:
            if fallback_type == "profile_config_loader":
                self._profile_config_loader_fallback_count += 1
            elif fallback_type == "profile_strategy_mapper":
                self._profile_strategy_mapper_fallback_count += 1
            elif fallback_type == "config_key_mismatch":
                self._config_key_mismatch_count += 1
            else:
                logger.warning(f"Unknown fallback type: {fallback_type}")

    def get_fallback_metrics(self) -> Dict[str, int]:
        """
        Get current fallback metrics (thread-safe).

        Returns:
            Dictionary with fallback counts
        """
        with self._lock:
            return {
                "profile_config_loader_fallback_count": self._profile_config_loader_fallback_count,
                "profile_strategy_mapper_fallback_count": self._profile_strategy_mapper_fallback_count,
                "config_key_mismatch_count": self._config_key_mismatch_count,
            }

    def log_fallback_summary(self) -> None:
        """Log a summary of all fallback metrics at INFO level."""
        metrics = self.get_fallback_metrics()
        total_fallbacks = sum(metrics.values())

        logger.info("=" * 60)
        logger.info("Fallback Metrics Summary:")
        logger.info(f"  ProfileConfigLoader fallbacks: {metrics['profile_config_loader_fallback_count']}")
        logger.info(f"  ProfileStrategyMapper fallbacks: {metrics['profile_strategy_mapper_fallback_count']}")
        logger.info(f"  Config key mismatches: {metrics['config_key_mismatch_count']}")
        logger.info(f"Total fallbacks: {total_fallbacks}")
        logger.info("=" * 60)

        # Provide interpretation
        if total_fallbacks == 0:
            logger.info("No fallbacks occurred - all components loaded successfully")
        elif total_fallbacks < 5:
            logger.info(f"Low fallback count ({total_fallbacks}) - minimal impact on backtesting")
        elif total_fallbacks < 20:
            logger.warning(f"Moderate fallback count ({total_fallbacks}) - some configurations may need review")
        else:
            logger.error(f"High fallback count ({total_fallbacks}) - review configuration files immediately")
