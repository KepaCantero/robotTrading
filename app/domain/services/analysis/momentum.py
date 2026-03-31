"""
Momentum Analysis Module - Backward Compatibility Layer

This module provides backward compatibility for code that imports
TechnicalIndicatorCalculator from app.domain.services.analysis.momentum.

All indicator calculations are now provided by the consolidated
app.domain.services.indicators module.

Usage (existing code, no changes needed):
    from app.domain.services.analysis.momentum import TechnicalIndicatorCalculator

    calculator = TechnicalIndicatorCalculator()
    rsi = calculator.calculate_rsi(prices, period=14)

Recommended (new code):
    from app.domain.services.indicators import get_indicator_calculator

    indicators = get_indicator_calculator()
    rsi = indicators.rsi(prices, period=14)
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Union, cast

import numpy as np
import pandas as pd

from app.domain.services.indicators.factory import get_indicator_calculator

# Import from consolidated module
from app.domain.services.indicators.technical_indicators import IndicatorResult, TechnicalIndicators

logger = logging.getLogger(__name__)


class TechnicalIndicatorCalculator:
    """
    Backward-compatible wrapper for technical indicator calculations.

    This class provides the same interface as the original TechnicalIndicatorCalculator
    but delegates to the new consolidated indicators module.

    Attributes:
        indicators: The underlying TechnicalIndicators instance.

    Example:
        >>> calculator = TechnicalIndicatorCalculator()
        >>> rsi = calculator.calculate_rsi([100, 101, 102, ...], period=14)
        >>> ema = calculator.calculate_ema(prices, period=20)
    """

    def __init__(self, use_pandas_ta: bool = True):
        """
        Initialize the technical indicator calculator.

        Args:
            use_pandas_ta: Whether to use pandas-ta library when available.
        """
        self._indicators = TechnicalIndicators(use_pandas_ta=use_pandas_ta)
        logger.debug("TechnicalIndicatorCalculator initialized (backward-compatible wrapper)")

    @property
    def indicators(self) -> TechnicalIndicators:
        """Get the underlying indicators instance."""
        return self._indicators

    def calculate_rsi(
        self, prices: Union[list, np.ndarray, pd.Series], period: int = 14
    ) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            prices: Array of price values.
            period: RSI period (default 14).

        Returns:
            RSI value (0-100) or None if insufficient data.
        """
        result = self._indicators.rsi(prices, period=period)
        return cast("Optional[float]", result)

    def calculate_ema(
        self, prices: Union[list, np.ndarray, pd.Series], period: int = 20
    ) -> Optional[float]:
        """
        Calculate Exponential Moving Average (EMA).

        Args:
            prices: Array of price values.
            period: EMA period.

        Returns:
            EMA value or None if insufficient data.
        """
        result = self._indicators.ema(prices, period=period)
        return cast("Optional[float]", result)

    def calculate_sma(
        self, prices: Union[list, np.ndarray, pd.Series], period: int = 20
    ) -> Optional[float]:
        """
        Calculate Simple Moving Average (SMA).

        Args:
            prices: Array of price values.
            period: SMA period.

        Returns:
            SMA value or None if insufficient data.
        """
        result = self._indicators.sma(prices, period=period)
        return cast("Optional[float]", result)

    def calculate_macd(
        self,
        prices: Union[list, np.ndarray, pd.Series],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> dict[str, Optional[float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            prices: Array of price values.
            fast_period: Fast EMA period (default 12).
            slow_period: Slow EMA period (default 26).
            signal_period: Signal line period (default 9).

        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' values.
        """
        macd, signal, histogram = self._indicators.macd(
            prices,
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
            return_components=True,
        )
        return {
            "macd": macd,
            "signal": signal,
            "histogram": histogram,
        }

    def calculate_atr(
        self,
        highs: Union[list, np.ndarray, pd.Series],
        lows: Union[list, np.ndarray, pd.Series],
        closes: Union[list, np.ndarray, pd.Series],
        period: int = 14,
    ) -> Optional[float]:
        """
        Calculate Average True Range (ATR).

        Args:
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            period: ATR period (default 14).

        Returns:
            ATR value or None if insufficient data.
        """
        result = self._indicators.atr(highs, lows, closes, period=period)
        return cast("Optional[float]", result)

    def calculate_bollinger_bands(
        self, prices: Union[list, np.ndarray, pd.Series], period: int = 20, std_dev: float = 2.0
    ) -> dict[str, Optional[float]]:
        """
        Calculate Bollinger Bands.

        Args:
            prices: Array of price values.
            period: MA period (default 20).
            std_dev: Number of standard deviations (default 2.0).

        Returns:
            Dictionary with 'upper', 'middle', 'lower', 'width', 'position'.
        """
        result = self._indicators.bollinger_bands(
            prices, period=period, std_dev=std_dev, return_components=False
        )
        return cast("dict[str, Optional[float]]", result)

    def calculate_roc(
        self, prices: Union[list, np.ndarray, pd.Series], period: int = 14
    ) -> Optional[float]:
        """
        Calculate Rate of Change (ROC).

        Args:
            prices: Array of price values.
            period: Lookback period (default 14).

        Returns:
            ROC value (as decimal) or None.
        """
        result = self._indicators.roc(prices, period=period)
        return cast("Optional[float]", result)

    def calculate_stochastic(
        self,
        highs: Union[list, np.ndarray, pd.Series],
        lows: Union[list, np.ndarray, pd.Series],
        closes: Union[list, np.ndarray, pd.Series],
        k_period: int = 14,
        d_period: int = 3,
    ) -> dict[str, Optional[float]]:
        """
        Calculate Stochastic Oscillator.

        Args:
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            k_period: %K period (default 14).
            d_period: %D period (default 3).

        Returns:
            Dictionary with 'k' and 'd' values.
        """
        k, d = self._indicators.stochastic(
            highs, lows, closes, k_period=k_period, d_period=d_period, return_components=True
        )
        return {"k": k, "d": d}

    def calculate_stochastic_rsi(
        self, rsi_values: Union[list, np.ndarray, pd.Series], period: int = 14, smooth_k: int = 3
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Calculate Stochastic RSI from pre-calculated RSI values.

        Delegates to TechnicalIndicators.stochrsi which tries pandas-ta first,
        then falls back to native pandas vectorized implementation.

        Args:
            rsi_values: List/array of RSI values.
            period: Period for Stochastic RSI calculation (default 14).
            smooth_k: Smoothing period for %D (default 3).

        Returns:
            Tuple of (StochRSI %K, StochRSI %D) or (None, None) if insufficient data.
        """
        result = self._indicators.stochrsi(
            rsi_values, period=period, k_period=smooth_k, d_period=smooth_k
        )
        k_val: Optional[float] = result[0] if result else None
        d_val: Optional[float] = result[1] if result else None
        return k_val, d_val

    def calculate_adx(
        self,
        highs: Union[list, np.ndarray, pd.Series],
        lows: Union[list, np.ndarray, pd.Series],
        closes: Union[list, np.ndarray, pd.Series],
        period: int = 14,
    ) -> dict[str, Optional[float]]:
        """
        Calculate Average Directional Index (ADX).

        Args:
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            period: ADX period (default 14).

        Returns:
            Dictionary with 'adx', 'plus_di', 'minus_di' values.
        """
        adx, plus_di, minus_di = self._indicators.adx(
            highs, lows, closes, period=period, return_components=True
        )
        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
        }

    def calculate_cci(
        self,
        highs: Union[list, np.ndarray, pd.Series],
        lows: Union[list, np.ndarray, pd.Series],
        closes: Union[list, np.ndarray, pd.Series],
        period: int = 20,
    ) -> Optional[float]:
        """
        Calculate Commodity Channel Index (CCI).

        Args:
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            period: CCI period (default 20).

        Returns:
            CCI value or None.
        """
        result = self._indicators.cci(highs, lows, closes, period=period)
        return cast("Optional[float]", result)

    def calculate_obv(
        self,
        closes: Union[list, np.ndarray, pd.Series],
        volumes: Union[list, np.ndarray, pd.Series],
    ) -> Optional[float]:
        """
        Calculate On-Balance Volume (OBV).

        Args:
            closes: Array of close prices.
            volumes: Array of volume values.

        Returns:
            OBV value or None.
        """
        result = self._indicators.obv(closes, volumes)
        return cast("Optional[float]", result)

    def calculate_williams_r(
        self,
        highs: Union[list, np.ndarray, pd.Series],
        lows: Union[list, np.ndarray, pd.Series],
        closes: Union[list, np.ndarray, pd.Series],
        period: int = 14,
    ) -> Optional[float]:
        """
        Calculate Williams %R.

        Args:
            highs: Array of high prices.
            lows: Array of low prices.
            closes: Array of close prices.
            period: Lookback period (default 14).

        Returns:
            Williams %R value (-100 to 0) or None.
        """
        result = self._indicators.williams_r(highs, lows, closes, period=period)
        return cast("Optional[float]", result)

    def calculate_all_indicators(
        self, df: pd.DataFrame, indicators: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Calculate multiple indicators at once.

        Args:
            df: DataFrame with OHLCV columns.
            indicators: List of indicator names to calculate.

        Returns:
            Dictionary with all calculated indicator values.
        """
        result = self._indicators.calculate_all(df, indicators)
        return cast("dict[str, Any]", result)


# Also export for backward compatibility with old imports
__all__ = [
    "IndicatorResult",
    "TechnicalIndicatorCalculator",
    "TechnicalIndicators",
    "get_indicator_calculator",
]
