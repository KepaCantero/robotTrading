"""
Risk monitoring protocols (R2)
"""

from typing import Protocol


class IKillSwitchMonitor(Protocol):
    """Monitor de drawdown máximo - Máximo 5 métodos"""

    async def check_kill_switch(self) -> bool:
        """R2: Verificar si drawdown >= 15%"""
        ...

    async def get_current_drawdown(self) -> float:
        """Obtener drawdown actual"""
        ...

    async def activate_kill_switch(self, reason: str) -> bool:
        """Activar kill switch"""
        ...

    async def deactivate_kill_switch(self) -> bool:
        """Desactivar kill switch"""
        ...

    async def get_kill_switch_status(self) -> dict:
        """Obtener estado del kill switch"""
        ...
