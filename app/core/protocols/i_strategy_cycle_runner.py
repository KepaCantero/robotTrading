"""Strategy cycle protocols"""
from typing import Protocol


class IStrategyCycleRunner(Protocol):
    """Ejecuta ciclos de estrategia - Máximo 5 métodos"""

    async def run_cycle(self, signals: list["TradeSignal"]) -> "CycleResult":
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
