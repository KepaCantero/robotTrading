"""
Meta Analyzer Module for Backtesting

Provides advanced analysis, auditing, and persistence capabilities for backtest results.
"""

from .meta_analyzer import BacktestMetaAnalyzer
from .audit_trail import AuditTrail
from .learning_storage import LearningEngineStorage
from .integration import integrate_meta_analyzer_with_runner, save_backtest_audit_and_weights

__all__ = [
    "BacktestMetaAnalyzer",
    "AuditTrail",
    "LearningEngineStorage",
    "integrate_meta_analyzer_with_runner",
    "save_backtest_audit_and_weights",
]

