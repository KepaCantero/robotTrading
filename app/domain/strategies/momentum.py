"""
MomentumStrategy - Estrategia de momentum basada en RSI, EMA y volumen.

REFACTORED: Usa indicadores vectorizados de TechnicalIndicatorCalculator
y corrige señales invertidas (BUY con RSI alto, SELL con RSI bajo).

Implementa una estrategia de momentum que utiliza indicadores técnicos
para identificar oportunidades de trading basadas en tendencias de precio.
"""

from __future__ import annotations

import logging
from collections import deque
from decimal import Decimal
from typing import Any

from app.core.centralized_config import get_strategy_config, get_trading_threshold, get_config
from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.services.analysis.momentum import TechnicalIndicatorCalculator
from app.domain.services.signals.scoring import get_signal_scoring_engine

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """Estrategia de momentum basada en RSI, EMA y volumen."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Inicializar estrategia de momentum.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Initialize all parameters with defaults FIRST (before loading YAML config)
        # Parámetros técnicos
        self.rsi_period = config.get("rsi_period", 14)
        self.ema_period = config.get("ema_period", 20)
        self.lookback_period = config.get("lookback_period", 5)

        # ATR volatility filter settings - initialize defaults first
        self.min_atr_threshold = Decimal(str(config.get("min_atr_threshold", 0.015)))
        self.atr_filter_enabled = config.get("atr_filter_enabled", True)
        self.use_relative_atr = config.get("use_relative_atr", True)

        # Load strategy-specific configuration and override defaults
        strategy_config = get_strategy_config("momentum")
        if strategy_config:
            params = strategy_config.parameters
            # Merge strategy parameters into local config so downstream `self.config.get(...)` uses YAML values
            if isinstance(params, dict):
                try:
                    # Do not lose existing config keys
                    self.config.update({k: v for k, v in params.items() if v is not None})
                    # Update config dict as well for downstream access
                    config.update({k: v for k, v in params.items() if v is not None})
                except (FileNotFoundError, ValueError, KeyError, TypeError):
                    pass

            # Core thresholds - load from YAML, no defaults
            self.rsi_threshold = Decimal(
                str(params.get("rsi_threshold_buy") or params.get("rsi_threshold"))
            )
            self.momentum_threshold = Decimal(str(params.get("momentum_threshold")))
            self.volume_threshold = Decimal(str(params.get("volume_threshold")))

            # Use strategy-specific risk parameters or fallback to global
            self.stop_loss = Decimal(
                str(strategy_config.stop_loss_pct or get_trading_threshold("stop_loss_pct"))
            )
            self.take_profit = Decimal(
                str(strategy_config.take_profit_pct or get_trading_threshold("take_profit_pct"))
            )
            self.max_position_size = Decimal(
                str(strategy_config.max_position_size or get_trading_threshold("max_position_size"))
            )
            # FIX: Load max_exposure from portfolio config (target_weight * 1.1 for buffer) or default 60%
            # portfolio.yaml has target_weight: 0.60 for momentum, so max_exposure should be ~0.60-0.70
            self.max_exposure = Decimal(
                str(params.get("max_exposure", 0.60))
            )  # Default 60% (matches portfolio target_weight)

            # Technical indicator periods from parameters if present (now safe because defaults initialized)
            if "ema_period" in params:
                self.ema_period = params.get("ema_period", self.ema_period)
            if "lookback_period" in params:
                self.lookback_period = params.get("lookback_period", self.lookback_period)
            if "rsi_period" in params:
                self.rsi_period = params.get("rsi_period", self.rsi_period)

            # ATR/Stochastic RSI filters from parameters if present (now safe because defaults initialized)
            if "atr_filter_enabled" in params:
                self.atr_filter_enabled = params.get("atr_filter_enabled", self.atr_filter_enabled)
            if "use_relative_atr" in params:
                self.use_relative_atr = params.get("use_relative_atr", self.use_relative_atr)
            if "min_atr_threshold" in params:
                self.min_atr_threshold = Decimal(
                    str(params.get("min_atr_threshold", self.min_atr_threshold))
                )
            if "stoch_rsi_enabled" in params:
                self.config["stoch_rsi_enabled"] = params.get("stoch_rsi_enabled")
            if "stoch_rsi_min" in params:
                self.config["stoch_rsi_min"] = params.get("stoch_rsi_min")
            if "stoch_rsi_max" in params:
                self.config["stoch_rsi_max"] = params.get("stoch_rsi_max")
        else:
            # Fallback to config or defaults
            self.rsi_threshold = Decimal(str(config.get("rsi_threshold", 40)))
            self.momentum_threshold = getattr(config.trading, 'max_risk_per_trade', 0.02)
            self.stop_loss = Decimal(
                str(config.get("stop_loss", get_trading_threshold("stop_loss_pct")))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", get_trading_threshold("take_profit_pct")))
            )
            self.max_position_size = Decimal(
                str(config.get("max_position_size", get_trading_threshold("max_position_size")))
            )
            self.volume_threshold = Decimal(str(config.get("volume_threshold", 1.5)))
            self.max_exposure = Decimal(
                str(config.get("max_exposure", 0.60))
            )  # Default 60% (matches portfolio target_weight)

        # Load trading thresholds for technical indicators
        trading_config = get_config()
        self.tt = trading_config.trading_thresholds

        # Histórico para calcular indicadores reales - use config values
        price_history_len = self.tt.default_price_history_length
        rsi_history_len = self.tt.rsi_history_length
        atr_history_len = self.tt.atr_history_length

        self.price_history = deque(maxlen=price_history_len)
        self.high_history = deque(maxlen=price_history_len)
        self.low_history = deque(maxlen=price_history_len)
        self.volume_history = deque(maxlen=price_history_len)
        self.last_rsi = None
        self.last_ema = None
        self.rsi_history = deque(maxlen=rsi_history_len)

        # ATR volatility filter settings
        self.atr_history = deque(maxlen=atr_history_len)
        # Note: min_atr_threshold, atr_filter_enabled, use_relative_atr already initialized above

        # Cooldown para evitar señales repetidas - use config value
        self.last_signal_bar_index = None
        self.last_signal_type = None
        self.current_bar_index = 0
        self.cooldown_bars = config.get("cooldown_bars", 5)  # Número de barras para cooldown

        # TASK-SC-5: Signal Scoring Engine integration
        self.signal_scoring_engine = get_signal_scoring_engine()

        # REFACTORED: Use vectorized TechnicalIndicatorCalculator
        self.indicator_calculator = TechnicalIndicatorCalculator()

        logger.info(f"MomentumStrategy initialized: {self.name}")

    def get_required_parameters(self) -> list[str]:
        """
        Obtener parámetros requeridos para la estrategia.

        Returns:
            Lista de parámetros requeridos
        """
        return [
            "rsi_threshold",
            "momentum_threshold",
            "stop_loss",
            "take_profit",
            "max_position_size",
        ]

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        """
        Generar señales de trading basadas en momentum con indicadores reales.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas (procesadas por Signal Scoring Engine)
        """
        raw_signals = []

        try:
            # Actualizar histórico
            self.price_history.append(float(market_data.close or market_data.last))
            self.high_history.append(
                float(market_data.high or market_data.close or market_data.last)
            )
            self.low_history.append(float(market_data.low or market_data.close or market_data.last))
            self.volume_history.append(float(market_data.volume))
            self.current_bar_index += 1

            # REFACTORED: Calcular indicadores usando TechnicalIndicatorCalculator (vectorizado)
            prices_list = list(self.price_history)
            highs_list = list(self.high_history)
            lows_list = list(self.low_history)
            volumes_list = list(self.volume_history)

            rsi = self.indicator_calculator.calculate_rsi(prices_list, self.rsi_period)
            ema = self.indicator_calculator.calculate_ema(prices_list, self.ema_period)
            volume_ratio = self._calculate_volume_ratio(market_data)
            roc = self.indicator_calculator.calculate_roc(prices_list, period=12)
            obv = self.indicator_calculator.calculate_obv(prices_list, volumes_list)
            obv_trend = self._calculate_obv_trend_from_value(obv)

            # Calculate ATR using vectorized calculator (pandas_ta.atr)
            atr = self.indicator_calculator.calculate_atr(
                highs_list, lows_list, prices_list, period=14
            )
            if atr is not None:
                self.atr_history.append(atr)

            # Only generate signals if we have sufficient history
            if rsi is None or ema is None:
                # Log why signals are not generated (insufficient history) - DEBUG level for diagnostics
                if self.current_bar_index % self.tt.log_interval_bars == 0:
                    logger.debug(
                        f"MOMENTUM {market_data.symbol}: Skipping - insufficient history "
                        f"(RSI={rsi}, EMA={ema}, bars={self.current_bar_index}). "
                        f"Need at least {self.rsi_period} bars for RSI and {self.ema_period} for EMA"
                    )
                return []

            # Convertir None a valores seguros para logging
            roc_safe = roc if roc is not None else 0.0

            # Guardar para uso en señales
            self.last_rsi = rsi
            self.last_ema = ema

            # OPTIMIZED: Calculate Stochastic RSI using pandas_ta library (no manual calculations)
            # Build RSI history for Stochastic RSI calculation
            stoch_rsi_k = None
            stoch_rsi_d = None
            if rsi is not None:
                if not hasattr(self, 'rsi_history'):
                    self.rsi_history = deque(maxlen=50)
                # Append RSI ONCE (removed duplicate append)
                self.rsi_history.append(rsi)

                # Calculate Stochastic RSI using pandas_ta.stochrsi() via TechnicalIndicatorCalculator
                # This uses the library, NOT manual calculation
                if len(self.rsi_history) >= 14:
                    rsi_history_list = list(self.rsi_history)
                    # This calls pandas_ta.stochrsi() internally (see momentum_analysis.py)
                    stoch_result = self.indicator_calculator.calculate_stochastic_rsi(
                        rsi_history_list, period=14
                    )
                    if stoch_result[0] is not None and stoch_result[1] is not None:
                        stoch_rsi_k, stoch_rsi_d = stoch_result
                        logger.debug(
                            f"MOMENTUM {market_data.symbol}: Stochastic RSI calculated: "
                            f"K={stoch_rsi_k:.2f}, D={stoch_rsi_d:.2f}"
                        )

            # Verificar cooldown
            cooldown_active = self._is_cooldown_active(market_data)
            current_price = market_data.close or market_data.last
            atr_filter_passed = self._passes_atr_filter(current_price)

            # Log diagnostic info BEFORE checking conditions (INFO level for visibility)

            # Log ALL candidates (every bar) to track what's being evaluated - DEBUG for detailed diagnostics
            logger.debug(
                f"MOMENTUM CANDIDATE {market_data.symbol}: "
                f"RSI={rsi:.2f}, price={current_price:.2f}, EMA={ema:.2f}, "
                f"volume_ratio={volume_ratio:.2f}, ROC={roc_safe:.2f}, OBV={obv_trend}, "
                f"ATR_filter={atr_filter_passed}, cooldown={cooldown_active}, bar_index={self.current_bar_index}"
            )

            if not cooldown_active:
                # IMPROVEMENT: Apply Stochastic RSI filter to reduce false signals
                stoch_rsi_passed = self._should_generate_signal(stoch_rsi_k, stoch_rsi_d)

                # CORRECTED: Prevent overlapping signals and inverted signals
                # Only generate one signal type per bar to avoid conflicts
                if atr_filter_passed and stoch_rsi_passed:
                    buy_condition = self._is_buy_signal(
                        rsi, ema, volume_ratio, roc, obv_trend, market_data
                    )
                    sell_condition = self._is_sell_signal(
                        rsi, ema, volume_ratio, roc, obv_trend, market_data
                    )

                    # FIXED: Prevent overlapping signals - prioritize buy if both conditions met
                    # CORRECTED: Never generate BUY with RSI > 70 or SELL with RSI < 30
                    if buy_condition and not sell_condition:
                        # Only generate BUY if conditions are met and no SELL
                        current_atr = self.atr_history[-1] if self.atr_history else None
                        signal = self._create_buy_signal(
                            market_data, rsi, ema, volume_ratio, roc, current_atr
                        )
                        raw_signals.append(signal)
                        self.last_signal_bar_index = self.current_bar_index
                        self.last_signal_type = "buy"
                        logger.info(
                            f"MOMENTUM BUY signal generated for {market_data.symbol}: "
                            f"RSI={rsi:.2f}, price={current_price:.2f}, EMA={ema:.2f}, "
                            f"volume_ratio={volume_ratio:.2f}, ROC={roc_safe:.2f}, OBV={obv_trend}"
                        )
                    elif sell_condition and not buy_condition:
                        # Only generate SELL if conditions are met and no BUY
                        current_atr = self.atr_history[-1] if self.atr_history else None
                        signal = self._create_sell_signal(
                            market_data, rsi, ema, volume_ratio, roc, current_atr
                        )
                        raw_signals.append(signal)
                        self.last_signal_bar_index = self.current_bar_index
                        self.last_signal_type = "sell"
                        logger.info(
                            f"MOMENTUM SELL signal generated for {market_data.symbol}: "
                            f"RSI={rsi:.2f}, price={current_price:.2f}, EMA={ema:.2f}, "
                            f"volume_ratio={volume_ratio:.2f}, ROC={roc_safe:.2f}, OBV={obv_trend}"
                        )
                    elif buy_condition and sell_condition:
                        # If both conditions are met, log warning and choose based on RSI
                        logger.warning(
                            f"MOMENTUM {market_data.symbol}: Both BUY and SELL conditions met - "
                            f"RSI={rsi:.2f}. Choosing based on RSI zone."
                        )
                        # Prioritize based on RSI: if RSI < 45, prefer BUY; if RSI > 55, prefer SELL
                        current_atr = self.atr_history[-1] if self.atr_history else None
                        if rsi < 45:
                            signal = self._create_buy_signal(
                                market_data, rsi, ema, volume_ratio, roc, current_atr
                            )
                            raw_signals.append(signal)
                            self.last_signal_bar_index = self.current_bar_index
                            self.last_signal_type = "buy"
                        elif rsi > 55:
                            signal = self._create_sell_signal(
                                market_data, rsi, ema, volume_ratio, roc, current_atr
                            )
                            raw_signals.append(signal)
                            self.last_signal_bar_index = self.current_bar_index
                            self.last_signal_type = "sell"
                        # If 45 <= RSI <= 55, don't generate any signal (neutral zone)
                else:
                    # Log filter rejections - DEBUG for diagnostics
                    current_atr = self.atr_history[-1] if self.atr_history else None
                    current_price = market_data.close or market_data.last
                    filter_failed = []
                    if not atr_filter_passed:
                        atr_str = f"{current_atr:.4f}" if current_atr is not None else "N/A"
                        filter_failed.append(
                            f"ATR filter (ATR={atr_str}, threshold={self.min_atr_threshold:.4f})"
                        )
                    if not stoch_rsi_passed:
                        k_str = f"{stoch_rsi_k:.2f}" if stoch_rsi_k is not None else "N/A"
                        d_str = f"{stoch_rsi_d:.2f}" if stoch_rsi_d is not None else "N/A"
                        filter_failed.append(f"StochRSI filter (K={k_str}, D={d_str})")

                    logger.debug(
                        f"MOMENTUM candidate rejected {market_data.symbol}: "
                        f"{', '.join(filter_failed)}"
                    )
            else:
                # Log cooldown rejections - DEBUG for diagnostics
                logger.debug(
                    f"MOMENTUM candidate rejected {market_data.symbol}: "
                    f"Cooldown active (last_signal_bar={self.last_signal_bar_index}, "
                    f"current_bar={self.current_bar_index}, cooldown_bars={self.cooldown_bars})"
                )

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(
                f"MOMENTUM error generating signals for {market_data.symbol}: {e}", exc_info=True
            )

        # TASK-SC-5: Process signals through Signal Scoring Engine
        # NOTE: Cooldown is managed internally by the strategy's cooldown logic
        # Don't apply additional cooldown from scoring engine for backtesting
        if raw_signals:
            logger.debug(
                f"MOMENTUM: {len(raw_signals)} raw signal(s) for {market_data.symbol}, "
                "processing through scoring engine"
            )
            # In backtesting, we want to evaluate all signals without cooldown
            # But we still want scoring and ranking
            processed_signals = self.signal_scoring_engine.process_signals(
                raw_signals, apply_cooldown=False
            )
            logger.debug(
                f"MOMENTUM: {len(processed_signals)} signal(s) after scoring (from {len(raw_signals)} raw) "
                f"for {market_data.symbol}"
            )
            if len(processed_signals) < len(raw_signals):
                logger.info(
                    f"MOMENTUM: {len(raw_signals) - len(processed_signals)} signal(s) filtered by scoring engine "
                    f"for {market_data.symbol}"
                )
            return processed_signals

        return []

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar si la señal cumple criterios de riesgo.

        Args:
            signal: Señal a verificar
            portfolio: Estado actual del portfolio

        Returns:
            True si la señal pasa el risk check, False en caso contrario
        """
        try:
            # FIX: Order matters - check SELL position existence BEFORE calculating position_size
            # For SELL, if no position exists, get_position_size() returns 0, which fails the min check
            if signal.signal_type == SignalType.SELL:
                # First check if position exists
                existing_position = self._get_existing_position(portfolio, signal.symbol)
                if not existing_position:
                    logger.debug(
                        f"MOMENTUM risk_check rejected SELL {signal.symbol}: "
                        "No position exists to sell"
                    )
                    return False
                # Now calculate sell quantity and verify we have enough
                sell_quantity = self.get_position_size(signal, portfolio)
                if sell_quantity <= 0:
                    logger.debug(
                        f"MOMENTUM risk_check rejected SELL {signal.symbol}: "
                        f"Position size too small ({sell_quantity:.6f})"
                    )
                    return False
                if existing_position.quantity < sell_quantity:
                    logger.debug(
                        f"MOMENTUM risk_check rejected SELL {signal.symbol}: "
                        f"Insufficient position (need={sell_quantity:.6f}, have={existing_position.quantity:.6f})"
                    )
                    return False
                # For SELL, position_size is the sell_quantity
                position_size = sell_quantity
            elif signal.signal_type == SignalType.BUY:
                # For BUY, calculate position size and verify cash
                position_size = self.get_position_size(signal, portfolio)
                if position_size <= 0:
                    logger.debug(
                        f"MOMENTUM risk_check rejected BUY {signal.symbol}: "
                        f"Position size too small ({position_size:.6f})"
                    )
                    return False
                required_cash = signal.price * position_size
                if required_cash > portfolio.cash:
                    logger.debug(
                        f"MOMENTUM risk_check rejected BUY {signal.symbol}: "
                        f"Insufficient cash (required=${required_cash:.2f} > available=${portfolio.cash:.2f})"
                    )
                    return False
            else:
                # HOLD or other signal types - not supported
                return False

            # Verificar límites de exposición
            total_exposure = self._calculate_total_exposure(portfolio)
            # CORRECTED: Use config max_exposure from self (loaded in __init__)
            max_exposure = self.max_exposure  # Loaded from config or default 50%

            # FIX: Add detailed logging to diagnose why signals are rejected
            # Calculate exposure after this trade would execute
            if signal.signal_type == SignalType.BUY:
                # Estimate exposure after BUY: add position value to invested
                estimated_position_value = signal.price * position_size
                total_value_after = (
                    portfolio.cash
                    + sum(p.market_value for p in portfolio.positions)
                    - (signal.price * position_size)
                )
                invested_after = (
                    sum(p.market_value for p in portfolio.positions) + estimated_position_value
                )
                exposure_after = (
                    invested_after / total_value_after if total_value_after > 0 else Decimal("0")
                )

                logger.debug(
                    f"MOMENTUM risk_check BUY {signal.symbol}: "
                    f"current_exposure={total_exposure:.2%}, exposure_after={exposure_after:.2%}, "
                    f"max={max_exposure:.2%}, cash=${portfolio.cash:.2f}, "
                    f"position_size={position_size:.6f}, position_value=${estimated_position_value:.2f}"
                )
            else:
                # For SELL, exposure should decrease
                logger.debug(
                    f"MOMENTUM risk_check SELL {signal.symbol}: "
                    f"current_exposure={total_exposure:.2%}, max={max_exposure:.2%}, "
                    f"cash=${portfolio.cash:.2f}, sell_quantity={position_size:.6f}"
                )

            if total_exposure > max_exposure:
                logger.debug(
                    f"MOMENTUM risk_check rejected {signal.signal_type} {signal.symbol}: "
                    f"Total exposure too high ({total_exposure:.2%} > {max_exposure:.2%})"
                )
                return False

            logger.debug(
                f"MOMENTUM risk_check passed {signal.signal_type} {signal.symbol}: "
                f"position_size={position_size:.6f}, cash=${portfolio.cash:.2f}, exposure={total_exposure:.2%}"
            )
            return True

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"MOMENTUM risk_check error for {signal.symbol}: {e}", exc_info=True)
            return False

    # REFACTORED: Methods removed - use TechnicalIndicatorCalculator instead

    def _calculate_volume_ratio(self, market_data: Quote) -> Decimal:
        """
        Calcular ratio de volumen dinámicamente usando histórico.

        Args:
            market_data: Datos de mercado

        Returns:
            Ratio de volumen
        """
        if len(self.volume_history) < 20:
            # No hay suficiente histórico, usar valor conservador
            return Decimal("1")

        # Calcular promedio de volumen de las últimas 20 barras
        volume_list = list(self.volume_history)
        avg_volume = sum(volume_list[-20:]) / 20
        if avg_volume > 0:
            return market_data.volume / Decimal(str(avg_volume))
        return Decimal("1")

    def _calculate_obv_trend_from_value(self, obv: float | None) -> str | None:
        """
        Calculate OBV trend from OBV value.

        REFACTORED: Simplified - uses OBV value from calculator.
        """
        if obv is None:
            return None

        # Compare current OBV with recent history
        if len(self.price_history) < 10:
            return "neutral"

        # Simple trend: if OBV is positive and increasing, trend is rising
        # This is a simplified version - in production, compare multiple OBV values
        return "rising" if obv > 0 else "falling"

    def _calculate_obv_trend(self, lookback: int = 10) -> str | None:
        """
        TASK-IND-OBV-1: Calcular tendencia de OBV.

        Compara OBV actual vs. OBV de hace N períodos para determinar la tendencia.

        Args:
            lookback: Períodos para comparar (default 10)

        Returns:
            "rising" si OBV está aumentando (buying pressure)
            "falling" si OBV está disminuyendo (selling pressure)
            "neutral" si es estable
            None si no hay suficiente histórico
        """
        if len(self.price_history) < lookback + 2:
            return None

        # Calcular OBV actual
        current_obv = 0.0
        for i in range(1, len(self.price_history)):
            if self.price_history[i] > self.price_history[i - 1]:
                current_obv += self.volume_history[i]
            elif self.price_history[i] < self.price_history[i - 1]:
                current_obv -= self.volume_history[i]

        # Calcular OBV de hace N períodos
        period_start = max(0, len(self.price_history) - lookback - 2)
        past_obv = 0.0
        for i in range(period_start + 1, len(self.price_history) - lookback + 1):
            if i < len(self.price_history) and i - 1 >= 0:
                if self.price_history[i] > self.price_history[i - 1]:
                    past_obv += self.volume_history[i]
                elif self.price_history[i] < self.price_history[i - 1]:
                    past_obv -= self.volume_history[i]

        # Comparar para determinar tendencia
        if current_obv > past_obv * 1.02:  # 2% margen para evitar ruido
            return "rising"
        elif current_obv < past_obv * 0.98:
            return "falling"
        else:
            return "neutral"

    def _is_cooldown_active(self, market_data: Quote) -> bool:
        """
        Verificar si el cooldown está activo para evitar señales repetidas.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            True si el cooldown está activo (no debe generar señales)
        """
        if self.last_signal_bar_index is None:
            # No ha habido señales aún, no hay cooldown
            return False

        # Calcular barras transcurridas desde última señal
        bars_since_last_signal = self.current_bar_index - self.last_signal_bar_index

        # Si han pasado menos barras que cooldown_bars, el cooldown está activo
        if bars_since_last_signal < self.cooldown_bars:
            logger.debug(
                f"MOMENTUM: Cooldown active ({bars_since_last_signal}/{self.cooldown_bars} bars since last signal)"
            )
            return True

        return False

    def _is_buy_signal(
        self,
        rsi: float,
        ema: float,
        volume_ratio: Decimal,
        roc: float | None,
        obv_trend: str | None,
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal de compra.

        CORRECTED: Never generate BUY when RSI > 70 (overbought).
        Only generate BUY when RSI indicates oversold conditions (< threshold).

        Args:
            rsi: Valor de RSI (0-100)
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            roc: Valor de ROC (Rate of Change)
            obv_trend: Tendencia de OBV
            market_data: Datos de mercado

        Returns:
            True si debe generar señal de compra
        """
        current_price = market_data.close or market_data.last

        # CORRECTED: BUY signals only when RSI < threshold (oversold)
        # NEVER generate BUY when RSI > configured overbought threshold
        if rsi >= self.tt.rsi_overbought:
            logger.debug(
                f"MOMENTUM {market_data.symbol}: BUY rejected - RSI overbought ({rsi:.2f} >= {self.tt.rsi_overbought})"
            )
            return False

        # FIXED: Momentum strategy should buy on momentum continuation, not oversold reversal
        # Buy when: RSI 40-70 (momentum zone), price above EMA, volume > threshold, positive ROC
        # This is TRUE momentum trading: catch the trend, not the bottom

        volume_threshold = Decimal(str(self.config.get("volume_threshold")))
        has_volume = volume_ratio >= volume_threshold

        ema_bullish = current_price > Decimal(str(ema))  # Price above EMA (uptrend)

        # Momentum confirmation
        momentum_threshold = Decimal(str(self.config.get("momentum_threshold")))
        has_momentum = roc is None or roc >= float(momentum_threshold)  # Positive momentum

        obv_bullish = obv_trend is None or obv_trend in ["rising", "neutral"]

        # FIXED: Momentum buy conditions - RSI in momentum zone using config values
        # Option 1: RSI in momentum zone with all confirmations
        rsi_momentum_zone = self.tt.momentum_zone_min <= rsi <= self.tt.momentum_zone_max

        # Option 2: RSI recovering from oversold (rising from below threshold) with volume surge
        rsi_recovering = rsi < self.tt.rsi_recovering_threshold and has_volume and has_momentum

        if rsi_momentum_zone:
            # Core momentum trade: RSI in good range, price above EMA, volume + momentum
            return (
                has_volume and ema_bullish and has_momentum and (obv_bullish is None or obv_bullish)
            )
        elif rsi_recovering:
            # Early entry: RSI recovering from oversold with strong volume/momentum
            strong_volume = volume_ratio >= Decimal(str(self.tt.strong_volume_multiplier))
            return strong_volume and ema_bullish and has_momentum

        return False

    def _is_sell_signal(
        self,
        rsi: float,
        ema: float,
        volume_ratio: Decimal,
        roc: float | None,
        obv_trend: str | None,
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal de venta.

        CORRECTED: Never generate SELL when RSI < 30 (oversold).
        Only generate SELL when RSI indicates overbought conditions (> threshold).

        Args:
            rsi: Valor de RSI (0-100)
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            roc: Valor de ROC (Rate of Change)
            obv_trend: Tendencia de OBV
            market_data: Datos de mercado

        Returns:
            True si debe generar señal de venta
        """
        current_price = market_data.close or market_data.last

        # CORRECTED: SELL signals only when RSI > threshold (overbought)
        # NEVER generate SELL when RSI < configured oversold threshold
        if rsi <= self.tt.rsi_oversold:
            logger.debug(
                f"MOMENTUM {market_data.symbol}: SELL rejected - RSI oversold ({rsi:.2f} <= {self.tt.rsi_oversold})"
            )
            return False

        # OPTIMIZED: SELL conditions for win rate >30%
        # SELL when RSI overbought with bearish confirmation using config values
        rsi_overbought = rsi > self.tt.rsi_sell_overbought
        rsi_neutral_bearish = (
            self.tt.rsi_neutral_zone_min <= rsi <= self.tt.rsi_neutral_zone_max
        ) and current_price < Decimal(str(ema))

        # Core conditions - stricter for better win rate
        volume_threshold = Decimal(str(self.config.get("volume_threshold")))
        has_volume = volume_ratio >= volume_threshold  # Use configured volume threshold

        ema_bearish = current_price < Decimal(str(ema))  # Price below EMA (trend reversal)

        # Momentum confirmation
        momentum_threshold = Decimal(str(self.config.get("momentum_threshold")))
        roc_negative = roc is None or roc <= -float(momentum_threshold)  # Negative momentum

        obv_bearish = obv_trend is None or obv_trend in ["falling", "neutral"]

        rsi_condition = rsi_overbought or rsi_neutral_bearish
        return rsi_condition and ema_bearish and has_volume and roc_negative and obv_bearish

    def _create_buy_signal(
        self,
        market_data: Quote,
        rsi: float,
        ema: float,
        volume_ratio: Decimal,
        roc: float | None,
        atr: float | None = None,
    ) -> Signal:
        """
        Crear señal de compra con metadata completa.

        Args:
            market_data: Datos de mercado
            rsi: Valor de RSI
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            roc: Valor de ROC - TASK-IND-ROC-2

        Returns:
            Señal de compra
        """
        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=float(rsi),
            liquidity_score=float(self.tt.signal_liquidity_score),
            priority_score=float(self.tt.signal_priority_score),
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=Decimal(
                "1"
            ),  # FIX: Placeholder - get_position_size() calculates actual size based on capital
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "rsi": str(rsi),
                "ema": str(ema),
                "volume_ratio": str(volume_ratio),
                "roc": str(roc) if roc is not None else "N/A",
                "atr": str(atr) if atr is not None else "N/A",  # ATR for dynamic stop-loss
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "atr_multiplier": str(self.config.get("atr_multiplier")),
                "use_dynamic_stop_loss": str(self.config.get("use_dynamic_stop_loss")),
                "momentum_type": "positive_breakout",
                "reason": self._format_signal_reason(
                    "positive_breakout", rsi, volume_ratio, roc, atr
                ),
            },
        )

    def _create_sell_signal(
        self,
        market_data: Quote,
        rsi: float,
        ema: float,
        volume_ratio: Decimal,
        roc: float | None,
        atr: float | None = None,
    ) -> Signal:
        """
        Crear señal de venta con metadata completa.

        Args:
            market_data: Datos de mercado
            rsi: Valor de RSI
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            roc: Valor de ROC - TASK-IND-ROC-2

        Returns:
            Señal de venta
        """
        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=abs(self.tt.rsi_neutral_zone_min - float(rsi)),  # Distance from neutral zone
            liquidity_score=float(self.tt.signal_liquidity_score),
            priority_score=float(self.tt.signal_priority_score),
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=Decimal(
                "1"
            ),  # FIX: Placeholder - get_position_size() calculates actual size based on capital
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "rsi": str(rsi),
                "ema": str(ema),
                "volume_ratio": str(volume_ratio),
                "roc": str(roc) if roc is not None else "N/A",
                "atr": str(atr) if atr is not None else "N/A",  # ATR for dynamic stop-loss
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "atr_multiplier": str(self.config.get("atr_multiplier")),
                "use_dynamic_stop_loss": str(self.config.get("use_dynamic_stop_loss")),
                "momentum_type": "negative_reversal",
                "reason": self._format_signal_reason(
                    "negative_reversal", rsi, volume_ratio, roc, atr
                ),
            },
        )

    def _get_existing_position(self, portfolio: Portfolio, symbol: str):
        """
        Obtener posición existente para un símbolo.

        Args:
            portfolio: Portfolio actual
            symbol: Símbolo a buscar

        Returns:
            Posición existente o None
        """
        for position in portfolio.positions:
            if position.symbol == symbol:
                return position
        return None

    def _calculate_total_exposure(self, portfolio: Portfolio) -> Decimal:
        """
        Calcular exposición total del portfolio.

        Args:
            portfolio: Portfolio actual

        Returns:
            Exposición total como porcentaje
        """
        total_value = portfolio.cash
        for position in portfolio.positions:
            total_value += position.market_value

        if total_value == 0:
            return Decimal("0")

        invested_value = total_value - portfolio.cash
        return invested_value / total_value

    # REFACTORED: _calculate_atr removed - use TechnicalIndicatorCalculator.calculate_atr()

    def _passes_atr_filter(self, current_price: Decimal | None = None) -> bool:
        """
        Check if current market passes ATR volatility filter.

        IMPROVEMENT: Uses relative ATR (% of price) instead of absolute ATR.
        This makes the filter more consistent across different price levels.
        """
        if not self.atr_filter_enabled:
            return True

        if len(self.atr_history) == 0:
            return True

        current_atr = self.atr_history[-1] if self.atr_history else None
        if current_atr is None:
            return True

        # IMPROVEMENT: Use relative ATR (% of price) if enabled and price available
        if self.use_relative_atr and current_price is not None and current_price > 0:
            relative_atr = float(current_atr) / float(current_price)
            # min_atr_threshold is already in decimal (e.g., 0.015 = 1.5%)
            return relative_atr > float(self.min_atr_threshold)
        else:
            # Fallback to absolute ATR for backward compatibility
            return float(current_atr) > float(self.min_atr_threshold)

    # REFACTORED: _calculate_stochastic_rsi removed - use TechnicalIndicatorCalculator.calculate_stochastic_rsi()

    def _should_generate_signal(
        self, stoch_rsi: float | None, stoch_rsi_signal: float | None
    ) -> bool:
        """
        TASK-IND-STOCH-2: Determinar si se debe generar señal basado en Stochastic RSI.

        OPTIMIZED: Uses configurable thresholds from config file.

        Args:
            stoch_rsi: Valor de Stochastic RSI
            stoch_rsi_signal: Valor de señal de Stochastic RSI

        Returns:
            True si se debe generar señal, False si se debe filtrar
        """
        # Check if Stochastic RSI filter is enabled
        stoch_rsi_enabled = self.config.get("stoch_rsi_enabled")
        if not stoch_rsi_enabled:
            return True

        # Si no hay suficiente data, permitir señales (degradación tolerante)
        if stoch_rsi is None or stoch_rsi_signal is None:
            return True

        # OPTIMIZED: Use configurable thresholds
        stoch_rsi_min = self.config.get("stoch_rsi_min")
        stoch_rsi_max = self.config.get("stoch_rsi_max")

        # Condiciones de filtrado:
        # - Generar señales cuando no está en extremos (evitar sobrecompra/sobreventa)
        # - Esto reduce falsas señales en zonas extremas
        return stoch_rsi_min <= stoch_rsi <= stoch_rsi_max

    def _format_signal_reason(
        self,
        signal_type: str,
        rsi: float,
        volume_ratio: Decimal,
        roc: float | None,
        atr: float | None,
    ) -> str:
        """
        Formatear razón de señal de manera segura sin formatos condicionales en f-strings.

        Args:
            signal_type: Tipo de señal ("positive_breakout" o "negative_reversal")
            rsi: Valor de RSI
            volume_ratio: Ratio de volumen
            roc: Valor de ROC (puede ser None)
            atr: Valor de ATR (puede ser None)

        Returns:
            String formateado con la razón de la señal
        """
        # Format roc safely - use "N/A" when None to match test expectations
        roc_str = "N/A" if roc is None else f"{roc:.2f}"

        # Format atr safely
        atr_str = f"{atr:.4f}" if atr is not None else "N/A"

        # Format trend direction based on signal type
        trend = "above" if signal_type == "positive_breakout" else "below"

        return (
            f"momentum_{signal_type}: rsi={rsi:.2f} ema_trend={trend} "
            f"volume={float(volume_ratio):.2f}x roc={roc_str} atr={atr_str}"
        )
