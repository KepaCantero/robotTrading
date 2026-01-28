"""
File-Based Backtest Repository Implementation

A file-system based implementation of the backtest repository for
persisting backtest results to disk.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from ...domain.entities.backtest import (
    Backtest,
    BacktestStatus,
    BacktestType,
)
from ...domain.repositories.backtest_repository import BacktestRepository
from ...domain.value_objects.backtest_config import BacktestConfigValue
from ...domain.value_objects.backtest_result import BacktestResultValue

logger = logging.getLogger(__name__)


class FileBacktestRepository(BacktestRepository):
    """
    File-system implementation of backtest repository.

    This implementation stores backtests as JSON files on disk,
    organized by status and date.
    """

    def __init__(self, base_dir: str = "data/backtests"):
        """
        Initialize file repository.

        Args:
            base_dir: Base directory for storing backtests
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for different statuses
        for status in BacktestStatus:
            (self.base_dir / status.value).mkdir(exist_ok=True)

    def save(self, backtest: Backtest) -> None:
        """
        Save a backtest to disk.

        Args:
            backtest: Backtest entity to save
        """
        # Determine file path based on status
        status_dir = self.base_dir / backtest.status.value
        file_path = status_dir / f"{backtest.backtest_id}.json"

        # Serialize backtest to JSON
        data = self._serialize_backtest(backtest)

        # Write to file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"Saved backtest to {file_path}")

    def find_by_id(self, backtest_id: str) -> Optional[Backtest]:
        """
        Find a backtest by ID.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Backtest entity or None if not found
        """
        # Search in all status directories
        for status in BacktestStatus:
            file_path = self.base_dir / status.value / f"{backtest_id}.json"
            if file_path.exists():
                return self._deserialize_backtest(file_path)

        return None

    def find_by_status(self, status: BacktestStatus) -> List[Backtest]:
        """
        Find backtests by status.

        Args:
            status: Backtest status

        Returns:
            List of backtests with the specified status
        """
        status_dir = self.base_dir / status.value
        backtests = []

        for file_path in status_dir.glob("*.json"):
            try:
                backtest = self._deserialize_backtest(file_path)
                if backtest:
                    backtests.append(backtest)
            except Exception as e:
                logger.warning(f"Error loading backtest from {file_path}: {e}")

        return backtests

    def find_by_type(self, backtest_type: BacktestType) -> List[Backtest]:
        """
        Find backtests by type.

        Args:
            backtest_type: Backtest type

        Returns:
            List of backtests of the specified type
        """
        all_backtests = self.find_all()
        return [bt for bt in all_backtests if bt.config.backtest_type == backtest_type]

    def find_all(self, limit: int = 100, offset: int = 0) -> List[Backtest]:
        """
        Find all backtests with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of backtests
        """
        all_backtests = []

        # Load from all status directories
        for status in BacktestStatus:
            status_dir = self.base_dir / status.value
            for file_path in status_dir.glob("*.json"):
                try:
                    backtest = self._deserialize_backtest(file_path)
                    if backtest:
                        all_backtests.append(backtest)
                except Exception as e:
                    logger.warning(f"Error loading backtest from {file_path}: {e}")

        # Sort by created date descending
        all_backtests.sort(key=lambda bt: bt.created_at, reverse=True)
        return all_backtests[offset : offset + limit]

    def delete(self, backtest_id: str) -> bool:
        """
        Delete a backtest by ID.

        Args:
            backtest_id: Backtest identifier

        Returns:
            True if deleted, False if not found
        """
        # Search in all status directories
        for status in BacktestStatus:
            file_path = self.base_dir / status.value / f"{backtest_id}.json"
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted backtest: {file_path}")
                return True

        return False

    def count_by_status(self, status: BacktestStatus) -> int:
        """
        Count backtests by status.

        Args:
            status: Backtest status

        Returns:
            Count of backtests with the specified status
        """
        status_dir = self.base_dir / status.value
        return len(list(status_dir.glob("*.json")))

    def get_recent_completed(self, limit: int = 10) -> List[Backtest]:
        """
        Get recently completed backtests.

        Args:
            limit: Maximum number of results

        Returns:
            List of recently completed backtests
        """
        completed = self.find_by_status(BacktestStatus.COMPLETED)
        # Sort by completion time descending
        completed.sort(key=lambda bt: bt.completed_at or bt.created_at, reverse=True)
        return completed[:limit]

    def _serialize_backtest(self, backtest: Backtest) -> Dict:
        """Serialize backtest to dictionary."""
        return {
            'backtest_id': backtest.backtest_id,
            'status': backtest.status.value,
            'error_message': backtest.error_message,
            'created_at': backtest.created_at.isoformat(),
            'started_at': backtest.started_at.isoformat() if backtest.started_at else None,
            'completed_at': backtest.completed_at.isoformat() if backtest.completed_at else None,
            'config': backtest.config.to_dict() if backtest.config else None,
            'result': backtest.result.to_dict() if backtest.result else None,
        }

    def _deserialize_backtest(self, file_path: Path) -> Optional[Backtest]:
        """Deserialize backtest from file."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Parse config
        config = BacktestConfigValue.from_dict(data['config']) if data.get('config') else None

        # Parse result
        result = None
        if data.get('result'):
            result_data = data['result']
            result = BacktestResultValue(
                initial_capital=Decimal(result_data['initial_capital']),
                final_capital=Decimal(result_data['final_capital']),
                total_return=Decimal(result_data['total_return']),
                total_return_pct=Decimal(result_data['total_return_pct']),
                sharpe_ratio=(
                    Decimal(result_data['sharpe_ratio'])
                    if result_data.get('sharpe_ratio')
                    else None
                ),
                sortino_ratio=(
                    Decimal(result_data['sortino_ratio'])
                    if result_data.get('sortino_ratio')
                    else None
                ),
                max_drawdown=(
                    Decimal(result_data['max_drawdown'])
                    if result_data.get('max_drawdown')
                    else None
                ),
                volatility=(
                    Decimal(result_data['volatility']) if result_data.get('volatility') else None
                ),
                var_95=Decimal(result_data['var_95']) if result_data.get('var_95') else None,
                total_trades=result_data.get('total_trades', 0),
                winning_trades=result_data.get('winning_trades', 0),
                losing_trades=result_data.get('losing_trades', 0),
                win_rate=Decimal(result_data['win_rate']) if result_data.get('win_rate') else None,
                avg_win=Decimal(result_data['avg_win']) if result_data.get('avg_win') else None,
                avg_loss=Decimal(result_data['avg_loss']) if result_data.get('avg_loss') else None,
                profit_factor=(
                    Decimal(result_data['profit_factor'])
                    if result_data.get('profit_factor')
                    else None
                ),
            )

        # Parse status
        status = BacktestStatus(data['status'])

        # Parse dates
        created_at = datetime.fromisoformat(data['created_at'])
        started_at = datetime.fromisoformat(data['started_at']) if data.get('started_at') else None
        completed_at = (
            datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None
        )

        return Backtest(
            backtest_id=data['backtest_id'],
            config=config,
            status=status,
            result=result,
            error_message=data.get('error_message'),
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
        )
