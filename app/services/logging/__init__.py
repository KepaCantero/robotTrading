"""
Logging module - re-exports from infrastructure layer for backward compatibility.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name == "AppendOnlyLog":
        from app.infrastructure.logging.append_only_log import AppendOnlyLog

        return AppendOnlyLog
    if name == "TradingDecisionLogger":
        from app.infrastructure.logging.trading_decision_logger import TradingDecisionLogger

        return TradingDecisionLogger
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AppendOnlyLog",
    "TradingDecisionLogger",
]
