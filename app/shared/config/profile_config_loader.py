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
from typing import Optional, Union

from .config_loader import YAMLConfigLoader

logger = logging.getLogger(__name__)

# Recursive type for values loaded from YAML configuration files.
# YAML can contain nested dicts, lists, and scalars.
_ConfigValue = Union[
    str,
    int,
    float,
    bool,
    None,
    "dict[str, _ConfigValue]",
    "list[_ConfigValue]",
]


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
        self._config: dict[str, _ConfigValue] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML file and apply overrides."""
        # Load base configuration
        loaded = self.yaml_loader.load(self.config_path.name)
        if not loaded:
            logger.warning(f"No configuration loaded from {self.config_path}")
            self._config = {}
            return

        self._config = loaded

        # Apply profile override if specified
        if self.profile:
            profiles = self._config.get("profiles")
            if isinstance(profiles, dict):
                profile_override = profiles.get(self.profile)
                if isinstance(profile_override, dict):
                    self._config = self._apply_overrides(self._config, profile_override)
                    logger.debug(f"Applied profile override: {self.profile}")
                elif profile_override is None:
                    logger.warning(f"Profile '{self.profile}' not found in configuration")

        # Apply tier override if specified
        if self.tier:
            tiers = self._config.get("tiers")
            if isinstance(tiers, dict):
                tier_override = tiers.get(self.tier)
                if isinstance(tier_override, dict):
                    self._config = self._apply_overrides(self._config, tier_override)
                    logger.debug(f"Applied tier override: {self.tier}")
                elif tier_override is None:
                    logger.warning(f"Tier '{self.tier}' not found in configuration")

    def _apply_overrides(
        self, base: dict[str, _ConfigValue], overrides: dict[str, _ConfigValue]
    ) -> dict[str, _ConfigValue]:
        """
        Recursively apply overrides to base configuration.

        Args:
            base: Base configuration dictionary
            overrides: Override values to apply

        Returns:
            Configuration with overrides applied
        """
        result: dict[str, _ConfigValue] = base.copy()

        for key, value in overrides.items():
            existing = result.get(key)
            if isinstance(existing, dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._apply_overrides(existing, value)
            else:
                # Override value
                result[key] = value

        return result

    @property
    def config(self) -> dict[str, _ConfigValue]:
        """Get the full configuration dictionary."""
        return self._config

    def get(
        self,
        key_path: str,
        default: _ConfigValue = None,
    ) -> _ConfigValue:
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
        if isinstance(default, (dict, list)):
            # get_nested only accepts scalar defaults; resolve manually for
            # container defaults.
            return self._resolve_path(key_path, default)

        return self.yaml_loader.get_nested(self.config, key_path, default)

    def _resolve_path(
        self, key_path: str, default: _ConfigValue
    ) -> _ConfigValue:
        """Manually resolve a dot-separated key path, returning *default* if not found."""
        keys = key_path.split(".")
        value: _ConfigValue = self.config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    # ========================================================================
    # PRIVATE TYPED ACCESSORS
    # ========================================================================

    def _get_int(self, key_path: str, default: int) -> int:
        """Retrieve a config value that must be an int."""
        value = self.get(key_path, default)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return default

    def _get_float(self, key_path: str, default: float) -> float:
        """Retrieve a config value that must be a float or int."""
        value = self.get(key_path, default)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return default

    def _get_str(self, key_path: str, default: str) -> str:
        """Retrieve a config value that must be a string."""
        value = self.get(key_path, default)
        if isinstance(value, str):
            return value
        return default

    def _get_dict(self, key_path: str, default: Optional[dict[str, _ConfigValue]] = None) -> dict[str, _ConfigValue]:
        """Retrieve a config value that must be a dict."""
        value = self.get(key_path, default if default is not None else {})
        if isinstance(value, dict):
            return value
        return default if default is not None else {}

    def _get_list(self, key_path: str, default: Optional[list[_ConfigValue]] = None) -> list[_ConfigValue]:
        """Retrieve a config value that must be a list."""
        value = self.get(key_path, default if default is not None else [])
        if isinstance(value, list):
            return value
        return default if default is not None else []

    # ========================================================================
    # COMMON PARAMETERS
    # ========================================================================

    def get_random_state(self) -> int:
        """Get random state seed for reproducibility."""
        return self._get_int("common.random_state", 42)

    def get_test_size(self) -> float:
        """Get train/test split ratio."""
        return self._get_float("common.test_size", 0.2)

    def get_cv_folds(self) -> int:
        """Get number of cross-validation folds."""
        return self._get_int("common.cv_folds", 5)

    def get_min_train_samples(self) -> int:
        """Get minimum samples required for training."""
        return self._get_int("common.min_train_samples", 100)

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
        if isinstance(max_workers, int) and not isinstance(max_workers, bool):
            return max_workers

        # Calculate from CPU count and multiplier
        multiplier = self._get_float("threading.worker_multiplier", 0.75)
        effective_cpu = cpu_count or 1
        return max(1, int(effective_cpu * multiplier))

    def get_batch_size(self) -> int:
        """Get batch size for parallel processing."""
        return self._get_int("threading.batch_size", 32)

    def get_task_timeout(self) -> int:
        """Get task timeout in seconds."""
        return self._get_int("threading.task_timeout", 300)

    # ========================================================================
    # MODEL PARAMETERS
    # ========================================================================

    def get_model_params(self, model_type: str) -> dict[str, _ConfigValue]:
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
        return self._get_dict(f"models.{model_type}")

    def get_random_forest_params(self) -> dict[str, _ConfigValue]:
        """Get Random Forest model parameters."""
        return self.get_model_params("random_forest")

    def get_xgboost_params(self) -> dict[str, _ConfigValue]:
        """Get XGBoost model parameters."""
        return self.get_model_params("xgboost")

    def get_lightgbm_params(self) -> dict[str, _ConfigValue]:
        """Get LightGBM model parameters."""
        return self.get_model_params("lightgbm")

    # ========================================================================
    # REINFORCEMENT LEARNING
    # ========================================================================

    def get_rl_environment_config(self) -> dict[str, _ConfigValue]:
        """Get RL environment configuration."""
        return self._get_dict("reinforcement_learning.environment")

    def get_rl_reward_config(self) -> dict[str, _ConfigValue]:
        """Get RL reward configuration."""
        return self._get_dict("reinforcement_learning.rewards")

    def get_rl_algorithm_params(self, algorithm: str) -> dict[str, _ConfigValue]:
        """
        Get RL algorithm parameters.

        Args:
            algorithm: Algorithm name (ppo, a2c, dqn, sac)

        Returns:
            Algorithm-specific parameters
        """
        return self._get_dict(f"reinforcement_learning.algorithms.{algorithm}")

    def get_rl_training_params(self) -> dict[str, _ConfigValue]:
        """Get RL training parameters."""
        return self._get_dict("reinforcement_learning.training")

    def get_rl_network_config(self) -> dict[str, _ConfigValue]:
        """Get RL network architecture configuration."""
        return self._get_dict("reinforcement_learning.network")

    # ========================================================================
    # THRESHOLD OPTIMIZATION
    # ========================================================================

    def get_threshold_config(self, indicator: str) -> dict[str, _ConfigValue]:
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
        return self._get_dict(f"threshold_optimization.{indicator}")

    def get_optimization_method(self) -> str:
        """Get optimization method (grid_search, random_search, bayesian)."""
        return self._get_str("threshold_optimization.optimization.method", "grid_search")

    def get_optimization_scoring(self) -> str:
        """Get optimization scoring metric."""
        return self._get_str("threshold_optimization.optimization.scoring", "sharpe")

    # ========================================================================
    # VALIDATION PARAMETERS
    # ========================================================================

    def get_walk_forward_config(self) -> dict[str, _ConfigValue]:
        """Get walk-forward validation configuration."""
        return self._get_dict("validation.walk_forward")

    def get_monte_carlo_config(self) -> dict[str, _ConfigValue]:
        """Get Monte Carlo validation configuration."""
        return self._get_dict("validation.monte_carlo")

    def get_validation_thresholds(self) -> dict[str, _ConfigValue]:
        """Get validation performance thresholds."""
        return self._get_dict("validation.thresholds")

    # ========================================================================
    # REPORTING CONFIGURATION
    # ========================================================================

    def get_output_directory(self) -> Path:
        """Get output directory for reports."""
        output_dir = self._get_str("reporting.output_directory", "reports")
        return Path(output_dir)

    def get_report_metrics(self, level: str = "basic") -> list[str]:
        """
        Get metrics to include in reports.

        Args:
            level: Metric level (basic, advanced, detailed)

        Returns:
            List of metric names
        """
        raw = self._get_list(f"reporting.metrics.{level}")
        result: list[str] = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
        return result

    def get_visualization_config(self) -> dict[str, _ConfigValue]:
        """Get visualization settings."""
        return self._get_dict("reporting.visualization")

    # ========================================================================
    # MEMORY MANAGEMENT
    # ========================================================================

    def get_memory_config(self) -> dict[str, _ConfigValue]:
        """Get memory management configuration."""
        return self._get_dict("memory")

    def get_max_results_in_memory(self) -> int:
        """Get maximum results to keep in memory."""
        return self._get_int("memory.max_results_in_memory", 500)

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
        param_config = self._get_dict(key_path)
        if not param_config:
            return True  # No range constraints

        min_val = param_config.get(min_key)
        max_val = param_config.get(max_key)

        if isinstance(min_val, (int, float)) and not isinstance(min_val, bool):
            if value < min_val:
                logger.warning(f"Value {value} below minimum {min_val} for {key_path}")
                return False

        if isinstance(max_val, (int, float)) and not isinstance(max_val, bool):
            if value > max_val:
                logger.warning(f"Value {value} above maximum {max_val} for {key_path}")
                return False

        return True

    def get_parameter_range(
        self, key_path: str, min_key: str = "min", max_key: str = "max"
    ) -> tuple[Optional[Union[int, float]], Optional[Union[int, float]], Optional[Union[int, float]]]:
        """
        Get parameter range from configuration.

        Args:
            key_path: Path to parameter configuration
            min_key: Key name for minimum value
            max_key: Key name for maximum value

        Returns:
            Tuple of (min_value, max_value, step) or (None, None, None)
        """
        param_config = self._get_dict(key_path)
        if not param_config:
            return (None, None, None)

        raw_min = param_config.get(min_key)
        raw_max = param_config.get(max_key)
        raw_step = param_config.get("step")

        min_val: Optional[Union[int, float]] = None
        max_val: Optional[Union[int, float]] = None
        step: Optional[Union[int, float]] = None

        if isinstance(raw_min, (int, float)) and not isinstance(raw_min, bool):
            min_val = raw_min
        if isinstance(raw_max, (int, float)) and not isinstance(raw_max, bool):
            max_val = raw_max
        if isinstance(raw_step, (int, float)) and not isinstance(raw_step, bool):
            step = raw_step

        return (min_val, max_val, step)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Singleton instance cache
_loaders: dict[tuple[Optional[str], Optional[str], Optional[Path]], ProfileConfigLoader] = {}


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


def get_common_params(
    profile: Optional[str] = None, tier: Optional[str] = None
) -> dict[str, _ConfigValue]:
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
) -> dict[str, _ConfigValue]:
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
) -> dict[str, _ConfigValue]:
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
) -> dict[str, _ConfigValue]:
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
    _loaders.clear()
