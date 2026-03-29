"""FX Carry Trade Strategy Package."""

from app.domain.strategies.fx_carry_trade.carry_calculator import (
    CarryCalculator,
    CarryTradeOpportunity,
)
from app.domain.strategies.fx_carry_trade.fx_rates_provider import (
    FXRateProvider,
    InMemoryFXRateProvider,
)
from app.domain.strategies.fx_carry_trade.models import (
    CarryTradeAction,
    FXCarryPosition,
    FXCarrySignal,
    FXCarryTradeConfig,
    FXPair,
    FXRateQuote,
    InterestRateQuote,
)

__all__ = [
    "CarryCalculator",
    "CarryTradeAction",
    "CarryTradeOpportunity",
    "FXCarryPosition",
    "FXCarrySignal",
    "FXCarryTradeConfig",
    "FXPair",
    "FXRateProvider",
    "FXRateQuote",
    "InMemoryFXRateProvider",
    "InterestRateQuote",
]
