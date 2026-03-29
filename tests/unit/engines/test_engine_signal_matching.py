"""
Tests para verificar el matching correcto de señales con market data.

Problemas identificados:
- Señales BUY generadas pero no ejecutadas
- Señales sin match con market data
- Timestamps incorrectos
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.domain.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


class TestSignalMatching(unittest.TestCase):
    """Tests para verificar matching de señales con market data."""

    def setUp(self):
        """Configurar backtester para tests."""
        config = BacktestConfig(
            strategy_name="test",
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
        )
        self.backtester = SimpleBacktester(config)

    def _create_quote(self, symbol: str, price: Decimal, timestamp: datetime) -> Quote:
        """Crear Quote de prueba."""
        return Quote(
            symbol=symbol,
            timestamp=timestamp,
            open=price,
            high=price * Decimal("1.01"),
            low=price * Decimal("0.99"),
            close=price,
            last=price,
            volume=Decimal("1000000"),
            bid=price * Decimal("0.999"),
            ask=price * Decimal("1.001"),
        )

    def _create_signal(
        self, symbol: str, signal_type: SignalType, price: Decimal, timestamp: datetime
    ) -> Signal:
        """Crear señal de prueba."""
        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=price,
            timestamp=timestamp,
            volume=Decimal("1"),
            metadata={"strategy": "test"},
        )

    def test_signal_matches_exact_timestamp(self):
        """Test: Señal con timestamp exacto debe ejecutarse."""
        symbol = "AAPL"
        price = Decimal("100")
        timestamp = datetime(2024, 1, 1, 10, 0, 0)

        # Crear señal y quote con mismo timestamp
        signal = self._create_signal(symbol, SignalType.BUY, price, timestamp)
        quote = self._create_quote(symbol, price, timestamp)

        # Procesar señal
        initial_capital = self.backtester.capital
        self.backtester._process_signal(signal, quote)

        # Verificar que se ejecutó (capital debe cambiar)
        self.assertNotEqual(
            self.backtester.capital, initial_capital, "Capital debe cambiar cuando se ejecuta BUY"
        )

        # Verificar que hay trade
        self.assertGreater(len(self.backtester.trades), 0, "Debe haber trade creado")

    def test_signal_matches_within_one_day_tolerance(self):
        """Test: Señal con timestamp dentro de 1 día de tolerancia debe ejecutarse."""
        symbol = "AAPL"
        price = Decimal("100")
        base_timestamp = datetime(2024, 1, 1, 10, 0, 0)

        # Crear señal un poco antes del quote
        signal = self._create_signal(
            symbol, SignalType.BUY, price, base_timestamp - timedelta(hours=12)
        )
        quote = self._create_quote(symbol, price, base_timestamp)

        # Procesar señal
        initial_trades = len(self.backtester.trades)
        self.backtester._process_signal(signal, quote)

        # Verificar que se ejecutó (debe crear trade)
        self.assertGreater(
            len(self.backtester.trades),
            initial_trades,
            "Debe ejecutar señal dentro de tolerancia de 1 día",
        )

    def test_signal_does_not_match_future_quote(self):
        """Test: Señal con timestamp futuro no debe ejecutarse en run_backtest."""
        symbol = "AAPL"
        price = Decimal("100")
        quote_timestamp = datetime(2024, 1, 1, 10, 0, 0)

        # Crear señal en el futuro (más de 1 día)
        signal = self._create_signal(
            symbol, SignalType.BUY, price, quote_timestamp + timedelta(days=2)
        )
        quote = self._create_quote(symbol, price, quote_timestamp)

        # Usar run_backtest que valida el matching
        result = self.backtester.run_backtest([quote], [signal])

        # Verificar que NO se ejecutó
        self.assertEqual(len(result.trades), 0, "No debe ejecutar señal del futuro (más de 1 día)")

    def test_signal_symbol_must_match_quote(self):
        """Test: Señal con symbol diferente no debe ejecutarse en run_backtest."""
        signal_symbol = "AAPL"
        quote_symbol = "MSFT"
        price = Decimal("100")
        timestamp = datetime(2024, 1, 1, 10, 0, 0)

        # Crear señal para un symbol y quote para otro
        signal = self._create_signal(signal_symbol, SignalType.BUY, price, timestamp)
        quote = self._create_quote(quote_symbol, price, timestamp)

        # Usar run_backtest que valida el matching
        result = self.backtester.run_backtest([quote], [signal])

        # Verificar que NO se ejecutó
        self.assertEqual(len(result.trades), 0, "No debe ejecutar señal con symbol diferente")

    def test_multiple_signals_same_timestamp(self):
        """Test: Múltiples señales con mismo timestamp deben ejecutarse."""
        symbol = "AAPL"
        price = Decimal("100")
        timestamp = datetime(2024, 1, 1, 10, 0, 0)

        # Crear múltiples señales
        signals = [
            self._create_signal(symbol, SignalType.BUY, price, timestamp),
            self._create_signal(symbol, SignalType.BUY, price, timestamp),
        ]
        quote = self._create_quote(symbol, price, timestamp)

        # Procesar señales
        initial_trades = len(self.backtester.trades)
        for signal in signals:
            self.backtester._process_signal(signal, quote)

        # Verificar que ambas se ejecutaron
        self.assertGreater(
            len(self.backtester.trades), initial_trades, "Debe ejecutar múltiples señales"
        )


class TestSignalExecutionOrder(unittest.TestCase):
    """Tests para verificar orden de ejecución de señales."""

    def setUp(self):
        """Configurar backtester para tests."""
        config = BacktestConfig(
            strategy_name="test",
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
        )
        self.backtester = SimpleBacktester(config)

    def _create_quote(self, symbol: str, price: Decimal, timestamp: datetime) -> Quote:
        """Crear Quote de prueba."""
        return Quote(
            symbol=symbol,
            timestamp=timestamp,
            open=price,
            high=price * Decimal("1.01"),
            low=price * Decimal("0.99"),
            close=price,
            last=price,
            volume=Decimal("1000000"),
            bid=price * Decimal("0.999"),
            ask=price * Decimal("1.001"),
        )

    def _create_signal(
        self, symbol: str, signal_type: SignalType, price: Decimal, timestamp: datetime
    ) -> Signal:
        """Crear señal de prueba."""
        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=price,
            timestamp=timestamp,
            volume=Decimal("1"),
            metadata={"strategy": "test"},
        )

    def test_buy_before_sell_creates_valid_trade(self):
        """Test: BUY seguido de SELL debe crear trade válido con PnL."""
        symbol = "AAPL"
        buy_price = Decimal("100")
        sell_price = Decimal("110")

        # BUY primero
        buy_signal = self._create_signal(symbol, SignalType.BUY, buy_price, datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        # Verificar posición
        self.assertGreater(self.backtester.positions.get(symbol, Decimal("0")), Decimal("0"))

        # SELL después
        sell_signal = self._create_signal(symbol, SignalType.SELL, sell_price, datetime(2024, 1, 2))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 2))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Verificar trade cerrado con PnL
        closed_trades = [t for t in self.backtester.trades if t.status.value == "closed"]
        self.assertGreater(len(closed_trades), 0)

        # Al menos un trade debe tener PnL positivo
        profitable = [t for t in closed_trades if t.pnl and t.pnl > 0]
        self.assertGreater(
            len(profitable), 0, "Debe haber trade con PnL positivo cuando se vende más caro"
        )

    def test_sell_before_buy_should_not_create_trade(self):
        """Test: SELL antes de BUY no debe crear trade."""
        symbol = "AAPL"
        sell_price = Decimal("100")
        buy_price = Decimal("110")

        # Intentar SELL primero (sin posición)
        sell_signal = self._create_signal(symbol, SignalType.SELL, sell_price, datetime(2024, 1, 1))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 1))
        self.backtester._process_signal(sell_signal, sell_quote)

        initial_trades = len(self.backtester.trades)

        # Luego BUY
        buy_signal = self._create_signal(symbol, SignalType.BUY, buy_price, datetime(2024, 1, 2))
        buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, 2))
        self.backtester._process_signal(buy_signal, buy_quote)

        # El SELL no debe haber creado trade
        # Solo el BUY debe crear trade
        trades_after = len(self.backtester.trades)
        self.assertGreater(trades_after, initial_trades, "BUY debe crear trade")
        # Pero no debe haber más trades que el BUY (SELL sin posición no crea trade)
        self.assertLessEqual(
            trades_after, initial_trades + 1, "SELL sin posición no debe crear trade"
        )


if __name__ == "__main__":
    unittest.main()
