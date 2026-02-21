"""
Shared type definitions for backtesting module.

Consolidates type aliases that were duplicated across multiple files.
"""

from typing import Any, Dict, List, Optional, Union

# Type aliases for better type safety and consistency
ConfigDict = Dict[str, Any]
MetricsDict = Dict[str, Union[float, int, str, bool, None]]
ParameterDict = Dict[str, Any]
OptimizationHistoryEntry = Dict[str, Any]
ValidationResultDict = Dict[str, Any]
PerStrategyResultsDict = Dict[str, Dict[str, Any]]
TradeList = List[Dict[str, Any]]
SignalList = List[Dict[str, Any]]


# Standard metrics keys - use these constants to avoid typos
class MetricKeys:
    """Standard metric key names for consistency."""

    SHARPE_RATIO = "sharpe_ratio"
    TOTAL_RETURN = "total_return"
    RETURN_PCT = "return_pct"
    TOTAL_PNL = "total_pnl"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    TOTAL_TRADES = "total_trades"
    WINNING_TRADES = "winning_trades"
    LOSING_TRADES = "losing_trades"
    AVERAGE_WIN = "average_win"
    AVERAGE_LOSS = "average_loss"
    PROFIT_FACTOR = "profit_factor"
    VOLATILITY = "volatility"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"


class ConfigKeys:
    """Standard config key names for consistency."""

    STRATEGY = "strategy"
    MODULES = "modules"
    FILTERS = "filters"
    PARAMETERS = "parameters"
    THRESHOLDS = "thresholds"
    ADAPTIVE_THRESHOLDS = "adaptive_thresholds"
    RISK_MANAGER = "risk_manager"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
