from __future__ import annotations

"""Strategy cycle protocols"""
"""Strategy cycle protocols"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.services.live_trading.alert_to_trade_mapper import TradeSignal

    CycleResult = dict  # Type alias for cycle execution results


class IStrategyCycleRunner(Protocol):
    """Ejecuta ciclos de estrategia - Máximo 5 métodos"""

    async def run_cycle(self, signals: list[TradeSignal]) -> CycleResult:
        """Ejecutar ciclo completo"""
        ...

    async def validate_cycle_input(self, signals: list) -> bool:
        """Valida entrada del ciclo"""
        ...

    async def execute_cycle_phase(self, phase: str, signals: list) -> dict:
        """Ejecuta fase del ciclo"""
        ...

    async def handle_cycle_error(self, error: Exception) -> None:
        """Maneja errores del ciclo"""
        ...

    async def get_cycle_metrics(self) -> dict:
        """Obtener métricas del ciclo"""
        ...
