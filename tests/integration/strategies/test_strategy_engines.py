"""
Integration Tests: Strategy Engines (Módulo 3)

Tests para los nuevos Strategy Engines refactorizados:
- MomentumStrategyEngine
- MeanReversionStrategyEngine
- PairsTradingStrategyEngine
- ModularMomentumStrategyEngine

Verifica:
1. Generación de señales
2. Feature extraction
3. Integración con Learning Engines
4. Callbacks
5. Métricas y estado
"""

"""
Integration Tests: Strategy Engines (Módulo 3)

Tests para los nuevos Strategy Engines refactorizados.
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.engines.strategy_engines import (
    BreakoutStrategyEngine,
    MeanReversionStrategyEngine,
    ModularMomentumStrategyEngine,
    MomentumStrategyEngine,
    PairsTradingStrategyEngine,
    TrendFollowingStrategyEngine,
)
from app.models.market_data import Quote
from app.models.signal import SignalType
from tests.integration.data.test_data_loader import load_all_csv_data

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def dataframe_to_quotes(symbol: str, df: pd.DataFrame):
    """Convert DataFrame to list of Quote objects."""
    quotes = []
    for idx, row in df.iterrows():
        quote = Quote(
            symbol=symbol,
            timestamp=idx if isinstance(idx, datetime) else datetime.now(),
            bid=Decimal(str(row.get('close', row.get('open', 0)))),
            ask=Decimal(str(row.get('close', row.get('open', 0)))),
            last=Decimal(str(row.get('close', 0))),
            close=Decimal(str(row.get('close', 0))),
            open=Decimal(str(row.get('open', row.get('close', 0)))),
            high=Decimal(str(row.get('high', row.get('close', 0)))),
            low=Decimal(str(row.get('low', row.get('close', 0)))),
            volume=Decimal(str(row.get('volume', 0))),
        )
        quotes.append(quote)
    return quotes


class TestMomentumStrategyEngine:
    """Tests para MomentumStrategyEngine."""

    def test_momentum_engine_initialization(self):
        """Test que el engine se inicializa correctamente."""
        config = {
            'rsi_period': 14,
            'ema_fast_period': 12,
            'ema_slow_period': 26,
            'learning_enabled': False,
        }

        engine = MomentumStrategyEngine(config)

        assert engine.get_strategy_type() == "momentum"
        assert not engine.learning_enabled
        assert engine.ensemble_weight == 1.0

    def test_momentum_engine_generate_signals(self):
        """Test generación de señales con datos reales."""
        # Cargar datos
        historical_data = load_all_csv_data()
        if not historical_data:
            pytest.skip("No hay datos históricos disponibles")

        symbol = list(historical_data.keys())[0]
        df = historical_data[symbol]
        quotes = dataframe_to_quotes(symbol, df[:100])  # Primeros 100 días

        # Crear engine
        config = {
            'rsi_period': 14,
            'ema_fast_period': 12,
            'ema_slow_period': 26,
            'learning_enabled': False,
        }
        engine = MomentumStrategyEngine(config)

        # Procesar quotes y generar señales
        signals_generated = 0
        for quote in quotes:
            signals = engine.generate_signals(quote)
            if signals:
                signals_generated += len(signals)
                # Verificar estructura de señal
                signal = signals[0]
                assert signal.symbol == symbol
                assert signal.signal_type in [SignalType.BUY, SignalType.SELL]

        logger.info(f"MomentumStrategyEngine generó {signals_generated} señales para {symbol}")
        # No assert estricto - puede no haber señales dependiendo del mercado

    def test_momentum_engine_feature_extraction(self):
        """Test feature extraction."""
        config = {'rsi_period': 14, 'learning_enabled': False}
        engine = MomentumStrategyEngine(config)

        # Crear quote de ejemplo
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.0"),
            ask=Decimal("150.1"),
            last=Decimal("150.05"),
            close=Decimal("150.05"),
            open=Decimal("149.0"),
            high=Decimal("151.0"),
            low=Decimal("148.0"),
            volume=Decimal("1000000"),
        )

        # Necesitamos procesar varias quotes para tener histórico
        for _ in range(50):
            engine.generate_signals(quote)

        # Extraer features (extract_features solo requiere quote)
        features = engine.extract_features(quote)

        assert isinstance(features, dict)
        assert 'rsi' in features or 'indicators' in features
        logger.info(f"Features extraídas: {list(features.keys())[:5]}")

    def test_momentum_engine_callbacks(self):
        """Test sistema de callbacks."""
        config = {'learning_enabled': False}
        engine = MomentumStrategyEngine(config)

        signal_callback_called = False
        trade_callback_called = False
        market_data_callback_called = False

        def signal_callback(signal):
            nonlocal signal_callback_called
            signal_callback_called = True

        def trade_callback(trade):
            nonlocal trade_callback_called
            trade_callback_called = True

        def market_data_callback(quote):
            nonlocal market_data_callback_called
            market_data_callback_called = True

        engine.register_signal_callback(signal_callback)
        engine.register_trade_callback(trade_callback)
        engine.register_market_data_callback(market_data_callback)

        # Crear quote y generar señal
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.0"),
            ask=Decimal("150.1"),
            last=Decimal("150.05"),
            close=Decimal("150.05"),
            open=Decimal("149.0"),
            high=Decimal("151.0"),
            low=Decimal("148.0"),
            volume=Decimal("1000000"),
        )

        # Procesar varias veces para generar señal
        for _ in range(50):
            engine.generate_signals(quote)

        # Verificar que callbacks fueron llamados
        assert market_data_callback_called, "Market data callback debería haberse llamado"
        # Signal y trade callbacks pueden no llamarse si no hay señales


class TestMeanReversionStrategyEngine:
    """Tests para MeanReversionStrategyEngine."""

    def test_mean_reversion_engine_initialization(self):
        """Test inicialización."""
        config = {'z_score_window': 20, 'z_score_threshold': 2.0, 'learning_enabled': False}

        engine = MeanReversionStrategyEngine(config)

        assert engine.get_strategy_type() == "mean_reversion"
        assert not engine.learning_enabled

    def test_mean_reversion_engine_generate_signals(self):
        """Test generación de señales."""
        historical_data = load_all_csv_data()
        if not historical_data:
            pytest.skip("No hay datos históricos disponibles")

        symbol = list(historical_data.keys())[0]
        df = historical_data[symbol]
        quotes = dataframe_to_quotes(symbol, df[:100])

        config = {'z_score_window': 20, 'z_score_threshold': 2.0, 'learning_enabled': False}
        engine = MeanReversionStrategyEngine(config)

        signals_count = 0
        for quote in quotes:
            signals = engine.generate_signals(quote)
            if signals:
                signals_count += len(signals)

        logger.info(f"MeanReversionStrategyEngine generó {signals_count} señales")

    def test_mean_reversion_engine_features(self):
        """Test feature extraction."""
        config = {'learning_enabled': False}
        engine = MeanReversionStrategyEngine(config)

        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.0"),
            ask=Decimal("150.1"),
            last=Decimal("150.05"),
            close=Decimal("150.05"),
            open=Decimal("149.0"),
            high=Decimal("151.0"),
            low=Decimal("148.0"),
            volume=Decimal("1000000"),
        )

        # Procesar para tener histórico
        for _ in range(50):
            engine.generate_signals(quote)

        features = engine.extract_features(quote)
        assert isinstance(features, dict)


class TestPairsTradingStrategyEngine:
    """Tests para PairsTradingStrategyEngine."""

    def test_pairs_engine_initialization(self):
        """Test inicialización."""
        config = {'lookback_window': 60, 'cointegration_threshold': 0.05, 'learning_enabled': False}

        engine = PairsTradingStrategyEngine(config)

        assert engine.get_strategy_type() == "pairs_trading"

    def test_pairs_engine_generate_signals(self):
        """Test generación de señales con dos símbolos."""
        historical_data = load_all_csv_data()
        if len(historical_data) < 2:
            pytest.skip("Se necesitan al menos 2 símbolos para pairs trading")

        symbols = list(historical_data.keys())[:2]
        symbol1, symbol2 = symbols[0], symbols[1]

        df1 = historical_data[symbol1][:100]
        df2 = historical_data[symbol2][:100]

        quotes1 = dataframe_to_quotes(symbol1, df1)
        quotes2 = dataframe_to_quotes(symbol2, df2)

        config = {
            'symbol1': symbol1,
            'symbol2': symbol2,
            'lookback_window': 60,
            'learning_enabled': False,
        }
        engine = PairsTradingStrategyEngine(config)

        signals_count = 0
        min_len = min(len(quotes1), len(quotes2))
        for i in range(min_len):
            # Procesar ambos símbolos
            engine.generate_signals(quotes1[i])
            signals = engine.generate_signals(quotes2[i])
            if signals:
                signals_count += len(signals)

        logger.info(
            f"PairsTradingStrategyEngine generó {signals_count} señales para {symbol1}-{symbol2}"
        )


class TestModularMomentumStrategyEngine:
    """Tests para ModularMomentumStrategyEngine."""

    def test_modular_momentum_with_context_engine(self):
        """Test ModularMomentumStrategyEngine con ContextEngine."""
        try:
            from app.engines.context_engine import ContextEngine

            context_engine = ContextEngine({})

            config = {
                'preset': 'balanced',
                'modules': {'ema_filter': {'enabled': True}, 'rsi_filter': {'enabled': True}},
                'context_engine_enabled': True,
            }

            engine = ModularMomentumStrategyEngine(config)
            engine.set_context_engine(context_engine)

            assert engine.context_engine_enabled is True
            assert engine.market_analyzer is None  # Debe usar ContextEngine en su lugar

            logger.info("✅ ModularMomentumStrategyEngine integrado con ContextEngine")

        except ImportError:
            pytest.skip("ContextEngine no disponible")

    def test_modular_momentum_engine_initialization(self):
        """Test inicialización."""
        config = {
            'filters': {'rsi_filter': {'enabled': True}, 'ema_filter': {'enabled': True}},
            'learning_enabled': False,
        }

        engine = ModularMomentumStrategyEngine(config)

        assert engine.get_strategy_type() == "modular_momentum"

    def test_modular_momentum_engine_generate_signals(self):
        """Test generación de señales con módulos."""
        historical_data = load_all_csv_data()
        if not historical_data:
            pytest.skip("No hay datos históricos disponibles")

        symbol = list(historical_data.keys())[0]
        df = historical_data[symbol]
        quotes = dataframe_to_quotes(symbol, df[:100])

        config = {
            'filters': {
                'rsi_filter': {'enabled': True, 'rsi_buy_min': 30, 'rsi_buy_max': 70},
                'ema_filter': {'enabled': True},
            },
            'learning_enabled': False,
        }
        engine = ModularMomentumStrategyEngine(config)

        signals_count = 0
        for quote in quotes:
            signals = engine.generate_signals(quote)
            if signals:
                signals_count += len(signals)

        logger.info(f"ModularMomentumStrategyEngine generó {signals_count} señales")

    def test_modular_momentum_engine_with_learning(self):
        """Test integración con learning engine (sin entrenar realmente)."""
        config = {
            'filters': {'rsi_filter': {'enabled': True}},
            'learning_enabled': True,
            'learning_engine': {
                'engine_type': 'supervised',
                'enabled': False,  # No entrenar, solo probar integración
            },
        }

        engine = ModularMomentumStrategyEngine(config)

        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.0"),
            ask=Decimal("150.1"),
            last=Decimal("150.05"),
            close=Decimal("150.05"),
            open=Decimal("149.0"),
            high=Decimal("151.0"),
            low=Decimal("148.0"),
            volume=Decimal("1000000"),
        )

        # Procesar varias veces
        for _ in range(50):
            engine.generate_signals(quote)
            # No debería fallar aunque learning engine no esté entrenado

        assert engine.learning_enabled


class TestBreakoutStrategyEngine:
    """Tests de integración para BreakoutStrategyEngine."""

    def test_breakout_engine_initialization(self):
        """El engine se inicializa correctamente con configuración mínima."""
        config = {
            "lookback_period": 10,
            "breakout_threshold_pct": 0.01,
            "min_volume_ratio": 1.0,
        }
        engine = BreakoutStrategyEngine(config)

        assert engine.get_strategy_type() == "breakout"
        # Note: lookback_period may be overridden by YAML config, check it's a valid int
        assert isinstance(engine.lookback_period, int)
        assert engine.lookback_period > 0
        assert not engine.learning_enabled

    def test_breakout_engine_generate_signals_with_real_data(self):
        """Generación de señales con datos históricos reales (si están disponibles)."""
        historical_data = load_all_csv_data()
        if not historical_data:
            pytest.skip("No hay datos históricos disponibles")

        symbol = list(historical_data.keys())[0]
        df = historical_data[symbol]
        quotes = dataframe_to_quotes(symbol, df[:200])  # más barras para aumentar prob. de breakout

        config = {
            "lookback_period": 20,
            "breakout_threshold_pct": 0.01,
            "min_volume_ratio": 1.0,
        }
        engine = BreakoutStrategyEngine(config)

        signals_count = 0
        for quote in quotes:
            signals = engine.generate_signals(quote)
            if signals:
                signals_count += len(signals)
                signal = signals[0]
                assert signal.symbol == symbol
                assert signal.signal_type in [SignalType.BUY, SignalType.SELL]

        logger.info(f"BreakoutStrategyEngine generó {signals_count} señales para {symbol}")
        # No assert estricto sobre signals_count (depende del activo)


class TestTrendFollowingStrategyEngine:
    """Tests de integración para TrendFollowingStrategyEngine."""

    def test_trend_following_engine_initialization(self):
        """El engine se inicializa correctamente con configuración mínima."""
        config = {
            "adx_period": 14,
            "adx_threshold": 25.0,
            "macd_fast_period": 12,
            "macd_slow_period": 26,
            "macd_signal_period": 9,
            "min_volume_ratio": 1.2,
        }
        engine = TrendFollowingStrategyEngine(config)

        assert engine.get_strategy_type() == "trend_following"
        assert engine.adx_period == 14
        assert engine.adx_threshold == Decimal("25.0")
        assert not engine.learning_enabled

    def test_trend_following_engine_generate_signals_with_real_data(self):
        """Generación de señales con datos históricos reales (si están disponibles)."""
        historical_data = load_all_csv_data()
        if not historical_data:
            pytest.skip("No hay datos históricos disponibles")

        symbol = list(historical_data.keys())[0]
        df = historical_data[symbol]
        quotes = dataframe_to_quotes(symbol, df[:200])  # más barras para tener suficiente histórico

        config = {
            "adx_period": 14,
            "adx_threshold": 25.0,
            "macd_fast_period": 12,
            "macd_slow_period": 26,
            "macd_signal_period": 9,
            "min_volume_ratio": 1.0,  # Bajar threshold para más señales en test
        }
        engine = TrendFollowingStrategyEngine(config)

        signals_count = 0
        for quote in quotes:
            signals = engine.generate_signals(quote)
            if signals:
                signals_count += len(signals)
                signal = signals[0]
                assert signal.symbol == symbol
                assert signal.signal_type in [SignalType.BUY, SignalType.SELL]
                # Signal.source is a string due to use_enum_values=True in Signal model
                assert signal.source == "trend_following"

        logger.info(f"TrendFollowingStrategyEngine generó {signals_count} señales para {symbol}")
        # No assert estricto sobre signals_count (depende del activo y tendencias)

    def test_trend_following_engine_feature_extraction(self):
        """Feature extraction debe devolver campos de ADX y MACD."""
        config = {
            "adx_period": 14,
            "macd_slow_period": 26,
        }
        engine = TrendFollowingStrategyEngine(config)

        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.0"),
            ask=Decimal("150.1"),
            last=Decimal("150.05"),
            close=Decimal("150.05"),
            open=Decimal("149.0"),
            high=Decimal("151.0"),
            low=Decimal("148.0"),
            volume=Decimal("1000000"),
        )

        # Procesar varias veces para tener suficiente histórico
        for i in range(30):
            quote_with_trend = Quote(
                symbol="AAPL",
                timestamp=datetime.now(),
                bid=Decimal(str(150.0 + i * 0.5)),  # Tendencia alcista
                ask=Decimal(str(150.1 + i * 0.5)),
                last=Decimal(str(150.05 + i * 0.5)),
                close=Decimal(str(150.05 + i * 0.5)),
                open=Decimal(str(149.0 + i * 0.5)),
                high=Decimal(str(151.0 + i * 0.5)),
                low=Decimal(str(148.0 + i * 0.5)),
                volume=Decimal("1000000"),
            )
            engine.generate_signals(quote_with_trend)

        features = engine.extract_features(quote)
        assert isinstance(features, dict)
        assert "adx" in features
        assert "macd_line" in features
        assert "macd_signal" in features
        assert "macd_histogram" in features
        assert "volume_ratio" in features
        assert features["symbol"] == "AAPL"

    def test_trend_following_engine_get_required_parameters(self):
        """get_required_parameters debe retornar lista de parámetros requeridos."""
        engine = TrendFollowingStrategyEngine({})
        params = engine.get_required_parameters()

        assert "adx_period" in params
        assert "adx_threshold" in params
        assert "macd_fast_period" in params
        assert "macd_slow_period" in params
        assert "macd_signal_period" in params
        assert "min_volume_ratio" in params

    def test_breakout_engine_feature_extraction(self):
        """Feature extraction debe devolver campos de rango y volumen."""
        config = {
            "lookback_period": 5,
            "breakout_threshold_pct": 0.01,
            "min_volume_ratio": 1.0,
        }
        engine = BreakoutStrategyEngine(config)

        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.0"),
            ask=Decimal("150.1"),
            last=Decimal("150.05"),
            close=Decimal("150.05"),
            open=Decimal("149.0"),
            high=Decimal("151.0"),
            low=Decimal("148.0"),
            volume=Decimal("1000000"),
        )

        # Alimentar histórico mínimo
        for price in [149.5, 150.0, 150.5, 149.8, 150.2]:
            engine.generate_signals(
                Quote(
                    symbol="AAPL",
                    timestamp=datetime.now(),
                    bid=Decimal(str(price)),
                    ask=Decimal(str(price)),
                    last=Decimal(str(price)),
                    close=Decimal(str(price)),
                    open=Decimal(str(price)),
                    high=Decimal(str(price)),
                    low=Decimal(str(price)),
                    volume=Decimal("1000000"),
                )
            )

        features = engine.extract_features(quote)
        assert isinstance(features, dict)
        # Campos clave de rango y volumen
        assert "range_high" in features
        assert "range_low" in features
        assert "volume_ratio" in features


class TestStrategyEnginesIntegration:
    """Tests de integración entre múltiples engines."""

    def test_ensemble_weights(self):
        """Test configuración de pesos para ensembles."""
        engines = [
            MomentumStrategyEngine({'learning_enabled': False}),
            MeanReversionStrategyEngine({'learning_enabled': False}),
        ]

        weights = [0.6, 0.4]
        for engine, weight in zip(engines, weights):
            engine.set_ensemble_weight(weight)

        assert engines[0].get_ensemble_weight() == Decimal("0.6")
        assert engines[1].get_ensemble_weight() == Decimal("0.4")

    def test_strategy_engines_with_data_context_engines(self):
        """Test Strategy Engines con DataEngine y ContextEngine integrados."""
        # Crear engines compartidos
        try:
            from app.engines.context_engine import ContextEngine
            from app.engines.data_engine import DataEngine

            data_engine = DataEngine({'sources': {}})
            context_engine = ContextEngine({})

            # Crear Strategy Engines
            momentum_engine = MomentumStrategyEngine({'rsi_period': 14})
            mean_reversion_engine = MeanReversionStrategyEngine({'z_score_period': 20})

            # Configurar engines compartidos
            momentum_engine.set_data_engine(data_engine)
            momentum_engine.set_context_engine(context_engine)

            mean_reversion_engine.set_data_engine(data_engine)
            mean_reversion_engine.set_context_engine(context_engine)

            # Verificar integración
            assert momentum_engine.data_engine_enabled is True
            assert momentum_engine.context_engine_enabled is True
            assert mean_reversion_engine.data_engine_enabled is True
            assert mean_reversion_engine.context_engine_enabled is True

            # Verificar status incluye engines
            momentum_status = momentum_engine.get_status()
            assert 'data_engine_enabled' in momentum_status
            assert 'context_engine_enabled' in momentum_status

            logger.info(
                "✅ Strategy Engines integrados correctamente con DataEngine y ContextEngine"
            )

        except ImportError as e:
            logger.warning(f"DataEngine o ContextEngine no disponibles: {e}")
            pytest.skip("DataEngine o ContextEngine no disponibles")

    def test_engine_metrics(self):
        """Test obtención de métricas."""
        config = {'learning_enabled': False}
        engine = MomentumStrategyEngine(config)

        metrics = engine.get_metrics()
        assert isinstance(metrics, dict)

        status = engine.get_status()
        assert isinstance(status, dict)
        assert 'learning_enabled' in status
        assert 'metrics' in status

    def test_feature_extraction_consistency(self):
        """Test que feature extraction es consistente."""
        engines = [
            MomentumStrategyEngine({'learning_enabled': False}),
            MeanReversionStrategyEngine({'learning_enabled': False}),
        ]

        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal("150.0"),
            ask=Decimal("150.1"),
            last=Decimal("150.05"),
            close=Decimal("150.05"),
            open=Decimal("149.0"),
            high=Decimal("151.0"),
            low=Decimal("148.0"),
            volume=Decimal("1000000"),
        )

        # Procesar para tener histórico
        for engine in engines:
            for _ in range(50):
                engine.generate_signals(quote)

        # Extraer features
        all_features = []
        for engine in engines:
            features = engine.extract_features(quote)
            assert isinstance(features, dict)
            all_features.append(features)

        # Verificar que cada engine extrae features apropiadas
        assert len(all_features) == len(engines)
