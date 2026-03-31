"""Backward-compatibility re-export. Canonical module: app.services.automated_backtest."""

from app.services.automated_backtest import (
    AutomatedBacktestRunner,
    PortfolioAnalyzer,
    run_automated_backtest,
)

__all__ = ["AutomatedBacktestRunner", "PortfolioAnalyzer", "run_automated_backtest"]
