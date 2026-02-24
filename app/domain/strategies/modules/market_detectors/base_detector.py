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

    def __init__(
        self,
        name: str,
        config: Optional[Dict] = None,
        tier: Optional[str] = None,
        use_yaml: bool = True,
    ):
        """
        Inicializar detector.

        Args:
            name: Nombre del detector
            config: Configuración específica del detector (opcional, se carga desde YAML si no se proporciona)
            tier: Capital tier para aplicar overrides ('micro', 'small', 'medium', 'large')
            use_yaml: Si True, carga configuración desde archivos YAML cuando config es None
        """
        self.name = name
        self.tier = tier

        # Cargar configuración desde YAML si no se proporciona
        if config is None and use_yaml:
            try:
                from app.shared.config.config_loader import get_detector_config

                config = get_detector_config(name, tier=tier)
                logger.debug(f"Loaded {name} config from YAML (tier={tier or 'default'})")
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to load {name} config from YAML: {e}, using empty config")
                config = {}

        self.config = config if config is not None else {}
        self.enabled = self.config.get("enabled", True)

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

    def is_enabled(self) -> bool:
        """Verificar si el detector está habilitado."""
        return self.enabled
