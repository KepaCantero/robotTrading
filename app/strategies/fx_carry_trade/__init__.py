"""
FX Carry Trade Strategy Module.

This module implements the FX Carry Trade strategy based on Antti Ilmanen's
methodology from "Expected Returns" - Rule 12.9.

The strategy exploits interest rate differentials between currency pairs:
    carry = (r_base - r_quote) - ((F - S) / S)

Components:
    - models: Data models for FX pairs, rates, signals, and positions
    - fx_rates_provider: Provider interface for FX market data
    - carry_calculator: Carry trade calculation engine
    - fx_carry_trade_strategy: Main strategy implementation

Examples:
    >>> from app.strategies.fx_carry_trade import (
    ...     FXCarryTradeStrategy,
    ...     InMemoryFXRateProvider,
    ...     FXCarryTradeConfig,
    ... )
    >>> config = FXCarryTradeConfig(min_carry_threshold=Decimal("0.02"))
    >>> provider = InMemoryFXRateProvider()
    >>> strategy = FXCarryTradeStrategy(config=config, rate_provider=provider)
"""

from app.strategies.fx_carry_trade.carry_calculator import CarryCalculator, CarryTradeOpportunity
from app.strategies.fx_carry_trade.fx_carry_trade_strategy import (
    FXCarryTradeState,
    FXCarryTradeStrategy,
)
from app.strategies.fx_carry_trade.fx_rates_provider import (
    CompositeFXRateProvider,
    FXRateProvider,
    InMemoryFXRateProvider,
)
from app.strategies.fx_carry_trade.models import (
    CarryTradeMetrics,
    FXCarryPosition,
    FXCarrySignal,
    FXCarryTradeConfig,
    FXPair,
    FXRateQuote,
    InterestRateQuote,
)

__all__ = [
    # Strategy
    "FXCarryTradeStrategy",
    "FXCarryTradeState",
    # Configuration
    "FXCarryTradeConfig",
    "CarryTradeMetrics",
    # Data Models
    "FXPair",
    "FXRateQuote",
    "InterestRateQuote",
    "FXCarrySignal",
    "FXCarryPosition",
    # Providers
    "FXRateProvider",
    "InMemoryFXRateProvider",
    "CompositeFXRateProvider",
    # Calculator
    "CarryCalculator",
    "CarryTradeOpportunity",
]
