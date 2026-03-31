"""
Strategy Factory Module for Backtesting

This module provides centralized strategy creation and configuration,
extracting this responsibility from ComprehensiveBacktestRunner to reduce
God Object anti-pattern.

Responsibilities:
- Create strategy instances from configuration
- Extract strategy parameters
- Get strategy metadata (name, thresholds)

This follows the Factory pattern for better separation of concerns.
"""

from __future__ import annotations

import logging
from typing import ClassVar, Optional, Union, cast

from app.domain.strategies.mean_reversion import MeanReversionStrategy
from app.domain.strategies.momentum import MomentumStrategy

# from app.domain.strategies.momentum_modular.strategy import ModularMomentumStrategy  # TODO: Create module
from app.domain.strategies.pairs_trading import PairsTrading as PairsTradingStrategy

logger = logging.getLogger(__name__)

# Temporary alias until momentum_modular is created
ModularMomentumStrategy = MomentumStrategy

# Type alias for the deeply-nested config value type used throughout this module
ConfigValue = Union[str, int, float, bool, list, dict]
ConfigDict = dict[str, ConfigValue]


def _extract_nested_dict(parent: ConfigDict, key: str) -> ConfigDict:
    """Extract a nested dict value from a config dict, defaulting to empty dict."""
    raw = parent.get(key, {})
    if isinstance(raw, dict):
        return cast("ConfigDict", raw)
    return {}


class StrategyFactory:
    """
    Factory for creating trading strategies from configuration.

    Extracted from ComprehensiveBacktestRunner to follow Single Responsibility Principle.
    """

    # Strategy type mapping
    STRATEGY_CLASSES: ClassVar[dict[str, type]] = {
        "mean_reversion": MeanReversionStrategy,
        "momentum": MomentumStrategy,
        "modular_momentum": ModularMomentumStrategy,
        "pairs_trading": PairsTradingStrategy,
    }

    @classmethod
    def create_strategy(
        cls,
        strategy_config: ConfigDict,
        symbols: Optional[list[str]] = None,
    ) -> Union[MomentumStrategy, MeanReversionStrategy, PairsTradingStrategy]:
        """
        Create a strategy instance from configuration.

        Args:
            strategy_config: Strategy configuration dictionary
            symbols: List of symbols (optional, for multi-strategy)

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy type is unknown
        """
        raw_strategy_type = strategy_config.get("type", "momentum")
        strategy_type = (
            raw_strategy_type if isinstance(raw_strategy_type, str) else str(raw_strategy_type)
        )

        strategy_class = cls.STRATEGY_CLASSES.get(strategy_type)
        if not strategy_class:
            raise ValueError(
                f"Unknown strategy type: {strategy_type}. "
                f"Available: {list(cls.STRATEGY_CLASSES.keys())}"
            )

        logger.info(f"Creating strategy: {strategy_type}")

        # Create strategy instance
        # Note: Strategy constructors vary, so we pass the full config
        strategy = strategy_class(strategy_config)

        return strategy

    @classmethod
    def get_strategy_name(cls, strategy: object) -> str:
        """
        Get the name of a strategy instance.

        Args:
            strategy: Strategy instance

        Returns:
            Strategy name as string
        """
        if hasattr(strategy, "name"):
            name_attr = strategy.name
            if isinstance(name_attr, str):
                return name_attr
            return str(name_attr)

        # Fallback to class name
        return strategy.__class__.__name__

    @classmethod
    def extract_thresholds(cls, strategy_config: ConfigDict) -> ConfigDict:
        """
        Extract trading thresholds from strategy configuration.

        Args:
            strategy_config: Strategy configuration dictionary

        Returns:
            Dictionary with thresholds for buy/sell signals
        """
        raw_thresholds = strategy_config.get("thresholds", {})

        # Ensure thresholds is a dict
        thresholds: ConfigDict
        thresholds = cast("ConfigDict", raw_thresholds) if isinstance(raw_thresholds, dict) else {}

        # Default thresholds if not specified
        if not thresholds:
            thresholds = {
                "buy_threshold": 0.7,  # Buy when signal > 70%
                "sell_threshold": 0.3,  # Sell when signal < 30%
                "stop_loss": -0.05,  # -5% stop loss
                "take_profit": 0.10,  # +10% take profit
            }

        return thresholds

    @classmethod
    def create_baseline_config(cls, base_config: ConfigDict) -> ConfigDict:
        """
        Create baseline strategy configuration.

        Args:
            base_config: Base backtest configuration

        Returns:
            Strategy configuration for baseline test
        """
        strategy_subdict = _extract_nested_dict(base_config, "strategy")
        strategy_type = strategy_subdict.get("type", "modular_momentum")
        if not isinstance(strategy_type, str):
            strategy_type = str(strategy_type)

        parameters_raw = strategy_subdict.get("parameters", {})
        parameters: ConfigDict = (
            cast("ConfigDict", parameters_raw) if isinstance(parameters_raw, dict) else {}
        )

        config: ConfigDict = {
            "type": strategy_type,
            "parameters": parameters,
            "thresholds": cls.extract_thresholds(strategy_subdict),
        }

        # Add default filters for modular_momentum to ensure signals are generated
        if strategy_type == "modular_momentum":
            config["modules"] = {
                "ema_filter": {"enabled": True},
                "rsi_filter": {"enabled": True},
                "stoch_rsi_filter": {"enabled": True},
                "momentum_filter": {"enabled": True},
                "volume_filter": {"enabled": True},
                "atr_filter": {"enabled": True},
            }
            config["preset"] = "balanced"

        return config

    @classmethod
    def create_multi_strategy_configs(cls, base_config: ConfigDict) -> list[ConfigDict]:
        """
        Create configurations for multiple strategies.

        Args:
            base_config: Base backtest configuration

        Returns:
            List of strategy configurations
        """
        base_strategy_config = _extract_nested_dict(base_config, "strategy")
        input_subdict = _extract_nested_dict(base_config, "input")
        symbols_raw = input_subdict.get("symbols", ["AAPL"])
        symbols: list[str]
        symbols = [str(s) for s in symbols_raw] if isinstance(symbols_raw, list) else ["AAPL"]

        configs: list[ConfigDict] = []

        # Create config for each strategy type
        for strategy_type in ["momentum", "mean_reversion", "modular_momentum"]:
            parameters_raw = base_strategy_config.get("parameters", {})
            parameters: ConfigDict = (
                cast("ConfigDict", parameters_raw) if isinstance(parameters_raw, dict) else {}
            )

            strategy_config: ConfigDict = {
                "type": strategy_type,
                "symbols": symbols,
                "parameters": parameters,
                "thresholds": cls.extract_thresholds(base_strategy_config),
            }
            configs.append(strategy_config)

        return configs

    @classmethod
    def list_available_strategies(cls) -> list[str]:
        """
        List all available strategy types.

        Returns:
            List of strategy type names
        """
        return list(cls.STRATEGY_CLASSES.keys())

    @classmethod
    def validate_config(cls, strategy_config: ConfigDict) -> bool:
        """
        Validate strategy configuration.

        Args:
            strategy_config: Strategy configuration to validate

        Returns:
            True if valid, False otherwise
        """
        strategy_type = strategy_config.get("type")

        if not strategy_type:
            logger.warning("Strategy config missing 'type' field")
            return False

        if strategy_type not in cls.STRATEGY_CLASSES:
            logger.warning(f"Unknown strategy type: {strategy_type}")
            return False

        # Check for required fields
        if "thresholds" in strategy_config:
            raw_thresholds = strategy_config["thresholds"]
            if isinstance(raw_thresholds, dict):
                thresholds = cast("ConfigDict", raw_thresholds)
                buy_val = thresholds.get("buy_threshold")
                sell_val = thresholds.get("sell_threshold")
                if (
                    buy_val is not None
                    and sell_val is not None
                    and isinstance(buy_val, (int, float))
                    and isinstance(sell_val, (int, float))
                    and buy_val <= sell_val
                ):
                    logger.warning("buy_threshold must be > sell_threshold")
                    return False

        return True


def create_strategy_from_config(
    strategy_config: ConfigDict,
    symbols: Optional[list[str]] = None,
) -> Union[MomentumStrategy, MeanReversionStrategy, PairsTradingStrategy]:
    """
    Convenience function to create a strategy from configuration.

    Args:
        strategy_config: Strategy configuration dictionary
        symbols: List of symbols (optional)

    Returns:
        Strategy instance
    """
    return StrategyFactory.create_strategy(strategy_config, symbols)


def get_strategy_metadata(strategy: object) -> ConfigDict:
    """
    Get metadata about a strategy instance.

    Args:
        strategy: Strategy instance

    Returns:
        Dictionary with strategy metadata
    """
    return {
        "name": StrategyFactory.get_strategy_name(strategy),
        "class": strategy.__class__.__name__,
        "module": strategy.__class__.__module__,
    }
