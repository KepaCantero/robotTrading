"""
BaseFilter - Clase abstracta base para todos los filtros modulares.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseFilter(ABC):
    """
    Interfaz base para todos los filtros modulares.

    Cada filtro puede:
    - Activarse/desactivarse según el contexto de mercado
    - Retornar un resultado con 'passed', 'confidence', 'reason'
    - Adaptar sus thresholds según el preset (conservative/balanced/aggressive)
    """

    def __init__(self, name: str, config: Dict, preset: str = "balanced"):
        """
        Inicializar filtro.

        Args:
            name: Nombre del filtro
            config: Configuración del filtro desde YAML
            preset: Preset activo ('conservative' | 'balanced' | 'aggressive')
        """
        self.name = name
        self.config = config
        self.preset = preset
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", "medium")  # 'high' | 'medium' | 'low'

        # Contextos donde el filtro está activo
        self.active_in_contexts = config.get("active_in_contexts", ["ALL"])
        self.inactive_in_contexts = config.get("inactive_in_contexts", [])

        # Obtener thresholds según preset
        thresholds_config = config.get("thresholds", {})
        self.thresholds = thresholds_config.get(preset, thresholds_config.get("balanced", {}))

    def _is_active_in_context(self, market_context: Dict) -> bool:
        """
        Determinar si el filtro debe estar activo según el contexto de mercado.

        Args:
            market_context: Contexto detectado por MarketAnalyzer

        Returns:
            True si el filtro debe evaluarse, False si debe ser ignorado
        """
        if not self.enabled:
            return False

        market_type = market_context.get("type", "unknown")

        # Si está explícitamente inactivo en este contexto
        if "ALL" in self.inactive_in_contexts:
            return False
        if market_type in self.inactive_in_contexts:
            return False

        # Si está activo en todos los contextos
        if "ALL" in self.active_in_contexts:
            return True

        # Si está activo en este contexto específico
        return market_type in self.active_in_contexts

    def evaluate(
        self, indicators: Dict, market_context: Dict, signal_type: str  # 'BUY' | 'SELL'
    ) -> Dict:
        """
        Evalúa si el filtro pasa para el signal_type dado.

        Args:
            indicators: Diccionario con todos los indicadores calculados
            market_context: Contexto de mercado detectado
            signal_type: Tipo de señal ('BUY' | 'SELL')

        Returns:
            {
                'passed': bool,
                'confidence': float,  # 0.0-1.0
                'reason': str,
                'metadata': Dict
            }
        """
        # Si el filtro no está activo en este contexto, no bloquea
        if not self._is_active_in_context(market_context):
            return {
                'passed': True,
                'confidence': 1.0,
                'reason': f"{self.name} inactive in {market_context.get('type', 'unknown')} market",
                'metadata': {'active': False},
            }

        # Aplicar lógica específica del filtro
        try:
            result = self._apply_filter_logic(indicators, market_context, signal_type)
            result['filter_name'] = self.name
            result['priority'] = self.priority
            return result
        except Exception as e:
            logger.error(f"Error in {self.name}.evaluate(): {e}", exc_info=True)
            # En caso de error, permitir la señal (fail-open)
            return {
                'passed': True,
                'confidence': 0.5,
                'reason': f"{self.name}_generic_error: {str(e)}",
                'metadata': {'error': True},
            }

    @abstractmethod
    def _apply_filter_logic(self, indicators: Dict, market_context: Dict, signal_type: str) -> Dict:
        """
        Lógica específica del filtro. Debe ser implementada por cada subclase.

        Returns:
            {
                'passed': bool,
                'confidence': float,
                'reason': str,
                'metadata': Dict
            }
        """
        pass
