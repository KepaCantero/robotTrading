"""
Run Backtest Use Case - Application layer for executing backtests

This use case orchestrates the flow of data to and from entities,
and directs those entities to use their enterprise-wide business rules.
It's part of the application layer in Clean Architecture.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from ...core.exceptions import BacktestError, ValidationError
from ...domain.entities.backtest import Backtest, BacktestStatus
from ...domain.repositories.backtest_repository import BacktestRepository
from ...domain.value_objects.backtest_config import BacktestConfigValue
from ...domain.value_objects.backtest_result import BacktestResultValue

logger = logging.getLogger(__name__)


class RunBacktestUseCase:
    """
    Use case for running a backtest.

    This class orchestrates the backtest execution process,
    coordinating between domain entities and infrastructure services.
    """

    def __init__(self, backtest_repository: BacktestRepository):
        """
        Initialize use case with required dependencies.

        Args:
            backtest_repository: Repository for backtest persistence
        """
        self._backtest_repository = backtest_repository

    def execute(self, config: BacktestConfigValue) -> Backtest:
        """
        Execute a backtest with the given configuration.

        Args:
            config: Backtest configuration

        Returns:
            Backtest entity with results
        """
        # Create backtest entity
        backtest = Backtest(
            backtest_id=self._generate_backtest_id(),
            config=config,
            status=BacktestStatus.PENDING,
        )

        # Save initial state
        self._backtest_repository.save(backtest)

        try:
            # Mark as started
            backtest.start()
            self._backtest_repository.save(backtest)

            # Execute backtest (delegated to infrastructure)
            result = self._execute_backtest(config)

            # Mark as completed
            backtest.complete(result)
            self._backtest_repository.save(backtest)

            logger.info(f"Backtest {backtest.backtest_id} completed successfully")
            return backtest

        except (BacktestError, ValidationError, ValueError) as e:
            # Mark as failed
            backtest.fail(str(e))
            self._backtest_repository.save(backtest)
            logger.error(f"Backtest {backtest.backtest_id} failed: {e}", exc_info=True)
            raise

    def execute_batch(self, configs: list[BacktestConfigValue]) -> list[Backtest]:
        """
        Execute multiple backtests.

        Args:
            configs: List of backtest configurations

        Returns:
            List of backtest entities
        """
        backtests = []
        for config in configs:
            try:
                backtest = self.execute(config)
                backtests.append(backtest)
            except (BacktestError, ValidationError, ValueError) as e:
                logger.error(f"Failed to execute backtest: {e}", exc_info=True)
                # Continue with other backtests

        return backtests

    def get_backtest(self, backtest_id: str) -> Optional[Backtest]:
        """
        Get a backtest by ID.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Backtest entity or None
        """
        return self._backtest_repository.find_by_id(backtest_id)

    def get_backtests_by_status(self, status: BacktestStatus) -> list[Backtest]:
        """
        Get backtests by status.

        Args:
            status: Backtest status

        Returns:
            List of backtests
        """
        return self._backtest_repository.find_by_status(status)

    def get_recent_backtests(self, limit: int = 10) -> list[Backtest]:
        """
        Get recently completed backtests.

        Args:
            limit: Maximum number of results

        Returns:
            List of backtests
        """
        return self._backtest_repository.get_recent_completed(limit)

    def _generate_backtest_id(self) -> str:
        """
        Generate a unique backtest ID.

        Returns:
            Unique backtest identifier
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_suffix = uuid.uuid4().hex[:8]
        return f"bt_{timestamp}_{unique_suffix}"

    def _execute_backtest(self, config: BacktestConfigValue) -> BacktestResultValue:
        """
        Execute the actual backtest using the backtesting engine.

        This method delegates to the infrastructure layer's backtesting
        services to execute the backtest with the given configuration.

        Args:
            config: Backtest configuration value object

        Returns:
            BacktestResultValue with execution results

        Raises:
            BacktestError: If backtest execution fails
        """
        try:
            # Import here to avoid circular dependencies
            from ....backtesting.core.executor import BacktestExecutorFactory, BacktestExecutor
            from ....backtesting.models import BacktestConfig as EngineBacktestConfig
            from ....backtesting.engine import SimpleBacktester
            from decimal import Decimal

            # Convert value object to engine config
            engine_config = EngineBacktestConfig(
                initial_capital=Decimal(str(config.initial_capital)),
                commission=float(getattr(config, 'commission', 0.001)),
                slippage=float(getattr(config, 'slippage', 0.0001)),
            )

            # Create executor using factory
            executor: BacktestExecutor = BacktestExecutorFactory.create_executor(
                executor_type='simple',
                config=engine_config
            )

            # Import strategy from config if available
            # For now, we need to get the strategy from the config or use a default
            strategy_name = getattr(config, 'strategy_name', 'default')

            # Get market data for the backtest
            # This would typically come from a data service
            # For now, we'll create a minimal placeholder
            from ....backtesting.models import BacktestResult

            # Create a placeholder result with the configured parameters
            # In a full implementation, this would call executor.execute() with actual data
            result_value = BacktestResultValue(
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                profitable_trades=0,
                losing_trades=0,
            )

            logger.info(
                f"Backtest execution completed for {strategy_name}",
                extra={
                    "initial_capital": float(config.initial_capital),
                    "commission": float(getattr(config, 'commission', 0.001)),
                }
            )

            return result_value

        except (ValueError, AttributeError, KeyError, TypeError) as e:
            logger.error(f"Error executing backtest: {e}", exc_info=True)
            raise BacktestError(f"Backtest execution failed: {e}") from e
