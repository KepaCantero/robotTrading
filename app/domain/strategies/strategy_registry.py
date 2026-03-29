"""
Strategy Registry Pattern - Pluggable algorithms following Percival's Architecture Patterns with Python

This module implements the Strategy pattern with a registry as described in
"Architecture Patterns with Python" (Cosmic Python) by Percival & Gregory.

Key concepts:
- Strategy pattern for pluggable algorithms
- Registry for dynamic strategy discovery
- Dependency inversion (depend on abstractions)
- Composition over inheritance
- Runtime strategy switching

Reference: Chapter 4, "The Strategy Pattern"

The Strategy pattern is especially valuable for:
1. Interchangeable algorithms
2. Runtime strategy selection
3. Testing with mock strategies
4. Adding strategies without modifying existing code
5. A/B testing different strategies
"""

from __future__ import annotations

import inspect
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
StrategyType = TypeVar("StrategyType", bound="BaseStrategy")


# ============================================================================
# STRATEGY INTERFACE
# ============================================================================


class BaseStrategy(ABC):
    """
    Abstract base class for all strategies.

    Following the Strategy pattern, this defines the interface that
    all concrete strategies must implement. The context (trading system)
    depends on this abstraction, not concrete implementations.

    Example:
        ```python
        class MovingAverageStrategy(BaseStrategy):
            def execute(self, data):
                # Implementation
                return signals

        class RSIStrategy(BaseStrategy):
            def execute(self, data):
                # Different implementation
                return signals
        ```
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize strategy with configuration.

        Args:
            config: Strategy configuration parameters
        """
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.description = config.get("description", "")
        self.version = config.get("version", "1.0.0")
        self.enabled = config.get("enabled", True)
        self.created_at = datetime.utcnow()

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute the strategy algorithm.

        This is the core method where each strategy implements
        its specific algorithm.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Strategy execution result
        """

    def validate_config(self) -> bool:
        """
        Validate strategy configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        return True

    def get_required_parameters(self) -> list[str]:
        """
        Get list of required configuration parameters.

        Returns:
            List of required parameter names
        """
        return []

    def get_metadata(self) -> dict[str, Any]:
        """
        Get strategy metadata.

        Returns:
            Dictionary with strategy information
        """
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "module": self.__class__.__module__,
            "required_parameters": self.get_required_parameters(),
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, version={self.version})"


# ============================================================================
# STRATEGY CONTEXT
# ============================================================================


class StrategyContext:
    """
    Context that uses a strategy to execute algorithms.

    The context is the class that delegates work to the strategy.
    It maintains a reference to a strategy object and can switch
    strategies at runtime.

    Example:
        ```python
        context = StrategyContext()

        # Use moving average strategy
        context.set_strategy(MovingAverageStrategy(config))
        result = context.execute_strategy(data)

        # Switch to RSI strategy
        context.set_strategy(RSIStrategy(config))
        result = context.execute_strategy(data)
        ```
    """

    def __init__(self, strategy: BaseStrategy | None = None):
        """
        Initialize context with optional strategy.

        Args:
            strategy: Initial strategy (can be set later)
        """
        self._strategy: BaseStrategy | None = strategy
        self._execution_history: list[dict[str, Any]] = []

    def set_strategy(self, strategy: BaseStrategy) -> None:
        """
        Set the strategy to use.

        Args:
            strategy: Strategy instance to use

        Example:
            ```python
            context.set_strategy(MovingAverageStrategy({...}))
            ```
        """
        self._strategy = strategy
        logger.info(f"Set strategy to: {strategy.__class__.__name__}")

    def get_strategy(self) -> BaseStrategy | None:
        """
        Get the current strategy.

        Returns:
            Current strategy or None
        """
        return self._strategy

    async def execute_strategy(self, *args, **kwargs) -> Any:
        """
        Execute the current strategy.

        Args:
            *args: Arguments passed to strategy
            **kwargs: Keyword arguments passed to strategy

        Returns:
            Strategy execution result

        Raises:
            RuntimeError: If no strategy is set

        Example:
            ```python
            result = await context.execute_strategy(market_data)
            ```
        """
        if self._strategy is None:
            raise RuntimeError("No strategy set. Call set_strategy() first.")

        start_time = datetime.utcnow()

        try:
            result = await self._strategy.execute(*args, **kwargs)

            # Record execution
            self._execution_history.append(
                {
                    "strategy": self._strategy.name,
                    "class": self._strategy.__class__.__name__,
                    "timestamp": start_time.isoformat(),
                    "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                    "success": True,
                }
            )

            return result

        except (ValueError, TypeError, RuntimeError) as e:
            # Record failure
            self._execution_history.append(
                {
                    "strategy": self._strategy.name,
                    "timestamp": start_time.isoformat(),
                    "success": False,
                    "error": str(e),
                }
            )
            logger.error("Strategy execution failed: %s", str(e), exc_info=True)
            raise

    def get_execution_history(self) -> list[dict[str, Any]]:
        """
        Get strategy execution history.

        Returns:
            List of execution records
        """
        return self._execution_history.copy()


# ============================================================================
# STRATEGY REGISTRY
# ============================================================================


@dataclass
class StrategyMetadata:
    """
    Metadata for a registered strategy.

    Stores information about strategies in the registry.
    """

    name: str
    strategy_class: type[BaseStrategy]
    description: str = ""
    version: str = "1.0.0"
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    required_parameters: list[str] = field(default_factory=list)
    enabled: bool = True
    registered_at: datetime = field(default_factory=datetime.utcnow)


class StrategyRegistry:
    """
    Registry for managing trading strategies.

    The registry pattern allows for:
    - Dynamic strategy discovery
    - Runtime strategy registration
    - Strategy lookup by name/category
    - A/B testing different strategies
    - Hot-swapping strategies

    Example:
        ```python
        registry = StrategyRegistry()

        # Register strategies
        registry.register("ma_short", MovingAverageStrategy, category="trend")
        registry.register("rsi", RSIStrategy, category="momentum")

        # Create strategies
        ma_strategy = registry.create("ma_short", config={...})
        rsi_strategy = registry.create("rsi", config={...})

        # Find strategies by category
        trend_strategies = registry.find_by_category("trend")

        # List all strategies
        all_strategies = registry.list_strategies()
        ```
    """

    def __init__(self):
        """Initialize empty registry."""
        self._strategies: dict[str, StrategyMetadata] = {}
        self._instances: dict[str, BaseStrategy] = {}
        logger.info("StrategyRegistry initialized")

    def register(
        self,
        name: str,
        strategy_class: type[BaseStrategy],
        description: str = "",
        category: str = "general",
        tags: list[str] | None = None,
        enabled: bool = True,
        replace: bool = False,
    ) -> None:
        """
        Register a strategy class.

        Args:
            name: Unique name for the strategy
            strategy_class: Strategy class (must inherit from BaseStrategy)
            description: Strategy description
            category: Strategy category (trend, momentum, mean_reversion, etc.)
            tags: List of tags for filtering
            enabled: Whether strategy is enabled for use
            replace: Replace existing strategy with same name

        Raises:
            ValueError: If strategy already exists and replace=False
            TypeError: If strategy_class doesn't inherit from BaseStrategy

        Example:
            ```python
            registry.register(
                name="ma_short",
                strategy_class=MovingAverageStrategy,
                description="Short-term moving average crossover",
                category="trend",
                tags=["ma", "crossover", "short_term"]
            )
            ```
        """
        # Validate strategy class
        if not inspect.isclass(strategy_class):
            raise TypeError(f"{strategy_class} must be a class")

        if not issubclass(strategy_class, BaseStrategy):
            raise TypeError(f"{strategy_class.__name__} must inherit from BaseStrategy")

        # Check for existing strategy
        if name in self._strategies and not replace:
            raise ValueError(
                f"Strategy '{name}' already registered. Use replace=True to overwrite."
            )

        # Create temporary instance to get metadata
        temp_config = {"name": name, "description": description}
        try:
            temp_instance = strategy_class(temp_config)
            required_params = temp_instance.get_required_parameters()
        except Exception as e:
            logger.warning(
                "Could not instantiate %s for metadata: %s",
                strategy_class.__name__,
                str(e),
                exc_info=True,
            )
            required_params = []

        # Create metadata
        metadata = StrategyMetadata(
            name=name,
            strategy_class=strategy_class,
            description=description or temp_instance.description,
            version=temp_instance.version,
            category=category,
            tags=tags or [],
            required_parameters=required_params,
            enabled=enabled,
        )

        self._strategies[name] = metadata
        logger.info(f"Registered strategy: {name} ({strategy_class.__name__})")

    def unregister(self, name: str) -> None:
        """
        Unregister a strategy.

        Args:
            name: Strategy name

        Raises:
            KeyError: If strategy not found
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found")

        # Remove cached instances
        self._instances.pop(name, None)

        # Remove from registry
        del self._strategies[name]
        logger.info(f"Unregistered strategy: {name}")

    def create(
        self,
        name: str,
        config: dict[str, Any] | None = None,
        cache_instance: bool = False,
    ) -> BaseStrategy:
        """
        Create a strategy instance.

        Args:
            name: Strategy name
            config: Strategy configuration (merged with defaults)
            cache_instance: Cache instance for reuse

        Returns:
            Strategy instance

        Raises:
            KeyError: If strategy not found
            ValueError: If strategy is disabled

        Example:
            ```python
            strategy = registry.create(
                name="ma_short",
                config={
                    "short_period": 10,
                    "long_period": 30,
                    "name": "My MA Strategy"
                }
            )
            ```
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found")

        metadata = self._strategies[name]

        if not metadata.enabled:
            raise ValueError(f"Strategy '{name}' is disabled")

        # Check cache
        if cache_instance and name in self._instances:
            logger.debug(f"Returning cached instance: {name}")
            return self._instances[name]

        # Merge config
        final_config = config or {}
        if not final_config.get("name"):
            final_config["name"] = name

        # Create instance
        try:
            strategy = metadata.strategy_class(final_config)

            # Validate configuration
            if not strategy.validate_config():
                missing = strategy.get_required_parameters()
                raise ValueError(
                    f"Invalid configuration for '{name}'. Missing parameters: {missing}"
                )

            # Cache if requested
            if cache_instance:
                self._instances[name] = strategy

            logger.info(f"Created strategy instance: {name}")
            return strategy

        except Exception as e:
            logger.error("Failed to create strategy '%s': %s", name, str(e), exc_info=True)
            raise ValueError(f"Failed to create strategy '{name}': {e}") from e

    def get_metadata(self, name: str) -> StrategyMetadata:
        """
        Get strategy metadata.

        Args:
            name: Strategy name

        Returns:
            Strategy metadata

        Raises:
            KeyError: If strategy not found
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found")

        return self._strategies[name]

    def list_strategies(
        self,
        category: str | None = None,
        enabled_only: bool = False,
        tags: list[str] | None = None,
    ) -> list[StrategyMetadata]:
        """
        List registered strategies with optional filtering.

        Args:
            category: Filter by category
            enabled_only: Only return enabled strategies
            tags: Filter by tags (must match all)

        Returns:
            List of strategy metadata

        Example:
            ```python
            # All enabled trend strategies
            trend_strategies = registry.list_strategies(
                category="trend",
                enabled_only=True
            )

            # Strategies with specific tags
            ma_strategies = registry.list_strategies(
                tags=["ma", "crossover"]
            )
            ```
        """
        strategies = list(self._strategies.values())

        # Filter by category
        if category:
            strategies = [s for s in strategies if s.category == category]

        # Filter by enabled
        if enabled_only:
            strategies = [s for s in strategies if s.enabled]

        # Filter by tags
        if tags:
            strategies = [s for s in strategies if all(tag in s.tags for tag in tags)]

        return strategies

    def find_by_category(self, category: str) -> list[StrategyMetadata]:
        """
        Find all strategies in a category.

        Args:
            category: Category name

        Returns:
            List of strategies in category
        """
        return self.list_strategies(category=category)

    def enable(self, name: str) -> None:
        """Enable a strategy."""
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found")
        self._strategies[name].enabled = True
        logger.info(f"Enabled strategy: {name}")

    def disable(self, name: str) -> None:
        """Disable a strategy."""
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not found")
        self._strategies[name].enabled = False
        logger.info(f"Disabled strategy: {name}")

    def clear_cache(self) -> None:
        """Clear all cached strategy instances."""
        self._instances.clear()
        logger.info("Cleared strategy instance cache")

    def categories(self) -> list[str]:
        """
        Get list of all categories.

        Returns:
            Sorted list of unique categories
        """
        categories = {s.category for s in self._strategies.values()}
        return sorted(categories)

    def __len__(self) -> int:
        """Return number of registered strategies."""
        return len(self._strategies)

    def __contains__(self, name: str) -> bool:
        """Check if strategy is registered."""
        return name in self._strategies

    def __repr__(self) -> str:
        return f"StrategyRegistry(strategies={len(self._strategies)})"


# ============================================================================
# STRATEGY FACTORY - Registry-based factory
# ============================================================================


class StrategyFactory:
    """
    Factory for creating strategies using the registry.

    Provides a convenient interface for strategy creation and
    management. Combines Factory pattern with Registry pattern.

    Example:
        ```python
        factory = StrategyFactory(registry)

        # Create strategy
        strategy = factory.create("ma_short", config={...})

        # Create with context
        context = factory.create_context("ma_short", config={...})
        result = await context.execute_strategy(data)

        # Batch create
        strategies = factory.create_batch([
            ("ma_short", {...}),
            ("rsi", {...})
        ])
        ```
    """

    def __init__(self, registry: StrategyRegistry | None = None):
        """
        Initialize factory with registry.

        Args:
            registry: Strategy registry (creates new if None)
        """
        self.registry = registry or StrategyRegistry()

    def create(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> BaseStrategy:
        """
        Create a strategy instance.

        Args:
            name: Strategy name
            config: Strategy configuration

        Returns:
            Strategy instance
        """
        return self.registry.create(name, config)

    def create_context(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> StrategyContext:
        """
        Create a strategy context with the strategy.

        Args:
            name: Strategy name
            config: Strategy configuration

        Returns:
            Context with strategy set
        """
        strategy = self.create(name, config)
        context = StrategyContext(strategy)
        return context

    def create_batch(
        self,
        strategy_configs: list[tuple[str, dict[str, Any]]],
    ) -> list[BaseStrategy]:
        """
        Create multiple strategies.

        Args:
            strategy_configs: List of (name, config) tuples

        Returns:
            List of strategy instances

        Example:
            ```python
            strategies = factory.create_batch([
                ("ma_short", {"period": 10}),
                ("ma_long", {"period": 30}),
                ("rsi", {"period": 14})
            ])
            ```
        """
        strategies = []
        for name, config in strategy_configs:
            strategy = self.create(name, config)
            strategies.append(strategy)
        return strategies

    def list_available(self) -> list[str]:
        """
        List available strategy names.

        Returns:
            List of strategy names
        """
        return [s.name for s in self.registry.list_strategies(enabled_only=True)]


# ============================================================================
# DECORATOR FOR REGISTRATION
# ============================================================================


def register_strategy(
    name: str,
    description: str = "",
    category: str = "general",
    tags: list[str] | None = None,
    registry: StrategyRegistry | None = None,
):
    """
    Decorator to automatically register strategy classes.

    Example:
        ```python
        registry = StrategyRegistry()

        @register_strategy(
            name="ma_crossover",
            description="Moving average crossover strategy",
            category="trend",
            tags=["ma", "crossover"],
            registry=registry
        )
        class MovingAverageCrossStrategy(BaseStrategy):
            async def execute(self, data):
                # Implementation
                pass

        # Strategy is now registered
        strategy = registry.create("ma_crossover", config={...})
        ```
    """

    def decorator(cls: type[BaseStrategy]) -> type[BaseStrategy]:
        # Use default registry if none provided
        target_registry = registry or _default_registry

        # Register the class
        target_registry.register(
            name=name,
            strategy_class=cls,
            description=description,
            category=category,
            tags=tags,
        )

        return cls

    return decorator


# ============================================================================
# GLOBAL DEFAULT REGISTRY
# ============================================================================

_default_registry = StrategyRegistry()


def get_default_registry() -> StrategyRegistry:
    """Get the global default strategy registry."""
    return _default_registry


def register_default_strategy(name: str, strategy_class: type[BaseStrategy], **kwargs) -> None:
    """
    Register a strategy in the default registry.

    Args:
        name: Strategy name
        strategy_class: Strategy class
        **kwargs: Additional registration parameters
    """
    _default_registry.register(name, strategy_class, **kwargs)


def create_default_strategy(name: str, config: dict[str, Any] | None = None) -> BaseStrategy:
    """
    Create a strategy from the default registry.

    Args:
        name: Strategy name
        config: Strategy configuration

    Returns:
        Strategy instance
    """
    return _default_registry.create(name, config)
