"""
Dependency Injection Container

This module provides a simple dependency injection container for managing
application dependencies and their lifecycles.

Reference: Rule 05-architecture.md, Rule 11-enterprise-architecture.md
"""

import inspect
import logging
from typing import TYPE_CHECKING, Callable, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.domain.strategies import (
        ExecutionEngine,
        StrategyConfigLoader,
        StrategyLogger,
        StrategyRegistry,
    )

T = TypeVar("T")


class DIContainer:
    """
    Simple dependency injection container.

    Supports:
    - Singleton lifecycle (default)
    - Transient lifecycle (new instance each time)
    - Factory functions for complex construction
    - Automatic dependency resolution

    Example:
        ```python
        container = DIContainer()

        # Register singleton
        container.register_singleton(Database, Database())

        # Register transient
        container.register_transient(Repository, SQLRepository)

        # Register factory
        container.register_factory("portfolio_service", lambda c: PortfolioService(c.get(Repository)))

        # Resolve
        portfolio_service = container.get("portfolio_service")
        ```
    """

    def __init__(self) -> None:
        """Initialize empty container."""
        self._singletons: dict[type, object] = {}
        self._factories: dict[str, Callable[[DIContainer], object]] = {}
        self._transient: dict[type, type] = {}

    def register_singleton(self, interface: type[T], instance: T) -> None:
        """
        Register a singleton instance.

        Args:
            interface: Type/interface to register
            instance: Instance to return (will be reused)
        """
        logger.debug(
            "registering_singleton",
            extra={"interface": interface.__name__, "instance_type": type(instance).__name__},
        )
        self._singletons[interface] = instance

    def register_transient(self, interface: type[T], implementation: type[T]) -> None:
        """
        Register a transient type (new instance each time).

        Args:
            interface: Type/interface to register
            implementation: Implementation type to instantiate
        """
        logger.debug(
            "registering_transient",
            extra={"interface": interface.__name__, "implementation": implementation.__name__},
        )
        self._transient[interface] = implementation

    def register_factory(self, name: str, factory: Callable[["DIContainer"], T]) -> None:
        """
        Register a factory function.

        Args:
            name: Name to register under
            factory: Factory function that takes container and returns instance
        """
        logger.debug(
            "registering_factory",
            extra={
                "name": name,
                "factory": factory.__name__ if hasattr(factory, "__name__") else "lambda",
            },
        )
        self._factories[name] = factory

    def get(self, key: Union[type, str]) -> object:
        """
        Get a dependency by key.

        Args:
            key: Type or name of dependency

        Returns:
            Instance of the requested dependency

        Raises:
            KeyError: If dependency not found
        """
        logger.debug("getting_dependency", extra={"key": str(key)})
        # Check singletons
        if isinstance(key, type) and key in self._singletons:
            logger.debug("dependency_resolved_from_singletons", extra={"key": str(key)})
            return self._singletons[key]

        # Check factories
        if isinstance(key, str) and key in self._factories:
            logger.debug("dependency_resolved_from_factory", extra={"key": key})
            return self._factories[key](self)

        # Check transient
        if isinstance(key, type) and key in self._transient:
            logger.debug("dependency_resolved_from_transient", extra={"key": str(key)})
            impl = self._transient[key]
            return self._create_instance(impl)

        logger.error("dependency_not_found", extra={"key": str(key)})
        raise KeyError(f"Dependency not found: {key}")

    def _create_instance(self, cls: type[T]) -> T:
        """
        Create instance with automatic dependency injection.

        Inspects constructor parameters and resolves dependencies from container.

        Args:
            cls: Class to instantiate

        Returns:
            New instance
        """
        logger.debug("creating_instance", extra={"class": cls.__name__})
        sig = inspect.signature(cls.__init__)
        kwargs = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            # Skip parameters without annotations
            if param.annotation == inspect.Parameter.empty:
                continue

            # Try to resolve dependency
            try:
                kwargs[param_name] = self.get(param.annotation)
            except KeyError:
                # Use default value if available
                if param.default != inspect.Parameter.empty:
                    logger.debug(
                        "using_default_parameter_value",
                        extra={"class": cls.__name__, "param": param_name},
                    )
                    kwargs[param_name] = param.default
                else:
                    # Required dependency not found
                    logger.error(
                        "required_dependency_not_found",
                        extra={"class": cls.__name__, "param": param_name},
                    )
                    raise

        instance = cls(**kwargs)
        logger.debug("instance_created", extra={"class": cls.__name__})
        return instance

    def get_optional(self, key: Union[type, str]) -> Optional[object]:
        """
        Get a dependency, returning None if not found.

        Args:
            key: Type or name of dependency

        Returns:
            Instance or None if not found
        """
        try:
            result = self.get(key)
            logger.debug("get_optional_succeeded", extra={"key": str(key)})
            return result
        except KeyError:
            logger.debug("get_optional_not_found", extra={"key": str(key)})
            return None


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get or create global DI container."""
    global _container
    if _container is None:
        logger.info("creating_global_di_container")
        _container = DIContainer()
        _register_default_services(_container)
        logger.info("global_di_container_created")
    return _container


def _register_default_services(container: DIContainer) -> None:
    """
    Register default strategy services in the container.

    This allows the container to be used with string-based lookups like
    container.get("execution_engine") for testing.

    Args:
        container: DI container to register services in
    """
    logger.debug("registering_default_services")
    # Register factory functions for string-based lookups
    container.register_factory("strategy_registry", lambda c: get_strategy_registry())
    container.register_factory("strategy_config_loader", lambda c: get_strategy_config_loader())
    container.register_factory("strategy_logger", lambda c: get_strategy_logger())
    container.register_factory("execution_engine", lambda c: get_execution_engine())
    logger.debug("default_services_registered")


def reset_container() -> None:
    """Reset global container (mainly for testing)."""
    global _container
    logger.debug("resetting_global_container")
    _container = None


# Portfolio service factory for FastAPI dependency injection
_portfolio_service_instance = None


def get_portfolio_service():
    """
    Get PortfolioService instance as a FastAPI dependency.

    This is a convenience function for use with FastAPI's Depends().
    It implements lazy singleton pattern - the service is created on first use.

    Returns:
        PortfolioService: Singleton instance of PortfolioService

    Example:
        ```python
        from fastapi import Depends
        from app.shared.config.di_container import get_portfolio_service

        @router.get("/")
        async def get_portfolio(service: PortfolioService = Depends(get_portfolio_service)):
            return await service.get_portfolio()
        ```
    """
    global _portfolio_service_instance
    if _portfolio_service_instance is None:
        logger.debug("creating_portfolio_service_instance")
        from app.infrastructure.providers.paper_trading import PaperTradingPortfolioProvider
        from app.services.portfolio_service import PortfolioService

        provider = PaperTradingPortfolioProvider()
        _portfolio_service_instance = PortfolioService(provider)
        logger.debug("portfolio_service_instance_created")
    return _portfolio_service_instance


def reset_portfolio_service() -> None:
    """Reset portfolio service singleton (mainly for testing)."""
    global _portfolio_service_instance
    logger.debug("resetting_portfolio_service")
    _portfolio_service_instance = None


# Signal scorer service factory for FastAPI dependency injection
_signal_scorer_service_instance = None


def get_signal_scorer_service():
    """
    Get SignalScorerService instance as a FastAPI dependency.

    This is a convenience function for use with FastAPI's Depends().
    It implements lazy singleton pattern - the service is created on first use.
    The SignalScorerService depends on PortfolioService.

    Returns:
        SignalScorerService: Singleton instance of SignalScorerService

    Example:
        ```python
        from fastapi import Depends
        from app.shared.config.di_container import get_signal_scorer_service

        @router.post("/evaluate")
        async def evaluate_signal(service: SignalScorerService = Depends(get_signal_scorer_service)):
            return await service.evaluate_signal(...)
        ```
    """
    global _signal_scorer_service_instance
    if _signal_scorer_service_instance is None:
        logger.debug("creating_signal_scorer_service_instance")
        from app.services.signal_scorer import SignalScorerService

        portfolio_service = get_portfolio_service()
        _signal_scorer_service_instance = SignalScorerService(portfolio_service)
        logger.debug("signal_scorer_service_instance_created")
    return _signal_scorer_service_instance


def reset_signal_scorer_service() -> None:
    """Reset signal scorer service singleton (mainly for testing)."""
    global _signal_scorer_service_instance
    logger.debug("resetting_signal_scorer_service")
    _signal_scorer_service_instance = None


# ============================================================================
# Strategy Services - Factory Functions
# ============================================================================

_strategy_registry_instance = None
_strategy_config_loader_instance = None
_strategy_logger_instance = None
_execution_engine_instance = None


def get_strategy_registry() -> "StrategyRegistry":
    """
    Get StrategyRegistry singleton as a FastAPI dependency.

    This is a convenience function for use with FastAPI's Depends().
    It implements lazy singleton pattern - the service is created on first use.

    Returns:
        StrategyRegistry: Singleton instance of StrategyRegistry

    Example:
        ```python
        from fastapi import Depends
        from app.shared.config.di_container import get_strategy_registry

        @router.get("/")
        async def get_strategies(registry: StrategyRegistry = Depends(get_strategy_registry)):
            return registry.list_available_strategies()
        ```
    """
    global _strategy_registry_instance
    if _strategy_registry_instance is None:
        logger.debug("creating_strategy_registry_instance")
        from app.domain.strategies import StrategyRegistry

        _strategy_registry_instance = StrategyRegistry()
        logger.debug("strategy_registry_instance_created")
    return _strategy_registry_instance


def get_strategy_config_loader() -> "StrategyConfigLoader":
    """
    Get StrategyConfigLoader singleton as a FastAPI dependency.

    This is a convenience function for use with FastAPI's Depends().
    It implements lazy singleton pattern - the service is created on first use.

    Returns:
        StrategyConfigLoader: Singleton instance of StrategyConfigLoader

    Example:
        ```python
        from fastapi import Depends
        from app.shared.config.di_container import get_strategy_config_loader

        @router.post("/load")
        async def load_strategy(config_loader: StrategyConfigLoader = Depends(get_strategy_config_loader)):
            return config_loader.load_config()
        ```
    """
    global _strategy_config_loader_instance
    if _strategy_config_loader_instance is None:
        logger.debug("creating_strategy_config_loader_instance")
        from app.domain.strategies import StrategyConfigLoader

        _strategy_config_loader_instance = StrategyConfigLoader()
        logger.debug("strategy_config_loader_instance_created")
    return _strategy_config_loader_instance


def get_strategy_logger() -> "StrategyLogger":
    """
    Get StrategyLogger singleton as a FastAPI dependency.

    This is a convenience function for use with FastAPI's Depends().
    It implements lazy singleton pattern - the service is created on first use.

    Returns:
        StrategyLogger: Singleton instance of StrategyLogger

    Example:
        ```python
        from fastapi import Depends
        from app.shared.config.di_container import get_strategy_logger

        @router.get("/metrics")
        async def get_metrics(logger: StrategyLogger = Depends(get_strategy_logger)):
            return logger.get_all_metrics()
        ```
    """
    global _strategy_logger_instance
    if _strategy_logger_instance is None:
        logger.debug("creating_strategy_logger_instance")
        from app.domain.strategies import StrategyLogger

        _strategy_logger_instance = StrategyLogger()
        logger.debug("strategy_logger_instance_created")
    return _strategy_logger_instance


def get_execution_engine() -> "ExecutionEngine":
    """
    Get ExecutionEngine singleton as a FastAPI dependency.

    This is a convenience function for use with FastAPI's Depends().
    It implements lazy singleton pattern - the engine is created on first use
    with its dependencies (StrategyRegistry and StrategyLogger) resolved from
    the DI container.

    Returns:
        ExecutionEngine: Singleton instance of ExecutionEngine

    Example:
        ```python
        from fastapi import Depends
        from app.shared.config.di_container import get_execution_engine

        @router.post("/start")
        async def start_engine(engine: ExecutionEngine = Depends(get_execution_engine)):
            engine.start()
            return {"message": "Engine started"}
        ```
    """
    global _execution_engine_instance
    if _execution_engine_instance is None:
        logger.debug("creating_execution_engine_instance")
        from app.domain.strategies import ExecutionEngine

        registry = get_strategy_registry()
        strategy_logger = get_strategy_logger()
        _execution_engine_instance = ExecutionEngine(registry, strategy_logger)
        logger.debug("execution_engine_instance_created")
    return _execution_engine_instance


def reset_strategy_services() -> None:
    """Reset all strategy service singletons (mainly for testing)."""
    global _strategy_registry_instance
    global _strategy_config_loader_instance
    global _strategy_logger_instance
    global _execution_engine_instance
    logger.debug("resetting_all_strategy_services")
    _strategy_registry_instance = None
    _strategy_config_loader_instance = None
    _strategy_logger_instance = None
    _execution_engine_instance = None
