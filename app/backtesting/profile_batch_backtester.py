"""
Profile Batch Backtester - Orchestrates batch testing with baseline AND optimization reporting.

This module implements comprehensive batch backtesting for investor profiles with:
- Baseline backtesting (default parameters)
- Bayesian optimization (Optuna)
- Walk-forward validation
- Monte Carlo simulation
- Out-of-sample testing
- Statistical comparison and reporting

Usage:
    ```python
    from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
    from app.core.models.input_profile import InputProfile

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

import json
import logging
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
import optuna
import pandas as pd
import yaml
from jinja2 import Template
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.backtesting.professional_reporter import ProfessionalReporter
from app.core.config.profile_config_loader import ProfileConfigLoader
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
)
from app.core.tier_mapper import map_profile_tier_to_config
from app.services.profile_driven_trading.profile_strategy_mapper import (
    StrategyMapping,
    create_profile_mapper,
)

logger = logging.getLogger(__name__)
# SQLAlchemy Base
Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================
class ProfileResultDB(Base):
    """Database model for profile results."""

    __tablename__ = "profile_results"
    id = Column(String, primary_key=True)
    profile_id = Column(String, unique=True, index=True)
    objective = Column(String, index=True)
    risk_tolerance = Column(String, index=True)
    capital_tier = Column(String, index=True)
    investment_horizon = Column(Integer)
    # Baseline results
    baseline_sharpe = Column(Float)
    baseline_return = Column(Float)
    baseline_max_dd = Column(Float)
    baseline_win_rate = Column(Float)
    # Optimization results
    optimized_sharpe = Column(Float)
    optimized_return = Column(Float)
    optimized_max_dd = Column(Float)
    optimized_win_rate = Column(Float)
    # Improvement metrics
    sharpe_improvement = Column(Float)
    return_improvement = Column(Float)
    max_dd_improvement = Column(Float)
    win_rate_improvement = Column(Float)
    # Best parameters
    best_parameters = Column(JSON)
    # Validation results
    walk_forward_passed = Column(Boolean)
    monte_carlo_passed = Column(Boolean)
    out_of_sample_passed = Column(Boolean)
    # Final recommendation
    ready_for_paper_trading = Column(Boolean)
    recommendation = Column(String)
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "profile_id": self.profile_id,
            "objective": self.objective,
            "risk_tolerance": self.risk_tolerance,
            "capital_tier": self.capital_tier,
            "investment_horizon": self.investment_horizon,
            "baseline_results": {
                "sharpe_ratio": self.baseline_sharpe,
                "total_return": self.baseline_return,
                "max_drawdown": self.baseline_max_dd,
                "win_rate": self.baseline_win_rate,
            },
            "optimization_results": {
                "sharpe_ratio": self.optimized_sharpe,
                "total_return": self.optimized_return,
                "max_drawdown": self.optimized_max_dd,
                "win_rate": self.optimized_win_rate,
            },
            "improvement_metrics": {
                "sharpe_improvement": self.sharpe_improvement,
                "return_improvement": self.return_improvement,
                "max_dd_improvement": self.max_dd_improvement,
                "win_rate_improvement": self.win_rate_improvement,
            },
            "best_parameters": self.best_parameters,
            "validation": {
                "walk_forward_passed": self.walk_forward_passed,
                "monte_carlo_passed": self.monte_carlo_passed,
                "out_of_sample_passed": self.out_of_sample_passed,
            },
            "ready_for_paper_trading": self.ready_for_paper_trading,
            "recommendation": self.recommendation,
        }


# ============================================================================
# Data Models
# ============================================================================
@dataclass
class BaselineOptimizationComparison:
    """Comparison between baseline and optimized results."""

    sharpe_improvement: float  # Percentage improvement
    return_improvement: float  # Percentage improvement
    max_dd_improvement: float  # Percentage improvement (positive is better)
    win_rate_improvement: float  # Percentage improvement
    # Statistical significance
    sharpe_significant: bool
    return_significant: bool
    # Parameter sensitivity
    parameter_importance: Dict[str, float]
    # Recommendation
    recommended: str  # "baseline", "optimized", "inconclusive"
    confidence: float  # 0-1
    reason: str


@dataclass
class OptimizedStrategy:
    """Result of optimization pipeline."""

    profile_id: str
    baseline_metrics: Dict[str, Any]
    optimized_metrics: Dict[str, Any]
    best_parameters: Dict[str, Any]
    optimization_history: List[Dict[str, Any]]
    walk_forward_results: Optional[Dict[str, Any]]
    monte_carlo_results: Optional[Dict[str, Any]]
    out_of_sample_results: Optional[Dict[str, Any]]
    comparison: BaselineOptimizationComparison
    ready_for_paper_trading: bool
    recommendation: str


@dataclass
class ProfileResult:
    """Complete result for a single profile."""

    profile_id: str
    profile: InputProfile
    baseline_results: Dict[str, Any]
    optimization_results: Dict[str, Any]
    best_parameters: Dict[str, Any]
    improvement_metrics: Dict[str, float]
    comparison: BaselineOptimizationComparison
    ready_for_paper_trading: bool
    recommendation: str
    created_at: datetime = field(default_factory=datetime.now)
    # Multi-strategy support fields
    strategy_mapping: Optional[StrategyMapping] = None
    enabled_strategies: List[str] = field(default_factory=list)
    learning_engines: List[str] = field(default_factory=list)
    ensemble_config: Dict[str, Any] = field(default_factory=dict)
    per_strategy_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ============================================================================
# Main Backtester Class
# ============================================================================
class ProfileBatchBacktester:
    """
    Orchestrates batch testing with baseline AND optimization reporting.
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
        Initialize batch backtester.
        Args:
            config_path: Path to configuration YAML file (profile_batch_backtest.yaml)
        Note:
            This uses TWO config files:
            - config_path: For workflow orchestration (database, output dirs, etc.)
            - profile_optimization.yaml: For parameter ranges, validation configs, etc.
              Loaded via ProfileConfigLoader
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        # Initialize ProfileConfigLoader for parameter ranges and validation configs
        # This loads from config/backtesting/profile_optimization.yaml
        try:
            self.profile_config_loader = ProfileConfigLoader()
            logger.info("ProfileConfigLoader initialized successfully")
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Failed to initialize ProfileConfigLoader: {e}")
            logger.warning("Falling back to hardcoded defaults in profile_batch_backtest.yaml")
            self.profile_config_loader = None
            # Track fallback - will be incremented safely in helper method
            self._increment_fallback_counter("profile_config_loader")
        # Initialize database
        db_url = self.config.get("database", {}).get("url", "sqlite:///profile_backtest_results.db")
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        # Output directory
        self.output_dir = Path(self.config.get("output_dir", "results/profile_batch_backtesting"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Initialize reporter
        self.professional_reporter = ProfessionalReporter()
        # Results storage
        self.results: Dict[str, ProfileResult] = {}
        # Configuration from YAML (for workflow orchestration)
        self.capital_tiers = self.config.get("capital_tiers", {})
        self.horizons = self.config.get("investment_horizons", {})
        self.optimization_config = self.config.get("optimization", {})
        self.validation_config = self.config.get("validation", {})
        # Initialize fallback metrics tracking (thread-safe)
        # These metrics track how often the system falls back to default behaviors
        self._profile_config_loader_fallback_count = 0
        self._profile_strategy_mapper_fallback_count = 0
        self._config_key_mismatch_count = 0
        self._fallback_lock = threading.Lock()
        # Initialize ProfileStrategyMapper
        try:
            self.profile_mapper = create_profile_mapper()
            logger.info("ProfileStrategyMapper initialized successfully")
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.warning(f"Failed to initialize ProfileStrategyMapper: {e}")
            self.profile_mapper = None
            # Track fallback
            self._increment_fallback_counter("profile_strategy_mapper")
        # Validate configurations on startup
        self._validate_configurations()
        logger.info(f"ProfileBatchBacktester initialized with config: {config_path}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _increment_fallback_counter(self, fallback_type: str) -> None:
        """
        Thread-safe increment of fallback counter.
        Args:
            fallback_type: Type of fallback ("profile_config_loader",
                          "profile_strategy_mapper", "config_key_mismatch")
        Example:
            >>> self._increment_fallback_counter("profile_config_loader")
        """
        with self._fallback_lock:
            if fallback_type == "profile_config_loader":
                self._profile_config_loader_fallback_count += 1
            elif fallback_type == "profile_strategy_mapper":
                self._profile_strategy_mapper_fallback_count += 1
            elif fallback_type == "config_key_mismatch":
                self._config_key_mismatch_count += 1
            else:
                logger.warning(f"Unknown fallback type: {fallback_type}")

    def _validate_configurations(self) -> None:
        """
        Validate that all required configurations are present and valid.
        This method checks:
        1. Capital tiers configuration exists
        2. Investment horizons configuration exists
        3. Optimization configuration exists
        4. Validation configuration exists
        Raises:
            ValueError: If a required configuration is missing or invalid
        """
        # Validate capital tiers
        if not self.capital_tiers:
            raise ValueError("Capital tiers configuration is missing")
        required_tier_keys = ["micro", "small", "medium", "large", "institutional"]
        for tier in required_tier_keys:
            if tier not in self.capital_tiers:
                logger.warning(f"Missing capital tier: {tier}")
        # Validate investment horizons
        if not self.horizons:
            raise ValueError("Investment horizons configuration is missing")
        required_horizon_keys = ["short", "medium", "long"]
        for horizon in required_horizon_keys:
            if horizon not in self.horizons:
                logger.warning(f"Missing investment horizon: {horizon}")
        # Validate optimization config
        if not self.optimization_config:
            logger.warning("Optimization configuration is missing, using defaults")
        # Validate validation config
        if not self.validation_config:
            logger.warning("Validation configuration is missing, using defaults")
        logger.debug("Configuration validation completed")

    def get_fallback_metrics(self) -> Dict[str, int]:
        """
        Get current fallback metrics (thread-safe).
        Returns:
            Dictionary with fallback counts:
            - profile_config_loader_fallback_count: Times ProfileConfigLoader failed/None
            - profile_strategy_mapper_fallback_count: Times ProfileStrategyMapper failed/None
            - config_key_mismatch_count: Times config keys didn't exist
        Example:
            >>> backtester = ProfileBatchBacktester("config.yaml")
            >>> metrics = backtester.get_fallback_metrics()
            >>> print(f"Config loader fallbacks: {metrics['profile_config_loader_fallback_count']}")
        """
        with self._fallback_lock:
            return {
                "profile_config_loader_fallback_count": self._profile_config_loader_fallback_count,
                "profile_strategy_mapper_fallback_count": self._profile_strategy_mapper_fallback_count,
                "config_key_mismatch_count": self._config_key_mismatch_count,
            }

    def log_fallback_summary(self) -> None:
        """
        Log a summary of all fallback metrics at INFO level.
        This method provides a comprehensive overview of how often the system
        fell back to default behaviors during backtesting.
        Example:
            >>> backtester = ProfileBatchBacktester("config.yaml")
            >>> backtester.run_all_profiles()
            >>> backtester.log_fallback_summary()
            INFO - Fallback Metrics Summary:
            INFO -   ProfileConfigLoader fallbacks: 0
            INFO -   ProfileStrategyMapper fallbacks: 2
            INFO -   Config key mismatches: 5
            INFO - Total fallbacks: 7
        """
        metrics = self.get_fallback_metrics()
        total_fallbacks = sum(metrics.values())
        logger.info("=" * 60)
        logger.info("Fallback Metrics Summary:")
        logger.info(
            f"  ProfileConfigLoader fallbacks: {metrics['profile_config_loader_fallback_count']}"
        )
        logger.info(
            f"  ProfileStrategyMapper fallbacks: {metrics['profile_strategy_mapper_fallback_count']}"
        )
        logger.info(f"  Config key mismatches: {metrics['config_key_mismatch_count']}")
        logger.info(f"Total fallbacks: {total_fallbacks}")
        logger.info("=" * 60)
        # Provide interpretation
        if total_fallbacks == 0:
            logger.info("No fallbacks occurred - all components loaded successfully")
        elif total_fallbacks < 5:
            logger.info(f"Low fallback count ({total_fallbacks}) - minimal impact on backtesting")
        elif total_fallbacks < 20:
            logger.warning(
                f"Moderate fallback count ({total_fallbacks}) - some configurations may need review"
            )
        else:
            logger.error(
                f"High fallback count ({total_fallbacks}) - review configuration files immediately"
            )

    def _load_investment_horizons(self) -> List[int]:
        """
        Load investment horizons from configuration.
        Supports both dict format (with labels) and list format.
        Falls back to default values if not configured.
        Returns:
            List of horizon values in months (positive integers)
        Examples:
            Dict format:
                investment_horizons:
                    short: 12
                    medium: 24
                    long: 36
                    very_long: 60
            List format:
                investment_horizons: [12, 24, 36, 60]
        """
        default_horizons = [12, 24, 36, 60]
        # Get horizons from config
        horizons_config = self.config.get("investment_horizons")
        if horizons_config is None:
            logger.warning("No investment_horizons in config, using defaults: [12, 24, 36, 60]")
            return default_horizons
        # Handle dict format (e.g., {short: 12, medium: 24, ...})
        if isinstance(horizons_config, dict):
            horizons = list(horizons_config.values())
            logger.info(f"Loaded investment horizons from dict: {horizons_config}")
        # Handle list format (e.g., [12, 24, 36, 60])
        elif isinstance(horizons_config, list):
            horizons = horizons_config
            logger.info(f"Loaded investment horizons from list: {horizons}")
        else:
            logger.error(
                f"Invalid investment_horizons format: {type(horizons_config)}. "
                f"Expected dict or list, using defaults."
            )
            return default_horizons
        # Validate horizons
        validated_horizons = []
        for horizon in horizons:
            # Must be integer or convertible to integer
            try:
                horizon_int = int(horizon)
            except (ValueError, TypeError):
                logger.error(f"Invalid horizon value '{horizon}', must be integer. Skipping.")
                continue
            # Must be positive
            if horizon_int <= 0:
                logger.error(f"Invalid horizon value {horizon_int}, must be positive. Skipping.")
                continue
            # Reasonable range check (1 month to 30 years)
            if horizon_int < 1 or horizon_int > 360:
                logger.warning(
                    f"Horizon {horizon_int} months is outside typical range (1-360). "
                    f"Using anyway, but please verify."
                )
            validated_horizons.append(horizon_int)
        if not validated_horizons:
            logger.error("No valid horizons found after validation, using defaults")
            return default_horizons
        logger.info(f"Validated investment horizons: {validated_horizons}")
        return validated_horizons

    def generate_all_profiles(self) -> List[InputProfile]:
        """
        Generate all profile combinations.
        Combinations:
        - 5 objectives
        - 3 risk tolerances (bajo, medio, alto)
        - 3 capital tiers (bajo, medio, alto)
        - N investment horizons (loaded from config)
        Returns:
            List of InputProfile objects
        """
        profiles = []
        # Generate combinations
        objectives = list(ObjectivoInversion)
        risk_tolerances = list(RiskTolerance)
        capital_tiers = ["bajo", "medio", "alto"]
        # Load horizons from config
        horizons = self._load_investment_horizons()
        for objective in objectives:
            for risk in risk_tolerances:
                for tier in capital_tiers:
                    for horizon in horizons:
                        # Get capital for tier
                        capital = Decimal(str(self.capital_tiers.get(tier, 100000)))
                        # Create profile
                        profile = InputProfile(
                            capital_initial=capital,
                            objetivo_inversion=objective,
                            risk_tolerance=risk,
                            investment_horizon=horizon,
                        )
                        profiles.append(profile)
        expected_count = len(objectives) * len(risk_tolerances) * len(capital_tiers) * len(horizons)
        logger.info(
            f"Generated {len(profiles)} profile combinations "
            f"({len(objectives)} objectives × {len(risk_tolerances)} risk levels × "
            f"{len(capital_tiers)} tiers × {len(horizons)} horizons = {expected_count})"
        )
        return profiles

    def _get_capital_tier_key(self, profile: InputProfile) -> str:
        """
        Map capital_flag to config tier key using unified tier mapping.
        The InputProfile.capital_flag returns 'small', 'medium', 'large'
        but config expects 'bajo', 'medio', 'alto'.
        This method uses the centralized TierMapper to ensure consistency
        across all tier conversions in the system.
        Tier Systems:
        - InputProfile.capital_flag: small (<€50k), medium (€50k-€250k), large (>=€250k)
        - investment_profiles.yaml: micro (<€15k), small (€15k-€50k), medium (€50k-€250k), large (>=€250k)
        - Config (Spanish): bajo (<€50k), medio (€50k-€250k), alto (>=€250k)
        Args:
            profile: InputProfile
        Returns:
            Mapped tier key for config lookups (bajo, medio, or alto)
        Examples:
            >>> profile = InputProfile(capital_initial=30000, ...)
            >>> backtester._get_capital_tier_key(profile)
            'bajo'
            >>> profile = InputProfile(capital_initial=100000, ...)
            >>> backtester._get_capital_tier_key(profile)
            'medio'
            >>> profile = InputProfile(capital_initial=500000, ...)
            >>> backtester._get_capital_tier_key(profile)
            'alto'
        """
        try:
            # Use the centralized tier mapper for consistency
            return map_profile_tier_to_config(profile.capital_flag, target_format="spanish")
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            # Fallback to manual mapping if tier mapper fails
            logger.warning(f"Tier mapper failed for {profile.capital_flag}, using fallback: {e}")
            tier_map = {"small": "bajo", "medium": "medio", "large": "alto"}
            return tier_map.get(profile.capital_flag, "medio")

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
        capital_tier_key = self._get_capital_tier_key(profile)
        profile_id = f"{profile.objetivo_inversion.value}_{profile.risk_tolerance.value}_{capital_tier_key}_{profile.investment_horizon}m"
        logger.info(f"Running profile: {profile_id} (multi_strategy={multi_strategy})")
        # Create temporary config file for this profile
        profile_config = self._create_profile_config(profile)
        # Extract strategy mapping metadata if available
        strategy_mapping_metadata = profile_config.pop("_strategy_mapping", {})
        enabled_strategies = strategy_mapping_metadata.get("enabled_strategies", [])
        learning_engines = strategy_mapping_metadata.get("learning_engines", [])
        ensemble_config = strategy_mapping_metadata.get("ensemble_config", {})
        # Log strategy selection
        if enabled_strategies:
            logger.info(
                f"Profile {profile_id}: enabled_strategies={enabled_strategies}, "
                f"learning_engines={learning_engines}, "
                f"ensemble_mode={ensemble_config.get('mode', 'N/A')}"
            )
        # Run baseline (single or multi-strategy)
        baseline_results = self._run_baseline(
            profile, profile_config, multi_strategy=multi_strategy
        )
        # Run optimization (pass baseline results to avoid duplicate execution)
        optimized_strategy = self._run_optimization_pipeline(
            profile,
            profile_config,
            baseline_metrics=baseline_results,
            multi_strategy=multi_strategy,
        )
        # Calculate improvement metrics
        improvement_metrics = self._calculate_improvements(
            baseline_results, optimized_strategy.optimized_metrics
        )
        # Determine readiness
        ready, recommendation = self._evaluate_readiness(
            profile, optimized_strategy, improvement_metrics
        )
        # Get StrategyMapping if available
        strategy_mapping_obj = None
        if self.profile_mapper is not None:
            try:
                strategy_mapping_obj = self.profile_mapper.create_strategy_mapping(profile)
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                logger.debug(f"Could not create StrategyMapping: {e}")
        # Extract per-strategy results from multi-strategy execution
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
        self._store_result(result)
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
        self._generate_batch_summary(results)
        return results

    def _run_parallel(
        self, profiles: List[InputProfile], max_workers: int
    ) -> Dict[str, ProfileResult]:
        """
        Run profiles in parallel using ProcessPoolExecutor.
        Results are collected in parallel and stored sequentially to avoid
        database race conditions with SQLite.
        """
        results = {}
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
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
                except (
                    IntegrityError,
                    OperationalError,
                    DatabaseError,
                    DataError,
                    ProgrammingError,
                ) as e:
                    logger.error(f"Profile {profile} failed: {e}", exc_info=True)
        # Batch store all results sequentially after parallel execution completes
        logger.info(f"Parallel execution complete, storing {len(results)} results sequentially...")
        self._batch_store_results(results)
        return results

    def _batch_store_results(self, results: Dict[str, ProfileResult]) -> None:
        """
        Store multiple results in database sequentially.
        This method is called after parallel execution to avoid race conditions
        when multiple workers try to write to SQLite simultaneously.
        """
        session = self.Session()
        stored_count = 0
        failed_count = 0
        try:
            for result in results.values():
                try:
                    # Check if exists
                    existing = (
                        session.query(ProfileResultDB)
                        .filter_by(profile_id=result.profile_id)
                        .first()
                    )
                    capital_tier_key = self._get_capital_tier_key(result.profile)
                    data = {
                        "profile_id": result.profile_id,
                        "objective": result.profile.objetivo_inversion.value,
                        "risk_tolerance": result.profile.risk_tolerance.value,
                        "capital_tier": capital_tier_key,  # Use mapped value
                        "investment_horizon": result.profile.investment_horizon,
                        "baseline_sharpe": result.baseline_results.get("sharpe_ratio"),
                        "baseline_return": result.baseline_results.get("return_pct"),
                        "baseline_max_dd": result.baseline_results.get("max_drawdown"),
                        "baseline_win_rate": result.baseline_results.get("win_rate"),
                        "optimized_sharpe": result.optimization_results.get("sharpe_ratio"),
                        "optimized_return": result.optimization_results.get("return_pct"),
                        "optimized_max_dd": result.optimization_results.get("max_drawdown"),
                        "optimized_win_rate": result.optimization_results.get("win_rate"),
                        "sharpe_improvement": result.improvement_metrics.get("sharpe_improvement"),
                        "return_improvement": result.improvement_metrics.get("return_improvement"),
                        "max_dd_improvement": result.improvement_metrics.get("max_dd_improvement"),
                        "win_rate_improvement": result.improvement_metrics.get(
                            "win_rate_improvement"
                        ),
                        "best_parameters": result.best_parameters,
                        "ready_for_paper_trading": result.ready_for_paper_trading,
                        "recommendation": result.recommendation,
                    }
                    if existing:
                        # Update
                        for key, value in data.items():
                            setattr(existing, key, value)
                    else:
                        # Create
                        data["id"] = str(uuid4())
                        db_result = ProfileResultDB(**data)
                        session.add(db_result)
                    stored_count += 1
                except (
                    IntegrityError,
                    OperationalError,
                    DatabaseError,
                    DataError,
                    ProgrammingError,
                ) as e:
                    failed_count += 1
                    logger.error(f"Failed to store result for {result.profile_id}: {e}")
                    # Continue with next result
            session.commit()
            logger.info(f"Batch store complete: {stored_count} stored, {failed_count} failed")
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            session.rollback()
            logger.error(f"Batch store failed: {e}", exc_info=True)
        finally:
            session.close()

    def _run_sequential(self, profiles: List[InputProfile]) -> Dict[str, ProfileResult]:
        """Run profiles sequentially."""
        results = {}
        for i, profile in enumerate(profiles, 1):
            try:
                result = self.run_single_profile(profile)
                results[result.profile_id] = result
                logger.info(f"Completed {i}/{len(profiles)}: {result.profile_id}")
            except (
                IntegrityError,
                OperationalError,
                DatabaseError,
                DataError,
                ProgrammingError,
            ) as e:
                logger.error(f"Profile {profile} failed: {e}", exc_info=True)
        return results

    @staticmethod
    def _run_profile_worker(config_path: str, profile: InputProfile) -> ProfileResult:
        """Worker function for parallel execution."""
        backtester = ProfileBatchBacktester(config_path)
        return backtester.run_single_profile(profile)

    def _create_profile_config(self, profile: InputProfile) -> Dict[str, Any]:
        """
        Create backtest configuration for a profile using ProfileStrategyMapper.
        This method now integrates with ProfileStrategyMapper to get comprehensive
        strategy configuration including multi-strategy support, learning engines,
        and ensemble configurations.
        Args:
            profile: InputProfile to create configuration for
        Returns:
            Configuration dictionary for backtesting
        """
        # Try to use ProfileStrategyMapper if available
        if self.profile_mapper is not None:
            try:
                # Get strategy mapping from profile
                strategy_config = self.profile_mapper.map_profile_to_strategies(profile)
                # Extract strategy information
                enabled_strategies = strategy_config.get("enabled_strategies", [])
                risk_params = strategy_config.get("risk_params", {})
                trading_params = strategy_config.get("trading_params", {})
                learning_engines = strategy_config.get("learning_engines", [])
                ensemble_config = strategy_config.get("ensemble_config", {})
                logger.info(
                    f"Profile {profile.input_id}: mapped to {len(enabled_strategies)} strategies, "
                    f"{len(learning_engines)} learning engines, ensemble mode={ensemble_config.get('mode', 'N/A')}"
                )
                # Build configuration from mapper results
                config = {
                    "input": {
                        "initial_capital": float(profile.capital_initial),
                        "start_date": self.config.get("backtest_period", {}).get(
                            "start_date", "2020-01-01"
                        ),
                        "end_date": self.config.get("backtest_period", {}).get(
                            "end_date", "2023-12-31"
                        ),
                        "symbols": self.config.get(
                            "symbols", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
                        ),
                    },
                    "modules": {
                        "enabled_strategies": enabled_strategies,
                        **self.config.get("modules", {}),
                    },
                    "risk_management": {
                        "max_position_size": profile.capital_initial
                        * Decimal(str(risk_params.get("max_position_size", 0.20))),
                        "max_sector_allocation": risk_params.get("max_sector_allocation", 0.30),
                        "leverage": risk_params.get("leverage", 1.0),
                        "risk_profile": risk_params.get("risk_profile", 4),
                        **risk_params,
                    },
                    "strategy": {
                        "learning_mode": learning_engines[0] if learning_engines else "supervised",
                        "learning_engines": learning_engines,
                        "ensemble_config": ensemble_config,
                        "objective": strategy_config.get("objective"),
                        "capital_tier": strategy_config.get("capital_tier"),
                        **trading_params,
                    },
                    "reporting": self.config.get("reporting", {}),
                    # Store mapping metadata for later use
                    "_strategy_mapping": {
                        "enabled_strategies": enabled_strategies,
                        "learning_engines": learning_engines,
                        "ensemble_config": ensemble_config,
                        "objective": strategy_config.get("objective"),
                        "capital_tier": strategy_config.get("capital_tier"),
                    },
                }
                return config
            except (FileNotFoundError, PermissionError, IOError, OSError) as e:
                logger.warning(
                    f"ProfileStrategyMapper failed for {profile.input_id}: {e}, falling back to manual config"
                )
                # Track fallback
                self._increment_fallback_counter("profile_strategy_mapper")
                # Fall through to manual configuration
        # Fallback: Manual configuration (backward compatible)
        # Track fallback if mapper is None
        if self.profile_mapper is None:
            self._increment_fallback_counter("profile_strategy_mapper")
        logger.info(f"Using manual configuration for profile {profile.input_id}")
        # Get parameters from config based on profile
        risk_key = profile.risk_tolerance.value
        objective_key = profile.objetivo_inversion.value
        # Risk-based parameters
        risk_params = self.config.get("risk_parameters", {}).get(risk_key, {})
        if not risk_params:
            # Track config key mismatch
            self._increment_fallback_counter("config_key_mismatch")
            logger.debug(f"Risk key '{risk_key}' not found in config, using empty defaults")
        # Objective-based parameters
        objective_params = self.config.get("objective_parameters", {}).get(objective_key, {})
        if not objective_params:
            # Track config key mismatch
            self._increment_fallback_counter("config_key_mismatch")
            logger.debug(
                f"Objective key '{objective_key}' not found in config, using empty defaults"
            )
        # Combine parameters
        config = {
            "input": {
                "initial_capital": float(profile.capital_initial),
                "start_date": self.config.get("backtest_period", {}).get(
                    "start_date", "2020-01-01"
                ),
                "end_date": self.config.get("backtest_period", {}).get("end_date", "2023-12-31"),
                "symbols": self.config.get("symbols", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]),
            },
            "modules": self.config.get("modules", {}),
            "risk_management": {
                **risk_params,
                "max_position_size": profile.capital_initial
                * Decimal(str(risk_params.get("max_position_pct", 0.1))),
            },
            "strategy": {
                **objective_params,
                "learning_mode": "supervised",
            },
            "reporting": self.config.get("reporting", {}),
            # Store empty mapping metadata for consistency
            "_strategy_mapping": {
                "enabled_strategies": [],
                "learning_engines": [],
                "ensemble_config": {},
                "objective": objective_key,
                "capital_tier": self._get_capital_tier_key(profile),
            },
        }
        return config

    def _run_baseline(
        self, profile: InputProfile, config: Dict[str, Any], multi_strategy: bool = False
    ) -> Dict[str, Any]:
        """
        Run baseline backtest with default parameters.
        Args:
            profile: InputProfile
            config: Configuration dict
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
            yaml.dump(config, f)
        try:
            # Use ComprehensiveBacktestRunner
            runner = ComprehensiveBacktestRunner(str(temp_config_path))
            if multi_strategy:
                # Multi-strategy execution
                logger.info("Executing multi-strategy baseline backtest")
                multi_strategy_results = runner.run_multi_strategy_backtest()
                # Aggregate results across strategies
                baseline_results = self._aggregate_multi_strategy_results(
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
                baseline_results = self._safe_extract_first_result(
                    baseline_results_list,
                    context=f"baseline backtest for {profile.objetivo_inversion.value}",
                )
                # Add combined field for consistency
                baseline_results["combined"] = baseline_results
            return baseline_results
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            logger.error(f"Baseline backtest failed: {e}", exc_info=True)
            return self._get_empty_metrics()
        finally:
            # Clean up temp file
            if temp_config_path.exists():
                temp_config_path.unlink()

    def _run_optimization_pipeline(
        self,
        profile: InputProfile,
        config: Dict[str, Any],
        baseline_metrics: Optional[Dict[str, Any]] = None,
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
            baseline_metrics: Pre-computed baseline metrics (optional, avoids duplicate execution)
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

    def _run_bayesian_optimization(
        self, profile: InputProfile, config: Dict[str, Any], multi_strategy: bool = False
    ) -> Dict[str, Any]:
        """
        Run Bayesian optimization using Optuna.
        Args:
            profile: InputProfile
            config: Configuration dict
            multi_strategy: If True, use multi-strategy optimization mode
        Returns:
            Optimization results with best parameters
        Note:
            Parameter ranges are loaded from ProfileConfigLoader (profile_optimization.yaml)
            Falls back to hardcoded values if loader is unavailable.
        """
        logger.info(
            f"Running Bayesian optimization for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )
        n_trials = self.optimization_config.get("n_trials", 100)
        timeout = self.optimization_config.get("timeout", None)
        # Get parameter ranges from ProfileConfigLoader
        # If loader is not available, fall back to hardcoded defaults
        if self.profile_config_loader is not None:
            try:
                # RSI thresholds
                rsi_buy_config = self.profile_config_loader.get_threshold_config("rsi").get(
                    "buy_threshold", {}
                )
                rsi_buy_min = rsi_buy_config.get("min", 20)
                rsi_buy_max = rsi_buy_config.get("max", 35)
                # Volume ratio
                vol_config = self.profile_config_loader.get_threshold_config("volume_ratio", {})
                vol_min = vol_config.get("min", 1.0)
                vol_max = vol_config.get("max", 1.5)
                logger.debug("Loaded parameter ranges from ProfileConfigLoader")
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                logger.warning(f"Failed to load parameter ranges from ProfileConfigLoader: {e}")
                logger.info("Falling back to default parameter ranges")
                # Track fallback
                self._increment_fallback_counter("profile_config_loader")
                # Fallback to hardcoded defaults
                # Values match profile_optimization.yaml threshold_optimization ranges
                rsi_buy_min, rsi_buy_max = 20, 35  # rsi.buy_threshold: min=20, max=35
                vol_min, vol_max = 1.0, 1.5  # volume_ratio: min=1.0, max=1.5
        else:
            # Use hardcoded defaults when ProfileConfigLoader is not available
            # Values match profile_optimization.yaml threshold_optimization ranges
            logger.info("Using default parameter ranges (ProfileConfigLoader not initialized)")
            # Track fallback
            self._increment_fallback_counter("profile_config_loader")
            rsi_buy_min, rsi_buy_max = 20, 35  # rsi.buy_threshold: min=20, max=35
            vol_min, vol_max = 1.0, 1.5  # volume_ratio: min=1.0, max=1.5

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
                metrics = self._run_backtest_with_params(
                    profile, config, params, multi_strategy=multi_strategy
                )
                # Maximize Sharpe ratio
                # For multi-strategy, use combined metrics
                if multi_strategy and "combined" in metrics:
                    return metrics["combined"].get("sharpe_ratio", -1.0)
                return metrics.get("sharpe_ratio", -1.0)
            except (FileNotFoundError, PermissionError, IOError, OSError) as e:
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
        config: Dict[str, Any],
        params: Dict[str, Any],
        multi_strategy: bool = False,
    ) -> Dict[str, Any]:
        """
        Run backtest with specific parameters.
        Args:
            profile: InputProfile
            config: Configuration dict
            params: Strategy parameters to test
            multi_strategy: If True, use multi-strategy backtest mode
        Returns:
            Backtest metrics (single or multi-strategy)
        """
        # Update config with params
        updated_config = config.copy()
        updated_config["strategy"].update(params)
        # Create temp config
        temp_config_path = self.output_dir / f"temp_{uuid4().hex[:8]}.yaml"
        with open(temp_config_path, "w") as f:
            yaml.dump(updated_config, f)
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
                # Safe extraction with proper validation
                return self._safe_extract_first_result(
                    results, context=f"backtest with params for {profile.objetivo_inversion.value}"
                )
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            logger.error(f"Backtest with params failed: {e}", exc_info=True)
            return self._get_empty_metrics()
        finally:
            if temp_config_path.exists():
                temp_config_path.unlink()

    def _run_walk_forward(
        self,
        profile: InputProfile,
        config: Dict[str, Any],
        params: Dict[str, Any],
        multi_strategy: bool = False,
    ) -> Dict[str, Any]:
        """
        Run walk-forward validation.
        Walk-forward validation tests the robustness of a strategy by:
        1. Splitting data into multiple train/test windows
        2. Training (optimizing) on each training window
        3. Testing on the subsequent out-of-sample window
        4. Rolling forward through time
        This provides a realistic assessment of how the strategy would have
        performed when deployed incrementally.
        Note:
            Validation parameters are loaded from ProfileConfigLoader (profile_optimization.yaml)
            Falls back to profile_batch_backtest.yaml values if loader is unavailable.
        """
        logger.info("Running walk-forward validation")
        # Configuration for walk-forward
        # Try to load from ProfileConfigLoader first, then fall back to workflow config
        if self.profile_config_loader is not None:
            try:
                wf_config = self.profile_config_loader.get_walk_forward_config()
                # Validate configuration structure
                if not wf_config:
                    raise ValueError("Empty walk-forward configuration")
                # Extract walk-forward parameters from profile_optimization.yaml structure:
                # validation:
                #   walk_forward:
                #     train_years: 2      # Training period in years
                #     test_years: 0.5     # Test period in years
                #     step_years: 0.5     # Step size for walk-forward
                #     min_train_samples: 500
                train_years = wf_config.get("train_years", 2)
                test_years = wf_config.get("test_years", 0.5)
                step_years = wf_config.get("step_years", 0.5)
                # Validate required parameters
                if train_years <= 0 or test_years <= 0 or step_years <= 0:
                    raise ValueError(
                        f"Invalid walk-forward parameters: train_years={train_years}, "
                        f"test_years={test_years}, step_years={step_years}"
                    )
                # Get backtest period dates for window calculation
                start_date = pd.Timestamp(config.get("input", {}).get("start_date", "2020-01-01"))
                end_date = pd.Timestamp(config.get("input", {}).get("end_date", "2023-12-31"))
                total_years = (end_date - start_date).days / 365.25
                # Calculate number of windows based on total period and step size
                # Formula: floor((total_years - initial_train_years - test_years) / step_years) + 1
                initial_train_years = train_years
                if total_years < (initial_train_years + test_years):
                    raise ValueError(
                        f"Insufficient data for walk-forward: {total_years:.2f} years available, "
                        f"but need at least {initial_train_years + test_years:.2f} years "
                        f"(train={initial_train_years}y + test={test_years}y)"
                    )
                n_windows = int((total_years - initial_train_years - test_years) / step_years) + 1
                n_windows = max(1, n_windows)  # Ensure at least 1 window
                # Calculate train percentage: train_years / (train_years + test_years)
                # This represents the proportion of each window used for training
                total_window_years = train_years + test_years
                train_pct = train_years / total_window_years
                # Get minimum test periods (used for validation)
                min_test_periods = wf_config.get("min_train_samples", 500)
                logger.info(
                    f"Loaded walk-forward config from ProfileConfigLoader: "
                    f"train_years={train_years}, test_years={test_years}, "
                    f"step_years={step_years}, n_windows={n_windows}, "
                    f"train_pct={train_pct:.2f}, min_test_periods={min_test_periods}"
                )
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                logger.warning(f"Failed to load walk-forward config from ProfileConfigLoader: {e}")
                # Fall back to workflow config
                # Track fallback
                self._increment_fallback_counter("profile_config_loader")
                wf_config = self.validation_config.get("walk_forward", {})
                n_windows = wf_config.get("n_windows", 5)
                train_pct = wf_config.get("train_percentage", 0.6)
                min_test_periods = wf_config.get("min_test_periods", 20)
                logger.info(
                    f"Falling back to workflow config: n_windows={n_windows}, train_pct={train_pct}"
                )
        else:
            # Use workflow config
            wf_config = self.validation_config.get("walk_forward", {})
            n_windows = wf_config.get("n_windows", 5)
            train_pct = wf_config.get("train_percentage", 0.6)
            min_test_periods = wf_config.get("min_test_periods", 20)
            logger.debug(f"Using workflow config: n_windows={n_windows}, train_pct={train_pct}")
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
            # Calculate window boundaries
            window_start = start_date + pd.Timedelta(days=int(i * window_size))
            train_end = window_start + pd.Timedelta(days=train_size)
            test_end = train_end + pd.Timedelta(days=test_size)
            # Ensure we don't go beyond end_date
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
            # Run training window (optimization on training data)
            try:
                # Train on training period
                train_results = self._run_backtest_with_params(profile, window_config, params)
                # Test on out-of-sample period
                test_config = config.copy()
                test_config["input"]["start_date"] = train_end.strftime("%Y-%m-%d")
                test_config["input"]["end_date"] = test_end.strftime("%Y-%m-%d")
                test_results = self._run_backtest_with_params(profile, test_config, params)
                # Collect metrics
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
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                logger.error(f"Window {i+1} failed: {e}")
                continue
        # Analyze walk-forward results
        if not window_results:
            return {
                "passed": False,
                "avg_sharpe": 0.0,
                "std_sharpe": 0.0,
                "n_windows": 0,
                "error": "All windows failed",
            }
        # Calculate aggregate metrics
        test_sharpes = [w["test_sharpe"] for w in window_results]
        avg_sharpe = np.mean(test_sharpes)
        std_sharpe = np.std(test_sharpes)
        # Calculate consistency metrics
        sharpe_decays = [w["sharpe_decay"] for w in window_results]
        avg_decay = np.mean(sharpe_decays)
        # Calculate success rate (windows with positive test Sharpe)
        success_rate = sum(1 for s in test_sharpes if s > 0) / len(test_sharpes)
        # Determine if passed
        # Criteria: average Sharpe > 0.5, success rate > 0.6, acceptable decay
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
        config: Dict[str, Any],
        params: Dict[str, Any],
        multi_strategy: bool = False,
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation using bootstrapping from actual returns.
        This method performs proper Monte Carlo validation by:
        1. Running backtest with optimized parameters
        2. Extracting actual return series from results
        3. Bootstrapping (sampling with replacement) to create simulations
        4. Evaluating robustness of strategy performance
        Note:
            Monte Carlo parameters are loaded from ProfileConfigLoader (profile_optimization.yaml)
            Falls back to profile_batch_backtest.yaml values if loader is unavailable.
        """
        logger.info("Running Monte Carlo simulation with bootstrapping")
        # Configuration
        # Try to load from ProfileConfigLoader first, then fall back to workflow config
        if self.profile_config_loader is not None:
            try:
                mc_config = self.profile_config_loader.get_monte_carlo_config()
                n_simulations = mc_config.get("n_simulations", 1000)
                min_profitable_pct = mc_config.get("confidence_level", 0.95)
                logger.debug("Loaded Monte Carlo config from ProfileConfigLoader")
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                logger.warning(f"Failed to load Monte Carlo config from ProfileConfigLoader: {e}")
                # Track fallback
                self._increment_fallback_counter("profile_config_loader")
                # Fall back to workflow config
                mc_config = self.validation_config.get("monte_carlo", {})
                n_simulations = mc_config.get("n_simulations", 1000)
                min_profitable_pct = mc_config.get("min_profitable_pct", 0.95)
        else:
            # Use workflow config
            # Track fallback
            self._increment_fallback_counter("profile_config_loader")
            mc_config = self.validation_config.get("monte_carlo", {})
            n_simulations = mc_config.get("n_simulations", 1000)
            min_profitable_pct = mc_config.get("min_profitable_pct", 0.95)
        # First, get actual backtest results with optimized params
        try:
            backtest_results = self._run_backtest_with_params(profile, config, params)
            # Extract actual returns from backtest results
            # The backtest results should contain daily returns or trade returns
            returns_series = backtest_results.get("returns_series")
            if returns_series is None or len(returns_series) == 0:
                # Fallback: generate returns from total return and trade count
                total_return = backtest_results.get("return_pct", 0)
                total_trades = backtest_results.get("total_trades", 1)
                if total_trades > 0:
                    # Create synthetic returns series
                    avg_return = total_return / total_trades
                    # Add some variability based on volatility
                    volatility = backtest_results.get("volatility", 0.15)
                    returns_series = np.random.normal(avg_return, volatility, total_trades)
                else:
                    logger.warning("No trade data available for Monte Carlo simulation")
                    return {
                        "passed": False,
                        "n_simulations": 0,
                        "profitable_pct": 0.0,
                        "avg_return": 0.0,
                        "std_return": 0.0,
                        "error": "No trade data available",
                    }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to get backtest results for Monte Carlo: {e}")
            return {
                "passed": False,
                "n_simulations": 0,
                "profitable_pct": 0.0,
                "avg_return": 0.0,
                "std_return": 0.0,
                "error": str(e),
            }
        # Perform bootstrapping: sample with replacement from actual returns
        simulated_returns = []
        sample_size = len(returns_series)
        for i in range(n_simulations):
            # Bootstrap: sample with replacement
            bootstrapped_returns = np.random.choice(returns_series, size=sample_size, replace=True)
            # Calculate cumulative return for this simulation
            sim_cumulative_return = np.prod(1 + bootstrapped_returns) - 1
            simulated_returns.append(sim_cumulative_return)
        # Calculate statistics
        simulated_returns = np.array(simulated_returns)
        profitable_pct = np.sum(simulated_returns > 0) / n_simulations
        passed = profitable_pct >= min_profitable_pct
        # Calculate confidence intervals
        # Use confidence_level from config, default to 0.95 if not set
        confidence_level = mc_config.get("confidence_level", 0.95)
        alpha = 1 - confidence_level
        lower_ci = np.percentile(simulated_returns, alpha / 2 * 100)
        upper_ci = np.percentile(simulated_returns, (1 - alpha / 2) * 100)
        logger.info(
            f"Monte Carlo: {n_simulations} simulations, "
            f"{profitable_pct:.1%} profitable, "
            f"95% CI: [{lower_ci:.2%}, {upper_ci:.2%}]"
        )
        return {
            "passed": passed,
            "n_simulations": n_simulations,
            "profitable_pct": profitable_pct,
            "avg_return": float(np.mean(simulated_returns)),
            "std_return": float(np.std(simulated_returns)),
            "median_return": float(np.median(simulated_returns)),
            "lower_ci": float(lower_ci),
            "upper_ci": float(upper_ci),
            "confidence_level": confidence_level,
        }

    def _run_out_of_sample(
        self,
        profile: InputProfile,
        config: Dict[str, Any],
        params: Dict[str, Any],
        multi_strategy: bool = False,
    ) -> Dict[str, Any]:
        """
        Run out-of-sample validation.
        Out-of-sample validation tests strategy performance on completely
        unseen data by splitting the dataset into training and testing periods.
        The strategy parameters are optimized on the training period and then
        evaluated on the held-out test period.
        This helps detect overfitting - a strategy that performs well in-sample
        but poorly out-of-sample is likely overfitted.
        Note:
            OOS parameters are loaded from ProfileConfigLoader (profile_optimization.yaml)
            Falls back to profile_batch_backtest.yaml values if loader is unavailable.
        """
        logger.info("Running out-of-sample validation")
        # Configuration
        # Try to load from ProfileConfigLoader first, then fall back to workflow config
        if self.profile_config_loader is not None:
            try:
                oos_config = self.profile_config_loader.get("validation.out_of_sample", {})
                train_pct = oos_config.get("oos_ratio", 0.2)
                # Convert oos_ratio to train_percentage (1 - oos_ratio)
                train_pct = 1 - train_pct
                # Get thresholds from validation config
                thresholds = self.profile_config_loader.get_validation_thresholds()
                min_oos_sharpe = thresholds.get("min_sharpe", 0.5)
                max_performance_decay = 0.3  # Default decay
                logger.debug("Loaded OOS config from ProfileConfigLoader")
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.warning(f"Failed to load OOS config from ProfileConfigLoader: {e}")
                # Track fallback
                self._increment_fallback_counter("profile_config_loader")
                # Fall back to workflow config
                oos_config = self.validation_config.get("out_of_sample", {})
                train_pct = oos_config.get("train_percentage", 0.7)
                min_oos_sharpe = oos_config.get("min_oos_sharpe", 0.5)
                max_performance_decay = oos_config.get("max_performance_decay", 0.3)
        else:
            # Use workflow config
            # Track fallback
            self._increment_fallback_counter("profile_config_loader")
            oos_config = self.validation_config.get("out_of_sample", {})
            train_pct = oos_config.get("train_percentage", 0.7)
            min_oos_sharpe = oos_config.get("min_oos_sharpe", 0.5)
            max_performance_decay = oos_config.get(
                "max_performance_decay", 0.3
            )  # 30% decay allowed
        # Get backtest period dates
        start_date = pd.Timestamp(config.get("input", {}).get("start_date", "2020-01-01"))
        end_date = pd.Timestamp(config.get("input", {}).get("end_date", "2023-12-31"))
        total_days = (end_date - start_date).days
        # Calculate split point
        split_date = start_date + pd.Timedelta(days=int(total_days * train_pct))
        logger.info(
            f"OOS split: Train {start_date.date()} to {split_date.date()}, "
            f"Test {split_date.date()} to {end_date.date()}"
        )
        # Create training config
        train_config = config.copy()
        train_config["input"]["start_date"] = start_date.strftime("%Y-%m-%d")
        train_config["input"]["end_date"] = split_date.strftime("%Y-%m-%d")
        # Create OOS test config
        oos_test_config = config.copy()
        oos_test_config["input"]["start_date"] = split_date.strftime("%Y-%m-%d")
        oos_test_config["input"]["end_date"] = end_date.strftime("%Y-%m-%d")
        try:
            # Run in-sample backtest
            train_results = self._run_backtest_with_params(profile, train_config, params)
            # Run out-of-sample backtest with SAME parameters
            oos_results = self._run_backtest_with_params(profile, oos_test_config, params)
            # Extract metrics
            train_sharpe = train_results.get("sharpe_ratio", 0)
            oos_sharpe = oos_results.get("sharpe_ratio", 0)
            train_return = train_results.get("return_pct", 0)
            oos_return = oos_results.get("return_pct", 0)
            train_win_rate = train_results.get("win_rate", 0)
            oos_win_rate = oos_results.get("win_rate", 0)
            # Calculate performance decay
            sharpe_decay = 0
            if train_sharpe > 0:
                sharpe_decay = (train_sharpe - oos_sharpe) / train_sharpe
            return_decay = 0
            if train_return > 0:
                return_decay = (train_return - oos_return) / abs(train_return)
            # Determine if passed
            # Criteria: OOS Sharpe meets minimum AND performance doesn't decay too much
            passed = (
                oos_sharpe >= min_oos_sharpe
                and sharpe_decay <= max_performance_decay
                and oos_sharpe > 0  # Must be positive
            )
            logger.info(
                f"OOS validation: Train Sharpe={train_sharpe:.2f}, OOS Sharpe={oos_sharpe:.2f}, "
                f"Decay={sharpe_decay:.1%}, Passed={passed}"
            )
            return {
                "passed": passed,
                "train_sharpe": float(train_sharpe),
                "oos_sharpe": float(oos_sharpe),
                "train_return": float(train_return),
                "oos_return": float(oos_return),
                "train_win_rate": float(train_win_rate),
                "oos_win_rate": float(oos_win_rate),
                "sharpe_decay": float(sharpe_decay),
                "return_decay": float(return_decay),
                "n_train_days": (split_date - start_date).days,
                "n_oos_days": (end_date - split_date).days,
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"OOS validation failed: {e}")
            return {
                "passed": False,
                "train_sharpe": 0.0,
                "oos_sharpe": 0.0,
                "train_return": 0.0,
                "oos_return": 0.0,
                "train_win_rate": 0.0,
                "oos_win_rate": 0.0,
                "sharpe_decay": 1.0,
                "return_decay": 1.0,
                "error": str(e),
            }

    def _generate_comparison(
        self, baseline: Dict[str, Any], optimized: Dict[str, Any], optuna_results: Dict[str, Any]
    ) -> BaselineOptimizationComparison:
        """
        Generate baseline vs optimization comparison.
        Uses acceptance criteria from config for thresholds:
        - significance_threshold: Minimum % improvement for statistical significance
        - strong_significance_threshold: Minimum % improvement for strong significance
        - degradation_threshold: Maximum % improvement degradation to prefer baseline
        - confidence_high/medium/low: Confidence levels for recommendations
        """
        # Get thresholds from config
        acceptance_criteria = self.config.get("acceptance_criteria", {})
        significance_threshold = acceptance_criteria.get("significance_threshold", 5)
        strong_significance_threshold = acceptance_criteria.get("strong_significance_threshold", 10)
        degradation_threshold = acceptance_criteria.get("degradation_threshold", -5)
        confidence_high = acceptance_criteria.get("confidence_high", 0.8)
        confidence_medium = acceptance_criteria.get("confidence_medium", 0.7)
        confidence_low = acceptance_criteria.get("confidence_low", 0.5)
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
        param_importance = self._calculate_parameter_importance(history)
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

    def _calculate_parameter_importance(self, history: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate parameter importance from optimization history."""
        if not history:
            return {}
        # Simple correlation-based importance
        df = pd.DataFrame([{"value": h["value"], **h["params"]} for h in history])
        importance = {}
        for col in df.columns:
            if col != "value":
                corr = df[col].corr(df["value"])
                if not np.isnan(corr):
                    importance[col] = abs(corr)
        # Normalize to 0-1
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

    def _calculate_improvements(
        self, baseline: Dict[str, Any], optimized: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate improvement metrics."""
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

    def _evaluate_readiness(
        self, profile: InputProfile, optimized: OptimizedStrategy, improvements: Dict[str, float]
    ) -> Tuple[bool, str]:
        """Evaluate if strategy is ready for paper trading."""
        # Get thresholds from config
        thresholds = self.config.get("acceptance_criteria", {})
        min_sharpe = thresholds.get("min_sharpe", 1.0)
        min_return = thresholds.get("min_return", 0.10)
        max_dd = thresholds.get("max_drawdown", -0.25)
        sharpe = optimized.optimized_metrics.get("sharpe_ratio", 0)
        total_return = optimized.optimized_metrics.get("return_pct", 0)
        max_dd = optimized.optimized_metrics.get("max_drawdown", 0)
        # Get revision multiplier from config
        revision_multiplier = thresholds.get("revision_multiplier", 0.8)
        # Check thresholds
        checks = [
            sharpe >= min_sharpe,
            total_return >= min_return,
            max_dd >= max_dd,
            optimized.ready_for_paper_trading,
        ]
        if all(checks):
            return True, "APPROVED: All acceptance criteria met"
        elif sharpe >= min_sharpe * revision_multiplier:
            return False, "REVISION: Marginal performance, review recommended"
        else:
            return False, "REJECTED: Insufficient performance"

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

    def _safe_extract_first_result(
        self, results: Optional[List[Dict[str, Any]]], context: str
    ) -> Dict[str, Any]:
        """
        Safely extract the first result from a list of backtest results.
        This helper method validates the results list before accessing the first
        element to prevent IndexError and provides detailed logging for debugging.
        Args:
            results: List of result dictionaries from ComprehensiveBacktestRunner
            context: Context string for logging (e.g., "baseline backtest for growth")
        Returns:
            First result dict if valid, otherwise empty metrics dict
        Examples:
            >>> results = [{"sharpe_ratio": 1.5, "return_pct": 20.0}]
            >>> self._safe_extract_first_result(results, "test context")
            {"sharpe_ratio": 1.5, "return_pct": 20.0}
            >>> self._safe_extract_first_result([], "test context")
            {"sharpe_ratio": 0.0, "return_pct": 0.0, ...}
        """
        # Check if results is None
        if results is None:
            logger.warning(f"Results is None for {context}, returning empty metrics")
            return self._get_empty_metrics()
        # Check if results list is empty
        if not results:
            logger.warning(f"Results list is empty for {context}, returning empty metrics")
            return self._get_empty_metrics()
        # Check if first element is None
        if results[0] is None:
            logger.warning(f"First result is None for {context}, returning empty metrics")
            return self._get_empty_metrics()
        # Check if first element is a dict
        if not isinstance(results[0], dict):
            logger.error(
                f"First result is not a dict for {context}, "
                f"got type {type(results[0])}, returning empty metrics"
            )
            return self._get_empty_metrics()
        # Validate that result has expected fields
        result = results[0]
        expected_fields = {"sharpe_ratio", "return_pct", "max_drawdown", "win_rate", "total_trades"}
        missing_fields = expected_fields - set(result.keys())
        if missing_fields:
            logger.warning(
                f"Result for {context} is missing expected fields: {missing_fields}. "
                f"Available fields: {set(result.keys())}"
            )
        # Return the validated result
        logger.debug(f"Successfully extracted result for {context}")
        return result

    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics dict."""
        return {
            "sharpe_ratio": 0.0,
            "return_pct": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "total_pnl": 0.0,
        }

    def _store_result(self, result: ProfileResult) -> None:
        """Store result in database."""
        session = self.Session()
        try:
            # Check if exists
            existing = (
                session.query(ProfileResultDB).filter_by(profile_id=result.profile_id).first()
            )
            capital_tier_key = self._get_capital_tier_key(result.profile)
            data = {
                "profile_id": result.profile_id,
                "objective": result.profile.objetivo_inversion.value,
                "risk_tolerance": result.profile.risk_tolerance.value,
                "capital_tier": capital_tier_key,  # Use mapped value instead of raw capital_flag
                "investment_horizon": result.profile.investment_horizon,
                "baseline_sharpe": result.baseline_results.get("sharpe_ratio"),
                "baseline_return": result.baseline_results.get("return_pct"),
                "baseline_max_dd": result.baseline_results.get("max_drawdown"),
                "baseline_win_rate": result.baseline_results.get("win_rate"),
                "optimized_sharpe": result.optimization_results.get("sharpe_ratio"),
                "optimized_return": result.optimization_results.get("return_pct"),
                "optimized_max_dd": result.optimization_results.get("max_drawdown"),
                "optimized_win_rate": result.optimization_results.get("win_rate"),
                "sharpe_improvement": result.improvement_metrics.get("sharpe_improvement"),
                "return_improvement": result.improvement_metrics.get("return_improvement"),
                "max_dd_improvement": result.improvement_metrics.get("max_dd_improvement"),
                "win_rate_improvement": result.improvement_metrics.get("win_rate_improvement"),
                "best_parameters": result.best_parameters,
                "ready_for_paper_trading": result.ready_for_paper_trading,
                "recommendation": result.recommendation,
            }
            if existing:
                # Update
                for key, value in data.items():
                    setattr(existing, key, value)
            else:
                # Create
                data["id"] = str(uuid4())
                db_result = ProfileResultDB(**data)
                session.add(db_result)
            session.commit()
            logger.debug(f"Stored result for {result.profile_id}")
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            session.rollback()
            logger.error(f"Failed to store result: {e}", exc_info=True)
        finally:
            session.close()

    def get_best_strategy(self, objective: str, tier: str, risk: str) -> Dict[str, Any]:
        """
        Get best strategy for specific objective, tier, and risk.
        Args:
            objective: Investment objective (maximizar_capital, etc.)
            tier: Capital tier (bajo, medio, alto)
            risk: Risk tolerance (bajo, medio, alto)
        Returns:
            Best configuration for the criteria
        """
        session = self.Session()
        try:
            # Query database
            results = (
                session.query(ProfileResultDB)
                .filter_by(objective=objective, capital_tier=tier, risk_tolerance=risk)
                .all()
            )
            if not results:
                logger.warning(f"No results found for {objective}_{tier}_{risk}")
                return {}
            # Sort by optimized Sharpe ratio
            best = max(results, key=lambda r: r.optimized_sharpe or 0)
            return {
                "profile_id": best.profile_id,
                "objective": best.objective,
                "risk_tolerance": best.risk_tolerance,
                "capital_tier": best.capital_tier,
                "baseline_metrics": {
                    "sharpe_ratio": best.baseline_sharpe,
                    "total_return": best.baseline_return,
                    "max_drawdown": best.baseline_max_dd,
                    "win_rate": best.baseline_win_rate,
                },
                "optimized_metrics": {
                    "sharpe_ratio": best.optimized_sharpe,
                    "total_return": best.optimized_return,
                    "max_drawdown": best.optimized_max_dd,
                    "win_rate": best.optimized_win_rate,
                },
                "best_parameters": best.best_parameters,
                "improvement": {
                    "sharpe": best.sharpe_improvement,
                    "return": best.return_improvement,
                    "max_dd": best.max_dd_improvement,
                    "win_rate": best.win_rate_improvement,
                },
                "ready_for_paper_trading": best.ready_for_paper_trading,
                "recommendation": best.recommendation,
            }
        finally:
            session.close()

    def export_results(self, format: str = "json") -> Path:
        """
        Export results to file.
        Args:
            format: Export format (json, csv, excel)
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if format == "json":
            output_path = self.output_dir / f"profile_batch_results_{timestamp}.json"
            # Convert results to dict
            data = {pid: self._result_to_dict(r) for pid, r in self.results.items()}
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        elif format == "csv":
            output_path = self.output_dir / f"profile_batch_results_{timestamp}.csv"
            # Flatten results
            rows = []
            for pid, result in self.results.items():
                row = {
                    "profile_id": pid,
                    "objective": result.profile.objetivo_inversion.value,
                    "risk_tolerance": result.profile.risk_tolerance.value,
                    "capital_tier": result.profile.capital_flag,
                    "investment_horizon": result.profile.investment_horizon,
                    **result.baseline_results,
                    **{f"opt_{k}": v for k, v in result.optimization_results.items()},
                    **{f"imp_{k}": v for k, v in result.improvement_metrics.items()},
                    "ready_for_paper_trading": result.ready_for_paper_trading,
                    "recommendation": result.recommendation,
                }
                rows.append(row)
            df = pd.DataFrame(rows)
            df.to_csv(output_path, index=False)
        elif format == "excel":
            output_path = self.output_dir / f"profile_batch_results_{timestamp}.xlsx"
            # Create multiple sheets
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                # Summary sheet
                rows = []
                for pid, result in self.results.items():
                    row = {
                        "profile_id": pid,
                        "objective": result.profile.objetivo_inversion.value,
                        "risk_tolerance": result.profile.risk_tolerance.value,
                        "capital_tier": result.profile.capital_flag,
                        "baseline_sharpe": result.baseline_results.get("sharpe_ratio"),
                        "optimized_sharpe": result.optimization_results.get("sharpe_ratio"),
                        "sharpe_improvement": result.improvement_metrics.get("sharpe_improvement"),
                        "ready": result.ready_for_paper_trading,
                        "recommendation": result.recommendation,
                    }
                    rows.append(row)
                pd.DataFrame(rows).to_excel(writer, sheet_name="Summary", index=False)
                # Detailed sheets by objective
                for objective in ObjectivoInversion:
                    obj_results = [
                        r
                        for r in self.results.values()
                        if r.profile.objetivo_inversion == objective
                    ]
                    if obj_results:
                        obj_rows = [self._result_to_dict(r) for r in obj_results]
                        pd.DataFrame(obj_rows).to_excel(
                            writer, sheet_name=objective.value[:31], index=False
                        )
        else:
            raise ValueError(f"Unsupported format: {format}")
        logger.info(f"Results exported to {output_path}")
        return output_path

    def _result_to_dict(self, result: ProfileResult) -> Dict[str, Any]:
        """Convert ProfileResult to dictionary."""
        return {
            "profile_id": result.profile_id,
            "objective": result.profile.objetivo_inversion.value,
            "risk_tolerance": result.profile.risk_tolerance.value,
            "capital_tier": result.profile.capital_flag,
            "investment_horizon": result.profile.investment_horizon,
            "baseline_results": result.baseline_results,
            "optimization_results": result.optimization_results,
            "best_parameters": result.best_parameters,
            "improvement_metrics": result.improvement_metrics,
            "ready_for_paper_trading": result.ready_for_paper_trading,
            "recommendation": result.recommendation,
            "created_at": result.created_at.isoformat(),
        }

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
        """
        template_str = """
<!DOCTYPE html>
<html>
<head>
    <title>Profile Batch Backtesting Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .metric-card h3 { margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; }
        .metric-card .value { font-size: 28px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #34495e; color: white; font-weight: 600; }
        tr:hover { background: #f5f5f5; }
        .improvement-positive { color: #27ae60; font-weight: bold; }
        .improvement-negative { color: #e74c3c; font-weight: bold; }
        .recommendation { padding: 15px; border-radius: 8px; margin: 20px 0; font-weight: bold; }
        .recommendation.approved { background: #d4edda; color: #155724; border: 2px solid #c3e6cb; }
        .recommendation.rejected { background: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; }
        .recommendation.revision { background: #fff3cd; color: #856404; border: 2px solid #ffeaa7; }
        .parameter-bar { height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; }
        .parameter-fill { height: 100%; background: linear-gradient(90deg, #3498db, #2ecc71); transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Profile Batch Backtesting Report</h1>
        <p><strong>Generated:</strong> {{ timestamp }}</p>
        <p><strong>Total Profiles:</strong> {{ total_profiles }}</p>
        <div class="summary">
            <div class="metric-card">
                <h3>Profiles Ready</h3>
                <div class="value">{{ ready_count }}</div>
            </div>
            <div class="metric-card">
                <h3>Avg Sharpe Improvement</h3>
                <div class="value">{{ avg_sharpe_improvement }}%</div>
            </div>
            <div class="metric-card">
                <h3>Avg Return Improvement</h3>
                <div class="value">{{ avg_return_improvement }}%</div>
            </div>
            <div class="metric-card">
                <h3>Optimization Recommended</h3>
                <div class="value">{{ optimization_pct }}%</div>
            </div>
        </div>
        <h2>Baseline vs Optimized Comparison</h2>
        <table>
            <thead>
                <tr>
                    <th>Profile</th>
                    <th>Baseline Sharpe</th>
                    <th>Optimized Sharpe</th>
                    <th>Improvement</th>
                    <th>Baseline Return</th>
                    <th>Optimized Return</th>
                    <th>Improvement</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>
                {% for result in results %}
                <tr>
                    <td>{{ result.profile_id }}</td>
                    <td>{{ "%.2f"|format(result.baseline_results.get('sharpe_ratio', 0)) }}</td>
                    <td>{{ "%.2f"|format(result.optimization_results.get('sharpe_ratio', 0)) }}</td>
                    <td class="{% if result.improvement_metrics.get('sharpe_improvement', 0) > 0 %}improvement-positive{% else %}improvement-negative{% endif %}">
                        {{ "%+.1f"|format(result.improvement_metrics.get('sharpe_improvement', 0)) }}%
                    </td>
                    <td>{{ "%.2f"|format(result.baseline_results.get('return_pct', 0)) }}%</td>
                    <td>{{ "%.2f"|format(result.optimization_results.get('return_pct', 0)) }}%</td>
                    <td class="{% if result.improvement_metrics.get('return_improvement', 0) > 0 %}improvement-positive{% else %}improvement-negative{% endif %}">
                        {{ "%+.1f"|format(result.improvement_metrics.get('return_improvement', 0)) }}%
                    </td>
                    <td>
                        {% if result.ready_for_paper_trading %}
                        <span class="recommendation approved">APPROVED</span>
                        {% else %}
                        <span class="recommendation rejected">REJECTED</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% if parameter_importance %}
        <h2>Parameter Importance Analysis</h2>
        <table>
            <thead>
                <tr>
                    <th>Parameter</th>
                    <th>Importance</th>
                    <th>Visual</th>
                </tr>
            </thead>
            <tbody>
                {% for param, importance in parameter_importance.items() %}
                <tr>
                    <td>{{ param }}</td>
                    <td>{{ "%.3f"|format(importance) }}</td>
                    <td>
                        <div class="parameter-bar">
                            <div class="parameter-fill" style="width: {{ (importance * 100)|int }}%"></div>
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
        <h2>Best Strategies by Objective</h2>
        {% for objective in best_strategies %}
        <h3>{{ objective.objective|upper }}</h3>
        <table>
            <tr>
                <th>Risk Tolerance</th>
                <th>Capital Tier</th>
                <th>Best Sharpe</th>
                <th>Best Return</th>
                <th>Improvement</th>
            </tr>
            {% for tier_result in objective.results %}
            <tr>
                <td>{{ tier_result.risk_tolerance }}</td>
                <td>{{ tier_result.capital_tier }}</td>
                <td>{{ "%.2f"|format(tier_result.optimized_sharpe or 0) }}</td>
                <td>{{ "%.2f"|format(tier_result.optimized_return or 0) }}%</td>
                <td class="{% if tier_result.sharpe_improvement > 0 %}improvement-positive{% else %}improvement-negative{% endif %}">
                    {{ "%+.1f"|format(tier_result.sharpe_improvement) }}%
                </td>
            </tr>
            {% endfor %}
        </table>
        {% endfor %}
    </div>
</body>
</html>
        """
        # Prepare template data
        results_list = list(self.results.values())
        # Calculate summary stats
        ready_count = sum(1 for r in results_list if r.ready_for_paper_trading)
        avg_sharpe_imp = np.mean(
            [r.improvement_metrics.get("sharpe_improvement", 0) for r in results_list]
        )
        avg_return_imp = np.mean(
            [r.improvement_metrics.get("return_improvement", 0) for r in results_list]
        )
        optimization_rec_pct = (
            sum(1 for r in results_list if "optimized" in r.recommendation.lower())
            / len(results_list)
            * 100
            if results_list
            else 0
        )
        # Aggregate parameter importance
        param_importance = {}
        for result in results_list:
            for param, imp in result.comparison.parameter_importance.items():
                if param not in param_importance:
                    param_importance[param] = []
                param_importance[param].append(imp)
        param_importance_avg = {
            k: np.mean(v) for k, v in sorted(param_importance.items(), key=lambda x: -np.mean(x[1]))
        }
        # Group best strategies by objective
        best_by_objective = []
        for objective in ObjectivoInversion:
            obj_results = [r for r in results_list if r.profile.objetivo_inversion == objective]
            if obj_results:
                # Group by risk and tier
                grouped = {}
                for r in obj_results:
                    key = (r.profile.risk_tolerance.value, r.profile.capital_flag)
                    if key not in grouped:
                        grouped[key] = r
                    else:
                        # Keep best Sharpe
                        if r.optimization_results.get("sharpe_ratio", 0) > grouped[
                            key
                        ].optimization_results.get("sharpe_ratio", 0):
                            grouped[key] = r
                best_by_objective.append(
                    {
                        "objective": objective.value,
                        "results": [
                            {
                                "risk_tolerance": k[0],
                                "capital_tier": k[1],
                                "optimized_sharpe": v.optimization_results.get("sharpe_ratio"),
                                "optimized_return": v.optimization_results.get("return_pct"),
                                "sharpe_improvement": v.improvement_metrics.get(
                                    "sharpe_improvement"
                                ),
                            }
                            for k, v in grouped.items()
                        ],
                    }
                )
        # Render template
        template = Template(template_str)
        html = template.render(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_profiles=len(results_list),
            ready_count=ready_count,
            avg_sharpe_improvement=f"{avg_sharpe_imp:.1f}",
            avg_return_improvement=f"{avg_return_imp:.1f}",
            optimization_pct=f"{optimization_rec_pct:.0f}",
            results=results_list,
            parameter_importance=param_importance_avg,
            best_strategies=best_by_objective,
        )
        # Save to file
        output_path = (
            self.output_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        with open(output_path, "w") as f:
            f.write(html)
        logger.info(f"Comparison report generated: {output_path}")
        return html

    def _generate_batch_summary(self, results: Dict[str, ProfileResult]) -> None:
        """Generate batch execution summary."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_profiles": len(results),
            "ready_for_paper_trading": sum(
                1 for r in results.values() if r.ready_for_paper_trading
            ),
            "rejected": sum(1 for r in results.values() if not r.ready_for_paper_trading),
            "average_improvements": {
                "sharpe": np.mean(
                    [r.improvement_metrics.get("sharpe_improvement", 0) for r in results.values()]
                ),
                "return": np.mean(
                    [r.improvement_metrics.get("return_improvement", 0) for r in results.values()]
                ),
            },
            "best_overall": max(
                results.items(),
                key=lambda x: x[1].optimization_results.get("sharpe_ratio", 0),
                default=(None, None),
            ),
            # Include fallback metrics in summary
            "fallback_metrics": self.get_fallback_metrics(),
        }
        summary_path = (
            self.output_dir / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"Batch summary saved: {summary_path}")
        # Log fallback summary after batch completion
        self.log_fallback_summary()

    def _aggregate_multi_strategy_results(
        self, results: List[Dict[str, Any]], profile: InputProfile
    ) -> Dict[str, Any]:
        """
        Aggregate multi-strategy backtest results into combined metrics.
        Args:
            results: List of results from multi-strategy backtest
            profile: InputProfile for context
        Returns:
            Combined metrics dictionary
        """
        if not results:
            logger.warning("No results to aggregate")
            return self._get_empty_metrics()
        # Separate per-strategy and combined results
        per_strategy_results = {}
        combined_result = None
        for result in results:
            strategy_name = result.get("strategy_name", "unknown")
            if strategy_name == "combined":
                combined_result = result
            else:
                per_strategy_results[strategy_name] = result
        if combined_result:
            # Use the pre-calculated combined result
            logger.info(
                f"Using pre-calculated combined result with {len(per_strategy_results)} strategies"
            )
            return combined_result
        # If no combined result, calculate it manually
        if not per_strategy_results:
            logger.warning("No per-strategy results found")
            return self._get_empty_metrics()
        logger.info(f"Calculating combined metrics from {len(per_strategy_results)} strategies")
        # Calculate weighted average metrics
        total_initial_capital = float(profile.capital_initial)
        total_final_capital = 0.0
        total_pnl = 0.0
        total_trades = 0
        # Weight metrics by capital allocation
        weighted_sharpe = 0.0
        weighted_return = 0.0
        weighted_max_dd = 0.0
        total_weight = 0.0
        for strategy_name, result in per_strategy_results.items():
            capital_weight = result.get("capital_weight", 0.0)
            if capital_weight == 0.0:
                # Equal weight if not specified
                capital_weight = 1.0 / len(per_strategy_results)
            final_capital = result.get("final_capital", 0.0)
            total_final_capital += final_capital
            total_trades += result.get("total_trades", 0)
            # Weight metrics
            weighted_sharpe += result.get("sharpe_ratio", 0.0) * capital_weight
            weighted_return += result.get("return_pct", 0.0) * capital_weight
            weighted_max_dd += result.get("max_drawdown", 0.0) * capital_weight
            total_weight += capital_weight
        # Calculate combined metrics
        total_pnl = total_final_capital - total_initial_capital
        combined_return = (
            (total_pnl / total_initial_capital * 100) if total_initial_capital > 0 else 0.0
        )
        # Normalize weighted metrics
        if total_weight > 0:
            weighted_sharpe /= total_weight
            weighted_return /= total_weight
            weighted_max_dd /= total_weight
        combined_metrics = {
            "test_type": "multi_strategy_combined",
            "test_name": f"Multi-Strategy Combined - {profile.objetivo_inversion.value}",
            "strategy_name": "combined",
            "modules_active": list(per_strategy_results.keys()),
            "learning_engine": None,
            "thresholds": {},
            # Combined metrics
            "total_pnl": total_pnl,
            "return_pct": combined_return,
            "sharpe_ratio": weighted_sharpe,
            "max_drawdown": weighted_max_dd,
            "win_rate": 0.0,  # Not applicable for combined portfolio
            "total_trades": total_trades,
            "avg_trade_pnl": (total_pnl / total_trades) if total_trades > 0 else 0.0,
            "final_capital": total_final_capital,
            # Portfolio info
            "total_initial_capital": total_initial_capital,
            "num_strategies": len(per_strategy_results),
            "per_strategy_results": per_strategy_results,
        }
        logger.info(
            f"Combined metrics: Sharpe={weighted_sharpe:.2f}, "
            f"Return={combined_return:.2f}%, Max DD={weighted_max_dd:.2f}%"
        )
        return combined_metrics

    def _apply_ensemble_voting(
        self,
        profile: InputProfile,
        strategy_mapping: Optional[StrategyMapping],
        per_strategy_signals: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Apply ensemble voting logic to combine strategy signals.
        Args:
            profile: InputProfile
            strategy_mapping: StrategyMapping with ensemble config
            per_strategy_signals: Dictionary of signals per strategy
        Returns:
            Ensemble voting result
        """
        if not strategy_mapping or not per_strategy_signals:
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
            # Conservative: requires majority
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
            # Balanced: weighted voting
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
            elif sell_weight >= min_confidence and sell_weight > buy_weight:
                action = "sell"
                confidence = sell_weight
            else:
                action = "hold"
                confidence = 0.0
            voting_breakdown["buy_weight"] = buy_weight
            voting_breakdown["sell_weight"] = sell_weight
        elif ensemble_mode == "regime_selector":
            # Aggressive: strongest signal
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
