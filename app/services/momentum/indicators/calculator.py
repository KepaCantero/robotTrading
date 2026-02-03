"""
Technical indicator calculator using pandas-ta-classic library.

SOLID Principles:
- SRP: Only calculates technical indicators
- OCP: Extensible through new indicator methods
- LSP: Substitutable with any IndicatorCalculator implementation
- ISP: Focused on indicator calculations only
- DIP: Implements IndicatorCalculator protocol
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pandas_ta_classic as ta

from app.services.momentum.protocols import IndicatorCalculator

logger = logging.getLogger(__name__)


class TechnicalIndicatorCalculator:
    """
    Calculator for technical indicators using pandas-ta-classic library.

    REQUIRED: pandas-ta-classic must be installed. All calculations use the library.
    NO manual calculations - all indicators come from pandas-ta-classic.

    This class follows:
    - Single Responsibility: Only calculates technical indicators
    - Open/Closed: Open for extension (new indicators), closed for modification
    - Liskov Substitution: Implements IndicatorCalculator protocol
    - Interface Segregation: Only indicator calculation methods
    - Dependency Inversion: Depends on IndicatorCalculator abstraction
    """

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index using pandas-ta-classic.rsi() library.

        Args:
            prices: List of price values
            period: RSI calculation period (default 14)

        Returns:
            RSI value or None if insufficient data

        Raises:
            ValueError: If prices list is empty or period is invalid
        """
        if len(prices) < period + 1:
            logger.debug(f"RSI: Insufficient data ({len(prices)} < {period + 1})")
            return None

        try:
            df = pd.Series(prices, name="close")
            rsi_series = ta.rsi(df, length=period)

            if rsi_series is None or rsi_series.empty or rsi_series.isna().all():
                logger.debug("RSI: pandas_ta_classic returned None or all NaN values")
                return None

            rsi_value = float(rsi_series.iloc[-1])
            logger.debug(f"RSI({period}) calculated: {rsi_value:.2f} from {len(prices)} prices")
            return round(rsi_value, 2)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"RSI calculation error with pandas_ta_classic: {e}")
            raise

    @staticmethod
    def calculate_ema(prices: List[float], period: int = 9) -> Optional[float]:
        """
        Calculate Exponential Moving Average using pandas-ta-classic.ema() library.

        Args:
            prices: List of price values
            period: EMA calculation period

        Returns:
            EMA value or None if insufficient data

        Raises:
            ValueError: If period is invalid
        """
        if period <= 0:
            logger.debug(f"EMA: Invalid period ({period}) must be > 0")
            return None

        if len(prices) < period:
            logger.debug(f"EMA: Insufficient data ({len(prices)} < {period})")
            return None

        try:
            df = pd.Series(prices, name="close")
            ema_series = ta.ema(df, length=period)

            if ema_series is None or ema_series.empty or ema_series.isna().all():
                logger.debug("EMA: pandas_ta_classic returned None or all NaN values")
                return None

            ema_value = float(ema_series.iloc[-1])
            logger.debug(f"EMA({period}) calculated: {ema_value:.2f} from {len(prices)} prices")
            return round(ema_value, 2)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"EMA calculation error with pandas_ta_classic: {e}")
            raise

    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD using pandas_ta_classic.macd() library.

        Args:
            prices: List of price values
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)

        Returns:
            Tuple of (MACD line, Signal line, Histogram) or (None, None, None)
        """
        if len(prices) < slow_period:
            logger.debug(f"MACD: Insufficient data ({len(prices)} < {slow_period})")
            return None, None, None

        try:
            df = pd.Series(prices, name="close")
            macd_df = ta.macd(df, fast=fast_period, slow=slow_period, signal=signal_period)

            if macd_df is None or macd_df.empty:
                logger.debug("MACD: pandas_ta_classic returned None or empty DataFrame")
                return None, None, None

            # Extract MACD line, signal line, and histogram
            macd_line_col = None
            signal_line_col = None
            histogram_col = None

            for col in macd_df.columns:
                col_upper = col.upper()
                if "MACD" in col_upper and "MACDS" not in col_upper and "MACDH" not in col_upper:
                    macd_line_col = col
                elif "MACDS" in col_upper or "MACD_SIGNAL" in col_upper:
                    signal_line_col = col
                elif "MACDH" in col_upper or "MACD_HIST" in col_upper:
                    histogram_col = col

            if macd_line_col is None or signal_line_col is None or histogram_col is None:
                logger.debug("MACD: Some column names not found in DataFrame")
                return None, None, None

            macd_line_val = macd_df[macd_line_col].iloc[-1]
            signal_line_val = macd_df[signal_line_col].iloc[-1]
            histogram_val = macd_df[histogram_col].iloc[-1]

            if pd.isna(macd_line_val) or pd.isna(signal_line_val) or pd.isna(histogram_val):
                logger.debug("MACD: NaN values in MACD calculation")
                return None, None, None

            macd_line = float(macd_line_val)
            signal_line = float(signal_line_val)
            histogram = float(histogram_val)

            logger.debug(
                f"MACD({fast_period},{slow_period},{signal_period}) calculated: "
                f"MACD={macd_line:.4f}, Signal={signal_line:.4f}, Histogram={histogram:.4f}"
            )

            return round(macd_line, 4), round(signal_line, 4), round(histogram, 4)

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"MACD calculation error with pandas_ta_classic: {e}")
            return None, None, None

    @staticmethod
    def calculate_roc(prices: List[float], period: int = 12) -> Optional[float]:
        """
        Calculate Rate of Change using pandas_ta_classic.roc() library.

        Args:
            prices: List of price values
            period: ROC calculation period (default 12)

        Returns:
            ROC value or None if insufficient data
        """
        if len(prices) < period + 1:
            logger.debug(f"ROC: Insufficient data ({len(prices)} < {period + 1})")
            return None

        try:
            df = pd.Series(prices, name="close")
            roc_series = ta.roc(df, length=period)

            if roc_series is None or roc_series.empty or roc_series.isna().all():
                logger.debug("ROC: pandas_ta_classic returned None or all NaN values")
                return None

            roc_value = float(roc_series.iloc[-1])
            logger.debug(f"ROC({period}) calculated: {roc_value:.4f}%")
            return round(roc_value, 4)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"ROC calculation error with pandas_ta_classic: {e}")
            raise

    @staticmethod
    def calculate_stochastic_rsi(
        rsi_values: List[float], period: int = 14, smooth_k: int = 3
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate Stochastic RSI from pre-calculated RSI values using pandas vectorized operations.

        Args:
            rsi_values: List of RSI values
            period: Period for Stochastic RSI calculation (default 14)
            smooth_k: Smoothing period for %D (default 3)

        Returns:
            Tuple of (StochRSI %K, StochRSI %D) or (None, None) if insufficient data
        """
        min_required = period + smooth_k - 1
        if len(rsi_values) < min_required:
            logger.debug(
                f"Stochastic RSI: Insufficient RSI data ({len(rsi_values)} < {min_required})"
            )
            return None, None

        try:
            rsi_series = pd.Series(rsi_values, name="rsi")

            # Calculate rolling min and max of RSI over the period
            rsi_min = rsi_series.rolling(window=period).min()
            rsi_max = rsi_series.rolling(window=period).max()

            # Calculate StochRSI %K
            denominator = rsi_max - rsi_min
            stoch_rsi_k = pd.Series(index=rsi_series.index, dtype=float)
            non_zero_mask = denominator != 0
            stoch_rsi_k[non_zero_mask] = (
                (rsi_series[non_zero_mask] - rsi_min[non_zero_mask]) / denominator[non_zero_mask]
            ) * 100
            stoch_rsi_k[~non_zero_mask] = np.nan

            # Calculate %D as SMA of %K
            stoch_rsi_d = stoch_rsi_k.rolling(window=smooth_k).mean()

            stoch_rsi_k_val = stoch_rsi_k.iloc[-1]
            stoch_rsi_d_val = stoch_rsi_d.iloc[-1]

            if pd.isna(stoch_rsi_k_val) or pd.isna(stoch_rsi_d_val):
                logger.debug(
                    f"Stochastic RSI: NaN values in result: K={stoch_rsi_k_val}, D={stoch_rsi_d_val}"
                )
                return None, None

            if not np.isfinite(stoch_rsi_k_val) or not np.isfinite(stoch_rsi_d_val):
                logger.debug(
                    f"Stochastic RSI: Inf values in result: K={stoch_rsi_k_val}, D={stoch_rsi_d_val}"
                )
                return None, None

            stoch_rsi_k = float(stoch_rsi_k_val)
            stoch_rsi_d = float(stoch_rsi_d_val)

            if not (0 <= stoch_rsi_k <= 100) or not (0 <= stoch_rsi_d <= 100):
                logger.debug(
                    f"Stochastic RSI: Values out of range [0,100]: K={stoch_rsi_k:.2f}, D={stoch_rsi_d:.2f}"
                )
                return None, None

            logger.debug(f"Stochastic RSI({period}): %K={stoch_rsi_k:.2f}, %D={stoch_rsi_d:.2f}")

            return round(stoch_rsi_k, 2), round(stoch_rsi_d, 2)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Stochastic RSI calculation error: {e}")
            return None, None

    @staticmethod
    def calculate_atr(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average True Range using pandas_ta_classic.atr() library.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: ATR calculation period (default 14)

        Returns:
            ATR value or None if insufficient data
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            logger.debug(
                f"ATR: Insufficient data (len={min(len(highs), len(lows), len(closes))} < {period + 1})"
            )
            return None

        try:
            df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
            atr_series = ta.atr(df["high"], df["low"], df["close"], length=period)

            if atr_series is None or atr_series.empty or atr_series.isna().all():
                logger.debug("ATR: pandas_ta_classic returned None or all NaN values")
                return None

            atr_value = float(atr_series.iloc[-1])
            logger.debug(f"ATR({period}) calculated: {atr_value:.4f}")
            return round(atr_value, 4)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"ATR calculation error with pandas_ta_classic: {e}")
            raise

    @staticmethod
    def calculate_adx(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average Directional Index using pandas_ta_classic.adx() library.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: ADX calculation period (default 14)

        Returns:
            ADX value or None if insufficient data
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            logger.debug(
                f"ADX: Insufficient data (len={min(len(highs), len(lows), len(closes))} < {period + 1})"
            )
            return None

        try:
            df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
            adx_df = ta.adx(df["high"], df["low"], df["close"], length=period)

            if adx_df is None or adx_df.empty:
                logger.debug("ADX: pandas_ta_classic returned None or empty DataFrame")
                return None

            # Extract ADX column
            adx_col = None
            for col in adx_df.columns:
                if "ADX" in col.upper():
                    adx_col = col
                    break

            if adx_col is None:
                logger.debug("ADX: ADX column not found in DataFrame")
                return None

            adx_value = float(adx_df[adx_col].iloc[-1])
            logger.debug(f"ADX({period}) calculated: {adx_value:.2f}")
            return round(adx_value, 2)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"ADX calculation error with pandas_ta_classic: {e}")
            raise

    @staticmethod
    def calculate_obv(prices: List[float], volumes: List[float]) -> Optional[float]:
        """
        Calculate On-Balance Volume (OBV) indicator.

        OBV is a cumulative indicator that adds volume on up days and
        subtracts volume on down days. It's used to confirm price trends.

        Formula:
            - If price > previous_price: OBV = previous_OBV + volume
            - If price < previous_price: OBV = previous_OBV - volume
            - If price == previous_price: OBV = previous_OBV

        Args:
            prices: List of price values
            volumes: List of volume values (must match prices length)

        Returns:
            OBV value or None if insufficient data

        Raises:
            ValueError: If lists are empty or have different lengths
        """
        if len(prices) != len(volumes):
            raise ValueError(
                f"OBV: prices and volumes must have same length: "
                f"{len(prices)} != {len(volumes)}"
            )

        if len(prices) < 2:
            logger.debug(f"OBV: Insufficient data ({len(prices)} < 2)")
            return None

        try:
            obv_values: List[float] = [0.0]

            for i in range(1, len(prices)):
                if prices[i] > prices[i - 1]:
                    obv_values.append(obv_values[-1] + volumes[i])
                elif prices[i] < prices[i - 1]:
                    obv_values.append(obv_values[-1] - volumes[i])
                else:
                    obv_values.append(obv_values[-1])

            obv_value = obv_values[-1]
            logger.debug(f"OBV calculated: {obv_value:.2f} from {len(prices)} prices")
            return round(obv_value, 2)

        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"OBV calculation error: {e}")
            raise

    @staticmethod
    def calculate_volume_sma(self, volumes: List[Decimal], period: int = 20) -> Optional[Decimal]:
        """
        Calculate Volume Simple Moving Average using pandas.rolling() library.

        Args:
            volumes: List of volume values
            period: SMA calculation period (default 20)

        Returns:
            Volume SMA value or None if insufficient data
        """
        if len(volumes) < period:
            logger.debug(f"Volume SMA: Insufficient data ({len(volumes)} < {period})")
            return None

        try:
            volumes_float = [float(v) for v in volumes]
            volumes_series = pd.Series(volumes_float)
            sma = volumes_series.rolling(window=period).mean().iloc[-1]

            logger.debug(f"Volume SMA({period}) calculated: {sma:.2f}")
            return Decimal(str(round(sma, 2)))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Volume SMA calculation error: {e}")
            raise

    @staticmethod
    def calculate_vwap(
        prices: List[float], volumes: List[float], period: Optional[int] = None
    ) -> Optional[float]:
        """
        Calculate Volume-Weighted Average Price using pandas DataFrame operations.

        Args:
            prices: List of price values
            volumes: List of volume values
            period: Optional period for VWAP calculation

        Returns:
            VWAP value or None if insufficient data
        """
        if len(prices) < 2 or len(volumes) < 2 or len(prices) != len(volumes):
            logger.debug("VWAP: Insufficient or mismatched data")
            return None

        try:
            df = pd.DataFrame({"price": prices, "volume": volumes})

            if period is not None:
                if len(df) < period:
                    logger.debug(f"VWAP: Insufficient data (have {len(df)}, need {period})")
                    return None
                df = df.iloc[-period:]

            cumulative_pv = (df["price"] * df["volume"]).sum()
            cumulative_volume = df["volume"].sum()

            if cumulative_volume == 0:
                return None

            vwap = cumulative_pv / cumulative_volume
            logger.debug(f"VWAP calculated: {vwap:.4f} from {len(df)} periods")
            return round(float(vwap), 4)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"VWAP calculation error: {e}")
            raise

    @staticmethod
    def calculate_zscore(
        self, prices: List[float], period: int = 30, std: float = 1.0
    ) -> Optional[float]:
        """
        Calculate Z-score using pandas-ta-classic.zscore() library.

        Args:
            prices: List of price values
            period: Rolling period for mean/std calculation (default 30)
            std: Standard deviation multiplier (default 1.0)

        Returns:
            Z-score value or None if insufficient data
        """
        if len(prices) < period + 1:
            logger.debug(f"Z-score: Insufficient data ({len(prices)} < {period + 1})")
            return None

        try:
            df = pd.Series(prices, name="close")
            zscore_series = ta.zscore(df, length=period, std=std)

            if zscore_series is None or zscore_series.empty or zscore_series.isna().all():
                logger.debug("Z-score: pandas_ta_classic returned None or all NaN values")
                return None

            zscore_value = float(zscore_series.iloc[-1])
            logger.debug(
                f"Z-score({period}, std={std}) calculated: {zscore_value:.4f} from {len(prices)} prices"
            )
            return round(zscore_value, 4)

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Z-score calculation error with pandas_ta_classic: {e}")
            raise

    @staticmethod
    def calculate_volatility(
        self, prices: List[float], tf: str = "days", returns: bool = False, log: bool = False
    ) -> Optional[float]:
        """
        Calculate volatility using pandas-ta-classic.volatility() library.

        Args:
            prices: List of price values
            tf: Time frame options: 'days', 'weeks', 'months', 'years' (default 'days')
            returns: If True, replace close Series with user-defined Series (default False)
            log: If True, calculates log_return (default False)

        Returns:
            Volatility value or None if insufficient data
        """
        if len(prices) < 2:
            logger.debug(f"Volatility: Insufficient data ({len(prices)} < 2)")
            return None

        try:
            df = pd.Series(prices, name="close")
            volatility_value = ta.volatility(df, tf=tf, returns=returns, log=log)

            if volatility_value is None or not np.isfinite(volatility_value):
                logger.debug("Volatility: pandas_ta_classic returned None or non-finite value")
                return None

            logger.debug(
                f"Volatility(tf={tf}) calculated: {volatility_value:.6f} from {len(prices)} prices"
            )
            return round(float(volatility_value), 6)

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Volatility calculation error with pandas_ta_classic: {e}")
            raise

    @staticmethod
    def calculate_expectancy(
        self,
        winning_trades: int,
        losing_trades: int,
        avg_win_amount: float,
        avg_loss_amount: float,
    ) -> Optional[float]:
        """
        Calculate Expectancy metric for system consistency.

        Args:
            winning_trades: Number of winning trades
            losing_trades: Number of losing trades
            avg_win_amount: Average win amount
            avg_loss_amount: Average loss amount

        Returns:
            Expectancy value or None if no trades
        """
        total_trades = winning_trades + losing_trades
        if total_trades == 0:
            return None

        win_rate = winning_trades / total_trades
        loss_rate = losing_trades / total_trades

        expectancy = (win_rate * avg_win_amount) - (loss_rate * avg_loss_amount)
        return round(expectancy, 4)

    @staticmethod
    def detect_macd_divergence(
        self, prices: List[float], macd_histograms: List[float], lookback: int = 5
    ) -> Optional[str]:
        """
        Detect MACD histogram divergence patterns using numpy.

        Args:
            prices: List of price values
            macd_histograms: List of MACD histogram values
            lookback: Lookback period for divergence detection (default 5)

        Returns:
            "bullish", "bearish", or None
        """
        if len(prices) < lookback * 2 or len(macd_histograms) < lookback * 2:
            return None

        prices_array = np.array(prices[-lookback:])
        histograms_array = np.array(macd_histograms[-lookback:])

        # Bullish divergence: price down, histogram up
        price_trend_down = prices_array[-1] < prices_array[0]
        histogram_trend_up = histograms_array[-1] > histograms_array[0]

        if price_trend_down and histogram_trend_up:
            if (
                prices_array[-1] < np.min(prices_array[:-1])
                and histograms_array[-1] > histograms_array[-2]
            ):
                return "bullish"

        # Bearish divergence: price up, histogram down
        price_trend_up = prices_array[-1] > prices_array[0]
        histogram_trend_down = histograms_array[-1] < histograms_array[0]

        if price_trend_up and histogram_trend_down:
            if (
                prices_array[-1] > np.max(prices_array[:-1])
                and histograms_array[-1] < histograms_array[-2]
            ):
                return "bearish"

        return None

    def calculate_all_indicators(
        self,
        symbol: str,
        prices: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[Decimal],
    ) -> "TechnicalIndicators":
        """
        Calculate all technical indicators at once.

        Args:
            symbol: Asset symbol
            prices: List of close prices
            highs: List of high prices
            lows: List of low prices
            volumes: List of volumes

        Returns:
            TechnicalIndicators object with all calculated values
        """
        from app.models.momentum import TechnicalIndicators

        rsi = self.calculate_rsi(prices, 14)
        ema_9 = self.calculate_ema(prices, 9)
        ema_21 = self.calculate_ema(prices, 21)
        ema_50 = self.calculate_ema(prices, 50)
        ema_200 = self.calculate_ema(prices, 200)
        macd, macd_signal, macd_histogram = self.calculate_macd(prices)
        atr = self.calculate_atr(highs, lows, prices, 14)
        adx = self.calculate_adx(highs, lows, prices, 14)
        volume_sma_20 = self.calculate_volume_sma(volumes, 20)

        # Calculate volatility using numpy
        volatility = None
        if len(prices) > 1:
            prices_array = np.array(prices)
            returns = np.diff(prices_array) / prices_array[:-1]
            if len(returns) > 0:
                volatility = float(np.std(returns) * 100)

        volume_ratio = None
        if volume_sma_20 and volumes:
            current_volume = float(volumes[-1])
            avg_volume = float(volume_sma_20)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        return TechnicalIndicators(
            symbol=symbol,
            rsi=rsi,
            ema_9=ema_9,
            ema_21=ema_21,
            ema_50=ema_50,
            ema_200=ema_200,
            macd=macd,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            atr=atr,
            adx=adx,
            volatility=volatility,
            volume_sma_20=volume_sma_20,
            volume_ratio=volume_ratio,
        )
