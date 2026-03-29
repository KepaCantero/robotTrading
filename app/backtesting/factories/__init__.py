"""
Strategy Factory Module

Provides centralized strategy creation and configuration for backtesting.
"""

from app.backtesting.factories.strategy_factory import (
    StrategyFactory,
    create_strategy_from_config,
    get_strategy_metadata,
)

__all__ = [
    "StrategyFactory",
    "create_strategy_from_config",
    "get_strategy_metadata",
]
