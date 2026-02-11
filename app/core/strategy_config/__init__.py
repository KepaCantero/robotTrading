"""
Strategy Configuration Module

This package provides modular configuration for individual trading strategies.
Each strategy has its own config class that can be imported independently.

Usage:
    from app.core.strategy_config import MomentumModularConfig, DividendStrategyConfig

    momentum_cfg = MomentumModularConfig()
    print(momentum_cfg.bear_market_strength_threshold)
"""

from .momentum_config import MomentumModularConfig
from .dividend_config import DividendStrategyConfig
from .fx_carry_config import FXCarryTradeStrategyConfig

__all__ = [
    "MomentumModularConfig",
    "DividendStrategyConfig",
    "FXCarryTradeStrategyConfig",
]
