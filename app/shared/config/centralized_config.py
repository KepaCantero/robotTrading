"""
Centralized Configuration System
TASK-10: Centralización de Configuración
TASK-24: SOLID Refactoring - OCP & SRP Compliance

This module provides a centralized configuration system that eliminates
magic values scattered throughout the codebase and centralizes all
thresholds and parameters.

REFACTORED STRUCTURE:
    - CentralizedConfig: Main facade aggregating all config groups
    - Protocol interfaces: app/shared/config/protocols.py
    - Loaders: app/shared/config/loaders.py
    - Validators: app/shared/config/validators.py
    - Mergers: app/shared/config/mergers.py
    - Cache: app/shared/config/cache.py
    - Legacy wrapper: app/shared/config/legacy_wrapper.py
    - Defaults: app/shared/config/defaults.py

SOLID COMPLIANCE:
    - SRP: Each module has single responsibility
    - OCP: Protocol interfaces allow extension without modification
    - LSP: All implementations follow protocols
    - ISP: Protocols are specific and focused
    - DIP: Depend on abstractions (protocols), not concretions
"""

import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

# Import extracted configuration groups (SRP)
from app.shared.config.params.backtest_config import BacktestingConfig
from app.shared.config.params.infrastructure_config import (
    APIConfig,
    DatabaseConfig,
    LoggingConfig,
    MonitoringConfig,
    RedisConfig,
)
from app.shared.config.params.risk_config import (
    ComplianceConfig,
    CurrencyHedgingConfig,
    SectorCountryDiversificationConfig,
)
from app.shared.config.params.shadow_mode_config import ShadowModeConfigParams
from app.shared.config.params.strategy_config import StrategyConfig
from app.shared.config.params.trading_thresholds import TradingThresholds
from app.shared.config.signal_risk import MarketMicrostructureThresholds

# Import modular components (OCP)
from app.shared.config.cache import FileBasedConfigCache
from app.shared.config.defaults import get_default_magic_values
from app.shared.config.legacy_wrapper import Configuration
from app.shared.config.loaders import ConfigLoaderRegistry
from app.shared.config.mergers import RecursiveConfigMerger
from app.shared.config.validators import CompositeConfigValidator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# SECTION 1: ENUMS & CONSTANTS
# =============================================================================


class Environment(str, Enum):
    """Environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


# =============================================================================
# SECTION 2: MAIN CONFIGURATION FACADE
#   - CentralizedConfig: Main configuration class that aggregates all sub-configs
#   - Follows Facade pattern to provide simple interface to complex subsystem
# =============================================================================


class CentralizedConfig(BaseSettings):
    """
    Centralized configuration facade for the entire application.

    This class aggregates all configuration groups and provides a unified
    interface. Each configuration group is responsible for its own validation
    and defaults (SRP).

    Configuration groups are imported from separate modules for better
    organization and maintainability.
    """

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Current environment"
    )
    debug: bool = Field(default=True, description="Debug mode")

    # Sub-configurations (each in separate module for SRP)
    trading: TradingThresholds = Field(
        default_factory=TradingThresholds, description="Trading thresholds"
    )
    backtesting: BacktestingConfig = Field(
        default_factory=BacktestingConfig, description="Backtesting configuration"
    )
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig, description="Database configuration"
    )
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    api: APIConfig = Field(default_factory=APIConfig, description="API configuration")
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    monitoring: MonitoringConfig = Field(
        default_factory=MonitoringConfig, description="Monitoring configuration"
    )
    currency_hedging: CurrencyHedgingConfig = Field(
        default_factory=CurrencyHedgingConfig, description="Currency hedging configuration"
    )
    diversification: SectorCountryDiversificationConfig = Field(
        default_factory=SectorCountryDiversificationConfig,
        description="Sector/country diversification configuration",
    )
    compliance: ComplianceConfig = Field(
        default_factory=ComplianceConfig, description="Compliance engine configuration"
    )
    shadow_mode: ShadowModeConfigParams = Field(
        default_factory=ShadowModeConfigParams, description="Shadow mode configuration"
    )
    market_microstructure: MarketMicrostructureThresholds = Field(
        default_factory=MarketMicrostructureThresholds,
        description="Market microstructure thresholds",
    )

    # Strategy configurations
    strategies: Dict[str, StrategyConfig] = Field(
        default_factory=dict, description="Strategy configurations"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra fields from .env not defined in model
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_strategy_configs()

    def _load_strategy_configs(self) -> None:
        """Load strategy configurations from YAML files."""
        strategies_dir = Path("config/strategies")
        logger.info(
            "Loading strategy configurations",
            extra={"strategies_dir": str(strategies_dir)},
        )

        if strategies_dir.exists():
            loaded_count = 0
            for strategy_file in strategies_dir.glob("*.yaml"):
                try:
                    with open(strategy_file, "r") as f:
                        strategy_data = yaml.safe_load(f)

                    strategy_name = strategy_file.stem

                    # Map strategy_name to name if exists (YAML compatibility)
                    if "strategy_name" in strategy_data and "name" not in strategy_data:
                        strategy_data["name"] = strategy_data.pop("strategy_name")
                    elif "name" not in strategy_data:
                        strategy_data["name"] = strategy_name

                    strategy_config = StrategyConfig(**strategy_data)
                    self.strategies[strategy_name] = strategy_config
                    loaded_count += 1

                    logger.debug(
                        f"Loaded strategy config: {strategy_name}",
                        extra={
                            "strategy_name": strategy_name,
                            "config_file": str(strategy_file),
                        },
                    )
                except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                    logger.warning(
                        f"Could not load strategy config from {strategy_file}: {e}",
                        extra={
                            "config_file": str(strategy_file),
                            "error_type": type(e).__name__,
                        },
                    )

            logger.info(
                f"Loaded {loaded_count} strategy configurations",
                extra={"loaded_count": loaded_count},
            )
        else:
            logger.debug(
                "Strategies directory does not exist, skipping strategy config loading"
            )

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def get_strategy_config(self, strategy_name: str) -> Optional[StrategyConfig]:
        """Get configuration for a specific strategy."""
        return self.strategies.get(strategy_name)

    @property
    def trading_thresholds(self) -> "TradingThresholds":
        """Alias for trading property - backwards compatibility."""
        return self.trading

    def get_trading_threshold(self, threshold_name: str) -> Any:
        """Get a specific trading threshold value."""
        if not hasattr(self.trading, threshold_name):
            raise AttributeError(f"Trading threshold '{threshold_name}' does not exist")
        return getattr(self.trading, threshold_name)

    def update_strategy_config(self, strategy_name: str, updates: Dict[str, Any]) -> bool:
        """Update configuration for a specific strategy."""
        if strategy_name in self.strategies:
            current_config = self.strategies[strategy_name]
            updated_data = current_config.model_dump()
            updated_data.update(updates)
            self.strategies[strategy_name] = StrategyConfig(**updated_data)
            return True
        else:
            # Create new strategy if it doesn't exist
            strategy_data = {"name": strategy_name, **updates}
            self.strategies[strategy_name] = StrategyConfig(**strategy_data)
            return True

    def validate_configuration(self) -> bool:
        """Validate the entire configuration."""
        logger.debug("Validating configuration")
        try:
            # Validate trading thresholds
            self.trading.model_validate(self.trading.model_dump())

            # Validate strategy configurations
            for _strategy_name, strategy_config in self.strategies.items():
                strategy_config.model_validate(strategy_config.model_dump())

            logger.info("Configuration validation passed")
            return True
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(
                f"Configuration validation failed: {e}",
                extra={"error_type": type(e).__name__},
            )
            return False

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        return {
            "environment": self.environment.value,
            "debug": self.debug,
            "trading_thresholds": {
                "min_signal_strength": self.trading.min_signal_strength,
                "min_signal_confidence": self.trading.min_signal_confidence,
                "min_liquidity_score": self.trading.min_liquidity_score,
                "max_position_size": self.trading.max_position_size,
                "stop_loss_pct": self.trading.stop_loss_pct,
                "take_profit_pct": self.trading.take_profit_pct,
            },
            "strategies": {
                "count": len(self.strategies),
                "enabled": [
                    name for name, config in self.strategies.items() if config.enabled
                ],
                "all": list(self.strategies.keys()),
            },
            "database": {
                "host": self.database.host,
                "port": self.database.port,
                "name": self.database.name,
            },
            "redis": {
                "host": self.redis.host,
                "port": self.redis.port,
                "db": self.redis.db,
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "workers": self.api.workers,
            },
        }


# =============================================================================
# SECTION 3: HELPER FUNCTIONS
#   - Global configuration instance management
#   - Convenience functions for common operations
# =============================================================================

# Global configuration instance
_config: Optional[CentralizedConfig] = None

# Modular components (OCP)
_loader_registry = ConfigLoaderRegistry()
_config_cache = FileBasedConfigCache()
_config_validator = CompositeConfigValidator()
_config_merger = RecursiveConfigMerger()


def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        logger.debug("Creating new global configuration instance")
        _config = CentralizedConfig()
        logger.info("Global configuration instance initialized")
    return _config


def get_trading_threshold(threshold_name: str = None) -> Any:
    """Get trading thresholds or specific threshold."""
    if threshold_name is None:
        return get_config().trading
    else:
        return get_config().get_trading_threshold(threshold_name)


def get_strategy_config(strategy_name: str) -> Optional[StrategyConfig]:
    """Get configuration for a specific strategy."""
    return get_config().strategies.get(strategy_name)


def get_compliance_config() -> ComplianceConfig:
    """Get compliance engine configuration."""
    return get_config().compliance


def get_strategy_stock_allocator_config(tier: Optional[str] = None) -> Dict[str, Any]:
    """
    Get Strategy Stock Allocator configuration.

    Args:
        tier: Capital tier for applying overrides

    Returns:
        Complete Strategy Stock Allocator configuration
    """
    from app.shared.config.config_loader import load_strategy_stock_allocator_config

    return load_strategy_stock_allocator_config(tier)


def reload_config() -> CentralizedConfig:
    """Reload the configuration from files."""
    global _config
    logger.info("Reloading configuration from files")
    _config = None
    config = get_config()
    logger.info("Configuration reloaded successfully")
    return config


def set_config(config: CentralizedConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def validate_config() -> bool:
    """Validate the current configuration."""
    return get_config().validate_configuration()


def get_config_summary() -> Dict[str, Any]:
    """Get a summary of the current configuration."""
    return get_config().get_config_summary()


def validate_configuration() -> bool:
    """Validate the current configuration (alias for validate_config)."""
    return validate_config()


def update_strategy_config(strategy_name: str, new_config: dict) -> bool:
    """Update strategy configuration."""
    config = get_config()
    return config.update_strategy_config(strategy_name, new_config)


# =============================================================================
# SECTION 4: CONFIGURATION LOADING UTILITIES
#   - Using modular loaders (OCP)
# =============================================================================


def load_config_from_yaml(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Dictionary containing configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If YAML is invalid
    """
    return _loader_registry.load(config_path)


def load_config_from_json(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to JSON configuration file

    Returns:
        Dictionary containing configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If JSON is invalid
    """
    return _loader_registry.load(config_path)


def load_config_with_cache(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration with caching support.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary (cached if available and valid)
    """
    # Check cache first
    cached = _config_cache.get_cached(config_path)
    if cached is not None:
        return cached

    # Load fresh configuration
    config = _loader_registry.load(config_path)

    # Cache the configuration
    _config_cache.set_cached(config_path, config)

    return config


# =============================================================================
# SECTION 5: CONFIGURATION VALIDATION UTILITIES
#   - Using modular validators (OCP)
# =============================================================================


def validate_atr_multipliers(atr_multipliers: Dict[str, float]) -> bool:
    """
    Validate ATR multiplier configuration.

    Args:
        atr_multipliers: Dictionary of ATR multiplier names to values

    Returns:
        True if all multipliers are positive, False otherwise
    """
    from app.shared.config.validators import ATRMultiplierValidator

    validator = ATRMultiplierValidator()
    return validator.validate(atr_multipliers)


def validate_risk_percentages(risk_config: Dict[str, float]) -> bool:
    """
    Validate risk percentage configuration.

    Args:
        risk_config: Dictionary of risk configuration values

    Returns:
        True if all percentages are between 0 and 1, False otherwise
    """
    from app.shared.config.validators import RiskPercentageValidator

    validator = RiskPercentageValidator()
    return validator.validate(risk_config)


def validate_trading_symbols(symbols: List[str]) -> bool:
    """
    Validate trading symbols list.

    Args:
        symbols: List of trading symbols

    Returns:
        True if symbols list is valid (non-empty, unique items), False otherwise
    """
    from app.shared.config.validators import TradingSymbolsValidator

    validator = TradingSymbolsValidator()
    return validator.validate({"symbols": symbols})


def validate_dates(backtest_config: Dict[str, str]) -> bool:
    """
    Validate backtesting date configuration.

    Args:
        backtest_config: Dictionary containing start_date and end_date

    Returns:
        True if dates are valid and in correct order, False otherwise
    """
    from app.shared.config.validators import DateRangeValidator

    validator = DateRangeValidator()
    return validator.validate(backtest_config)


def validate_config_object(config: Configuration) -> bool:
    """
    Validate complete configuration object.

    Args:
        config: Configuration object to validate

    Returns:
        True if configuration is valid, False otherwise
    """
    if not config or not hasattr(config, "_config"):
        return False

    return _config_validator.validate(config._config)


# =============================================================================
# SECTION 6: CONFIGURATION MERGING UTILITIES
#   - Using modular mergers (OCP)
# =============================================================================


def merge_configs(
    base_config: Dict[str, Any], override_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries recursively.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    return _config_merger.merge(base_config, override_config)


# =============================================================================
# SECTION 7: MIGRATION UTILITIES
#   - Helper functions for migrating magic values
# =============================================================================


def find_magic_values() -> Dict[str, List[str]]:
    """Find magic values in the codebase that should be moved to configuration."""
    return get_default_magic_values()


def migrate_magic_values(magic_values: Dict[str, List[str]]) -> bool:
    """Migrate magic values to centralized configuration."""
    # This would implement the migration logic
    # For now, return True
    return True


# =============================================================================
# SECTION 8: PROPERTY-BASED TEST HELPERS
#   - Helper functions for property-based testing
# =============================================================================


def get_atr_multiplier_positive_property(multiplier: float) -> bool:
    """
    Property-based test helper: ATR multiplier should be positive.

    Args:
        multiplier: ATR multiplier value to test

    Returns:
        True if multiplier is positive
    """
    return isinstance(multiplier, (int, float)) and multiplier > 0


def get_risk_percentage_bounds_property(risk_pct: float) -> bool:
    """
    Property-based test helper: Risk percentage should be between 0 and 1.

    Args:
        risk_pct: Risk percentage value to test

    Returns:
        True if risk_pct is between 0 and 1
    """
    return isinstance(risk_pct, (int, float)) and 0 < risk_pct <= 1.0


def get_symbols_list_property(symbols: List[str]) -> bool:
    """
    Property-based test helper: Symbols list should be valid.

    Args:
        symbols: List of symbols to test

    Returns:
        True if symbols list is valid
    """
    return validate_trading_symbols(symbols)


def get_date_order_property(start_date: str, end_date: str) -> bool:
    """
    Property-based test helper: End date should be after start date.

    Args:
        start_date: Start date string (YYYY-MM-DD format)
        end_date: End date string (YYYY-MM-DD format)

    Returns:
        True if end_date is after start_date
    """
    return validate_dates({"start_date": start_date, "end_date": end_date})


# =============================================================================
# SECTION 9: UPDATE HELPER FUNCTIONS
#   - Helper functions for updating configuration
# =============================================================================


def update_atr_multiplier(
    config: Configuration, multiplier_name: str, value: float
) -> None:
    """
    Update ATR multiplier in configuration.

    Args:
        config: Configuration object
        multiplier_name: Name of the ATR multiplier
        value: New value
    """
    config.set_atr_multiplier(multiplier_name, value)


def update_nested_value(
    config: Configuration, key_path: str, value: Any
) -> None:
    """
    Update nested configuration value.

    Args:
        config: Configuration object
        key_path: Dot-notation path to the value
        value: New value
    """
    config.set(key_path, value)


# =============================================================================
# SECTION 10: THREAD SAFETY UTILITIES
#   - Helper functions for thread-safe operations
# =============================================================================


def concurrent_read_access(config: Configuration, num_threads: int = 10) -> list:
    """
    Test concurrent read access to configuration.

    Args:
        config: Configuration object
        num_threads: Number of threads to use

    Returns:
        List of results from concurrent reads
    """
    import threading

    results = []

    def read_config():
        results.append(config.get_atr_multiplier("default_stop"))

    threads = [threading.Thread(target=read_config) for _ in range(num_threads)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    return results


# =============================================================================
# SECTION 11: INTEGRATION TEST FUNCTIONS
#   - Helper functions for integration testing
# =============================================================================


def full_config_workflow(config_path: Path) -> Dict[str, Any]:
    """
    Test complete configuration workflow: load, access, validate.

    Args:
        config_path: Path to configuration file

    Returns:
        Dictionary with workflow results
    """
    # Load from file
    config_dict = load_config_from_yaml(config_path)

    # Create configuration object
    config = Configuration(config_dict)

    # Access values
    atr_multiplier = config.get_atr_multiplier("default_stop")
    symbols = config.get_trading_symbols()
    dates = config.get_backtest_dates()

    # Validate
    is_valid = validate_config_object(config)

    return {
        "success": is_valid,
        "atr_multiplier": atr_multiplier,
        "symbols": symbols,
        "dates": dates,
    }


def config_with_validation(config_dict: Dict[str, Any]) -> tuple:
    """
    Create configuration and perform full validation.

    Args:
        config_dict: Configuration dictionary

    Returns:
        Tuple of (config_object, is_valid)
    """
    config = Configuration(config_dict)
    is_valid = validate_config_object(config)

    return config, is_valid


# =============================================================================
# SECTION 12: DEFAULT VALUE FUNCTIONS
#   - Re-exported from defaults module (SRP)
# =============================================================================

from app.shared.config.defaults import (
    get_default_atr_multiplier,
    get_default_max_position_size,
    get_default_risk_per_trade,
    get_default_stop_distance_pct,
)

# =============================================================================
# BACKWARD COMPATIBILITY
#   - Ensure all existing imports continue to work
# =============================================================================

# Re-export Configuration class for backward compatibility
__all__ = [
    # Main configuration
    "CentralizedConfig",
    "Environment",
    # Configuration groups (already in separate files)
    "TradingThresholds",
    "BacktestingConfig",
    "StrategyConfig",
    "DatabaseConfig",
    "RedisConfig",
    "APIConfig",
    "LoggingConfig",
    "MonitoringConfig",
    "CurrencyHedgingConfig",
    "SectorCountryDiversificationConfig",
    "ComplianceConfig",
    "ShadowModeConfigParams",
    "MarketMicrostructureThresholds",
    # Legacy wrapper
    "Configuration",
    # Helper functions
    "get_config",
    "get_trading_threshold",
    "get_strategy_config",
    "get_compliance_config",
    "get_strategy_stock_allocator_config",
    "reload_config",
    "set_config",
    "validate_config",
    "get_config_summary",
    "validate_configuration",
    "update_strategy_config",
    # Loading functions
    "load_config_from_yaml",
    "load_config_from_json",
    "load_config_with_cache",
    # Validation functions
    "validate_atr_multipliers",
    "validate_risk_percentages",
    "validate_trading_symbols",
    "validate_dates",
    "validate_config_object",
    # Merging functions
    "merge_configs",
    # Migration utilities
    "find_magic_values",
    "migrate_magic_values",
    # Property-based test helpers
    "get_atr_multiplier_positive_property",
    "get_risk_percentage_bounds_property",
    "get_symbols_list_property",
    "get_date_order_property",
    # Update helpers
    "update_atr_multiplier",
    "update_nested_value",
    # Thread safety
    "concurrent_read_access",
    # Integration test functions
    "full_config_workflow",
    "config_with_validation",
    # Default value functions
    "get_default_atr_multiplier",
    "get_default_risk_per_trade",
    "get_default_max_position_size",
    "get_default_stop_distance_pct",
]
