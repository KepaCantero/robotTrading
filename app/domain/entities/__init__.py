"""
Domain Entities - Core business objects with identity.

Entities represent the core business concepts and maintain
their identity across their lifecycle.
"""

from .order import Order
from .portfolio import Portfolio

try:
    from .backtest import Backtest, BacktestStatus, BacktestType

    _backtest_available = True
except ImportError:
    _backtest_available = False

try:
    from .position import Position

    _position_available = True
except ImportError:
    _position_available = False

try:
    from .trade import Trade

    _trade_available = True
except ImportError:
    _trade_available = False

try:
    from .pre_trade_analysis import PreTradeAnalysis

    _pre_trade_analysis_available = True
except ImportError:
    _pre_trade_analysis_available = False

try:
    from .post_trade_analysis import PostTradeAnalysis

    _post_trade_analysis_available = True
except ImportError:
    _post_trade_analysis_available = False

try:
    from .portfolio_optimization import PortfolioOptimization

    _portfolio_optimization_available = True
except ImportError:
    _portfolio_optimization_available = False

__all__ = [
    'Portfolio',
    'Order',
]

if _backtest_available:
    __all__.extend(['Backtest', 'BacktestStatus', 'BacktestType'])

if _position_available:
    __all__.append('Position')

if _trade_available:
    __all__.append('Trade')

if _pre_trade_analysis_available:
    __all__.append('PreTradeAnalysis')

if _post_trade_analysis_available:
    __all__.append('PostTradeAnalysis')

if _portfolio_optimization_available:
    __all__.append('PortfolioOptimization')
