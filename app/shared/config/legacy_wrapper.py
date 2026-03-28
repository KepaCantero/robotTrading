"""
Legacy Configuration Wrapper

Provides backward-compatible Configuration class that wraps dict-based config.
Maintains existing API while delegating to new modular components.

TASK-24: SRP Compliance - Legacy wrapper for backward compatibility
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Configuration:
    """
    Configuration wrapper class for accessing configuration values.

    Provides convenient methods for accessing nested configuration values
    and updating configuration. This is a legacy wrapper maintained for
    backward compatibility.

    Args:
        config_dict: Dictionary containing configuration data

    Examples:
        >>> config = Configuration({'risk_management': {'atr_multipliers': {'default_stop': 2.0}}})
        >>> config.get_atr_multiplier('default_stop')
        2.0
    """

    def __init__(self, config_dict: Dict[str, object]):
        self._config = config_dict if config_dict is not None else {}
        self._lock = None  # For thread safety

    def get(self, key: str, default: Optional[object] = None) -> Optional[object]:
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
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: object) -> None:
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
        keys = key.split(".")
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
        return self.get(f"risk_management.atr_multipliers.{multiplier_name}")

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
        self.set(f"risk_management.atr_multipliers.{multiplier_name}", value)

    def get_risk_config(self) -> Dict[str, object]:
        """
        Get risk management configuration section.

        Returns:
            Risk management configuration dictionary

        Examples:
            >>> config = Configuration({'risk_management': {'atr_multipliers': {...}}})
            >>> risk_config = config.get_risk_config()
        """
        return self.get("risk_management", {})

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
        return self.get("trading.symbols", [])

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
            "start_date": self.get("backtesting.start_date", ""),
            "end_date": self.get("backtesting.end_date", ""),
        }
