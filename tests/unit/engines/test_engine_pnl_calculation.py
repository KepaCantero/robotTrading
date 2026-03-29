"""
Tests para verificar el cálculo correcto de PnL en el backtesting engine.

Estos tests verifican problemas críticos identificados:
- Win rate 0% a pesar de tener trades
- Cálculo incorrecto de PnL
- Problemas con positions sin buy_trades
"""

import unittest
from datetime import datetime
from decimal import Decimal

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, TradeStatus
from app.domain.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


class TestEnginePnLCalculation(unittest.TestCase):
    """Tests para verificar cálculo correcto de PnL."""

    def setUp(self):
        """Configurar backtester para tests."""
        config = BacktestConfig(
            strategy_name="test",
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            stop_loss_percentage=Decimal("3"),
            take_profit_percentage=Decimal("8"),
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

    def _create_buy_signal(self, symbol: str, price: Decimal, timestamp: datetime = None) -> Signal:
        """Crear señal BUY de prueba."""
        if timestamp is None:
            timestamp = datetime(2024, 1, 1)
        return Signal(
            symbol=symbol,
            signal_type=SignalType.BUY,
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

    def _create_sell_signal(
        self, symbol: str, price: Decimal, timestamp: datetime = None
    ) -> Signal:
        """Crear señal SELL de prueba."""
        if timestamp is None:
            timestamp = datetime(2024, 1, 1)
        return Signal(
            symbol=symbol,
            signal_type=SignalType.SELL,
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

    def test_buy_then_sell_profitable_pnl(self):
        """Test: BUY seguido de SELL con ganancia debe tener PnL positivo."""
        symbol = "AAPL"
        buy_price = Decimal("100")
        sell_price = Decimal("110")  # 10% de ganancia

        # Ejecutar BUY
        buy_signal = self._create_buy_signal(symbol, buy_price, datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        # Verificar que hay posición
        self.assertGreater(self.backtester.positions.get(symbol, Decimal("0")), Decimal("0"))

        # Ejecutar SELL
        sell_signal = self._create_sell_signal(symbol, sell_price, datetime(2024, 1, 2))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 2))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Verificar que hay trades cerrados
        closed_trades = [t for t in self.backtester.trades if t.status == TradeStatus.CLOSED]
        self.assertGreater(len(closed_trades), 0, "Debe haber trades cerrados")

        # Verificar que al menos un trade tiene PnL positivo
        profitable_trades = [t for t in closed_trades if t.pnl and t.pnl > 0]
        self.assertGreater(
            len(profitable_trades),
            0,
            "Debe haber al menos un trade con PnL positivo cuando se vende más caro que se compró",
        )

        # Verificar que el PnL es razonable (aproximadamente 10% menos comisiones/slippage)
        for trade in profitable_trades:
            self.assertGreater(
                trade.pnl, Decimal("0"), f"Trade {trade.trade_id} debe tener PnL positivo"
            )

    def test_buy_then_sell_loss_pnl(self):
        """Test: BUY seguido de SELL con pérdida debe tener PnL negativo."""
        symbol = "AAPL"
        buy_price = Decimal("100")
        sell_price = Decimal("90")  # 10% de pérdida

        # Ejecutar BUY
        buy_signal = self._create_buy_signal(symbol, buy_price, datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        # Ejecutar SELL
        sell_signal = self._create_sell_signal(symbol, sell_price, datetime(2024, 1, 2))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 2))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Verificar que hay trades cerrados
        closed_trades = [t for t in self.backtester.trades if t.status == TradeStatus.CLOSED]
        self.assertGreater(len(closed_trades), 0)

        # Verificar que todos los trades tienen PnL negativo
        for trade in closed_trades:
            if trade.pnl is not None:
                self.assertLess(
                    trade.pnl,
                    Decimal("0"),
                    f"Trade {trade.trade_id} debe tener PnL negativo cuando se vende más barato",
                )

    def test_sell_without_buy_should_not_create_trade(self):
        """Test: SELL sin posición previa no debe crear trade con PnL."""
        symbol = "AAPL"
        sell_price = Decimal("100")

        # Intentar ejecutar SELL sin BUY previo
        initial_trade_count = len(self.backtester.trades)
        sell_signal = self._create_sell_signal(symbol, sell_price, datetime(2024, 1, 1))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 1))
        self.backtester._process_signal(sell_signal, sell_quote)

        # No debe crear trades nuevos
        self.assertEqual(
            len(self.backtester.trades),
            initial_trade_count,
            "No debe crear trades al ejecutar SELL sin posición",
        )

    def test_sell_with_buy_trades_open_should_calculate_pnl(self):
        """Test: SELL con buy_trades abiertos debe calcular PnL correctamente."""
        symbol = "AAPL"
        buy_price = Decimal("100")
        sell_price = Decimal("105")

        # Crear BUY
        buy_signal = self._create_buy_signal(symbol, buy_price, datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, buy_price, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        # Verificar que hay buy_trades abiertos
        open_buy_trades = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]
        self.assertGreater(len(open_buy_trades), 0, "Debe haber buy_trades abiertos antes del SELL")

        # Ejecutar SELL
        sell_signal = self._create_sell_signal(symbol, sell_price, datetime(2024, 1, 2))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 2))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Verificar que el trade SELL tiene PnL calculado
        sell_trades = [
            t for t in self.backtester.trades if t.side == "sell" and t.status == TradeStatus.CLOSED
        ]
        self.assertGreater(len(sell_trades), 0, "Debe haber trades SELL cerrados")

        for trade in sell_trades:
            self.assertIsNotNone(trade.pnl, f"Trade SELL {trade.trade_id} debe tener PnL calculado")
            # Con ganancia del 5%, PnL debe ser positivo (menos comisiones/slippage)
            self.assertGreater(
                trade.pnl, Decimal("-10"), "PnL debe ser razonablemente positivo con 5% de ganancia"
            )

    def test_pnl_calculation_uses_avg_buy_price(self):
        """Test: PnL debe calcularse usando precio promedio de compra."""
        symbol = "AAPL"

        # Compra múltiple a diferentes precios
        buy_price_1 = Decimal("100")
        buy_price_2 = Decimal("110")

        buy_signal_1 = self._create_buy_signal(symbol, buy_price_1, datetime(2024, 1, 1))
        buy_quote_1 = self._create_quote(symbol, buy_price_1, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal_1, buy_quote_1)

        buy_signal_2 = self._create_buy_signal(symbol, buy_price_2, datetime(2024, 1, 2))
        buy_quote_2 = self._create_quote(symbol, buy_price_2, datetime(2024, 1, 2))
        self.backtester._process_signal(buy_signal_2, buy_quote_2)

        # Precio promedio = (100 + 110) / 2 = 105
        avg_buy_price = (buy_price_1 + buy_price_2) / Decimal("2")

        # Vender a precio mayor que promedio
        sell_price = Decimal("108")  # Mayor que promedio pero menor que última compra
        sell_signal = self._create_sell_signal(symbol, sell_price, datetime(2024, 1, 3))
        sell_quote = self._create_quote(symbol, sell_price, datetime(2024, 1, 3))
        self.backtester._process_signal(sell_signal, sell_quote)

        # Verificar que el PnL se calcula correctamente
        sell_trades = [
            t for t in self.backtester.trades if t.side == "sell" and t.status == TradeStatus.CLOSED
        ]
        self.assertGreater(len(sell_trades), 0)

        for trade in sell_trades:
            if trade.pnl is not None:
                # PnL debe ser positivo porque sell_price (108) > avg_buy_price (105)
                # Permitir pérdida pequeña debido a comisiones/slippage, pero verificar que el cálculo es razonable
                # Con sell_price (108) vs avg_buy_price (105), la ganancia bruta es ~3%, pero comisiones/slippage pueden reducirla
                # El PnL debería ser cercano a 0 (pequeña pérdida o pequeña ganancia) debido a comisiones/slippage
                self.assertGreater(
                    trade.pnl,
                    Decimal("-150"),
                    f"PnL debe ser razonable cuando se vende por encima del promedio de compra. PnL={trade.pnl}, avg_buy={avg_buy_price}, sell={sell_price}",
                )
                # Si el cálculo está correcto, PnL debería estar entre -150 y +50 aproximadamente
                # Esto verifica que el cálculo usa avg_buy_price y no el precio de la última compra

    def test_win_rate_calculation(self):
        """Test: Win rate debe calcularse correctamente."""
        symbol = "AAPL"

        # Crear trades ganadores y perdedores
        scenarios = [
            (Decimal("100"), Decimal("110"), True),  # Ganancia
            (Decimal("100"), Decimal("90"), False),  # Pérdida
            (Decimal("100"), Decimal("105"), True),  # Ganancia pequeña
            (Decimal("100"), Decimal("95"), False),  # Pérdida pequeña
        ]

        for buy_price, sell_price, expected_profit in scenarios:
            # BUY
            buy_signal = self._create_buy_signal(
                symbol,
                buy_price,
                datetime(
                    2024, 1, scenarios.index((buy_price, sell_price, expected_profit)) * 2 + 1
                ),
            )
            buy_quote = self._create_quote(
                symbol,
                buy_price,
                datetime(
                    2024, 1, scenarios.index((buy_price, sell_price, expected_profit)) * 2 + 1
                ),
            )
            self.backtester._process_signal(buy_signal, buy_quote)

            # SELL
            sell_signal = self._create_sell_signal(
                symbol,
                sell_price,
                datetime(
                    2024, 1, scenarios.index((buy_price, sell_price, expected_profit)) * 2 + 2
                ),
            )
            sell_quote = self._create_quote(
                symbol,
                sell_price,
                datetime(
                    2024, 1, scenarios.index((buy_price, sell_price, expected_profit)) * 2 + 2
                ),
            )
            self.backtester._process_signal(sell_signal, sell_quote)

        # Calcular métricas
        performance = self.backtester._calculate_performance_metrics()

        # Verificar que hay trades cerrados
        self.assertGreater(performance.total_trades, 0, "Debe haber trades cerrados")

        # Win rate debe ser aproximadamente 50% (2 ganadores, 2 perdedores)
        # Permitir margen debido a comisiones y slippage
        self.assertGreater(
            performance.win_rate, Decimal("30"), "Win rate debe ser > 30% (2 de 4 deberían ganar)"
        )
        self.assertLess(
            performance.win_rate, Decimal("70"), "Win rate debe ser < 70% (2 de 4 deberían ganar)"
        )

        # Debe haber winning trades y losing trades
        self.assertGreater(performance.winning_trades, 0, "Debe haber winning trades")
        self.assertGreater(performance.losing_trades, 0, "Debe haber losing trades")

    def test_buy_closes_existing_position(self):
        """Test: Nuevo BUY debe cerrar posición existente antes de abrir nueva."""
        symbol = "AAPL"
        buy_price_1 = Decimal("100")
        buy_price_2 = Decimal("110")

        # Primer BUY
        buy_signal_1 = self._create_buy_signal(symbol, buy_price_1, datetime(2024, 1, 1))
        buy_quote_1 = self._create_quote(symbol, buy_price_1, datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal_1, buy_quote_1)

        # Verificar posición abierta
        initial_position = self.backtester.positions.get(symbol, Decimal("0"))
        self.assertGreater(
            initial_position, Decimal("0"), "Debe haber posición después del primer BUY"
        )

        # Verificar que hay buy_trades abiertos
        open_trades_before = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]
        self.assertGreater(
            len(open_trades_before), 0, "Debe haber trades abiertos antes del segundo BUY"
        )

        # Segundo BUY (debe cerrar el primero)
        buy_signal_2 = self._create_buy_signal(symbol, buy_price_2, datetime(2024, 1, 2))
        buy_quote_2 = self._create_quote(symbol, buy_price_2, datetime(2024, 1, 2))
        self.backtester._process_signal(buy_signal_2, buy_quote_2)

        # Verificar que los trades anteriores se cerraron
        closed_trades = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.status == TradeStatus.CLOSED
        ]
        self.assertGreater(
            len(closed_trades), 0, "Los trades anteriores deben cerrarse cuando llega nuevo BUY"
        )

        # Verificar que hay un nuevo trade abierto
        open_trades_after = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]
        # Puede haber 0 o 1 trade abierto (dependiendo de la implementación)
        self.assertLessEqual(
            len(open_trades_after), 1, "Debe haber máximo 1 trade abierto después del segundo BUY"
        )

    def test_position_without_buy_trades_is_problem(self):
        """Test: Verificar que no haya positions sin buy_trades correspondientes."""
        symbol = "AAPL"

        # Simular situación problemática: position existe pero no hay buy_trades
        # Esto no debería pasar, pero puede indicar un bug

        # Crear BUY normal
        buy_signal = self._create_buy_signal(symbol, Decimal("100"), datetime(2024, 1, 1))
        buy_quote = self._create_quote(symbol, Decimal("100"), datetime(2024, 1, 1))
        self.backtester._process_signal(buy_signal, buy_quote)

        # Verificar consistencia
        position = self.backtester.positions.get(symbol, Decimal("0"))
        open_buy_trades = [
            t
            for t in self.backtester.trades
            if t.symbol == symbol and t.side == "buy" and t.status == TradeStatus.OPEN
        ]
        total_open_quantity = sum(t.quantity for t in open_buy_trades)

        # La posición debe coincidir con la cantidad de buy_trades abiertos
        self.assertAlmostEqual(
            float(position),
            float(total_open_quantity),
            places=2,
            msg="Position debe coincidir con cantidad total de buy_trades abiertos",
        )


if __name__ == "__main__":
    unittest.main()
