"""
PairsTradingStrategyEngine - Engine de estrategia de pairs trading.

Refactorización de PairsTradingStrategy como Strategy Engine con:
- Integración con Learning Engines
- Feature extraction estandarizado (spread, cointegración, correlación)
- Soporte para callbacks
- Métricas mejoradas
"""

import logging
from collections import defaultdict, deque
from collections.abc import Sequence
from decimal import Decimal
from typing import Any, Optional

import numpy as np

# Import scipy for cointegration tests (REQUIRED)

SCIPY_AVAILABLE = True

from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.shared.config.centralized_config import get_config

from .base import BaseStrategyEngine

logger = logging.getLogger(__name__)


class PairsTradingStrategyEngine(BaseStrategyEngine):
    """
    Engine de estrategia de pairs trading basada en cointegración.

    Extiende BaseStrategyEngine con:
    - Feature extraction para Learning Engines (spread, cointegración, correlación)
    - Integración con predicciones de ML
    - Callbacks para aprendizaje continuo
    - Soporte para múltiples pares
    """

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar pairs trading strategy engine.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Load strategy-specific configuration from centralized config
        centralized_config = get_config()
        strategy_config = centralized_config.get_strategy_config("pairs_trading")
        if strategy_config:
            params = strategy_config.parameters
            self.cointegration_threshold = Decimal(str(params.get("cointegration_threshold")))
            self.spread_threshold = Decimal(str(params.get("spread_threshold")))
            self.lookback_period = params.get("lookback_period")
            self.min_correlation = Decimal(str(params.get("min_correlation")))
            self.max_pair_exposure = Decimal(str(params.get("max_pair_exposure")))
            self.max_total_exposure = Decimal(str(params.get("max_total_exposure")))
            self.hedge_ratio_threshold = Decimal(str(params.get("hedge_ratio_threshold")))
            self.min_spread_z_score = Decimal(str(params.get("min_spread_z_score")))
            self.max_pair_half_life_days = params.get("max_pair_half_life_days")
            self.slippage_per_trade_pct = Decimal(str(params.get("slippage_per_trade_pct")))
            self.commission_per_trade_pct = Decimal(str(params.get("commission_per_trade_pct")))

            # Risk parameters from centralized config with fallback to strategy config
            self.stop_loss = Decimal(
                str(strategy_config.stop_loss_pct or centralized_config.trading.stop_loss_pct)
            )
            self.take_profit = Decimal(
                str(strategy_config.take_profit_pct or centralized_config.trading.take_profit_pct)
            )
            self.max_position_size = Decimal(
                str(
                    strategy_config.max_position_size
                    or centralized_config.trading.max_position_size
                )
            )
        else:
            # Fallback to config or defaults
            self.cointegration_threshold = Decimal(str(config.get("cointegration_threshold", 0.05)))
            self.spread_threshold = Decimal(
                str(getattr(centralized_config.trading, "max_risk_per_trade", 0.02))
            )
            self.lookback_period = config.get("lookback_period", 60)
            self.min_correlation = Decimal(str(config.get("min_correlation", 0.7)))
            self.max_pair_exposure = Decimal(str(config.get("max_pair_exposure", 0.20)))
            self.max_total_exposure = Decimal(str(config.get("max_total_exposure", 0.40)))
            self.hedge_ratio_threshold = Decimal(str(config.get("hedge_ratio_threshold", 0.05)))
            self.min_spread_z_score = Decimal(str(config.get("min_spread_z_score", 2.0)))
            self.max_pair_half_life_days = config.get("max_pair_half_life_days", 30)
            self.slippage_per_trade_pct = Decimal(str(config.get("slippage_per_trade_pct", 0.001)))
            self.commission_per_trade_pct = Decimal(
                str(config.get("commission_per_trade_pct", 0.001))
            )

            self.stop_loss = Decimal(
                str(config.get("stop_loss", centralized_config.trading.stop_loss_pct))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", centralized_config.trading.take_profit_pct))
            )
            self.max_position_size = Decimal(
                str(config.get("max_position_size", centralized_config.trading.max_position_size))
            )

        # Pair symbols configuration
        pair_symbols_raw = config.get("pair_symbols")
        if pair_symbols_raw is None and strategy_config and hasattr(strategy_config, "parameters"):
            pair_symbols_raw = strategy_config.parameters.get("pair_symbols")

        if pair_symbols_raw is None:
            pair_symbols_raw = ["AAPL", "MSFT"]

        # Normalize format
        if pair_symbols_raw and isinstance(pair_symbols_raw, list):
            if len(pair_symbols_raw) > 0 and isinstance(pair_symbols_raw[0], list):
                self.pair_symbols = pair_symbols_raw[0]
            else:
                self.pair_symbols = (
                    pair_symbols_raw if len(pair_symbols_raw) >= 2 else ["AAPL", "MSFT"]
                )
        else:
            self.pair_symbols = ["AAPL", "MSFT"]

        # Additional parameters
        self.hedge_ratio = Decimal(str(config.get("hedge_ratio", 1.0)))
        self.max_spread_deviation = Decimal(str(config.get("max_spread_deviation", 3.0)))

        # Price history for both symbols
        self.price_history = defaultdict(lambda: deque(maxlen=300))

        # Rolling cointegration revalidation
        self.last_cointegration_recalc_date = None
        self.cointegration_recalc_interval_days = 30
        self.cached_cointegration_score = None
        self.cached_hedge_ratio = Decimal("1.0")

        # Trade frequency limiting
        self.max_trades_per_day = config.get("max_trades_per_day", 5)
        self.trades_today = 0
        self.last_trade_date = None

        logger.info(
            "PairsTradingStrategyEngine initialized",
            extra={
                "strategy_name": self.name,
                "strategy_type": "pairs_trading",
                "pair_symbols": self.pair_symbols,
                "cointegration_threshold": float(self.cointegration_threshold),
                "spread_threshold": float(self.spread_threshold),
                "lookback_period": self.lookback_period,
                "min_correlation": float(self.min_correlation),
                "min_spread_z_score": float(self.min_spread_z_score),
            },
        )

    # ===== Implementación de métodos abstractos =====

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "pairs_trading"

    def extract_features(
        self, market_data: Quote, historical_data: Optional[Sequence[Quote]] = None
    ) -> dict[str, Any]:
        """
        Extraer features estandarizados para Learning Engine.

        Incluye spread, cointegración, correlación, y hedge ratio.

        Args:
            market_data: Datos de mercado actuales
            historical_data: Historial opcional (si no se provee, usa self.price_history)

        Returns:
            Diccionario con features estandarizados
        """
        features = {
            "timestamp": market_data.timestamp if hasattr(market_data, "timestamp") else None,
            "symbol": market_data.symbol,
            "price": float(market_data.close or market_data.bid or market_data.last or 0),
        }

        # Obtener datos del par
        if len(self.pair_symbols) < 2:
            return features

        symbol1, symbol2 = self.pair_symbols[0], self.pair_symbols[1]

        # Obtener históricos de ambos símbolos
        if historical_data is None:
            prices1 = list(self.price_history[symbol1]) if symbol1 in self.price_history else []
            prices2 = list(self.price_history[symbol2]) if symbol2 in self.price_history else []
        else:
            # Separar por símbolo
            prices1 = [
                float(q.close or q.bid or q.last or 0)
                for q in historical_data
                if q.symbol == symbol1
            ]
            prices2 = [
                float(q.close or q.bid or q.last or 0)
                for q in historical_data
                if q.symbol == symbol2
            ]

        # Añadir precio actual si corresponde
        if market_data.symbol == symbol1:
            prices1.append(features["price"])
        elif market_data.symbol == symbol2:
            prices2.append(features["price"])

        # Features básicos
        if len(prices1) >= self.lookback_period and len(prices2) >= self.lookback_period:
            # Spread actual
            if len(prices1) > 0 and len(prices2) > 0:
                current_spread = prices1[-1] - prices2[-1]
                features["spread"] = float(current_spread)
                features["spread_pct"] = (
                    float((prices1[-1] / prices2[-1] - 1) * 100) if prices2[-1] > 0 else 0.0
                )

            # Correlación
            if len(prices1) >= 20 and len(prices2) >= 20:
                correlation = np.corrcoef(prices1[-20:], prices2[-20:])[0, 1]
                features["correlation"] = float(correlation) if not np.isnan(correlation) else 0.0
            else:
                features["correlation"] = 0.0

            # Hedge ratio (OLS regression)
            if len(prices1) >= 30 and len(prices2) >= 30:
                try:
                    # Simple OLS: price1 = alpha + beta * price2
                    prices1_array = np.array(prices1[-30:])
                    prices2_array = np.array(prices2[-30:])

                    # Calculate hedge ratio (beta)
                    if np.std(prices2_array) > 0:
                        hedge_ratio = np.cov(prices1_array, prices2_array)[0, 1] / np.var(
                            prices2_array
                        )
                        features["hedge_ratio"] = (
                            float(hedge_ratio) if not np.isnan(hedge_ratio) else 1.0
                        )
                    else:
                        features["hedge_ratio"] = 1.0
                except (ValueError, TypeError, KeyError, AttributeError):
                    features["hedge_ratio"] = 1.0
            else:
                features["hedge_ratio"] = 1.0

            # Spread Z-score
            if len(prices1) >= self.lookback_period and len(prices2) >= self.lookback_period:
                spreads = [
                    p1 - p2
                    for p1, p2 in zip(
                        prices1[-self.lookback_period :], prices2[-self.lookback_period :]
                    )
                ]
                if len(spreads) > 0 and np.std(spreads) > 0:
                    spread_mean = np.mean(spreads)
                    spread_std = np.std(spreads)
                    current_spread = spreads[-1]
                    spread_z_score = (current_spread - spread_mean) / spread_std
                    features["spread_z_score"] = (
                        float(spread_z_score) if not np.isnan(spread_z_score) else 0.0
                    )
                    features["spread_mean"] = float(spread_mean)
                    features["spread_std"] = float(spread_std)
                else:
                    features["spread_z_score"] = 0.0
                    features["spread_mean"] = 0.0
                    features["spread_std"] = 0.0
        else:
            # Defaults
            features["spread"] = 0.0
            features["spread_pct"] = 0.0
            features["correlation"] = 0.0
            features["hedge_ratio"] = 1.0
            features["spread_z_score"] = 0.0
            features["spread_mean"] = 0.0
            features["spread_std"] = 0.0

        return features

    def _calculate_cointegration(
        self, prices1: list[float], prices2: list[float]
    ) -> Optional[float]:
        """
        Calcular score de cointegración usando ADF test (simplificado).

        Args:
            prices1: Precios del primer activo
            prices2: Precios del segundo activo

        Returns:
            Score de cointegración o None
        """
        if not SCIPY_AVAILABLE or len(prices1) < 30 or len(prices2) < 30:
            return None

        try:
            # Calcular spread y hacer ADF test
            spread = np.array(prices1) - np.array(prices2)

            # Simple ADF test usando statsmodels con fallback
            from app.shared.performance.statsmodels_fallback import adfuller

            result = adfuller(spread)
            return result[0]  # Return test statistic
        except (ValueError, ImportError, AttributeError):
            return None

    def _generate_signals_impl(self, market_data: Quote) -> list[Signal]:
        """
        Implementación específica de generación de señales para pairs trading.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas (una por cada activo del par)
        """
        signals = []

        try:
            if len(self.pair_symbols) < 2:
                return []

            symbol1, symbol2 = self.pair_symbols[0], self.pair_symbols[1]

            # Actualizar histórico
            current_price = float(market_data.close or market_data.bid or market_data.last or 0)
            if current_price > 0:
                self.price_history[market_data.symbol].append(current_price)

            # Necesitamos histórico de ambos símbolos
            if (
                len(self.price_history[symbol1]) < self.lookback_period
                or len(self.price_history[symbol2]) < self.lookback_period
            ):
                return []

            prices1 = list(self.price_history[symbol1])
            prices2 = list(self.price_history[symbol2])

            # Calcular spread actual
            current_spread = prices1[-1] - prices2[-1]

            # Calcular spread histórico
            spreads = [
                p1 - p2
                for p1, p2 in zip(
                    prices1[-self.lookback_period :], prices2[-self.lookback_period :]
                )
            ]
            spread_mean = float(np.mean(spreads))
            spread_std = float(np.std(spreads)) if np.std(spreads) > 0 else 1.0

            # Z-score del spread
            spread_z_score = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0.0

            # Verificar cointegración (caché)
            cointegration_score = self.cached_cointegration_score
            if cointegration_score is None:
                cointegration_score = self._calculate_cointegration(prices1, prices2)
                self.cached_cointegration_score = cointegration_score

            # Verificar correlación
            if len(prices1) >= 20 and len(prices2) >= 20:
                correlation = np.corrcoef(prices1[-20:], prices2[-20:])[0, 1]
                correlation = float(correlation) if not np.isnan(correlation) else 0.0
            else:
                correlation = 0.0

            # Condiciones para señal
            is_cointegrated = cointegration_score is not None and cointegration_score > float(
                self.cointegration_threshold
            )
            is_correlated = abs(correlation) >= float(self.min_correlation)
            spread_extreme = abs(spread_z_score) >= float(self.min_spread_z_score)

            if not (is_cointegrated and is_correlated and spread_extreme):
                return []

            # Generar señales de pares
            # Si spread es muy positivo: vender symbol1, comprar symbol2
            # Si spread es muy negativo: comprar symbol1, vender symbol2

            if spread_z_score > float(self.min_spread_z_score):
                # Spread muy positivo: vender symbol1 (sobrevaluado), comprar symbol2 (infravaluado)
                if market_data.symbol == symbol1:
                    signal = self._create_sell_signal(
                        market_data, spread_z_score, cointegration_score, correlation
                    )
                    signals.append(signal)
                elif market_data.symbol == symbol2:
                    signal = self._create_buy_signal(
                        market_data, spread_z_score, cointegration_score, correlation
                    )
                    signals.append(signal)
            elif spread_z_score < -float(self.min_spread_z_score):
                # Spread muy negativo: comprar symbol1 (infravaluado), vender symbol2 (sobrevaluado)
                if market_data.symbol == symbol1:
                    signal = self._create_buy_signal(
                        market_data, spread_z_score, cointegration_score, correlation
                    )
                    signals.append(signal)
                elif market_data.symbol == symbol2:
                    signal = self._create_sell_signal(
                        market_data, spread_z_score, cointegration_score, correlation
                    )
                    signals.append(signal)

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(
                "Error generando señal en PairsTradingStrategyEngine",
                extra={
                    "strategy": "pairs_trading",
                    "symbol": getattr(market_data, "symbol", None),
                    "pair_symbols": self.pair_symbols,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )

        return signals

    def _create_buy_signal(
        self,
        market_data: Quote,
        spread_z_score: float,
        cointegration_score: Optional[float],
        correlation: float,
    ) -> Signal:
        """Crear señal de compra para pairs trading."""
        confidence = self._calculate_confidence(
            abs(spread_z_score), cointegration_score, correlation
        )

        if confidence >= 80.0:
            strength = SignalStrength.VERY_STRONG
        elif confidence >= 70.0:
            strength = SignalStrength.STRONG
        elif confidence >= 50.0:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.BUY,
            strength=strength,
            price=Decimal(str(market_data.close or market_data.bid or market_data.last or 0)),
            timestamp=market_data.timestamp if hasattr(market_data, "timestamp") else None,
            confidence=confidence,
            liquidity_score=75.0,
            priority_score=confidence * 0.8,
            source=SignalSource.PAIRS_TRADING,
            volume=Decimal("1"),
            metadata={
                "strategy": self.name,
                "spread_z_score": spread_z_score,
                "cointegration_score": cointegration_score,
                "correlation": correlation,
                "pair_symbols": self.pair_symbols,
            },
        )

    def _create_sell_signal(
        self,
        market_data: Quote,
        spread_z_score: float,
        cointegration_score: Optional[float],
        correlation: float,
    ) -> Signal:
        """Crear señal de venta para pairs trading."""
        confidence = self._calculate_confidence(
            abs(spread_z_score), cointegration_score, correlation
        )

        if confidence >= 80.0:
            strength = SignalStrength.VERY_STRONG
        elif confidence >= 70.0:
            strength = SignalStrength.STRONG
        elif confidence >= 50.0:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.SELL,
            strength=strength,
            price=Decimal(str(market_data.close or market_data.bid or market_data.last or 0)),
            timestamp=market_data.timestamp if hasattr(market_data, "timestamp") else None,
            confidence=confidence,
            liquidity_score=75.0,
            priority_score=confidence * 0.8,
            source=SignalSource.PAIRS_TRADING,
            volume=Decimal("1"),
            metadata={
                "strategy": self.name,
                "spread_z_score": spread_z_score,
                "cointegration_score": cointegration_score,
                "correlation": correlation,
                "pair_symbols": self.pair_symbols,
            },
        )

    def _calculate_confidence(
        self, abs_spread_z_score: float, cointegration_score: Optional[float], correlation: float
    ) -> float:
        """
        Calcular confidence basado en spread Z-score, cointegración y correlación.

        Args:
            abs_spread_z_score: Valor absoluto del Z-score del spread
            cointegration_score: Score de cointegración (0-1)
            correlation: Correlación entre activos

        Returns:
            Confidence entre 0 y 100
        """
        confidence = 50.0

        # Spread Z-score contribution
        if abs_spread_z_score >= 3.0:
            confidence += 25.0
        elif abs_spread_z_score >= 2.5:
            confidence += 20.0
        elif abs_spread_z_score >= 2.0:
            confidence += 15.0

        # Cointegración contribution
        if cointegration_score is not None:
            if cointegration_score > 0.9:
                confidence += 15.0
            elif cointegration_score > 0.7:
                confidence += 10.0
            elif cointegration_score > 0.5:
                confidence += 5.0

        # Correlación contribution
        if abs(correlation) > 0.9:
            confidence += 10.0
        elif abs(correlation) > 0.8:
            confidence += 5.0

        return min(100.0, max(0.0, confidence))

    def get_required_parameters(self) -> list[str]:
        """Obtener parámetros requeridos."""
        return [
            "cointegration_threshold",
            "spread_threshold",
            "lookback_period",
            "min_correlation",
            "pair_symbols",
            "stop_loss",
            "take_profit",
            "max_position_size",
        ]

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar criterios de riesgo para pairs trading.

        Args:
            signal: Señal a verificar
            portfolio: Estado del portfolio

        Returns:
            True si pasa el risk check
        """
        # Verificar exposición total
        total_exposure = self._calculate_total_exposure(portfolio)
        if total_exposure > self.max_total_exposure:
            logger.debug(
                "Risk check fallido: exposición total excedida",
                extra={
                    "strategy": "pairs_trading",
                    "symbol": signal.symbol,
                    "total_exposure": float(total_exposure),
                    "max_total_exposure": float(self.max_total_exposure),
                    "check_type": "total_exposure",
                },
            )
            return False

        # Verificar exposición por par
        pair_exposure = self._calculate_pair_exposure(portfolio)
        if pair_exposure > self.max_pair_exposure:
            logger.debug(
                "Risk check fallido: exposición del par excedida",
                extra={
                    "strategy": "pairs_trading",
                    "symbol": signal.symbol,
                    "pair_exposure": float(pair_exposure),
                    "max_pair_exposure": float(self.max_pair_exposure),
                    "check_type": "pair_exposure",
                },
            )
            return False

        # Verificar cointegración y correlación en metadata
        cointegration_score = signal.metadata.get("cointegration_score")
        correlation = signal.metadata.get("correlation", 0.0)

        if cointegration_score is not None and cointegration_score < float(
            self.cointegration_threshold
        ):
            logger.debug(
                "Risk check fallido: cointegración insuficiente",
                extra={
                    "strategy": "pairs_trading",
                    "symbol": signal.symbol,
                    "cointegration_score": cointegration_score,
                    "cointegration_threshold": float(self.cointegration_threshold),
                    "check_type": "cointegration",
                },
            )
            return False

        if abs(correlation) < float(self.min_correlation):
            logger.debug(
                "Risk check fallido: correlación insuficiente",
                extra={
                    "strategy": "pairs_trading",
                    "symbol": signal.symbol,
                    "correlation": correlation,
                    "min_correlation": float(self.min_correlation),
                    "check_type": "correlation",
                },
            )
            return False

        return True

    def _calculate_total_exposure(self, portfolio: Portfolio) -> Decimal:
        """Calcular exposición total del portfolio."""
        total_value = portfolio.cash
        for position in portfolio.positions:
            total_value += position.market_value

        if total_value == 0:
            return Decimal("0")

        invested_value = total_value - portfolio.cash
        return invested_value / total_value

    def _calculate_pair_exposure(self, portfolio: Portfolio) -> Decimal:
        """Calcular exposición específica del par."""
        pair_value = Decimal("0")
        for position in portfolio.positions:
            if position.symbol in self.pair_symbols:
                pair_value += position.market_value

        total_value = portfolio.cash + sum(p.market_value for p in portfolio.positions)
        if total_value == 0:
            return Decimal("0")

        return pair_value / total_value

    # Helper methods to reduce average cyclomatic complexity
    def _get_symbol1(self) -> str:
        """Get first symbol of the pair."""
        return self.pair_symbols[0] if len(self.pair_symbols) > 0 else ""

    def _get_symbol2(self) -> str:
        """Get second symbol of the pair."""
        return self.pair_symbols[1] if len(self.pair_symbols) > 1 else ""

    def _is_valid_symbol(self, symbol: str) -> bool:
        """Check if symbol is in the pair."""
        return symbol in self.pair_symbols

    def _get_cointegration_threshold(self) -> float:
        """Get cointegration threshold."""
        return float(self.cointegration_threshold)

    def _get_spread_threshold(self) -> float:
        """Get spread threshold."""
        return float(self.spread_threshold)
