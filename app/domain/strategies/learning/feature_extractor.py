"""
FeatureExtractor - Extrae features completas para learning engines.
"""

import logging
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Extrae y normaliza features completas para learning engines.

    Features extraídas:
    - Indicadores técnicos: RSI, EMA fast/slow, Momentum, Volume, ATR
    - Resultados de filtros: Todos los filtros modulares
    - Contexto de mercado: Tipo, volatilidad, tendencia
    - Metadata: Temporal, histórico de trades
    """

    def __init__(self):
        """Inicializar extractor de features."""
        self.feature_names = []

    def extract_complete_features(
        self,
        indicators: dict[str, Any],
        filter_results: dict[str, dict],
        market_context: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Extraer todas las features disponibles.

        Args:
            indicators: Indicadores técnicos calculados
            filter_results: Resultados de evaluación de filtros
            market_context: Contexto de mercado detectado
            metadata: Metadata adicional (timestamp, symbol, trade_history, etc.)

        Returns:
            {
                'feature_vector': List[float],  # Vector normalizado
                'feature_names': List[str],     # Nombres de features
                'raw_features': Dict            # Features sin normalizar
            }
        """
        raw_features = {}
        feature_vector = []
        feature_names = []

        # ============================================================
        # 1. INDICADORES TÉCNICOS
        # ============================================================

        # RSI
        rsi = indicators.get("rsi", 50.0)
        raw_features["rsi"] = rsi
        feature_vector.append(self._normalize_rsi(rsi))
        feature_names.append("rsi_normalized")

        # EMAs
        ema_fast = indicators.get("ema_fast", 0.0)
        ema_slow = indicators.get("ema_slow", 0.0)
        current_price = indicators.get("price", 0.0)

        raw_features["ema_fast"] = ema_fast
        raw_features["ema_slow"] = ema_slow
        raw_features["price"] = current_price

        if current_price > 0:
            feature_vector.append(ema_fast / current_price)  # Normalizado
            feature_names.append("ema_fast_ratio")
            feature_vector.append(ema_slow / current_price)
            feature_names.append("ema_slow_ratio")
            feature_vector.append((ema_fast - ema_slow) / ema_slow if ema_slow > 0 else 0.0)
            feature_names.append("ema_distance_pct")
            feature_vector.append(1.0 if current_price > ema_fast else 0.0)
            feature_names.append("price_above_ema_fast")
        else:
            feature_vector.extend([0.0, 0.0, 0.0, 0.0])
            feature_names.extend(
                ["ema_fast_ratio", "ema_slow_ratio", "ema_distance_pct", "price_above_ema_fast"]
            )

        # Momentum / ROC
        momentum_roc = indicators.get("momentum_roc", 0.0)
        raw_features["momentum_roc"] = momentum_roc
        feature_vector.append(self._normalize_momentum(momentum_roc))
        feature_names.append("momentum_roc_normalized")

        # Volume
        volume_ratio = indicators.get("volume_ratio", 1.0)
        raw_features["volume_ratio"] = volume_ratio
        feature_vector.append(self._normalize_volume_ratio(volume_ratio))
        feature_names.append("volume_ratio_normalized")

        current_volume = indicators.get("volume", 0.0)
        avg_volume = indicators.get("avg_volume", 0.0)
        raw_features["volume"] = current_volume
        raw_features["avg_volume"] = avg_volume

        # ATR
        atr = indicators.get("atr", 0.0)
        atr_relative = indicators.get("relative_atr", 0.0)
        atr_percentile = indicators.get("atr_percentile", 50.0)

        raw_features["atr"] = atr
        raw_features["relative_atr"] = atr_relative
        raw_features["atr_percentile"] = atr_percentile

        if current_price > 0:
            feature_vector.append(atr / current_price if atr > 0 else 0.0)  # ATR relativo
            feature_names.append("atr_relative")
        else:
            feature_vector.append(0.0)
            feature_names.append("atr_relative")

        feature_vector.append(atr_percentile / 100.0)  # Normalizar 0-1
        feature_names.append("atr_percentile_normalized")

        # StochRSI
        stoch_rsi_k = indicators.get("stoch_rsi_k", 50.0)
        stoch_rsi_d = indicators.get("stoch_rsi_d", 50.0)

        raw_features["stoch_rsi_k"] = stoch_rsi_k
        raw_features["stoch_rsi_d"] = stoch_rsi_d

        feature_vector.append(stoch_rsi_k / 100.0)  # Normalizar 0-1
        feature_names.append("stoch_rsi_k_normalized")
        feature_vector.append(stoch_rsi_d / 100.0)
        feature_names.append("stoch_rsi_d_normalized")
        feature_vector.append(1.0 if stoch_rsi_k > stoch_rsi_d else 0.0)
        feature_names.append("stoch_rsi_k_above_d")

        # ============================================================
        # 1.5 INDICADORES TÉCNICOS ADICIONALES (Mejora de Features)
        # ============================================================

        # MACD
        macd = indicators.get("macd", 0.0)
        macd_signal = indicators.get("macd_signal", 0.0)
        macd_histogram = indicators.get("macd_histogram", 0.0)

        raw_features["macd"] = macd
        raw_features["macd_signal"] = macd_signal
        raw_features["macd_histogram"] = macd_histogram

        # Normalizar MACD usando sigmoid
        feature_vector.append(self._normalize_momentum(macd * 10))  # Escalar para mejor rango
        feature_names.append("macd_normalized")
        feature_vector.append(self._normalize_momentum(macd_signal * 10))
        feature_names.append("macd_signal_normalized")
        feature_vector.append(self._normalize_momentum(macd_histogram * 100))
        feature_names.append("macd_histogram_normalized")
        feature_vector.append(1.0 if macd > macd_signal else 0.0)  # MACD crossover
        feature_names.append("macd_above_signal")

        # Bollinger Bands
        bb_upper = indicators.get("bb_upper", current_price)
        bb_middle = indicators.get("bb_middle", current_price)
        bb_lower = indicators.get("bb_lower", current_price)
        bb_width = indicators.get("bb_width", 0.0)
        bb_position = indicators.get("bb_position", 0.5)  # 0=lower, 1=upper

        raw_features["bb_upper"] = bb_upper
        raw_features["bb_middle"] = bb_middle
        raw_features["bb_lower"] = bb_lower
        raw_features["bb_width"] = bb_width
        raw_features["bb_position"] = bb_position

        feature_vector.append(bb_position)  # Ya está normalizado 0-1
        feature_names.append("bb_position")
        feature_vector.append(min(1.0, bb_width * 10))  # Normalizar width
        feature_names.append("bb_width_normalized")
        feature_vector.append(1.0 if current_price > bb_middle else 0.0)
        feature_names.append("price_above_bb_middle")
        # Squeeze detection (low volatility)
        feature_vector.append(1.0 if bb_width < 0.02 else 0.0)
        feature_names.append("bb_squeeze")

        # ADX (Average Directional Index) - Trend Strength
        adx = indicators.get("adx", 25.0)
        plus_di = indicators.get("plus_di", 25.0)
        minus_di = indicators.get("minus_di", 25.0)

        raw_features["adx"] = adx
        raw_features["plus_di"] = plus_di
        raw_features["minus_di"] = minus_di

        feature_vector.append(adx / 100.0)  # Normalizar 0-1
        feature_names.append("adx_normalized")
        feature_vector.append(1.0 if adx > 25 else 0.0)  # Strong trend
        feature_names.append("strong_trend")
        feature_vector.append(1.0 if plus_di > minus_di else 0.0)  # Bullish direction
        feature_names.append("bullish_direction")
        feature_vector.append(abs(plus_di - minus_di) / 100.0)  # DI difference
        feature_names.append("di_difference_normalized")

        # CCI (Commodity Channel Index)
        cci = indicators.get("cci", 0.0)
        raw_features["cci"] = cci

        # Normalizar CCI (típicamente -200 a 200)
        feature_vector.append(max(-1.0, min(1.0, cci / 200.0)))
        feature_names.append("cci_normalized")
        feature_vector.append(1.0 if cci > 100 else 0.0)  # Overbought
        feature_names.append("cci_overbought")
        feature_vector.append(1.0 if cci < -100 else 0.0)  # Oversold
        feature_names.append("cci_oversold")

        # Williams %R
        williams_r = indicators.get("williams_r", -50.0)
        raw_features["williams_r"] = williams_r

        # Williams %R va de -100 a 0, normalizar a 0-1
        feature_vector.append((williams_r + 100) / 100.0)
        feature_names.append("williams_r_normalized")
        feature_vector.append(1.0 if williams_r > -20 else 0.0)  # Overbought
        feature_names.append("williams_r_overbought")
        feature_vector.append(1.0 if williams_r < -80 else 0.0)  # Oversold
        feature_names.append("williams_r_oversold")

        # OBV (On-Balance Volume) - relative
        obv = indicators.get("obv", 0.0)
        obv_ema = indicators.get("obv_ema", obv)
        obv_trend = indicators.get("obv_trend", 0.0)  # OBV price divergence

        raw_features["obv"] = obv
        raw_features["obv_ema"] = obv_ema
        raw_features["obv_trend"] = obv_trend

        # OBV trend direction (comparado con su EMA)
        if obv_ema != 0:
            feature_vector.append(min(1.0, max(-1.0, (obv - obv_ema) / abs(obv_ema) * 10)))
        else:
            feature_vector.append(0.0)
        feature_names.append("obv_relative")
        feature_vector.append(self._normalize_momentum(obv_trend))
        feature_names.append("obv_trend_normalized")

        # Multi-period Rate of Change (ROC)
        roc_5 = indicators.get("roc_5", 0.0)  # 5-period ROC
        roc_10 = indicators.get("roc_10", 0.0)  # 10-period ROC
        roc_20 = indicators.get("roc_20", 0.0)  # 20-period ROC

        raw_features["roc_5"] = roc_5
        raw_features["roc_10"] = roc_10
        raw_features["roc_20"] = roc_20

        feature_vector.append(self._normalize_momentum(roc_5 * 10))
        feature_names.append("roc_5_normalized")
        feature_vector.append(self._normalize_momentum(roc_10 * 10))
        feature_names.append("roc_10_normalized")
        feature_vector.append(self._normalize_momentum(roc_20 * 10))
        feature_names.append("roc_20_normalized")
        # ROC acceleration (cambio en velocidad)
        roc_acceleration = roc_5 - roc_10 if roc_10 != 0 else 0.0
        feature_vector.append(self._normalize_momentum(roc_acceleration * 100))
        feature_names.append("roc_acceleration")

        # Price Distance from High/Low (period)
        period_high = indicators.get("period_high", current_price)
        period_low = indicators.get("period_low", current_price)

        raw_features["period_high"] = period_high
        raw_features["period_low"] = period_low

        if period_high > period_low:
            price_position_in_range = (current_price - period_low) / (period_high - period_low)
        else:
            price_position_in_range = 0.5

        feature_vector.append(price_position_in_range)
        feature_names.append("price_position_in_range")
        # Distance from high/low as percentage
        if current_price > 0:
            feature_vector.append(min(1.0, abs(current_price - period_high) / current_price * 10))
            feature_names.append("distance_from_high_normalized")
            feature_vector.append(min(1.0, abs(current_price - period_low) / current_price * 10))
            feature_names.append("distance_from_low_normalized")
        else:
            feature_vector.extend([0.0, 0.0])
            feature_names.extend(["distance_from_high_normalized", "distance_from_low_normalized"])

        # ============================================================
        # 2. RESULTADOS DE FILTROS (TODOS)
        # ============================================================

        filter_names = [
            "ema_filter",
            "rsi_filter",
            "stoch_rsi_filter",
            "momentum_filter",
            "volume_filter",
            "atr_filter",
        ]

        for filter_name in filter_names:
            filter_result = filter_results.get(filter_name, {})
            passed = 1.0 if filter_result.get("passed", False) else 0.0
            confidence = filter_result.get("confidence", 0.5)

            raw_features[f"{filter_name}_passed"] = passed
            raw_features[f"{filter_name}_confidence"] = confidence

            feature_vector.append(passed)
            feature_names.append(f"{filter_name}_passed")
            feature_vector.append(confidence)
            feature_names.append(f"{filter_name}_confidence")

        # ============================================================
        # 3. CONTEXTO DE MERCADO
        # ============================================================

        market_type = market_context.get("type", "unknown")
        trend_strength = market_context.get("trend_strength", 0.0)
        volatility_regime = market_context.get("volatility_regime", "normal")
        volatility_percentile = market_context.get("volatility_percentile", 50.0)
        in_range = market_context.get("in_range", False)

        raw_features["market_type"] = market_type
        raw_features["trend_strength"] = trend_strength
        raw_features["volatility_regime"] = volatility_regime
        raw_features["volatility_percentile"] = volatility_percentile
        raw_features["in_range"] = in_range

        # Codificar tipo de mercado (one-hot encoding simplificado)
        market_type_encoding = {
            "trend_up": [1.0, 0.0, 0.0, 0.0, 0.0],
            "trend_down": [0.0, 1.0, 0.0, 0.0, 0.0],
            "range": [0.0, 0.0, 1.0, 0.0, 0.0],
            "high_vol": [0.0, 0.0, 0.0, 1.0, 0.0],
            "low_vol": [0.0, 0.0, 0.0, 0.0, 1.0],
        }
        market_encoded = market_type_encoding.get(market_type, [0.0, 0.0, 0.0, 0.0, 0.0])
        feature_vector.extend(market_encoded)
        feature_names.extend(
            [
                "market_trend_up",
                "market_trend_down",
                "market_range",
                "market_high_vol",
                "market_low_vol",
            ]
        )

        feature_vector.append(trend_strength)
        feature_names.append("trend_strength")

        # Codificar régimen de volatilidad
        vol_encoding = {"high": [1.0, 0.0, 0.0], "normal": [0.0, 1.0, 0.0], "low": [0.0, 0.0, 1.0]}
        vol_encoded = vol_encoding.get(volatility_regime, [0.0, 1.0, 0.0])
        feature_vector.extend(vol_encoded)
        feature_names.extend(["volatility_high", "volatility_normal", "volatility_low"])

        feature_vector.append(volatility_percentile / 100.0)
        feature_names.append("volatility_percentile_normalized")

        feature_vector.append(1.0 if in_range else 0.0)
        feature_names.append("in_range")

        # ============================================================
        # 4. FEATURES TEMPORALES
        # ============================================================

        if metadata and "timestamp" in metadata:
            timestamp = metadata["timestamp"]
            if isinstance(timestamp, (datetime, pd.Timestamp)):
                # Día de la semana (0=Monday, 6=Sunday)
                feature_vector.append(timestamp.weekday() / 6.0)
                feature_names.append("day_of_week_normalized")

                # Mes del año (0-11)
                feature_vector.append(timestamp.month / 12.0)
                feature_names.append("month_normalized")

                # Hora del día (si está disponible)
                feature_vector.append(timestamp.hour / 23.0 if hasattr(timestamp, "hour") else 0.5)
                feature_names.append("hour_normalized")

        # ============================================================
        # 5. HISTÓRICO DE TRADES (últimos N trades)
        # ============================================================

        if metadata and "recent_trades" in metadata:
            recent_trades = metadata["recent_trades"]

            # Últimos 5 trades
            for i in range(5):
                if i < len(recent_trades):
                    trade = recent_trades[i]
                    pnl = trade.get("pnl", 0.0)
                    success = 1.0 if pnl > 0 else 0.0

                    feature_vector.append(success)
                    feature_names.append(f"recent_trade_{i}_success")
                    feature_vector.append(self._normalize_pnl(pnl))
                    feature_names.append(f"recent_trade_{i}_pnl_normalized")
                else:
                    feature_vector.extend([0.0, 0.0])
                    feature_names.extend(
                        [f"recent_trade_{i}_success", f"recent_trade_{i}_pnl_normalized"]
                    )
        else:
            # Sin trades recientes
            for i in range(5):
                feature_vector.extend([0.0, 0.0])
                feature_names.extend(
                    [f"recent_trade_{i}_success", f"recent_trade_{i}_pnl_normalized"]
                )

        # Win rate reciente
        if metadata and "recent_win_rate" in metadata:
            feature_vector.append(metadata["recent_win_rate"])
            feature_names.append("recent_win_rate")
        else:
            feature_vector.append(0.5)  # Default
            feature_names.append("recent_win_rate")

        self.feature_names = feature_names

        return {
            "feature_vector": feature_vector,
            "feature_names": feature_names,
            "raw_features": raw_features,
        }

    def _normalize_rsi(self, rsi: float) -> float:
        """Normalizar RSI a rango 0-1."""
        # RSI típico: 0-100, normalizar a 0-1
        return max(0.0, min(1.0, rsi / 100.0))

    def _normalize_momentum(self, momentum: float) -> float:
        """
        Normalizar momentum a rango 0-1 usando sigmoid.

        Args:
            momentum: Valor de momentum (típicamente -0.1 a 0.1, pero puede variar)

        Returns:
            Valor normalizado entre 0 y 1

        Nota: Clampea el exponente para evitar overflow numérico.
        """
        # Momentum típico aproximadamente -0.1 a 0.1
        # Normalizar a 0-1 usando sigmoid
        # Clampear exponente para evitar overflow (exp(x) para x > 709 causa overflow)
        exponent = -momentum * 100
        # Limitar exponente a rango seguro [-700, 700] para evitar overflow/underflow
        exponent_clamped = np.clip(exponent, -700, 700)

        try:
            sigmoid = 1.0 / (1.0 + np.exp(exponent_clamped))
            # Asegurar que el resultado esté en [0, 1]
            return float(np.clip(sigmoid, 0.0, 1.0))
        except (OverflowError, FloatingPointError):
            # Fallback si aún hay problemas: usar función más simple
            logger.debug(
                f"Momentum overflow, usando normalización alternativa para momentum={momentum}"
            )
            # Normalización lineal con clamping
            normalized = (momentum + 0.5) / 1.0  # Asumiendo rango -0.5 a 0.5
            return float(np.clip(normalized, 0.0, 1.0))

    def _normalize_volume_ratio(self, volume_ratio: float) -> float:
        """
        Normalizar volume ratio.

        Args:
            volume_ratio: Ratio de volumen (típicamente 0.5 a 3.0, pero puede ser mayor)

        Returns:
            Valor normalizado entre 0 y 1

        Nota: Maneja overflow en log() para valores muy grandes.
        """
        # Volume ratio típico: 0.5 a 3.0
        # Normalizar usando log
        if volume_ratio <= 0:
            return 0.0

        try:
            # Clampear volume_ratio para evitar overflow en log
            # log(1e308) ≈ 710, lo cual está cerca del límite
            volume_clamped = min(volume_ratio, 1e100)  # Límite seguro para log
            normalized = min(1.0, np.log(1 + volume_clamped) / np.log(4))
            return float(np.clip(normalized, 0.0, 1.0))
        except (OverflowError, FloatingPointError):
            # Fallback: normalización lineal
            logger.debug(
                f"Volume ratio overflow, usando normalización alternativa para ratio={volume_ratio}"
            )
            # Asumir que ratios > 10 son extremos, normalizar linealmente
            return float(np.clip(volume_ratio / 10.0, 0.0, 1.0))

    def _normalize_pnl(self, pnl: float) -> float:
        """
        Normalizar P&L a rango -1 a 1 usando tanh.

        Args:
            pnl: Profit and Loss (puede variar mucho)

        Returns:
            Valor normalizado entre -1 y 1

        Nota: tanh es más estable que exp, pero aún se protege contra valores extremos.
        """
        # P&L puede variar mucho, usar tanh para normalizar
        # Asumir P&L típico en rango -1000 a 1000
        # Clampear entrada para evitar problemas con valores extremos
        # tanh es estable pero clampear por seguridad
        pnl_normalized = pnl / 1000.0
        # Clampear a rango razonable para tanh (aunque tanh maneja bien valores grandes)
        pnl_clamped = np.clip(pnl_normalized, -50, 50)  # tanh(50) ≈ 1.0, tanh(-50) ≈ -1.0
        return float(np.clip(np.tanh(pnl_clamped), -1.0, 1.0))

    def extract_sequence_features(
        self,
        historical_data: list[dict[str, Any]],
        sequence_length: int,
        feature_names: Optional[list[str]] = None,
    ) -> np.ndarray:
        """
        Extraer secuencias de features para Deep Learning.

        Args:
            historical_data: Lista de dicts con features por timestep
            sequence_length: Longitud de la secuencia
            feature_names: Nombres de features a usar (si None, usa todas)

        Returns:
            np.array shape (sequence_length, n_features)
        """
        if len(historical_data) < sequence_length:
            # Rellenar con ceros al principio
            padding: list[dict[str, Any]] = [{}] * (sequence_length - len(historical_data))
            historical_data = padding + historical_data

        # Tomar últimos sequence_length elementos
        sequence_data = historical_data[-sequence_length:]

        # Extraer features para cada timestep
        feature_vectors = []
        for data_point in sequence_data:
            features = self.extract_complete_features(
                indicators=data_point.get("indicators", {}),
                filter_results=data_point.get("filter_results", {}),
                market_context=data_point.get("market_context", {}),
                metadata=data_point.get("metadata", {}),
            )
            feature_vectors.append(features["feature_vector"])

        return np.array(feature_vectors, dtype=np.float32)
