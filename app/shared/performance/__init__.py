"""
Performance Module

This module provides unified performance calculation utilities:
- metrics: Unified performance metrics (Sharpe, Sortino, MaxDrawdown, etc.)
- numba_accelerators: Numba JIT-compiled performance functions
- numba_enforcer: Mandatory Numba enforcement utilities
- statsmodels_fallback: Fallback implementations when statsmodels unavailable

Usage:
    from app.shared.performance.metrics import (
        sharpe_ratio,
        sortino_ratio,
        max_drawdown,
        PerformanceMetricsCalculator,
    )
"""

from app.shared.performance.metrics import (
    DrawdownResult,
    PerformanceMetricsCalculator,
    PerformanceResult,
    SharpeRatioResult,
    calmar_ratio,
    max_drawdown,
    omega_ratio,
    sharpe_ratio,
    sortino_ratio,
    ulcer_index,
)

__all__ = [
    "DrawdownResult",
    # Metrics calculator
    "PerformanceMetricsCalculator",
    "PerformanceResult",
    # Result dataclasses
    "SharpeRatioResult",
    "calmar_ratio",
    "max_drawdown",
    "omega_ratio",
    # Convenience functions
    "sharpe_ratio",
    "sortino_ratio",
    "ulcer_index",
]
