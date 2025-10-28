"""
StrategyFactory - Factory para crear estrategias dinámicamente.

Implementa el patrón Factory para la creación dinámica de estrategias,
permitiendo registro y creación de estrategias sin modificar código.
"""

import logging
from typing import Any, Dict, List, Type

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class StrategyFactory:
    """Factory para crear estrategias dinámicamente."""

    def __init__(self):
        """Inicializar factory con registro vacío."""
        self.strategy_registry: Dict[str, Type[BaseStrategy]] = {}
        self._register_default_strategies()

    def register_strategy(self, name: str, strategy_class: Type[BaseStrategy]) -> None:
        """
        Registrar nueva estrategia en el factory.

        Args:
            name: Nombre único de la estrategia
            strategy_class: Clase de la estrategia que hereda de BaseStrategy

        Raises:
            ValueError: Si la clase no hereda de BaseStrategy
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError("Strategy class must inherit from BaseStrategy")

        self.strategy_registry[name] = strategy_class
        logger.info(f"Registered strategy: {name} -> {strategy_class.__name__}")

    def create_strategy(self, name: str, config: Dict[str, Any]) -> BaseStrategy:
        """
        Crear instancia de estrategia.

        Args:
            name: Nombre de la estrategia a crear
            config: Configuración para la estrategia

        Returns:
            Instancia de la estrategia

        Raises:
            ValueError: Si la estrategia no existe o la configuración es inválida
        """
        if name not in self.strategy_registry:
            available = list(self.strategy_registry.keys())
            raise ValueError(f"Strategy '{name}' not found. Available: {available}")

        strategy_class = self.strategy_registry[name]

        try:
            strategy = strategy_class(config)

            # Validar configuración
            if not strategy.validate_config():
                required_params = strategy.get_required_parameters()
                raise ValueError(
                    f"Invalid configuration for strategy '{name}'. Required: {required_params}"
                )

            logger.info(f"Created strategy: {name} with config keys: {list(config.keys())}")
            return strategy

        except Exception as e:
            logger.error(f"Failed to create strategy '{name}': {str(e)}")
            raise ValueError(f"Failed to create strategy '{name}': {str(e)}")

    def list_available_strategies(self) -> List[str]:
        """
        Listar estrategias disponibles para crear.

        Returns:
            Lista de nombres de estrategias registradas
        """
        return list(self.strategy_registry.keys())

    def get_strategy_info(self, name: str) -> Dict[str, Any]:
        """
        Obtener información de una estrategia registrada.

        Args:
            name: Nombre de la estrategia

        Returns:
            Diccionario con información de la estrategia

        Raises:
            ValueError: Si la estrategia no existe
        """
        if name not in self.strategy_registry:
            raise ValueError(f"Strategy '{name}' not found")

        strategy_class = self.strategy_registry[name]

        # Crear instancia temporal para obtener información
        temp_config = {"name": name, "description": "", "version": "1.0.0"}
        temp_strategy = strategy_class(temp_config)

        return {
            "name": name,
            "class_name": strategy_class.__name__,
            "description": temp_strategy.description,
            "version": temp_strategy.version,
            "required_parameters": temp_strategy.get_required_parameters(),
            "module": strategy_class.__module__,
        }

    def unregister_strategy(self, name: str) -> None:
        """
        Desregistrar estrategia del factory.

        Args:
            name: Nombre de la estrategia a desregistrar

        Raises:
            ValueError: Si la estrategia no existe
        """
        if name not in self.strategy_registry:
            raise ValueError(f"Strategy '{name}' not found")

        del self.strategy_registry[name]
        logger.info(f"Unregistered strategy: {name}")

    def _register_default_strategies(self) -> None:
        """Registrar estrategias por defecto."""
        try:
            # Importar estrategias por defecto
            from .mean_reversion import MeanReversionStrategy
            from .momentum import MomentumStrategy
            from .pairs_trading import PairsTradingStrategy

            # Registrar estrategias
            self.register_strategy("momentum", MomentumStrategy)
            self.register_strategy("mean_reversion", MeanReversionStrategy)
            self.register_strategy("pairs_trading", PairsTradingStrategy)

            logger.info("Registered default strategies: momentum, mean_reversion, pairs_trading")

        except ImportError as e:
            logger.warning(f"Could not import default strategies: {e}")
            logger.info("Default strategies will be registered when their modules are available")

    def reload_strategies(self) -> None:
        """Recargar estrategias por defecto."""
        logger.info("Reloading default strategies...")
        self._register_default_strategies()

    def __str__(self) -> str:
        """Representación string del factory."""
        return f"StrategyFactory(registered={len(self.strategy_registry)})"

    def __repr__(self) -> str:
        """Representación detallada del factory."""
        strategies = list(self.strategy_registry.keys())
        return f"StrategyFactory(registered={len(strategies)}, strategies={strategies})"
