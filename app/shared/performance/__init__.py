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
    PerformanceMetricsCalculator,
    SharpeRatioResult,
    DrawdownResult,
    PerformanceResult,
    sharpe_ratio,
    sortino_ratio,
    calmar_ratio,
    omega_ratio,
    max_drawdown,
    ulcer_index,
)

__all__ = [
    # Metrics calculator
    "PerformanceMetricsCalculator",
    # Result dataclasses
    "SharpeRatioResult",
    "DrawdownResult",
    "PerformanceResult",
    # Convenience functions
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "omega_ratio",
    "max_drawdown",
    "ulcer_index",
]
