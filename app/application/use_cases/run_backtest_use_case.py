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
        Execute the actual backtest (delegated to infrastructure).

        This method is a placeholder for the actual backtest execution
        logic, which should be implemented in the infrastructure layer.

        Args:
            config: Backtest configuration

        Returns:
            Backtest results
        """
        # This would be implemented by infrastructure services
        # For now, return a placeholder result
        raise NotImplementedError("Backtest execution must be implemented in infrastructure layer")
