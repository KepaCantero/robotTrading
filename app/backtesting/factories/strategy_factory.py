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

import logging
from typing import Dict, List, Optional, Union

from app.domain.strategies.mean_reversion import MeanReversionStrategy
from app.domain.strategies.momentum import MomentumStrategy

# from app.domain.strategies.momentum_modular.strategy import ModularMomentumStrategy  # TODO: Create module
from app.domain.strategies.pairs_trading import PairsTrading as PairsTradingStrategy

logger = logging.getLogger(__name__)

# Temporary alias until momentum_modular is created
ModularMomentumStrategy = MomentumStrategy


class StrategyFactory:
    """
    Factory for creating trading strategies from configuration.

    Extracted from ComprehensiveBacktestRunner to follow Single Responsibility Principle.
    """

    # Strategy type mapping
    STRATEGY_CLASSES = {
        'mean_reversion': MeanReversionStrategy,
        'momentum': MomentumStrategy,
        'modular_momentum': ModularMomentumStrategy,
        'pairs_trading': PairsTradingStrategy,
    }

    @classmethod
    def create_strategy(
        cls,
        strategy_config: Dict[str, Union[str, int, float, bool, List, Dict]],
        symbols: Optional[List[str]] = None,
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
        strategy_type = strategy_config.get('type', 'momentum')

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
        if hasattr(strategy, 'name'):
            return strategy.name

        # Fallback to class name
        return strategy.__class__.__name__

    @classmethod
    def extract_thresholds(cls, strategy_config: Dict[str, Union[str, int, float, bool, List, Dict]]) -> Dict[str, Union[str, int, float, bool, List, Dict]]:
        """
        Extract trading thresholds from strategy configuration.

        Args:
            strategy_config: Strategy configuration dictionary

        Returns:
            Dictionary with thresholds for buy/sell signals
        """
        thresholds = strategy_config.get('thresholds', {})

        # Default thresholds if not specified
        if not thresholds:
            thresholds = {
                'buy_threshold': 0.7,  # Buy when signal > 70%
                'sell_threshold': 0.3,  # Sell when signal < 30%
                'stop_loss': -0.05,  # -5% stop loss
                'take_profit': 0.10,  # +10% take profit
            }

        return thresholds

    @classmethod
    def create_baseline_config(cls, base_config: Dict[str, Union[str, int, float, bool, List, Dict]]) -> Dict[str, Union[str, int, float, bool, List, Dict]]:
        """
        Create baseline strategy configuration.

        Args:
            base_config: Base backtest configuration

        Returns:
            Strategy configuration for baseline test
        """
        strategy_type = base_config.get('strategy', {}).get('type', 'modular_momentum')

        config = {
            'type': strategy_type,
            'parameters': base_config.get('strategy', {}).get('parameters', {}),
            'thresholds': cls.extract_thresholds(base_config.get('strategy', {})),
        }

        # Add default filters for modular_momentum to ensure signals are generated
        if strategy_type == 'modular_momentum':
            config['modules'] = {
                'ema_filter': {'enabled': True},
                'rsi_filter': {'enabled': True},
                'stoch_rsi_filter': {'enabled': True},
                'momentum_filter': {'enabled': True},
                'volume_filter': {'enabled': True},
                'atr_filter': {'enabled': True},
            }
            config['preset'] = 'balanced'

        return config

    @classmethod
    def create_multi_strategy_configs(cls, base_config: Dict[str, Union[str, int, float, bool, List, Dict]]) -> List[Dict[str, Union[str, int, float, bool, List, Dict]]]:
        """
        Create configurations for multiple strategies.

        Args:
            base_config: Base backtest configuration

        Returns:
            List of strategy configurations
        """
        base_strategy_config = base_config.get('strategy', {})
        symbols = base_config.get('input', {}).get('symbols', ['AAPL'])

        configs = []

        # Create config for each strategy type
        for strategy_type in ['momentum', 'mean_reversion', 'modular_momentum']:
            strategy_config = {
                'type': strategy_type,
                'symbols': symbols,
                'parameters': base_strategy_config.get('parameters', {}),
                'thresholds': cls.extract_thresholds(base_strategy_config),
            }
            configs.append(strategy_config)

        return configs

    @classmethod
    def list_available_strategies(cls) -> List[str]:
        """
        List all available strategy types.

        Returns:
            List of strategy type names
        """
        return list(cls.STRATEGY_CLASSES.keys())

    @classmethod
    def validate_config(cls, strategy_config: Dict[str, Union[str, int, float, bool, List, Dict]]) -> bool:
        """
        Validate strategy configuration.

        Args:
            strategy_config: Strategy configuration to validate

        Returns:
            True if valid, False otherwise
        """
        strategy_type = strategy_config.get('type')

        if not strategy_type:
            logger.warning("Strategy config missing 'type' field")
            return False

        if strategy_type not in cls.STRATEGY_CLASSES:
            logger.warning(f"Unknown strategy type: {strategy_type}")
            return False

        # Check for required fields
        if 'thresholds' in strategy_config:
            thresholds = strategy_config['thresholds']
            if 'buy_threshold' in thresholds and 'sell_threshold' in thresholds and thresholds['buy_threshold'] <= thresholds['sell_threshold']:
                logger.warning("buy_threshold must be > sell_threshold")
                return False

        return True


def create_strategy_from_config(
    strategy_config: Dict[str, Union[str, int, float, bool, List, Dict]],
    symbols: Optional[List[str]] = None,
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


def get_strategy_metadata(strategy: object) -> Dict[str, Union[str, int, float, bool, List, Dict]]:
    """
    Get metadata about a strategy instance.

    Args:
        strategy: Strategy instance

    Returns:
        Dictionary with strategy metadata
    """
    return {
        'name': StrategyFactory.get_strategy_name(strategy),
        'class': strategy.__class__.__name__,
        'module': strategy.__class__.__module__,
    }
