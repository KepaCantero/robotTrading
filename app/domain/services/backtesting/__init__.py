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
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
    Trade,
    PerformanceMetrics,
)
from .transaction_costs import (
    TransactionCostModel,
    LinearCostModel,
    PiecewiseLinearCostModel,
    MarketImpactModel,
    AlmgrenChristModel,
)
from .slippage import (
    SlippageModel,
    LinearSlippageModel,
    PercentageSlippageModel,
    VolatilityAdjustedSlippage,
)
from .survivorship_bias import (
    SurvivorshipBiasCorrector,
    DelistingEvent,
    CorporateAction,
)
from .dividend_handler import (
    DividendHandler,
    DividendReinvestmentStrategy,
    DividendPayment,
)
from .market_impact import (
    MarketImpactCalculator,
    ImpactParameters,
    TemporaryImpact,
    PermanentImpact,
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
