"""
Configuration loader for backtesting system.

This module provides centralized configuration loading from YAML files,
with support for backtest configuration, strategy parameters, and execution settings.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Union, cast

import yaml

from app.backtesting.models import BacktestConfig
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)

YamlValue = Union[str, int, float, bool, "YamlDict", list[object]]
YamlDict = dict[str, "YamlValue"]


def _ensure_dict(value: YamlValue) -> YamlDict:
    """Narrow a YamlValue to YamlDict, returning empty dict if not a dict."""
    if isinstance(value, dict):
        return value
    return {}


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""


class BacktestConfigLoader:
    """
    Load and manage backtesting configuration from YAML files.

    This class provides a clean interface for loading configuration from YAML
    files and creating BacktestConfig objects with proper validation.
    """

    def __init__(self, config_path: str):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to YAML configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        self.config_path = Path(config_path)
        self._raw_config: YamlDict = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with open(self.config_path) as f:
            loaded: object = yaml.safe_load(f)

        if isinstance(loaded, dict):
            self._raw_config = loaded
        else:
            self._raw_config = {}

        logger.debug(f"Loaded configuration from {self.config_path}")

    def _validate_positive_decimal(
        self,
        value: str | int | float | bool | Decimal | YamlDict | list[object],
        name: str,
        allow_zero: bool = False,
    ) -> Decimal:
        """
        Validate that a value is a positive Decimal.

        Args:
            value: Value to validate
            name: Parameter name for error messages
            allow_zero: Whether zero is allowed (default: False)

        Returns:
            Validated Decimal value

        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            decimal_value = Decimal(str(value))
        except (ValueError, TypeError) as e:
            raise ConfigValidationError(f"{name} must be a number, got: {value}") from e

        if decimal_value < 0:
            raise ConfigValidationError(f"{name} must be non-negative, got: {decimal_value}")

        if not allow_zero and decimal_value == 0:
            raise ConfigValidationError(f"{name} must be positive, got: {decimal_value}")

        return decimal_value

    def _validate_percentage(
        self,
        value: str | int | float | bool | Decimal | YamlDict | list[object],
        name: str,
        max_value: Decimal | None = None,
    ) -> Decimal:
        """
        Validate that a value is a percentage (0-100 or 0-1).

        Args:
            value: Value to validate
            name: Parameter name for error messages
            max_value: Maximum allowed value (default: 100 for percentages)

        Returns:
            Validated Decimal value

        Raises:
            ConfigValidationError: If validation fails
        """
        decimal_value = self._validate_positive_decimal(value, name, allow_zero=True)

        if max_value is None:
            max_value = Decimal("100")

        if decimal_value > max_value:
            raise ConfigValidationError(f"{name} must be <= {max_value}%, got: {decimal_value}")

        return decimal_value

    @property
    def raw_config(self) -> YamlDict:
        """Get raw configuration dictionary."""
        return self._raw_config

    def get_section(
        self,
        section: str,
        default: dict[str, str | int | float | bool | dict | list] | None = None,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get configuration section.

        Args:
            section: Section name (e.g., 'backtest', 'strategy', 'execution')
            default: Default value if section not found

        Returns:
            Configuration section as dictionary
        """
        value = self._raw_config.get(section, default or {})
        if isinstance(value, dict):
            return cast("dict[str, str | int | float | bool | dict | list]", value)
        return default or {}

    def get_backtest_config(self) -> BacktestConfig:
        """
        Create BacktestConfig from loaded YAML.

        Returns:
            BacktestConfig object with validated parameters

        Raises:
            ConfigValidationError: If required configuration is missing or invalid
        """
        config = _ensure_dict(self._raw_config.get("backtest", {}))
        input_config = _ensure_dict(self._raw_config.get("input", {}))

        # Get initial capital from input section if not in backtest section
        initial_capital_raw = config.get("initial_capital") or input_config.get(
            "initial_capital", 100000
        )

        # Validate all configuration parameters
        initial_capital = self._validate_positive_decimal(
            initial_capital_raw, "initial_capital", allow_zero=False
        )

        commission_per_trade = self._validate_positive_decimal(
            config.get("commission_per_trade", 1.0),
            "commission_per_trade",
            allow_zero=True,  # Zero commission is allowed
        )

        slippage_percentage = self._validate_percentage(
            config.get("slippage", 0.1),
            "slippage",
            max_value=Decimal("100"),  # Up to 100%
        )

        max_position_size = self._validate_percentage(
            config.get("max_position_size", 0.20),
            "max_position_size",
            max_value=Decimal("1"),  # 0-100% as decimal (0.0 to 1.0)
        )

        # Optional stop loss - support both stop_loss and stop_loss_pct keys
        stop_loss_raw = config.get("stop_loss") or config.get("stop_loss_pct")
        stop_loss_percentage = None
        if stop_loss_raw is not None:
            stop_loss_percentage = self._validate_percentage(
                stop_loss_raw, "stop_loss", max_value=Decimal("100")
            )

        # Optional take profit - support both take_profit and take_profit_pct keys
        take_profit_raw = config.get("take_profit") or config.get("take_profit_pct")
        take_profit_percentage = None
        if take_profit_raw is not None:
            take_profit_percentage = self._validate_positive_decimal(
                take_profit_raw, "take_profit", allow_zero=False
            )
            # Take profit can be any positive number (not really a percentage)

        # Risk free rate (can be 0 or negative for some markets)
        risk_free_rate_raw = config.get(
            "risk_free_rate", float(get_config().backtesting.default_risk_free_rate)
        )
        try:
            risk_free_rate = Decimal(str(risk_free_rate_raw))
        except (ValueError, TypeError) as e:
            raise ConfigValidationError(
                f"risk_free_rate must be a number, got: {risk_free_rate_raw}"
            ) from e

        return BacktestConfig(
            strategy_name=str(config.get("strategy_name", "default")),
            initial_capital=initial_capital,
            commission_per_trade=commission_per_trade,
            slippage_percentage=slippage_percentage,
            max_position_size=max_position_size,
            stop_loss_percentage=stop_loss_percentage,
            take_profit_percentage=take_profit_percentage,
            risk_free_rate=risk_free_rate,
        )

    def get_strategy_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get strategy configuration section.

        Returns:
            Strategy configuration dictionary
        """
        return self.get_section("strategy")

    def get_execution_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get execution configuration section.

        Returns:
            Execution configuration dictionary
        """
        return self.get_section("execution")

    def get_modules_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get modules configuration section.

        Returns:
            Modules configuration dictionary
        """
        return self.get_section("modules")

    def get_learning_engines_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get learning engines configuration section.

        Returns:
            Learning engines configuration dictionary
        """
        return self.get_section("learning_engines")

    def get_parallelization_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get parallelization configuration section.

        Returns:
            Parallelization configuration dictionary
        """
        return self.get_section("parallelization")

    def get_reporting_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get reporting configuration section.

        Returns:
            Reporting configuration dictionary
        """
        return self.get_section("reporting")

    def get_meta_analysis_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get meta-analysis configuration section.

        Returns:
            Meta-analysis configuration dictionary
        """
        return self.get_section("meta_analysis")

    def get_input_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get input configuration section.

        Returns:
            Input configuration dictionary
        """
        return self.get_section("input")

    def get_backtests_config(
        self,
    ) -> dict[str, str | int | float | bool | dict | list]:
        """
        Get backtests configuration section.

        Returns:
            Backtests configuration dictionary
        """
        return self.get_section("backtests")

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load()
        logger.info(f"Configuration reloaded from {self.config_path}")
