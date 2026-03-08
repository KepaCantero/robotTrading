"""
Post-trade analysis protocols (R11, R12, R13)
"""
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from app.services.live_trading.alert_to_trade_mapper import TradeSignal


class IPostTradeAnalyzer(Protocol):
    """Análisis post-trade - Máximo 5 métodos"""

    async def update_trailing_stop(
        self, position_id: str, current_price: Decimal
    ) -> Optional[Decimal]:
        """R11: Trailing Stop Dinámico"""
        ...

    async def check_partial_take_profit(self, position_id: str, current_pnl: Decimal) -> bool:
        """R12: Take Profit Parcial"""
        ...

    async def evaluate_pyramiding(self, position_id: str, unrealized_pnl: Decimal) -> bool:
        """R13: Pyramiding (solo ganadores)"""
        ...

    async def calculate_position_metrics(self, position_id: str) -> dict:
        """Calcular métricas de posición"""
        ...

    async def generate_exit_signal(self, position_id: str) -> Optional["TradeSignal"]:
        """Generar señal de salida"""
        ...
