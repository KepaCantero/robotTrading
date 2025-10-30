"""
Momentum strategy service for AlgoTrading system.

This service handles momentum analysis, technical indicator calculations,
and momentum signal generation for trading strategies.

REFACTORED: All indicator calculations now use vectorized libraries:
- pandas_ta (ta) for technical indicators (RSI, EMA, MACD, ATR, ADX, Stochastic, OBV, Bollinger Bands)
- pandas for efficient time series operations
- numpy for statistical calculations
- scipy.stats for advanced statistical tests (cointegration, etc.)
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning("pandas_ta not available, falling back to manual calculations")

# scipy is imported where needed (pairs_trading.py) - not needed here

from app.core.centralized_config import get_config
from app.models.momentum import (
    MomentumAnalysis,
    MomentumFilter,
    MomentumSignal,
    MomentumStrategy,
    MomentumType,
    TechnicalIndicators,
    Timeframe,
)
from app.services.asset_identification import (
    AssetIdentificationService,
    get_asset_identification_service,
)

logger = logging.getLogger(__name__)


class TechnicalIndicatorCalculator:
    """
    Calculator for technical indicators using vectorized libraries.
    
    REFACTORED: Uses pandas_ta for all technical indicator calculations.
    This provides professional-grade, optimized, and well-tested implementations.
    """
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index using pandas_ta.rsi() library.
        
        ✅ USES LIBRARY: pandas_ta.rsi() - NO manual calculations
        Only falls back to manual if pandas_ta is not available.
        """
        if len(prices) < period + 1:
            logger.debug(f"RSI: Insufficient data ({len(prices)} < {period + 1})")
            return None
        
        if not PANDAS_TA_AVAILABLE:
            # Fallback to manual calculation if pandas_ta not available
            return TechnicalIndicatorCalculator._calculate_rsi_manual(prices, period)
        
        try:
            # ✅ USE LIBRARY: Convert to pandas Series and use pandas_ta.rsi()
            df = pd.Series(prices, name='close')
            rsi_series = ta.rsi(df, length=period)
            
            if rsi_series is None or rsi_series.empty or rsi_series.isna().all():
                logger.debug("RSI: pandas_ta returned None or all NaN values")
                return None
            
            # Get last valid value
            rsi_value = float(rsi_series.iloc[-1])
            
            logger.debug(f"RSI({period}) calculated: {rsi_value:.2f} from {len(prices)} prices")
            return round(rsi_value, 2)
            
        except Exception as e:
            logger.warning(f"RSI calculation error with pandas_ta: {e}, falling back to manual")
            return TechnicalIndicatorCalculator._calculate_rsi_manual(prices, period)
    
    @staticmethod
    def _calculate_rsi_manual(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Fallback manual RSI calculation using numpy.
        
        ⚠️ ONLY USED IF pandas_ta IS NOT AVAILABLE
        Uses numpy for vectorized operations but prefer pandas_ta library.
        """
        if len(prices) < period + 1:
            return None
        
        # REFACTORED: Use numpy for vectorized gain/loss calculation
        prices_array = np.array(prices)
        changes = np.diff(prices_array)
        
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, np.abs(changes), 0)
        
        if len(gains) < period:
            return None
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(float(rsi), 2)
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average using pandas_ta.ema() library.
        
        ✅ USES LIBRARY: pandas_ta.ema() - NO manual calculations
        Only falls back to manual if pandas_ta is not available.
        """
        # Validate period to prevent errors with negative or zero periods
        if period <= 0:
            logger.debug(f"EMA: Invalid period ({period}) must be > 0")
            return None
            
        if len(prices) < period:
            logger.debug(f"EMA: Insufficient data ({len(prices)} < {period})")
            return None
        
        if not PANDAS_TA_AVAILABLE:
            # Fallback to manual calculation
            return TechnicalIndicatorCalculator._calculate_ema_manual(prices, period)
        
        try:
            # ✅ USE LIBRARY: Convert to pandas Series and use pandas_ta.ema()
            df = pd.Series(prices, name='close')
            ema_series = ta.ema(df, length=period)
            
            if ema_series is None or ema_series.empty or ema_series.isna().all():
                logger.debug("EMA: pandas_ta returned None or all NaN values")
                return None
            
            ema_value = float(ema_series.iloc[-1])
            
            logger.debug(f"EMA({period}) calculated: {ema_value:.2f} from {len(prices)} prices")
            return round(ema_value, 2)
            
        except Exception as e:
            logger.warning(f"EMA calculation error with pandas_ta: {e}, falling back to manual")
            return TechnicalIndicatorCalculator._calculate_ema_manual(prices, period)
    
    @staticmethod
    def _calculate_ema_manual(prices: List[float], period: int) -> Optional[float]:
        """
        Fallback manual EMA calculation using pandas ewm.
        
        ⚠️ ONLY USED IF pandas_ta IS NOT AVAILABLE
        Uses pandas ewm() which is vectorized but prefer pandas_ta library.
        """
        # Validate period to prevent ValueError from pandas
        if period <= 0:
            return None
            
        if len(prices) < period:
            return None
        
        try:
            # Use pandas for EMA calculation (more efficient than manual loop)
            prices_series = pd.Series(prices)
            
            # Calculate EMA using pandas ewm (exponential weighted mean)
            # span parameter automatically handles the multiplier calculation
            # span must be >= 1, so we validate period before this
            ema = prices_series.ewm(span=period, adjust=False).mean().iloc[-1]
            
            return round(float(ema), 2)
        except ValueError as e:
            # pandas.ewm() raises ValueError if span < 1
            logger.debug(f"EMA manual calculation error: {e}")
            return None
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD using pandas_ta.macd() library.
        
        ✅ USES LIBRARY: pandas_ta.macd() - NO manual calculations
        Returns (MACD line, Signal line, Histogram)
        Only falls back to manual if pandas_ta is not available.
        """
        if len(prices) < slow_period:
            logger.debug(f"MACD: Insufficient data ({len(prices)} < {slow_period})")
            return None, None, None
        
        if not PANDAS_TA_AVAILABLE:
            # Fallback to manual calculation using EMAs
            return TechnicalIndicatorCalculator._calculate_macd_manual(
                prices, fast_period, slow_period, signal_period
            )
        
        try:
            # ✅ USE LIBRARY: Convert to pandas Series and use pandas_ta.macd()
            df = pd.Series(prices, name='close')
            macd_df = ta.macd(df, fast=fast_period, slow=slow_period, signal=signal_period)
            
            if macd_df is None or macd_df.empty:
                logger.debug("MACD: pandas_ta returned None or empty DataFrame")
                return None, None, None
            
            # Extract MACD line, signal line, and histogram (pandas_ta may use different naming)
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
            
            # Get last valid values
            macd_line = float(macd_df[macd_line_col].iloc[-1])
            signal_line = float(macd_df[signal_line_col].iloc[-1])
            histogram = float(macd_df[histogram_col].iloc[-1])
            
            logger.debug(
                f"MACD({fast_period},{slow_period},{signal_period}) calculated: "
                f"MACD={macd_line:.4f}, Signal={signal_line:.4f}, Histogram={histogram:.4f}"
            )
            
            return round(macd_line, 4), round(signal_line, 4), round(histogram, 4)
            
        except Exception as e:
            logger.warning(f"MACD calculation error with pandas_ta: {e}, falling back to manual")
            return TechnicalIndicatorCalculator._calculate_macd_manual(
                prices, fast_period, slow_period, signal_period
            )
    
    @staticmethod
    def _calculate_macd_manual(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Fallback manual MACD calculation using EMAs.
        
        ⚠️ ONLY USED IF pandas_ta IS NOT AVAILABLE
        This is a simplified approximation - prefer using pandas_ta library.
        """
        if len(prices) < slow_period:
            return None, None, None
        
        # Calculate fast and slow EMAs
        ema_fast = TechnicalIndicatorCalculator.calculate_ema(prices, fast_period)
        ema_slow = TechnicalIndicatorCalculator.calculate_ema(prices, slow_period)
        
        if ema_fast is None or ema_slow is None:
            return None, None, None
        
        macd_line = ema_fast - ema_slow
        
        # For signal line, we need MACD history. Simplified approach:
        # Calculate EMA of MACD line values
        # Note: Full implementation would track MACD history and apply EMA to it
        signal_line = macd_line * 0.9  # Simplified approximation
        
        histogram = macd_line - signal_line
        
        return round(macd_line, 4), round(signal_line, 4), round(histogram, 4)
    
    @staticmethod
    def calculate_roc(prices: List[float], period: int = 12) -> Optional[float]:
        """
        Calculate Rate of Change using pandas_ta.roc() library.
        
        ✅ USES LIBRARY: pandas_ta.roc() - NO manual calculations
        Only falls back to manual if pandas_ta is not available.
        """
        if len(prices) < period + 1:
            logger.debug(f"ROC: Insufficient data ({len(prices)} < {period + 1})")
            return None
        
        if not PANDAS_TA_AVAILABLE:
            return TechnicalIndicatorCalculator._calculate_roc_manual(prices, period)
        
        try:
            df = pd.Series(prices, name='close')
            # ✅ USE LIBRARY: pandas_ta.roc() - vectorized calculation
            roc_series = ta.roc(df, length=period)
            
            if roc_series is None or roc_series.empty or roc_series.isna().all():
                logger.debug("ROC: pandas_ta returned None or all NaN values")
                return None
            
            roc_value = float(roc_series.iloc[-1])
            
            logger.debug(f"ROC({period}) calculated: {roc_value:.4f}%")
            return round(roc_value, 4)
            
        except Exception as e:
            logger.warning(f"ROC calculation error: {e}, falling back to manual")
            return TechnicalIndicatorCalculator._calculate_roc_manual(prices, period)
    
    @staticmethod
    def _calculate_roc_manual(prices: List[float], period: int = 12) -> Optional[float]:
        """
        Fallback manual ROC calculation.
        
        ⚠️ ONLY USED IF pandas_ta IS NOT AVAILABLE
        Simple calculation - prefer using pandas_ta library.
        """
        if len(prices) < period + 1:
            return None
        
        current_price = prices[-1]
        price_periods_ago = prices[-period - 1]
        
        if price_periods_ago == 0:
            return None
        
        roc = ((current_price - price_periods_ago) / price_periods_ago) * 100
        return round(roc, 4)
    
    @staticmethod
    def calculate_obv(prices: List[float], volumes: List[float]) -> Optional[float]:
        """
        Calculate On Balance Volume using pandas_ta.obv() library.
        
        ✅ USES LIBRARY: pandas_ta.obv() - NO manual calculations
        Only falls back to manual if pandas_ta is not available.
        """
        if len(prices) < 2 or len(volumes) < 2 or len(prices) != len(volumes):
            logger.debug(f"OBV: Insufficient or mismatched data (prices={len(prices)}, volumes={len(volumes)})")
            return None
        
        if not PANDAS_TA_AVAILABLE:
            return TechnicalIndicatorCalculator._calculate_obv_manual(prices, volumes)
        
        try:
            # Create DataFrame with close and volume for pandas_ta
            df = pd.DataFrame({
                'close': prices,
                'volume': volumes
            })
            
            # ✅ USE LIBRARY: pandas_ta.obv() - vectorized calculation
            obv_series = ta.obv(df['close'], df['volume'])
            
            if obv_series is None or obv_series.empty or obv_series.isna().all():
                logger.debug("OBV: pandas_ta returned None or all NaN values")
                return None
            
            obv_value = float(obv_series.iloc[-1])
            
            logger.debug(f"OBV calculated: {obv_value:.2f}")
            return round(obv_value, 2)
            
        except Exception as e:
            logger.warning(f"OBV calculation error: {e}, falling back to manual")
            return TechnicalIndicatorCalculator._calculate_obv_manual(prices, volumes)
    
    @staticmethod
    def _calculate_obv_manual(prices: List[float], volumes: List[float]) -> Optional[float]:
        """
        Fallback manual OBV calculation using numpy.
        
        ⚠️ ONLY USED IF pandas_ta IS NOT AVAILABLE
        Uses numpy for vectorized operations but prefer pandas_ta library.
        """
        if len(prices) < 2 or len(volumes) < 2 or len(prices) != len(volumes):
            return None
        
        # Use numpy for vectorized calculation
        prices_array = np.array(prices)
        volumes_array = np.array(volumes)
        
        # Calculate price changes
        price_changes = np.diff(prices_array)
        
        # OBV: add volume when price up, subtract when price down, unchanged when equal
        obv_changes = np.where(price_changes > 0, volumes_array[1:],
                              np.where(price_changes < 0, -volumes_array[1:], 0))
        
        # Cumulative sum
        obv = np.sum(obv_changes)
        
        return round(float(obv), 2)
    
    @staticmethod
    def calculate_stochastic_rsi(rsi_values: List[float], period: int = 14) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate Stochastic RSI using pandas_ta.stochrsi() library.
        
        ✅ USES LIBRARY: pandas_ta.stochrsi() - NO manual calculations
        Only falls back to manual if pandas_ta is not available.
        
        Args:
            rsi_values: List of RSI values
            period: Period for Stochastic RSI calculation (default 14)
            
        Returns:
            Tuple of (StochRSI %K, StochRSI %D) or (None, None) if insufficient data
        """
        if len(rsi_values) < period:
            logger.debug(f"Stochastic RSI: Insufficient RSI data ({len(rsi_values)} < {period})")
            return None, None
        
        # PRIMARY: Use pandas_ta library (vectorized, optimized, tested)
        if not PANDAS_TA_AVAILABLE:
            logger.warning("pandas_ta not available, using manual fallback for Stochastic RSI")
            return TechnicalIndicatorCalculator._calculate_stochastic_rsi_manual(rsi_values, period)
        
        try:
            # Convert RSI values to pandas Series for pandas_ta
            rsi_series = pd.Series(rsi_values, name='rsi')
            
            # ✅ USE LIBRARY: pandas_ta.stochrsi() - vectorized calculation
            # This is the PRIMARY method - uses professional library implementation
            stoch_rsi_df = ta.stochrsi(rsi_series, length=period)
            
            if stoch_rsi_df is None or stoch_rsi_df.empty:
                logger.debug("Stochastic RSI: pandas_ta.stochrsi() returned None or empty DataFrame")
                return None, None
            
            # Extract %K and %D values from pandas_ta result (column names may vary)
            stoch_rsi_k_col = None
            stoch_rsi_d_col = None
            for col in stoch_rsi_df.columns:
                col_upper = col.upper()
                if "STOCHRSIK" in col_upper or "STOCHRSI_K" in col_upper or "K" in col_upper:
                    stoch_rsi_k_col = col
                elif "STOCHRSID" in col_upper or "STOCHRSI_D" in col_upper or "D" in col_upper:
                    stoch_rsi_d_col = col
            
            if stoch_rsi_k_col is None or stoch_rsi_d_col is None:
                logger.debug(f"Stochastic RSI: Column names not found. Available: {list(stoch_rsi_df.columns)}")
                return None, None
            
            # Extract the last values (%K and %D)
            stoch_rsi_k = float(stoch_rsi_df[stoch_rsi_k_col].iloc[-1])
            stoch_rsi_d = float(stoch_rsi_df[stoch_rsi_d_col].iloc[-1])
            
            # Validate values are in expected range [0, 100]
            if not (0 <= stoch_rsi_k <= 100) or not (0 <= stoch_rsi_d <= 100):
                logger.warning(f"Stochastic RSI: Values out of range [0,100]: K={stoch_rsi_k}, D={stoch_rsi_d}")
                return None, None
            
            logger.debug(f"Stochastic RSI({period}) via pandas_ta: %K={stoch_rsi_k:.2f}, %D={stoch_rsi_d:.2f}")
            
            return round(stoch_rsi_k, 2), round(stoch_rsi_d, 2)
            
        except Exception as e:
            logger.warning(f"Stochastic RSI calculation error with pandas_ta: {e}, falling back to manual")
            return TechnicalIndicatorCalculator._calculate_stochastic_rsi_manual(rsi_values, period)
    
    @staticmethod
    def _calculate_stochastic_rsi_manual(rsi_values: List[float], period: int = 14) -> Tuple[Optional[float], Optional[float]]:
        """
        Fallback manual Stochastic RSI calculation.
        
        ⚠️ ONLY USED IF pandas_ta IS NOT AVAILABLE
        This is a simplified fallback - prefer using pandas_ta library.
        """
        if len(rsi_values) < period:
            return None, None
        
        # Get recent period of RSI values
        recent_rsi = np.array(rsi_values[-period:])
        
        highest_rsi = np.max(recent_rsi)
        lowest_rsi = np.min(recent_rsi)
        current_rsi = recent_rsi[-1]
        
        if highest_rsi == lowest_rsi:
            return None, None
        
        stoch_rsi_k = ((current_rsi - lowest_rsi) / (highest_rsi - lowest_rsi)) * 100
        
        # Calculate %D as 3-period SMA of %K
        if len(rsi_values) >= period + 2:
            k_values = []
            for i in range(-3, 0):
                if i >= -(len(rsi_values)):
                    recent = rsi_values[i - period : i] if i < 0 else rsi_values[-period + i :]
                    if len(recent) == period:
                        highest = np.max(recent)
                        lowest = np.min(recent)
                        if highest != lowest:
                            k = ((recent[-1] - lowest) / (highest - lowest)) * 100
                            k_values.append(k)
            stoch_rsi_d = np.mean(k_values) if k_values else stoch_rsi_k
        else:
            stoch_rsi_d = stoch_rsi_k
        
        return round(float(stoch_rsi_k), 2), round(float(stoch_rsi_d), 2)
    
    @staticmethod
    def calculate_atr(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average True Range using pandas_ta.atr() library.
        
        ✅ USES LIBRARY: pandas_ta.atr() - NO manual calculations
        Only falls back to manual if pandas_ta is not available.
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            logger.debug(f"ATR: Insufficient data (len={min(len(highs), len(lows), len(closes))} < {period + 1})")
            return None
        
        if not PANDAS_TA_AVAILABLE:
            return TechnicalIndicatorCalculator._calculate_atr_manual(highs, lows, closes, period)
        
        try:
            # Create DataFrame with OHLC data for pandas_ta
            df = pd.DataFrame({
                'high': highs,
                'low': lows,
                'close': closes
            })
            
            # ✅ USE LIBRARY: pandas_ta.atr() - vectorized calculation
            atr_series = ta.atr(df['high'], df['low'], df['close'], length=period)
            
            if atr_series is None or atr_series.empty or atr_series.isna().all():
                logger.debug("ATR: pandas_ta returned None or all NaN values")
                return None
            
            atr_value = float(atr_series.iloc[-1])
            
            logger.debug(f"ATR({period}) calculated: {atr_value:.4f}")
            return round(atr_value, 4)
            
        except Exception as e:
            logger.warning(f"ATR calculation error: {e}, falling back to manual")
            return TechnicalIndicatorCalculator._calculate_atr_manual(highs, lows, closes, period)
    
    @staticmethod
    def _calculate_atr_manual(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """
        Fallback manual ATR calculation using numpy.
        
        ⚠️ ONLY USED IF pandas_ta IS NOT AVAILABLE
        Uses numpy for vectorized True Range calculation but prefer pandas_ta library.
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            return None
        
        # REFACTORED: Use numpy for vectorized True Range calculation
        highs_array = np.array(highs[1:])
        lows_array = np.array(lows[1:])
        prev_closes = np.array(closes[:-1])
        
        # Calculate three possible True Ranges
        tr1 = highs_array - lows_array
        tr2 = np.abs(highs_array - prev_closes)
        tr3 = np.abs(lows_array - prev_closes)
        
        # True Range is the maximum of the three
        true_ranges = np.maximum(tr1, np.maximum(tr2, tr3))
        
        if len(true_ranges) < period:
            return None
        
        # ATR is the average of True Ranges over the period
        atr = np.mean(true_ranges[-period:])
        
        return round(float(atr), 4)
    
    @staticmethod
    def calculate_adx(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """
        Calculate Average Directional Index using pandas_ta.adx() library.
        
        ✅ USES LIBRARY: pandas_ta.adx() - NO manual calculations
        Only falls back to manual if pandas_ta is not available.
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            logger.debug(f"ADX: Insufficient data (len={min(len(highs), len(lows), len(closes))} < {period + 1})")
            return None
        
        if not PANDAS_TA_AVAILABLE:
            return TechnicalIndicatorCalculator._calculate_adx_manual(highs, lows, closes, period)
        
        try:
            # Create DataFrame with OHLC data for pandas_ta
            df = pd.DataFrame({
                'high': highs,
                'low': lows,
                'close': closes
            })
            
            # ✅ USE LIBRARY: pandas_ta.adx() - vectorized calculation (includes +DI, -DI, ADX)
            adx_df = ta.adx(df['high'], df['low'], df['close'], length=period)
            
            if adx_df is None or adx_df.empty:
                logger.debug("ADX: pandas_ta returned None or empty DataFrame")
                return None
            
            # Extract ADX column (pandas_ta may use different naming)
            # Try common column names
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
            
        except Exception as e:
            logger.warning(f"ADX calculation error: {e}, falling back to manual")
            return TechnicalIndicatorCalculator._calculate_adx_manual(highs, lows, closes, period)
    
    @staticmethod
    def _calculate_adx_manual(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """
        Fallback manual ADX calculation (simplified approximation).
        
        ⚠️ ONLY USED IF pandas_ta IS NOT AVAILABLE
        This is a simplified approximation based on volatility.
        ADX is complex - strongly prefer using pandas_ta library.
        """
        logger.warning("ADX manual calculation not fully implemented, returning volatility-based approximation")
        
        # Simplified ADX approximation based on price volatility
        if len(closes) < period:
            return None
        
        closes_array = np.array(closes)
        volatility = np.std(closes_array[-period:]) / np.mean(closes_array[-period:]) * 100
        
        # ADX approximation: higher volatility = higher ADX (trend strength)
        adx_approx = min(volatility * 10, 100)  # Cap at 100
        
        return round(float(adx_approx), 2)
    
    @staticmethod
    def calculate_volume_sma(volumes: List[Decimal], period: int = 20) -> Optional[Decimal]:
        """
        Calculate Volume Simple Moving Average using pandas.rolling() library.
        
        ✅ USES LIBRARY: pandas.Series.rolling().mean() - NO manual calculations
        This is always vectorized via pandas, no fallback needed.
        """
        if len(volumes) < period:
            logger.debug(f"Volume SMA: Insufficient data ({len(volumes)} < {period})")
            return None
        
        try:
            # Convert to pandas Series for vectorized calculation
            volumes_float = [float(v) for v in volumes]
            volumes_series = pd.Series(volumes_float)
            
            # ✅ USE LIBRARY: pandas.Series.rolling().mean() - vectorized calculation
            sma = volumes_series.rolling(window=period).mean().iloc[-1]
            
            logger.debug(f"Volume SMA({period}) calculated: {sma:.2f}")
            return Decimal(str(round(sma, 2)))
            
        except Exception as e:
            logger.warning(f"Volume SMA calculation error: {e}, falling back to manual")
            # Fallback to manual calculation
            avg_volume = sum(volumes[-period:]) / period
            return Decimal(str(round(float(avg_volume), 2)))
    
    @staticmethod
    def calculate_vwap(
        prices: List[float], volumes: List[float], period: Optional[int] = None
    ) -> Optional[float]:
        """
        Calculate Volume-Weighted Average Price using pandas DataFrame operations.
        
        ✅ USES LIBRARY: pandas DataFrame vectorized operations - NO manual calculations
        Formula: sum(price * volume) / sum(volume) using pandas vectorized operations.
        """
        if len(prices) < 2 or len(volumes) < 2 or len(prices) != len(volumes):
            logger.debug("VWAP: Insufficient or mismatched data")
            return None
        
        try:
            # Create DataFrame for vectorized calculation
            df = pd.DataFrame({
                'price': prices,
                'volume': volumes
            })
            
            # Slice to period if specified
            if period is not None:
                if len(df) < period:
                    logger.debug(f"VWAP: Insufficient data (have {len(df)}, need {period})")
                    return None
                df = df.iloc[-period:]
            
            # ✅ USE LIBRARY: pandas vectorized operations for VWAP calculation
            # Formula: sum(price * volume) / sum(volume)
            cumulative_pv = (df['price'] * df['volume']).sum()
            cumulative_volume = df['volume'].sum()
            
            if cumulative_volume == 0:
                return None
            
            vwap = cumulative_pv / cumulative_volume
            
            logger.debug(f"VWAP calculated: {vwap:.4f} from {len(df)} periods")
            return round(float(vwap), 4)
            
        except Exception as e:
            logger.warning(f"VWAP calculation error: {e}")
            return None
    
    @staticmethod
    def detect_macd_divergence(
        prices: List[float], macd_histograms: List[float], lookback: int = 5
    ) -> Optional[str]:
        """
        Detect MACD histogram divergence patterns using numpy.
        
        REFACTORED: Uses numpy for efficient array operations
        """
        if len(prices) < lookback * 2 or len(macd_histograms) < lookback * 2:
            return None
        
        # Use numpy for vectorized operations
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
    
    @staticmethod
    def calculate_expectancy(
        winning_trades: int,
        losing_trades: int,
        avg_win_amount: float,
        avg_loss_amount: float,
    ) -> Optional[float]:
        """Calculate Expectancy metric for system consistency."""
        total_trades = winning_trades + losing_trades
        if total_trades == 0:
            return None
        
        win_rate = winning_trades / total_trades
        loss_rate = losing_trades / total_trades
        
        expectancy = (win_rate * avg_win_amount) - (loss_rate * avg_loss_amount)
        return round(expectancy, 4)


class MomentumAnalysisService:
    """Service for momentum analysis and signal generation.
    
    REFACTORED: Uses TechnicalIndicatorCalculator with vectorized libraries (pandas_ta, pandas, numpy)
    """

    def __init__(self):
        self.asset_service: AssetIdentificationService = get_asset_identification_service()
        self.strategies: Dict[str, MomentumStrategy] = {}
        self.analyses: Dict[str, MomentumAnalysis] = {}
        self.indicator_calculator = TechnicalIndicatorCalculator()

        # Initialize default strategies
        self._initialize_default_strategies()

    def _initialize_default_strategies(self):
        """Initialize default momentum strategies using centralized configuration."""
        # Get trading thresholds from centralized config
        trading_config = get_config().trading

        strategies = [
            MomentumStrategy(
                name="Daily Price Momentum",
                description="Daily momentum strategy based on price and volume",
                momentum_type=MomentumType.PRICE_MOMENTUM,
                timeframe=Timeframe.DAILY,
                min_strength=trading_config.min_signal_strength,
                min_confidence=trading_config.min_signal_confidence,
                signal_duration=24,
                rsi_oversold=trading_config.rsi_oversold,
                rsi_overbought=trading_config.rsi_overbought,
                ema_short_period=9,
                ema_long_period=21,
                min_volume_ratio=1.2,
                volume_spike_threshold=2.0,
                max_position_size=trading_config.max_position_size,
                stop_loss_pct=trading_config.stop_loss_pct,
                take_profit_pct=trading_config.take_profit_pct,
            ),
            MomentumStrategy(
                name="Volume Momentum",
                description="Volume-based momentum strategy",
                momentum_type=MomentumType.VOLUME_MOMENTUM,
                timeframe=Timeframe.DAILY,
                min_strength=trading_config.min_signal_strength + 10.0,
                min_confidence=trading_config.min_signal_confidence + 5.0,
                signal_duration=12,
                min_volume_ratio=1.5,
                volume_spike_threshold=2.5,
                max_position_size=trading_config.max_position_size * 0.8,
                stop_loss_pct=trading_config.stop_loss_pct * 0.8,
                take_profit_pct=trading_config.take_profit_pct * 0.8,
            ),
            MomentumStrategy(
                name="Combined Momentum",
                description="Combined price, volume, and volatility momentum",
                momentum_type=MomentumType.COMBINED_MOMENTUM,
                timeframe=Timeframe.DAILY,
                min_strength=trading_config.min_signal_strength + 15.0,
                min_confidence=trading_config.min_signal_confidence + 10.0,
                signal_duration=18,
                rsi_oversold=trading_config.rsi_oversold - 5.0,
                rsi_overbought=trading_config.rsi_overbought + 5.0,
                ema_short_period=12,
                ema_long_period=26,
                min_volume_ratio=1.3,
                volume_spike_threshold=2.0,
                max_position_size=trading_config.max_position_size * 1.2,
                stop_loss_pct=trading_config.stop_loss_pct * 1.2,
                take_profit_pct=trading_config.take_profit_pct * 1.2,
            ),
        ]

        for strategy in strategies:
            self.strategies[strategy.name] = strategy

    async def analyze_asset_momentum(
        self, symbol: str, timeframe: Timeframe = Timeframe.DAILY
    ) -> MomentumAnalysis:
        """Analyze momentum for a specific asset."""
        try:
            price_data = await self._generate_mock_price_data(symbol, timeframe)
            indicators = await self._calculate_technical_indicators(symbol, price_data)
            signals = await self._generate_momentum_signals(symbol, indicators, timeframe)
            overall_momentum = self._calculate_overall_momentum(signals)
            trend_direction = self._determine_trend_direction(indicators)
            risk_level = self._assess_risk_level(indicators, signals)
            volatility_level = self._assess_volatility_level(indicators)

            analysis = MomentumAnalysis(
                symbol=symbol,
                timeframe=timeframe,
                indicators=indicators,
                signals=signals,
                overall_momentum=overall_momentum,
                trend_direction=trend_direction,
                signal_count=len(signals),
                risk_level=risk_level,
                volatility_level=volatility_level,
            )

            self.analyses[f"{symbol}_{timeframe.value}"] = analysis
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing momentum for {symbol}: {e}")
            raise

    async def _generate_mock_price_data(
        self, symbol: str, timeframe: Timeframe
    ) -> Dict[str, List[float]]:
        """Generate mock price data for demonstration."""
        import random

        base_price = 100.0
        prices = [base_price]
        highs = [base_price * 1.02]
        lows = [base_price * 0.98]
        volumes = [Decimal("1000000")]

        for i in range(50):
            change = random.uniform(-0.05, 0.05)
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
            highs.append(new_price * random.uniform(1.0, 1.03))
            lows.append(new_price * random.uniform(0.97, 1.0))
            volumes.append(Decimal(str(random.randint(500000, 2000000))))

        return {"prices": prices, "highs": highs, "lows": lows, "volumes": volumes}

    async def _calculate_technical_indicators(
        self, symbol: str, price_data: Dict[str, List[float]]
    ) -> TechnicalIndicators:
        """Calculate technical indicators using vectorized libraries."""
        prices = price_data["prices"]
        highs = price_data["highs"]
        lows = price_data["lows"]
        volumes = price_data["volumes"]

        # REFACTORED: Use TechnicalIndicatorCalculator (vectorized)
        rsi = self.indicator_calculator.calculate_rsi(prices, 14)
        ema_9 = self.indicator_calculator.calculate_ema(prices, 9)
        ema_21 = self.indicator_calculator.calculate_ema(prices, 21)
        ema_50 = self.indicator_calculator.calculate_ema(prices, 50)
        ema_200 = self.indicator_calculator.calculate_ema(prices, 200)
        macd, macd_signal, macd_histogram = self.indicator_calculator.calculate_macd(prices)
        atr = self.indicator_calculator.calculate_atr(highs, lows, prices, 14)
        adx = self.indicator_calculator.calculate_adx(highs, lows, prices, 14)
        volume_sma_20 = self.indicator_calculator.calculate_volume_sma(volumes, 20)

        # Calculate volatility using numpy (vectorized)
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

    async def _generate_momentum_signals(
        self, symbol: str, indicators: TechnicalIndicators, timeframe: Timeframe
    ) -> List[MomentumSignal]:
        """Generate momentum signals based on technical indicators."""
        signals = []

        if (
            indicators.rsi is not None
            and indicators.ema_9 is not None
            and indicators.ema_21 is not None
        ):
            signal = await self._create_price_momentum_signal(symbol, indicators, timeframe)
            if signal:
                signals.append(signal)

        if indicators.volume_ratio is not None:
            signal = await self._create_volume_momentum_signal(symbol, indicators, timeframe)
            if signal:
                signals.append(signal)

        if len(signals) >= 2:
            signal = await self._create_combined_momentum_signal(
                symbol, indicators, timeframe, signals
            )
            if signal:
                signals.append(signal)

        return signals

    async def _create_price_momentum_signal(
        self, symbol: str, indicators: TechnicalIndicators, timeframe: Timeframe
    ) -> Optional[MomentumSignal]:
        """Create price momentum signal with correct RSI logic."""
        if not all([indicators.rsi, indicators.ema_9, indicators.ema_21]):
            return None

        # CORRECTED: BUY when RSI is oversold (< threshold), SELL when overbought (> threshold)
        # Never generate BUY when RSI > 70 or SELL when RSI < 30
        direction = None
        strength = 0
        confidence = 0

        if indicators.rsi < 45:  # Oversold - BUY signal
            direction = "BUY"
            strength = 75.0
            confidence = 80.0
        elif indicators.rsi > 55:  # Overbought - SELL signal
            direction = "SELL"
            strength = 70.0
            confidence = 75.0
        else:
            # Neutral zone - no signal to avoid confusion
            return None

        current_price = Decimal("100.0")
        price_change = Decimal("2.5")
        price_change_pct = 2.5
        volume = Decimal("1500000")
        volume_change = Decimal("200000")
        volume_change_pct = 15.0

        return MomentumSignal(
            symbol=symbol,
            signal_type=MomentumType.PRICE_MOMENTUM,
            timeframe=timeframe,
            strength=strength,
            direction=direction,
            confidence=confidence,
            rsi=indicators.rsi,
            ema_short=indicators.ema_9,
            ema_long=indicators.ema_21,
            macd=indicators.macd,
            macd_signal=indicators.macd_signal,
            macd_histogram=indicators.macd_histogram,
            current_price=current_price,
            price_change=price_change,
            price_change_pct=price_change_pct,
            volume=volume,
            volume_change=volume_change,
            volume_change_pct=volume_change_pct,
            atr=Decimal(str(indicators.atr)) if indicators.atr else None,
            volatility=indicators.volatility,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

    async def _create_volume_momentum_signal(
        self, symbol: str, indicators: TechnicalIndicators, timeframe: Timeframe
    ) -> Optional[MomentumSignal]:
        """Create volume momentum signal."""
        if indicators.volume_ratio is None:
            return None

        direction = "BUY"
        strength = 80.0
        confidence = 85.0

        current_price = Decimal("100.0")
        price_change = Decimal("1.5")
        price_change_pct = 1.5
        volume = Decimal("2000000")
        volume_change = Decimal("500000")
        volume_change_pct = 25.0

        return MomentumSignal(
            symbol=symbol,
            signal_type=MomentumType.VOLUME_MOMENTUM,
            timeframe=timeframe,
            strength=strength,
            direction=direction,
            confidence=confidence,
            current_price=current_price,
            price_change=price_change,
            price_change_pct=price_change_pct,
            volume=volume,
            volume_change=volume_change,
            volume_change_pct=volume_change_pct,
            expires_at=datetime.utcnow() + timedelta(hours=12),
        )

    async def _create_combined_momentum_signal(
        self,
        symbol: str,
        indicators: TechnicalIndicators,
        timeframe: Timeframe,
        existing_signals: List[MomentumSignal],
    ) -> Optional[MomentumSignal]:
        """Create combined momentum signal."""
        if len(existing_signals) < 2:
            return None

        total_strength = sum(signal.strength for signal in existing_signals)
        avg_strength = total_strength / len(existing_signals)
        total_confidence = sum(signal.confidence for signal in existing_signals)
        avg_confidence = total_confidence / len(existing_signals)

        buy_signals = [s for s in existing_signals if s.direction == "BUY"]
        sell_signals = [s for s in existing_signals if s.direction == "SELL"]

        direction = "BUY" if len(buy_signals) > len(sell_signals) else "SELL"

        if avg_strength < 70 or avg_confidence < 75:
            return None

        current_price = Decimal("100.0")
        price_change = Decimal("3.0")
        price_change_pct = 3.0
        volume = Decimal("1800000")
        volume_change = Decimal("300000")
        volume_change_pct = 20.0

        return MomentumSignal(
            symbol=symbol,
            signal_type=MomentumType.COMBINED_MOMENTUM,
            timeframe=timeframe,
            strength=avg_strength,
            direction=direction,
            confidence=avg_confidence,
            rsi=indicators.rsi,
            ema_short=indicators.ema_9,
            ema_long=indicators.ema_21,
            macd=indicators.macd,
            macd_signal=indicators.macd_signal,
            macd_histogram=indicators.macd_histogram,
            current_price=current_price,
            price_change=price_change,
            price_change_pct=price_change_pct,
            volume=volume,
            volume_change=volume_change,
            volume_change_pct=volume_change_pct,
            atr=Decimal(str(indicators.atr)) if indicators.atr else None,
            volatility=indicators.volatility,
            expires_at=datetime.utcnow() + timedelta(hours=18),
        )

    def _calculate_overall_momentum(self, signals: List[MomentumSignal]) -> float:
        """Calculate overall momentum score."""
        if not signals:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for signal in signals:
            weight = (signal.strength + signal.confidence) / 2
            total_score += signal.momentum_score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def _determine_trend_direction(self, indicators: TechnicalIndicators) -> str:
        """Determine overall trend direction."""
        if not indicators.ema_trend:
            return "NEUTRAL"
        return indicators.ema_trend

    def _assess_risk_level(
        self, indicators: TechnicalIndicators, signals: List[MomentumSignal]
    ) -> str:
        """Assess risk level based on indicators and signals."""
        risk_score = 0

        if indicators.volatility:
            if indicators.volatility > 5:
                risk_score += 3
            elif indicators.volatility > 3:
                risk_score += 2
            else:
                risk_score += 1

        if signals:
            avg_strength = sum(s.strength for s in signals) / len(signals)
            if avg_strength > 80:
                risk_score += 2
            elif avg_strength > 60:
                risk_score += 1

        if indicators.atr:
            if indicators.atr > 3:
                risk_score += 2
            elif indicators.atr > 1.5:
                risk_score += 1

        if risk_score >= 5:
            return "HIGH"
        elif risk_score >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def _assess_volatility_level(self, indicators: TechnicalIndicators) -> str:
        """Assess volatility level."""
        if not indicators.volatility:
            return "MEDIUM"

        if indicators.volatility > 5:
            return "HIGH"
        elif indicators.volatility > 2:
            return "MEDIUM"
        else:
            return "LOW"

    async def get_momentum_signals(
        self, filter_criteria: Optional[MomentumFilter] = None
    ) -> List[MomentumSignal]:
        """Get momentum signals based on filter criteria."""
        all_signals = []

        for analysis in self.analyses.values():
            signals = analysis.get_active_signals()
            if filter_criteria:
                signals = [s for s in signals if filter_criteria.matches(s)]
            all_signals.extend(signals)

        all_signals.sort(key=lambda x: x.momentum_score, reverse=True)
        return all_signals

    async def get_strategy_signals(self, strategy_name: str) -> List[MomentumSignal]:
        """Get signals for a specific strategy."""
        if strategy_name not in self.strategies:
            return []

        strategy = self.strategies[strategy_name]
        filter_criteria = MomentumFilter(
            min_strength=strategy.min_strength,
            min_confidence=strategy.min_confidence,
            active_only=True,
        )

        signals = await self.get_momentum_signals(filter_criteria)
        strategy_signals = [
            s for s in signals if s.signal_type == strategy.momentum_type
        ]

        return strategy_signals

    async def get_top_momentum_assets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top momentum assets."""
        signals = await self.get_momentum_signals()

        asset_signals = {}
        for signal in signals:
            if (
                signal.symbol not in asset_signals
                or signal.momentum_score > asset_signals[signal.symbol].momentum_score
            ):
                asset_signals[signal.symbol] = signal

        sorted_assets = sorted(
            asset_signals.values(), key=lambda x: x.momentum_score, reverse=True
        )

        top_assets = []
        for signal in sorted_assets[:limit]:
            top_assets.append(
                {
                    "symbol": signal.symbol,
                    "momentum_score": signal.momentum_score,
                    "strength": signal.strength,
                    "confidence": signal.confidence,
                    "direction": signal.direction,
                    "signal_type": signal.signal_type.value,
                    "timestamp": signal.timestamp,
                }
            )

        return top_assets

    async def create_strategy(self, strategy: MomentumStrategy) -> MomentumStrategy:
        """Create a new momentum strategy."""
        self.strategies[strategy.name] = strategy
        return strategy

    async def get_strategy(self, strategy_name: str) -> Optional[MomentumStrategy]:
        """Get a momentum strategy by name."""
        return self.strategies.get(strategy_name)

    async def update_strategy(
        self, strategy_name: str, updated_fields: Dict[str, Any]
    ) -> Optional[MomentumStrategy]:
        """Update a momentum strategy."""
        if strategy_name not in self.strategies:
            return None

        strategy = self.strategies[strategy_name]
        for field, value in updated_fields.items():
            if hasattr(strategy, field):
                setattr(strategy, field, value)
        strategy.updated_at = datetime.utcnow()
        return strategy

    async def delete_strategy(self, strategy_name: str) -> bool:
        """Delete a momentum strategy."""
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            return True
        return False

    async def get_analyses(self) -> List[MomentumAnalysis]:
        """Get all momentum analyses."""
        return list(self.analyses.values())

    async def get_analysis(self, analysis_id: str) -> Optional[MomentumAnalysis]:
        """Get a momentum analysis by ID."""
        return self.analyses.get(analysis_id)

    async def delete_analysis(self, analysis_id: str) -> bool:
        """Delete a momentum analysis."""
        if analysis_id in self.analyses:
            del self.analyses[analysis_id]
            return True
        return False


# Global service instance
_momentum_service: Optional[MomentumAnalysisService] = None


def get_momentum_analysis_service() -> MomentumAnalysisService:
    """Get global momentum analysis service instance."""
    global _momentum_service
    if _momentum_service is None:
        _momentum_service = MomentumAnalysisService()
    return _momentum_service
