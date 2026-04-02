"""
Portfolio Engine - Base Engine

Engine principal para gestión de portfolios que refactoriza y extiende PortfolioService.
Proporciona interfaz clara para:
- Asignación de capital
- Optimización de portfolio
- Rebalanceo dinámico
- Integración con múltiples brokers
"""

from __future__ import annotations

import contextlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.domain.models.portfolio import Portfolio, PortfolioProvider
from app.services.portfolio_service import PortfolioService

if TYPE_CHECKING:
    from app.engines.portfolio_engine.meta_learners.meta_learners import BaseMetaLearner
    from app.engines.portfolio_engine.optimizers.base import BaseOptimizer
    from app.engines.portfolio_engine.rebalancers.rebalancers import BaseRebalancer

logger = logging.getLogger(__name__)

__all__ = ["BasePortfolioEngine", "PortfolioEngine"]


class BasePortfolioEngine(ABC):
    """
    Clase base para Portfolio Engine.

    Define la interfaz común para todos los engines de portfolio.
    """

    def __init__(self, config: dict[str, object]):
        """
        Inicializar Portfolio Engine.

        Args:
            config: Configuración del engine
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False

    @abstractmethod
    def initialize(self) -> None:
        """Inicializar el engine."""

    @abstractmethod
    def process(self, input_data: object) -> Portfolio | None:
        """Procesar datos de entrada."""

    def health_check(self) -> dict[str, bool | str]:
        """Verificar salud del engine."""
        return {
            "status": "healthy" if self.enabled else "disabled",
            "enabled": self.enabled,
            "initialized": self._initialized,
            "timestamp": datetime.utcnow().isoformat(),
        }


class PortfolioEngine(BasePortfolioEngine):
    """
    Portfolio Engine principal.

    Refactoriza PortfolioService y proporciona:
    - Interfaz clara para gestión de portfolios
    - Integración con múltiples brokers
    - Asignación de capital optimizada
    - Rebalanceo dinámico
    """

    def __init__(self, config: dict[str, object], provider: PortfolioProvider | None = None):
        """
        Inicializar Portfolio Engine.

        Args:
            config: Configuración del engine
            provider: Provider de portfolio (opcional, se crea uno por defecto)
        """
        super().__init__(config)
        self.provider = provider

        # Servicio de portfolio refactorizado (mantener compatibilidad)
        self.portfolio_service = None

        # Componentes del engine
        self.optimizer = None
        self.rebalancer = None
        self.meta_learner = None

        # Estado del engine
        self.current_portfolio: Portfolio | None = None
        self.allocation_history: list[dict[str, object]] = []
        self.rebalance_history: list[dict[str, object]] = []

        # Métricas
        self.total_allocation_operations = 0
        self.total_rebalance_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0

    def initialize(self) -> None:
        """Inicializar el Portfolio Engine."""
        try:
            # Crear PortfolioService si no hay provider
            if self.provider is None:
                from app.infrastructure.providers.paper_trading import PaperTradingPortfolioProvider

                self.provider = PaperTradingPortfolioProvider()

            self.portfolio_service = PortfolioService(self.provider)

            # Inicializar componentes (se configurarán después)
            self.logger.info("PortfolioEngine inicializado")
            self._initialized = True

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error inicializando PortfolioEngine: {e}", exc_info=True)
            self._initialized = False

    def process(self, input_data: object) -> Portfolio | None:
        """
        Procesar datos de entrada.

        Args:
            input_data: Datos de entrada (puede ser Portfolio, dict, etc.)

        Returns:
            Resultado del procesamiento
        """
        if not self._initialized:
            self.initialize()

        if not self.enabled:
            self.logger.warning("PortfolioEngine está deshabilitado")
            return None

        return self._process_portfolio(input_data)

    def _process_portfolio(self, portfolio_data: object) -> Portfolio | None:
        """Procesar datos de portfolio."""
        try:
            if isinstance(portfolio_data, Portfolio):
                self.current_portfolio = portfolio_data
                return portfolio_data
            elif isinstance(portfolio_data, dict):
                # Convertir dict a Portfolio si es necesario
                # Por ahora, retornar None
                return None
            else:
                self.logger.warning(f"Tipo de datos no soportado: {type(portfolio_data)}")
                return None
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.logger.error(f"Error procesando portfolio: {e}", exc_info=True)
            return None

    async def get_portfolio(self) -> Portfolio | None:
        """
        Obtener portfolio actual.

        Returns:
            Portfolio actual o None
        """
        if not self._initialized:
            self.initialize()

        if not self.portfolio_service:
            return None

        try:
            portfolio = await self.portfolio_service.get_portfolio()
            if portfolio:
                self.current_portfolio = portfolio
                self.successful_operations += 1
            return portfolio
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.logger.error(f"Error obteniendo portfolio: {e}", exc_info=True)
            self.failed_operations += 1
            return None

    def set_optimizer(self, optimizer: BaseOptimizer) -> None:
        """
        Establecer optimizer para asignación de capital.

        Args:
            optimizer: Optimizer instance (Markowitz, Risk Parity, etc.)
        """
        self.optimizer = optimizer
        self.logger.info(f"Optimizer configurado: {type(optimizer).__name__}")

    def set_rebalancer(self, rebalancer: BaseRebalancer) -> None:
        """
        Establecer rebalancer para rebalanceo dinámico.

        Args:
            rebalancer: Rebalancer instance
        """
        self.rebalancer = rebalancer
        self.logger.info(f"Rebalancer configurado: {type(rebalancer).__name__}")

    def set_meta_learner(self, meta_learner: BaseMetaLearner) -> None:
        """
        Establecer meta-learner para asignación adaptativa.

        Args:
            meta_learner: Meta-learner instance
        """
        self.meta_learner = meta_learner
        self.logger.info(f"Meta-learner configurado: {type(meta_learner).__name__}")

    def get_allocation_by_asset_class(
        self,
    ) -> dict[str, dict[str, Decimal | float | int | list[str] | str]]:
        """
        Obtener asignación agrupada por clase de activo.

        Returns:
            Dict con asignación por asset class
        """
        if not self.current_portfolio:
            return {}

        allocation = {}
        for position in self.current_portfolio.positions:
            asset_class = (
                position.asset_class.value
                if hasattr(position.asset_class, "value")
                else str(position.asset_class)
            )

            if asset_class not in allocation:
                allocation[asset_class] = {
                    "positions": [],
                    "total_value": Decimal("0"),
                    "total_weight": 0.0,
                    "count": 0,
                }

            allocation[asset_class]["positions"].append(position.symbol)
            allocation[asset_class]["total_value"] += position.market_value
            allocation[asset_class]["count"] += 1

        # Calcular pesos
        total_value = self.current_portfolio.total_equity
        if total_value > 0:
            for asset_class in allocation:
                allocation[asset_class]["total_weight"] = float(
                    allocation[asset_class]["total_value"] / total_value
                )

        return allocation

    def get_status(self) -> dict[str, bool | str | int | None | dict[str, int]]:
        """
        Obtener estado del engine.

        Returns:
            Dict con estado del engine
        """
        status = {
            "enabled": self.enabled,
            "initialized": self._initialized,
            "has_optimizer": self.optimizer is not None,
            "has_rebalancer": self.rebalancer is not None,
            "has_meta_learner": self.meta_learner is not None,
            "current_portfolio": (
                self.current_portfolio.portfolio_id if self.current_portfolio else None
            ),
            "total_allocation_operations": self.total_allocation_operations,
            "total_rebalance_operations": self.total_rebalance_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.portfolio_service:
            with contextlib.suppress(ValueError, TypeError, KeyError, AttributeError, IndexError):
                status["portfolio_service_status"] = {
                    "operations_count": self.portfolio_service.operations_count,
                    "successful_operations": self.portfolio_service.successful_operations,
                    "failed_operations": self.portfolio_service.failed_operations,
                }

        return status
