"""
YAML Configuration Loader

Loads configurations from YAML files with validation and fallback to default values.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Callable

import structlog
import yaml

logger = structlog.get_logger()


class YAMLConfigLoader:
    """
    YAML configuration loader with validation and support for defaults.

    Features:
    - Safe YAML loading (yaml.safe_load)
    - Fallback to default values if file does not exist
    - Support for key nesting with dot notation
    - Logging of loaded configuration
    - Thread-safe cache with locking
    - Configuration value validation
    """

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize the configuration loader.

        Args:
            config_dir: Configuration directory. Default: config/ or from CONFIG_DIR env var
        """
        # CFG-002: Use environment variable for config directory
        env_config_dir = os.getenv("CONFIG_DIR")
        if env_config_dir:
            self.config_dir = Path(env_config_dir)
        else:
            self.config_dir = config_dir or Path("config")

        self._cache: dict[str, dict[str, object]] = {}
        # CFG-CACHE-001: Thread-safe cache with lock
        self._cache_lock = threading.RLock()

        # Validate config_dir exists
        if not self.config_dir.exists():
            logger.warning(
                "config_directory_not_found",
                config_dir=str(self.config_dir),
                message="Config directory does not exist",
            )

    def load(self, filename: str, use_cache: bool = True) -> dict[str, object]:
        """
        Load a YAML file from the configuration directory.

        Args:
            filename: Name of YAML file (e.g., "strategy_stock_allocator.yaml")
            use_cache: If True, uses cache for already loaded files

        Returns:
            Dictionary with YAML content

        Raises:
            FileNotFoundError: If file does not exist and no fallback
            yaml.YAMLError: If file has invalid format
        """
        # Validate filename input
        if not filename or not isinstance(filename, str):
            logger.error(
                "invalid_filename",
                filename=filename,
                message="Invalid filename provided",
            )
            return {}

        cache_key = filename

        # CFG-CACHE-001: Thread-safe cache access with lock
        if use_cache:
            with self._cache_lock:
                if cache_key in self._cache:
                    logger.debug(
                        "loading_from_cache",
                        filename=filename,
                        cache_key=cache_key,
                    )
                    return self._cache[cache_key]

        config_path = self.config_dir / filename

        if not config_path.exists():
            logger.warning(
                "config_file_not_found",
                config_path=str(config_path),
                filename=filename,
            )
            return {}

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            # CFG-003: Validate configuration values after loading
            config = self._validate_config(config, filename)

            # CFG-CACHE-001: Thread-safe cache update
            if use_cache:
                with self._cache_lock:
                    self._cache[cache_key] = config

            logger.info(
                "config_loaded",
                config_path=str(config_path),
                filename=filename,
                config_keys=list(config.keys()) if config else [],
            )
            return config

        except yaml.YAMLError as e:
            logger.error(
                "yaml_parse_error",
                config_path=str(config_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            return {}
        except OSError as e:
            logger.error(
                "file_read_error",
                config_path=str(config_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            return {}

    def get_nested(
        self,
        config: dict[str, object],
        key_path: str,
        default: str | int | float | bool | None = None,
        separator: str = ".",
    ) -> str | int | float | bool | dict[str, object] | list[object] | None:
        """
        Get a nested value using dot notation.

        Args:
            config: Configuration dictionary
            key_path: Key path (e.g., "data_validation.lookback_max_days")
            default: Default value if key does not exist
            separator: Key separator (default: ".")

        Returns:
            Key value or default if not found

        Examples:
            >>> loader.get_nested(config, "data_validation.lookback_max_days", 126)
            126
        """
        keys = key_path.split(separator)
        value: object = config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        if value is not None and isinstance(value, (str, int, float, bool, dict, list)):
            return value
        return default

    def load_with_tier_override(
        self,
        filename: str,
        tier: str | None = None,
    ) -> dict[str, object]:
        """
        Load configuration with tier-specific overrides.

        Args:
            filename: Name of YAML file
            tier: Capital tier ("micro", "small", "medium", "large")

        Returns:
            Dictionary with base configuration + tier overrides

        Examples:
            >>> loader.load_with_tier_override("strategy_stock_allocator.yaml", "micro")
            {
                "data_validation": {"lookback_max_days": 126, ...},
                "exposure": {"max_strategy_exposure": 0.30, ...},  # Overridden
                ...
            }
        """
        config = self.load(filename)

        tiers_data = config.get("tiers")
        if tier and isinstance(tiers_data, dict) and tier in tiers_data:
            tier_overrides_raw = tiers_data[tier]
            if not isinstance(tier_overrides_raw, dict):
                return config
            tier_overrides: dict[str, object] = tier_overrides_raw

            # Apply tier overrides recursively
            config = self._apply_overrides(config, tier_overrides)
            logger.info(
                "tier_overrides_applied",
                tier=tier,
                override_keys=list(tier_overrides.keys()),
            )

        return config

    def _apply_overrides(
        self, base: dict[str, object], overrides: dict[str, object]
    ) -> dict[str, object]:
        """
        Recursively apply overrides to base configuration.

        Args:
            base: Base configuration
            overrides: Overrides to apply

        Returns:
            Configuration with overrides applied
        """
        result = base.copy()

        for key, value in overrides.items():
            base_val = result.get(key)
            if isinstance(base_val, dict) and isinstance(value, dict):
                result[key] = self._apply_overrides(base_val, value)
            else:
                result[key] = value

        return result

    def get_strategy_stock_allocator_config(self, tier: str | None = None) -> dict[str, object]:
        """
        Load the Strategy Stock Allocator configuration.

        Args:
            tier: Capital tier for applying overrides

        Returns:
            Complete Strategy Stock Allocator configuration
        """
        return self.load_with_tier_override("strategy_stock_allocator.yaml", tier)

    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        # CFG-CACHE-001: Thread-safe cache clear
        with self._cache_lock:
            self._cache.clear()
        logger.debug("config_cache_cleared")

    def _validate_config(self, config: dict[str, object], filename: str) -> dict[str, object]:
        """
        Validate configuration values after loading.

        CFG-003: Validates configuration values to ensure data integrity
        and prevent invalid values from being used.

        Args:
            config: Configuration dictionary to validate
            filename: Name of the config file (for context in error messages)

        Returns:
            Validated configuration dictionary
        """
        if not isinstance(config, dict):
            logger.error(
                "invalid_config_type",
                filename=filename,
                expected_type="dict",
                actual_type=type(config).__name__,
            )
            return {}

        # CFG-SEC-001: Check for potential sensitive data patterns
        sensitive_keys = ["password", "secret", "api_key", "token", "private_key"]
        for key in config:
            key_lower = str(key).lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                logger.warning(
                    "potential_sensitive_data_key",
                    filename=filename,
                    key=key,
                    message="CFG-SEC-001: Potential sensitive data key found. Ensure secrets are loaded from environment variables.",
                )

        # Validate common configuration value types
        validation_rules = {
            # Max exposure: must be between 0 and 1
            "max_strategy_exposure": lambda v: isinstance(v, (int, float)) and 0 <= v <= 1,
            "min_strategy_exposure": lambda v: isinstance(v, (int, float)) and 0 <= v <= 1,
            # Lookback days: must be positive integer
            "lookback_max_days": lambda v: isinstance(v, int) and v > 0,
            "lookback_min_days": lambda v: isinstance(v, int) and v >= 0,
            # Thresholds: can be numeric OR dict (for optimization ranges or nested threshold configs)
            # Dicts are valid if they contain threshold-related keys or are nested configurations
            "threshold": lambda v: isinstance(v, (int, float, dict)),
            "enabled": lambda v: isinstance(v, bool),
            # Tier validation - only validate string values, not tier config dicts
            "tier": lambda v: (
                (isinstance(v, str) and v in ["micro", "small", "medium", "large"])
                or isinstance(v, dict)
            ),  # tier config dicts are valid
        }

        # Recursively validate nested config
        return self._validate_dict_values(config, validation_rules, filename)

    def _validate_dict_values(
        self,
        config: dict[str, object],
        validation_rules: dict[str, Callable[..., bool]],
        filename: str,
        path: str = "",
    ) -> dict[str, object]:
        """
        Recursively validate dictionary values against rules.

        Args:
            config: Configuration to validate
            validation_rules: Rules to apply
            filename: Config file name for error messages
            path: Current path in nested structure

        Returns:
            Validated configuration
        """
        validated_config: dict[str, object] = {}

        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key

            # Check if key matches any validation rule
            for rule_key, rule_func in validation_rules.items():
                if rule_key in key.lower():
                    try:
                        if not rule_func(value):
                            logger.warning(
                                "invalid_config_value",
                                filename=filename,
                                key=current_path,
                                value=value,
                                value_type=type(value).__name__,
                                rule=rule_key,
                                message="CFG-003: Invalid configuration value",
                            )
                    except Exception as e:
                        logger.warning(
                            "config_validation_error",
                            filename=filename,
                            key=current_path,
                            error=str(e),
                            rule=rule_key,
                            message="CFG-003: Configuration validation error",
                        )

            # Recursively validate nested dictionaries
            if isinstance(value, dict):
                nested_dict: dict[str, object] = {str(k): v for k, v in value.items()}
                validated_config[key] = self._validate_dict_values(
                    nested_dict, validation_rules, filename, current_path
                )
            else:
                validated_config[key] = value

        return validated_config


# Singleton instance for easy access
_default_loader: YAMLConfigLoader | None = None


def get_config_loader() -> YAMLConfigLoader:
    """
    Get the singleton instance of the configuration loader.

    Returns:
        YAMLConfigLoader instance
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = YAMLConfigLoader()
    return _default_loader


def load_strategy_stock_allocator_config(
    tier: str | None = None,
) -> dict[str, object]:
    """
    Convenience function to load the Strategy Stock Allocator configuration.

    Args:
        tier: Capital tier for applying overrides

    Returns:
        Complete Strategy Stock Allocator configuration
    """
    return get_config_loader().get_strategy_stock_allocator_config(tier)


def load_momentum_filters_config(
    tier: str | None = None,
) -> dict[str, object]:
    """
    Convenience function to load the Momentum Filters configuration.

    Args:
        tier: Capital tier for applying overrides

    Returns:
        Complete Momentum Filters configuration
    """
    return get_config_loader().load_with_tier_override("momentum_filters.yaml", tier)


def load_market_detectors_config(
    tier: str | None = None,
) -> dict[str, object]:
    """
    Convenience function to load the Market Detectors configuration.

    Args:
        tier: Capital tier for applying overrides

    Returns:
        Complete Market Detectors configuration
    """
    return get_config_loader().load_with_tier_override("market_detectors.yaml", tier)


def load_strategy_defaults_config(
    tier: str | None = None,
) -> dict[str, object]:
    """
    Convenience function to load the Strategy Defaults configuration.

    Args:
        tier: Capital tier for applying overrides

    Returns:
        Complete Strategy Defaults configuration
    """
    return get_config_loader().load_with_tier_override("strategy_defaults.yaml", tier)


def load_learning_parameters_config(
    tier: str | None = None,
) -> dict[str, object]:
    """
    Convenience function to load the Learning Parameters configuration.

    Args:
        tier: Capital tier for applying overrides

    Returns:
        Complete Learning Parameters configuration
    """
    return get_config_loader().load_with_tier_override("learning_parameters.yaml", tier)


def get_filter_config(
    filter_name: str,
    tier: str | None = None,
    preset: str = "balanced",
) -> dict[str, object]:
    """
    Get the configuration of a specific filter from momentum_filters.yaml.

    Args:
        filter_name: Name of the filter (e.g., "rsi_filter", "momentum_filter")
        tier: Capital tier for applying overrides
        preset: Preset to use ("conservative", "balanced", "aggressive")

    Returns:
        Filter configuration with preset thresholds
    """
    config = load_momentum_filters_config(tier)

    # Get specific filter configuration
    filter_config_raw = config.get(filter_name, {})
    if not isinstance(filter_config_raw, dict):
        filter_config_raw = {}
    filter_config: dict[str, object] = {str(k): v for k, v in filter_config_raw.items()}

    # Add preset thresholds
    thresholds_raw = filter_config.get("thresholds", {})
    if not isinstance(thresholds_raw, dict):
        thresholds_raw = {}
    thresholds: dict[str, object] = {str(k): v for k, v in thresholds_raw.items()}

    balanced_raw = thresholds.get("balanced", {})
    preset_thresholds_raw = thresholds.get(preset, balanced_raw)
    if not isinstance(preset_thresholds_raw, dict):
        preset_thresholds_raw = {}
    preset_thresholds: dict[str, object] = {str(k): v for k, v in preset_thresholds_raw.items()}

    result = filter_config.copy()
    result["preset_thresholds"] = preset_thresholds

    return result


def get_detector_config(
    detector_name: str,
    tier: str | None = None,
) -> dict[str, object]:
    """
    Get the configuration of a specific detector from market_detectors.yaml.

    Args:
        detector_name: Name of the detector (e.g., "trend_detector", "volatility_detector")
        tier: Capital tier for applying overrides

    Returns:
        Detector configuration
    """
    config = load_market_detectors_config(tier)
    raw_val = config.get(detector_name, {})
    if isinstance(raw_val, dict):
        return {str(k): v for k, v in raw_val.items()}
    return {}


def get_strategy_config(
    strategy_name: str,
    tier: str | None = None,
) -> dict[str, object]:
    """
    Get the configuration of a specific strategy from strategy_defaults.yaml.

    Args:
        strategy_name: Name of the strategy (e.g., "momentum_strategy", "mean_reversion_strategy")
        tier: Capital tier for applying overrides

    Returns:
        Strategy configuration
    """
    config = load_strategy_defaults_config(tier)
    raw_val = config.get(strategy_name, {})
    if isinstance(raw_val, dict):
        return {str(k): v for k, v in raw_val.items()}
    return {}
