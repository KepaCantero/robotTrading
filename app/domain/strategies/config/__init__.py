"""
Strategy Configuration Module

This package provides modular configuration for individual trading strategies.
Each strategy has its own config class that can be imported independently.

Usage:
    from app.domain.strategies.config import MomentumModularConfig, DividendStrategyConfig

    momentum_cfg = MomentumModularConfig()
    print(momentum_cfg.bear_market_strength_threshold)
"""

from .dividend_config import DividendStrategyConfig
from .fx_carry_config import FXCarryTradeStrategyConfig
from .momentum_config import MomentumModularConfig

__all__ = [
    "DividendStrategyConfig",
    "FXCarryTradeStrategyConfig",
    "MomentumModularConfig",
]
