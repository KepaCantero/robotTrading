"""
BaseDataSource - Interfaz base para todas las fuentes de datos.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BaseDataSource(ABC):
    """
    Clase base abstracta para todas las fuentes de datos.

    Define la interfaz común que todas las fuentes deben implementar.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente de datos.

        Args:
            config: Configuración específica de la fuente
        """
        self.config = config
        self.name = self.__class__.__name__
        self.is_connected = False
        self.last_error: Optional[str] = None

    @abstractmethod
    async def connect(self) -> bool:
        """
        Conectar a la fuente de datos.

        Returns:
            True si la conexión fue exitosa
        """

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Desconectar de la fuente de datos.

        Returns:
            True si la desconexión fue exitosa
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verificar el estado de la conexión.

        Returns:
            True si la fuente está saludable
        """

    def get_config(self) -> Dict[str, Any]:
        """Obtener configuración actual."""
        return self.config.copy()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Actualizar configuración."""
        self.config.update(new_config)
        logger.info(f"{self.name}: Configuración actualizada")

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado de la fuente."""
        return {
            'name': self.name,
            'is_connected': self.is_connected,
            'last_error': self.last_error,
            'config': self.config,
        }
