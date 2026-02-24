"""
ArbitrageStrategyEngine - Engine de estrategia de arbitraje.

Implementa estrategias de arbitraje incluyendo:
- Arbitraje estadistico (statistical arbitrage)
- Spread trading (diferencias de precio entre activos relacionados)
- Carry trades (diferencias en tasas de interes/rendimiento)

Caracteristicas principales:
- Deteccion de desviaciones de precio vs valor justo
- Calculo de spreads y z-scores dinamicos
- Soporte para multiples pares/grupos de activos
- Integracion con Learning Engines para ajustes dinamicos
- Gestion de riesgo especifica para arbitraje
"""

import logging
from collections import defaultdict, deque
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from app.shared.config.centralized_config import get_config
from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.services.analysis.momentum import TechnicalIndicatorCalculator

from .base import BaseStrategyEngine

logger = logging.getLogger(__name__)


class ArbitrageStrategyEngine(BaseStrategyEngine):
    """
    Engine de estrategia de arbitraje.

    Soporta multiples tipos de arbitraje:
    1. Statistical Arbitrage: Explota reversiones a la media en spreads
    2. Spread Trading: Opera diferencias de precio entre activos correlacionados
    3. Carry Trade: Aprovecha diferencias en tasas de interes/rendimiento

    La estrategia monitorea spreads entre activos y genera senales cuando
    el spread se desvia significativamente de su valor justo historico.
    """

    # Tipos de arbitraje soportados
    ARBITRAGE_TYPE_STATISTICAL = "statistical"
    ARBITRAGE_TYPE_SPREAD = "spread"
    ARBITRAGE_TYPE_CARRY = "carry"

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar ArbitrageStrategyEngine.

        Args:
            config: Configuracion de la estrategia
        """
        super().__init__(config)

        # Initialize all parameters with defaults FIRST
        self.arbitrage_type: str = config.get("arbitrage_type", self.ARBITRAGE_TYPE_STATISTICAL)
        self.lookback_period: int = int(config.get("lookback_period", 60))
        self.entry_z_score: Decimal = Decimal(str(config.get("entry_z_score", 2.0)))
        self.exit_z_score: Decimal = Decimal(str(config.get("exit_z_score", 0.5)))
        self.min_spread_pct: Decimal = Decimal(str(config.get("min_spread_pct", 0.005)))
        self.max_spread_pct: Decimal = Decimal(str(config.get("max_spread_pct", 0.10)))
        self.min_correlation: Decimal = Decimal(str(config.get("min_correlation", 0.70)))
        self.max_exposure: Decimal = Decimal(str(config.get("max_exposure", 0.40)))
        self.max_position_per_leg: Decimal = Decimal(str(config.get("max_position_per_leg", 0.15)))
        self.min_signal_confidence: float = float(config.get("min_signal_confidence", 60.0))

        # Carry trade specific parameters
        self.carry_yield_threshold: Decimal = Decimal(
            str(config.get("carry_yield_threshold", 0.02))
        )
        self.funding_rate_threshold: Decimal = Decimal(
            str(config.get("funding_rate_threshold", 0.0001))
        )

        # Risk parameters from centralized config with fallback to local config
        centralized_config = get_config()
        self.stop_loss = Decimal(str(config.get("stop_loss", centralized_config.trading.stop_loss_pct)))
        self.take_profit = Decimal(str(config.get("take_profit", centralized_config.trading.take_profit_pct)))
        self.max_position_size = Decimal(str(config.get("max_position_size", centralized_config.trading.max_position_size)))

        # Load strategy-specific configuration from centralized config
        strategy_config = centralized_config.get_strategy_config("arbitrage")
        if strategy_config:
            params = strategy_config.parameters
            if isinstance(params, dict):
                try:
                    self.config.update({k: v for k, v in params.items() if v is not None})
                    config.update({k: v for k, v in params.items() if v is not None})
                except (ValueError, TypeError, KeyError, AttributeError):
                    pass

                # Override defaults with YAML values
                if "arbitrage_type" in params:
                    self.arbitrage_type = params.get("arbitrage_type", self.arbitrage_type)
                if "lookback_period" in params:
                    self.lookback_period = int(params.get("lookback_period", self.lookback_period))
                if "entry_z_score" in params:
                    self.entry_z_score = Decimal(
                        str(params.get("entry_z_score", self.entry_z_score))
                    )
                if "exit_z_score" in params:
                    self.exit_z_score = Decimal(str(params.get("exit_z_score", self.exit_z_score)))
                if "min_spread_pct" in params:
                    self.min_spread_pct = Decimal(
                        str(params.get("min_spread_pct", self.min_spread_pct))
                    )
                if "max_spread_pct" in params:
                    self.max_spread_pct = Decimal(
                        str(params.get("max_spread_pct", self.max_spread_pct))
                    )
                if "min_correlation" in params:
                    self.min_correlation = Decimal(
                        str(params.get("min_correlation", self.min_correlation))
                    )
                if "max_exposure" in params:
                    self.max_exposure = Decimal(str(params.get("max_exposure", self.max_exposure)))
                if "max_position_per_leg" in params:
                    self.max_position_per_leg = Decimal(
                        str(params.get("max_position_per_leg", self.max_position_per_leg))
                    )
                if "min_signal_confidence" in params:
                    self.min_signal_confidence = float(
                        params.get("min_signal_confidence", self.min_signal_confidence)
                    )
                if "carry_yield_threshold" in params:
                    self.carry_yield_threshold = Decimal(
                        str(params.get("carry_yield_threshold", self.carry_yield_threshold))
                    )
                if "funding_rate_threshold" in params:
                    self.funding_rate_threshold = Decimal(
                        str(params.get("funding_rate_threshold", self.funding_rate_threshold))
                    )

            # Risk parameters from centralized config with fallback to strategy config
            self.stop_loss = Decimal(
                str(strategy_config.stop_loss_pct or centralized_config.trading.stop_loss_pct)
            )
            self.take_profit = Decimal(
                str(strategy_config.take_profit_pct or centralized_config.trading.take_profit_pct)
            )
            self.max_position_size = Decimal(
                str(strategy_config.max_position_size or centralized_config.trading.max_position_size)
            )

        # Arbitrage pairs configuration
        arbitrage_pairs_raw = config.get("arbitrage_pairs")
        if arbitrage_pairs_raw is None and strategy_config:
            if hasattr(strategy_config, 'parameters'):
                arbitrage_pairs_raw = strategy_config.parameters.get("arbitrage_pairs")

        if arbitrage_pairs_raw is None:
            # Default pairs for different arbitrage types
            arbitrage_pairs_raw = [
                ["SPY", "IVV"],  # S&P 500 ETF arbitrage
                ["GLD", "IAU"],  # Gold ETF arbitrage
                ["QQQ", "TQQQ"],  # Nasdaq ETF/leveraged
            ]

        self.arbitrage_pairs: List[List[str]] = arbitrage_pairs_raw

        # Price history for each symbol
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=300))
        self.volume_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=300))

        # Spread tracking for each pair
        self.spread_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=300))

        # Carry trade data (yield/funding rates)
        self.yield_data: Dict[str, float] = {}
        self.funding_rates: Dict[str, float] = {}

        # Active positions tracking
        self.active_arbitrage_positions: Dict[str, Dict[str, Any]] = {}

        # Technical indicator calculator
        self.indicator_calculator = TechnicalIndicatorCalculator()

        # Trade limits
        self.max_trades_per_day = config.get("max_trades_per_day", 10)
        self.trades_today = 0
        self.last_trade_date = None

        logger.info(f"ArbitrageStrategyEngine initialized: {self.name}")
        logger.info(f"Arbitrage type: {self.arbitrage_type}")
        logger.info(f"Arbitrage pairs: {self.arbitrage_pairs}")

    # ===== Implementation of abstract methods =====

    def get_strategy_type(self) -> str:
        """Obtener tipo de estrategia."""
        return "arbitrage"

    def extract_features(
        self,
        market_data: Quote,
        historical_data: Optional[Sequence[Quote]] = None,
    ) -> Dict[str, Any]:
        """
        Extraer features estandarizados para Learning Engine.

        Features principales:
        - spread / spread_pct para cada par
        - spread_z_score para cada par
        - correlation entre activos
        - volatility del spread
        - half_life del spread (mean reversion speed)

        Args:
            market_data: Datos de mercado actuales
            historical_data: Historial opcional

        Returns:
            Diccionario con features estandarizados
        """
        features: Dict[str, Any] = {
            "timestamp": getattr(market_data, "timestamp", None),
            "symbol": market_data.symbol,
            "price": float(market_data.close or market_data.bid or market_data.last or 0),
            "arbitrage_type": self.arbitrage_type,
        }

        current_symbol = market_data.symbol

        # Find which pair this symbol belongs to
        pair_found = None
        other_symbol = None
        for pair in self.arbitrage_pairs:
            if current_symbol in pair:
                pair_found = pair
                other_symbol = pair[1] if pair[0] == current_symbol else pair[0]
                break

        if pair_found is None:
            return features

        features["pair"] = pair_found
        features["other_symbol"] = other_symbol

        # Get price histories
        prices_current = list(self.price_history.get(current_symbol, []))
        prices_other = list(self.price_history.get(other_symbol, []))

        # Add current price
        prices_current_with_current = prices_current + [features["price"]]

        if (
            len(prices_current_with_current) >= self.lookback_period
            and len(prices_other) >= self.lookback_period
        ):
            # Align lengths
            min_len = min(len(prices_current_with_current), len(prices_other))
            p1 = prices_current_with_current[-min_len:]
            p2 = prices_other[-min_len:]

            # Calculate spread metrics
            spreads = [a - b for a, b in zip(p1, p2)]
            spread_pcts = [(a / b - 1) if b > 0 else 0 for a, b in zip(p1, p2)]

            current_spread = spreads[-1]
            current_spread_pct = spread_pcts[-1]

            # Spread statistics
            spread_mean = float(np.mean(spreads))
            spread_std = float(np.std(spreads)) if np.std(spreads) > 0 else 1e-8
            spread_z_score = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0.0

            features.update(
                {
                    "spread": float(current_spread),
                    "spread_pct": float(current_spread_pct * 100),
                    "spread_mean": spread_mean,
                    "spread_std": spread_std,
                    "spread_z_score": float(spread_z_score),
                }
            )

            # Correlation
            if len(p1) >= 20 and len(p2) >= 20:
                correlation = float(np.corrcoef(p1[-20:], p2[-20:])[0, 1])
                features["correlation"] = correlation if not np.isnan(correlation) else 0.0
            else:
                features["correlation"] = 0.0

            # Spread volatility (rolling std)
            if len(spreads) >= 20:
                spread_volatility = float(np.std(spreads[-20:]))
                features["spread_volatility"] = spread_volatility
            else:
                features["spread_volatility"] = 0.0

            # Half-life estimation (mean reversion speed)
            half_life = self._estimate_half_life(spreads)
            features["half_life_days"] = half_life if half_life is not None else 0.0

            # Relative spread position (0-1 scale within recent range)
            recent_spreads = spreads[-self.lookback_period :]
            spread_min = min(recent_spreads)
            spread_max = max(recent_spreads)
            spread_range = spread_max - spread_min
            if spread_range > 0:
                relative_position = (current_spread - spread_min) / spread_range
                features["relative_spread_position"] = float(relative_position)
            else:
                features["relative_spread_position"] = 0.5

        else:
            # Defaults when not enough history
            features.update(
                {
                    "spread": 0.0,
                    "spread_pct": 0.0,
                    "spread_mean": 0.0,
                    "spread_std": 0.0,
                    "spread_z_score": 0.0,
                    "correlation": 0.0,
                    "spread_volatility": 0.0,
                    "half_life_days": 0.0,
                    "relative_spread_position": 0.5,
                }
            )

        # Carry trade features (if applicable)
        if self.arbitrage_type == self.ARBITRAGE_TYPE_CARRY:
            yield_current = self.yield_data.get(current_symbol, 0.0)
            yield_other = self.yield_data.get(other_symbol, 0.0)
            features["yield_current"] = yield_current
            features["yield_other"] = yield_other
            features["yield_differential"] = yield_current - yield_other

            funding_rate = self.funding_rates.get(current_symbol, 0.0)
            features["funding_rate"] = funding_rate

        return features

    def _estimate_half_life(self, spreads: List[float]) -> Optional[float]:
        """
        Estimar half-life de la reversion a la media del spread.

        Half-life indica cuantos periodos tarda el spread en revertir
        a la mitad de su desviacion de la media.

        Args:
            spreads: Lista de spreads historicos

        Returns:
            Half-life en periodos o None si no se puede calcular
        """
        if len(spreads) < 30:
            return None

        try:
            spread_array = np.array(spreads)
            spread_lag = spread_array[:-1]
            spread_diff = np.diff(spread_array)

            # OLS regression: spread_diff = theta * spread_lag + epsilon
            if np.std(spread_lag) > 0:
                # Simple OLS
                theta = np.cov(spread_diff, spread_lag)[0, 1] / np.var(spread_lag)

                # Half-life = -ln(2) / ln(1 + theta)
                if theta < 0:  # Mean-reverting
                    half_life = -np.log(2) / np.log(1 + theta) if (1 + theta) > 0 else None
                    return (
                        float(half_life)
                        if half_life is not None and not np.isnan(half_life)
                        else None
                    )
            return None
        except (ValueError, KeyError, AttributeError, IndexError, TypeError):
            return None

    def _generate_signals_impl(self, market_data: Quote) -> List[Signal]:
        """
        Implementacion especifica de generacion de senales para arbitraje.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de senales generadas
        """
        signals: List[Signal] = []

        try:
            current_price = float(market_data.close or market_data.bid or market_data.last or 0)
            if current_price <= 0:
                return []

            current_symbol = market_data.symbol

            # Update price history
            self.price_history[current_symbol].append(current_price)
            self.volume_history[current_symbol].append(float(getattr(market_data, "volume", 0)))

            # Find which pair this symbol belongs to
            pair_found = None
            other_symbol = None
            for pair in self.arbitrage_pairs:
                if current_symbol in pair:
                    pair_found = pair
                    other_symbol = pair[1] if pair[0] == current_symbol else pair[0]
                    break

            if pair_found is None:
                return []

            # Need history for both symbols
            prices_current = list(self.price_history.get(current_symbol, []))
            prices_other = list(self.price_history.get(other_symbol, []))

            if (
                len(prices_current) < self.lookback_period
                or len(prices_other) < self.lookback_period
            ):
                return []

            # Align lengths
            min_len = min(len(prices_current), len(prices_other))
            p1 = prices_current[-min_len:]
            p2 = prices_other[-min_len:]

            # Calculate spread metrics
            spreads = [a - b for a, b in zip(p1, p2)]
            spread_mean = float(np.mean(spreads[-self.lookback_period :]))
            spread_std = (
                float(np.std(spreads[-self.lookback_period :]))
                if np.std(spreads[-self.lookback_period :]) > 0
                else 1e-8
            )
            current_spread = spreads[-1]
            spread_z_score = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0.0

            # Calculate spread percentage
            if p2[-1] > 0:
                spread_pct = abs(current_spread / p2[-1])
            else:
                spread_pct = 0.0

            # Calculate correlation
            if len(p1) >= 20 and len(p2) >= 20:
                correlation = float(np.corrcoef(p1[-20:], p2[-20:])[0, 1])
                correlation = correlation if not np.isnan(correlation) else 0.0
            else:
                correlation = 0.0

            # Store spread for tracking
            pair_key = f"{pair_found[0]}_{pair_found[1]}"
            self.spread_history[pair_key].append(current_spread)

            # Check arbitrage conditions based on type
            if self.arbitrage_type == self.ARBITRAGE_TYPE_STATISTICAL:
                signals.extend(
                    self._generate_statistical_arbitrage_signals(
                        market_data=market_data,
                        current_symbol=current_symbol,
                        other_symbol=other_symbol,
                        pair_key=pair_key,
                        spread_z_score=spread_z_score,
                        spread_pct=spread_pct,
                        correlation=correlation,
                        current_price=current_price,
                    )
                )
            elif self.arbitrage_type == self.ARBITRAGE_TYPE_SPREAD:
                signals.extend(
                    self._generate_spread_arbitrage_signals(
                        market_data=market_data,
                        current_symbol=current_symbol,
                        other_symbol=other_symbol,
                        pair_key=pair_key,
                        spread_pct=spread_pct,
                        correlation=correlation,
                        current_price=current_price,
                    )
                )
            elif self.arbitrage_type == self.ARBITRAGE_TYPE_CARRY:
                signals.extend(
                    self._generate_carry_trade_signals(
                        market_data=market_data,
                        current_symbol=current_symbol,
                        other_symbol=other_symbol,
                        pair_key=pair_key,
                        current_price=current_price,
                    )
                )

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error generando senal en ArbitrageStrategyEngine: {e}", exc_info=True)

        return signals

    def _generate_statistical_arbitrage_signals(
        self,
        market_data: Quote,
        current_symbol: str,
        other_symbol: str,
        pair_key: str,
        spread_z_score: float,
        spread_pct: float,
        correlation: float,
        current_price: float,
    ) -> List[Signal]:
        """
        Generar senales de arbitraje estadistico basado en z-score del spread.

        Entry: Cuando spread z-score > entry_z_score (short spread) o < -entry_z_score (long spread)
        Exit: Cuando spread z-score cruza exit_z_score hacia cero
        """
        signals: List[Signal] = []

        # Check correlation threshold
        if abs(correlation) < float(self.min_correlation):
            return []

        # Check spread percentage bounds
        if spread_pct < float(self.min_spread_pct) or spread_pct > float(self.max_spread_pct):
            return []

        # Entry conditions
        # Long spread: spread is too negative (z < -entry), expect it to increase
        # Short spread: spread is too positive (z > entry), expect it to decrease

        is_first_leg = current_symbol == pair_key.split("_")[0]

        if spread_z_score > float(self.entry_z_score):
            # Spread is too high: SELL first leg, BUY second leg
            if is_first_leg:
                signal = self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.SELL,
                    spread_z_score=spread_z_score,
                    correlation=correlation,
                    arbitrage_action="short_spread_leg1",
                    other_symbol=other_symbol,
                    current_price=current_price,
                )
                signals.append(signal)
            else:
                signal = self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.BUY,
                    spread_z_score=spread_z_score,
                    correlation=correlation,
                    arbitrage_action="short_spread_leg2",
                    other_symbol=other_symbol,
                    current_price=current_price,
                )
                signals.append(signal)

        elif spread_z_score < -float(self.entry_z_score):
            # Spread is too low: BUY first leg, SELL second leg
            if is_first_leg:
                signal = self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.BUY,
                    spread_z_score=spread_z_score,
                    correlation=correlation,
                    arbitrage_action="long_spread_leg1",
                    other_symbol=other_symbol,
                    current_price=current_price,
                )
                signals.append(signal)
            else:
                signal = self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.SELL,
                    spread_z_score=spread_z_score,
                    correlation=correlation,
                    arbitrage_action="long_spread_leg2",
                    other_symbol=other_symbol,
                    current_price=current_price,
                )
                signals.append(signal)

        return signals

    def _generate_spread_arbitrage_signals(
        self,
        market_data: Quote,
        current_symbol: str,
        other_symbol: str,
        pair_key: str,
        spread_pct: float,
        correlation: float,
        current_price: float,
    ) -> List[Signal]:
        """
        Generar senales de arbitraje de spread puro.

        Entry cuando el spread porcentual excede un umbral minimo.
        """
        signals: List[Signal] = []

        # Check correlation threshold
        if abs(correlation) < float(self.min_correlation):
            return []

        # Check if spread is large enough
        if spread_pct < float(self.min_spread_pct):
            return []

        if spread_pct > float(self.max_spread_pct):
            return []

        # For pure spread arbitrage, we always go long the cheaper and short the more expensive
        # Compare prices
        price_other = (
            list(self.price_history.get(other_symbol, []))[-1]
            if self.price_history.get(other_symbol)
            else 0
        )

        if current_price > 0 and price_other > 0:
            # Determine which is relatively more expensive
            if current_price > price_other * (1 + float(self.min_spread_pct)):
                # Current is more expensive: SELL current, BUY other
                signal = self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.SELL,
                    spread_z_score=0.0,  # Not using z-score for pure spread
                    correlation=correlation,
                    arbitrage_action="spread_arb_sell_expensive",
                    other_symbol=other_symbol,
                    current_price=current_price,
                )
                signals.append(signal)
            elif price_other > current_price * (1 + float(self.min_spread_pct)):
                # Other is more expensive: BUY current
                signal = self._create_signal(
                    market_data=market_data,
                    signal_type=SignalType.BUY,
                    spread_z_score=0.0,
                    correlation=correlation,
                    arbitrage_action="spread_arb_buy_cheap",
                    other_symbol=other_symbol,
                    current_price=current_price,
                )
                signals.append(signal)

        return signals

    def _generate_carry_trade_signals(
        self,
        market_data: Quote,
        current_symbol: str,
        other_symbol: str,
        pair_key: str,
        current_price: float,
    ) -> List[Signal]:
        """
        Generar senales de carry trade basadas en diferenciales de rendimiento.

        Buy asset with higher yield, sell asset with lower yield.
        """
        signals: List[Signal] = []

        # Get yield data
        yield_current = self.yield_data.get(current_symbol, 0.0)
        yield_other = self.yield_data.get(other_symbol, 0.0)
        yield_differential = yield_current - yield_other

        # Check if yield differential is significant
        if abs(yield_differential) < float(self.carry_yield_threshold):
            return []

        if yield_differential > float(self.carry_yield_threshold):
            # Current has higher yield: BUY current
            signal = self._create_signal(
                market_data=market_data,
                signal_type=SignalType.BUY,
                spread_z_score=0.0,
                correlation=0.0,
                arbitrage_action="carry_long_high_yield",
                other_symbol=other_symbol,
                current_price=current_price,
                yield_differential=yield_differential,
            )
            signals.append(signal)
        elif yield_differential < -float(self.carry_yield_threshold):
            # Other has higher yield: SELL current (to go long other)
            signal = self._create_signal(
                market_data=market_data,
                signal_type=SignalType.SELL,
                spread_z_score=0.0,
                correlation=0.0,
                arbitrage_action="carry_short_low_yield",
                other_symbol=other_symbol,
                current_price=current_price,
                yield_differential=yield_differential,
            )
            signals.append(signal)

        return signals

    def _create_signal(
        self,
        market_data: Quote,
        signal_type: SignalType,
        spread_z_score: float,
        correlation: float,
        arbitrage_action: str,
        other_symbol: str,
        current_price: float,
        yield_differential: float = 0.0,
    ) -> Signal:
        """Crear senal de arbitraje."""
        confidence = self._calculate_confidence(
            spread_z_score=spread_z_score,
            correlation=correlation,
            arbitrage_type=self.arbitrage_type,
        )
        strength = self._map_confidence_to_strength(confidence)

        return Signal(
            symbol=market_data.symbol,
            signal_type=signal_type,
            strength=strength,
            price=Decimal(str(current_price)),
            timestamp=getattr(market_data, "timestamp", None),
            confidence=confidence,
            liquidity_score=70.0,
            priority_score=confidence * 0.75 + 25.0,
            source=SignalSource.ARBITRAGE,
            volume=Decimal("1"),
            metadata={
                "strategy": self.name,
                "arbitrage_type": self.arbitrage_type,
                "arbitrage_action": arbitrage_action,
                "other_symbol": other_symbol,
                "spread_z_score": spread_z_score,
                "correlation": correlation,
                "yield_differential": yield_differential,
                "entry_z_score": float(self.entry_z_score),
                "exit_z_score": float(self.exit_z_score),
            },
        )

    def _calculate_confidence(
        self,
        spread_z_score: float,
        correlation: float,
        arbitrage_type: str,
    ) -> float:
        """
        Calcular confidence de la senal de arbitraje.

        Args:
            spread_z_score: Z-score del spread (para statistical)
            correlation: Correlacion entre activos
            arbitrage_type: Tipo de arbitraje

        Returns:
            Confidence entre 0 y 100
        """
        confidence = 50.0

        if arbitrage_type == self.ARBITRAGE_TYPE_STATISTICAL:
            # Z-score contribution (higher deviation = higher confidence)
            abs_z = abs(spread_z_score)
            if abs_z >= 3.0:
                confidence += 25.0
            elif abs_z >= 2.5:
                confidence += 20.0
            elif abs_z >= 2.0:
                confidence += 15.0
            elif abs_z >= 1.5:
                confidence += 10.0

            # Correlation contribution (higher correlation = more reliable arbitrage)
            if abs(correlation) >= 0.95:
                confidence += 15.0
            elif abs(correlation) >= 0.90:
                confidence += 10.0
            elif abs(correlation) >= 0.80:
                confidence += 5.0

        elif arbitrage_type == self.ARBITRAGE_TYPE_SPREAD:
            # For spread arbitrage, base confidence on correlation
            if abs(correlation) >= 0.95:
                confidence += 30.0
            elif abs(correlation) >= 0.90:
                confidence += 20.0
            elif abs(correlation) >= 0.80:
                confidence += 10.0

        elif arbitrage_type == self.ARBITRAGE_TYPE_CARRY:
            # For carry trades, confidence based on yield differential
            confidence += 20.0  # Base premium for carry trades

        return min(100.0, max(0.0, confidence))

    @staticmethod
    def _map_confidence_to_strength(confidence: float) -> SignalStrength:
        """Mapear confidence (0-100) a SignalStrength."""
        if confidence >= 80.0:
            return SignalStrength.VERY_STRONG
        if confidence >= 70.0:
            return SignalStrength.STRONG
        if confidence >= 50.0:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def set_yield_data(self, symbol: str, yield_rate: float) -> None:
        """
        Establecer datos de rendimiento para carry trades.

        Args:
            symbol: Simbolo del activo
            yield_rate: Tasa de rendimiento anualizada
        """
        self.yield_data[symbol] = yield_rate
        logger.debug(f"Set yield for {symbol}: {yield_rate:.4f}")

    def set_funding_rate(self, symbol: str, funding_rate: float) -> None:
        """
        Establecer tasa de funding para derivados.

        Args:
            symbol: Simbolo del activo
            funding_rate: Tasa de funding
        """
        self.funding_rates[symbol] = funding_rate
        logger.debug(f"Set funding rate for {symbol}: {funding_rate:.6f}")

    def get_required_parameters(self) -> List[str]:
        """Obtener parametros requeridos."""
        return [
            "arbitrage_type",
            "lookback_period",
            "entry_z_score",
            "exit_z_score",
            "min_spread_pct",
            "max_exposure",
            "min_signal_confidence",
        ]

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar criterios de riesgo para arbitraje.

        Args:
            signal: Senal a verificar
            portfolio: Estado del portfolio

        Returns:
            True si pasa el risk check
        """
        # Check total exposure
        try:
            current_exposure = portfolio.get_total_exposure()
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            current_exposure = 0.0

        if current_exposure >= float(self.max_exposure):
            logger.debug(
                "Risk check fallido en ArbitrageStrategyEngine: "
                f"exposicion {current_exposure:.2%} >= {float(self.max_exposure):.2%}"
            )
            return False

        # Check signal confidence
        if signal.confidence < self.min_signal_confidence:
            logger.debug(
                "Risk check fallido en ArbitrageStrategyEngine: "
                f"confidence {signal.confidence:.2f} < {self.min_signal_confidence:.2f}"
            )
            return False

        # Check position limits per leg
        symbol_exposure = self._calculate_symbol_exposure(signal.symbol, portfolio)
        if symbol_exposure >= float(self.max_position_per_leg):
            logger.debug(
                "Risk check fallido en ArbitrageStrategyEngine: "
                f"exposicion simbolo {symbol_exposure:.2%} >= {float(self.max_position_per_leg):.2%}"
            )
            return False

        return True

    def _calculate_symbol_exposure(self, symbol: str, portfolio: Portfolio) -> float:
        """Calcular exposicion de un simbolo especifico."""
        symbol_value = Decimal("0")
        for position in portfolio.positions:
            if position.symbol == symbol:
                symbol_value += position.market_value

        total_value = portfolio.cash + sum(p.market_value for p in portfolio.positions)
        if total_value == 0:
            return 0.0

        return float(symbol_value / total_value)

    def get_active_arbitrage_positions(self) -> Dict[str, Dict[str, Any]]:
        """Obtener posiciones de arbitraje activas."""
        return self.active_arbitrage_positions.copy()

    def get_spread_statistics(self, pair_key: str) -> Optional[Dict[str, float]]:
        """
        Obtener estadisticas del spread para un par.

        Args:
            pair_key: Clave del par (e.g., "SPY_IVV")

        Returns:
            Dict con estadisticas o None
        """
        spreads = list(self.spread_history.get(pair_key, []))
        if len(spreads) < self.lookback_period:
            return None

        recent_spreads = spreads[-self.lookback_period :]
        return {
            "mean": float(np.mean(recent_spreads)),
            "std": float(np.std(recent_spreads)),
            "min": float(min(recent_spreads)),
            "max": float(max(recent_spreads)),
            "current": float(recent_spreads[-1]),
            "z_score": (
                float((recent_spreads[-1] - np.mean(recent_spreads)) / np.std(recent_spreads))
                if np.std(recent_spreads) > 0
                else 0.0
            ),
        }
