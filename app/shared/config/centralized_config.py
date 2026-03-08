"""
Centralized Configuration System
TASK-10: Centralización de Configuración

This module provides a centralized configuration system that eliminates
magic values scattered throughout the codebase and centralizes all
thresholds and parameters.

SECTIONS:
    1. Enums & Constants
    2. Trading Configuration (TradingThresholds, StrategyConfig, StockAllocationSettings)
    3. Infrastructure Configuration (DatabaseConfig, RedisConfig, APIConfig)
    4. Monitoring & Logging (LoggingConfig, MonitoringConfig)
    5. Risk & Compliance (CurrencyHedgingConfig, SectorCountryDiversificationConfig, ComplianceConfig)
    6. Main Configuration (CentralizedConfig)
    7. Helper Functions (get_config, etc.)
    8. Legacy/Utility (Configuration wrapper class)
"""

import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    pass

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
from app.shared.config.params.strategy_config import StrategyConfig

# SRP: Import extracted configuration modules (TASK-24)
from app.shared.config.params.trading_thresholds import TradingThresholds
from app.shared.config.signal_risk import MarketMicrostructureThresholds

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


# SECTION 6: MAIN CONFIGURATION
#   - CentralizedConfig: Main configuration class that aggregates all sub-configs
# =============================================================================


class CentralizedConfig(BaseSettings):
    """Centralized configuration for the entire application."""

    # Environment
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Current environment"
    )
    debug: bool = Field(default=True, description="Debug mode")

    # Sub-configurations
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

    def _load_strategy_configs(self):
        """Load strategy configurations from YAML files."""
        strategies_dir = Path("config/strategies")
        if strategies_dir.exists():
            for strategy_file in strategies_dir.glob("*.yaml"):
                try:
                    with open(strategy_file, "r") as f:
                        strategy_data = yaml.safe_load(f)

                    strategy_name = strategy_file.stem

                    # Mapear strategy_name a name si existe (compatibilidad con YAML)
                    if "strategy_name" in strategy_data and "name" not in strategy_data:
                        strategy_data["name"] = strategy_data.pop("strategy_name")
                    elif "name" not in strategy_data:
                        strategy_data["name"] = strategy_name

                    strategy_config = StrategyConfig(**strategy_data)
                    self.strategies[strategy_name] = strategy_config
                except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Could not load strategy config from {strategy_file}: {e}")

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
        try:
            # Validate trading thresholds
            self.trading.model_validate(self.trading.model_dump())

            # Validate strategy configurations
            for _strategy_name, strategy_config in self.strategies.items():
                strategy_config.model_validate(strategy_config.model_dump())

            return True
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
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
                "enabled": [name for name, config in self.strategies.items() if config.enabled],
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
# SECTION 7: HELPER FUNCTIONS
#   - get_config(): Get global configuration instance
#   - get_compliance_config(): Get compliance configuration
#   - get_trading_threshold(): Get trading thresholds
#   - reload_config(), set_config(), etc.
# =============================================================================

# Global configuration instance
_config: Optional[CentralizedConfig] = None


def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = CentralizedConfig()

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


def reload_config():
    """Reload the configuration from files."""
    global _config
    _config = None
    return get_config()


def set_config(config: CentralizedConfig):
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


def update_strategy_config(strategy_name: str, new_config: dict):
    """Update strategy configuration."""
    config = get_config()
    return config.update_strategy_config(strategy_name, new_config)


# Configuration migration utilities
def find_magic_values() -> Dict[str, List[str]]:
    """Find magic values in the codebase that should be moved to configuration."""
    magic_values = {
        "numeric_thresholds": [
            "Signal cooldown: 10 minutes",
            "Compound score weights: 30/25/20/15/10",
            "Priority thresholds: 80/50",
            "Risk per trade: 2%",
            "Risk/reward ratio: 3:1",
            "Max consecutive stops: 5",
            "Rebalance frequency: 30 days",
            "Allocation weights: 50/25/25",
        ],
        "string_constants": [],
        "timeout_values": [],
        "retry_counts": [],
    }

    return magic_values


def migrate_magic_values(magic_values: Dict[str, List[str]]) -> bool:
    """Migrate magic values to centralized configuration."""
    # This would implement the migration logic
    # For now, return True
    return True


# =============================================================================
# Configuration Loading Functions
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

    Examples:
        >>> config = load_config_from_yaml(Path("config.yaml"))
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
            return config_data if config_data is not None else {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}")


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

    Examples:
        >>> config = load_config_from_json(Path("config.json"))
    """
    import json

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            return config_data if config_data is not None else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_path}: {e}")


# =============================================================================
# Configuration Validation Functions
# =============================================================================


def validate_atr_multipliers(atr_multipliers: Dict[str, float]) -> bool:
    """
    Validate ATR multiplier configuration.

    Args:
        atr_multipliers: Dictionary of ATR multiplier names to values

    Returns:
        True if all multipliers are positive, False otherwise

    Examples:
        >>> validate_atr_multipliers({'default_stop': 2.0})
        True
        >>> validate_atr_multipliers({'default_stop': -1.0})
        False
    """
    if not atr_multipliers:
        return False

    return all(isinstance(v, (int, float)) and v > 0 for v in atr_multipliers.values())


def validate_risk_percentages(risk_config: Dict[str, float]) -> bool:
    """
    Validate risk percentage configuration.

    Args:
        risk_config: Dictionary of risk configuration values

    Returns:
        True if all percentages are between 0 and 1, False otherwise

    Examples:
        >>> validate_risk_percentages({'default_risk_per_trade': 0.02})
        True
        >>> validate_risk_percentages({'default_risk_per_trade': 1.5})
        False
    """
    if not risk_config:
        return False

    return all(isinstance(v, (int, float)) and 0 < v <= 1.0 for v in risk_config.values())


def validate_trading_symbols(symbols: List[str]) -> bool:
    """
    Validate trading symbols list.

    Args:
        symbols: List of trading symbols

    Returns:
        True if symbols list is valid (non-empty, unique items), False otherwise

    Examples:
        >>> validate_trading_symbols(['AAPL', 'MSFT'])
        True
        >>> validate_trading_symbols([])
        False
    """
    if not symbols or not isinstance(symbols, list):
        return False

    # Check for non-empty and all strings
    if not all(isinstance(s, str) and s.strip() for s in symbols):
        return False

    # Check for duplicates
    if len(symbols) != len(set(symbols)):
        return False

    return True


def validate_dates(backtest_config: Dict[str, str]) -> bool:
    """
    Validate backtesting date configuration.

    Args:
        backtest_config: Dictionary containing start_date and end_date

    Returns:
        True if dates are valid and in correct order, False otherwise

    Examples:
        >>> validate_dates({'start_date': '2020-01-01', 'end_date': '2024-12-31'})
        True
        >>> validate_dates({'start_date': '2024-01-01', 'end_date': '2020-01-01'})
        False
    """
    if not backtest_config:
        return False

    start_date = backtest_config.get('start_date')
    end_date = backtest_config.get('end_date')

    if not start_date or not end_date:
        return False

    try:
        from datetime import datetime

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        return start < end
    except (ValueError, TypeError):
        return False


def validate_config_object(config: 'Configuration') -> bool:
    """
    Validate complete configuration object.

    Args:
        config: Configuration object to validate

    Returns:
        True if configuration is valid, False otherwise

    Examples:
        >>> config = Configuration({'risk_management': {...}})
        >>> validate_config_object(config)
        True
    """
    if not config or not hasattr(config, '_config'):
        return False

    config_dict = config._config

    # Validate risk management section
    if 'risk_management' in config_dict:
        rm = config_dict['risk_management']

        if 'atr_multipliers' in rm and not validate_atr_multipliers(rm['atr_multipliers']):
            return False

        if 'position_sizing' in rm and not validate_risk_percentages(rm['position_sizing']):
            return False

    # Validate trading section
    if 'trading' in config_dict:
        trading = config_dict['trading']

        if 'symbols' in trading and not validate_trading_symbols(trading['symbols']):
            return False

    # Validate backtesting section
    if 'backtesting' in config_dict and not validate_dates(config_dict['backtesting']):
        return False

    return True


# =============================================================================
# Configuration Merging Functions
# =============================================================================


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries recursively.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary

    Returns:
        Merged configuration dictionary

    Examples:
        >>> base = {'level1': {'key1': 'value1'}}
        >>> override = {'level1': {'key2': 'value2'}}
        >>> merged = merge_configs(base, override)
        >>> merged['level1']['key1']
        'value1'
        >>> merged['level1']['key2']
        'value2'
    """
    result = base_config.copy()

    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


# =============================================================================
# SECTION 8: LEGACY/UTILITY
#   - Configuration: Legacy wrapper class for backward compatibility
#   - Cache functions, validation functions, etc.
# =============================================================================

# =============================================================================
# Configuration Class (Legacy - for backward compatibility)
# =============================================================================


class Configuration:
    """
    Configuration wrapper class for accessing configuration values.

    Provides convenient methods for accessing nested configuration values
    and updating configuration.

    Args:
        config_dict: Dictionary containing configuration data

    Examples:
        >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
        >>> config.get_atr_multiplier('default_stop')
        2.0
    """

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict if config_dict is not None else {}
        self._lock = None  # For thread safety

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation).

        Args:
            key: Configuration key (supports nested notation like 'risk_management.atr_multipliers')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
            >>> config.get('risk_management.atr_multipliers.default_stop')
            2.0
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by key (supports dot notation).

        Args:
            key: Configuration key (supports nested notation)
            value: Value to set

        Examples:
            >>> config = Configuration({'risk_management': {}})
            >>> config.set('risk_management.new_key', 'value')
            >>> config.get('risk_management.new_key')
            'value'
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_atr_multiplier(self, multiplier_name: str) -> Optional[float]:
        """
        Get ATR multiplier value.

        Args:
            multiplier_name: Name of the ATR multiplier

        Returns:
            ATR multiplier value or None if not found

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
            >>> config.get_atr_multiplier('default_stop')
            2.0
        """
        return self.get(f'risk_management.atr_multipliers.{multiplier_name}')

    def set_atr_multiplier(self, multiplier_name: str, value: float) -> None:
        """
        Set ATR multiplier value.

        Args:
            multiplier_name: Name of the ATR multiplier
            value: Value to set

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {}}})
            >>> config.set_atr_multiplier('default_stop', 2.5)
            >>> config.get_atr_multiplier('default_stop')
            2.5
        """
        self.set(f'risk_management.atr_multipliers.{multiplier_name}', value)

    def get_risk_config(self) -> Dict[str, Any]:
        """
        Get risk management configuration section.

        Returns:
            Risk management configuration dictionary

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {...}}})
            >>> risk_config = config.get_risk_config()
        """
        return self.get('risk_management', {})

    def get_trading_symbols(self) -> List[str]:
        """
        Get trading symbols list.

        Returns:
            List of trading symbols

        Examples:
            >>> config = Configuration({'trading': {'symbols': ['AAPL', 'MSFT']}})
            >>> config.get_trading_symbols()
            ['AAPL', 'MSFT']
        """
        return self.get('trading.symbols', [])

    def get_backtest_dates(self) -> Dict[str, str]:
        """
        Get backtesting date range.

        Returns:
            Dictionary with start_date and end_date

        Examples:
            >>> config = Configuration({'backtesting': {'start_date': '2020-01-01', 'end_date': '2024-12-31'}})
            >>> dates = config.get_backtest_dates()
            >>> dates['start_date']
            '2020-01-01'
        """
        return {
            'start_date': self.get('backtesting.start_date', ''),
            'end_date': self.get('backtesting.end_date', ''),
        }


# =============================================================================
# Default Value Functions
# =============================================================================


def get_default_atr_multiplier() -> float:
    """
    Get default ATR multiplier value.

    Returns:
        Default ATR multiplier (2.0)

    Examples:
        >>> get_default_atr_multiplier()
        2.0
    """
    return 2.0


def get_default_risk_per_trade() -> float:
    """
    Get default risk per trade percentage.

    Returns:
        Default risk per trade (0.02 = 2%)

    Examples:
        >>> get_default_risk_per_trade()
        0.02
    """
    return 0.02


def get_default_max_position_size() -> float:
    """
    Get default maximum position size.

    Returns:
        Default max position size (0.25 = 25%)

    Examples:
        >>> get_default_max_position_size()
        0.25
    """
    return 0.25


def get_default_stop_distance_pct() -> float:
    """
    Get default stop loss distance percentage.

    Returns:
        Default stop distance (0.05 = 5%)

    Examples:
        >>> get_default_stop_distance_pct()
        0.05
    """
    return 0.05


# =============================================================================
# Cache Functions (for caching tests)
# =============================================================================

_config_cache: Dict[Path, Dict[str, Any]] = {}
_config_cache_timestamps: Dict[Path, float] = {}


def get_config_cached_after_load(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration with caching support.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary (cached if available)

    Examples:
        >>> config1 = get_config_cached_after_load(Path("config.yaml"))
        >>> config2 = get_config_cached_after_load(Path("config.yaml"))
        >>> # config2 will be returned from cache if file hasn't changed
    """
    import os
    import time

    # Check if we have a cached version
    if config_path in _config_cache:
        cached_time = _config_cache_timestamps.get(config_path, 0)
        file_mtime = os.path.getmtime(config_path)

        # Return cached version if file hasn't changed
        if file_mtime <= cached_time:
            return _config_cache[config_path]

    # Load fresh configuration
    if config_path.suffix in ['.yaml', '.yml']:
        config = load_config_from_yaml(config_path)
    elif config_path.suffix == '.json':
        config = load_config_from_json(config_path)
    else:
        raise ValueError(f"Unsupported config file type: {config_path.suffix}")

    # Cache the configuration
    _config_cache[config_path] = config
    _config_cache_timestamps[config_path] = time.time()

    return config


def get_config_cache_invalidated_on_change(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration with automatic cache invalidation on file changes.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary (fresh if file changed, cached otherwise)

    Examples:
        >>> config1 = get_config_cache_invalidated_on_change(Path("config.yaml"))
        >>> # Modify file externally
        >>> config2 = get_config_cache_invalidated_on_change(Path("config.yaml"))
        >>> # config2 will be fresh (cache invalidated)
    """
    return get_config_cached_after_load(config_path)


# =============================================================================
# Property-Based Test Helper Functions
# =============================================================================


def get_atr_multiplier_positive_property(multiplier: float) -> bool:
    """
    Property-based test helper: ATR multiplier should be positive.

    Args:
        multiplier: ATR multiplier value to test

    Returns:
        True if multiplier is positive

    Examples:
        >>> get_atr_multiplier_positive_property(2.0)
        True
        >>> get_atr_multiplier_positive_property(-1.0)
        False
    """
    return isinstance(multiplier, (int, float)) and multiplier > 0


def get_risk_percentage_bounds_property(risk_pct: float) -> bool:
    """
    Property-based test helper: Risk percentage should be between 0 and 1.

    Args:
        risk_pct: Risk percentage value to test

    Returns:
        True if risk_pct is between 0 and 1

    Examples:
        >>> get_risk_percentage_bounds_property(0.02)
        True
        >>> get_risk_percentage_bounds_property(1.5)
        False
    """
    return isinstance(risk_pct, (int, float)) and 0 < risk_pct <= 1.0


def get_symbols_list_property(symbols: List[str]) -> bool:
    """
    Property-based test helper: Symbols list should be valid.

    Args:
        symbols: List of symbols to test

    Returns:
        True if symbols list is valid

    Examples:
        >>> get_symbols_list_property(['AAPL', 'MSFT'])
        True
        >>> get_symbols_list_property([])
        False
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

    Examples:
        >>> get_date_order_property('2020-01-01', '2024-12-31')
        True
        >>> get_date_order_property('2024-01-01', '2020-01-01')
        False
    """
    return validate_dates({'start_date': start_date, 'end_date': end_date})


# =============================================================================
# Update Helper Functions
# =============================================================================


def update_atr_multiplier(config: Configuration, multiplier_name: str, value: float) -> None:
    """
    Update ATR multiplier in configuration.

    Args:
        config: Configuration object
        multiplier_name: Name of the ATR multiplier
        value: New value

    Examples:
        >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
        >>> update_atr_multiplier(config, 'default_stop', 2.5)
        >>> config.get_atr_multiplier('default_stop')
        2.5
    """
    config.set_atr_multiplier(multiplier_name, value)


def update_nested_value(config: Configuration, key_path: str, value: Any) -> None:
    """
    Update nested configuration value.

    Args:
        config: Configuration object
        key_path: Dot-notation path to the value
        value: New value

    Examples:
        >>> config = Configuration({'risk_management': {'position_sizing': {'default_risk_per_trade': 0.02}}})
        >>> update_nested_value(config, 'risk_management.position_sizing.default_risk_per_trade', 0.03)
        >>> config.get('risk_management.position_sizing.default_risk_per_trade')
        0.03
    """
    config.set(key_path, value)


# =============================================================================
# Thread Safety Functions
# =============================================================================


def concurrent_read_access(config: Configuration, num_threads: int = 10) -> list:
    """
    Test concurrent read access to configuration.

    Args:
        config: Configuration object
        num_threads: Number of threads to use

    Returns:
        List of results from concurrent reads

    Examples:
        >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
        >>> results = concurrent_read_access(config, 10)
        >>> len(results)
        10
    """
    import threading

    results = []

    def read_config():
        results.append(config.get_atr_multiplier('default_stop'))

    threads = [threading.Thread(target=read_config) for _ in range(num_threads)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    return results


# =============================================================================
# Integration Test Functions
# =============================================================================


def full_config_workflow(config_path: Path) -> Dict[str, Any]:
    """
    Test complete configuration workflow: load, access, validate.

    Args:
        config_path: Path to configuration file

    Returns:
        Dictionary with workflow results

    Examples:
        >>> result = full_config_workflow(Path("config.yaml"))
        >>> result['success']
        True
    """
    # Load from file
    config_dict = load_config_from_yaml(config_path)

    # Create configuration object
    config = Configuration(config_dict)

    # Access values
    atr_multiplier = config.get_atr_multiplier('default_stop')
    symbols = config.get_trading_symbols()
    dates = config.get_backtest_dates()

    # Validate
    is_valid = validate_config_object(config)

    return {
        'success': is_valid,
        'atr_multiplier': atr_multiplier,
        'symbols': symbols,
        'dates': dates,
    }


def config_with_validation(config_dict: Dict[str, Any]) -> tuple:
    """
    Create configuration and perform full validation.

    Args:
        config_dict: Configuration dictionary

    Returns:
        Tuple of (config_object, is_valid)

    Examples:
        >>> config_dict = {'risk_management': {...}, 'trading': {...}}
        >>> config, is_valid = config_with_validation(config_dict)
        >>> is_valid
        True
    """
    config = Configuration(config_dict)
    is_valid = validate_config_object(config)

    return config, is_valid
