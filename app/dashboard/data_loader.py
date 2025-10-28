"""
Data Loader for Dashboard

Loads data from backtesting results and paper trading logs.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DashboardDataLoader:
    """Loader for dashboard data."""

    def __init__(self):
        """Initialize data loader."""
        self.backtest_path = Path("reports/backtesting")
        self.paper_trading_path = Path("app/providers/paper_trading.py")

    def load_backtest_results(self, strategy_name: str) -> Optional[Dict]:
        """
        Load backtest results for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Dictionary with backtest results or None
        """
        result_file = self.backtest_path / f"results_{strategy_name}.json"

        if not result_file.exists():
            logger.warning(f"No backtest results found for {strategy_name}")
            return None

        try:
            with open(result_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading backtest results: {e}")
            return None

    def list_strategies(self) -> List[Dict]:
        """
        List all available strategies.

        Returns:
            List of strategy information dictionaries
        """
        strategies = []

        # Check app/strategies for strategy files
        strategies_path = Path("app/strategies")
        for file in strategies_path.glob("*.py"):
            if file.name.startswith("_"):
                continue

            strategy_name = file.stem
            strategy_info = {
                "name": strategy_name,
                "file": file.name,
                "status": self._get_strategy_status(strategy_name),
                "last_pnl": self._get_last_pnl(strategy_name),
            }
            strategies.append(strategy_info)

        return strategies

    def _get_strategy_status(self, strategy_name: str) -> str:
        """Get current status of strategy."""
        # TODO: Implement actual status check
        return "Idle"

    def _get_last_pnl(self, strategy_name: str) -> float:
        """Get last PnL for strategy."""
        # TODO: Implement actual PnL retrieval
        return 0.0
