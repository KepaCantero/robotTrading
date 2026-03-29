"""
Protocol definitions for the strategy stock allocation module.

Defines interfaces for dependency injection and adherence to the Dependency
Inversion Principle (DIP) from SOLID.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd


class StockFilterProtocol(Protocol):
    """Protocol for stock filtering operations."""

    def filter_stocks(self, historical_data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """
        Filter stocks based on validation criteria.

        Args:
            historical_data: Dictionary mapping ticker to OHLCV DataFrame

        Returns:
            Dictionary of filtered stocks with valid data
        """
        ...


class CalculatorProtocol(Protocol):
    """Protocol for statistical calculations."""

    def calculate_hurst_exponent(
        self, prices: np.ndarray, max_lag: int | None = None
    ) -> float | None:
        """
        Calculate Hurst exponent using R/S method.

        Args:
            prices: Price series as numpy array
            max_lag: Maximum lag for calculation

        Returns:
            Hurst exponent (0 < H < 1), or None if calculation fails
        """
        ...

    def calculate_half_life(self, spread: pd.Series) -> float | None:
        """
        Calculate half-life from Ornstein-Uhlenbeck model.

        Args:
            spread: Spread series

        Returns:
            Half-life in days, or None if calculation fails
        """
        ...

    def test_stationarity(self, series: pd.Series) -> dict[str, Any]:
        """
        Test stationarity using ADF and KPSS tests.

        Args:
            series: Time series to test

        Returns:
            Dictionary with test results
        """
        ...


class RegimeClassifierProtocol(Protocol):
    """Protocol for market regime classification."""

    def classify_market_regime(self, prices: np.ndarray) -> dict[str, float | None]:
        """
        Classify market regime using Hurst exponent.

        Args:
            prices: Price series

        Returns:
            Dictionary with H_short, H_long, and regime classification
        """
        ...


class ScorerProtocol(Protocol):
    """Protocol for strategy scoring operations."""

    def score_momentum(self, ticker: str, data: pd.DataFrame) -> dict[str, Any]:
        """
        Score asset for Momentum strategy.

        Args:
            ticker: Stock ticker
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with scores and metrics
        """
        ...

    def score_mean_reversion(self, ticker: str, data: pd.DataFrame) -> dict[str, Any]:
        """
        Score asset for Mean Reversion strategy.

        Args:
            ticker: Stock ticker
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with scores and metrics
        """
        ...

    def score_pairs_trading(
        self, pair: tuple[str, str], data1: pd.DataFrame, data2: pd.DataFrame
    ) -> dict[str, Any]:
        """
        Score pair for Pairs Trading strategy.

        Args:
            pair: Tuple of (ticker1, ticker2)
            data1: DataFrame for first asset
            data2: DataFrame for second asset

        Returns:
            Dictionary with scores and metrics
        """
        ...


class AllocatorProtocol(Protocol):
    """Protocol for capital allocation operations."""

    def allocate_capital(
        self,
        scores: dict[str, dict[str, float]],
        total_capital: float,
        strategy_allocations: dict[str, float],
    ) -> dict[str, float]:
        """
        Allocate capital using risk parity approach.

        Args:
            scores: Dictionary mapping ticker to strategy scores
            total_capital: Total capital to allocate
            strategy_allocations: Strategy-level capital allocations

        Returns:
            Dictionary mapping ticker to allocated capital
        """
        ...
