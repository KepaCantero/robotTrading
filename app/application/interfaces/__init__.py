"""
Application Interfaces - Contracts for presentation layer.

Interfaces define the contracts for presenting data to the UI layer,
following the Humble Object pattern to keep presentation logic testable.
"""

from .backtest_presenter import BacktestPresenter

__all__ = [
    "BacktestPresenter",
]
