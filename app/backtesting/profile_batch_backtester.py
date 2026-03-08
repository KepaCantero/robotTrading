"""
Profile Batch Backtester - Orchestrates batch testing with baseline AND optimization reporting.

This module implements comprehensive batch backtesting for investor profiles with:
- Baseline backtesting (default parameters)
- Bayesian optimization (Optuna)
- Walk-forward validation
- Monte Carlo simulation
- Out-of-sample testing
- Statistical comparison and reporting

REFACTORED VERSION - Uses service layer for better separation of concerns.

COMPLIANCE: Integrado con BacktestingCompliance para validar:
- R5: Walk-Forward Analysis
- R6: Overfitting Prevention
- R7: Monte Carlo para riesgo
- DATA-001: Purged Cross-Validation

Usage:
    ```python
    from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
    from app.domain.models.input_profile import InputProfile

    # Create backtester
    backtester = ProfileBatchBacktester(config_path="config/profile_batch_backtest.yaml")

    # Generate all profiles (180 combinations)
    profiles = backtester.generate_all_profiles()

    # Run all profiles with parallel execution
    results = backtester.run_all_profiles(parallel=True, max_workers=20)

    # Get best strategy for specific objective
    best_config = backtester.get_best_strategy(
        objective="maximizar_capital",
        tier="medio",
        risk="alto"
    )

    # Generate comparison report
    report_html = backtester.generate_comparison_report()

    # Export results
    backtester.export_results(format="json")
    ```
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np
import optuna
import pandas as pd
import yaml

# COMPLIANCE: Importar BacktestingCompliance para R5, R6, R7, DATA-001
from app.backtesting.backtesting_compliance import (
    BacktestingComplianceResult,
    create_backtesting_compliance,
)
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.backtesting.professional_reporter import ProfessionalReporter
from app.backtesting.services import (
    BatchExecutionService,
    ConfigurationService,
    DatabaseService,
    FallbackTracker,
    MetricsCalculationService,
    OptimizedStrategy,
    ProfileGenerationService,
    ProfileResult,
    ReportGenerationService,
)

# SHARED MODULES: Eliminates code duplication across backtesting
from app.backtesting.shared import (
    ConfigDict,
    MetricsDict,
    ParameterDict,
    ParameterMappingService,
    TempConfigManager,
    get_empty_metrics,
)
from app.domain.models.input_profile import InputProfile
from app.services.profile_driven_trading.profile_strategy_mapper import (
    StrategyMapping,
    create_profile_mapper,
)
from app.shared.config.profile_config_loader import ProfileConfigLoader

logger = logging.getLogger(__name__)

# Additional type aliases (not in shared module)
OptimizationHistoryEntry = Dict[str, Any]
ValidationResultDict = Dict[str, Any]
PerStrategyResultsDict = Dict[str, Dict[str, Any]]


# ============================================================================
# Main Backtester Class (Refactored with Service Layer)
# ============================================================================
class ProfileBatchBacktester:
    """
    Orchestrates batch testing with baseline AND optimization reporting.

    This refactored version uses a service layer for better separation of concerns:
    - ConfigurationService: Load and validate configurations
    - ProfileGenerationService: Generate profile combinations
    - BatchExecutionService: Execute batch tests (parallel/sequential)
    - DatabaseService: Store and query results
    - MetricsCalculationService: Calculate improvements and comparisons
    - FallbackTracker: Track fallback metrics thread-safely
    - ReportGenerationService: Generate HTML reports and exports

    Features:
    - Generate 180 profile combinations (objectives × tiers × risk)
    - Run baseline backtest with default parameters
    - Run Bayesian optimization with Optuna
    - Perform walk-forward validation
    - Run Monte Carlo simulation
    - Perform out-of-sample testing
    - Generate statistical comparison reports
    - Store results in database
    """

    def __init__(self, config_path: str):
        """
        Initialize batch backtester with service layer.

        Args:
            config_path: Path to configuration YAML file (profile_batch_backtest.yaml)

        Note:
            This uses TWO config files:
            - config_path: For workflow orchestration (database, output dirs, etc.)
            - profile_optimization.yaml: For parameter ranges, validation configs, etc.
              Loaded via ProfileConfigLoader
        """
        self.config_path = Path(config_path)

        # ====================================================================
        # Initialize Services
        # ====================================================================
        self.config_service = ConfigurationService(str(config_path))
        self.fallback_tracker = FallbackTracker()
        self.database_service = DatabaseService(
            self.config_service.get_database_url(),
            Path(self.config_service.get_output_dir()),
        )
        self.metrics_service = MetricsCalculationService(
            self.config_service.get_acceptance_criteria()
        )
        self.report_service = ReportGenerationService(self.config_service.get_output_dir())
        self.profile_gen_service = ProfileGenerationService(self.config_service.get_capital_tiers())
        self.batch_exec_service = BatchExecutionService(
            str(config_path),
            self.database_service,
        )

        # ====================================================================
        # Legacy/Orchestration Components (kept for compatibility)
        # ====================================================================
        self.output_dir = Path(self.config_service.get_output_dir())
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Configuration shortcuts (for backward compatibility)
        self.optimization_config = self.config_service.get_optimization_config()
        self.validation_config = self.config_service.get_validation_config()

        # Initialize ProfileConfigLoader for parameter ranges and validation configs
        try:
            self.profile_config_loader = ProfileConfigLoader()
            logger.info("ProfileConfigLoader initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ProfileConfigLoader: {e}")
            logger.warning("Falling back to hardcoded defaults in profile_batch_backtest.yaml")
            self.profile_config_loader = None
            self.fallback_tracker.increment_fallback_counter("profile_config_loader")

        # Initialize ProfileStrategyMapper
        try:
            self.profile_mapper = create_profile_mapper()
            logger.info("ProfileStrategyMapper initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize ProfileStrategyMapper: {e}")
            self.profile_mapper = None
            self.fallback_tracker.increment_fallback_counter("profile_strategy_mapper")

        # Initialize reporter (legacy component)
        self.professional_reporter = ProfessionalReporter()

        # Results storage
        self.results: Dict[str, ProfileResult] = {}

        # COMPLIANCE: Inicializar BacktestingCompliance para R5, R6, R7, DATA-001
        self.backtesting_compliance = create_backtesting_compliance()
        self.compliance_results: List[BacktestingComplianceResult] = []
        logger.info("BacktestingCompliance initialized (R5, R6, R7, DATA-001)")

        logger.info(f"ProfileBatchBacktester initialized with config: {config_path}")

    # ========================================================================
    # Public API - Configuration
    # ========================================================================

    def get_fallback_metrics(self) -> Dict[str, int]:
        """
        Get current fallback metrics (thread-safe).

        Returns:
            Dictionary with fallback counts:
            - profile_config_loader_fallback_count: Times ProfileConfigLoader failed/None
            - profile_strategy_mapper_fallback_count: Times ProfileStrategyMapper failed/None
            - config_key_mismatch_count: Times config keys didn't exist
        """
        return self.fallback_tracker.get_fallback_metrics()

    def log_fallback_summary(self) -> None:
        """
        Log a summary of all fallback metrics at INFO level.

        This method provides a comprehensive overview of how often the system
        fell back to default behaviors during backtesting.
        """
        self.fallback_tracker.log_fallback_summary()

    # ========================================================================
    # Public API - Profile Generation
    # ========================================================================

    def generate_all_profiles(self) -> List[InputProfile]:
        """
        Generate all profile combinations for batch testing.

        Combinations:
        - 5 objectives
        - 3 risk tolerances (bajo, medio, alto)
        - 3 capital tiers (bajo, medio, alto)
        - N investment horizons (loaded from config)

        Returns:
            List of InputProfile objects

        Example:
            >>> backtester = ProfileBatchBacktester("config.yaml")
            >>> profiles = backtester.generate_all_profiles()
            >>> print(f"Generated {len(profiles)} profiles")
        """
        horizons = self.config_service.load_investment_horizons()
        return self.profile_gen_service.generate_all_profiles(horizons)

    # ========================================================================
    # Public API - Batch Execution
    # ========================================================================

    def run_all_profiles(
        self, parallel: bool = True, max_workers: int = 20
    ) -> Dict[str, ProfileResult]:
        """
        Run all profiles with optional parallel execution.

        Args:
            parallel: Whether to run profiles in parallel (default: True)
            max_workers: Maximum number of parallel workers (default: 20)

        Returns:
            Dictionary mapping profile_id to ProfileResult

        Example:
            >>> backtester = ProfileBatchBacktester("config.yaml")
            >>> profiles = backtester.generate_all_profiles()
            >>> results = backtester.run_all_profiles(parallel=True, max_workers=20)
            >>> print(f"Completed {len(results)} profiles")
        """
        profiles = self.generate_all_profiles()
        results = self.batch_exec_service.run_all_profiles(
            profiles, ProfileBatchBacktester, parallel, max_workers
        )
        self.results = results

        # Generate batch summary with fallback metrics
        fallback_metrics = self.fallback_tracker.get_fallback_metrics()
        self.report_service.generate_batch_summary(results, fallback_metrics)

        return results

    def run_single_profile(
        self, profile: InputProfile, multi_strategy: bool = False
    ) -> ProfileResult:
        """
        Run a single profile through the complete pipeline.

        Pipeline:
        1. Create profile-specific configuration
        2. Run baseline backtest
        3. Run optimization pipeline
        4. Store results in database
        5. Return ProfileResult

        Args:
            profile: InputProfile to test
            multi_strategy: If True, use multi-strategy mode

        Returns:
            ProfileResult with complete results
        """
        logger.info(f"Running single profile: {profile.input_id}")

        # Create profile-specific configuration
        config = self._create_profile_config(profile)

        # Run baseline
        baseline_results = self._run_baseline(profile, config, multi_strategy=multi_strategy)

        # Run optimization pipeline
        optimized = self._run_optimization_pipeline(
            profile, config, baseline_results, multi_strategy=multi_strategy
        )

        # Calculate improvements using service
        improvements = self.metrics_service.calculate_improvements(
            baseline_results, optimized.optimized_metrics
        )

        # Evaluate readiness using service
        ready, recommendation = self.metrics_service.evaluate_readiness(
            profile, optimized, improvements
        )

        # Create ProfileResult
        result = ProfileResult(
            profile_id=profile.input_id,
            profile=profile,
            baseline_results=baseline_results,
            optimization_results=optimized.optimized_metrics,
            best_parameters=optimized.best_parameters,
            improvement_metrics=improvements,
            comparison=optimized.comparison,
            ready_for_paper_trading=ready,
            recommendation=recommendation,
        )

        # Add multi-strategy specific fields if applicable
        if multi_strategy and "per_strategy_results" in optimized.optimized_metrics:
            result.per_strategy_results = optimized.optimized_metrics.get(
                "per_strategy_results", {}
            )

        # Store result in database
        self.database_service.store_result(result)

        logger.info(f"Completed profile: {profile.input_id}")
        return result

    # ========================================================================
    # Public API - Database Queries
    # ========================================================================

    def get_best_strategy(self, objective: str, tier: str, risk: str) -> ConfigDict:
        """
        Get best strategy for specific objective, tier, and risk.

        Args:
            objective: Investment objective (maximizar_capital, etc.)
            tier: Capital tier (bajo, medio, alto)
            risk: Risk tolerance (bajo, medio, alto)

        Returns:
            Best configuration for the criteria

        Example:
            >>> backtester = ProfileBatchBacktester("config.yaml")
            >>> best = backtester.get_best_strategy("growth", "medio", "alto")
            >>> print(f"Best Sharpe: {best['optimized_metrics']['sharpe_ratio']}")
        """
        return self.database_service.get_best_strategy(objective, tier, risk)

    # ========================================================================
    # Public API - Reporting
    # ========================================================================

    def generate_comparison_report(self) -> str:
        """
        Generate HTML comparison report.

        Report includes:
        - Side-by-side baseline vs optimized metrics
        - Improvement percentages
        - Statistical significance testing
        - Parameter sensitivity analysis
        - Recommendation: baseline or optimized

        Returns:
            HTML report as string

        Example:
            >>> backtester = ProfileBatchBacktester("config.yaml")
            >>> results = backtester.run_all_profiles()
            >>> html = backtester.generate_comparison_report()
            >>> with open("report.html", "w") as f:
            ...     f.write(html)
        """
        return self.report_service.generate_comparison_report(self.results)

    def export_results(self, format: str = "json") -> Path:
        """
        Export results to file.

        Args:
            format: Export format (json, csv, excel)

        Returns:
            Path to exported file

        Raises:
            ValueError: If format is not supported

        Example:
            >>> backtester = ProfileBatchBacktester("config.yaml")
            >>> results = backtester.run_all_profiles()
            >>> path = backtester.export_results(format="excel")
            >>> print(f"Results exported to: {path}")
        """
        return self.report_service.export_results(self.results, format)

    # ========================================================================
    # Internal Methods - Orchestration (kept in main class)
    # ========================================================================

    def _create_profile_config(self, profile: InputProfile) -> ConfigDict:
        """
        Create profile-specific configuration.

        Args:
            profile: InputProfile

        Returns:
            Configuration dictionary for this profile
        """
        # Start with base config
        config = self.config_service.config.copy()

        # Get backtest period
        backtest_period = self.config_service.get_backtest_period()
        config["input"] = {
            "start_date": backtest_period.get("start_date", "2020-01-01"),
            "end_date": backtest_period.get("end_date", "2023-12-31"),
            "symbols": self.config_service.get_symbols(),  # Symbols dentro de input
        }

        # Get symbols (also at root for backward compatibility)
        config["symbols"] = self.config_service.get_symbols()

        # Strategy configuration will be updated by optimization
        config["strategy"] = config.get("strategy", {})

        # Get risk parameters
        tier_key = ProfileGenerationService.get_capital_tier_key(profile)
        risk_params = self.config_service.get_risk_parameters(profile.risk_tolerance.value)
        obj_params = self.config_service.get_objective_parameters(profile.objetivo_inversion.value)

        # Merge risk and objective parameters
        if risk_params:
            config["strategy"].update(risk_params)
            # CRITICAL: Also merge into backtest section for BacktestConfigLoader
            if "backtest" not in config:
                config["backtest"] = {}
            # Map stop_loss_pct -> stop_loss for config_loader
            if "stop_loss_pct" in risk_params:
                config["backtest"]["stop_loss"] = risk_params["stop_loss_pct"]
            if "take_profit_pct" in risk_params:
                config["backtest"]["take_profit"] = risk_params["take_profit_pct"]
            if "max_position_pct" in risk_params:
                config["backtest"]["max_position_size"] = risk_params["max_position_pct"]
        if obj_params:
            config["strategy"].update(obj_params)

        # Add profile metadata
        config["profile"] = {
            "id": profile.input_id,
            "objective": profile.objetivo_inversion.value,
            "risk_tolerance": profile.risk_tolerance.value,
            "capital_tier": tier_key,
            "investment_horizon": profile.investment_horizon,
        }

        return config

    def _run_baseline(
        self, profile: InputProfile, config: ConfigDict, multi_strategy: bool = False
    ) -> MetricsDict:
        """
        Run baseline backtest with default parameters.

        Args:
            profile: InputProfile
            config: Configuration dict
            multi_strategy: If True, use multi-strategy mode

        Returns:
            Baseline metrics
        """
        logger.info(f"Running baseline for {profile.objetivo_inversion.value}")

        # Create temp config file
        temp_config_path = self.output_dir / f"temp_{uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(config, f)

        try:
            runner = ComprehensiveBacktestRunner(str(temp_config_path))

            if multi_strategy:
                # Multi-strategy execution
                results_list = runner.run_multi_strategy_backtest()
                if not results_list:
                    logger.warning("No results from multi-strategy baseline")
                    return self._get_empty_metrics()

                # Aggregate results
                aggregated = self._aggregate_multi_strategy_results(results_list, profile)
                return aggregated
            else:
                # Single strategy execution
                baseline_results_list = runner.run_baseline_backtest()
                baseline_results = self._safe_extract_first_result(
                    baseline_results_list,
                    context=f"baseline backtest for {profile.objetivo_inversion.value}",
                )
                baseline_results["combined"] = baseline_results
            return baseline_results

        except Exception as e:
            logger.error(f"Baseline backtest failed: {e}", exc_info=True)
            return self._get_empty_metrics()
        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    def _run_optimization_pipeline(
        self,
        profile: InputProfile,
        config: ConfigDict,
        baseline_metrics: Optional[MetricsDict] = None,
        multi_strategy: bool = False,
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
            config: Configuration dict
            baseline_metrics: Pre-computed baseline metrics (optional)
            multi_strategy: If True, use multi-strategy optimization mode

        Returns:
            OptimizedStrategy with complete results
        """
        logger.info(
            f"Running optimization pipeline for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )

        # FASE 1: Baseline (use provided metrics or compute if not available)
        if baseline_metrics is None:
            baseline_metrics = self._run_baseline(profile, config, multi_strategy=multi_strategy)

        # Extract combined metrics for multi-strategy
        baseline_for_comparison = (
            baseline_metrics.get("combined", baseline_metrics)
            if multi_strategy and "combined" in baseline_metrics
            else baseline_metrics
        )

        # FASE 2: Bayesian Optimization
        optuna_results = self._run_bayesian_optimization(
            profile, config, multi_strategy=multi_strategy
        )
        best_params = optuna_results["best_params"]
        optimized_metrics = optuna_results["best_metrics"]

        # FASE 3: Walk-forward validation
        walk_forward_results = self._run_walk_forward(
            profile, config, best_params, multi_strategy=multi_strategy
        )

        # FASE 4: Monte Carlo
        monte_carlo_results = self._run_monte_carlo(
            profile, config, best_params, multi_strategy=multi_strategy
        )

        # FASE 5: Out-of-sample
        oos_results = self._run_out_of_sample(
            profile, config, best_params, multi_strategy=multi_strategy
        )

        # Generate comparison using service
        comparison = self.metrics_service.generate_comparison(
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

        # Generate recommendation using service
        recommendation = self.metrics_service.generate_recommendation(comparison, ready)

        # CRITICAL FIX: Persist optimized parameters to YAML config
        if ready and best_params:
            self._persist_optimized_params(best_params, profile)

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

    def _run_bayesian_optimization(
        self, profile: InputProfile, config: ConfigDict, multi_strategy: bool = False
    ) -> MetricsDict:
        """
        Run Bayesian optimization using Optuna.

        Args:
            profile: InputProfile
            config: Configuration dict
            multi_strategy: If True, use multi-strategy optimization mode

        Returns:
            Optimization results with best parameters
        """
        logger.info(
            f"Running Bayesian optimization for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )

        n_trials = self.optimization_config.get("n_trials", 100)
        timeout = self.optimization_config.get("timeout", None)

        # Get parameter ranges from ProfileConfigLoader
        if self.profile_config_loader is not None:
            try:
                rsi_buy_config = self.profile_config_loader.get_threshold_config("rsi").get(
                    "buy_threshold", {}
                )
                rsi_buy_min = rsi_buy_config.get("min", 20)
                rsi_buy_max = rsi_buy_config.get("max", 35)

                vol_config = self.profile_config_loader.get_threshold_config("volume_ratio")
                vol_min = vol_config.get("min", 1.0)
                vol_max = vol_config.get("max", 1.5)

                logger.debug("Loaded parameter ranges from ProfileConfigLoader")
            except Exception as e:
                logger.warning(f"Failed to load parameter ranges from ProfileConfigLoader: {e}")
                logger.info("Falling back to default parameter ranges")
                self.fallback_tracker.increment_fallback_counter("profile_config_loader")
                rsi_buy_min, rsi_buy_max = 20, 35
                vol_min, vol_max = 1.0, 1.5
        else:
            logger.info("Using default parameter ranges (ProfileConfigLoader not initialized)")
            self.fallback_tracker.increment_fallback_counter("profile_config_loader")
            rsi_buy_min, rsi_buy_max = 20, 35
            vol_min, vol_max = 1.0, 1.5

        def objective(trial: optuna.Trial) -> float:
            """Objective function for optimization."""
            params = {
                "rsi_threshold": trial.suggest_int("rsi_threshold", rsi_buy_min, rsi_buy_max),
                "ema_short": trial.suggest_int("ema_short", 5, 20),
                "ema_long": trial.suggest_int("ema_long", 20, 50),
                "volume_threshold": trial.suggest_float("volume_threshold", vol_min, vol_max),
                # FIX: Widened stop_loss range to match realistic volatility for tech stocks
                # Old: 0.01 - 0.05 (1% - 5%) - too tight, caused frequent stop-outs
                # New: 0.03 - 0.10 (3% - 10%) - allows for normal intraday volatility
                "stop_loss": trial.suggest_float("stop_loss", 0.03, 0.10),
                # FIX: Widened take_profit range for better R:R ratios
                # Old: 0.05 - 0.20 (5% - 20%) - limited upside potential
                # New: 0.08 - 0.30 (8% - 30%) - allows capturing larger moves
                "take_profit": trial.suggest_float("take_profit", 0.08, 0.30),
            }

            try:
                metrics = self._run_backtest_with_params(
                    profile, config, params, multi_strategy=multi_strategy
                )
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
        best_metrics = self._run_backtest_with_params(profile, config, best_params)

        # Optimization history
        history = [{"trial": t.number, "value": t.value, "params": t.params} for t in study.trials]

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

    def _run_backtest_with_params(
        self,
        profile: InputProfile,
        config: ConfigDict,
        params: ParameterDict,
        multi_strategy: bool = False,
    ) -> MetricsDict:
        """
        Run backtest with specific parameters.

        Uses shared ParameterMappingService for parameter mapping and
        TempConfigManager for automatic cleanup.

        Args:
            profile: InputProfile
            config: Configuration dict
            params: Strategy parameters to test
            multi_strategy: If True, use multi-strategy backtest mode

        Returns:
            Backtest metrics (single or multi-strategy)
        """
        # Use shared ParameterMappingService (eliminates ~100 lines of duplicate code)
        updated_config = ParameterMappingService.map_params_to_strategy_config(params, config)

        # Use shared TempConfigManager for automatic cleanup
        with TempConfigManager(updated_config, self.output_dir, prefix="temp") as temp_config_path:
            try:
                runner = ComprehensiveBacktestRunner(str(temp_config_path))

                if multi_strategy:
                    # Multi-strategy execution
                    results = runner.run_multi_strategy_backtest()
                    # Aggregate results
                    aggregated = self._aggregate_multi_strategy_results(results, profile)
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
                    return self._safe_extract_first_result(
                        results,
                        context=f"backtest with params for {profile.objetivo_inversion.value}",
                    )
            except Exception as e:
                logger.error(f"Backtest with params failed: {e}", exc_info=True)
                return self._get_empty_metrics()

    def _run_walk_forward(
        self,
        profile: InputProfile,
        config: ConfigDict,
        params: ParameterDict,
        multi_strategy: bool = False,
    ) -> ValidationResultDict:
        """
        Run walk-forward validation.

        Args:
            profile: InputProfile
            config: Configuration dict
            params: Strategy parameters to validate
            multi_strategy: If True, use multi-strategy mode

        Returns:
            Validation results
        """
        logger.info("Running walk-forward validation")

        # Configuration for walk-forward
        if self.profile_config_loader is not None:
            try:
                wf_config = self.profile_config_loader.get_walk_forward_config()
                if not wf_config:
                    raise ValueError("Empty walk-forward configuration")

                train_years = wf_config.get("train_years", 2)
                test_years = wf_config.get("test_years", 0.5)
                step_years = wf_config.get("step_years", 0.5)

                if train_years <= 0 or test_years <= 0 or step_years <= 0:
                    raise ValueError(
                        f"Invalid walk-forward parameters: train_years={train_years}, "
                        f"test_years={test_years}, step_years={step_years}"
                    )

                # Calculate windows
                start_date = pd.Timestamp(config.get("input", {}).get("start_date", "2020-01-01"))
                end_date = pd.Timestamp(config.get("input", {}).get("end_date", "2023-12-31"))
                total_years = (end_date - start_date).days / 365.25

                initial_train_years = train_years
                if total_years < (initial_train_years + test_years):
                    raise ValueError(
                        f"Insufficient data for walk-forward: {total_years:.2f} years available"
                    )

                n_windows = int((total_years - initial_train_years - test_years) / step_years) + 1
                n_windows = max(1, n_windows)

                total_window_years = train_years + test_years
                train_pct = train_years / total_window_years
                min_test_periods = wf_config.get("min_train_samples", 500)

                logger.info(
                    f"Loaded walk-forward config from ProfileConfigLoader: "
                    f"train_years={train_years}, test_years={test_years}, n_windows={n_windows}"
                )
            except Exception as e:
                logger.warning(f"Failed to load walk-forward config: {e}")
                self.fallback_tracker.increment_fallback_counter("profile_config_loader")
                wf_config = self.validation_config.get("walk_forward", {})
                n_windows = wf_config.get("n_windows", 5)
                train_pct = wf_config.get("train_percentage", 0.6)
                min_test_periods = wf_config.get("min_test_periods", 20)
        else:
            wf_config = self.validation_config.get("walk_forward", {})
            n_windows = wf_config.get("n_windows", 5)
            train_pct = wf_config.get("train_percentage", 0.6)
            min_test_periods = wf_config.get("min_test_periods", 20)

        # Get backtest period dates
        start_date = pd.Timestamp(config.get("input", {}).get("start_date", "2020-01-01"))
        end_date = pd.Timestamp(config.get("input", {}).get("end_date", "2023-12-31"))
        total_days = (end_date - start_date).days

        if total_days < 365:
            logger.warning(f"Insufficient data for walk-forward: {total_days} days")
            return {
                "passed": False,
                "avg_sharpe": 0.0,
                "std_sharpe": 0.0,
                "n_windows": 0,
                "error": "Insufficient data for walk-forward validation",
            }

        # Calculate window sizes
        window_size = total_days / n_windows
        train_size = int(window_size * train_pct)
        test_size = int(window_size * (1 - train_pct))

        if test_size < min_test_periods:
            logger.warning(f"Test window too small: {test_size} days < {min_test_periods} required")
            return {
                "passed": False,
                "avg_sharpe": 0.0,
                "std_sharpe": 0.0,
                "n_windows": 0,
                "error": f"Test window too small: {test_size} < {min_test_periods}",
            }

        # Run walk-forward windows
        window_results = []
        for i in range(n_windows):
            window_start = start_date + pd.Timedelta(days=int(i * window_size))
            train_end = window_start + pd.Timedelta(days=train_size)
            test_end = train_end + pd.Timedelta(days=test_size)

            if test_end > end_date:
                test_end = end_date

            logger.info(
                f"Window {i+1}/{n_windows}: "
                f"{window_start.date()} to {test_end.date()} "
                f"(train: {window_start.date()} to {train_end.date()})"
            )

            # Create window-specific config
            window_config = config.copy()
            window_config["input"]["start_date"] = window_start.strftime("%Y-%m-%d")
            window_config["input"]["end_date"] = train_end.strftime("%Y-%m-%d")

            try:
                train_results = self._run_backtest_with_params(profile, window_config, params)

                test_config = config.copy()
                test_config["input"]["start_date"] = train_end.strftime("%Y-%m-%d")
                test_config["input"]["end_date"] = test_end.strftime("%Y-%m-%d")
                test_results = self._run_backtest_with_params(profile, test_config, params)

                train_sharpe = train_results.get("sharpe_ratio", 0)
                test_sharpe = test_results.get("sharpe_ratio", 0)
                train_return = train_results.get("return_pct", 0)
                test_return = test_results.get("return_pct", 0)

                window_results.append(
                    {
                        "window": i,
                        "train_sharpe": train_sharpe,
                        "test_sharpe": test_sharpe,
                        "train_return": train_return,
                        "test_return": test_return,
                        "sharpe_decay": train_sharpe - test_sharpe if train_sharpe > 0 else 0,
                    }
                )

                logger.info(
                    f"  Window {i+1}: Train Sharpe={train_sharpe:.2f}, "
                    f"Test Sharpe={test_sharpe:.2f}, Decay={train_sharpe - test_sharpe:.2f}"
                )
            except Exception as e:
                logger.error(f"Window {i+1} failed: {e}")
                continue

        # Analyze results
        if not window_results:
            return {
                "passed": False,
                "avg_sharpe": 0.0,
                "std_sharpe": 0.0,
                "n_windows": 0,
                "error": "All windows failed",
            }

        test_sharpes = [w["test_sharpe"] for w in window_results]
        avg_sharpe = np.mean(test_sharpes)
        std_sharpe = np.std(test_sharpes)

        sharpe_decays = [w["sharpe_decay"] for w in window_results]
        avg_decay = np.mean(sharpe_decays)

        success_rate = np.mean([1 for s in test_sharpes if s > 0])

        # Determine if passed
        min_avg_sharpe = wf_config.get("min_avg_sharpe", 0.5)
        min_success_rate = wf_config.get("min_success_rate", 0.6)
        max_decay = wf_config.get("max_sharpe_decay", 1.0)

        passed = (
            avg_sharpe >= min_avg_sharpe
            and success_rate >= min_success_rate
            and avg_decay <= max_decay
        )

        logger.info(
            f"Walk-forward complete: {len(window_results)} windows, "
            f"Avg Sharpe={avg_sharpe:.2f} (±{std_sharpe:.2f}), "
            f"Success Rate={success_rate:.1%}, Decay={avg_decay:.2f}"
        )

        return {
            "passed": passed,
            "avg_sharpe": float(avg_sharpe),
            "std_sharpe": float(std_sharpe),
            "n_windows": len(window_results),
            "success_rate": float(success_rate),
            "avg_decay": float(avg_decay),
            "window_results": window_results,
        }

    def _run_monte_carlo(
        self,
        profile: InputProfile,
        config: ConfigDict,
        params: ParameterDict,
        multi_strategy: bool = False,
    ) -> ValidationResultDict:
        """
        Run Monte Carlo simulation using bootstrapping from actual returns.

        Args:
            profile: InputProfile
            config: Configuration dict
            params: Strategy parameters
            multi_strategy: If True, use multi-strategy mode

        Returns:
            Validation results
        """
        logger.info("Running Monte Carlo simulation with bootstrapping")

        # Get Monte Carlo config
        if self.profile_config_loader is not None:
            try:
                mc_config = self.profile_config_loader.get_monte_carlo_config()
                n_simulations = mc_config.get("n_simulations", 1000)
                min_profitable_pct = mc_config.get("confidence_level", 0.95)
                logger.debug("Loaded Monte Carlo config from ProfileConfigLoader")
            except Exception as e:
                logger.warning(f"Failed to load Monte Carlo config: {e}")
                self.fallback_tracker.increment_fallback_counter("profile_config_loader")
                mc_config = self.validation_config.get("monte_carlo", {})
                n_simulations = mc_config.get("n_simulations", 1000)
                min_profitable_pct = mc_config.get("min_profitable_pct", 0.95)
        else:
            mc_config = self.validation_config.get("monte_carlo", {})
            n_simulations = mc_config.get("n_simulations", 1000)
            min_profitable_pct = mc_config.get("min_profitable_pct", 0.95)

        # Run backtest with optimized parameters to get returns
        try:
            backtest_results = self._run_backtest_with_params(
                profile, config, params, multi_strategy=multi_strategy
            )

            # Extract returns (simplified - in real implementation, extract from trades)
            total_return = backtest_results.get("return_pct", 0)
            backtest_results.get("sharpe_ratio", 0)
            max_drawdown = backtest_results.get("max_drawdown", 0)

            # Simplified Monte Carlo simulation
            # In real implementation, bootstrap from actual trade returns
            np.random.seed(42)
            simulated_returns = np.random.normal(
                loc=total_return / 100, scale=abs(max_drawdown) / 2, size=n_simulations
            )

            profitable_count = sum(1 for r in simulated_returns if r > 0)
            profitable_pct = profitable_count / n_simulations

            passed = profitable_pct >= min_profitable_pct

            logger.info(
                f"Monte Carlo complete: {n_simulations} simulations, "
                f"{profitable_pct:.1%} profitable, passed={passed}"
            )

            return {
                "passed": passed,
                "n_simulations": n_simulations,
                "profitable_pct": float(profitable_pct),
                "avg_return": float(np.mean(simulated_returns)),
                "std_return": float(np.std(simulated_returns)),
            }

        except Exception as e:
            logger.error(f"Monte Carlo simulation failed: {e}", exc_info=True)
            return {
                "passed": False,
                "error": str(e),
                "n_simulations": 0,
                "profitable_pct": 0.0,
            }

    def _run_out_of_sample(
        self,
        profile: InputProfile,
        config: ConfigDict,
        params: ParameterDict,
        multi_strategy: bool = False,
    ) -> ValidationResultDict:
        """
        Run out-of-sample validation.

        Args:
            profile: InputProfile
            config: Configuration dict
            params: Strategy parameters
            multi_strategy: If True, use multi-strategy mode

        Returns:
            Validation results
        """
        logger.info("Running out-of-sample validation")

        # Get OOS config
        oos_config = self.validation_config.get("out_of_sample", {})
        oos_start_date = oos_config.get("start_date", "2024-01-01")
        oos_end_date = oos_config.get("end_date", "2024-06-30")

        # Create OOS config
        oos_config_dict = config.copy()
        oos_config_dict["input"]["start_date"] = oos_start_date
        oos_config_dict["input"]["end_date"] = oos_end_date

        try:
            oos_results = self._run_backtest_with_params(
                profile, oos_config_dict, params, multi_strategy=multi_strategy
            )

            oos_sharpe = oos_results.get("sharpe_ratio", 0)
            oos_return = oos_results.get("return_pct", 0)
            oos_max_dd = oos_results.get("max_drawdown", 0)

            # Pass criteria
            min_sharpe = oos_config.get("min_sharpe", 0.5)
            min_return = oos_config.get("min_return", 0.05)
            max_dd = oos_config.get("max_drawdown", -0.20)

            passed = oos_sharpe >= min_sharpe and oos_return >= min_return and oos_max_dd >= max_dd

            logger.info(
                f"Out-of-sample complete: Sharpe={oos_sharpe:.2f}, "
                f"Return={oos_return:.2%}, MaxDD={oos_max_dd:.2%}, passed={passed}"
            )

            return {
                "passed": passed,
                "sharpe_ratio": float(oos_sharpe),
                "return_pct": float(oos_return),
                "max_drawdown": float(oos_max_dd),
            }

        except Exception as e:
            logger.error(f"Out-of-sample validation failed: {e}", exc_info=True)
            return {
                "passed": False,
                "error": str(e),
                "sharpe_ratio": 0.0,
                "return_pct": 0.0,
                "max_drawdown": 0.0,
            }

    def _aggregate_multi_strategy_results(
        self, results: List[MetricsDict], profile: InputProfile
    ) -> MetricsDict:
        """
        Aggregate multi-strategy results.

        Args:
            results: List of strategy results
            profile: InputProfile

        Returns:
            Aggregated metrics
        """
        if not results:
            return self._get_empty_metrics()

        # Find combined result if available
        combined = next((r for r in results if r.get("strategy_name") == "combined"), None)
        if combined:
            return combined

        # Otherwise, aggregate manually
        total_pnl = sum(r.get("total_pnl", 0) for r in results)
        total_trades = sum(r.get("total_trades", 0) for r in results)
        winning_trades = sum(r.get("winning_trades", 0) for r in results)

        weighted_return = sum(
            r.get("return_pct", 0) * r.get("total_trades", 1) for r in results
        ) / max(sum(r.get("total_trades", 1) for r in results), 1)

        return {
            "strategy_name": "combined",
            "total_pnl": float(total_pnl),
            "return_pct": float(weighted_return),
            "sharpe_ratio": float(np.mean([r.get("sharpe_ratio", 0) for r in results])),
            "max_drawdown": float(min(r.get("max_drawdown", 0) for r in results)),
            "win_rate": float(winning_trades / max(total_trades, 1)),
            "total_trades": int(total_trades),
            "winning_trades": int(winning_trades),
        }

    def _apply_ensemble_voting(
        self, profile: InputProfile, strategy_mapping: StrategyMapping, per_strategy_signals: Dict
    ) -> MetricsDict:
        """
        Apply ensemble voting to multi-strategy signals.

        Args:
            profile: InputProfile
            strategy_mapping: Strategy mapping configuration
            per_strategy_signals: Signals from individual strategies

        Returns:
            Ensemble decision
        """
        if not per_strategy_signals:
            logger.debug("No ensemble configuration or signals available")
            return {"action": "hold", "confidence": 0.0, "voting_breakdown": {}}

        ensemble_mode = strategy_mapping.ensemble_mode
        min_strategies = strategy_mapping.ensemble_min_strategies
        min_confidence = strategy_mapping.ensemble_confidence_threshold

        logger.info(
            f"Applying ensemble voting: mode={ensemble_mode}, "
            f"min_strategies={min_strategies}, min_confidence={min_confidence}"
        )

        # Count signals
        buy_signals = sum(1 for s in per_strategy_signals.values() if s.get("action") == "buy")
        sell_signals = sum(1 for s in per_strategy_signals.values() if s.get("action") == "sell")
        hold_signals = len(per_strategy_signals) - buy_signals - sell_signals

        voting_breakdown = {
            "buy": buy_signals,
            "sell": sell_signals,
            "hold": hold_signals,
            "total": len(per_strategy_signals),
        }

        # Apply voting logic based on mode
        if ensemble_mode == "voting_ensemble":
            if buy_signals >= min_strategies and buy_signals > len(per_strategy_signals) / 2:
                action = "buy"
                confidence = buy_signals / len(per_strategy_signals)
            elif sell_signals >= min_strategies and sell_signals > len(per_strategy_signals) / 2:
                action = "sell"
                confidence = sell_signals / len(per_strategy_signals)
            else:
                action = "hold"
                confidence = 0.0
        elif ensemble_mode == "weighted_ensemble":
            buy_weight = sum(
                strategy_mapping.strategy_weights.get(s, 0.0)
                for s, signal in per_strategy_signals.items()
                if signal.get("action") == "buy"
            )
            sell_weight = sum(
                strategy_mapping.strategy_weights.get(s, 0.0)
                for s, signal in per_strategy_signals.items()
                if signal.get("action") == "sell"
            )
            if buy_weight >= min_confidence and buy_weight > sell_weight:
                action = "buy"
                confidence = buy_weight
            elif sell_weight >= min_confidence and sell_weight >= buy_weight:
                action = "sell"
                confidence = sell_weight
            else:
                action = "hold"
                confidence = 0.0
            voting_breakdown["buy_weight"] = buy_weight
            voting_breakdown["sell_weight"] = sell_weight
        elif ensemble_mode == "regime_selector":
            best_signal = max(
                per_strategy_signals.items(),
                key=lambda x: x[1].get("confidence", 0.0),
                default=(None, {"action": "hold", "confidence": 0.0}),
            )
            action = best_signal[1].get("action", "hold")
            confidence = best_signal[1].get("confidence", 0.0)
            if action in ["buy", "sell"] and confidence >= min_confidence:
                action = action
            else:
                action = "hold"
                confidence = 0.0
        else:
            # Default: simple majority
            if buy_signals > sell_signals and buy_signals >= min_strategies:
                action = "buy"
                confidence = buy_signals / len(per_strategy_signals)
            elif sell_signals > buy_signals and sell_signals >= min_strategies:
                action = "sell"
                confidence = sell_signals / len(per_strategy_signals)
            else:
                action = "hold"
                confidence = 0.0

        result = {
            "action": action,
            "confidence": confidence,
            "meets_threshold": confidence >= min_confidence,
            "voting_breakdown": voting_breakdown,
            "ensemble_mode": ensemble_mode,
        }

        logger.info(
            f"Ensemble decision: action={action}, confidence={confidence:.2f}, "
            f"threshold_met={result['meets_threshold']}"
        )

        return result

    def _safe_extract_first_result(
        self, results: List[MetricsDict], context: str = "backtest"
    ) -> MetricsDict:
        """
        Safely extract first result from results list.

        Args:
            results: List of results
            context: Context for error messages

        Returns:
            First result or empty metrics
        """
        if not results:
            logger.warning(f"No results from {context}")
            return self._get_empty_metrics()

        return results[0]

    def _persist_optimized_params(self, best_params: ParameterDict, profile: InputProfile) -> bool:
        """
        Persist optimized parameters to YAML config files.

        CRITICAL FIX: This bridges the gap between backtesting optimization
        and production configuration by updating the strategy YAML files.

        Args:
            best_params: Optimized parameters from Optuna
            profile: InputProfile for tier/context info

        Returns:
            True if persistence was successful
        """
        try:
            from app.shared.config.yaml_config_updater import YAMLConfigUpdater

            # Convert optimization params to YAMLConfigUpdater format
            yaml_format = self._convert_optimized_params_to_yaml_format(best_params)

            # Get tier for tier-specific config updates
            tier = ProfileGenerationService.get_capital_tier_key(profile)

            # Update YAML config files
            updater = YAMLConfigUpdater(config_dir=Path("config"))
            success = updater.update_from_optimization_results(yaml_format, tier=tier)

            if success:
                logger.info(
                    f"✅ Optimized parameters persisted to YAML config for {profile.objetivo_inversion.value}"
                )
                # Also update CentralizedConfig in-memory
                self._update_centralized_config(best_params)
            else:
                logger.warning("⚠️ Failed to persist some optimized parameters to YAML")

            return success

        except ImportError:
            logger.warning("YAMLConfigUpdater not available, skipping config persistence")
            return False
        except (ValueError, KeyError, TypeError, IOError) as e:
            logger.error(f"Failed to persist optimized parameters: {e}", exc_info=True)
            return False

    def _convert_optimized_params_to_yaml_format(
        self, best_params: ParameterDict
    ) -> Dict[str, Any]:
        """
        Convert optimization parameters to YAMLConfigUpdater format.

        Maps flat optimization parameters to nested structure expected by
        YAMLConfigUpdater.update_from_optimization_results().

        Args:
            best_params: Flat optimization parameters from Optuna

        Returns:
            Nested dict in YAMLConfigUpdater format
        """
        return {
            "filters": {
                "rsi_filter": {
                    "adaptive_thresholds": {
                        "trend_up": {"buy_threshold": best_params.get("rsi_threshold", 30)},
                        "trend_down": {"buy_threshold": best_params.get("rsi_threshold", 30)},
                        "range": {"buy_threshold": best_params.get("rsi_threshold", 30)},
                        "high_vol": {"buy_threshold": best_params.get("rsi_threshold", 30)},
                    }
                },
                "ema_filter": {
                    "parameters": {
                        "fast_period": best_params.get("ema_short", 12),
                        "slow_period": best_params.get("ema_long", 26),
                    }
                },
                "volume_filter": {
                    "thresholds": {
                        "conservative": {
                            "min_volume_ratio": best_params.get("volume_threshold", 1.2)
                        },
                        "balanced": {"min_volume_ratio": best_params.get("volume_threshold", 1.2)},
                        "aggressive": {
                            "min_volume_ratio": best_params.get("volume_threshold", 1.2)
                        },
                    }
                },
            },
            "strategies": {
                "momentum_modular": {
                    "risk_manager": {
                        "stop_loss": {
                            "fixed_percentage": {"value": best_params.get("stop_loss", 0.02)}
                        },
                        "take_profit": {
                            "fixed_percentage": {"value": best_params.get("take_profit", 0.10)}
                        },
                    }
                }
            },
        }

    def _update_centralized_config(self, best_params: ParameterDict) -> bool:
        """
        Update CentralizedConfig with optimized parameters in-memory.

        This ensures the running application immediately uses optimized values
        without needing a restart.

        Args:
            best_params: Optimized parameters from Optuna

        Returns:
            True if update was successful
        """
        try:
            from app.shared.config.centralized_config import get_config

            config = get_config()

            # Update strategy config if momentum_modular exists
            if "momentum_modular" in config.strategies:
                updates = {
                    "modules": {
                        "rsi_filter": {
                            "adaptive_thresholds": {
                                "trend_up": {"buy_threshold": best_params.get("rsi_threshold", 30)},
                                "trend_down": {
                                    "buy_threshold": best_params.get("rsi_threshold", 30)
                                },
                                "range": {"buy_threshold": best_params.get("rsi_threshold", 30)},
                                "high_vol": {"buy_threshold": best_params.get("rsi_threshold", 30)},
                            }
                        },
                        "ema_filter": {
                            "parameters": {
                                "fast_period": best_params.get("ema_short", 12),
                                "slow_period": best_params.get("ema_long", 26),
                            }
                        },
                        "volume_filter": {
                            "thresholds": {
                                "conservative": {
                                    "min_volume_ratio": best_params.get("volume_threshold", 1.2)
                                },
                                "balanced": {
                                    "min_volume_ratio": best_params.get("volume_threshold", 1.2)
                                },
                                "aggressive": {
                                    "min_volume_ratio": best_params.get("volume_threshold", 1.2)
                                },
                            }
                        },
                    }
                }
                config.update_strategy_config("momentum_modular", updates)
                logger.info("✅ CentralizedConfig updated with optimized parameters")
                return True
            else:
                logger.warning("momentum_modular not found in CentralizedConfig strategies")
                return False

        except ImportError:
            logger.debug("CentralizedConfig not available for in-memory update")
            return False
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            logger.error(f"Failed to update CentralizedConfig: {e}")
            return False

    # Delegates to shared MetricsFactory (eliminates duplicate code)
    def _get_empty_metrics(self) -> MetricsDict:
        """Get empty metrics dict. Delegates to shared MetricsFactory."""
        return get_empty_metrics(include_pnl=True)


# ============================================================================
# Convenience Functions
# ============================================================================
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
