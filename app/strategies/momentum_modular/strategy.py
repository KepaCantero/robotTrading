"""
ModularMomentumStrategy - Estrategia de momentum completamente modular con learning engines integrado.
"""

import logging
from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    pass

from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.momentum_analysis import TechnicalIndicatorCalculator
from app.strategies.base import BaseStrategy

from .modules.filters import (
    ATRFilter,
    EMAFilter,
    MomentumFilter,
    RSIFilter,
    StochRSIFilter,
    VolumeFilter,
)
from .modules.market_analyzer import MarketAnalyzer

# BaseLearningEngine solo para type hints (no se ejecuta en runtime)

logger = logging.getLogger(__name__)


class RateLimitedLogger:
    """Logger que solo imprime warnings cada N veces para evitar spam."""

    def __init__(self, logger_obj, rate_limit: int = 100):
        self.logger = logger_obj
        self.rate_limit = rate_limit
        self.counters: Dict[str, int] = {}

    def warning(self, msg: str, key: str = "default"):
        """Log warning only every N times."""
        if key not in self.counters:
            self.counters[key] = 0
        self.counters[key] += 1

        if self.counters[key] == 1 or self.counters[key] % self.rate_limit == 0:
            self.logger.warning(f"{msg} (occurrence #{self.counters[key]})")


_rate_limited_logger = RateLimitedLogger(logger, rate_limit=100)


class ModularMomentumStrategy(BaseStrategy):
    """
    Estrategia de momentum completamente modular con learning engines integrado.

    Características:
    - Arquitectura modular: filtros activables/desactivables
    - Learning engines: Supervised, Deep, Reinforcement Learning
    - Análisis de contexto de mercado
    - Ajuste dinámico de thresholds basado en predicciones
    - Reentrenamiento automático
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia modular.

        Args:
            config: Configuración desde YAML (momentum_modular.yaml)
        """
        super().__init__(config)

        # Configuración
        self.preset = config.get("preset", "balanced")
        self.presets_config = config.get("presets", {})
        self.current_preset = self.presets_config.get(self.preset, {})

        # Módulos de análisis
        self.market_analyzer = MarketAnalyzer(config.get("market_analyzer", {}))

        # Filtros modulares
        modules_config = config.get("modules", {})
        self.filters = []
        filter_classes = {
            "ema_filter": EMAFilter,
            "rsi_filter": RSIFilter,
            "stoch_rsi_filter": StochRSIFilter,
            "momentum_filter": MomentumFilter,
            "volume_filter": VolumeFilter,
            "atr_filter": ATRFilter,
        }

        for filter_name, filter_class in filter_classes.items():
            if filter_name in modules_config:
                filter_config = modules_config[filter_name]
                if filter_config.get("enabled", True):
                    filter_instance = filter_class(filter_config, preset=self.preset)
                    self.filters.append(filter_instance)
                    logger.info(f"✅ Filtro activado: {filter_name}")

        # Learning engine (opcional) - INICIALIZACIÓN LAZY para evitar bloqueos de mutex
        # NO inicializar aquí - se inicializará cuando realmente se necesite
        learning_config = config.get("adaptive_learning", {})
        self._learning_config = learning_config if learning_config.get("enabled", False) else None
        self._learning_engine_type = (
            learning_config.get("engine_type", "supervised")
            if learning_config.get("enabled", False)
            else None
        )
        self.learning_engine = None  # Se inicializará lazy cuando se necesite

        # Solo loguear que está configurado, pero NO crear la instancia
        if self._learning_config:
            logger.info(
                f"📋 Learning engine configurado: {self._learning_engine_type} (se inicializará cuando se necesite)"
            )

        # Feature extractor para learning engines (import lazy - solo cuando se necesite)
        # NO importar aquí para evitar bloqueos - se importará cuando realmente se use
        self._feature_extractor = None

        # Thresholds configurables
        self.min_success_probability = self.current_preset.get("min_confidence", 0.6)
        combination_mode = self.current_preset.get("combination_mode", "MAJORITY")
        self.combination_mode = combination_mode  # "ALL", "MAJORITY", "ANY"

        # Históricos para indicadores
        self.indicator_calculator = TechnicalIndicatorCalculator()
        self.price_history = deque(maxlen=200)
        self.high_history = deque(maxlen=200)
        self.low_history = deque(maxlen=200)
        self.volume_history = deque(maxlen=200)
        self.atr_history = deque(maxlen=100)

        # Histórico de trades para metadata
        self.recent_trades: deque = deque(maxlen=10)

        # Histórico de features para Deep Learning / Transformer (secuencias)
        self.features_history = deque(
            maxlen=200
        )  # Almacena dicts con indicators, filter_results, market_context, metadata

        logger.info(
            f"✅ ModularMomentumStrategy inicializada (preset: {self.preset}, "
            f"{len(self.filters)} filtros activos, "
            f"learning: {'✅ configurado' if self._learning_config else '❌'})"
        )

    def _initialize_learning_engine(self) -> None:
        """
        Inicializar learning engine de forma lazy.

        Esto previene que PyTorch/MKL se inicialicen durante la creación de la estrategia,
        evitando bloqueos de mutex.cc
        """
        if not self._learning_config or self.learning_engine is not None:
            return

        engine_type = self._learning_engine_type
        if not engine_type:
            return

        try:
            # CRÍTICO: Configurar variables de entorno ANTES de importar learning engines
            import os

            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['OPENBLAS_NUM_THREADS'] = '1'
            os.environ['MKL_NUM_THREADS'] = '1'
            os.environ['NUMEXPR_NUM_THREADS'] = '1'
            os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
            os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
            os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
            os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
            os.environ['CUDA_VISIBLE_DEVICES'] = ''
            os.environ['TORCH_USE_CUDA_DSA'] = '0'

            if engine_type == "supervised":
                from .learning.supervised_learning_engine import SupervisedLearningEngine

                self.learning_engine = SupervisedLearningEngine(self._learning_config)
            elif engine_type == "deep":
                # CRÍTICO: NO crear DeepLearningEngine en proceso principal - causa mutex.cc blocking
                # Se entrenará en subprocess y NO se usará para predicciones en proceso principal
                logger.info(
                    "⚠️ Deep Learning configurado pero NO se inicializará en proceso principal (previene mutex.cc blocking)"
                )
                logger.info(
                    "⚠️ El entrenamiento se hará en subprocess. No habrá predicciones del modelo durante el backtest."
                )
                self.learning_engine = None  # NO crear - evitar cualquier import de PyTorch
                # NO desactivar _learning_engine_type - mantenerlo para saber qué tipo es
            elif engine_type == "reinforcement":
                from .learning.reinforcement_learning_engine import ReinforcementLearningEngine

                self.learning_engine = ReinforcementLearningEngine(self._learning_config)
            elif engine_type == "transformer":
                # CRÍTICO: NO crear TransformerEngine en proceso principal - causa mutex.cc blocking
                logger.info(
                    "⚠️ Transformer configurado pero NO se inicializará en proceso principal (previene mutex.cc blocking)"
                )
                logger.info(
                    "⚠️ El entrenamiento se hará en subprocess. No habrá predicciones del modelo durante el backtest."
                )
                self.learning_engine = None  # NO crear - evitar cualquier import de PyTorch
                # NO desactivar _learning_engine_type - mantenerlo para saber qué tipo es

            if self.learning_engine and self.learning_engine.enabled:
                logger.info(f"✅ Learning engine inicializado: {engine_type}")
            elif self.learning_engine and not self.learning_engine.enabled:
                logger.warning(
                    f"⚠️ Learning engine {engine_type} está deshabilitado (dependencias faltantes)"
                )
                self.learning_engine = None
        except (ImportError, RuntimeError) as e:
            logger.error(f"❌ Error al inicializar learning engine {engine_type}: {e}")
            logger.error(
                "⚠️ Asegúrate de instalar todas las dependencias: pip install -r requirements.txt"
            )
            self.learning_engine = None
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            error_msg = str(e).lower()
            if 'mutex' in error_msg or 'lock' in error_msg or 'blocking' in error_msg:
                logger.error(f"❌ Bloqueo de mutex al inicializar {engine_type}: {e}")
                logger.error("💡 El learning engine se intentará inicializar más tarde o se omitirá")
                self.learning_engine = None
            else:
                raise

    def _is_market_regime_safe(self, market_context: Dict[str, Any]) -> bool:
        """
        Check if the current market regime is safe for trading.

        This is a CRITICAL filter that prevents trading during adverse market conditions:
        - Bear market crashes (DOWN trend + HIGH volatility)
        - Dead markets (sideways/range + LOW volatility)
        - Only allows trading in favorable conditions

        Args:
            market_context: Market analysis context from market_analyzer

        Returns:
            True if trading is allowed, False if market regime is bad
        """
        market_type = market_context.get('type', 'unknown')
        trend_strength = market_context.get('trend_strength', 0.0)
        volatility_regime = market_context.get('volatility_regime', 'normal')
        volatility_percentile = market_context.get('volatility_percentile', 50)

        # BAD REGIME CONDITIONS (return False - NO trading)

        # 1. Bear market crash: trend DOWN with high strength
        if market_type == 'trend_down' and trend_strength > 0.6:
            _rate_limited_logger.warning(
                f"🚨 BEAR MARKET CRASH DETECTED: "
                f"type={market_type}, strength={trend_strength:.2f} > 0.6 - "
                f"STOPPING TRADING to prevent losses",
                key="bear_market_crash",
            )
            return False

        # 2. Dead/sideways market with low volatility (no opportunity)
        if market_type in ['range', 'sideways'] and volatility_regime == 'low':
            logger.debug(
                f"💀 DEAD MARKET: "
                f"type={market_type}, volatility={volatility_regime} - "
                f"NO trading (insufficient volatility for profits)"
            )
            return False

        # 3. HIGH volatility regime (crash/crisis conditions)
        # If volatility is above 75th percentile, market is in crisis
        if volatility_percentile > 75:
            _rate_limited_logger.warning(
                f"🔥 EXTREME VOLATILITY CRISIS: "
                f"volatility_percentile={volatility_percentile} > 75 - "
                f"STOPPING TRADING to prevent crash losses",
                key="volatility_crisis",
            )
            return False

        # GOOD REGIME CONDITIONS (return True - ALLOW trading)

        # 1. Bull market: trend UP is always good
        if market_type == 'trend_up':
            logger.debug(
                f"✅ BULL MARKET: "
                f"type={market_type}, strength={trend_strength:.2f} - "
                f"Trading ALLOWED"
            )
            return True

        # 2. Normal volatility (40-70 percentile) with any trend except strong down
        if 40 <= volatility_percentile <= 70:
            if market_type != 'trend_down' or trend_strength <= 0.5:
                logger.debug(
                    f"✅ NORMAL VOLATILITY: "
                    f"percentile={volatility_percentile}, type={market_type} - "
                    f"Trading ALLOWED"
                )
                return True

        # 3. No trend / range with normal volatility (acceptable)
        if market_type in ['range', 'no_trend'] and volatility_regime == 'normal':
            logger.debug(
                f"✅ RANGE MARKET (NORMAL VOL): "
                f"type={market_type}, volatility={volatility_regime} - "
                f"Trading ALLOWED (cautious)"
            )
            return True

        # DEFAULT: Conservative - don't trade if uncertain
        logger.debug(
            f"⚠️ UNCERTAIN MARKET REGIME: "
            f"type={market_type}, strength={trend_strength:.2f}, "
            f"volatility={volatility_regime} (percentile={volatility_percentile}) - "
            f"DEFAULTING to NO TRADING (conservative)"
        )
        return False

    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Genera señales usando módulos y learning engines.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        signals = []

        try:
            # 1. Actualizar históricos
            current_price = float(market_data.close or market_data.bid or market_data.last or 0)
            if current_price <= 0:
                return []

            self.price_history.append(current_price)
            self.high_history.append(float(market_data.high or current_price))
            self.low_history.append(float(market_data.low or current_price))
            self.volume_history.append(float(market_data.volume or 0))

            # Necesitamos suficiente histórico para calcular indicadores
            min_history = 60  # Suficiente para EMA slow (26) + RSI (14) + buffer
            if len(self.price_history) < min_history:
                return []

            # 2. Calcular indicadores técnicos
            indicators = self._calculate_indicators()
            if not indicators:
                return []

            # 3. Analizar contexto de mercado
            price_list = list(self.price_history)
            atr_list = list(self.atr_history) if self.atr_history else []
            market_context = self.market_analyzer.analyze(market_data, price_list, atr_list)

            # 4. CRITICAL: Market Regime Filter - Prevent trading during bad conditions
            if not self._is_market_regime_safe(market_context):
                logger.debug(
                    f"🚫 Market regime filter: NO trading allowed. "
                    f"type={market_context.get('type')}, "
                    f"strength={market_context.get('trend_strength', 0):.2f}, "
                    f"volatility={market_context.get('volatility_regime', 'unknown')}"
                )
                return []

            # 4. Evaluar todos los filtros
            filter_results = self._evaluate_filters(indicators, market_context)

            # 5. Generar señal candidata basada en filtros
            signal_type = self._determine_signal_type(filter_results, market_context)

            if signal_type is None:
                return []

            # 6. SI learning engine está activo, obtener predicción
            # CRÍTICO: NUNCA inicializar learning engine en proceso principal - CAUSA MUTEX.CC BLOCKING
            # El learning engine solo se entrena en subprocess durante backtesting
            learning_prediction = None

            # Para deep/transformer, SIEMPRE usar predicción neutral (nunca tocar PyTorch)
            if self._learning_engine_type in ['deep', 'transformer']:
                learning_prediction = {
                    'success_probability': 0.5,
                    'confidence': 0.0,
                    'recommended_action': 'HOLD',
                    'filter_adjustments': {},
                }
                logger.debug(
                    f"⚠️ {self._learning_engine_type} engine - usando predicción neutral (previene mutex.cc blocking)"
                )
            # Solo usar learning engine si YA está inicializado (no intentar inicializar aquí)
            elif self.learning_engine is not None and self.learning_engine.enabled:
                # Para otros engines (supervised, reinforcement), proceder normalmente
                if learning_prediction is None:
                    # Si no está entrenado pero está habilitado, intentar entrenar automáticamente
                    if not self.learning_engine.is_ready():
                        # Intentar entrenar con datos históricos si hay suficientes
                        if len(self.price_history) >= 100:  # Mínimo de datos para entrenar
                            try:
                                self._auto_train_learning_engine()
                            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                                logger.debug(
                                    f"No se pudo entrenar learning engine automáticamente: {e}"
                                )

                    # Preparar metadata
                    metadata = {
                        'timestamp': (
                            market_data.timestamp
                            if hasattr(market_data, 'timestamp')
                            else datetime.now()
                        ),
                        'symbol': market_data.symbol,
                        'recent_trades': list(self.recent_trades),
                        'recent_win_rate': self._calculate_recent_win_rate(),
                    }

                    # Preparar features según el tipo de learning engine
                    learning_engine_type = self.learning_engine.__class__.__name__

                    if learning_engine_type in ['DeepLearningEngine', 'TransformerEngine']:
                        # Para Deep Learning y Transformer, necesitamos una secuencia histórica
                        features = self._prepare_sequence_features_for_learning(
                            indicators, filter_results, market_context, metadata
                        )
                    else:
                        # Para Supervised y Reinforcement, usar features estándar
                        features = {
                            'indicators': indicators,
                            'filter_results': filter_results,
                            'market_context': market_context,
                            'metadata': metadata,
                        }

                    if self.learning_engine.is_ready():
                        # Learning engine entrenado - usar predicción real
                        try:
                            learning_prediction = self.learning_engine.predict(features)
                        except KeyError as e:
                            if 'sequence' in str(e):
                                logger.warning(
                                    f"⚠️ Learning engine {learning_engine_type} necesita 'sequence' pero no está disponible. Usando predicción neutral."
                                )
                                learning_prediction = {
                                    'success_probability': 0.5,
                                    'confidence': 0.0,
                                    'recommended_action': 'HOLD',
                                }
                            else:
                                raise
                        except (RuntimeError, ValueError, TypeError, KeyError) as e:
                            logger.warning(f"⚠️ Error en predicción de learning engine: {e}")
                            learning_prediction = {
                                'success_probability': 0.5,
                                'confidence': 0.0,
                                'recommended_action': 'HOLD',
                            }

                        # Filtrar señal si probabilidad es baja
                        if self.learning_engine.__class__.__name__ in [
                            'SupervisedLearningEngine',
                            'DeepLearningEngine',
                        ]:
                            success_prob = learning_prediction.get(
                                'success_probability', learning_prediction.get('confidence', 0.5)
                            )
                            if success_prob < self.min_success_probability:
                                logger.debug(
                                    f"🚫 Señal rechazada por learning engine: prob={success_prob:.2f} < {self.min_success_probability:.2f}"
                                )
                                return []

                        # Aplicar ajustes sugeridos por learning engine
                        self._apply_learning_adjustments(learning_prediction)
                    else:
                        # Learning engine no entrenado - usar predicción neutral
                        learning_prediction = {
                            'success_probability': 0.5,
                            'confidence': 0.0,
                            'recommended_action': 'HOLD',
                        }
                        logger.debug(
                            f"⚠️ Learning engine ({self.learning_engine.__class__.__name__}) no entrenado - usando predicción neutral. "
                            f"Estado: enabled={self.learning_engine.enabled}, is_trained={self.learning_engine.is_trained}, model={'exists' if self.learning_engine.model else 'None'}"
                        )

            # 7. Crear señal
            confidence = self._calculate_signal_confidence(filter_results, learning_prediction)

            # Calcular strength basado en confidence
            # IMPORTANTE: Debe coincidir con validación en Signal model
            # - STRONG/VERY_STRONG requieren confidence >= 70.0
            # - WEAK requiere confidence <= 80.0
            if confidence >= 80.0:
                strength = SignalStrength.VERY_STRONG
            elif confidence >= 70.0:  # Cambiado de 65.0 a 70.0 para cumplir validación Pydantic
                strength = SignalStrength.STRONG
            elif confidence >= 50.0:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK

            # Validación de seguridad: asegurar consistencia entre strength y confidence
            # Esto previene errores de validación Pydantic
            if (
                strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]
                and confidence < 70.0
            ):
                # Ajustar strength a MODERATE si confidence es demasiado bajo
                logger.warning(
                    f"⚠️ Confidence {confidence:.2f} es demasiado bajo para {strength}, ajustando a MODERATE"
                )
                strength = SignalStrength.MODERATE
            elif strength == SignalStrength.WEAK and confidence > 80.0:
                # Ajustar strength si confidence es demasiado alto para WEAK
                logger.warning(
                    f"⚠️ Confidence {confidence:.2f} es demasiado alto para {strength}, ajustando a MODERATE"
                )
                strength = SignalStrength.MODERATE

            # Calcular liquidity_score (usar volume_ratio del indicador o default)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            liquidity_score = min(
                100.0, max(0.0, (volume_ratio - 0.5) * 50.0)
            )  # Normalizar 0.5-2.0 -> 0-100

            # Calcular priority_score (combinación de confidence y liquidity)
            priority_score = (confidence * 0.7) + (liquidity_score * 0.3)

            # Obtener volume del market_data o usar un default
            volume = Decimal(str(getattr(market_data, 'volume', 0)))
            if volume == 0:
                volume = Decimal("0.01")  # Default mínimo

            # Usar SignalSource enum - momentum_modular es una variante de momentum
            signal_source = SignalSource.MOMENTUM

            signal = Signal(
                symbol=market_data.symbol,
                signal_type=signal_type,
                strength=strength,
                price=Decimal(str(current_price)),
                timestamp=(
                    market_data.timestamp if hasattr(market_data, 'timestamp') else datetime.now()
                ),
                confidence=confidence,
                liquidity_score=liquidity_score,
                priority_score=priority_score,
                source=signal_source,
                volume=volume,
                metadata={
                    'strategy': self.name,
                    'indicators': indicators,
                    'market_context': market_context,
                    'filter_results': {
                        name: {'passed': res.get('passed'), 'confidence': res.get('confidence')}
                        for name, res in filter_results.items()
                    },
                    'learning_prediction': learning_prediction,
                    'preset': self.preset,
                },
            )

            signals.append(signal)

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            logger.error(f"Error generando señal: {e}", exc_info=True)

        return signals

    def _calculate_indicators(self) -> Dict[str, Any]:
        """Calcular todos los indicadores técnicos necesarios."""
        if len(self.price_history) < 26:
            return {}

        prices = list(self.price_history)
        highs = list(self.high_history)
        lows = list(self.low_history)
        volumes = list(self.volume_history)

        indicators = {}

        # RSI - CRITICAL: Use None instead of neutral 50.0 to force proper handling
        rsi = self.indicator_calculator.calculate_rsi(prices, period=14)
        indicators['rsi'] = rsi  # Can be None - filters must handle this

        # EMAs
        ema_fast = self.indicator_calculator.calculate_ema(prices, period=12)
        ema_slow = self.indicator_calculator.calculate_ema(prices, period=26)
        indicators['ema_fast'] = ema_fast  # Can be None
        indicators['ema_slow'] = ema_slow  # Can be None

        # Momentum / ROC - CRITICAL: Use None instead of neutral 0.0
        momentum = self.indicator_calculator.calculate_roc(prices, period=14)
        indicators['momentum_roc'] = momentum  # Can be None - filters must handle this

        # Volume
        if len(volumes) >= 20:
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1] if volumes else 0
            indicators['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1.0
            indicators['volume'] = current_volume
            indicators['avg_volume'] = avg_volume
        else:
            indicators['volume_ratio'] = 1.0
            indicators['volume'] = volumes[-1] if volumes else 0
            indicators['avg_volume'] = 0

        # ATR
        atr = self.indicator_calculator.calculate_atr(highs, lows, prices, period=14)
        if atr is not None:
            self.atr_history.append(atr)
            indicators['atr'] = atr
            current_price = prices[-1]
            indicators['relative_atr'] = (atr / current_price * 100) if current_price > 0 else 0

            # ATR percentile
            if len(self.atr_history) >= 30:
                # Convert deque to list for slicing (deque doesn't support slice notation in older Python)
                recent_atr = list(self.atr_history)[-30:] if len(self.atr_history) > 0 else []
                sorted_atr = sorted(recent_atr)
                percentile = (
                    (sorted_atr.index(atr) / len(sorted_atr)) * 100 if atr in sorted_atr else 50
                )
                indicators['atr_percentile'] = percentile
            else:
                indicators['atr_percentile'] = 50
        else:
            indicators['atr'] = 0.0
            indicators['relative_atr'] = 0.0
            indicators['atr_percentile'] = 50.0

        # StochRSI - CRITICAL: Use None instead of neutral 50.0 to force proper handling
        stoch_rsi_k, stoch_rsi_d = self._calculate_stochastic_rsi(indicators['rsi'], period=14)
        indicators['stoch_rsi_k'] = stoch_rsi_k  # Can be None - filters must handle this
        indicators['stoch_rsi_d'] = stoch_rsi_d  # Can be None - filters must handle this

        # Precio actual
        indicators['price'] = prices[-1]

        return indicators

    def _evaluate_filters(
        self, indicators: Dict[str, Any], market_context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluar todos los filtros activos."""
        filter_results = {}

        for filter_instance in self.filters:
            try:
                # Evaluar para compra (BUY)
                result_buy = filter_instance.evaluate(indicators, market_context, 'BUY')
                filter_results[f"{filter_instance.name}_buy"] = result_buy

                # Evaluar para venta (SELL)
                result_sell = filter_instance.evaluate(indicators, market_context, 'SELL')
                filter_results[f"{filter_instance.name}_sell"] = result_sell

                # Resultado general (usar BUY para simplificar)
                filter_results[filter_instance.name] = result_buy

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.error(f"Error evaluando filtro {filter_instance.name}: {e}")
                filter_results[filter_instance.name] = {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f"Error: {str(e)}",
                }

        return filter_results

    def _determine_signal_type(
        self, filter_results: Dict[str, Dict[str, Any]], market_context: Dict[str, Any]
    ) -> Optional[SignalType]:
        """Determinar tipo de señal basado en resultados de filtros."""

        if len(self.filters) == 0:
            _rate_limited_logger.warning(
                "⚠️ No hay filtros activos - no se pueden generar señales", key="no_filters"
            )
            return None

        # Contar solo los resultados principales de cada filtro (sin _buy/_sell)
        # Cada filtro tiene una entrada principal con su nombre
        filter_names = [f.name for f in self.filters]
        passed_filters = [
            filter_name
            for filter_name in filter_names
            if filter_name in filter_results and filter_results[filter_name].get('passed', False)
        ]

        total_filters = len(self.filters)

        logger.debug(
            f"🔍 Determinando señal: {len(passed_filters)}/{total_filters} filtros pasaron, modo={self.combination_mode}"
        )
        logger.debug(f"   Filtros que pasaron: {passed_filters}")
        logger.debug(f"   Todos los filtros: {filter_names}")

        # Decidir según modo de combinación
        if self.combination_mode == "ALL":
            if len(passed_filters) == total_filters:
                logger.debug("✅ Todos los filtros pasaron - generando señal BUY")
                return SignalType.BUY
        elif self.combination_mode == "MAJORITY":
            required = max(1, (total_filters + 1) // 2)  # Mayoría = >50%
            if len(passed_filters) >= required:
                logger.debug(
                    f"✅ Mayoría de filtros pasaron ({len(passed_filters)}/{total_filters}) - generando señal BUY"
                )
                return SignalType.BUY
        elif self.combination_mode == "ANY":
            if len(passed_filters) > 0:
                logger.debug(
                    f"✅ Al menos un filtro pasó ({len(passed_filters)}) - generando señal BUY"
                )
                return SignalType.BUY

        logger.debug(
            f"❌ No se cumple el modo de combinación ({self.combination_mode}) - no se genera señal"
        )

        # Revisar condiciones de venta
        # Generar SELL si hay condiciones de salida
        sell_passed_filters = [
            filter_name.replace('_sell', '')
            for filter_name in filter_results
            if filter_name.endswith('_sell') and filter_results[filter_name].get('passed', False)
        ]

        market_type = market_context.get('type', 'unknown')
        market_strength = market_context.get('strength', 0.5)

        # Condiciones para señal SELL:
        # 1. Tendencia bajista con mayoría de filtros de venta pasando
        # 2. RSI en sobrecompra (>70) con momentum negativo
        # 3. Cruce EMA bajista con volumen alto
        should_sell = False
        sell_reason = None

        if self.combination_mode == "ALL":
            should_sell = len(sell_passed_filters) >= len(self.filters)
        elif self.combination_mode == "MAJORITY":
            required = max(1, (len(self.filters) + 1) // 2)
            should_sell = len(sell_passed_filters) >= required
        elif self.combination_mode == "ANY":
            should_sell = len(sell_passed_filters) > 0

        # Condiciones adicionales de mercado para SELL
        # CRITICAL: Use None as default, not neutral values that could cause false positives
        rsi = filter_results.get('rsi_filter', {}).get('value')
        momentum = filter_results.get('momentum_filter', {}).get('value')

        # Sobrecompra extrema (only if RSI is available)
        if rsi is not None and isinstance(rsi, (int, float)) and rsi > 75:
            should_sell = True
            sell_reason = "OVERBOUGHT"
            logger.debug(f"🔴 SELL signal: RSI overbought ({rsi:.1f})")

        # Tendencia bajista fuerte
        if market_type == 'trend_down' and market_strength > 0.7:
            should_sell = True
            sell_reason = "STRONG_DOWNTREND"
            logger.debug(f"🔴 SELL signal: Strong downtrend ({market_strength:.2f})")

        # Momentum negativo significativo (only if momentum is available)
        if momentum is not None and isinstance(momentum, (int, float)) and momentum < -0.03:
            should_sell = True
            sell_reason = "NEGATIVE_MOMENTUM"
            logger.debug(f"🔴 SELL signal: Negative momentum ({momentum:.3f})")

        if should_sell:
            logger.debug(
                f"✅ SELL signal generated: {len(sell_passed_filters)} filters passed, "
                f"reason={sell_reason or 'FILTERS'}"
            )
            return SignalType.SELL

        return None

    def _calculate_signal_confidence(
        self,
        filter_results: Dict[str, Dict[str, Any]],
        learning_prediction: Optional[Dict[str, Any]],
    ) -> float:
        """Calcular confianza de la señal."""
        # Confianza base desde filtros
        confidences = [res.get('confidence', 0.0) for res in filter_results.values()]
        base_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Ajustar con predicción de learning engine
        if learning_prediction:
            learning_confidence = learning_prediction.get(
                'confidence', learning_prediction.get('success_probability', 0.5)
            )
            # Combinar: 60% filtros, 40% learning
            combined = base_confidence * 0.6 + learning_confidence * 0.4
            return min(100.0, max(0.0, combined * 100))

        return min(100.0, max(0.0, base_confidence * 100))

    def _auto_train_learning_engine(self) -> None:
        """
        Entrenar automáticamente el learning engine usando datos históricos disponibles.
        Solo se ejecuta una vez cuando hay suficientes datos.
        """
        if not self.learning_engine or not self.learning_engine.enabled:
            return

        if self.learning_engine.is_ready():
            return  # Ya está entrenado

        # Marcar que ya intentamos entrenar para evitar múltiples intentos
        if not hasattr(self, '_training_attempted'):
            self._training_attempted = False

        if self._training_attempted:
            return  # Ya intentamos entrenar antes

        self._training_attempted = True

        try:
            # Preparar datos usando FeatureExtractor
            # Lazy import de feature_extractor solo cuando se necesite
            if self._feature_extractor is None:
                try:
                    from .learning.feature_extractor import FeatureExtractor

                    self._feature_extractor = FeatureExtractor()
                except (RuntimeError, ValueError, TypeError, KeyError) as e:
                    logger.debug(f"FeatureExtractor no disponible: {e}")
                    self._feature_extractor = None

            if self._feature_extractor is not None and len(self.price_history) >= 100:
                # Crear datos sintéticos basados en histórico
                # Nota: Esto es una aproximación. En producción, necesitaríamos los quotes completos
                logger.debug(
                    f"🎓 Intentando auto-entrenar learning engine con {len(self.price_history)} datos históricos..."
                )

                # Por ahora, simplemente marcamos que necesitamos entrenar
                # El entrenamiento real debe hacerse antes del backtest con quotes completos
                logger.debug(
                    "⚠️ Auto-entrenamiento requiere quotes completos - será entrenado en el backtest"
                )

        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            logger.debug(f"Error en auto-entrenamiento: {e}")

    def _prepare_sequence_features_for_learning(
        self,
        indicators: Dict[str, Any],
        filter_results: Dict[str, Dict],
        market_context: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Preparar features en formato de secuencia para Deep Learning / Transformer engines.

        Almacena features históricas y construye una secuencia de la longitud requerida.
        """
        # Guardar features actuales en historial
        self.features_history.append(
            {
                'indicators': indicators.copy(),
                'filter_results': filter_results.copy(),
                'market_context': market_context.copy(),
                'metadata': metadata.copy(),
            }
        )

        # Determinar longitud de secuencia requerida
        sequence_length = 60  # Default
        learning_engine_type = self.learning_engine.__class__.__name__
        if learning_engine_type == 'DeepLearningEngine':
            # Obtener sequence_length de la configuración del engine
            engine_config = getattr(self.learning_engine, 'config', {})
            params = engine_config.get('parameters', {})
            sequence_length = params.get('sequence_length', 60)
        elif learning_engine_type == 'TransformerEngine':
            sequence_length = 30  # Default para Transformer

        # Construir secuencia usando FeatureExtractor
        if self._feature_extractor is None:
            try:
                from .learning.feature_extractor import FeatureExtractor

                self._feature_extractor = FeatureExtractor()
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.debug(f"FeatureExtractor no disponible: {e}")
                self._feature_extractor = None

        if self._feature_extractor is None:
            # Fallback: construir secuencia básica
            sequence = self._build_basic_sequence(sequence_length)
            return {'sequence': sequence, 'market_context': market_context}

        # Convertir historial a lista para FeatureExtractor
        historical_data = list(self.features_history)

        # Si no hay suficiente historial, rellenar con el último elemento
        if len(historical_data) < sequence_length:
            padding = [
                (
                    historical_data[-1]
                    if historical_data
                    else {
                        'indicators': indicators,
                        'filter_results': filter_results,
                        'market_context': market_context,
                        'metadata': metadata,
                    }
                )
            ] * (sequence_length - len(historical_data))
            historical_data = padding + historical_data

        # Extraer secuencia usando FeatureExtractor
        try:
            sequence = self._feature_extractor.extract_sequence_features(
                historical_data[-sequence_length:], sequence_length=sequence_length
            )
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            logger.warning(f"Error extrayendo secuencia: {e}, usando fallback")
            sequence = self._build_basic_sequence(sequence_length)

        return {'sequence': sequence, 'market_context': market_context}

    def _build_basic_sequence(self, sequence_length: int):
        """Construir secuencia básica usando price_history como fallback."""
        import numpy as np

        # Extraer últimas sequence_length precios y normalizarlos
        prices = list(self.price_history)[-sequence_length:]

        if len(prices) < sequence_length:
            # Rellenar con el último precio disponible
            if prices:
                padding = [prices[-1]] * (sequence_length - len(prices))
                prices = padding + prices
            else:
                prices = [0.0] * sequence_length

        # Convertir a numpy array y normalizar (porcentaje de cambio)
        price_array = np.array(prices, dtype=np.float32)

        # Calcular cambios porcentuales
        if len(price_array) > 1:
            pct_changes = np.diff(price_array) / price_array[:-1]
            pct_changes = np.concatenate([[0.0], pct_changes])  # Primer elemento sin cambio
        else:
            pct_changes = np.array([0.0], dtype=np.float32)

        # Reshape para (sequence_length, 1) - una sola feature (price change)
        if len(pct_changes) < sequence_length:
            padding = np.zeros(sequence_length - len(pct_changes), dtype=np.float32)
            pct_changes = np.concatenate([padding, pct_changes])

        sequence = pct_changes.reshape(sequence_length, 1)
        return sequence

    def _apply_learning_adjustments(self, prediction: Dict[str, Any]) -> None:
        """Aplicar ajustes sugeridos por learning engine."""
        if not prediction:
            return

        # Ajustar thresholds de filtros
        filter_adjustments = prediction.get('filter_adjustments', {})
        if filter_adjustments:
            for filter_name, adjustment_value in filter_adjustments.items():
                # Buscar el filtro por nombre
                filter_instance = None
                for f in self.filters:
                    if f.name == filter_name or filter_name in f.name.lower():
                        filter_instance = f
                        break

                if filter_instance:
                    # Aplicar ajuste según el tipo de threshold
                    if isinstance(adjustment_value, dict):
                        # Ajuste estructurado (ej: {'rsi_buy_min': -5, 'momentum_threshold': -0.005})
                        for threshold_name, threshold_adjustment in adjustment_value.items():
                            if hasattr(filter_instance, threshold_name):
                                current_value = getattr(filter_instance, threshold_name)
                                if isinstance(current_value, (int, float)):
                                    new_value = current_value + threshold_adjustment
                                    setattr(filter_instance, threshold_name, new_value)
                                    logger.debug(
                                        f"🔧 Ajustando {filter_instance.name}.{threshold_name}: {current_value} → {new_value} (Δ{threshold_adjustment})"
                                    )
                    elif isinstance(adjustment_value, (int, float)):
                        # Ajuste simple (escalar)
                        # Intentar ajustar thresholds comunes
                        for attr_name in [
                            'threshold',
                            'buy_threshold',
                            'sell_threshold',
                            'min_threshold',
                            'max_threshold',
                        ]:
                            if hasattr(filter_instance, attr_name):
                                current_value = getattr(filter_instance, attr_name)
                                if isinstance(current_value, (int, float)):
                                    new_value = current_value * (
                                        1 + adjustment_value * 0.1
                                    )  # Ajuste del 10% por unidad
                                    setattr(filter_instance, attr_name, new_value)
                                    logger.debug(
                                        f"🔧 Ajustando {filter_instance.name}.{attr_name}: {current_value} → {new_value}"
                                    )
                                    break

        # Ajustar confianza mínima requerida basado en predicción
        if 'confidence' in prediction:
            predicted_confidence = prediction['confidence']
            if predicted_confidence < 0.5:
                self.min_success_probability = 0.7  # Ser más estricto
            else:
                self.min_success_probability = 0.6  # Normal

        # Ajustar thresholds globales de la estrategia si están en la predicción
        if 'threshold_adjustments' in prediction:
            threshold_adjs = prediction['threshold_adjustments']
            for threshold_name, adjustment in threshold_adjs.items():
                if hasattr(self, threshold_name):
                    current = getattr(self, threshold_name)
                    if isinstance(current, (int, float)) and isinstance(adjustment, (int, float)):
                        new_value = current * (1 + adjustment)
                        setattr(self, threshold_name, new_value)
                        logger.debug(
                            f"🔧 Ajustando estrategia.{threshold_name}: {current} → {new_value}"
                        )

    def _calculate_stochastic_rsi(
        self,
        current_rsi: float,
        period: int = 14,
        smooth_k: int = 3,
        smooth_d: int = 3,
    ) -> tuple:
        """
        Calculate Stochastic RSI from RSI values.

        StochRSI = (RSI - Lowest RSI) / (Highest RSI - Lowest RSI) * 100

        Uses historical RSI values stored in price_history to compute
        the stochastic oscillator of RSI.

        Args:
            current_rsi: Current RSI value
            period: Lookback period for StochRSI calculation
            smooth_k: Smoothing period for %K line
            smooth_d: Smoothing period for %D line (signal)

        Returns:
            tuple: (stoch_rsi_k, stoch_rsi_d) or (None, None) if insufficient data
        """
        # Build RSI history from price history
        if not hasattr(self, '_rsi_history'):
            self._rsi_history = deque(maxlen=period + smooth_k + smooth_d)
            self._stoch_k_history = deque(maxlen=smooth_d)

        # Add current RSI to history
        if current_rsi is not None:
            self._rsi_history.append(current_rsi)

        # Need at least 'period' RSI values
        if len(self._rsi_history) < period:
            return None, None

        # Get last 'period' RSI values
        rsi_window = list(self._rsi_history)[-period:]

        # Calculate raw Stochastic RSI
        lowest_rsi = min(rsi_window)
        highest_rsi = max(rsi_window)

        # Handle flat RSI (no range)
        if highest_rsi == lowest_rsi:
            return None, None

        # StochRSI = (Current RSI - Lowest RSI) / (Highest RSI - Lowest RSI) * 100
        stoch_rsi_raw = ((current_rsi - lowest_rsi) / (highest_rsi - lowest_rsi)) * 100

        # Store for %K smoothing
        self._stoch_k_history.append(stoch_rsi_raw)

        # Calculate smoothed %K (SMA of raw StochRSI)
        if len(self._stoch_k_history) >= smooth_k:
            k_values = list(self._stoch_k_history)[-smooth_k:]
            stoch_rsi_k = sum(k_values) / len(k_values)
        else:
            stoch_rsi_k = stoch_rsi_raw

        # Calculate %D (SMA of %K) - signal line
        if not hasattr(self, '_stoch_d_history'):
            self._stoch_d_history = deque(maxlen=smooth_d)

        self._stoch_d_history.append(stoch_rsi_k)

        if len(self._stoch_d_history) >= smooth_d:
            d_values = list(self._stoch_d_history)[-smooth_d:]
            stoch_rsi_d = sum(d_values) / len(d_values)
        else:
            stoch_rsi_d = stoch_rsi_k

        # Clamp values to 0-100 range
        stoch_rsi_k = max(0.0, min(100.0, stoch_rsi_k))
        stoch_rsi_d = max(0.0, min(100.0, stoch_rsi_d))

        return round(stoch_rsi_k, 2), round(stoch_rsi_d, 2)

    def _calculate_recent_win_rate(self) -> float:
        """Calcular win rate de trades recientes."""
        if not self.recent_trades:
            return 0.5

        winning = sum(1 for t in self.recent_trades if t.get('pnl', 0) > 0)
        return winning / len(self.recent_trades)

    def add_trade_result(self, trade: Dict[str, Any]) -> None:
        """Agregar resultado de trade para aprendizaje futuro."""
        self.recent_trades.append(trade)

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """Verificar criterios de riesgo (implementación básica)."""
        # Verificaciones básicas
        if signal.signal_type == SignalType.BUY:
            # Verificar capital disponible
            required_cash = signal.price * self.get_position_size(signal, portfolio)
            if required_cash > portfolio.cash:
                return False

        return True

    def get_required_parameters(self) -> List[str]:
        """Parámetros requeridos."""
        return ["name", "preset"]

    def get_position_size(self, signal: Signal, portfolio: Portfolio) -> Decimal:
        """Calcular tamaño de posición."""
        max_position_size = Decimal(str(self.config.get("max_position_size", 0.1)))
        available_cash = portfolio.cash

        if signal.signal_type == SignalType.BUY:
            max_position_value = available_cash * max_position_size
            position_size = max_position_value / signal.price
            return max(position_size, Decimal("1"))
        else:
            # SELL: usar posición existente
            for pos in portfolio.positions:
                if pos.symbol == signal.symbol:
                    return pos.quantity
            return Decimal("0")
