"""Alert processing protocols"""
from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from app.services.live_trading.alert_to_trade_mapper import TradeSignal


class IAlertProcessor(Protocol):
    """Procesa alertas de mercado - Máximo 5 métodos"""

    async def process_alert(self, alert: dict) -> Optional["TradeSignal"]:
        """Procesa alerta y genera señal"""
        ...

    async def validate_alert(self, alert: dict) -> bool:
        """Valida formato de alerta"""
        ...

    async def filter_duplicate_alerts(self, alerts: list) -> list:
        """Filtra alertas duplicadas"""
        ...

    async def prioritize_alerts(self, alerts: list) -> list:
        """Prioriza alertas por urgencia"""
        ...

    async def get_alert_history(self, symbol: str, days: int) -> list:
        """Obtener historial de alertas"""
        ...
