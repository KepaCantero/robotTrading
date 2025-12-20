"""
Tests específicos para diagnosticar el problema de win rate 0%.

Este test simula exactamente el escenario que causa el problema:
- Momentum ejecuta 420 trades pero win rate = 0.0%
- Todas las operaciones resultan en pérdidas
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, TradeStatus
from app.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


class TestWinRateBug(unittest.TestCase):
    """Tests específicos para diagnosticar win rate 0%."""

    def setUp(self):
        """Configurar backtester para tests."""
        config = BacktestConfig(
            strategy_name="test",
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
        )
        self.backtester = SimpleBacktester(config)

    def _create_quote(self, symbol: str, price: Decimal, timestamp: datetime = None) -> Quote:
        """Crear Quote de prueba."""
        if timestamp is None:
            timestamp = datetime(2024, 1, 1)
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
        self, symbol: str, signal_type: SignalType, price: Decimal, timestamp: datetime = None
    ) -> Signal:
        """Crear señal de prueba."""
        if timestamp is None:
            timestamp = datetime(2024, 1, 1)
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
            metadata={"strategy": "momentum"},
        )

    def test_sell_without_buy_trades_creates_zero_pnl(self):
        """Test: SELL sin buy_trades abiertos crea trade con PnL = 0."""
        symbol = "AAPL"
        sell_price = Decimal("100")

        # Simular situación problemática: position existe pero no hay buy_trades
        # Esto puede pasar si el position fue creado manualmente o hay un bug
        self.backtester.positions[symbol] = Decimal("100")  # Position fantasma

        # Intentar SELL
        sell_signal = self._create_signal(symbol, SignalType.SELL, sell_price, datetime(2024, 1, 1))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 1))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Verificar que NO se creó trade porque no hay posición real
        # (el engine debería verificar que hay buy_trades antes de ejecutar SELL)
        sell_trades = [t for t in self.backtester.trades if t.side == "sell"]
        # Si se crea trade, debería tener PnL = 0
        for trade in sell_trades:
            if trade.pnl is not None:
                self.assertEqual(
                    trade.pnl,
                    Decimal("0"),
                    "SELL sin buy_trades debe tener PnL = 0 (esto puede causar win rate 0% si todas son así)",
                )

    def test_multiple_buys_then_sell_calculates_correct_pnl(self):
        """Test: Múltiples BUY seguidos de SELL debe calcular PnL correctamente."""
        symbol = "AAPL"
        base_price = Decimal("100")

        # Crear múltiples BUY con precios diferentes
        for i in range(3):
            buy_price = base_price + Decimal(str(i * 5))  # 100, 105, 110
            buy_signal = self._create_signal(
                symbol, SignalType.BUY, buy_price, datetime(2024, 1, i + 1)
            )
            buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, i + 1))
            self.backtester._process_signal(buy_signal, buy_quote)

        # Precio promedio = (100 + 105 + 110) / 3 = 105
        avg_price = (Decimal("100") + Decimal("105") + Decimal("110")) / Decimal("3")

        # SELL a precio mayor que promedio
        sell_price = Decimal("108")  # Mayor que promedio (105)
        sell_signal = self._create_signal(symbol, SignalType.SELL, sell_price, datetime(2024, 1, 4))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 4))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Calcular métricas
        performance = self.backtester._calculate_performance_metrics()

        # Verificar que hay winning trades
        if performance.total_trades > 0:
            # Con sell_price (108) > avg_price (105), debería haber al menos una ganancia pequeña
            # (menos comisiones/slippage)
            # El win rate NO debería ser 0%
            self.assertGreater(
                performance.win_rate,
                Decimal("0"),
                f"Win rate no debe ser 0% cuando se vende por encima del promedio. "
                f"Win rate={performance.win_rate}%, winning={performance.winning_trades}, "
                f"total={performance.total_trades}",
            )

    def test_new_buy_closes_position_causing_loss(self):
        """Test: Nuevo BUY que cierra posición existente puede generar pérdida."""
        symbol = "AAPL"
        buy_price_1 = Decimal("100")
        buy_price_2 = Decimal("90")  # Precio más bajo

        # Primer BUY
        buy_signal_1 = self._create_signal(
            symbol, SignalType.BUY, buy_price_1, datetime(2024, 1, 1)
        )
        buy_quote_1 = self._create_quote(symbol, buy_price_1, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal_1, buy_quote_1)

        # Segundo BUY (cierra el primero al precio de mercado actual)
        # Si el precio bajó, esto genera pérdida
        buy_signal_2 = self._create_signal(
            symbol, SignalType.BUY, buy_price_2, datetime(2024, 1, 2)
        )
        buy_quote_2 = self._create_quote(symbol, buy_price_2, datetime(2024, 1, 2))
        self.backtester._process_signal(buy_signal_2, buy_quote_2)

        # Verificar que se cerró el primer trade con pérdida
        closed_trades = [t for t in self.backtester.trades if t.status == TradeStatus.CLOSED]
        losing_trades = [t for t in closed_trades if t.pnl and t.pnl < 0]

        # Debe haber al menos un trade cerrado con pérdida
        # (cuando se cierra la posición al precio más bajo)
        if closed_trades:
            # Al menos un trade debe tener PnL negativo porque el precio bajó
            self.assertGreater(
                len(losing_trades),
                0,
                "Al cerrar posición cuando el precio bajó, debe generar pérdida. "
                "Esto puede explicar por qué todas las operaciones resultan en pérdidas.",
            )

    def test_sell_immediately_after_buy_should_be_profitable(self):
        """Test: SELL inmediatamente después de BUY a precio mayor debe ser ganancia."""
        symbol = "AAPL"
        buy_price = Decimal("100")
        sell_price = Decimal("101")  # Pequeña ganancia

        # BUY
        buy_signal = self._create_signal(
            symbol, SignalType.BUY, buy_price, datetime(2024, 1, 1, 10, 0, 0)
        )
        buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, 1, 10, 0, 0))
        self.backtester._process_signal(buy_signal, buy_quote)

        # SELL inmediatamente después
        sell_signal = self._create_signal(
            symbol, SignalType.SELL, sell_price, datetime(2024, 1, 1, 10, 1, 0)
        )
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 1, 10, 1, 0))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Calcular métricas
        performance = self._calculate_performance_metrics()

        # Verificar que hay winning trades
        if performance.total_trades > 0:
            # Debe haber al menos un trade ganador
            self.assertGreater(
                performance.winning_trades,
                0,
                "Cuando se vende por encima del precio de compra, debe haber winning trades. "
                f"Win rate={performance.win_rate}%, winning={performance.winning_trades}, total={performance.total_trades}",
            )

    def _calculate_performance_metrics(self):
        """Helper para calcular métricas."""
        return self.backtester._calculate_performance_metrics()


if __name__ == "__main__":
    unittest.main()
