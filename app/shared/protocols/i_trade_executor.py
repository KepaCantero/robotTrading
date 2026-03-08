"""
Trade execution protocols
"""
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.services.live_trading.alert_to_trade_mapper import TradeSignal

    TradeResult = dict  # Type alias for trade execution results


class ITradeExecutor(Protocol):
    """Ejecuta trades vía broker - Máximo 5 métodos"""

    async def execute_order(self, signal: "TradeSignal") -> "TradeResult":
        """Ejecutar orden con validaciones"""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden existente"""
        ...

    async def modify_order(self, order_id: str, new_price: Decimal) -> bool:
        """Modificar orden existente"""
        ...

    async def get_order_status(self, order_id: str) -> str:
        """Obtener estado de orden"""
        ...

    async def get_open_orders(self) -> list["TradeSignal"]:
        """Obtener órdenes abiertas"""
        ...
