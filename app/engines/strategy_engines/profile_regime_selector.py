"""
Profile-Based Regime Selector - Selector de estrategia basado en perfil de inversor.

Implementa un selector adaptativo que ajusta estrategias y parametros segun:
- Perfil de capital (SURVIVAL, GROWTH, OPTIMIZATION)
- Regimen de mercado (usando Hurst exponent y half-life)
- Factores de calidad y momentum

Basado en reglas de:
- Ernest Chan: Hurst exponent, half-life, 2% max risk
- Robert Carver: Volatility targeting 15%, diversification
- Gray & Vogel: Multi-window momentum, skip-month momentum
- Berkin & Swedroe: Quality screening, factor-based
- Realistic Retail Rules: Capital phases
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from numpy.linalg import LinAlgError

from app.domain.models.market_data import Quote
from app.domain.models.signal import Signal

from .base import BaseStrategyEngine

logger = logging.getLogger(__name__)


class InvestorProfile(str, Enum):
    """Perfiles de inversor basados en capital."""

    SURVIVAL = "survival"  # 1k-10k: aprendizaje, bajo riesgo
    GROWTH = "growth"  # 10k-50k: equilibrado
    OPTIMIZATION = "optimization"  # 50k-500k: todas las estrategias


class MarketRegime(str, Enum):
    """Regimenes de mercado detectados."""

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


@dataclass
class ProfileConfig:
    """Configuracion por perfil de inversor."""

    # Limites de capital
    min_capital: Decimal
    max_capital: Decimal

    # Risk management (Ernest Chan rules)
    max_risk_per_trade: Decimal  # % maximo por trade
    max_position_size: Decimal  # % maximo por posicion
    max_positions: int  # numero maximo de posiciones

    # Volatility targeting (Robert Carver rules)
    target_volatility: Decimal  # volatilidad objetivo anualizada

    # Estrategias habilitadas
    strategies_enabled: List[str]

    # Stop loss y take profit
    default_stop_loss: Decimal
    default_take_profit: Decimal


# Configuraciones por perfil (from realistic-retail-trading-rules.md)
PROFILE_CONFIGS: Dict[InvestorProfile, ProfileConfig] = {
    InvestorProfile.SURVIVAL: ProfileConfig(
        min_capital=Decimal("1000"),
        max_capital=Decimal("10000"),
        max_risk_per_trade=Decimal("0.005"),  # 0.5%
        max_position_size=Decimal("0.10"),  # 10%
        max_positions=2,
        target_volatility=Decimal("0.10"),  # 10%
        strategies_enabled=["trend_following"],
        default_stop_loss=Decimal("0.02"),  # 2%
        default_take_profit=Decimal("0.04"),  # 4%
    ),
    InvestorProfile.GROWTH: ProfileConfig(
        min_capital=Decimal("10000"),
        max_capital=Decimal("50000"),
        max_risk_per_trade=Decimal("0.01"),  # 1%
        max_position_size=Decimal("0.15"),  # 15%
        max_positions=4,
        target_volatility=Decimal("0.12"),  # 12%
        strategies_enabled=["trend_following", "momentum_engine", "mean_reversion_engine"],
        default_stop_loss=Decimal("0.025"),  # 2.5%
        default_take_profit=Decimal("0.06"),  # 6%
    ),
    InvestorProfile.OPTIMIZATION: ProfileConfig(
        min_capital=Decimal("50000"),
        max_capital=Decimal("500000"),
        max_risk_per_trade=Decimal("0.02"),  # 2% (Ernest Chan max)
        max_position_size=Decimal("0.20"),  # 20% (Markowitz max)
        max_positions=8,
        target_volatility=Decimal("0.15"),  # 15% (Robert Carver target)
        strategies_enabled=[
            "trend_following",
            "momentum_engine",
            "mean_reversion_engine",
            "breakout",
        ],
        default_stop_loss=Decimal("0.03"),  # 3%
        default_take_profit=Decimal("0.08"),  # 8%
    ),
}


class ProfileBasedRegimeSelector(BaseStrategyEngine):
    """
    Selector de estrategia basado en perfil de inversor y regimen de mercado.

    Caracteristicas:
    - Deteccion de regimen usando Hurst exponent y half-life
    - Parametros ajustados por perfil de capital
    - Quality screening antes de generar senales
    - Multi-window momentum (Gray & Vogel)
    - Volatility targeting (Robert Carver)
    - Kelly Criterion position sizing

    Referencias:
    - Ernest Chan: Quantitative Trading, Algorithmic Trading
    - Robert Carver: Systematic Trading
    - Gray & Vogel: Quantitative Momentum
    - Berkin & Swedroe: The Incredible Shrinking Alpha
    """

    # Ventanas de momentum (Gray & Vogel)
    MOMENTUM_WINDOWS = [21, 63, 126, 252]  # 1m, 3m, 6m, 12m
    SKIP_MONTH_DAYS = 21  # Skip ultimo mes para momentum

    # Umbrales de deteccion
    HURST_TRENDING_THRESHOLD = 0.55  # H > 0.55 = trending
    HURST_MEAN_REVERSION_THRESHOLD = 0.45  # H < 0.45 = mean reversion
    HALF_LIFE_MAX = 252  # Max half-life para mean reversion (1 ano)
    VOLATILITY_HIGH_THRESHOLD = 0.30  # 30% anualizado = alta volatilidad
    VOLATILITY_LOW_THRESHOLD = 0.12  # 12% anualizado = baja volatilidad

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar ProfileBasedRegimeSelector.

        Args:
            config: Configuracion del selector
                - capital: Capital actual (determina perfil)
                - strategies: Dict de estrategias disponibles
                - override_profile: Forzar perfil especifico (opcional)
        """
        super().__init__(config)

        # Capital y perfil
        self.capital = Decimal(str(config.get("capital", 10000)))
        self.profile = self._determine_profile(config.get("override_profile"))
        self.profile_config = PROFILE_CONFIGS[self.profile]

        # Estrategias disponibles
        self.strategies: Dict[str, BaseStrategyEngine] = {}

        # Estado del regimen
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_confidence = 0.0
        self.hurst_exponent: Optional[float] = None
        self.half_life: Optional[float] = None

        # Historial de precios
        self.price_history: List[float] = []
        self.return_history: List[float] = []
        self.regime_lookback = config.get("regime_lookback", 252)  # 1 ano

        # Hysteresis para estabilidad
        self.regime_history: List[str] = []
        self.hysteresis_count = config.get("hysteresis_count", 3)

        # Mapeo de regimen a estrategias
        self.regime_strategy_map: Dict[MarketRegime, List[str]] = {
            MarketRegime.TRENDING_UP: ["trend_following", "momentum_engine", "breakout"],
            MarketRegime.TRENDING_DOWN: ["trend_following", "momentum_engine"],
            MarketRegime.MEAN_REVERTING: ["mean_reversion_engine"],
            MarketRegime.HIGH_VOLATILITY: ["breakout"],
            MarketRegime.LOW_VOLATILITY: ["mean_reversion_engine"],
            MarketRegime.UNKNOWN: [],
        }

        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.win_rate = 0.0
        self.avg_win = Decimal("0")
        self.avg_loss = Decimal("0")

        logger.info(
            f"ProfileBasedRegimeSelector initialized: "
            f"profile={self.profile.value}, "
            f"capital={self.capital}, "
            f"max_risk={self.profile_config.max_risk_per_trade}"
        )

    def _determine_profile(self, override: Optional[str] = None) -> InvestorProfile:
        """Determinar perfil de inversor basado en capital."""
        if override:
            try:
                return InvestorProfile(override.lower())
            except ValueError:
                logger.warning(f"Invalid override profile: {override}")

        capital_float = float(self.capital)
        if capital_float < 10000:
            return InvestorProfile.SURVIVAL
        elif capital_float < 50000:
            return InvestorProfile.GROWTH
        else:
            return InvestorProfile.OPTIMIZATION

    def add_strategy(self, name: str, strategy: BaseStrategyEngine) -> None:
        """Anadir estrategia si esta habilitada para el perfil."""
        if name in self.profile_config.strategies_enabled:
            self.strategies[name] = strategy
            logger.info(f"Added strategy '{name}' for profile {self.profile.value}")
        else:
            logger.warning(
                f"Strategy '{name}' not enabled for profile {self.profile.value}. "
                f"Enabled: {self.profile_config.strategies_enabled}"
            )

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "profile_regime_selector"

    def extract_features(
        self,
        market_data: Quote,
        historical_data: Optional[Sequence[Quote]] = None,
    ) -> Dict[str, Any]:
        """Extraer features para el selector."""
        return {
            "timestamp": getattr(market_data, "timestamp", None),
            "symbol": market_data.symbol,
            "profile": self.profile.value,
            "regime": self.current_regime.value,
            "regime_confidence": self.regime_confidence,
            "hurst_exponent": self.hurst_exponent,
            "half_life": self.half_life,
            "capital": float(self.capital),
            "max_risk_per_trade": float(self.profile_config.max_risk_per_trade),
        }

    def get_required_parameters(self) -> List[str]:
        """Parametros requeridos."""
        return []

    def _generate_signals_impl(self, market_data: Quote) -> List[Signal]:
        """Generar senales basadas en perfil y regimen."""
        if not self.strategies:
            return []

        # Actualizar historial de precios
        current_price = float(market_data.close or market_data.bid or market_data.last or 0)
        if current_price > 0:
            self.price_history.append(current_price)
            if len(self.price_history) > self.regime_lookback * 2:
                self.price_history = self.price_history[-self.regime_lookback * 2 :]

        # Detectar regimen
        self._detect_regime()

        # Calcular momentum multi-ventana
        momentum_score = self._calculate_multi_window_momentum()

        # Quality screening
        if not self._quality_screen(market_data, momentum_score):
            return []

        # Seleccionar estrategias
        selected_strategies = self._select_strategies()

        # Generar senales
        signals = []
        for name in selected_strategies:
            if name in self.strategies:
                try:
                    strategy_signals = self.strategies[name].generate_signals(market_data)
                    for signal in strategy_signals:
                        # Aplicar position sizing basado en Kelly
                        enhanced_signal = self._apply_position_sizing(signal, momentum_score)
                        signals.append(enhanced_signal)
                except Exception as e:
                    logger.warning(f"Error generating signals from {name}: {e}")

        return signals

    def _detect_regime(self) -> None:
        """Detectar regimen de mercado usando Hurst exponent y half-life."""
        if len(self.price_history) < self.regime_lookback:
            self.current_regime = MarketRegime.UNKNOWN
            self.regime_confidence = 0.0
            return

        prices = np.array(self.price_history[-self.regime_lookback :])

        # Calcular Hurst exponent (Ernest Chan)
        self.hurst_exponent = self._calculate_hurst_exponent(prices)

        # Calcular half-life (Ernest Chan)
        self.half_life = self._calculate_half_life(prices)

        # Calcular volatilidad anualizada
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)

        # Detectar regimen
        detected_regime = MarketRegime.UNKNOWN
        detected_confidence = 0.0

        # Primero verificar Hurst para trending vs mean reversion
        if self.hurst_exponent is not None:
            if self.hurst_exponent > self.HURST_TRENDING_THRESHOLD:
                # Tendencia alcista o bajista
                slope = self._calculate_trend_slope(prices)
                if slope > 0:
                    detected_regime = MarketRegime.TRENDING_UP
                else:
                    detected_regime = MarketRegime.TRENDING_DOWN
                detected_confidence = ((self.hurst_exponent - 0.5) / (1.0 - 0.5)) * 100  # 0-100

            elif self.hurst_exponent < self.HURST_MEAN_REVERSION_THRESHOLD:
                # Mean reversion - verificar half-life
                if self.half_life is not None and self.half_life < self.HALF_LIFE_MAX:
                    detected_regime = MarketRegime.MEAN_REVERTING
                    detected_confidence = ((0.5 - self.hurst_exponent) / 0.5) * 100
                else:
                    # Half-life muy largo, no es mean reversion tradeable
                    detected_regime = MarketRegime.UNKNOWN

        # Verificar volatilidad si no hay tendencia clara
        if detected_regime == MarketRegime.UNKNOWN:
            if volatility > self.VOLATILITY_HIGH_THRESHOLD:
                detected_regime = MarketRegime.HIGH_VOLATILITY
                detected_confidence = min(volatility / self.VOLATILITY_HIGH_THRESHOLD, 2.0) * 50
            elif volatility < self.VOLATILITY_LOW_THRESHOLD:
                detected_regime = MarketRegime.LOW_VOLATILITY
                detected_confidence = 70.0
            else:
                detected_regime = MarketRegime.MEAN_REVERTING
                detected_confidence = 50.0

        # Aplicar hysteresis
        self.regime_history.append(detected_regime.value)
        if len(self.regime_history) > self.hysteresis_count * 2:
            self.regime_history = self.regime_history[-self.hysteresis_count * 2 :]

        if len(self.regime_history) >= self.hysteresis_count:
            recent = self.regime_history[-self.hysteresis_count :]
            if all(r == detected_regime.value for r in recent):
                self.current_regime = detected_regime
                self.regime_confidence = detected_confidence
        else:
            self.current_regime = detected_regime
            self.regime_confidence = detected_confidence

    def _calculate_hurst_exponent(self, prices: np.ndarray) -> Optional[float]:
        """
        Calcular Hurst exponent para detectar trending vs mean reversion.

        H < 0.5: Mean reverting
        H = 0.5: Random walk
        H > 0.5: Trending

        (Ernest Chan: Quantitative Trading)
        """
        try:
            lags = range(2, min(20, len(prices) // 2))
            tau = []

            for lag in lags:
                # Diferencia de precios a diferentes lags
                pp = np.subtract(prices[lag:], prices[:-lag])
                tau.append(np.std(pp))

            if len(tau) < 3:
                return None

            # Regresion log-log
            log_lags = np.log(list(lags))
            log_tau = np.log(tau)

            poly = np.polyfit(log_lags, log_tau, 1)
            hurst = poly[0]  # Pendiente = H

            return float(hurst)

        except (LinAlgError, ValueError, RuntimeError) as e:
            logger.debug(f"Error calculating Hurst exponent: {e}")
            return None

    def _calculate_half_life(self, prices: np.ndarray) -> Optional[float]:
        """
        Calcular half-life de mean reversion usando AR(1).

        Half-life < 252 dias (1 ano) es necesario para mean reversion tradeable.

        (Ernest Chan: Quantitative Trading)
        """
        try:
            # Diferencias de precios
            price_diff = np.diff(prices)
            price_lag = prices[:-1]

            # Regresion: diff = lambda * lag + epsilon
            lambda_coef = np.polyfit(price_lag, price_diff, 1)[0]

            if lambda_coef >= 0:
                # No hay mean reversion
                return None

            # Half-life = -ln(2) / lambda
            half_life = -np.log(2) / lambda_coef

            return float(half_life)

        except (LinAlgError, ValueError, ZeroDivisionError, RuntimeError) as e:
            logger.debug(f"Error calculating half-life: {e}")
            return None

    def _calculate_trend_slope(self, prices: np.ndarray) -> float:
        """Calcular pendiente de tendencia normalizada."""
        try:
            x = np.arange(len(prices))
            slope = np.polyfit(x, prices, 1)[0]
            normalized_slope = slope / np.mean(prices)
            return float(normalized_slope)
        except (LinAlgError, ValueError):
            return 0.0

    def _calculate_multi_window_momentum(self) -> float:
        """
        Calcular momentum multi-ventana (Gray & Vogel).

        Combina momentum de multiples ventanas (1m, 3m, 6m, 12m)
        con skip-month adjustment.
        """
        if len(self.price_history) < 252:
            return 0.0

        prices = np.array(self.price_history)
        signals = []

        for window in self.MOMENTUM_WINDOWS:
            if len(prices) < window + self.SKIP_MONTH_DAYS:
                continue

            # Skip-month momentum (excluir ultimo mes)
            current_price = prices[-self.SKIP_MONTH_DAYS]
            past_price = prices[-(window + self.SKIP_MONTH_DAYS)]

            if past_price <= 0:
                continue

            momentum = (current_price - past_price) / past_price

            # Normalizar por volatilidad de la ventana
            window_returns = np.diff(prices[-(window + self.SKIP_MONTH_DAYS) :])
            if len(window_returns) > 0:
                volatility = np.std(window_returns)
                if volatility > 0:
                    vol_adj_momentum = momentum / volatility
                    signals.append(vol_adj_momentum)

        if not signals:
            return 0.0

        # Promedio de senales
        combined = np.mean(signals)

        # Normalizar a [-1, 1]
        return float(np.tanh(combined * 5))

    def _quality_screen(self, market_data: Quote, momentum_score: float) -> bool:
        """
        Quality screening basado en Berkin & Swedroe.

        Para datos solo de precio, usamos:
        - Momentum positivo
        - Liquidez suficiente
        """
        # Verificar liquidez minima
        volume = getattr(market_data, "volume", 0) or 0
        if volume < 100000:  # Minimo 100k volumen
            return False

        # Para mean reversion, momentum negativo es aceptable
        if self.current_regime == MarketRegime.MEAN_REVERTING:
            return True

        # Para trending, preferimos momentum positivo
        if self.current_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if momentum_score < -0.5:
                return False

        return True

    def _select_strategies(self) -> List[str]:
        """Seleccionar estrategias basadas en regimen y perfil."""
        # Obtener estrategias preferidas para el regimen
        preferred = self.regime_strategy_map.get(self.current_regime, [])

        # Filtrar por estrategias disponibles y habilitadas para el perfil
        available = [
            s
            for s in preferred
            if s in self.strategies and s in self.profile_config.strategies_enabled
        ]

        if not available:
            # Usar todas las estrategias habilitadas para el perfil
            available = list(self.strategies.keys())

        # Limitar numero de estrategias segun perfil
        max_strategies = min(self.profile_config.max_positions, len(available))

        return available[:max_strategies]

    def _apply_position_sizing(self, signal: Signal, momentum_score: float) -> Signal:
        """
        Aplicar position sizing usando Kelly Criterion.

        Kelly = W - ((1-W)/R)
        donde W = win rate, R = avg win / avg loss

        (Ernest Chan: Algorithmic Trading)
        """
        # Calcular Kelly fraction si tenemos historial
        kelly_fraction = 1.0  # Default: full position

        if len(self.trade_history) >= 10:
            wins = [t for t in self.trade_history if t.get("pnl", 0) > 0]
            losses = [t for t in self.trade_history if t.get("pnl", 0) <= 0]

            if wins and losses:
                win_rate = len(wins) / len(self.trade_history)
                avg_win = np.mean([t["pnl"] for t in wins])
                avg_loss = abs(np.mean([t["pnl"] for t in losses]))

                if avg_loss > 0:
                    ratio = avg_win / avg_loss
                    kelly = win_rate - ((1 - win_rate) / ratio)
                    # Usar half-Kelly para ser conservador
                    kelly_fraction = max(0.25, min(1.0, kelly * 0.5))

        # Calcular tamano de posicion
        base_position = float(self.profile_config.max_position_size)
        adjusted_position = base_position * kelly_fraction

        # Reducir si momentum es debil
        if abs(momentum_score) < 0.3:
            adjusted_position *= 0.7

        # Asegurar que no excede maximo del perfil
        adjusted_position = min(adjusted_position, float(self.profile_config.max_position_size))

        # Crear metadata mejorada
        enhanced_metadata = signal.metadata.copy() if signal.metadata else {}
        enhanced_metadata.update(
            {
                "profile": self.profile.value,
                "regime": self.current_regime.value,
                "regime_confidence": self.regime_confidence,
                "hurst_exponent": self.hurst_exponent,
                "momentum_score": momentum_score,
                "kelly_fraction": kelly_fraction,
                "position_size": adjusted_position,
                "max_risk_per_trade": float(self.profile_config.max_risk_per_trade),
                "stop_loss": float(self.profile_config.default_stop_loss),
                "take_profit": float(self.profile_config.default_take_profit),
            }
        )

        # Ajustar confianza basada en regimen
        confidence_adjustment = self.regime_confidence / 100.0
        adjusted_confidence = signal.confidence * confidence_adjustment

        # Import enum types for proper Signal creation
        from app.domain.models.signal import SignalSource, SignalStrength, SignalType

        # Ensure enum types are used (signal model has use_enum_values=True, so we get strings)
        signal_type = signal.signal_type
        if isinstance(signal_type, str):
            signal_type = SignalType(signal_type)

        strength = signal.strength
        if isinstance(strength, str):
            strength = SignalStrength(strength)

        source = signal.source
        if isinstance(source, str):
            source = SignalSource(source)

        return Signal(
            symbol=signal.symbol,
            signal_type=signal_type,
            strength=strength,
            price=signal.price,
            timestamp=signal.timestamp,
            confidence=min(100.0, adjusted_confidence),
            liquidity_score=signal.liquidity_score,
            priority_score=signal.priority_score,
            source=source,
            volume=signal.volume,
            metadata=enhanced_metadata,
        )

    def risk_check(self, signal: Signal, portfolio: Any) -> bool:
        """
        Verificar criterios de riesgo basados en perfil.

        Incluye:
        - Max risk per trade (Ernest Chan: 2%)
        - Max position size (Markowitz: 20%)
        - Max positions (por perfil)
        """
        # Verificar confianza minima
        min_confidence = 30.0
        if signal.confidence < min_confidence:
            logger.debug(f"Signal confidence {signal.confidence} below minimum {min_confidence}")
            return False

        # Verificar position size
        position_size = signal.metadata.get("position_size", 0.10)
        if position_size > float(self.profile_config.max_position_size):
            logger.debug(
                f"Position size {position_size} exceeds max "
                f"{self.profile_config.max_position_size}"
            )
            return False

        # Verificar riesgo por trade
        risk_per_trade = signal.metadata.get("max_risk_per_trade", 0.02)
        if risk_per_trade > float(self.profile_config.max_risk_per_trade):
            logger.debug(
                f"Risk per trade {risk_per_trade} exceeds max "
                f"{self.profile_config.max_risk_per_trade}"
            )
            return False

        # Verificar con estrategia individual si disponible
        strategy_name = signal.metadata.get("selected_strategy")
        if strategy_name and strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
            try:
                return strategy.risk_check(signal, portfolio)
            except Exception:
                pass

        return True

    def update_trade_result(self, trade_result: Dict[str, Any]) -> None:
        """Actualizar historial de trades para Kelly Criterion."""
        self.trade_history.append(trade_result)

        # Mantener solo ultimos 100 trades
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]

        # Recalcular win rate y promedios
        if self.trade_history:
            wins = [t for t in self.trade_history if t.get("pnl", 0) > 0]
            self.win_rate = len(wins) / len(self.trade_history)

            if wins:
                self.avg_win = Decimal(str(np.mean([t["pnl"] for t in wins])))
            losses = [t for t in self.trade_history if t.get("pnl", 0) <= 0]
            if losses:
                self.avg_loss = Decimal(str(abs(np.mean([t["pnl"] for t in losses]))))

    def get_current_regime(self) -> Tuple[MarketRegime, float]:
        """Obtener regimen actual y confianza."""
        return self.current_regime, self.regime_confidence

    def get_profile_config(self) -> ProfileConfig:
        """Obtener configuracion del perfil actual."""
        return self.profile_config

    def get_strategy_weights(self) -> Dict[str, float]:
        """Obtener pesos de estrategias (para compatibilidad con BaseStrategyEnsemble)."""
        return {name: 1.0 for name in self.strategies}
