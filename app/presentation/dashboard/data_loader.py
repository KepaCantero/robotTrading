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
        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
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
        """
        Get current status of strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Strategy status string (Idle, Running, Paused, Error)
        """
        # Try to load strategy status from backtest results
        results = self.load_backtest_results(strategy_name)
        if results:
            # Check if strategy is currently running (has recent activity)
            last_updated = results.get("timestamp")
            if last_updated:
                return "Completed"

        # Check paper trading logs for active status
        paper_log = self.paper_trading_path.parent / f"paper_trading_{strategy_name}.log"
        if paper_log.exists():
            try:
                # Read last few lines to check for recent activity
                with open(paper_log, "r") as f:
                    lines = f.readlines()[-10:] if f.readlines() else []
                if lines and "running" in str(lines).lower():
                    return "Running"
            except (FileNotFoundError, PermissionError, IOError, OSError):
                pass

        # Default to Idle status
        return "Idle"

    def _get_last_pnl(self, strategy_name: str) -> float:
        """
        Get last PnL for strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Last PnL value or 0.0 if not available
        """
        # Try to load PnL from backtest results
        results = self.load_backtest_results(strategy_name)
        if results:
            # Look for PnL in various possible fields
            pnl = results.get("total_pnl") or results.get("pnl") or results.get("final_pnl")
            if pnl is not None:
                try:
                    return float(pnl)
                except (ValueError, TypeError):
                    pass

        # Try to load from paper trading logs
        paper_log = self.paper_trading_path.parent / f"paper_trading_{strategy_name}.log"
        if paper_log.exists():
            try:
                with open(paper_log, "r") as f:
                    content = f.read()
                # Look for PnL pattern in log (e.g., "PnL: 123.45")
                import re

                pnl_match = re.search(r'[Pp][Nn][Ll]:\s*[-+]?\d*\.?\d+', content)
                if pnl_match:
                    try:
                        return float(pnl_match.group().split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
            except (FileNotFoundError, PermissionError, IOError, OSError):
                pass

        # Default to 0.0 if no PnL found
        return 0.0
