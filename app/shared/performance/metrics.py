"""
Unified Performance Metrics Module

This is THE SINGLE SOURCE OF TRUTH for all performance metric calculations.
It re-exports from the consolidated domain implementation and provides
config-aware wrappers.

ARCHITECTURE:
    - Domain implementation: app/domain/services/metrics/performance_metrics.py
    - Numba-accelerated: app/backtesting/numba_metrics.py
    - This module: Unified interface with config integration

USAGE:
    from app.shared.performance.metrics import (
        sharpe_ratio,
        sortino_ratio,
        max_drawdown,
        PerformanceMetricsCalculator,
    )

    # Using convenience functions (reads defaults from CentralizedConfig)
    sr = sharpe_ratio(returns)

    # Using calculator with custom config
    calc = PerformanceMetricsCalculator.from_config()
    sr = calc.sharpe_ratio(returns)

Reference:
    - Lopez de Prado, M. (2020). Machine Learning for Asset Managers.
    - Chan, E.P. (2013). Algorithmic Trading.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import cast

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Import the consolidated domain implementation
from app.domain.services.metrics.performance_metrics import (
    DrawdownResult,
    PerformanceMetricsCalculator as _PerformanceMetricsCalculator,
    PerformanceResult,
    SharpeRatioResult,
)

# Re-export dataclasses
__all__ = [
    # Direct access to domain implementation
    "DomainPerformanceMetricsCalculator",
    "DrawdownResult",
    # Calculator
    "PerformanceMetricsCalculator",
    "PerformanceResult",
    "SharpeRatioResult",
    "calmar_ratio",
    "max_drawdown",
    "omega_ratio",
    # Convenience functions (config-aware)
    "sharpe_ratio",
    "sortino_ratio",
    "ulcer_index",
]


class PerformanceMetricsCalculator(_PerformanceMetricsCalculator):
    """
    Config-aware performance metrics calculator.

    Extends the domain PerformanceMetricsCalculator to read defaults
    from CentralizedConfig instead of hardcoded values.

    Usage:
        # Uses config defaults automatically
        calc = PerformanceMetricsCalculator.from_config()
        sharpe = calc.sharpe_ratio(returns)

        # Override specific values
        calc = PerformanceMetricsCalculator.from_config(
            risk_free_rate=0.03  # Override config default
        )
    """

    @classmethod
    def from_config(
        cls,
        risk_free_rate: float | None = None,
        trading_days: int | None = None,
        use_empyrical: bool = True,
    ) -> PerformanceMetricsCalculator:
        """
        Create calculator with defaults from CentralizedConfig.

        Args:
            risk_free_rate: Override config default risk-free rate
            trading_days: Override config default trading days
            use_empyrical: Whether to use empyrical library

        Returns:
            PerformanceMetricsCalculator with config defaults
        """
        from app.shared.config.centralized_config import get_config

        config = get_config().backtesting

        rf = risk_free_rate if risk_free_rate is not None else float(config.default_risk_free_rate)
        td = trading_days if trading_days is not None else config.annual_trading_days

        logger.debug(
            "Creating PerformanceMetricsCalculator from config",
            extra={
                "risk_free_rate": rf,
                "trading_days": td,
                "use_empyrical": use_empyrical,
                "config_source": "CentralizedConfig",
            },
        )

        return cls(
            risk_free_rate=rf,
            trading_days=td,
            use_empyrical=use_empyrical,
        )


def _to_float_array(
    returns: pd.Series | np.ndarray | list[Decimal] | list[float],
) -> np.ndarray:
    """Convert returns to numpy array, handling various input types."""
    logger.debug(
        "Converting returns to float array",
        extra={
            "input_type": type(returns).__name__,
            "input_length": len(returns) if hasattr(returns, "__len__") else "N/A",
        },
    )
    if isinstance(returns, pd.Series):
        arr = returns.values.astype(np.float64)
    elif isinstance(returns, list):
        if len(returns) > 0 and isinstance(returns[0], Decimal):
            arr = np.array([float(r) for r in returns], dtype=np.float64)
        else:
            arr = np.array(returns, dtype=np.float64)
    else:
        arr = np.asarray(returns, dtype=np.float64)

    result = arr[~np.isnan(arr)]
    logger.debug(
        "Returns conversion complete",
        extra={
            "output_length": len(result),
            "nan_removed": len(arr) - len(result),
        },
    )
    return cast("np.ndarray", result)


def sharpe_ratio(
    returns: pd.Series | np.ndarray | list[Decimal] | list[float],
    risk_free_rate: float | None = None,
    annualize: bool = True,
) -> float:
    """
    Calculate Sharpe ratio using CentralizedConfig defaults.

    Args:
        returns: Return series (daily returns by default)
        risk_free_rate: Annual risk-free rate (default: from CentralizedConfig)
        annualize: Whether to annualize the ratio

    Returns:
        Sharpe ratio (annualized if annualize=True)
    """
    logger.debug(
        "Calculating Sharpe ratio",
        extra={
            "returns_length": len(returns) if hasattr(returns, "__len__") else "N/A",
            "risk_free_rate": risk_free_rate,
            "annualize": annualize,
        },
    )
    calc = PerformanceMetricsCalculator.from_config(risk_free_rate=risk_free_rate)
    result = calc.sharpe_ratio(returns, risk_free_rate=risk_free_rate, annualize=annualize)
    logger.info(
        "Sharpe ratio calculated",
        extra={
            "sharpe_ratio": result,
            "annualized": annualize,
        },
    )
    return float(result)


def sortino_ratio(
    returns: pd.Series | np.ndarray | list[Decimal] | list[float],
    risk_free_rate: float | None = None,
    target_return: float = 0.0,
    annualize: bool = True,
) -> float:
    """
    Calculate Sortino ratio using CentralizedConfig defaults.

    Args:
        returns: Return series
        risk_free_rate: Annual risk-free rate (default: from CentralizedConfig)
        target_return: Target/minimum acceptable return (MAR)
        annualize: Whether to annualize the ratio

    Returns:
        Sortino ratio (annualized if annualize=True)
    """
    calc = PerformanceMetricsCalculator.from_config(risk_free_rate=risk_free_rate)
    return float(
        calc.sortino_ratio(
            returns, risk_free_rate=risk_free_rate, target_return=target_return, annualize=annualize
        )
    )


def calmar_ratio(
    returns: pd.Series | np.ndarray | list[float],
    equity_curve: pd.Series | np.ndarray | list[float] | None = None,
) -> float | None:
    """
    Calculate Calmar ratio using CentralizedConfig defaults.

    Args:
        returns: Return series
        equity_curve: Optional equity curve for drawdown calculation

    Returns:
        Calmar ratio or None if calculation not possible
    """
    calc = PerformanceMetricsCalculator.from_config()
    result = calc.calmar_ratio(returns, equity_curve)
    return float(result) if result is not None else None


def omega_ratio(
    returns: pd.Series | np.ndarray | list[Decimal] | list[float],
    threshold: float = 0.0,
) -> float:
    """
    Calculate Omega ratio.

    Args:
        returns: Return series
        threshold: Target return threshold (default: 0%)

    Returns:
        Omega ratio (>1.0 indicates more upside than downside)
    """
    calc = PerformanceMetricsCalculator.from_config()
    return float(calc.omega_ratio(returns, threshold))


def max_drawdown(
    equity_curve: pd.Series | np.ndarray | list[Decimal] | list[float],
    as_percentage: bool = False,
) -> float:
    """
    Calculate maximum drawdown.

    Args:
        equity_curve: Equity or portfolio value series
        as_percentage: If True, return as percentage (e.g., -20.0)

    Returns:
        Maximum drawdown (negative value, e.g., -0.20 or -20.0)
    """
    calc = PerformanceMetricsCalculator.from_config()
    return float(calc.max_drawdown(equity_curve, as_percentage))


def ulcer_index(
    equity_curve: pd.Series | np.ndarray | list[Decimal] | list[float],
) -> float:
    """
    Calculate Ulcer Index.

    Args:
        equity_curve: Portfolio equity values over time

    Returns:
        Ulcer Index (lower is better)
    """
    calc = PerformanceMetricsCalculator.from_config()
    return float(calc.ulcer_index(equity_curve))


# Alias for domain calculator direct access
DomainPerformanceMetricsCalculator = _PerformanceMetricsCalculator
