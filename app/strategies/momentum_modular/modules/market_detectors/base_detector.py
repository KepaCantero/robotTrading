"""
BaseMarketDetector - Clase base abstracta para detectores de régimen de mercado.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseMarketDetector(ABC):
    """
    Interfaz base para todos los detectores de régimen de mercado.

    Cada detector es un módulo independiente que puede:
    - Activarse/desactivarse
    - Aprender y ajustar parámetros
    - Funcionar independientemente de otros detectores
    """

    def __init__(self, name: str, config: Dict):
        """
        Inicializar detector.

        Args:
            name: Nombre del detector
            config: Configuración específica del detector
        """
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)

    @abstractmethod
    def detect(self, price_history: List[float], **kwargs) -> Dict:
        """
        Detectar régimen específico.

        Args:
            price_history: Histórico de precios
            **kwargs: Argumentos adicionales (volume, indicators, etc.)

        Returns:
            Dict con información del régimen detectado
        """
        pass

    def is_enabled(self) -> bool:
        """Verificar si el detector está habilitado."""
        return self.enabled
