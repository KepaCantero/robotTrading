"""
Base executor for backtesting operations.

This module provides abstract base classes for backtest execution,
following the Template Method pattern for extensible backtesting strategies.

Updated in Phase 2 with complete type hints and improved error handling.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process, Queue
from typing import Any, Dict, List, Literal, Optional, Type, Union

from app.backtesting.models import BacktestConfig, BacktestResult

logger = logging.getLogger(__name__)


# Module-level function for multiprocessing (must be picklable)
def _run_backtest_process(
    config: BacktestConfig,
    quotes: List[Any],
    strategy: Any,
    strategy_name: str,
    enable_risk_envelope: bool,
    result_queue: Queue,
) -> None:
    """
    Run backtest in subprocess (module-level function for pickling).

    Args:
        config: Backtest configuration
        quotes: List of market data quotes
        strategy: Trading strategy instance
        strategy_name: Name for the strategy
        enable_risk_envelope: Enable risk envelope tracking
        result_queue: Queue to put results in
    """
    try:
        # Re-import in subprocess
        from app.backtesting.engine import SimpleBacktester

        backtester = SimpleBacktester(
            config=config,
            strategy=strategy,
            strategy_name=strategy_name,
            enable_risk_envelope=enable_risk_envelope,
        )

        # Generate signals in subprocess
        signals = []
        for quote in quotes:
            quote_signals = strategy.generate_signals(quote)
            signals.extend(quote_signals)

        result = backtester.run_backtest(quotes, signals=signals)

        # Put result in queue (BacktestResult should be pickleable)
        result_queue.put(('success', result))
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        result_queue.put(('error', str(e)))


# Type aliases for better readability
StrategyType = Any  # Could be more specific if we have a Strategy base class
QuotesType = List[Any]
SignalsType = List[Any]
MetricsDict = Dict[str, Union[float, int, str]]
OptionalMetrics = Optional[MetricsDict]


class BacktestExecutor(ABC):
    """
    Base class for all backtest executors.

    This abstract class defines the interface for executing backtests,
    with built-in validation and error handling.
    """

    def __init__(self, config: BacktestConfig) -> None:
        """
        Initialize executor.

        Args:
            config: Backtest configuration
        """
        self.config = config
        self._execution_count: int = 0

    @abstractmethod
    def execute(
        self,
        quotes: QuotesType,
        strategy: StrategyType,
        **kwargs: Any,
    ) -> BacktestResult:
        """
        Execute backtest and return results.

        Args:
            quotes: List of market data quotes
            strategy: Trading strategy instance
            **kwargs: Additional execution parameters

        Returns:
            BacktestResult with performance metrics

        Raises:
            ValueError: If inputs are invalid
            RuntimeError: If execution fails
        """
        raise NotImplementedError

    def validate_inputs(
        self,
        quotes: QuotesType,
        strategy: StrategyType,
    ) -> None:
        """
        Validate inputs before execution.

        Args:
            quotes: List of market data quotes
            strategy: Trading strategy instance

        Raises:
            ValueError: If validation fails
        """
        if not quotes:
            raise ValueError("Quotes cannot be empty")

        if not strategy:
            raise ValueError("Strategy cannot be None")

        if self.config.initial_capital <= 0:
            raise ValueError(f"Initial capital must be positive: {self.config.initial_capital}")

        logger.debug(
            f"Inputs validated: {len(quotes)} quotes, " f"strategy: {type(strategy).__name__}"
        )

    def _pre_execute(
        self,
        quotes: QuotesType,
        strategy: StrategyType,
    ) -> None:
        """
        Hook called before execution.

        Override in subclasses for custom pre-execution logic.
        """
        self.validate_inputs(quotes, strategy)
        self._execution_count += 1

    def _post_execute(self, result: BacktestResult) -> None:
        """
        Hook called after execution.

        Override in subclasses for custom post-execution logic.
        """
        logger.debug(f"Execution #{self._execution_count} completed: {result.final_capital}")

    @property
    def execution_count(self) -> int:
        """Get number of executions performed."""
        return self._execution_count


class SimpleBacktestExecutor(BacktestExecutor):
    """
    Simple executor for basic backtesting operations.

    This executor uses the SimpleBacktester for straightforward
    backtest execution without advanced features.
    """

    def execute(
        self,
        quotes: QuotesType,
        strategy: StrategyType,
        **kwargs: Any,
    ) -> BacktestResult:
        """
        Execute simple backtest.

        Args:
            quotes: List of market data quotes
            strategy: Trading strategy instance
            **kwargs: Additional parameters:
                - strategy_name: Name for the strategy
                - signals: Pre-computed signals (optional)
                - diagnostic_logger: Logger for diagnostics
                - enable_risk_envelope: Enable risk envelope tracking

        Returns:
            BacktestResult with performance metrics
        """
        self._pre_execute(quotes, strategy)

        # Import here to avoid circular dependency
        from app.backtesting.engine import SimpleBacktester

        # Get strategy name
        strategy_name: str = kwargs.get('strategy_name', getattr(strategy, 'name', 'unknown'))

        # Create backtester
        backtester = SimpleBacktester(
            config=self.config,
            strategy=strategy,
            strategy_name=strategy_name,
            diagnostic_logger=kwargs.get('diagnostic_logger'),
            enable_risk_envelope=kwargs.get('enable_risk_envelope', True),
        )

        # Get or generate signals
        signals: Optional[SignalsType] = kwargs.get('signals')
        if signals is None:
            signals = []
            for quote in quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)

        # Execute backtest
        result: BacktestResult = backtester.run_backtest(quotes, signals=signals)

        self._post_execute(result)
        return result


class ParallelBacktestExecutor(BacktestExecutor):
    """
    Executor for parallel backtesting operations.

    This executor can run multiple backtests concurrently using
    ThreadPoolExecutor for I/O-bound operations.
    """

    def __init__(
        self,
        config: BacktestConfig,
        max_workers: Optional[int] = None,
    ) -> None:
        """
        Initialize parallel executor.

        Args:
            config: Backtest configuration
            max_workers: Maximum number of worker threads (None for auto)
        """
        super().__init__(config)
        self.max_workers = max_workers

    def execute_batch(
        self,
        quotes: QuotesType,
        strategies: List[StrategyType],
        **kwargs: Any,
    ) -> List[BacktestResult]:
        """
        Execute multiple backtests in parallel.

        Args:
            quotes: List of market data quotes
            strategies: List of trading strategy instances
            **kwargs: Additional execution parameters

        Returns:
            List of BacktestResult objects
        """
        results: List[BacktestResult] = []
        max_workers = self.max_workers or min(len(strategies), 4)

        def run_single(strategy: StrategyType) -> Optional[BacktestResult]:
            """Run single backtest."""
            try:
                return self.execute(quotes, strategy, **kwargs)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Error in parallel execution: {e}", exc_info=True)
                return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_single, s): s for s in strategies}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        return results

    def execute(
        self,
        quotes: QuotesType,
        strategy: StrategyType,
        **kwargs: Any,
    ) -> BacktestResult:
        """
        Execute single backtest (delegates to SimpleBacktestExecutor).

        Args:
            quotes: List of market data quotes
            strategy: Trading strategy instance
            **kwargs: Additional execution parameters

        Returns:
            BacktestResult with performance metrics
        """
        executor = SimpleBacktestExecutor(self.config)
        return executor.execute(quotes, strategy, **kwargs)


class ProcessPoolBacktestExecutor(BacktestExecutor):
    """
    Executor using process pool for CPU-bound operations.

    This executor uses multiprocessing instead of threading to avoid
    mutex/locking issues with machine learning libraries.
    """

    def __init__(
        self,
        config: BacktestConfig,
        max_processes: Optional[int] = None,
    ) -> None:
        """
        Initialize process pool executor.

        Args:
            config: Backtest configuration
            max_processes: Maximum number of processes (None for auto)
        """
        super().__init__(config)
        self.max_processes = max_processes

    def execute(
        self,
        quotes: QuotesType,
        strategy: StrategyType,
        **kwargs: Any,
    ) -> BacktestResult:
        """
        Execute backtest using process isolation.

        This method spawns a new process to run the backtest, avoiding
        threading issues with ML libraries.

        Args:
            quotes: List of market data quotes
            strategy: Trading strategy instance
            **kwargs: Additional execution parameters

        Returns:
            BacktestResult with performance metrics
        """
        return self._execute_in_process(quotes, strategy, **kwargs)

    def _execute_in_process(
        self,
        quotes: QuotesType,
        strategy: StrategyType,
        **kwargs: Any,
    ) -> BacktestResult:
        """
        Execute backtest in isolated process.

        Args:
            quotes: List of market data quotes
            strategy: Trading strategy instance
            **kwargs: Additional execution parameters

        Returns:
            BacktestResult with performance metrics
        """
        # Import module-level function for pickling
        from app.backtesting.core.executor import _run_backtest_process

        result_queue: Queue = Queue()

        strategy_name = kwargs.get('strategy_name', getattr(strategy, 'name', 'unknown'))

        p = Process(
            target=_run_backtest_process,
            args=(
                self.config,
                quotes,
                strategy,
                strategy_name,
                kwargs.get('enable_risk_envelope', True),
                result_queue,
            ),
        )
        p.start()
        p.join(timeout=300)  # 5 minute timeout

        if p.is_alive():
            p.terminate()
            p.join()
            raise RuntimeError("Backtest execution timeout")

        status, data = result_queue.get()

        if status == 'success':
            return data
        else:
            raise RuntimeError(f"Backtest execution failed: {data}")


class BacktestExecutorFactory:
    """
    Factory for creating appropriate executor instances.

    This factory provides a centralized way to create executors
    based on configuration parameters.
    """

    ExecutorType = Literal[
        'simple',
        'parallel',
        'process',
    ]

    _executor_registry: Dict[ExecutorType, Type[BacktestExecutor]] = {
        'simple': SimpleBacktestExecutor,
        'parallel': ParallelBacktestExecutor,
        'process': ProcessPoolBacktestExecutor,
    }

    @classmethod
    def create(
        cls,
        config: BacktestConfig,
        executor_type: ExecutorType = 'simple',
        max_workers: Optional[int] = None,
    ) -> BacktestExecutor:
        """
        Create appropriate executor instance.

        Args:
            config: Backtest configuration
            executor_type: Type of executor ('simple', 'parallel', 'process')
            max_workers: Maximum workers/processes for parallel execution

        Returns:
            BacktestExecutor instance

        Raises:
            ValueError: If executor_type is not recognized

        Example:
            >>> executor = BacktestExecutorFactory.create(
            ...     config=my_config,
            ...     executor_type='process',  # Avoid threading issues
            ...     max_workers=4
            ... )
        """
        executor_class = cls._executor_registry.get(executor_type)

        if executor_class is None:
            raise ValueError(
                f"Unknown executor type: {executor_type}. "
                f"Valid types: {list(cls._executor_registry.keys())}"
            )

        if executor_type == 'simple':
            return executor_class(config)
        elif executor_type == 'parallel':
            return executor_class(config, max_workers=max_workers)
        elif executor_type == 'process':
            # ProcessPoolBacktestExecutor uses max_processes parameter
            return executor_class(config, max_processes=max_workers)
        else:
            return executor_class(config)

    @classmethod
    def register_executor(
        cls,
        executor_type: ExecutorType,
        executor_class: Type[BacktestExecutor],
    ) -> None:
        """
        Register a custom executor type.

        Args:
            executor_type: Name for the executor type
            executor_class: Executor class to register

        Example:
            >>> class CustomExecutor(BacktestExecutor):
            ...     pass
            >>> BacktestExecutorFactory.register_executor(
            ...     'custom',
            ...     CustomExecutor
            ... )
        """
        cls._executor_registry[executor_type] = executor_class
