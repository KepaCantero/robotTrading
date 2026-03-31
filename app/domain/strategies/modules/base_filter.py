"""
BaseFilter - Clase abstracta base para todos los filtros modulares.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseFilter(ABC):
    """
    Interfaz base para todos los filtros modulares.

    Cada filtro puede:
    - Activarse/desactivarse según el contexto de mercado
    - Retornar un resultado con 'passed', 'confidence', 'reason'
    - Adaptar sus thresholds según el preset (conservative/balanced/aggressive)
    """

    def __init__(
        self,
        name: str,
        config: Optional[dict] = None,
        preset: str = "balanced",
        tier: Optional[str] = None,
        use_yaml: bool = True,
    ):
        """
        Inicializar filtro.

        Args:
            name: Nombre del filtro
            config: Configuración del filtro desde YAML (opcional, se carga desde YAML si no se proporciona)
            preset: Preset activo ('conservative' | 'balanced' | 'aggressive')
            tier: Capital tier para aplicar overrides ('micro', 'small', 'medium', 'large')
            use_yaml: Si True, carga configuración desde archivos YAML cuando config es None
        """
        self.name = name
        self.preset = preset
        self.tier = tier

        # Cargar configuración desde YAML si no se proporciona
        if config is None and use_yaml:
            try:
                from app.shared.config.config_loader import get_filter_config

                config = get_filter_config(name, tier=tier, preset=preset)
                logger.debug(
                    f"Loaded {name} config from YAML (tier={tier or 'default'}, preset={preset})"
                )
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to load {name} config from YAML: {e}, using empty config")
                config = {}

        self.config = config if config is not None else {}
        self.enabled = self.config.get("enabled", True)
        self.priority = self.config.get("priority", "medium")  # 'high' | 'medium' | 'low'

        # Contextos donde el filtro está activo
        self.active_in_contexts = self.config.get("active_in_contexts", ["ALL"])
        self.inactive_in_contexts = self.config.get("inactive_in_contexts", [])

        # Obtener thresholds según preset
        thresholds_config = self.config.get("thresholds", {})
        preset_thresholds = self.config.get("preset_thresholds")

        # Usar preset_thresholds si está disponible (cargado desde YAML)
        if preset_thresholds:
            self.thresholds = preset_thresholds
        elif isinstance(thresholds_config, dict) and "balanced" in thresholds_config:
            # thresholds_config es un dict de presets
            self.thresholds = thresholds_config.get(preset, thresholds_config.get("balanced", {}))
        else:
            # thresholds_config son valores directos (no es un dict de presets)
            self.thresholds = thresholds_config if thresholds_config else {}

    def _is_active_in_context(self, market_context: dict) -> bool:
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
        self,
        indicators: dict,
        market_context: dict,
        signal_type: str,  # 'BUY' | 'SELL'
    ) -> dict:
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
                "passed": True,
                "confidence": 1.0,
                "reason": f"{self.name} inactive in {market_context.get('type', 'unknown')} market",
                "metadata": {"active": False},
            }

        # Aplicar lógica específica del filtro
        try:
            result = self._apply_filter_logic(indicators, market_context, signal_type)
            result["filter_name"] = self.name
            result["priority"] = self.priority
            return result
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error in {self.name}.evaluate(): {e}", exc_info=True)
            # En caso de error, permitir la señal (fail-open)
            return {
                "passed": True,
                "confidence": 0.5,
                "reason": f"{self.name}_generic_error: {e!s}",
                "metadata": {"error": True},
            }

    @abstractmethod
    def _apply_filter_logic(self, indicators: dict, market_context: dict, signal_type: str) -> dict:
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
