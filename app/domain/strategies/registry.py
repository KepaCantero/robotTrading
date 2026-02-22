"""
StrategyRegistry - Registro centralizado de estrategias disponibles.

Gestiona el ciclo de vida de las estrategias, incluyendo carga, descarga,
activación y hot-swapping de estrategias.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseStrategy
from .factory import StrategyFactory

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """Registro centralizado de estrategias disponibles."""

    def __init__(self):
        """Inicializar registry con factory y estado vacío."""
        self.strategies: Dict[str, BaseStrategy] = {}
        self.factory = StrategyFactory()
        self.active_strategy: Optional[str] = None
        self.created_at = datetime.utcnow()

    def load_strategy(self, name: str, config: Dict[str, Any]) -> BaseStrategy:
        """
        Cargar estrategia desde configuración.

        Args:
            name: Nombre de la estrategia a cargar
            config: Configuración para la estrategia

        Returns:
            Instancia de la estrategia cargada

        Raises:
            ValueError: Si la estrategia no se puede crear o ya existe
        """
        if name in self.strategies:
            logger.warning(f"Strategy '{name}' already loaded, replacing...")
            self.unload_strategy(name)

        try:
            strategy = self.factory.create_strategy(name, config)
            self.strategies[name] = strategy
            logger.info(f"Loaded strategy: {name}")
            return strategy

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error("Failed to load strategy", name=name, error=str(e), exc_info=True)
            raise ValueError(f"Failed to load strategy '{name}': {str(e)}")

    def unload_strategy(self, name: str) -> None:
        """
        Descargar estrategia del registry.

        Args:
            name: Nombre de la estrategia a descargar

        Raises:
            ValueError: Si la estrategia no está cargada
        """
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not loaded")

        strategy = self.strategies[name]
        strategy.is_active = False

        # Si era la estrategia activa, limpiar
        if self.active_strategy == name:
            self.active_strategy = None
            logger.info(f"Deactivated strategy: {name}")

        del self.strategies[name]
        logger.info(f"Unloaded strategy: {name}")

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """
        Obtener estrategia cargada.

        Args:
            name: Nombre de la estrategia

        Returns:
            Instancia de la estrategia o None si no está cargada
        """
        return self.strategies.get(name)

    def set_active_strategy(self, name: str) -> None:
        """
        Establecer estrategia activa.

        Args:
            name: Nombre de la estrategia a activar

        Raises:
            ValueError: Si la estrategia no está cargada
        """
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not loaded")

        # Desactivar estrategia anterior
        if self.active_strategy and self.active_strategy in self.strategies:
            self.strategies[self.active_strategy].is_active = False
            logger.info(f"Deactivated previous strategy: {self.active_strategy}")

        # Activar nueva estrategia
        self.strategies[name].is_active = True
        self.active_strategy = name
        logger.info(f"Activated strategy: {name}")

    def get_active_strategy(self) -> Optional[BaseStrategy]:
        """
        Obtener estrategia activa.

        Returns:
            Instancia de la estrategia activa o None si no hay ninguna
        """
        if self.active_strategy:
            return self.strategies.get(self.active_strategy)
        return None

    def list_loaded_strategies(self) -> List[str]:
        """
        Listar estrategias cargadas.

        Returns:
            Lista de nombres de estrategias cargadas
        """
        return list(self.strategies.keys())

    def list_available_strategies(self) -> List[str]:
        """
        Listar estrategias disponibles para cargar.

        Returns:
            Lista de nombres de estrategias disponibles
        """
        return self.factory.list_available_strategies()

    def get_strategy_status(self, name: str) -> Dict[str, Any]:
        """
        Obtener estado de una estrategia.

        Args:
            name: Nombre de la estrategia

        Returns:
            Diccionario con estado de la estrategia

        Raises:
            ValueError: Si la estrategia no está cargada
        """
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not loaded")

        strategy = self.strategies[name]

        return {
            "name": strategy.name,
            "is_active": strategy.is_active,
            "is_currently_active": self.active_strategy == name,
            "version": strategy.version,
            "description": strategy.description,
            "created_at": strategy.created_at.isoformat(),
            "parameters": strategy.get_parameters(),
        }

    def get_all_strategies_status(self) -> Dict[str, Any]:
        """
        Obtener estado de todas las estrategias.

        Returns:
            Diccionario con estado de todas las estrategias
        """
        loaded_strategies = {}
        for name in self.strategies:
            loaded_strategies[name] = self.get_strategy_status(name)

        return {
            "active_strategy": self.active_strategy,
            "loaded_strategies": loaded_strategies,
            "available_strategies": self.list_available_strategies(),
            "registry_created_at": self.created_at.isoformat(),
            "total_loaded": len(self.strategies),
        }

    def reload_strategy(self, name: str, config: Dict[str, Any]) -> BaseStrategy:
        """
        Recargar estrategia con nueva configuración.

        Args:
            name: Nombre de la estrategia a recargar
            config: Nueva configuración

        Returns:
            Nueva instancia de la estrategia

        Raises:
            ValueError: Si la estrategia no se puede recargar
        """
        was_active = self.active_strategy == name

        try:
            # Descargar estrategia actual
            if name in self.strategies:
                self.unload_strategy(name)

            # Cargar nueva versión
            strategy = self.load_strategy(name, config)

            # Reactivar si era la activa
            if was_active:
                self.set_active_strategy(name)

            logger.info(f"Reloaded strategy: {name}")
            return strategy

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error("Failed to reload strategy", name=name, error=str(e), exc_info=True)
            raise ValueError(f"Failed to reload strategy '{name}': {str(e)}")

    def clear_all_strategies(self) -> None:
        """Limpiar todas las estrategias cargadas."""
        strategies_to_remove = list(self.strategies.keys())

        for name in strategies_to_remove:
            self.unload_strategy(name)

        logger.info(f"Cleared all strategies: {len(strategies_to_remove)} removed")

    def __str__(self) -> str:
        """Representación string del registry."""
        active = self.active_strategy or "None"
        return f"StrategyRegistry(loaded={len(self.strategies)}, active={active})"

    def __repr__(self) -> str:
        """Representación detallada del registry."""
        loaded = list(self.strategies.keys())
        return (
            "StrategyRegistry("
            f"loaded={len(loaded)}, "
            f"active='{self.active_strategy}', "
            f"strategies={loaded})"
        )
