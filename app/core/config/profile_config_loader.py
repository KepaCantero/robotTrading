"""
Profile Configuration Loader for Backtesting and Strategy Parameters

Centralized loader for accessing all backtesting and strategy parameters
from the profile_optimization.yaml configuration file.

This module provides:
- Loading of profile optimization configuration
- Profile-specific overrides (conservative, balanced, aggressive, etc.)
- Tier-specific overrides (micro, small, medium, large)
- Parameter validation
- Default value handling
- Convenience methods for common parameter access patterns
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ...core.config_loader import YAMLConfigLoader

logger = logging.getLogger(__name__)


class ProfileConfigLoader:
    """
    Loader for profile optimization configuration with tier and profile support.

    Features:
    - Load profile optimization configuration from YAML
    - Apply profile-specific overrides (conservative, balanced, aggressive, etc.)
    - Apply tier-specific overrides (micro, small, medium, large)
    - Validate parameter ranges
    - Provide convenience methods for common parameters
    - Cache loaded configurations for performance
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        profile: Optional[str] = None,
        tier: Optional[str] = None,
    ):
        """
        Initialize the profile configuration loader.

        Args:
            config_path: Path to profile_optimization.yaml.
                        Defaults to config/backtesting/profile_optimization.yaml
            profile: Risk profile to apply (conservative, balanced, aggressive, etc.)
            tier: Capital tier to apply (micro, small, medium, large)
        """
        self.config_path = config_path or Path("config/backtesting/profile_optimization.yaml")
        self.profile = profile
        self.tier = tier

        # Use the existing YAMLConfigLoader
        self.yaml_loader = YAMLConfigLoader(self.config_path.parent)

        # Load configuration
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file and apply overrides."""
        # Load base configuration
        self._config = self.yaml_loader.load(self.config_path.name)

        if not self._config:
            logger.warning(f"No configuration loaded from {self.config_path}")
            self._config = {}
            return

        # Apply profile override if specified
        if self.profile and "profiles" in self._config:
            if self.profile in self._config["profiles"]:
                profile_override = self._config["profiles"][self.profile]
                if profile_override != "pass":
                    self._config = self._apply_overrides(self._config, profile_override)
                    logger.debug(f"Applied profile override: {self.profile}")
            else:
                logger.warning(f"Profile '{self.profile}' not found in configuration")

        # Apply tier override if specified
        if self.tier and "tiers" in self._config:
            if self.tier in self._config["tiers"]:
                tier_override = self._config["tiers"][self.tier]
                if tier_override != "pass":
                    self._config = self._apply_overrides(self._config, tier_override)
                    logger.debug(f"Applied tier override: {self.tier}")
            else:
                logger.warning(f"Tier '{self.tier}' not found in configuration")

    def _apply_overrides(self, base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively apply overrides to base configuration.

        Args:
            base: Base configuration dictionary
            overrides: Override values to apply

        Returns:
            Configuration with overrides applied
        """
        result = base.copy()

        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._apply_overrides(result[key], value)
            else:
                # Override value
                result[key] = value

        return result

    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config or {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the value (e.g., "common.random_state")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> loader.get("common.random_state", 42)
            42
            >>> loader.get("models.random_forest.n_estimators", 100)
            100
        """
        return self.yaml_loader.get_nested(self.config, key_path, default)

    # ========================================================================
    # COMMON PARAMETERS
    # ========================================================================

    def get_random_state(self) -> int:
        """Get random state seed for reproducibility."""
        return self.get("common.random_state", 42)

    def get_test_size(self) -> float:
        """Get train/test split ratio."""
        return self.get("common.test_size", 0.2)

    def get_cv_folds(self) -> int:
        """Get number of cross-validation folds."""
        return self.get("common.cv_folds", 5)

    def get_min_train_samples(self) -> int:
        """Get minimum samples required for training."""
        return self.get("common.min_train_samples", 100)

    # ========================================================================
    # THREADING CONFIGURATION
    # ========================================================================

    def get_max_workers(self, cpu_count: Optional[int] = None) -> Optional[int]:
        """
        Get maximum number of workers for parallel operations.

        Args:
            cpu_count: Number of CPUs available (auto-detected if None)

        Returns:
            Maximum workers or None for auto-detect
        """
        max_workers = self.get("threading.max_workers")
        if max_workers is not None:
            return max_workers

        # Calculate from CPU count and multiplier
        multiplier = self.get("threading.worker_multiplier", 0.75)
        cpu_count = cpu_count or 1
        return max(1, int(cpu_count * multiplier))

    def get_batch_size(self) -> int:
        """Get batch size for parallel processing."""
        return self.get("threading.batch_size", 32)

    def get_task_timeout(self) -> int:
        """Get task timeout in seconds."""
        return self.get("threading.task_timeout", 300)

    # ========================================================================
    # MODEL PARAMETERS
    # ========================================================================

    def get_model_params(self, model_type: str) -> Dict[str, Any]:
        """
        Get parameters for a specific model type.

        Args:
            model_type: Model type (random_forest, xgboost, lightgbm, etc.)

        Returns:
            Dictionary of model parameters

        Examples:
            >>> params = loader.get_model_params("random_forest")
            >>> params["n_estimators"]
            100
        """
        return self.get(f"models.{model_type}", {})

    def get_random_forest_params(self) -> Dict[str, Any]:
        """Get Random Forest model parameters."""
        return self.get_model_params("random_forest")

    def get_xgboost_params(self) -> Dict[str, Any]:
        """Get XGBoost model parameters."""
        return self.get_model_params("xgboost")

    def get_lightgbm_params(self) -> Dict[str, Any]:
        """Get LightGBM model parameters."""
        return self.get_model_params("lightgbm")

    # ========================================================================
    # REINFORCEMENT LEARNING
    # ========================================================================

    def get_rl_environment_config(self) -> Dict[str, Any]:
        """Get RL environment configuration."""
        return self.get("reinforcement_learning.environment", {})

    def get_rl_reward_config(self) -> Dict[str, Any]:
        """Get RL reward configuration."""
        return self.get("reinforcement_learning.rewards", {})

    def get_rl_algorithm_params(self, algorithm: str) -> Dict[str, Any]:
        """
        Get RL algorithm parameters.

        Args:
            algorithm: Algorithm name (ppo, a2c, dqn, sac)

        Returns:
            Algorithm-specific parameters
        """
        return self.get(f"reinforcement_learning.algorithms.{algorithm}", {})

    def get_rl_training_params(self) -> Dict[str, Any]:
        """Get RL training parameters."""
        return self.get("reinforcement_learning.training", {})

    def get_rl_network_config(self) -> Dict[str, Any]:
        """Get RL network architecture configuration."""
        return self.get("reinforcement_learning.network", {})

    # ========================================================================
    # THRESHOLD OPTIMIZATION
    # ========================================================================

    def get_threshold_config(self, indicator: str) -> Dict[str, Any]:
        """
        Get threshold optimization configuration for an indicator.

        Args:
            indicator: Indicator name (rsi, stoch_rsi, momentum, etc.)

        Returns:
            Threshold optimization configuration

        Examples:
            >>> config = loader.get_threshold_config("rsi")
            >>> config["buy_threshold"]["default"]
            30
        """
        return self.get(f"threshold_optimization.{indicator}", {})

    def get_optimization_method(self) -> str:
        """Get optimization method (grid_search, random_search, bayesian)."""
        return self.get("threshold_optimization.optimization.method", "grid_search")

    def get_optimization_scoring(self) -> str:
        """Get optimization scoring metric."""
        return self.get("threshold_optimization.optimization.scoring", "sharpe")

    # ========================================================================
    # VALIDATION PARAMETERS
    # ========================================================================

    def get_walk_forward_config(self) -> Dict[str, Any]:
        """Get walk-forward validation configuration."""
        return self.get("validation.walk_forward", {})

    def get_monte_carlo_config(self) -> Dict[str, Any]:
        """Get Monte Carlo validation configuration."""
        return self.get("validation.monte_carlo", {})

    def get_validation_thresholds(self) -> Dict[str, Any]:
        """Get validation performance thresholds."""
        return self.get("validation.thresholds", {})

    # ========================================================================
    # REPORTING CONFIGURATION
    # ========================================================================

    def get_output_directory(self) -> Path:
        """Get output directory for reports."""
        output_dir = self.get("reporting.output_directory", "reports")
        return Path(output_dir)

    def get_report_metrics(self, level: str = "basic") -> List[str]:
        """
        Get metrics to include in reports.

        Args:
            level: Metric level (basic, advanced, detailed)

        Returns:
            List of metric names
        """
        return self.get(f"reporting.metrics.{level}", [])

    def get_visualization_config(self) -> Dict[str, Any]:
        """Get visualization settings."""
        return self.get("reporting.visualization", {})

    # ========================================================================
    # MEMORY MANAGEMENT
    # ========================================================================

    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory management configuration."""
        return self.get("memory", {})

    def get_max_results_in_memory(self) -> int:
        """Get maximum results to keep in memory."""
        return self.get("memory.max_results_in_memory", 500)

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate_parameter_range(
        self,
        key_path: str,
        value: Union[int, float],
        min_key: str = "min",
        max_key: str = "max",
    ) -> bool:
        """
        Validate a parameter value against its configured range.

        Args:
            key_path: Path to parameter configuration (e.g., "threshold_optimization.rsi.buy_threshold")
            value: Value to validate
            min_key: Key name for minimum value
            max_key: Key name for maximum value

        Returns:
            True if value is in range, False otherwise
        """
        param_config = self.get(key_path, {})
        if not param_config:
            return True  # No range constraints

        min_val = param_config.get(min_key)
        max_val = param_config.get(max_key)

        if min_val is not None and value < min_val:
            logger.warning(f"Value {value} below minimum {min_val} for {key_path}")
            return False

        if max_val is not None and value > max_val:
            logger.warning(f"Value {value} above maximum {max_val} for {key_path}")
            return False

        return True

    def get_parameter_range(
        self, key_path: str, min_key: str = "min", max_key: str = "max"
    ) -> tuple:
        """
        Get parameter range from configuration.

        Args:
            key_path: Path to parameter configuration
            min_key: Key name for minimum value
            max_key: Key name for maximum value

        Returns:
            Tuple of (min_value, max_value, step) or (None, None, None)
        """
        param_config = self.get(key_path, {})
        if not param_config:
            return (None, None, None)

        min_val = param_config.get(min_key)
        max_val = param_config.get(max_key)
        step = param_config.get("step")

        return (min_val, max_val, step)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Singleton instance cache
_loaders: Dict[tuple, ProfileConfigLoader] = {}


def get_profile_config_loader(
    profile: Optional[str] = None,
    tier: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> ProfileConfigLoader:
    """
    Get or create a ProfileConfigLoader instance with caching.

    Args:
        profile: Risk profile to apply
        tier: Capital tier to apply
        config_path: Path to configuration file

    Returns:
        ProfileConfigLoader instance

    Examples:
        >>> loader = get_profile_config_loader(profile="aggressive", tier="medium")
        >>> random_state = loader.get_random_state()
        42
    """
    cache_key = (profile, tier, config_path)

    if cache_key not in _loaders:
        _loaders[cache_key] = ProfileConfigLoader(
            config_path=config_path, profile=profile, tier=tier
        )

    return _loaders[cache_key]


def get_common_params(profile: Optional[str] = None, tier: Optional[str] = None) -> Dict[str, Any]:
    """
    Get common parameters as a dictionary.

    Args:
        profile: Risk profile to apply
        tier: Capital tier to apply

    Returns:
        Dictionary of common parameters
    """
    loader = get_profile_config_loader(profile=profile, tier=tier)

    return {
        "random_state": loader.get_random_state(),
        "test_size": loader.get_test_size(),
        "cv_folds": loader.get_cv_folds(),
        "min_train_samples": loader.get_min_train_samples(),
    }


def get_model_params(
    model_type: str,
    profile: Optional[str] = None,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get model parameters with profile and tier overrides applied.

    Args:
        model_type: Model type (random_forest, xgboost, etc.)
        profile: Risk profile to apply
        tier: Capital tier to apply

    Returns:
        Model parameters dictionary
    """
    loader = get_profile_config_loader(profile=profile, tier=tier)
    return loader.get_model_params(model_type)


def get_threshold_ranges(
    indicator: str,
    profile: Optional[str] = None,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get threshold optimization ranges for an indicator.

    Args:
        indicator: Indicator name (rsi, stoch_rsi, etc.)
        profile: Risk profile to apply
        tier: Capital tier to apply

    Returns:
        Dictionary with min, max, step, and default values
    """
    loader = get_profile_config_loader(profile=profile, tier=tier)
    return loader.get_threshold_config(indicator)


def get_rl_config(
    profile: Optional[str] = None,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get complete RL configuration with overrides.

    Args:
        profile: Risk profile to apply
        tier: Capital tier to apply

    Returns:
        Complete RL configuration dictionary
    """
    loader = get_profile_config_loader(profile=profile, tier=tier)

    return {
        "environment": loader.get_rl_environment_config(),
        "rewards": loader.get_rl_reward_config(),
        "training": loader.get_rl_training_params(),
        "network": loader.get_rl_network_config(),
    }


def clear_loader_cache() -> None:
    """Clear the loader cache."""
    global _loaders
    _loaders.clear()
