"""
Tests para verificar gestión correcta de posiciones en el engine.

Problemas identificados:
- Positions sin buy_trades correspondientes
- Posiciones que no se cierran correctamente
- Problemas al cerrar posición antes de nuevo BUY
"""

import unittest
from datetime import datetime
from decimal import Decimal

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, TradeStatus
from app.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


class TestPositionManagement(unittest.TestCase):
    """Tests para verificar gestión de posiciones."""

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
            metadata={"strategy": "test"},
        )

    def test_position_consistency_after_buy(self):
        """Test: Position debe ser consistente con buy_trades después de BUY."""
        symbol = "AAPL"
        price = Decimal("100")

        # Ejecutar BUY
        buy_signal = self._create_signal(symbol, SignalType.BUY, price, datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, price, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        # Verificar consistencia
        position = self.backtester.positions.get(symbol, Decimal("0"))
        open_buy_trades = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]
        total_open_quantity = sum(t.quantity for t in open_buy_trades)

        self.assertAlmostEqual(
            float(position),
            float(total_open_quantity),
            places=2,
            msg="Position debe coincidir con cantidad total de buy_trades abiertos",
        )

    def test_position_zeroed_after_sell(self):
        """Test: Position debe ser 0 después de vender toda la posición."""
        symbol = "AAPL"
        buy_price = Decimal("100")
        sell_price = Decimal("110")

        # BUY
        buy_signal = self._create_signal(symbol, SignalType.BUY, buy_price, datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        # Verificar posición existe
        position_before = self.backtester.positions.get(symbol, Decimal("0"))
        self.assertGreater(position_before, Decimal("0"))

        # SELL
        sell_signal = self._create_signal(symbol, SignalType.SELL, sell_price, datetime(2024, 1, 2))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 2))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Verificar posición es 0 o muy pequeña (permitir errores de precisión)
        position_after = self.backtester.positions.get(symbol, Decimal("0"))
        self.assertAlmostEqual(
            float(position_after),
            0.0,
            places=2,
            msg="Position debe ser 0 después de vender toda la posición",
        )

    def test_new_buy_closes_existing_position(self):
        """Test: Nuevo BUY debe cerrar posición existente completamente."""
        symbol = "AAPL"
        buy_price_1 = Decimal("100")
        buy_price_2 = Decimal("110")

        # Primer BUY
        buy_signal_1 = self._create_signal(
            symbol, SignalType.BUY, buy_price_1, datetime(2024, 1, 1)
        )
        buy_quote_1 = self._create_quote(symbol, buy_price_1, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal_1, buy_quote_1)

        # Verificar posición existe
        position_before = self.backtester.positions.get(symbol, Decimal("0"))
        self.assertGreater(position_before, Decimal("0"))

        # Verificar buy_trades abiertos
        open_trades_before = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]
        self.assertGreater(len(open_trades_before), 0)

        # Segundo BUY (debe cerrar el primero)
        buy_signal_2 = self._create_signal(
            symbol, SignalType.BUY, buy_price_2, datetime(2024, 1, 2)
        )
        buy_quote_2 = self._create_quote(symbol, buy_price_2, datetime(2024, 1, 2))
        self.backtester._process_signal(buy_signal_2, buy_quote_2)

        # Verificar que los trades anteriores se cerraron
        closed_trades = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.status == TradeStatus.CLOSED
        ]
        self.assertGreater(len(closed_trades), 0, "Los trades anteriores deben cerrarse")

        # Verificar que hay máximo 1 trade abierto
        open_trades_after = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]
        self.assertLessEqual(len(open_trades_after), 1, "Debe haber máximo 1 trade abierto")

    def test_no_position_without_buy_trades(self):
        """Test: No debe haber position sin buy_trades correspondientes."""
        symbol = "AAPL"
        price = Decimal("100")

        # Crear BUY
        buy_signal = self._create_signal(symbol, SignalType.BUY, price, datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, price, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        # Verificar consistencia
        position = self.backtester.positions.get(symbol, Decimal("0"))
        open_buy_trades = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]

        # Si hay posición, debe haber buy_trades
        if position > 0:
            self.assertGreater(
                len(open_buy_trades),
                0,
                "Si hay position > 0, debe haber buy_trades abiertos correspondientes",
            )

        # Si no hay buy_trades, no debe haber posición
        if len(open_buy_trades) == 0:
            self.assertAlmostEqual(
                float(position),
                0.0,
                places=2,
                msg="Si no hay buy_trades abiertos, position debe ser 0",
            )

    def test_partial_sell_maintains_consistency(self):
        """Test: Venta parcial debe mantener consistencia position/buy_trades."""
        symbol = "AAPL"
        buy_price = Decimal("100")
        sell_price = Decimal("110")

        # BUY
        buy_signal = self._create_signal(symbol, SignalType.BUY, buy_price, datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        self.backtester.positions.get(symbol, Decimal("0"))

        # SELL parcial (esto depende de cómo se calcula sell_quantity)
        sell_signal = self._create_signal(symbol, SignalType.SELL, sell_price, datetime(2024, 1, 2))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 2))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Verificar que la posición restante es consistente
        remaining_position = self.backtester.positions.get(symbol, Decimal("0"))
        open_buy_trades = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]
        total_open_quantity = sum(t.quantity for t in open_buy_trades)

        # Position restante debe coincidir con buy_trades abiertos
        self.assertAlmostEqual(
            float(remaining_position),
            float(total_open_quantity),
            places=2,
            msg="Position restante debe coincidir con buy_trades abiertos después de venta parcial",
        )


if __name__ == "__main__":
    unittest.main()
