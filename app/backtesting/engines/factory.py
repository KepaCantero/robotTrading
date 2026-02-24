"""
Engine Factory for Backtest Engines.

This module provides a factory for creating backtest engines,
making it easy to instantiate the correct engine type based on
configuration or parameters.

Usage:
    from app.backtesting.engines import EngineFactory, EngineType

    # Create a standard engine
    engine = EngineFactory.create(
        engine_type=EngineType.STANDARD,
        config=my_config,
        strategy=my_strategy,
    )

    # Or use the convenience methods
    engine = EngineFactory.create_standard(config, strategy)
"""

from typing import Any, Dict, Optional, Type, TypeVar

from app.backtesting.base_engine import (
    BaseBacktestEngine,
    EngineType,
)
from app.backtesting.models import BacktestConfig

# Type variable for engine types
EngineT = TypeVar("EngineT", bound=BaseBacktestEngine)


class EngineFactory:
    """
    Factory for creating backtest engines.

    This factory provides a centralized way to create backtest engines
    based on the engine type, ensuring consistent configuration and
    initialization across the codebase.

    The factory supports:
    - STANDARD: Standard single-strategy backtest
    - EXECUTION: Pessimistic execution engine
    - MULTI_STRATEGY: Multi-strategy with capital allocation
    - ROBUST: Long-term robust backtest with checkpointing
    """

    # Registry of engine types to their classes
    _registry: Dict[EngineType, Type[BaseBacktestEngine]] = {}

    @classmethod
    def register(cls, engine_type: EngineType, engine_class: Type[BaseBacktestEngine]) -> None:
        """
        Register an engine class for a given type.

        This allows for custom engine implementations to be registered
        and created through the factory.

        Args:
            engine_type: The engine type identifier
            engine_class: The engine class to register
        """
        cls._registry[engine_type] = engine_class

    @classmethod
    def create(
        cls,
        engine_type: EngineType,
        config: Any,
        **kwargs,
    ) -> BaseBacktestEngine:
        """
        Create a backtest engine of the specified type.

        Args:
            engine_type: The type of engine to create
            config: Configuration for the engine
            **kwargs: Additional arguments passed to the engine constructor

        Returns:
            Configured backtest engine instance

        Raises:
            ValueError: If the engine type is not supported
        """
        # Lazy import to avoid circular dependencies
        cls._ensure_registered(engine_type)

        if engine_type not in cls._registry:
            raise ValueError(
                f"Unsupported engine type: {engine_type}. "
                f"Supported types: {list(cls._registry.keys())}"
            )

        engine_class = cls._registry[engine_type]
        return engine_class(config, **kwargs)

    @classmethod
    def _ensure_registered(cls, engine_type: EngineType) -> None:
        """Ensure all engine types are registered (lazy loading)."""
        if cls._registry:
            return

        # Import and register all engine types
        try:
            from app.backtesting.engines.standard_engine import StandardBacktestEngine
            cls._registry[EngineType.STANDARD] = StandardBacktestEngine
        except ImportError:
            pass

        try:
            from app.backtesting.engines.execution_engine import ExecutionBacktestEngine
            cls._registry[EngineType.EXECUTION] = ExecutionBacktestEngine
        except ImportError:
            pass

        try:
            from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktestEngine
            cls._registry[EngineType.MULTI_STRATEGY] = MultiStrategyBacktestEngine
        except ImportError:
            pass

        try:
            from app.backtesting.engines.robust_engine import RobustBacktestEngine
            cls._registry[EngineType.ROBUST] = RobustBacktestEngine
        except ImportError:
            pass

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    @classmethod
    def create_standard(
        cls,
        config: BacktestConfig,
        strategy: Optional[Any] = None,
        diagnostic_logger: Optional[Any] = None,
        strategy_name: str = "unknown",
        enable_risk_envelope: bool = True,
        **kwargs,
    ) -> BaseBacktestEngine:
        """
        Create a standard backtest engine.

        The standard engine is suitable for single-strategy backtests
        with full compliance integration.

        Args:
            config: Backtest configuration
            strategy: Strategy instance
            diagnostic_logger: Optional diagnostic logger
            strategy_name: Name of the strategy
            enable_risk_envelope: Enable risk envelope validation
            **kwargs: Additional arguments

        Returns:
            StandardBacktestEngine instance
        """
        return cls.create(
            EngineType.STANDARD,
            config,
            strategy=strategy,
            diagnostic_logger=diagnostic_logger,
            strategy_name=strategy_name,
            enable_risk_envelope=enable_risk_envelope,
            **kwargs,
        )

    @classmethod
    def create_execution(
        cls,
        config: BacktestConfig,
        execution_type: str = "pessimistic",
        base_slippage_bps: Optional[Any] = None,
        **kwargs,
    ) -> BaseBacktestEngine:
        """
        Create an execution backtest engine.

        The execution engine implements pessimistic execution to eliminate
        look-ahead bias and provide more realistic backtesting results.

        Args:
            config: Backtest configuration
            execution_type: Type of execution (optimistic, pessimistic, realistic)
            base_slippage_bps: Base slippage in basis points
            **kwargs: Additional arguments

        Returns:
            ExecutionBacktestEngine instance
        """
        from app.backtesting.base_engine import ExecutionType as ExecType

        exec_type = ExecType(execution_type.lower())

        return cls.create(
            EngineType.EXECUTION,
            config,
            execution_type=exec_type,
            base_slippage_bps=base_slippage_bps,
            **kwargs,
        )

    @classmethod
    def create_multi_strategy(
        cls,
        allocation_manager: Any,
        strategies: Dict[str, Any],
        config_params: Dict[str, Any],
        **kwargs,
    ) -> BaseBacktestEngine:
        """
        Create a multi-strategy backtest engine.

        The multi-strategy engine manages multiple strategies with
        capital allocation and dynamic reallocation.

        Args:
            allocation_manager: Capital allocation manager
            strategies: Dictionary of strategy instances
            config_params: Common backtest parameters
            **kwargs: Additional arguments

        Returns:
            MultiStrategyBacktestEngine instance
        """
        # Multi-strategy has a different constructor signature
        cls._ensure_registered(EngineType.MULTI_STRATEGY)

        if EngineType.MULTI_STRATEGY not in cls._registry:
            raise ValueError("MultiStrategyBacktestEngine not available")

        engine_class = cls._registry[EngineType.MULTI_STRATEGY]
        return engine_class(
            allocation_manager=allocation_manager,
            strategies=strategies,
            config_params=config_params,
            **kwargs,
        )

    @classmethod
    def create_robust(
        cls,
        config: Any,  # RobustBacktestConfig
        **kwargs,
    ) -> BaseBacktestEngine:
        """
        Create a robust backtest engine.

        The robust engine is designed for long-term backtests (25+ years)
        with checkpointing and memory-efficient processing.

        Args:
            config: Robust backtest configuration
            **kwargs: Additional arguments

        Returns:
            RobustBacktestEngine instance
        """
        return cls.create(
            EngineType.ROBUST,
            config,
            **kwargs,
        )

    @classmethod
    def get_supported_types(cls) -> list:
        """
        Get list of supported engine types.

        Returns:
            List of supported EngineType values
        """
        cls._ensure_registered(EngineType.STANDARD)  # Ensure registry is populated
        return list(cls._registry.keys())

    @classmethod
    def get_engine_class(cls, engine_type: EngineType) -> Optional[Type[BaseBacktestEngine]]:
        """
        Get the engine class for a given type.

        Args:
            engine_type: The engine type

        Returns:
            The engine class, or None if not registered
        """
        cls._ensure_registered(engine_type)
        return cls._registry.get(engine_type)


# =========================================================================
# ENGINE REGISTRY INITIALIZATION
# =========================================================================

def _initialize_registry():
    """Initialize the engine registry with all built-in engines."""
    # This is called on module import to ensure all engines are available
    try:
        from app.backtesting.engines.standard_engine import StandardBacktestEngine
        EngineFactory.register(EngineType.STANDARD, StandardBacktestEngine)
    except ImportError:
        pass

    try:
        from app.backtesting.engines.execution_engine import ExecutionBacktestEngine
        EngineFactory.register(EngineType.EXECUTION, ExecutionBacktestEngine)
    except ImportError:
        pass

    try:
        from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktestEngine
        EngineFactory.register(EngineType.MULTI_STRATEGY, MultiStrategyBacktestEngine)
    except ImportError:
        pass

    try:
        from app.backtesting.engines.robust_engine import RobustBacktestEngine
        EngineFactory.register(EngineType.ROBUST, RobustBacktestEngine)
    except ImportError:
        pass


# Initialize registry on import
_initialize_registry()
