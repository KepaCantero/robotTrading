"""
Technical Indicators - Unified Implementation with Pandas-TA Backend

This module provides a unified interface for calculating technical indicators
using pandas-ta as the primary backend with optional Numba JIT compilation
for performance-critical calculations.

Supported Indicators:
- RSI (Relative Strength Index)
- EMA (Exponential Moving Average)
- SMA (Simple Moving Average)
- MACD (Moving Average Convergence Divergence)
- ATR (Average True Range)
- Bollinger Bands
- ADX (Average Directional Index)
- Stochastic Oscillator
- CCI (Commodity Channel Index)
- OBV (On-Balance Volume)
- Williams %R
- ROC (Rate of Change)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import pandas-ta
try:
    import pandas_ta as ta

    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logger.warning(
        "pandas-ta not available. Using native pandas implementations. "
        "Install with: pip install pandas-ta"
    )


@dataclass
class IndicatorResult:
    """Container for indicator calculation results."""

    value: Optional[float] = None
    values: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Check if the result is valid."""
        return self.value is not None or self.values is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "values": self.values.tolist() if self.values is not None else None,
            "metadata": self.metadata,
        }


class TechnicalIndicators:
    """
    Unified technical indicators calculator.

    This class provides a consistent interface for calculating technical
    indicators using pandas-ta as the primary backend. It accepts DataFrames
    with OHLCV columns or individual Series/arrays.

    Attributes:
        use_pandas_ta: Whether to use pandas-ta library when available.

    Example:
        >>> indicators = TechnicalIndicators()
        >>> df = pd.DataFrame({
        ...     'open': [...], 'high': [...], 'low': [...],
        ...     'close': [...], 'volume': [...]
        ... })
        >>> rsi = indicators.rsi(df['close'], period=14)
        >>> ema = indicators.ema(df['close'], period=20)
    """

    # Required OHLCV columns
    OHLCV_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
    REQUIRED_OHLC = ['high', 'low', 'close']

    def __init__(self, use_pandas_ta: bool = True):
        """
        Initialize the technical indicators calculator.

        Args:
            use_pandas_ta: Whether to use pandas-ta library when available.
        """
        self.use_pandas_ta = use_pandas_ta and PANDAS_TA_AVAILABLE
        if self.use_pandas_ta:
            logger.debug("Using pandas-ta backend for technical indicators")
        else:
            logger.debug("Using native pandas implementations for technical indicators")

    def _validate_input(
        self,
        data: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        min_length: int = 1,
        name: str = "data",
    ) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Validate input data and convert to numpy array.

        Args:
            data: Input data (DataFrame, Series, list, or array).
            min_length: Minimum required length.
            name: Name for error messages.

        Returns:
            Tuple of (is_valid, numpy_array).
        """
        if data is None:
            logger.warning(f"{name} is None")
            return False, None

        # Convert to numpy array
        if isinstance(data, pd.DataFrame):
            if 'close' in data.columns:
                arr = data['close'].values
            else:
                arr = data.iloc[:, 0].values
        elif isinstance(data, pd.Series):
            arr = data.values
        elif isinstance(data, list):
            arr = np.array(data, dtype=np.float64)
        elif isinstance(data, np.ndarray):
            arr = data.astype(np.float64) if data.dtype != np.float64 else data
        else:
            logger.warning(f"Unsupported data type for {name}: {type(data)}")
            return False, None

        # Check length
        if len(arr) < min_length:
            logger.warning(f"Insufficient data for {name}: {len(arr)} < {min_length}")
            return False, None

        return True, arr

    def _get_column(
        self, df: pd.DataFrame, column: str, default: Optional[str] = None
    ) -> Optional[pd.Series]:
        """Get a column from DataFrame with fallback."""
        if column in df.columns:
            return df[column]
        if default and default in df.columns:
            return df[default]
        return None

    # ========================================================================
    # RSI (Relative Strength Index)
    # ========================================================================

    def rsi(
        self,
        data: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        period: int = 14,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """
        Calculate Relative Strength Index (RSI).

        RSI measures the speed and magnitude of price movements.
        Values range from 0 to 100.
        - RSI > 70: Overbought condition
        - RSI < 30: Oversold condition

        Args:
            data: Price data (close prices).
            period: RSI period (default 14).
            return_array: If True, return full array; otherwise, last value.

        Returns:
            RSI value(s) or None if insufficient data.
        """
        is_valid, prices = self._validate_input(data, min_length=period + 1, name="RSI")
        if not is_valid:
            return (
                np.full(len(data) if isinstance(data, (list, np.ndarray)) else len(data), np.nan)
                if return_array
                else None
            )

        if self.use_pandas_ta:
            try:
                series = pd.Series(prices)
                result = ta.rsi(series, length=period)
                if return_array:
                    return result.values
                return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else None
            except Exception as e:
                logger.debug(f"pandas-ta RSI failed, using fallback: {e}")

        # Native pandas implementation (Wilder's smoothing)
        return self._rsi_native(prices, period, return_array)

    def _rsi_native(
        self, prices: np.ndarray, period: int, return_array: bool
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """Native pandas implementation of RSI."""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        # Calculate initial averages
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        rsi_values = np.full(len(prices), np.nan)

        # First RSI value
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi_values[period] = 100.0 - (100.0 / (1.0 + rs))
        else:
            rsi_values[period] = 100.0

        # Wilder's smoothing for remaining values
        for i in range(period, len(prices) - 1):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi_values[i + 1] = 100.0 - (100.0 / (1.0 + rs))
            else:
                rsi_values[i + 1] = 100.0

        if return_array:
            return rsi_values
        return float(rsi_values[-1]) if not np.isnan(rsi_values[-1]) else None

    # ========================================================================
    # EMA (Exponential Moving Average)
    # ========================================================================

    def ema(
        self,
        data: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        period: int = 20,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """
        Calculate Exponential Moving Average (EMA).

        EMA gives more weight to recent prices, making it more responsive
        to new information compared to SMA.

        Args:
            data: Price data.
            period: EMA period (default 20).
            return_array: If True, return full array; otherwise, last value.

        Returns:
            EMA value(s) or None if insufficient data.
        """
        is_valid, prices = self._validate_input(data, min_length=period, name="EMA")
        if not is_valid:
            return (
                np.full(len(data) if isinstance(data, (list, np.ndarray)) else len(data), np.nan)
                if return_array
                else None
            )

        if self.use_pandas_ta:
            try:
                series = pd.Series(prices)
                result = ta.ema(series, length=period)
                if return_array:
                    return result.values
                return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else None
            except Exception as e:
                logger.debug(f"pandas-ta EMA failed, using fallback: {e}")

        # Native pandas implementation
        return self._ema_native(prices, period, return_array)

    def _ema_native(
        self, prices: np.ndarray, period: int, return_array: bool
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """Native implementation of EMA."""
        alpha = 2.0 / (period + 1.0)
        ema_values = np.full(len(prices), np.nan)

        # Initialize with SMA
        ema_values[period - 1] = np.mean(prices[:period])

        # Calculate EMA
        for i in range(period, len(prices)):
            ema_values[i] = alpha * prices[i] + (1.0 - alpha) * ema_values[i - 1]

        if return_array:
            return ema_values
        return float(ema_values[-1]) if not np.isnan(ema_values[-1]) else None

    # ========================================================================
    # SMA (Simple Moving Average)
    # ========================================================================

    def sma(
        self,
        data: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        period: int = 20,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """
        Calculate Simple Moving Average (SMA).

        SMA is the unweighted mean of the previous n data points.

        Args:
            data: Price data.
            period: SMA period (default 20).
            return_array: If True, return full array; otherwise, last value.

        Returns:
            SMA value(s) or None if insufficient data.
        """
        is_valid, prices = self._validate_input(data, min_length=period, name="SMA")
        if not is_valid:
            return (
                np.full(len(data) if isinstance(data, (list, np.ndarray)) else len(data), np.nan)
                if return_array
                else None
            )

        if self.use_pandas_ta:
            try:
                series = pd.Series(prices)
                result = ta.sma(series, length=period)
                if return_array:
                    return result.values
                return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else None
            except Exception as e:
                logger.debug(f"pandas-ta SMA failed, using fallback: {e}")

        # Native pandas implementation
        sma_values = np.full(len(prices), np.nan)
        for i in range(period - 1, len(prices)):
            sma_values[i] = np.mean(prices[i - period + 1 : i + 1])

        if return_array:
            return sma_values
        return float(sma_values[-1]) if not np.isnan(sma_values[-1]) else None

    # ========================================================================
    # MACD (Moving Average Convergence Divergence)
    # ========================================================================

    def macd(
        self,
        data: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        return_components: bool = False,
    ) -> Union[
        Optional[float],
        Tuple[Optional[float], Optional[float], Optional[float]],
        Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]],
    ]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        MACD is a trend-following momentum indicator that shows the
        relationship between two moving averages of prices.

        Args:
            data: Price data.
            fast_period: Fast EMA period (default 12).
            slow_period: Slow EMA period (default 26).
            signal_period: Signal line period (default 9).
            return_components: If True, return (macd, signal, histogram).

        Returns:
            MACD value or tuple of (macd, signal, histogram) components.
        """
        is_valid, prices = self._validate_input(
            data, min_length=slow_period + signal_period, name="MACD"
        )
        if not is_valid:
            if return_components:
                return (None, None, None)
            return None

        if self.use_pandas_ta:
            try:
                series = pd.Series(prices)
                result = ta.macd(series, fast=fast_period, slow=slow_period, signal=signal_period)
                if result is not None and not result.empty:
                    macd_val = result[f"MACD_{fast_period}_{slow_period}_{signal_period}"]
                    signal_val = result[f"MACDs_{fast_period}_{slow_period}_{signal_period}"]
                    hist_val = result[f"MACDh_{fast_period}_{slow_period}_{signal_period}"]

                    if return_components:
                        return (
                            float(macd_val.iloc[-1]) if not pd.isna(macd_val.iloc[-1]) else None,
                            float(signal_val.iloc[-1])
                            if not pd.isna(signal_val.iloc[-1])
                            else None,
                            float(hist_val.iloc[-1]) if not pd.isna(hist_val.iloc[-1]) else None,
                        )
                    return float(macd_val.iloc[-1]) if not pd.isna(macd_val.iloc[-1]) else None
            except Exception as e:
                logger.debug(f"pandas-ta MACD failed, using fallback: {e}")

        # Native implementation
        return self._macd_native(prices, fast_period, slow_period, signal_period, return_components)

    def _macd_native(
        self,
        prices: np.ndarray,
        fast_period: int,
        slow_period: int,
        signal_period: int,
        return_components: bool,
    ):
        """Native implementation of MACD."""
        fast_ema_result = self._ema_native(prices, fast_period, return_array=True)
        slow_ema_result = self._ema_native(prices, slow_period, return_array=True)

        # Type narrowing - when return_array=True, result is np.ndarray or None
        if fast_ema_result is None or slow_ema_result is None:
            if return_components:
                return (None, None, None)
            return None

        # At this point, both are np.ndarray (not float) since return_array=True
        assert isinstance(fast_ema_result, np.ndarray)
        assert isinstance(slow_ema_result, np.ndarray)
        fast_ema = fast_ema_result
        slow_ema = slow_ema_result

        macd_line = np.full(len(prices), np.nan)
        for i in range(len(prices)):
            if not np.isnan(fast_ema[i]) and not np.isnan(slow_ema[i]):
                macd_line[i] = fast_ema[i] - slow_ema[i]

        # Signal line
        valid_macd = macd_line[~np.isnan(macd_line)]
        if len(valid_macd) >= signal_period:
            signal_line = self._ema_native(valid_macd, signal_period, return_array=False)
            histogram = macd_line[-1] - signal_line if signal_line else None
        else:
            signal_line = None
            histogram = None

        if return_components:
            return (
                float(macd_line[-1]) if not np.isnan(macd_line[-1]) else None,
                signal_line,
                histogram,
            )
        return float(macd_line[-1]) if not np.isnan(macd_line[-1]) else None

    # ========================================================================
    # ATR (Average True Range)
    # ========================================================================

    def atr(
        self,
        high: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        period: int = 14,
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """
        Calculate Average True Range (ATR).

        ATR is a volatility indicator that measures market volatility
        by decomposing the entire range of an asset price for that period.

        Args:
            high: High prices.
            low: Low prices.
            close: Close prices.
            period: ATR period (default 14).
            return_array: If True, return full array; otherwise, last value.

        Returns:
            ATR value(s) or None if insufficient data.
        """
        is_valid_h, highs = self._validate_input(high, min_length=period + 1, name="ATR high")
        is_valid_l, lows = self._validate_input(low, min_length=period + 1, name="ATR low")
        is_valid_c, closes = self._validate_input(close, min_length=period + 1, name="ATR close")

        if not (is_valid_h and is_valid_l and is_valid_c):
            return (
                np.full(len(high) if isinstance(high, (list, np.ndarray)) else len(high), np.nan)
                if return_array
                else None
            )

        if self.use_pandas_ta:
            try:
                df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
                result = ta.atr(df['high'], df['low'], df['close'], length=period)
                if return_array:
                    return result.values
                return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else None
            except Exception as e:
                logger.debug(f"pandas-ta ATR failed, using fallback: {e}")

        # Native implementation
        return self._atr_native(highs, lows, closes, period, return_array)

    def _atr_native(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int, return_array: bool
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """Native implementation of ATR."""
        n = len(close)
        tr = np.empty(n)
        tr[0] = high[0] - low[0]

        for i in range(1, n):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i - 1])
            lc = abs(low[i] - close[i - 1])
            tr[i] = max(hl, hc, lc)

        atr_values = np.full(n, np.nan)

        # Initial ATR
        atr_values[period] = np.mean(tr[1 : period + 1])

        # Wilder's smoothing
        for i in range(period + 1, n):
            atr_values[i] = (atr_values[i - 1] * (period - 1) + tr[i]) / period

        if return_array:
            return atr_values
        return float(atr_values[-1]) if not np.isnan(atr_values[-1]) else None

    # ========================================================================
    # Bollinger Bands
    # ========================================================================

    def bollinger_bands(
        self,
        data: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        period: int = 20,
        std_dev: float = 2.0,
        return_components: bool = True,
    ) -> Union[
        Tuple[Optional[float], Optional[float], Optional[float]], Dict[str, Optional[float]]
    ]:
        """
        Calculate Bollinger Bands.

        Bollinger Bands consist of a middle band (SMA) with upper and lower
        bands at standard deviation levels above and below.

        Args:
            data: Price data.
            period: SMA period (default 20).
            std_dev: Number of standard deviations (default 2.0).
            return_components: If True, return tuple; otherwise, dict.

        Returns:
            (upper, middle, lower) bands or dict with band values.
        """
        is_valid, prices = self._validate_input(data, min_length=period, name="Bollinger")
        if not is_valid:
            if return_components:
                return (None, None, None)
            return {"upper": None, "middle": None, "lower": None, "width": None, "position": None}

        if self.use_pandas_ta:
            try:
                series = pd.Series(prices)
                result = ta.bbands(series, length=period, std=std_dev)
                if result is not None and not result.empty:
                    upper = result[f"BBU_{period}_{std_dev}"].iloc[-1]
                    middle = result[f"BBM_{period}_{std_dev}"].iloc[-1]
                    lower = result[f"BBL_{period}_{std_dev}"].iloc[-1]

                    upper = float(upper) if not pd.isna(upper) else None
                    middle = float(middle) if not pd.isna(middle) else None
                    lower = float(lower) if not pd.isna(lower) else None

                    # Calculate width and position
                    width = (upper - lower) / middle if middle and upper and lower else None
                    position = (prices[-1] - lower) / (upper - lower) if upper != lower else 0.5

                    if return_components:
                        return (upper, middle, lower)
                    return {
                        "upper": upper,
                        "middle": middle,
                        "lower": lower,
                        "width": width,
                        "position": position,
                    }
            except Exception as e:
                logger.debug(f"pandas-ta Bollinger failed, using fallback: {e}")

        # Native implementation
        middle = float(np.mean(prices[-period:]))
        std = float(np.std(prices[-period:]))
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        width = (upper - lower) / middle if middle > 0.0 else 0.0
        position = (prices[-1] - lower) / (upper - lower) if upper != lower else 0.5

        if return_components:
            return (upper, middle, lower)
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "width": width,
            "position": position,
        }

    # ========================================================================
    # ADX (Average Directional Index)
    # ========================================================================

    def adx(
        self,
        high: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        period: int = 14,
        return_components: bool = True,
    ) -> Union[Optional[float], Tuple[Optional[float], Optional[float], Optional[float]]]:
        """
        Calculate Average Directional Index (ADX).

        ADX measures the strength of a trend, regardless of direction.
        - ADX > 25: Strong trend
        - ADX < 20: Weak or no trend

        Args:
            high: High prices.
            low: Low prices.
            close: Close prices.
            period: ADX period (default 14).
            return_components: If True, return (adx, plus_di, minus_di).

        Returns:
            ADX value or tuple of (adx, plus_di, minus_di).
        """
        is_valid_h, highs = self._validate_input(high, min_length=period * 2, name="ADX high")
        is_valid_l, lows = self._validate_input(low, min_length=period * 2, name="ADX low")
        is_valid_c, closes = self._validate_input(close, min_length=period * 2, name="ADX close")

        if not (is_valid_h and is_valid_l and is_valid_c):
            if return_components:
                return (None, None, None)
            return None

        if self.use_pandas_ta:
            try:
                df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
                result = ta.adx(df['high'], df['low'], df['close'], length=period)
                if result is not None and not result.empty:
                    adx_val = result[f"ADX_{period}"].iloc[-1]
                    plus_di = result[f"DMP_{period}"].iloc[-1]
                    minus_di = result[f"DMN_{period}"].iloc[-1]

                    adx_val = float(adx_val) if not pd.isna(adx_val) else None
                    plus_di = float(plus_di) if not pd.isna(plus_di) else None
                    minus_di = float(minus_di) if not pd.isna(minus_di) else None

                    if return_components:
                        return (adx_val, plus_di, minus_di)
                    return adx_val
            except Exception as e:
                logger.debug(f"pandas-ta ADX failed, using fallback: {e}")

        # Native implementation (simplified)
        return self._adx_native(highs, lows, closes, period, return_components)

    def _adx_native(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        period: int,
        return_components: bool,
    ):
        """Native implementation of ADX."""
        n = len(close)

        # Calculate True Range and Directional Movement
        tr = np.zeros(n)
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)

        tr[0] = high[0] - low[0]

        for i in range(1, n):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i - 1])
            lc = abs(low[i] - close[i - 1])
            tr[i] = max(hl, hc, lc)

            up_move = high[i] - high[i - 1]
            down_move = low[i - 1] - low[i]

            plus_dm[i] = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm[i] = down_move if down_move > up_move and down_move > 0 else 0

        # Smoothed values
        atr_smoothed: float = float(np.mean(tr[-period:]))
        plus_di: float = (
            100 * float(np.mean(plus_dm[-period:])) / atr_smoothed if atr_smoothed > 0 else 0.0
        )
        minus_di: float = (
            100 * float(np.mean(minus_dm[-period:])) / atr_smoothed if atr_smoothed > 0 else 0.0
        )

        # DX and ADX
        di_diff: float = abs(plus_di - minus_di)
        di_sum: float = plus_di + minus_di
        dx: float = 100 * di_diff / di_sum if di_sum > 0 else 0.0

        # Use current DX as approximation (proper ADX needs more history)
        adx_val = dx

        if return_components:
            return (adx_val, plus_di, minus_di)
        return adx_val

    # ========================================================================
    # Stochastic Oscillator
    # ========================================================================

    def stochastic(
        self,
        high: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        k_period: int = 14,
        d_period: int = 3,
        return_components: bool = True,
    ) -> Union[Optional[float], Tuple[Optional[float], Optional[float]]]:
        """
        Calculate Stochastic Oscillator.

        The Stochastic Oscillator compares a security's closing price to
        its price range over a given time period.

        Args:
            high: High prices.
            low: Low prices.
            close: Close prices.
            k_period: %K period (default 14).
            d_period: %D period (default 3).
            return_components: If True, return (%K, %D).

        Returns:
            %K value or tuple of (%K, %D).
        """
        is_valid_h, highs = self._validate_input(high, min_length=k_period, name="Stochastic high")
        is_valid_l, lows = self._validate_input(low, min_length=k_period, name="Stochastic low")
        is_valid_c, closes = self._validate_input(
            close, min_length=k_period, name="Stochastic close"
        )

        if not (is_valid_h and is_valid_l and is_valid_c):
            if return_components:
                return (None, None)
            return None

        if self.use_pandas_ta:
            try:
                df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
                result = ta.stoch(df['high'], df['low'], df['close'], k=k_period, d=d_period)
                if result is not None and not result.empty:
                    k_val = result[f"STOCHk_{k_period}_{d_period}_{d_period}"].iloc[-1]
                    d_val = result[f"STOCHd_{k_period}_{d_period}_{d_period}"].iloc[-1]

                    k_val = float(k_val) if not pd.isna(k_val) else None
                    d_val = float(d_val) if not pd.isna(d_val) else None

                    if return_components:
                        return (k_val, d_val)
                    return k_val
            except Exception as e:
                logger.debug(f"pandas-ta Stochastic failed, using fallback: {e}")

        # Native implementation
        recent_highs = highs[-k_period:]
        recent_lows = lows[-k_period:]
        highest_high: float = float(np.max(recent_highs))
        lowest_low: float = float(np.min(recent_lows))
        current_close = closes[-1]

        if highest_high != lowest_low:
            k_val = 100.0 * (current_close - lowest_low) / (highest_high - lowest_low)
        else:
            k_val = 50.0

        # For %D, we'd need historical %K values - use current %K as approximation
        d_val = k_val

        if return_components:
            return (k_val, d_val)
        return k_val

    # ========================================================================
    # Stochastic RSI
    # ========================================================================

    def stochrsi(
        self,
        rsi_values: Union[pd.Series, List, np.ndarray],
        period: int = 14,
        k_period: int = 3,
        d_period: int = 3,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate Stochastic RSI from pre-calculated RSI values.

        Stochastic RSI applies the Stochastic formula to RSI values,
        creating an oscillator of an oscillator.

        Args:
            rsi_values: Pre-calculated RSI values.
            period: Stochastic period (default 14).
            k_period: %K smoothing period (default 3).
            d_period: %D smoothing period (default 3).

        Returns:
            Tuple of (%K, %D) or (None, None) if insufficient data.
        """
        min_required = period + k_period + d_period - 2
        is_valid, rsi_arr = self._validate_input(
            rsi_values, min_length=min_required, name="StochRSI"
        )

        if not is_valid:
            return (None, None)

        if self.use_pandas_ta and PANDAS_TA_AVAILABLE:
            try:
                rsi_series = pd.Series(rsi_arr)
                result = ta.stochrsi(rsi_series, length=period, k=k_period, d=d_period)
                if result is not None and not result.empty:
                    k_col = f"STOCHRSIk_{period}_{k_period}_{d_period}"
                    d_col = f"STOCHRSId_{period}_{k_period}_{d_period}"
                    k_val = result[k_col].iloc[-1] if k_col in result.columns else None
                    d_val = result[d_col].iloc[-1] if d_col in result.columns else None

                    k_val = float(k_val) if k_val is not None and not pd.isna(k_val) else None
                    d_val = float(d_val) if d_val is not None and not pd.isna(d_val) else None

                    return (k_val, d_val)
            except Exception as e:
                logger.debug(f"pandas-ta StochRSI failed, using fallback: {e}")

        # Native pandas vectorized implementation
        try:
            rsi_series = pd.Series(rsi_arr, name="rsi")

            # Rolling min/max of RSI
            rsi_min = rsi_series.rolling(window=period).min()
            rsi_max = rsi_series.rolling(window=period).max()

            # Stochastic RSI %K (raw)
            denominator = rsi_max - rsi_min
            stoch_rsi = pd.Series(index=rsi_series.index, dtype=float)
            non_zero_mask = denominator != 0
            stoch_rsi[non_zero_mask] = (
                (rsi_series[non_zero_mask] - rsi_min[non_zero_mask]) / denominator[non_zero_mask]
            ) * 100
            stoch_rsi[~non_zero_mask] = np.nan

            # Smooth %K
            k_smooth = stoch_rsi.rolling(window=k_period).mean()

            # %D is smoothed %K
            d_smooth = k_smooth.rolling(window=d_period).mean()

            k_val = k_smooth.iloc[-1]
            d_val = d_smooth.iloc[-1]

            if pd.isna(k_val) or pd.isna(d_val):
                return (None, None)

            if not np.isfinite(k_val) or not np.isfinite(d_val):
                return (None, None)

            k_val = float(k_val)
            d_val = float(d_val)

            if not (0 <= k_val <= 100) or not (0 <= d_val <= 100):
                return (None, None)

            return (round(k_val, 2), round(d_val, 2))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.debug(f"StochRSI calculation error: {e}")
            return (None, None)

    # ========================================================================
    # CCI (Commodity Channel Index)
    # ========================================================================

    def cci(
        self,
        high: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        period: int = 20,
    ) -> Optional[float]:
        """
        Calculate Commodity Channel Index (CCI).

        CCI measures the current price level relative to an average price
        level over a given period.

        Args:
            high: High prices.
            low: Low prices.
            close: Close prices.
            period: CCI period (default 20).

        Returns:
            CCI value or None.
        """
        is_valid_h, highs = self._validate_input(high, min_length=period, name="CCI high")
        is_valid_l, lows = self._validate_input(low, min_length=period, name="CCI low")
        is_valid_c, closes = self._validate_input(close, min_length=period, name="CCI close")

        if not (is_valid_h and is_valid_l and is_valid_c):
            return None

        if self.use_pandas_ta:
            try:
                df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
                result = ta.cci(df['high'], df['low'], df['close'], length=period)
                if result is not None and not result.empty:
                    return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else None
            except Exception as e:
                logger.debug(f"pandas-ta CCI failed, using fallback: {e}")

        # Native implementation
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]
        recent_closes = closes[-period:]

        tp_list = (recent_highs + recent_lows + recent_closes) / 3
        tp_sma = np.mean(tp_list)
        mean_deviation = np.mean(np.abs(tp_list - tp_sma))
        current_tp = (highs[-1] + lows[-1] + closes[-1]) / 3

        if mean_deviation > 0:
            return (current_tp - tp_sma) / (0.015 * mean_deviation)
        return 0.0

    # ========================================================================
    # OBV (On-Balance Volume)
    # ========================================================================

    def obv(
        self,
        close: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        volume: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        return_array: bool = False,
    ) -> Union[Optional[float], Optional[np.ndarray]]:
        """
        Calculate On-Balance Volume (OBV).

        OBV is a momentum indicator that uses volume flow to predict
        changes in stock price.

        Args:
            close: Close prices.
            volume: Volume data.
            return_array: If True, return full array.

        Returns:
            OBV value(s) or None.
        """
        is_valid_c, closes = self._validate_input(close, min_length=2, name="OBV close")
        is_valid_v, volumes = self._validate_input(volume, min_length=2, name="OBV volume")

        if not (is_valid_c and is_valid_v):
            return (
                np.full(len(close) if isinstance(close, (list, np.ndarray)) else len(close), np.nan)
                if return_array
                else None
            )

        if self.use_pandas_ta:
            try:
                close_series = pd.Series(closes)
                vol_series = pd.Series(volumes)
                result = ta.obv(close_series, vol_series)
                if return_array:
                    return result.values
                return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else None
            except Exception as e:
                logger.debug(f"pandas-ta OBV failed, using fallback: {e}")

        # Native implementation
        obv_values = np.zeros(len(closes))
        obv_values[0] = volumes[0]

        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv_values[i] = obv_values[i - 1] + volumes[i]
            elif closes[i] < closes[i - 1]:
                obv_values[i] = obv_values[i - 1] - volumes[i]
            else:
                obv_values[i] = obv_values[i - 1]

        if return_array:
            return obv_values
        return float(obv_values[-1])

    # ========================================================================
    # Williams %R
    # ========================================================================

    def williams_r(
        self,
        high: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        low: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        close: Union[pd.DataFrame, pd.Series, List, np.ndarray],
        period: int = 14,
    ) -> Optional[float]:
        """
        Calculate Williams %R.

        Williams %R is a momentum indicator that measures overbought
        and oversold levels.

        Args:
            high: High prices.
            low: Low prices.
            close: Close prices.
            period: Lookback period (default 14).

        Returns:
            Williams %R value (-100 to 0) or None.
        """
        is_valid_h, highs = self._validate_input(high, min_length=period, name="Williams %R high")
        is_valid_l, lows = self._validate_input(low, min_length=period, name="Williams %R low")
        is_valid_c, closes = self._validate_input(
            close, min_length=period, name="Williams %R close"
        )

        if not (is_valid_h and is_valid_l and is_valid_c):
            return None

        if self.use_pandas_ta:
            try:
                df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
                result = ta.willr(df['high'], df['low'], df['close'], length=period)
                if result is not None and not result.empty:
                    return float(result.iloc[-1]) if not pd.isna(result.iloc[-1]) else None
            except Exception as e:
                logger.debug(f"pandas-ta Williams %R failed, using fallback: {e}")

        # Native implementation
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]
        highest_high: float = float(np.max(recent_highs))
        lowest_low: float = float(np.min(recent_lows))
        current_close: float = float(closes[-1])

        if highest_high != lowest_low:
            return ((highest_high - current_close) / (highest_high - lowest_low)) * -100
        return -50.0

    # ========================================================================
    # ROC (Rate of Change)
    # ========================================================================

    def roc(
        self, data: Union[pd.DataFrame, pd.Series, List, np.ndarray], period: int = 14
    ) -> Optional[float]:
        """
        Calculate Rate of Change (ROC).

        ROC measures the percentage change in price between the current
        price and the price a certain number of periods ago.

        Args:
            data: Price data.
            period: Lookback period (default 14).

        Returns:
            ROC value (as decimal, e.g., 0.05 for 5%) or None.
        """
        is_valid, prices = self._validate_input(data, min_length=period + 1, name="ROC")
        if not is_valid:
            return None

        if self.use_pandas_ta:
            try:
                series = pd.Series(prices)
                result = ta.roc(series, length=period)
                if result is not None and not result.empty:
                    # pandas-ta returns percentage, convert to decimal
                    val = result.iloc[-1]
                    return float(val / 100.0) if not pd.isna(val) else None
            except Exception as e:
                logger.debug(f"pandas-ta ROC failed, using fallback: {e}")

        # Native implementation
        if len(prices) > period and prices[-period - 1] != 0:
            return (prices[-1] - prices[-period - 1]) / prices[-period - 1]
        return None

    # ========================================================================
    # Convenience Methods
    # ========================================================================

    def _calculate_rsi_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate RSI indicator if data permits."""
        if 'close' not in df.columns:
            return {}
        return {'rsi': self.rsi(df['close'])}

    def _calculate_ema_indicators(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate EMA indicators if data permits."""
        if 'close' not in df.columns:
            return {}
        return {
            'ema_20': self.ema(df['close'], period=20),
            'ema_50': self.ema(df['close'], period=50),
        }

    def _calculate_sma_indicators(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate SMA indicators if data permits."""
        if 'close' not in df.columns:
            return {}
        return {'sma_20': self.sma(df['close'], period=20)}

    def _calculate_macd_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate MACD indicator if data permits."""
        if 'close' not in df.columns:
            return {}
        macd_result = self.macd(df['close'], return_components=True)
        if isinstance(macd_result, tuple) and len(macd_result) == 3:
            return {
                'macd': macd_result[0],
                'macd_signal': macd_result[1],
                'macd_histogram': macd_result[2],
            }
        return {}

    def _calculate_atr_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate ATR indicator if OHLC data is available."""
        if not all(col in df.columns for col in self.REQUIRED_OHLC):
            return {}
        return {'atr': self.atr(df['high'], df['low'], df['close'])}

    def _calculate_bollinger_indicator(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """Calculate Bollinger Bands if data permits."""
        if 'close' not in df.columns:
            return {}
        bands = self.bollinger_bands(df['close'], return_components=False)
        if isinstance(bands, dict):
            return bands
        return {}

    def _calculate_adx_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate ADX indicator if OHLC data is available."""
        if not all(col in df.columns for col in self.REQUIRED_OHLC):
            return {}
        adx_result = self.adx(df['high'], df['low'], df['close'], return_components=True)
        if isinstance(adx_result, tuple) and len(adx_result) == 3:
            return {
                'adx': adx_result[0],
                'plus_di': adx_result[1],
                'minus_di': adx_result[2],
            }
        return {}

    def _calculate_stochastic_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate Stochastic indicator if OHLC data is available."""
        if not all(col in df.columns for col in self.REQUIRED_OHLC):
            return {}
        stoch_result = self.stochastic(df['high'], df['low'], df['close'], return_components=True)
        if isinstance(stoch_result, tuple) and len(stoch_result) == 2:
            return {'stoch_k': stoch_result[0], 'stoch_d': stoch_result[1]}
        return {}

    def _calculate_cci_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate CCI indicator if OHLC data is available."""
        if not all(col in df.columns for col in self.REQUIRED_OHLC):
            return {}
        return {'cci': self.cci(df['high'], df['low'], df['close'])}

    def _calculate_williams_r_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate Williams %R indicator if OHLC data is available."""
        if not all(col in df.columns for col in self.REQUIRED_OHLC):
            return {}
        return {'williams_r': self.williams_r(df['high'], df['low'], df['close'])}

    def _calculate_obv_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate OBV indicator if close and volume data is available."""
        if 'close' not in df.columns or 'volume' not in df.columns:
            return {}
        return {'obv': self.obv(df['close'], df['volume'])}

    def _calculate_roc_indicator(
        self, df: pd.DataFrame
    ) -> Dict[str, Optional[Union[float, np.ndarray]]]:
        """Calculate ROC indicator if data permits."""
        if 'close' not in df.columns:
            return {}
        return {'roc': self.roc(df['close'])}

    def calculate_all(
        self, df: pd.DataFrame, indicators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate multiple indicators at once.

        Args:
            df: DataFrame with OHLCV columns.
            indicators: List of indicator names to calculate.
                       If None, calculates all available indicators.

        Returns:
            Dictionary with all calculated indicator values.
        """
        default_indicators = [
            'rsi',
            'ema_20',
            'ema_50',
            'sma_20',
            'macd',
            'atr',
            'bollinger',
            'adx',
            'stochastic',
            'cci',
            'williams_r',
        ]
        indicators_to_calc = indicators if indicators is not None else default_indicators

        indicator_calculators: Dict[
            str,
            Callable[[pd.DataFrame], Dict[str, Any]],
        ] = {
            'rsi': self._calculate_rsi_indicator,
            'ema_20': self._calculate_ema_indicators,
            'ema_50': self._calculate_ema_indicators,
            'sma_20': self._calculate_sma_indicators,
            'macd': self._calculate_macd_indicator,
            'atr': self._calculate_atr_indicator,
            'bollinger': self._calculate_bollinger_indicator,
            'adx': self._calculate_adx_indicator,
            'stochastic': self._calculate_stochastic_indicator,
            'cci': self._calculate_cci_indicator,
            'williams_r': self._calculate_williams_r_indicator,
            'obv': self._calculate_obv_indicator,
            'roc': self._calculate_roc_indicator,
        }

        results: Dict[str, Optional[Union[float, np.ndarray]]] = {}
        processed_calculators: set = set()

        for indicator in indicators_to_calc:
            calculator = indicator_calculators.get(indicator)
            if calculator is None:
                continue

            calculator_key = calculator.__name__
            if calculator_key in processed_calculators:
                continue
            processed_calculators.add(calculator_key)

            try:
                indicator_results = calculator(df)
                results.update(indicator_results)
            except Exception as e:
                logger.warning(f"Failed to calculate {indicator}: {e}")
                results[indicator] = None

        return results


# Alias for backward compatibility
TechnicalIndicatorCalculator = TechnicalIndicators
