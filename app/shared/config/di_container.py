"""
Dependency Injection Container

This module provides a simple dependency injection container for managing
application dependencies and their lifecycles.

Reference: Rule 05-architecture.md, Rule 11-enterprise-architecture.md
"""

import inspect
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Type, TypeVar

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
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[str, Callable[[DIContainer], Any]] = {}
        self._transient: Dict[Type, Type] = {}

    def register_singleton(self, interface: Type[T], instance: T) -> None:
        """
        Register a singleton instance.

        Args:
            interface: Type/interface to register
            instance: Instance to return (will be reused)
        """
        self._singletons[interface] = instance

    def register_transient(self, interface: Type[T], implementation: Type[T]) -> None:
        """
        Register a transient type (new instance each time).

        Args:
            interface: Type/interface to register
            implementation: Implementation type to instantiate
        """
        self._transient[interface] = implementation

    def register_factory(self, name: str, factory: Callable[["DIContainer"], T]) -> None:
        """
        Register a factory function.

        Args:
            name: Name to register under
            factory: Factory function that takes container and returns instance
        """
        self._factories[name] = factory

    def get(self, key: Any) -> Any:
        """
        Get a dependency by key.

        Args:
            key: Type or name of dependency

        Returns:
            Instance of the requested dependency

        Raises:
            KeyError: If dependency not found
        """
        # Check singletons
        if isinstance(key, type) and key in self._singletons:
            return self._singletons[key]

        # Check factories
        if isinstance(key, str) and key in self._factories:
            return self._factories[key](self)

        # Check transient
        if isinstance(key, type) and key in self._transient:
            impl = self._transient[key]
            return self._create_instance(impl)

        raise KeyError(f"Dependency not found: {key}")

    def _create_instance(self, cls: Type[T]) -> T:
        """
        Create instance with automatic dependency injection.

        Inspects constructor parameters and resolves dependencies from container.

        Args:
            cls: Class to instantiate

        Returns:
            New instance
        """
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
                    kwargs[param_name] = param.default
                else:
                    # Required dependency not found
                    raise

        return cls(**kwargs)

    def get_optional(self, key: Any) -> Optional[Any]:
        """
        Get a dependency, returning None if not found.

        Args:
            key: Type or name of dependency

        Returns:
            Instance or None if not found
        """
        try:
            return self.get(key)
        except KeyError:
            return None


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """Get or create global DI container."""
    global _container
    if _container is None:
        _container = DIContainer()
        _register_default_services(_container)
    return _container


def _register_default_services(container: DIContainer) -> None:
    """
    Register default strategy services in the container.

    This allows the container to be used with string-based lookups like
    container.get("execution_engine") for testing.

    Args:
        container: DI container to register services in
    """
    # Register factory functions for string-based lookups
    container.register_factory("strategy_registry", lambda c: get_strategy_registry())
    container.register_factory("strategy_config_loader", lambda c: get_strategy_config_loader())
    container.register_factory("strategy_logger", lambda c: get_strategy_logger())
    container.register_factory("execution_engine", lambda c: get_execution_engine())


def reset_container() -> None:
    """Reset global container (mainly for testing)."""
    global _container
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
        from app.core.di_container import get_portfolio_service

        @router.get("/")
        async def get_portfolio(service: PortfolioService = Depends(get_portfolio_service)):
            return await service.get_portfolio()
        ```
    """
    global _portfolio_service_instance
    if _portfolio_service_instance is None:
        from app.infrastructure.providers.paper_trading import PaperTradingPortfolioProvider
        from app.services.portfolio_service import PortfolioService

        provider = PaperTradingPortfolioProvider()
        _portfolio_service_instance = PortfolioService(provider)
    return _portfolio_service_instance


def reset_portfolio_service() -> None:
    """Reset portfolio service singleton (mainly for testing)."""
    global _portfolio_service_instance
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
        from app.core.di_container import get_signal_scorer_service

        @router.post("/evaluate")
        async def evaluate_signal(service: SignalScorerService = Depends(get_signal_scorer_service)):
            return await service.evaluate_signal(...)
        ```
    """
    global _signal_scorer_service_instance
    if _signal_scorer_service_instance is None:
        from app.domain.services.signals.scorer import SignalScorerService

        portfolio_service = get_portfolio_service()
        _signal_scorer_service_instance = SignalScorerService(portfolio_service)
    return _signal_scorer_service_instance


def reset_signal_scorer_service() -> None:
    """Reset signal scorer service singleton (mainly for testing)."""
    global _signal_scorer_service_instance
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
        from app.core.di_container import get_strategy_registry

        @router.get("/")
        async def get_strategies(registry: StrategyRegistry = Depends(get_strategy_registry)):
            return registry.list_available_strategies()
        ```
    """
    global _strategy_registry_instance
    if _strategy_registry_instance is None:
        from app.domain.strategies import StrategyRegistry

        _strategy_registry_instance = StrategyRegistry()
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
        from app.core.di_container import get_strategy_config_loader

        @router.post("/load")
        async def load_strategy(config_loader: StrategyConfigLoader = Depends(get_strategy_config_loader)):
            return config_loader.load_config()
        ```
    """
    global _strategy_config_loader_instance
    if _strategy_config_loader_instance is None:
        from app.domain.strategies import StrategyConfigLoader

        _strategy_config_loader_instance = StrategyConfigLoader()
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
        from app.core.di_container import get_strategy_logger

        @router.get("/metrics")
        async def get_metrics(logger: StrategyLogger = Depends(get_strategy_logger)):
            return logger.get_all_metrics()
        ```
    """
    global _strategy_logger_instance
    if _strategy_logger_instance is None:
        from app.domain.strategies import StrategyLogger

        _strategy_logger_instance = StrategyLogger()
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
        from app.core.di_container import get_execution_engine

        @router.post("/start")
        async def start_engine(engine: ExecutionEngine = Depends(get_execution_engine)):
            engine.start()
            return {"message": "Engine started"}
        ```
    """
    global _execution_engine_instance
    if _execution_engine_instance is None:
        from app.domain.strategies import ExecutionEngine

        registry = get_strategy_registry()
        logger = get_strategy_logger()
        _execution_engine_instance = ExecutionEngine(registry, logger)
    return _execution_engine_instance


def reset_strategy_services() -> None:
    """Reset all strategy service singletons (mainly for testing)."""
    global _strategy_registry_instance
    global _strategy_config_loader_instance
    global _strategy_logger_instance
    global _execution_engine_instance
    _strategy_registry_instance = None
    _strategy_config_loader_instance = None
    _strategy_logger_instance = None
    _execution_engine_instance = None
