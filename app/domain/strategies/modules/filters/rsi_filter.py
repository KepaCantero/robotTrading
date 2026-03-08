"""
RSIFilter - Filtro de momentum relativo usando RSI.

Standard RSI Strategy (CORRECTED):
- BUY when RSI crosses ABOVE buy_threshold (oversold reversal confirmation, typically > 30)
- SELL when RSI crosses BELOW sell_threshold (overbought reversal confirmation, typically < 70)

CORRECTED LOGIC:
- Track previous RSI value
- BUY signal: previous_rsi <= buy_threshold AND current_rsi > buy_threshold (crossover above)
- SELL signal: previous_rsi >= sell_threshold AND current_rsi < sell_threshold (crossover below)
- FALLBACK (no history): use stricter threshold (buy_threshold - 2) to be more conservative

Configuration:
This filter now uses centralized configuration from config/indicators.yaml:
- RSI thresholds (30, 70, 45, 55) are loaded from config
- Adaptive thresholds for market regimes are loaded from config
- Period settings are loaded from config
"""

import logging
from typing import Dict, Optional

from ..base_filter import BaseFilter

# Try to import strategy config loader from centralized config
try:
    from app.shared.config.centralized_config import get_config

    HAS_CONFIG_LOADER = True
except ImportError:
    get_config = None  # type: ignore
    HAS_CONFIG_LOADER = False

logger = logging.getLogger(__name__)


class RSIFilter(BaseFilter):
    """
    Filtro de momentum usando Relative Strength Index (RSI).

    Estrategia RSI Estándar (CORREGIDA):
    - BUY cuando RSI cruza POR ENCIMA de buy_threshold (confirmación de reversión desde sobreventa, típicamente > 30)
    - SELL cuando RSI cruza POR DEBAJO de sell_threshold (confirmación de reversión desde sobrecompra, típicamente < 70)

    LÓGICA CORREGIDA:
    - Rastrea valor RSI previo
    - Señal BUY: previous_rsi <= buy_threshold AND current_rsi > buy_threshold (cruce hacia arriba)
    - Señal SELL: previous_rsi >= sell_threshold AND current_rsi < sell_threshold (cruce hacia abajo)
    - FALLBACK (sin historial): usa umbral más estricto (buy_threshold - 2) para ser más conservador
    """

    # Class-level storage for tracking RSI history per symbol
    _rsi_history: Dict[str, float] = {}

    def __init__(
        self, config: Dict = None, preset: str = "balanced", tier: str = None, use_yaml: bool = True
    ):
        """Inicializar filtro RSI."""
        super().__init__("rsi_filter", config, preset, tier, use_yaml)

        # Default values (can be overridden by YAML config)
        self.period = 14
        default_extreme_low = 30
        default_extreme_high = 70

        # Get settings from YAML or config
        settings = self.config.get("settings", self.config)
        self.period = settings.get("period", self.period)
        self.adaptive = settings.get("adaptive", True)
        self.use_crossover = settings.get(
            "use_crossover", True
        )  # Enable crossover logic by default
        self.fallback_offset = settings.get(
            "fallback_offset", 2
        )  # Stricter threshold when no history

        # Thresholds adaptativos por contexto (desde YAML config)
        # Using NEW correct format: buy_threshold and sell_threshold (single values)
        self.adaptive_thresholds = self.config.get("adaptive_thresholds", {})

        if not self.adaptive_thresholds:
            # Fallback a defaults si no están en YAML - CORRECTED LOGIC with crossover
            # FIX: Lowered thresholds for better signal generation
            # In bull markets, RSI rarely drops below 30, so use higher buy_threshold
            # to generate more BUY signals and higher sell_threshold to reduce SELL signals
            self.adaptive_thresholds = {
                "balanced": {"buy_threshold": 35, "sell_threshold": 70},  # Lowered from 40/75
                "volatile": {"buy_threshold": 30, "sell_threshold": 75},  # Lowered from 35/80
                "trending": {"buy_threshold": 40, "sell_threshold": 75},  # Lowered from 45/75
                "trend_up": {
                    "buy_threshold": 40,
                    "sell_threshold": 80,
                },  # Lowered from 50/80 - too restrictive!
                "trend_down": {"buy_threshold": 25, "sell_threshold": 55},  # Lowered from 30/60
                "range": {"buy_threshold": 30, "sell_threshold": 70},  # Lowered from 35/65
                "low_vol": {"buy_threshold": 35, "sell_threshold": 70},  # Lowered from 40/70
                "high_vol": {"buy_threshold": 30, "sell_threshold": 70},  # Lowered from 35/75
                "no_trend": {"buy_threshold": 35, "sell_threshold": 70},  # Lowered from 40/75
                "unknown": {"buy_threshold": 35, "sell_threshold": 70},  # Lowered from 40/75
            }

    def _get_previous_rsi(self, symbol: str) -> Optional[float]:
        """
        Get previous RSI value for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Previous RSI value or None if not available
        """
        return self._rsi_history.get(symbol)

    def _update_rsi_history(self, symbol: str, rsi: float) -> None:
        """
        Update RSI history for a symbol.

        Args:
            symbol: Trading symbol
            rsi: Current RSI value
        """
        self._rsi_history[symbol] = rsi

    @classmethod
    def clear_rsi_history(cls, symbol: Optional[str] = None) -> None:
        """
        Clear RSI history. Useful for testing or resetting state.

        Args:
            symbol: If provided, only clear history for this symbol.
                    If None, clear all history.
        """
        if symbol:
            cls._rsi_history.pop(symbol, None)
        else:
            cls._rsi_history.clear()

    @classmethod
    def get_rsi_history(cls) -> Dict[str, float]:
        """
        Get a copy of the current RSI history. Useful for debugging/testing.

        Returns:
            Dictionary mapping symbols to their last RSI value
        """
        return cls._rsi_history.copy()

    def _get_thresholds_for_context(self, market_context: Dict) -> Dict:
        """Obtener thresholds según el contexto de mercado."""
        market_type = market_context.get("type", "unknown")

        # Intentar obtener thresholds específicos para este contexto
        if market_type in self.adaptive_thresholds:
            return self.adaptive_thresholds[market_type]

        # Fallback a preset genérico
        return self.adaptive_thresholds.get("unknown", {"buy_threshold": 30, "sell_threshold": 70})

    def _apply_filter_logic(self, indicators: Dict, market_context: Dict, signal_type: str) -> Dict:
        """
        Aplicar lógica del filtro RSI con CONFIRMACIÓN de cruce (crossover).

        CORRECTED LOGIC:
        - BUY: Requires RSI to cross ABOVE buy_threshold (confirms reversal)
        - SELL: Requires RSI to cross BELOW sell_threshold (confirms reversal)
        - FALLBACK: If no history, use stricter threshold (buy_threshold - fallback_offset)
        """
        rsi = indicators.get("rsi")
        symbol = indicators.get("symbol", "UNKNOWN")

        if rsi is None:
            return {
                'passed': False,
                'confidence': 0.0,
                'reason': 'RSI indicator missing',
                'metadata': {},
            }

        # Obtener thresholds adaptativos
        thresholds = (
            self._get_thresholds_for_context(market_context) if self.adaptive else self.thresholds
        )

        # Support both old and new config formats for backward compatibility
        if "buy_threshold" in thresholds:
            buy_threshold = thresholds.get("buy_threshold", 30)
            sell_threshold = thresholds.get("sell_threshold", 70)
        else:
            # Legacy format fallback - convert old range to single threshold
            buy_threshold = thresholds.get("buy_min", 30)
            sell_threshold = thresholds.get("sell_max", 70)
            logger.warning(
                f"Using legacy RSI threshold format (buy_min/buy_max). "
                f"Please update to use buy_threshold/sell_threshold. "
                f"Derived: buy_threshold={buy_threshold}, sell_threshold={sell_threshold}"
            )

        # Get previous RSI value for crossover detection
        previous_rsi = self._get_previous_rsi(symbol)
        has_history = previous_rsi is not None

        # Update history for next call
        self._update_rsi_history(symbol, rsi)

        if signal_type == "BUY":
            # FIX: In trending markets, be more lenient - don't require strict crossover
            market_type = market_context.get("type", "unknown")
            is_trending = market_type in ["trend_up", "trending"]

            if self.use_crossover and has_history and not is_trending:
                # CORRECTED: BUY when RSI crosses ABOVE buy_threshold (reversal confirmation)
                if previous_rsi <= buy_threshold and rsi > buy_threshold:
                    # Crossover detected! Calculate confidence based on strength of reversal
                    # The further below threshold we were, the stronger the signal
                    crossover_strength = (
                        (buy_threshold - previous_rsi) / buy_threshold if buy_threshold > 0 else 0
                    )
                    confidence = 0.6 + (crossover_strength * 0.4)  # Base 0.6, max 1.0

                    logger.info(
                        f"RSI BUY crossover detected for {symbol}: "
                        f"RSI {previous_rsi:.2f} -> {rsi:.2f} (crossed above {buy_threshold})"
                    )

                    return {
                        'passed': True,
                        'confidence': max(0.5, min(1.0, confidence)),
                        'reason': f'RSI crossover: {previous_rsi:.2f} -> {rsi:.2f} (crossed above {buy_threshold})',
                        'metadata': {
                            'rsi': rsi,
                            'previous_rsi': previous_rsi,
                            'buy_threshold': buy_threshold,
                            'context': market_context.get('type'),
                            'crossover': True,
                            'symbol': symbol,
                        },
                    }
                else:
                    # No crossover yet
                    if rsi <= buy_threshold:
                        reason = (
                            f'RSI {rsi:.2f} <= {buy_threshold} (oversold, waiting for crossover)'
                        )
                    else:
                        reason = f'RSI {rsi:.2f} > {buy_threshold} (not oversold, no crossover)'

                    return {
                        'passed': False,
                        'confidence': 0.0,
                        'reason': reason,
                        'metadata': {
                            'rsi': rsi,
                            'previous_rsi': previous_rsi,
                            'buy_threshold': buy_threshold,
                            'waiting_for_crossover': True,
                            'symbol': symbol,
                        },
                    }
            else:
                # TRENDING MARKET or NO HISTORY: Use more lenient threshold
                # In trending markets, we just need RSI to be in a reasonable range
                # FIX: For trending markets, use buy_threshold directly (not stricter)
                # For non-trending markets with no history, use fallback offset
                if is_trending:
                    # In uptrend, allow BUY if RSI is not overbought (< sell_threshold)
                    # This allows dip buying during pullbacks in an uptrend
                    max_buy_rsi = sell_threshold - 10  # Allow BUY up to 10 below sell threshold
                    if rsi < max_buy_rsi:
                        logger.debug(
                            f"RSI BUY trending mode for {symbol}: "
                            f"RSI {rsi:.2f} < {max_buy_rsi} (dip opportunity in uptrend)"
                        )
                        return {
                            'passed': True,
                            'confidence': 0.6,
                            'reason': f'RSI {rsi:.2f} < {max_buy_rsi} (trending market, dip opportunity)',
                            'metadata': {
                                'rsi': rsi,
                                'buy_threshold': buy_threshold,
                                'max_buy_rsi': max_buy_rsi,
                                'context': market_context.get('type'),
                                'trending_mode': True,
                                'symbol': symbol,
                            },
                        }
                    else:
                        return {
                            'passed': False,
                            'confidence': 0.0,
                            'reason': f'RSI {rsi:.2f} >= {max_buy_rsi} (too high for dip buying)',
                            'metadata': {
                                'rsi': rsi,
                                'max_buy_rsi': max_buy_rsi,
                                'trending_mode': True,
                                'symbol': symbol,
                            },
                        }
                else:
                    # FALLBACK MODE: No history available, use stricter threshold
                    fallback_buy_threshold = buy_threshold - self.fallback_offset

                    if rsi <= fallback_buy_threshold:
                        # Calculate confidence: lower RSI = higher confidence (more oversold)
                        confidence = (
                            1.0 - ((rsi / fallback_buy_threshold) * 0.5)
                            if fallback_buy_threshold > 0
                            else 0.5
                        )

                        logger.debug(
                            f"RSI BUY fallback mode for {symbol}: "
                            f"RSI {rsi:.2f} <= {fallback_buy_threshold} (no history, using stricter threshold)"
                        )

                        return {
                            'passed': True,
                            'confidence': max(0.5, min(1.0, confidence)),
                            'reason': f'RSI {rsi:.2f} <= {fallback_buy_threshold} (oversold, fallback mode)',
                            'metadata': {
                                'rsi': rsi,
                                'buy_threshold': buy_threshold,
                                'fallback_threshold': fallback_buy_threshold,
                                'context': market_context.get('type'),
                                'fallback_mode': True,
                                'symbol': symbol,
                            },
                        }
                    else:
                        return {
                            'passed': False,
                            'confidence': 0.0,
                            'reason': f'RSI {rsi:.2f} > {fallback_buy_threshold} (not oversold enough for fallback)',
                            'metadata': {
                                'rsi': rsi,
                                'buy_threshold': buy_threshold,
                                'fallback_threshold': fallback_buy_threshold,
                                'fallback_mode': True,
                                'symbol': symbol,
                            },
                        }

        elif signal_type == "SELL":
            if self.use_crossover and has_history:
                # CORRECTED: SELL when RSI crosses BELOW sell_threshold (reversal confirmation)
                if previous_rsi >= sell_threshold and rsi < sell_threshold:
                    # Crossover detected! Calculate confidence based on strength of reversal
                    # The further above threshold we were, the stronger the signal
                    crossover_strength = (
                        (previous_rsi - sell_threshold) / (100 - sell_threshold)
                        if sell_threshold < 100
                        else 0
                    )
                    confidence = 0.6 + (crossover_strength * 0.4)  # Base 0.6, max 1.0

                    logger.info(
                        f"RSI SELL crossover detected for {symbol}: "
                        f"RSI {previous_rsi:.2f} -> {rsi:.2f} (crossed below {sell_threshold})"
                    )

                    return {
                        'passed': True,
                        'confidence': max(0.5, min(1.0, confidence)),
                        'reason': f'RSI crossover: {previous_rsi:.2f} -> {rsi:.2f} (crossed below {sell_threshold})',
                        'metadata': {
                            'rsi': rsi,
                            'previous_rsi': previous_rsi,
                            'sell_threshold': sell_threshold,
                            'context': market_context.get('type'),
                            'crossover': True,
                            'symbol': symbol,
                        },
                    }
                else:
                    # No crossover yet
                    if rsi >= sell_threshold:
                        reason = (
                            f'RSI {rsi:.2f} >= {sell_threshold} (overbought, waiting for crossover)'
                        )
                    else:
                        reason = f'RSI {rsi:.2f} < {sell_threshold} (not overbought, no crossover)'

                    return {
                        'passed': False,
                        'confidence': 0.0,
                        'reason': reason,
                        'metadata': {
                            'rsi': rsi,
                            'previous_rsi': previous_rsi,
                            'sell_threshold': sell_threshold,
                            'waiting_for_crossover': True,
                            'symbol': symbol,
                        },
                    }
            else:
                # FALLBACK MODE: No history available, use stricter threshold
                fallback_sell_threshold = sell_threshold + self.fallback_offset

                if rsi >= fallback_sell_threshold:
                    # Calculate confidence: higher RSI = higher confidence (more overbought)
                    distance_from_threshold = (
                        (rsi - fallback_sell_threshold) / (100 - fallback_sell_threshold)
                        if fallback_sell_threshold < 100
                        else 0
                    )
                    confidence = 0.5 + (distance_from_threshold * 0.5)

                    logger.debug(
                        f"RSI SELL fallback mode for {symbol}: "
                        f"RSI {rsi:.2f} >= {fallback_sell_threshold} (no history, using stricter threshold)"
                    )

                    return {
                        'passed': True,
                        'confidence': max(0.5, min(1.0, confidence)),
                        'reason': f'RSI {rsi:.2f} >= {fallback_sell_threshold} (overbought, fallback mode)',
                        'metadata': {
                            'rsi': rsi,
                            'sell_threshold': sell_threshold,
                            'fallback_threshold': fallback_sell_threshold,
                            'context': market_context.get('type'),
                            'fallback_mode': True,
                            'symbol': symbol,
                        },
                    }
                else:
                    return {
                        'passed': False,
                        'confidence': 0.0,
                        'reason': f'RSI {rsi:.2f} < {fallback_sell_threshold} (not overbought enough for fallback)',
                        'metadata': {
                            'rsi': rsi,
                            'sell_threshold': sell_threshold,
                            'fallback_threshold': fallback_sell_threshold,
                            'fallback_mode': True,
                            'symbol': symbol,
                        },
                    }

        return {'passed': False, 'confidence': 0.0, 'reason': 'Unknown signal type', 'metadata': {}}
