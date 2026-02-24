"""
Pre-trade validation protocols (R1, R2, R4)
"""
from typing import Protocol, Optional
from decimal import Decimal


class IPreTradeValidator(Protocol):
    """Validaciones pre-trade (R1, R2, R4) - Máximo 5 métodos"""

    async def validate_kelly(self, capital: Decimal, order_value: Decimal) -> bool:
        """R1: Kelly Criterion + 2% max"""
        ...

    async def validate_drawdown(self) -> bool:
        """R2: Drawdown 15% stop"""
        ...

    async def validate_rr_ratio(self, entry: Decimal, target: Decimal, stop: Decimal) -> bool:
        """R4: R:R 2:1 minimum"""
        ...

    async def validate_stop_loss(self, stop_loss: Optional[Decimal]) -> bool:
        """R3: Stop Loss SIEMPRE requerido"""
        ...

    async def validate_market_hours(self) -> bool:
        """R9: Evitar horarios de baja liquidez"""
        ...
