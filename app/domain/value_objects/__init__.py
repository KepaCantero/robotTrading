"""
Value Objects - Immutable values without identity.

Value Objects are defined by their attributes rather than identity.
They are immutable and can be freely shared.
"""

from .capital import Capital
from .investment_horizon import HorizonCategory, InvestmentHorizon
from .money import Money
from .percentage import Percentage, Weight
from .risk_parameters import RiskParameters
from .symbol import AssetClass, Exchange, Symbol
from .tax_residence import RegulatoryRegion, TaxResidence

try:
    pass

    _trading_params_available = True
except ImportError:
    _trading_params_available = False

try:
    pass

    _backtest_config_available = True
except ImportError:
    _backtest_config_available = False

try:
    pass

    _backtest_result_available = True
except ImportError:
    _backtest_result_available = False

try:
    pass

    _backtest_type_available = True
except ImportError:
    _backtest_type_available = False

__all__ = [
    "AssetClass",
    "Capital",
    "Exchange",
    "HorizonCategory",
    "InvestmentHorizon",
    "Money",
    "Percentage",
    "RegulatoryRegion",
    "RiskParameters",
    "Symbol",
    "TaxResidence",
    "Weight",
]

if _trading_params_available:
    __all__.append("TradingParameters")

if _backtest_config_available:
    __all__.append("BacktestConfigValue")

if _backtest_result_available:
    __all__.append("BacktestResultValue")

if _backtest_type_available:
    __all__.append("BacktestType")
