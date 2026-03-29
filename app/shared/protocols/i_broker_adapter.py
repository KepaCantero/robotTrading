"""
Broker adapter protocols
"""

from typing import Protocol


class IBrokerAdapter(Protocol):
    """Adapter para broker - Máximo 5 métodos"""

    async def connect(self) -> bool:
        """Conectar al broker"""
        ...

    async def disconnect(self) -> bool:
        """Desconectar del broker"""
        ...

    async def place_order(self, order: dict) -> str:
        """Colocar orden, retorna order_id"""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden"""
        ...

    async def get_account(self) -> dict:
        """Obtener datos de cuenta"""
        ...
