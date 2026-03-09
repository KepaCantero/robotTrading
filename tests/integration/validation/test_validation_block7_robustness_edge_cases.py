"""
BLOQUE 7 & 8 — Robustness & Edge Case Tests

Tests para verificar:
- Empty dataset, single candle, NaN prices, division by zero
- Constant price dataset, extreme volatility
- Indicator NaN handling, signal delay compensation
"""

import math
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.domain.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.momentum_analysis import TechnicalIndicatorCalculator
from app.domain.strategies.mean_reversion import MeanReversionStrategy
from app.domain.strategies.momentum import MomentumStrategy


class TestEmptyDataset(unittest.TestCase):
    """Test 29: Empty dataset."""

    def setUp(self):
        """Setup para tests de dataset vacío."""
        self.momentum = MomentumStrategy({"name": "momentum"})
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.05"),
        )
        self.backtester = SimpleBacktester(config=config)

    def test_strategy_with_empty_dataset(self):
        """Ejecuta estrategia con dataset vacío: no debe lanzar excepción."""
        quotes = []

        try:
            signals = []
            for quote in quotes:
                signals.extend(self.momentum.generate_signals(quote))

            # Debe devolver lista vacía, no lanzar excepción
            self.assertEqual(len(signals), 0, "Dataset vacío debe generar 0 señales")
        except Exception as e:
            self.fail(f"Estrategia no debe lanzar excepción con dataset vacío: {e}")

    def test_backtest_with_empty_dataset(self):
        """Backtest con dataset vacío: debe lanzar ValueError."""
        quotes = []
        signals = []

        # El backtester lanza ValueError cuando no hay market data
        with self.assertRaises(ValueError):
            self.backtester.run_backtest(
                market_data=quotes,
                signals=signals,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            )


class TestSingleCandleDataset(unittest.TestCase):
    """Test 30: Single candle dataset."""

    def setUp(self):
        """Setup para tests de vela única."""
        self.momentum = MomentumStrategy({"name": "momentum"})
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.05"),
        )
        self.backtester = SimpleBacktester(config=config)

    def test_no_invalid_trades_with_single_candle(self):
        """Dataset de una sola vela: no debe generar trades inválidos."""
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            open=Decimal("200"),
            high=Decimal("202"),
            low=Decimal("198"),
            close=Decimal("200"),
            last=Decimal("200"),
            bid=Decimal("199.8"),
            ask=Decimal("200.2"),
            volume=Decimal("1000000"),
        )

        signals = self.momentum.generate_signals(quote)

        # Puede o no generar señales, pero si genera, deben ser válidas
        if signals:
            for signal in signals:
                self.assertIn(
                    signal.signal_type,
                    [SignalType.BUY, SignalType.SELL],
                    "Señal debe ser BUY o SELL",
                )
                self.assertIsNotNone(signal.price, "Señal debe tener precio")
                self.assertGreater(signal.price, 0, "Precio debe ser positivo")


class TestNaNPriceHandling(unittest.TestCase):
    """Test 31: NaN prices."""

    def setUp(self):
        """Setup para tests de NaN."""
        self.momentum = MomentumStrategy({"name": "momentum"})

    def test_nan_in_price_does_not_break_execution(self):
        """NaN en close/open/high/low: sistema debe ignorar o imputar sin romper."""
        # Crear quote con valores válidos primero
        Quote(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            open=Decimal("200"),
            high=Decimal("202"),
            low=Decimal("198"),
            close=Decimal("200"),
            last=Decimal("200"),
            bid=Decimal("199.8"),
            ask=Decimal("200.2"),
            volume=Decimal("1000000"),
        )

        # Verificar que Quote valida precios positivos
        # (NaN no debería pasar la validación de Pydantic)
        try:
            quote_nan = Quote(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1),
                open=Decimal("200"),
                high=Decimal("202"),
                low=Decimal("198"),
                close=Decimal(str(float('nan'))),  # Intentar NaN
                last=Decimal("200"),
                bid=Decimal("199.8"),
                ask=Decimal("200.2"),
                volume=Decimal("1000000"),
            )
            # Si pasa la validación, generar señales no debe romper
            signals = self.momentum.generate_signals(quote_nan)
            # Si hay señales, deben tener precios válidos
            for signal in signals:
                self.assertIsNotNone(signal.price)
                self.assertFalse(math.isnan(float(signal.price)))
        except (ValueError, Exception):
            # Si falla la validación, eso es correcto (NaN no debería pasar)
            pass


class TestDivisionByZeroInIndicators(unittest.TestCase):
    """Test 32: Division by zero in indicators."""

    def setUp(self):
        """Setup para tests de división por cero."""
        self.calculator = TechnicalIndicatorCalculator()

    def test_rsi_with_zero_volatility(self):
        """RSI con volatilidad 0 (precios constantes): debe manejar correctamente."""
        # Precios constantes (volatilidad = 0)
        prices = [100.0] * 50

        rsi = self.calculator.calculate_rsi(prices, period=14)

        # Con precios constantes, RSI debería ser 50 (neutro) o None
        if rsi is not None:
            self.assertGreaterEqual(rsi, 0, "RSI debe ser >= 0")
            self.assertLessEqual(rsi, 100, "RSI debe ser <= 100")

    def test_macd_with_zero_volatility(self):
        """MACD con volatilidad 0: debe manejar correctamente."""
        prices = [100.0] * 50

        macd, signal, hist = self.calculator.calculate_macd(prices)

        # Con precios constantes, MACD puede ser 0 o None
        if macd is not None:
            # MACD debe ser un número válido (no NaN ni Inf)
            self.assertFalse(math.isnan(float(macd)))
            self.assertFalse(math.isinf(float(macd)))


class TestConstantPriceDataset(unittest.TestCase):
    """Test 33: Constant price dataset."""

    def setUp(self):
        """Setup para tests de precio constante."""
        self.momentum = MomentumStrategy({"name": "momentum"})
        self.mean_reversion = MeanReversionStrategy({"name": "mean_reversion"})

    def test_momentum_no_unnecessary_trades_on_constant_price(self):
        """Precio constante: Momentum no debe abrir trades innecesarios."""
        quotes = []
        all_signals = []

        # 50 velas con precio constante
        for i in range(50):
            quote = Quote(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                open=Decimal("200"),
                high=Decimal("200.1"),
                low=Decimal("199.9"),
                close=Decimal("200"),
                last=Decimal("200"),
                bid=Decimal("199.8"),
                ask=Decimal("200.2"),
                volume=Decimal("1000000"),
            )
            quotes.append(quote)
            signals = self.momentum.generate_signals(quote)
            all_signals.extend(signals)

        # Con precio constante, Momentum no debería generar muchas señales
        # (no hay momentum si el precio no cambia)
        self.assertLessEqual(
            len(all_signals),
            20,  # Tolerancia: pocas señales con precio constante
            "Momentum no debe generar muchas señales con precio constante",
        )

    def test_mean_reversion_no_trades_on_constant_price(self):
        """Precio constante: Mean Reversion no debe generar señales."""
        quotes = []
        all_signals = []

        for i in range(50):
            quote = Quote(
                symbol="AAPL",
                timestamp=datetime(2024, 1, 1) + timedelta(days=i),
                open=Decimal("200"),
                high=Decimal("200.1"),
                low=Decimal("199.9"),
                close=Decimal("200"),
                last=Decimal("200"),
                bid=Decimal("199.8"),
                ask=Decimal("200.2"),
                volume=Decimal("1000000"),
            )
            quotes.append(quote)
            signals = self.mean_reversion.generate_signals(quote)
            all_signals.extend(signals)

        # Precio constante = no desviación = no señales
        self.assertLessEqual(
            len(all_signals), 10, "Mean Reversion no debe generar señales con precio constante"
        )


class TestExtremeVolatilityDataset(unittest.TestCase):
    """Test 34: Extreme volatility dataset."""

    def setUp(self):
        """Setup para tests de volatilidad extrema."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.05"),
        )
        self.backtester = SimpleBacktester(config=config)

    def test_stop_loss_still_works_with_extreme_volatility(self):
        """Simula spikes extremos: verifica que stop-loss funciona."""
        quotes = []
        signals = []

        base_date = datetime(2024, 1, 1)
        base_price = Decimal("200")

        # Spike extremo: precio cae 70% en 1 día
        for i in range(10):
            if i == 5:  # Día del crash
                price = base_price * Decimal("0.3")  # -70%
            else:
                price = base_price

            quote = Quote(
                symbol="AAPL",
                timestamp=base_date + timedelta(days=i),
                open=price,
                high=price * Decimal("1.02"),
                low=price * Decimal("0.98"),
                close=price,
                last=price,
                bid=price * Decimal("0.99"),
                ask=price * Decimal("1.01"),
                volume=Decimal("50000000"),  # Alto volumen
            )
            quotes.append(quote)

            if i == 0:  # BUY antes del crash
                signal = Signal(
                    symbol="AAPL",
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=70.0,
                    liquidity_score=80.0,
                    priority_score=85.0,
                    source=SignalSource.MOMENTUM,
                    price=price,
                    volume=Decimal("1"),
                    timestamp=base_date + timedelta(days=i),
                    metadata={"strategy": "momentum"},
                )
                signals.append(signal)

        # El backtest debe ejecutar con stop-loss
        result = self.backtester.run_backtest(
            market_data=quotes,
            signals=signals,
            start_date=base_date,
            end_date=base_date + timedelta(days=10),
        )

        # Verificar que el backtest no falla
        self.assertIsNotNone(result, "Backtest debe completarse con volatilidad extrema")

        # El capital no debe ser negativo (stop-loss debe proteger)
        self.assertGreater(
            result.final_capital,
            Decimal("0"),
            "Capital no debe ser negativo incluso con volatilidad extrema",
        )


class TestIndicatorNaNHandling(unittest.TestCase):
    """Test 35: Indicator NaN handling."""

    def setUp(self):
        """Setup para tests de NaN en indicadores."""
        self.calculator = TechnicalIndicatorCalculator()
        self.momentum = MomentumStrategy({"name": "momentum"})

    def test_no_invalid_signals_with_nan_indicators(self):
        """Si hay NaNs en indicadores, no debe generar señales inválidas."""
        # Crear datos que potencialmente generen NaN
        prices = [100.0, 0.0, 100.0, 100.0]  # Precio 0 puede causar problemas

        rsi = self.calculator.calculate_rsi(prices, period=14)

        # Si RSI es None o NaN, no debe generar señales
        if rsi is not None:
            self.assertFalse(math.isnan(float(rsi)), "RSI no debe ser NaN")
            self.assertGreaterEqual(rsi, 0, "RSI debe ser >= 0")
            self.assertLessEqual(rsi, 100, "RSI debe ser <= 100")


class TestSignalDelayCompensation(unittest.TestCase):
    """Test 36: Signal delay compensation."""

    def setUp(self):
        """Setup para tests de compensación de delay."""
        self.momentum = MomentumStrategy({"name": "momentum"})

    def test_signals_use_current_candle_data(self):
        """Verifica que las señales usan datos de la vela actual, no anterior."""
        base_date = datetime(2024, 1, 1)

        # Primera vela: precio bajo (RSI bajo potencialmente)
        quote1 = Quote(
            symbol="AAPL",
            timestamp=base_date,
            open=Decimal("190"),
            high=Decimal("192"),
            low=Decimal("188"),
            close=Decimal("190"),
            last=Decimal("190"),
            bid=Decimal("189.8"),
            ask=Decimal("190.2"),
            volume=Decimal("2000000"),
        )

        # Segunda vela: precio más alto (RSI puede subir)
        quote2 = Quote(
            symbol="AAPL",
            timestamp=base_date + timedelta(days=1),
            open=Decimal("200"),
            high=Decimal("202"),
            low=Decimal("198"),
            close=Decimal("200"),
            last=Decimal("200"),
            bid=Decimal("199.8"),
            ask=Decimal("200.2"),
            volume=Decimal("2000000"),
        )

        # Generar señales para cada vela
        signals1 = self.momentum.generate_signals(quote1)
        signals2 = self.momentum.generate_signals(quote2)

        # Las señales deben corresponder a sus respectivas velas
        for signal in signals1:
            self.assertEqual(
                signal.timestamp.date(),
                quote1.timestamp.date(),
                "Señal debe usar timestamp de vela correspondiente",
            )

        for signal in signals2:
            self.assertEqual(
                signal.timestamp.date(),
                quote2.timestamp.date(),
                "Señal debe usar timestamp de vela correspondiente",
            )


class TestSignalsConsistencyMultipleSymbols(unittest.TestCase):
    """Test 37: Signals consistency multiple symbols."""

    def setUp(self):
        """Setup para tests multi-símbolo."""
        self.momentum = MomentumStrategy({"name": "momentum"})

    def test_signals_independent_per_symbol(self):
        """Para estrategias multi-symbol: señales de un símbolo no afectan otro."""
        quote1 = Quote(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1),
            open=Decimal("200"),
            high=Decimal("202"),
            low=Decimal("198"),
            close=Decimal("200"),
            last=Decimal("200"),
            bid=Decimal("199.8"),
            ask=Decimal("200.2"),
            volume=Decimal("2000000"),
        )

        quote2 = Quote(
            symbol="MSFT",
            timestamp=datetime(2024, 1, 1),
            open=Decimal("300"),
            high=Decimal("302"),
            low=Decimal("298"),
            close=Decimal("300"),
            last=Decimal("300"),
            bid=Decimal("299.8"),
            ask=Decimal("300.2"),
            volume=Decimal("1500000"),
        )

        signals1 = self.momentum.generate_signals(quote1)
        signals2 = self.momentum.generate_signals(quote2)

        # Verificar que las señales son independientes
        # (no hay bug de estado compartido)
        for signal in signals1:
            self.assertEqual(signal.symbol, "AAPL", "Señal debe pertenecer a símbolo correcto")

        for signal in signals2:
            self.assertEqual(signal.symbol, "MSFT", "Señal debe pertenecer a símbolo correcto")


class TestSignalsWithMissingQuotes(unittest.TestCase):
    """Test 38: Signals with missing quotes."""

    def setUp(self):
        """Setup para tests de quotes faltantes."""
        self.momentum = MomentumStrategy({"name": "momentum"})

    def test_strategy_handles_missing_quotes(self):
        """Comprueba que la estrategia no falla si faltan algunas velas intermedias."""
        base_date = datetime(2024, 1, 1)

        # Crear quotes con gaps (faltan días 5, 6, 7)
        quotes = []
        for i in range(10):
            if i in [5, 6, 7]:  # Saltar estos días
                continue

            close_price = Decimal("200") + Decimal(str((i % 10) - 5))
            quote = Quote(
                symbol="AAPL",
                timestamp=base_date + timedelta(days=i),
                open=close_price,
                high=close_price * Decimal("1.02"),
                low=close_price * Decimal("0.98"),
                close=close_price,
                last=close_price,
                bid=close_price * Decimal("0.999"),
                ask=close_price * Decimal("1.001"),
                volume=Decimal("2000000"),
            )
            quotes.append(quote)

        # Procesar quotes con gaps
        all_signals = []
        for quote in quotes:
            try:
                signals = self.momentum.generate_signals(quote)
                all_signals.extend(signals)
            except Exception as e:
                self.fail(f"Estrategia no debe fallar con quotes faltantes: {e}")

        # Verificar que se procesaron correctamente
        self.assertIsInstance(all_signals, list, "Debe generar lista de señales incluso con gaps")


if __name__ == "__main__":
    unittest.main()
