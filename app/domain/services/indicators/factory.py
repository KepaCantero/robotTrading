"""
Indicator Factory Module

This module provides a factory function to get the appropriate indicator
calculator based on the desired backend (pandas or numba).

Usage:
    from app.domain.services.indicators import get_indicator_calculator

    # Get pandas-based calculator (default, more features)
    indicators = get_indicator_calculator(backend='pandas')

    # Get numba-based calculator (faster, for high-frequency)
    indicators = get_indicator_calculator(backend='numba')

    # Auto-select based on data size
    indicators = get_indicator_calculator(backend='auto')
"""

import logging
from enum import Enum
from typing import Optional, Protocol, Union, runtime_checkable

import numpy as np
import pandas as pd

from app.domain.services.indicators.numba_indicators import NUMBA_AVAILABLE, NumbaIndicators
from app.domain.services.indicators.technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class IndicatorBackend(str, Enum):
    """Available indicator calculation backends."""

    PANDAS = "pandas"
    NUMBA = "numba"
    AUTO = "auto"


@runtime_checkable
class IndicatorCalculator(Protocol):
    """Protocol defining the indicator calculator interface."""

    def rsi(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 14,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        ...

    def ema(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 20,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        ...

    def sma(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 20,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        ...

    def macd(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        return_components: bool = True,
    ) -> Union[Optional[float], tuple]:
        ...

    def atr(
        self,
        high: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 14,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        ...

    def bollinger_bands(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 20,
        std_dev: float = 2.0,
        return_components: bool = True,
    ) -> Union[tuple, dict]:
        ...

    def stochastic(
        self,
        high: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        k_period: int = 14,
        d_period: int = 3,
        return_components: bool = True,
    ) -> Union[Optional[float], tuple]:
        ...


class UnifiedIndicatorCalculator:
    """
    Unified indicator calculator that can switch between backends.

    This class provides a unified interface for indicator calculations
    with automatic backend selection based on data characteristics.
    """

    def __init__(
        self,
        backend: Union[str, IndicatorBackend] = IndicatorBackend.PANDAS,
        auto_threshold: int = 1000,
    ):
        """
        Initialize unified indicator calculator.

        Args:
            backend: Preferred backend ('pandas', 'numba', 'auto').
            auto_threshold: Data size threshold for auto-switching to numba.
        """
        if isinstance(backend, str):
            backend = IndicatorBackend(backend.lower())

        self.backend = backend
        self.auto_threshold = auto_threshold

        # Initialize calculators
        self._pandas_calculator = TechnicalIndicators(use_pandas_ta=True)
        self._numba_calculator = NumbaIndicators() if NUMBA_AVAILABLE else None

        if backend == IndicatorBackend.NUMBA and not NUMBA_AVAILABLE:
            logger.warning(
                "Numba backend requested but Numba not available. "
                "Falling back to pandas backend."
            )
            self.backend = IndicatorBackend.PANDAS

    def _select_backend(self, data: Union[pd.DataFrame, pd.Series, list, np.ndarray]) -> str:
        """Select the appropriate backend based on data characteristics."""
        if self.backend != IndicatorBackend.AUTO:
            return self.backend.value

        # Determine data size
        if isinstance(data, pd.DataFrame) or isinstance(data, pd.Series) or isinstance(data, np.ndarray):
            size = len(data)
        else:
            size = len(data) if hasattr(data, '__len__') else 0

        # Use numba for large datasets if available
        if size >= self.auto_threshold and NUMBA_AVAILABLE:
            return IndicatorBackend.NUMBA.value

        return IndicatorBackend.PANDAS.value

    def _convert_to_array(
        self, data: Union[pd.DataFrame, pd.Series, list, np.ndarray]
    ) -> np.ndarray:
        """Convert data to numpy array for numba backend."""
        if isinstance(data, pd.DataFrame):
            if 'close' in data.columns:
                return data['close'].values
            return data.iloc[:, 0].values
        elif isinstance(data, pd.Series):
            return data.values
        elif isinstance(data, np.ndarray):
            return data
        else:
            return np.array(data, dtype=np.float64)

    @property
    def pandas(self) -> TechnicalIndicators:
        """Get pandas calculator directly."""
        return self._pandas_calculator

    @property
    def numba(self) -> Optional[NumbaIndicators]:
        """Get numba calculator directly."""
        return self._numba_calculator

    def rsi(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 14,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """Calculate RSI."""
        backend = self._select_backend(data)

        if backend == IndicatorBackend.NUMBA.value:
            return self._numba_calculator.rsi(self._convert_to_array(data), period, return_array)
        return self._pandas_calculator.rsi(data, period, return_array)

    def ema(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 20,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """Calculate EMA."""
        backend = self._select_backend(data)

        if backend == IndicatorBackend.NUMBA.value:
            return self._numba_calculator.ema(self._convert_to_array(data), period, return_array)
        return self._pandas_calculator.ema(data, period, return_array)

    def sma(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 20,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """Calculate SMA."""
        backend = self._select_backend(data)

        if backend == IndicatorBackend.NUMBA.value:
            return self._numba_calculator.sma(self._convert_to_array(data), period, return_array)
        return self._pandas_calculator.sma(data, period, return_array)

    def macd(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        return_components: bool = True,
    ) -> Union[Optional[float], tuple]:
        """Calculate MACD."""
        backend = self._select_backend(data)

        if backend == IndicatorBackend.NUMBA.value:
            return self._numba_calculator.macd(
                self._convert_to_array(data),
                fast_period,
                slow_period,
                signal_period,
                return_components,
            )
        return self._pandas_calculator.macd(
            data, fast_period, slow_period, signal_period, return_components
        )

    def atr(
        self,
        high: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 14,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """Calculate ATR."""
        backend = self._select_backend(close)

        if backend == IndicatorBackend.NUMBA.value:
            return self._numba_calculator.atr(
                self._convert_to_array(high),
                self._convert_to_array(low),
                self._convert_to_array(close),
                period,
                return_array,
            )
        return self._pandas_calculator.atr(high, low, close, period, return_array)

    def bollinger_bands(
        self,
        data: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 20,
        std_dev: float = 2.0,
        return_components: bool = True,
    ) -> Union[tuple, dict]:
        """Calculate Bollinger Bands."""
        backend = self._select_backend(data)

        if backend == IndicatorBackend.NUMBA.value:
            return self._numba_calculator.bollinger_bands(
                self._convert_to_array(data), period, std_dev
            )
        return self._pandas_calculator.bollinger_bands(data, period, std_dev, return_components)

    def adx(
        self,
        high: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 14,
        return_components: bool = True,
    ) -> Union[Optional[float], tuple]:
        """Calculate ADX (uses pandas backend only)."""
        return self._pandas_calculator.adx(high, low, close, period, return_components)

    def stochastic(
        self,
        high: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        k_period: int = 14,
        d_period: int = 3,
        return_components: bool = True,
    ) -> Union[Optional[float], tuple]:
        """Calculate Stochastic Oscillator."""
        backend = self._select_backend(close)

        if backend == IndicatorBackend.NUMBA.value:
            return self._numba_calculator.stochastic(
                self._convert_to_array(high),
                self._convert_to_array(low),
                self._convert_to_array(close),
                k_period,
                d_period,
            )
        return self._pandas_calculator.stochastic(
            high, low, close, k_period, d_period, return_components
        )

    def cci(
        self,
        high: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 20,
    ) -> Optional[float]:
        """Calculate CCI (uses pandas backend only)."""
        return self._pandas_calculator.cci(high, low, close, period)

    def obv(
        self,
        close: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        volume: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """Calculate OBV (uses pandas backend only)."""
        return self._pandas_calculator.obv(close, volume, return_array)

    def williams_r(
        self,
        high: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, list, np.ndarray],
        period: int = 14,
    ) -> Optional[float]:
        """Calculate Williams %R (uses pandas backend only)."""
        return self._pandas_calculator.williams_r(high, low, close, period)

    def roc(
        self, data: Union[pd.DataFrame, pd.Series, list, np.ndarray], period: int = 14
    ) -> Optional[float]:
        """Calculate ROC (uses pandas backend only)."""
        return self._pandas_calculator.roc(data, period)

    def calculate_all(self, df: pd.DataFrame, indicators: Optional[list] = None) -> dict:
        """Calculate multiple indicators (uses pandas backend only)."""
        return self._pandas_calculator.calculate_all(df, indicators)


# Singleton instance for convenience
_default_calculator: Optional[UnifiedIndicatorCalculator] = None


def get_indicator_calculator(
    backend: Union[str, IndicatorBackend] = IndicatorBackend.PANDAS,
    auto_threshold: int = 1000,
    use_singleton: bool = True,
) -> UnifiedIndicatorCalculator:
    """
    Get an indicator calculator instance.

    This is the main factory function for obtaining an indicator calculator.
    By default, it returns a singleton instance for efficiency.

    Args:
        backend: Backend to use ('pandas', 'numba', 'auto').
            - 'pandas': Use pandas/pandas-ta (more features, good for most cases)
            - 'numba': Use Numba JIT (faster, best for high-frequency)
            - 'auto': Automatically select based on data size
        auto_threshold: Data size threshold for auto-switching to numba.
        use_singleton: If True, return a singleton instance (default).

    Returns:
        UnifiedIndicatorCalculator instance.

    Example:
        >>> # Get default pandas calculator
        >>> indicators = get_indicator_calculator()
        >>> rsi = indicators.rsi(prices)

        >>> # Get numba calculator for high-frequency
        >>> indicators = get_indicator_calculator(backend='numba')
        >>> rsi = indicators.rsi(prices)

        >>> # Let system auto-select
        >>> indicators = get_indicator_calculator(backend='auto')
    """
    global _default_calculator

    if use_singleton and backend == IndicatorBackend.PANDAS:
        if _default_calculator is None:
            _default_calculator = UnifiedIndicatorCalculator(backend, auto_threshold)
        return _default_calculator

    return UnifiedIndicatorCalculator(backend, auto_threshold)


def get_available_backends() -> dict:
    """
    Get information about available backends.

    Returns:
        Dictionary with backend availability and recommendations.
    """
    return {
        "pandas": {
            "available": True,
            "description": "Pandas-based calculations with pandas-ta integration",
            "best_for": [
                "General purpose indicator calculations",
                "DataFrame input/output",
                "Full indicator library access",
                "Development and debugging",
            ],
            "features": [
                "All indicators supported",
                "DataFrame support",
                "Detailed metadata",
            ],
        },
        "numba": {
            "available": NUMBA_AVAILABLE,
            "description": "Numba JIT-compiled calculations for high performance",
            "best_for": [
                "High-frequency trading",
                "Large datasets (>1000 points)",
                "Batch processing",
                "Real-time calculations",
            ],
            "features": [
                "10-100x speedup",
                "NumPy array input/output",
                "Core indicators only",
            ],
            "install_hint": "pip install numba" if not NUMBA_AVAILABLE else None,
        },
        "auto": {
            "available": True,
            "description": "Automatically select backend based on data characteristics",
            "best_for": [
                "Variable workload",
                "Mixed data sizes",
                "Optimal performance",
            ],
        },
    }


# For backward compatibility with existing code
def calculate_rsi(prices: list, period: int = 14) -> Union[Optional[float], Optional[np.ndarray]]:
    """Convenience function for RSI calculation."""
    return get_indicator_calculator().rsi(prices, period)


def calculate_ema(prices: list, period: int = 20) -> Union[Optional[float], Optional[np.ndarray]]:
    """Convenience function for EMA calculation."""
    return get_indicator_calculator().ema(prices, period)


def calculate_sma(prices: list, period: int = 20) -> Union[Optional[float], Optional[np.ndarray]]:
    """Convenience function for SMA calculation."""
    return get_indicator_calculator().sma(prices, period)


def calculate_macd(
    prices: list, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> Union[Optional[float], tuple]:
    """Convenience function for MACD calculation."""
    return get_indicator_calculator().macd(
        prices, fast_period, slow_period, signal_period, return_components=True
    )


def calculate_atr(
    high: list, low: list, close: list, period: int = 14
) -> Union[Optional[float], Optional[np.ndarray]]:
    """Convenience function for ATR calculation."""
    return get_indicator_calculator().atr(high, low, close, period)


def calculate_bollinger_bands(
    prices: list, period: int = 20, std_dev: float = 2.0
) -> Union[tuple, dict]:
    """Convenience function for Bollinger Bands calculation."""
    return get_indicator_calculator().bollinger_bands(prices, period, std_dev)
