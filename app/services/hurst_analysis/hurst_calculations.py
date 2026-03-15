# pylint: disable=unsupported-binary-operation
"""Utility functions for Hurst Analysis module.

This module contains helper functions used across the hurst_analysis package.
Following the Single Responsibility Principle, these utilities are focused
on specific tasks like data conversion and preparation.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.services.hurst_analysis.models import HurstResult, MarketRegime, StrategyRecommendation

logger = logging.getLogger(__name__)


def to_numpy_array(series: pd.Series | np.ndarray | list[float]) -> np.ndarray:
    """
        Convert input to numpy array.

    from __future__ import annotations

        Args:
            series: Input time series

        Returns:
            Numpy array
    """
    if isinstance(series, pd.Series):
        return series.values
    if isinstance(series, list):
        return np.array(series)
    return series


def calculate_log_returns(prices: np.ndarray) -> np.ndarray | None:
    """
    Calculate log returns from price series.

    Log returns are preferred for Hurst analysis because:
    1. They are stationary (required for R/S analysis)
    2. They are additive over time
    3. They follow normal distribution better

    Args:
        prices: Price series

    Returns:
        Log returns array or None if calculation fails
    """
    if len(prices) < 2:
        return None

    # Filter out non-positive prices
    valid_prices = prices[prices > 0]
    if len(valid_prices) < 2:
        return None

    # Calculate log returns: ln(P_t / P_{t-1})
    log_prices = np.log(valid_prices)
    returns = log_prices[1:] - log_prices[:-1]

    # Filter out infinite values
    returns_clean = returns[np.isfinite(returns)]

    return returns_clean if len(returns_clean) >= 2 else None


def create_default_result(method: str = "unknown") -> HurstResult:
    """
    Create default result when analysis fails.

    Args:
        method: Method name

    Returns:
        Default HurstResult assuming random walk
    """
    return HurstResult(
        hurst_exponent=0.5,
        regime=MarketRegime.RANDOM_WALK,
        strategy=StrategyRecommendation.NEUTRAL,
        confidence=0.0,
        method=method,
    )


def clean_and_validate_series(series_array: np.ndarray, min_length: int = 10) -> np.ndarray | None:
    """
    Remove NaN values and validate series length.

    Args:
        series_array: Input series as numpy array
        min_length: Minimum required length

    Returns:
        Cleaned series or None if validation fails
    """
    if len(series_array) < min_length:
        logger.warning(f"Series too short: {len(series_array)}")
        return None

    # Remove NaN values
    series_clean = series_array[~np.isnan(series_array)]

    if len(series_clean) < min_length:
        logger.warning("Too many NaN values")
        return None

    return series_clean
