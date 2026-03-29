"""
Position Management Services

Implementación de gestión de posiciones post-trade:
- R11: Trailing Stop Dinámico
- R12: Take Profit Parcial
- R13: Pyramiding (solo ganadores)
"""

from app.services.position_management.partial_take_profit import (
    PartialTakeProfit,
    ProfitTarget,
    TakeProfitAction,
)
from app.services.position_management.post_trade_analyzer_impl import (
    PositionState,
    PostTradeAnalyzerImpl,
    TradeSignal,
)
from app.services.position_management.pyramiding_manager import (
    PyramidingAddition,
    PyramidingManager,
    PyramidingResult,
)
from app.services.position_management.trailing_stop_manager import (
    TrailingStopManager,
    TrailingStopResult,
)

__all__ = [
    # Partial Take Profit (R12)
    "PartialTakeProfit",
    "PositionState",
    # Main Implementation
    "PostTradeAnalyzerImpl",
    "ProfitTarget",
    "PyramidingAddition",
    # Pyramiding (R13)
    "PyramidingManager",
    "PyramidingResult",
    "TakeProfitAction",
    "TradeSignal",
    # Trailing Stop (R11)
    "TrailingStopManager",
    "TrailingStopResult",
]
