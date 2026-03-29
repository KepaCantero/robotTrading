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

# Re-export canonical Trade and PerformanceMetrics from app.backtesting.models
from app.backtesting.models import PerformanceMetrics, Trade, TradeSide, TradeStatus

from .backtest_engine import (
    BacktestConfig,
    BacktestEngine,
    BacktestResult,
    OrderSide,
    OrderStatus,
    OrderType,
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
    "AlmgrenChristModel",
    "BacktestConfig",
    # Backtest Engine
    "BacktestEngine",
    "BacktestResult",
    "CorporateAction",
    "DelistingEvent",
    # Dividend Handler
    "DividendHandler",
    "DividendPayment",
    "DividendReinvestmentStrategy",
    "ImpactParameters",
    "LinearCostModel",
    "LinearSlippageModel",
    # Market Impact
    "MarketImpactCalculator",
    "MarketImpactModel",
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "PercentageSlippageModel",
    "PerformanceMetrics",
    "PermanentImpact",
    "PiecewiseLinearCostModel",
    # Slippage
    "SlippageModel",
    # Survivorship Bias
    "SurvivorshipBiasCorrector",
    "TemporaryImpact",
    "Trade",  # Re-exported from app.backtesting.models
    "TradeSide",  # Re-exported from app.backtesting.models
    "TradeStatus",  # Re-exported from app.backtesting.models
    # Transaction Costs
    "TransactionCostModel",
    "VolatilityAdjustedSlippage",
]
