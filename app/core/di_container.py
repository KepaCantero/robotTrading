"""
Dependency Injection Container

This module provides a simple dependency injection container for managing
application dependencies and their lifecycles.

Reference: Rule 05-architecture.md, Rule 11-enterprise-architecture.md
"""

import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar

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
    return _container


def reset_container() -> None:
    """Reset global container (mainly for testing)."""
    global _container
    _container = None
