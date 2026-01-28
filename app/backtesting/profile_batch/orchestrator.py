"""
Profile Batch Backtester Orchestrator

Main orchestrator for batch backtesting with profile-driven optimization.
Coordinates all components and manages the overall workflow.

Responsibilities:
- Orchestrate batch backtesting workflow
- Coordinate parallel/sequential execution
- Delegate to specialized components
- Manage fallback metrics
- Provide unified interface
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

import yaml

from app.core.config.profile_config_loader import ProfileConfigLoader
from app.core.models.input_profile import InputProfile

from .baseline_executor import BaselineBacktestExecutor
from .profile_generator import ProfileGenerator
from .report_generator import ReportGenerator
from .result_aggregator import ProfileResult, ResultAggregator

logger = logging.getLogger(__name__)


class ProfileBatchBacktester:
    """
    Orchestrates batch testing with baseline AND optimization reporting.

    This is the main entry point for batch backtesting. It coordinates
    all components and provides a unified interface for running backtests.

    Features:
    - Generate profile combinations
    - Run baseline backtest with default parameters
    - Run Bayesian optimization with Optuna
    - Perform walk-forward validation
    - Run Monte Carlo simulation
    - Perform out-of-sample testing
    - Generate statistical comparison reports
    - Store results in database
    """

    def __init__(self, config_path: str | Path):
        """
        Initialize batch backtester orchestrator.

        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Initialize ProfileConfigLoader
        try:
            self.profile_config_loader = ProfileConfigLoader()
            logger.info("ProfileConfigLoader initialized successfully")
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Failed to initialize ProfileConfigLoader: {e}")
            self.profile_config_loader = None
            self._fallback_count = 1

        # Initialize components
        self.profile_generator = ProfileGenerator(config_path)
        self.baseline_executor = BaselineBacktestExecutor(
            Path(self.config.get("output_dir", "results/profile_batch_backtesting"))
        )

        # Initialize result aggregator
        db_url = self.config.get("database", {}).get("url", "sqlite:///profile_backtest_results.db")
        self.result_aggregator = ResultAggregator(
            db_url, self.profile_generator.get_capital_tier_key
        )

        # Initialize report generator
        output_dir = Path(self.config.get("output_dir", "results/profile_batch_backtesting"))
        self.report_generator = ReportGenerator(output_dir)

        # Results storage
        self.results: Dict[str, ProfileResult] = {}

        # Initialize fallback metrics (thread-safe)
        self._fallback_lock = threading.Lock()
        self._total_fallback_count = 0

        logger.info(f"ProfileBatchBacktester initialized with config: {config_path}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def generate_all_profiles(self) -> List[InputProfile]:
        """
        Generate all profile combinations.

        Returns:
            List of InputProfile objects
        """
        return self.profile_generator.generate_all_profiles()

    def run_single_profile(
        self, profile: InputProfile, multi_strategy: bool = False
    ) -> ProfileResult:
        """
        Run baseline and optimization for a single profile.

        Args:
            profile: InputProfile to test
            multi_strategy: If True, use multi-strategy backtest mode

        Returns:
            ProfileResult with baseline and optimization results
        """
        profile_id = self.profile_generator.create_profile_id(profile)

        logger.info(f"Running profile: {profile_id} (multi_strategy={multi_strategy})")

        # Create profile config
        output_dir = Path(self.config.get("output_dir", "results/profile_batch_backtesting"))
        profile_config = self.profile_generator.create_profile_config(profile, output_dir)

        # Extract strategy mapping metadata
        strategy_mapping_metadata = profile_config.pop("_strategy_mapping", {})
        enabled_strategies = strategy_mapping_metadata.get("enabled_strategies", [])
        learning_engines = strategy_mapping_metadata.get("learning_engines", [])
        ensemble_config = strategy_mapping_metadata.get("ensemble_config", {})

        # Run baseline
        baseline_results = self.baseline_executor.run_baseline(
            profile, profile_config, multi_strategy=multi_strategy
        )

        # Run optimization pipeline
        from .optimization_pipeline import OptimizationPipeline

        optimization_pipeline = OptimizationPipeline(
            output_dir=output_dir,
            optimization_config=self.config.get("optimization", {}),
            validation_config=self.config.get("validation", {}),
            acceptance_criteria=self.config.get("acceptance_criteria", {}),
            profile_config_loader=self.profile_config_loader,
        )

        optimized_strategy = optimization_pipeline.run_optimization_pipeline(
            profile, profile_config, baseline_results, multi_strategy=multi_strategy
        )

        # Calculate improvement metrics
        improvement_metrics = self.result_aggregator.calculate_improvements(
            baseline_results, optimized_strategy.optimized_metrics
        )

        # Determine readiness
        ready, recommendation = self.result_aggregator.evaluate_readiness(
            profile,
            optimized_strategy,
            improvement_metrics,
            self.config.get("acceptance_criteria", {}),
        )

        # Get StrategyMapping if available
        strategy_mapping_obj = None
        try:
            if self.profile_generator.profile_mapper is not None:
                strategy_mapping_obj = (
                    self.profile_generator.profile_mapper.create_strategy_mapping(profile)
                )
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.debug(f"Could not create StrategyMapping: {e}")

        # Extract per-strategy results
        per_strategy_results = {}
        if multi_strategy and "per_strategy_results" in baseline_results:
            per_strategy_results = baseline_results["per_strategy_results"]
            logger.info(f"Collected {len(per_strategy_results)} per-strategy results")

        # Create result
        result = ProfileResult(
            profile_id=profile_id,
            profile=profile,
            baseline_results=baseline_results.get("combined", baseline_results),
            optimization_results=optimized_strategy.optimized_metrics,
            best_parameters=optimized_strategy.best_parameters,
            improvement_metrics=improvement_metrics,
            comparison=optimized_strategy.comparison,
            ready_for_paper_trading=ready,
            recommendation=recommendation,
            strategy_mapping=strategy_mapping_obj,
            enabled_strategies=enabled_strategies,
            learning_engines=learning_engines,
            ensemble_config=ensemble_config,
            per_strategy_results=per_strategy_results,
        )

        # Store in database
        self.result_aggregator.store_result(result)

        logger.info(f"Profile {profile_id} completed: {recommendation}")

        return result

    def run_all_profiles(
        self, parallel: bool = True, max_workers: int = 20
    ) -> Dict[str, ProfileResult]:
        """
        Run all profiles with optional parallel execution.

        Args:
            parallel: Whether to run profiles in parallel
            max_workers: Maximum number of parallel workers

        Returns:
            Dictionary mapping profile_id to ProfileResult
        """
        profiles = self.generate_all_profiles()

        logger.info(
            f"Running {len(profiles)} profiles (parallel={parallel}, workers={max_workers})"
        )

        if parallel:
            results = self._run_parallel(profiles, max_workers)
        else:
            results = self._run_sequential(profiles)

        self.results = results

        # Generate summary
        self.report_generator.generate_batch_summary(results, self.get_fallback_metrics())

        return results

    def _run_parallel(
        self, profiles: List[InputProfile], max_workers: int
    ) -> Dict[str, ProfileResult]:
        """Run profiles in parallel using ProcessPoolExecutor."""
        results = {}

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_profile = {
                executor.submit(self._run_profile_worker, str(self.config_path), profile): profile
                for profile in profiles
            }

            for future in as_completed(future_to_profile):
                profile = future_to_profile[future]
                try:
                    result = future.result()
                    profile_id = result.profile_id
                    results[profile_id] = result
                    logger.info(f"Completed {profile_id} ({len(results)}/{len(profiles)})")
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.error(f"Profile {profile} failed: {e}", exc_info=True)

        # Batch store all results sequentially
        logger.info(f"Parallel execution complete, storing {len(results)} results sequentially...")
        self.result_aggregator.batch_store_results(results)

        return results

    def _run_sequential(self, profiles: List[InputProfile]) -> Dict[str, ProfileResult]:
        """Run profiles sequentially."""
        results = {}

        for i, profile in enumerate(profiles, 1):
            try:
                result = self.run_single_profile(profile)
                results[result.profile_id] = result
                logger.info(f"Completed {i}/{len(profiles)}: {result.profile_id}")
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Profile {profile} failed: {e}", exc_info=True)

        return results

    @staticmethod
    def _run_profile_worker(config_path: str, profile: InputProfile) -> ProfileResult:
        """Worker function for parallel execution."""
        backtester = ProfileBatchBacktester(config_path)
        return backtester.run_single_profile(profile)

    def get_best_strategy(self, objective: str, tier: str, risk: str) -> Dict[str, Any]:
        """
        Get best strategy for specific objective, tier, and risk.

        Args:
            objective: Investment objective
            tier: Capital tier
            risk: Risk tolerance

        Returns:
            Best configuration for the criteria
        """
        return self.result_aggregator.get_best_strategy(objective, tier, risk)

    def export_results(self, format: str = "json") -> Path:
        """
        Export results to file.

        Args:
            format: Export format (json, csv, excel)

        Returns:
            Path to exported file
        """
        return self.report_generator.export_results(self.results, format)

    def generate_comparison_report(self) -> str:
        """
        Generate HTML comparison report.

        Returns:
            HTML report as string
        """
        return self.report_generator.generate_comparison_report(self.results)

    def get_fallback_metrics(self) -> Dict[str, int]:
        """
        Get current fallback metrics.

        Returns:
            Dictionary with fallback counts
        """
        with self._fallback_lock:
            return {
                "profile_config_loader_fallback_count": (
                    1 if self.profile_config_loader is None else 0
                ),
                "total_fallback_count": self._total_fallback_count,
            }

    def log_fallback_summary(self) -> None:
        """Log a summary of all fallback metrics."""
        metrics = self.get_fallback_metrics()
        total_fallbacks = sum(metrics.values())

        logger.info("=" * 60)
        logger.info("Fallback Metrics Summary:")
        logger.info(f"  Total fallbacks: {total_fallbacks}")
        logger.info("=" * 60)


def create_profile_batch_backtester(
    config_path: str = "config/profile_batch_backtest.yaml",
) -> ProfileBatchBacktester:
    """
    Convenience function to create ProfileBatchBacktester.

    Args:
        config_path: Path to configuration file

    Returns:
        ProfileBatchBacktester instance
    """
    return ProfileBatchBacktester(config_path)
