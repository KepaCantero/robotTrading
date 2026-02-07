"""
Robust Backtesting Module

Implements institutional-grade backtesting with realistic assumptions.
Handles survivorship bias, corporate actions, transaction costs, slippage,
and market impact for accurate strategy evaluation.

Reference: Rule 11-lopez-de-prado-advances-in-financial-machine-learning.md
- Backtesting overfitting detection
- PnL distribution analysis
- Harrah's bias and look-ahead bias prevention
"""

from __future__ import annotations

from .backtest_engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    PerformanceMetrics,
    Trade,
)
from .dividend_handler import DividendHandler, DividendPayment, DividendReinvestmentStrategy
from .market_impact import (
    ImpactParameters,
    MarketImpactCalculator,
    PermanentImpact,
    TemporaryImpact,
)
from .slippage import (
    LinearSlippageModel,
    PercentageSlippageModel,
    SlippageModel,
    VolatilityAdjustedSlippage,
)
from .survivorship_bias import CorporateAction, DelistingEvent, SurvivorshipBiasCorrector
from .transaction_costs import (
    AlmgrenChristModel,
    LinearCostModel,
    MarketImpactModel,
    PiecewiseLinearCostModel,
    TransactionCostModel,
)

__all__ = [
    # Backtest Engine
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "Trade",
    "PerformanceMetrics",
    # Transaction Costs
    "TransactionCostModel",
    "LinearCostModel",
    "PiecewiseLinearCostModel",
    "MarketImpactModel",
    "AlmgrenChristModel",
    # Slippage
    "SlippageModel",
    "LinearSlippageModel",
    "PercentageSlippageModel",
    "VolatilityAdjustedSlippage",
    # Survivorship Bias
    "SurvivorshipBiasCorrector",
    "DelistingEvent",
    "CorporateAction",
    # Dividend Handler
    "DividendHandler",
    "DividendReinvestmentStrategy",
    "DividendPayment",
    # Market Impact
    "MarketImpactCalculator",
    "ImpactParameters",
    "TemporaryImpact",
    "PermanentImpact",
]
