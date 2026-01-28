"""
Profile Batch Configuration Module.

This module contains configuration dataclasses, profile definitions,
and database models for profile batch backtesting.

Clean Architecture Principles:
- Configuration as value objects (immutable dataclasses)
- Clear separation between domain models and persistence models
- Dependency inversion: depend on abstractions, not concretions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.models.input_profile import InputProfile

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


# ============================================================================
# Database Models
# ============================================================================


class ProfileResultDB(Base):
    """Database model for profile results.

    This is a persistence model - separate from domain models to follow
    Clean Architecture's dependency rule: domain models don't depend
    on infrastructure.
    """

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
# Domain Models (Value Objects)
# ============================================================================


@dataclass(frozen=True)
class BaselineOptimizationComparison:
    """Comparison between baseline and optimized results.

    Immutable value object following Clean Architecture.
    Represents a comparison that cannot be changed after creation.
    """

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


@dataclass(frozen=True)
class OptimizedStrategy:
    """Result of optimization pipeline.

    Immutable value object containing complete optimization results.
    """

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
    """Complete result for a single profile.

    Domain entity representing the complete backtest result for a profile.
    """

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
    strategy_mapping: Optional[Any] = None
    enabled_strategies: List[str] = field(default_factory=list)
    learning_engines: List[str] = field(default_factory=list)
    ensemble_config: Dict[str, Any] = field(default_factory=dict)
    per_strategy_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)


# ============================================================================
# Configuration Value Objects
# ============================================================================


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for backtest execution.

    Immutable configuration value object.
    """

    input_config: Dict[str, Any]
    modules_config: Dict[str, Any]
    risk_management: Dict[str, Any]
    strategy_config: Dict[str, Any]
    reporting_config: Dict[str, Any]
    strategy_metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backtest runner."""
        return {
            "input": self.input_config,
            "modules": self.modules_config,
            "risk_management": self.risk_management,
            "strategy": self.strategy_config,
            "reporting": self.reporting_config,
        }


@dataclass(frozen=True)
class OptimizationConfig:
    """Configuration for optimization parameters."""

    n_trials: int = 100
    timeout: Optional[int] = None
    rsi_buy_min: int = 20
    rsi_buy_max: int = 35
    volume_min: float = 1.0
    volume_max: float = 1.5
    ema_short_min: int = 5
    ema_short_max: int = 20
    ema_long_min: int = 20
    ema_long_max: int = 50
    stop_loss_min: float = 0.01
    stop_loss_max: float = 0.05
    take_profit_min: float = 0.05
    take_profit_max: float = 0.20


@dataclass(frozen=True)
class ValidationConfig:
    """Configuration for validation thresholds."""

    # Walk-forward
    wf_min_avg_sharpe: float = 0.5
    wf_min_success_rate: float = 0.6
    wf_max_sharpe_decay: float = 1.0
    wf_n_windows: int = 5
    wf_train_pct: float = 0.7

    # Monte Carlo
    mc_n_simulations: int = 1000
    mc_confidence_level: float = 0.95
    mc_min_profitable_pct: float = 0.95

    # Out-of-Sample
    oos_train_percentage: float = 0.7
    oos_min_sharpe: float = 0.5
    oos_max_performance_decay: float = 0.3


@dataclass(frozen=True)
class AcceptanceCriteriaConfig:
    """Configuration for acceptance criteria."""

    significance_threshold: float = 5.0
    strong_significance_threshold: float = 10.0
    degradation_threshold: float = -5.0
    confidence_high: float = 0.8
    confidence_medium: float = 0.7
    confidence_low: float = 0.5


# ============================================================================
# Configuration Manager
# ============================================================================


class ProfileBatchConfigManager:
    """
    Load and validate configurations for profile batch backtesting.

    This class follows the Single Responsibility Principle:
    - Load configuration from YAML
    - Validate configuration
    - Create profile-specific configurations
    - Provide configuration objects to other components

    It depends on abstractions (interfaces) rather than concrete implementations.
    """

    def __init__(self, config_path: str):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Extract configuration sections
        self.capital_tiers = self.config.get("capital_tiers", {})
        self.horizons = self.config.get("investment_horizons", {})
        self.optimization_config = self.config.get("optimization", {})
        self.validation_config = self.config.get("validation", {})
        self.acceptance_criteria = self.config.get("acceptance_criteria", {})

        # Initialize ProfileConfigLoader for parameter ranges
        from app.core.config.profile_config_loader import ProfileConfigLoader
        try:
            self.profile_config_loader = ProfileConfigLoader()
            logger.info("ProfileConfigLoader initialized successfully")
        except Exception as e:
            logger.warning(f"ProfileConfigLoader not available: {e}")
            self.profile_config_loader = None

        # Initialize ProfileStrategyMapper
        from app.services.profile_driven_trading.profile_strategy_mapper import create_profile_mapper
        try:
            self.profile_mapper = create_profile_mapper()
            logger.info("ProfileStrategyMapper initialized successfully")
        except Exception as e:
            logger.warning(f"ProfileStrategyMapper not available: {e}")
            self.profile_mapper = None

        # Validate configurations on startup
        self._validate_configurations()

        logger.info(f"ProfileBatchConfigManager initialized with config: {config_path}")

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

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

    def get_investment_horizons(self) -> List[int]:
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

        # Handle dict format
        if isinstance(horizons_config, dict):
            horizons = list(horizons_config.values())
            logger.info(f"Loaded investment horizons from dict: {horizons_config}")
        # Handle list format
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
            try:
                horizon_int = int(horizon)
            except (ValueError, TypeError):
                logger.error(f"Invalid horizon value '{horizon}', must be integer. Skipping.")
                continue

            if horizon_int <= 0:
                logger.error(f"Invalid horizon value {horizon_int}, must be positive. Skipping.")
                continue

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

    def get_optimization_config(self) -> OptimizationConfig:
        """Get optimization configuration as value object."""
        n_trials = self.optimization_config.get("n_trials", 100)
        timeout = self.optimization_config.get("timeout", None)

        # Try to get parameter ranges from ProfileConfigLoader
        if self.profile_config_loader is not None:
            try:
                rsi_buy_config = self.profile_config_loader.get_threshold_config("rsi").get("buy_threshold", {})
                rsi_buy_min = rsi_buy_config.get("min", 20)
                rsi_buy_max = rsi_buy_config.get("max", 35)

                vol_config = self.profile_config_loader.get_threshold_config("volume_ratio", {})
                vol_min = vol_config.get("min", 1.0)
                vol_max = vol_config.get("max", 1.5)

                logger.debug("Loaded parameter ranges from ProfileConfigLoader")
            except Exception as e:
                logger.warning(f"Failed to load from ProfileConfigLoader: {e}, using defaults")
                rsi_buy_min, rsi_buy_max = 20, 35
                vol_min, vol_max = 1.0, 1.5
        else:
            logger.info("Using default parameter ranges (ProfileConfigLoader not initialized)")
            rsi_buy_min, rsi_buy_max = 20, 35
            vol_min, vol_max = 1.0, 1.5

        return OptimizationConfig(
            n_trials=n_trials,
            timeout=timeout,
            rsi_buy_min=rsi_buy_min,
            rsi_buy_max=rsi_buy_max,
            volume_min=vol_min,
            volume_max=vol_max,
        )

    def get_validation_config(self) -> ValidationConfig:
        """Get validation configuration as value object."""
        wf_config = self.validation_config.get("walk_forward", {})
        mc_config = self.validation_config.get("monte_carlo", {})
        oos_config = self.validation_config.get("out_of_sample", {})

        return ValidationConfig(
            # Walk-forward
            wf_min_avg_sharpe=wf_config.get("min_avg_sharpe", 0.5),
            wf_min_success_rate=wf_config.get("min_success_rate", 0.6),
            wf_max_sharpe_decay=wf_config.get("max_sharpe_decay", 1.0),
            wf_n_windows=wf_config.get("n_windows", 5),
            wf_train_pct=wf_config.get("train_percentage", 0.7),
            # Monte Carlo
            mc_n_simulations=mc_config.get("n_simulations", 1000),
            mc_confidence_level=mc_config.get("confidence_level", 0.95),
            mc_min_profitable_pct=mc_config.get("min_profitable_pct", 0.95),
            # Out-of-Sample
            oos_train_percentage=oos_config.get("train_percentage", 0.7),
            oos_min_sharpe=oos_config.get("min_oos_sharpe", 0.5),
            oos_max_performance_decay=oos_config.get("max_performance_decay", 0.3),
        )

    def get_acceptance_criteria_config(self) -> AcceptanceCriteriaConfig:
        """Get acceptance criteria configuration as value object."""
        return AcceptanceCriteriaConfig(
            significance_threshold=self.acceptance_criteria.get("significance_threshold", 5.0),
            strong_significance_threshold=self.acceptance_criteria.get("strong_significance_threshold", 10.0),
            degradation_threshold=self.acceptance_criteria.get("degradation_threshold", -5.0),
            confidence_high=self.acceptance_criteria.get("confidence_high", 0.8),
            confidence_medium=self.acceptance_criteria.get("confidence_medium", 0.7),
            confidence_low=self.acceptance_criteria.get("confidence_low", 0.5),
        )

    def create_profile_config(self, profile: InputProfile) -> BacktestConfig:
        """
        Create backtest configuration for a profile using ProfileStrategyMapper.

        This method integrates with ProfileStrategyMapper to get comprehensive
        strategy configuration including multi-strategy support, learning engines,
        and ensemble configurations.

        Args:
            profile: InputProfile to create configuration for

        Returns:
            BacktestConfig value object
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
                return BacktestConfig(
                    input_config={
                        "initial_capital": float(profile.capital_initial),
                        "start_date": self.config.get("backtest_period", {}).get("start_date", "2020-01-01"),
                        "end_date": self.config.get("backtest_period", {}).get("end_date", "2023-12-31"),
                        "symbols": self.config.get("symbols", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]),
                    },
                    modules_config={
                        "enabled_strategies": enabled_strategies,
                        **self.config.get("modules", {}),
                    },
                    risk_management={
                        "max_position_size": float(profile.capital_initial * Decimal(str(risk_params.get("max_position_size", 0.20)))),
                        "max_sector_allocation": risk_params.get("max_sector_allocation", 0.30),
                        "leverage": risk_params.get("leverage", 1.0),
                        "risk_profile": risk_params.get("risk_profile", 4),
                        **risk_params,
                    },
                    strategy_config={
                        "learning_mode": learning_engines[0] if learning_engines else "supervised",
                        "learning_engines": learning_engines,
                        "ensemble_config": ensemble_config,
                        "objective": strategy_config.get("objective"),
                        "capital_tier": strategy_config.get("capital_tier"),
                        **trading_params,
                    },
                    reporting_config=self.config.get("reporting", {}),
                    strategy_metadata={
                        "enabled_strategies": enabled_strategies,
                        "learning_engines": learning_engines,
                        "ensemble_config": ensemble_config,
                        "objective": strategy_config.get("objective"),
                        "capital_tier": self._get_capital_tier_key(profile),
                    },
                )

            except Exception as e:
                logger.warning(f"ProfileStrategyMapper failed for {profile.input_id}: {e}, falling back to manual config")
                # Fall through to manual configuration

        # Fallback: Manual configuration (backward compatible)
        logger.info(f"Using manual configuration for profile {profile.input_id}")

        # Get parameters from config based on profile
        risk_key = profile.risk_tolerance.value
        objective_key = profile.objetivo_inversion.value

        # Risk-based parameters
        risk_params = self.config.get("risk_parameters", {}).get(risk_key, {})
        # Objective-based parameters
        objective_params = self.config.get("objective_parameters", {}).get(objective_key, {})

        return BacktestConfig(
            input_config={
                "initial_capital": float(profile.capital_initial),
                "start_date": self.config.get("backtest_period", {}).get("start_date", "2020-01-01"),
                "end_date": self.config.get("backtest_period", {}).get("end_date", "2023-12-31"),
                "symbols": self.config.get("symbols", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]),
            },
            modules_config=self.config.get("modules", {}),
            risk_management={
                **risk_params,
                "max_position_size": float(profile.capital_initial * Decimal(str(risk_params.get("max_position_pct", 0.1)))),
            },
            strategy_config={
                **objective_params,
                "learning_mode": "supervised",
            },
            reporting_config=self.config.get("reporting", {}),
            strategy_metadata={
                "enabled_strategies": [],
                "learning_engines": [],
                "ensemble_config": {},
                "objective": objective_key,
                "capital_tier": self._get_capital_tier_key(profile),
            },
        )

    def _get_capital_tier_key(self, profile: InputProfile) -> str:
        """
        Map capital_flag to config tier key using unified tier mapping.

        The InputProfile.capital_flag returns 'small', 'medium', 'large'
        but config expects 'bajo', 'medio', 'alto'.

        Args:
            profile: InputProfile

        Returns:
            Mapped tier key for config lookups (bajo, medio, or alto)
        """
        try:
            from app.core.tier_mapper import map_profile_tier_to_config
            return map_profile_tier_to_config(profile.capital_flag, target_format="spanish")
        except Exception as e:
            logger.warning(f"Tier mapper failed for {profile.capital_flag}, using fallback: {e}")
            tier_map = {
                "small": "bajo",
                "medium": "medio",
                "large": "alto"
            }
            return tier_map.get(profile.capital_flag, "medio")

    def get_capital_tier_config(self, tier: str) -> Decimal:
        """Get capital amount for tier."""
        return Decimal(str(self.capital_tiers.get(tier, 100000)))
