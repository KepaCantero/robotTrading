"""
Test de Regresión para Momentum

Generado automáticamente por StrategyAuditor.
Valida coherencia de señales y parámetros.
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.market_data import Quote
from app.models.signal import SignalType
from app.strategies.momentum import MomentumStrategy


class TestMomentumRegression(unittest.TestCase):
    """Tests de regresión para momentum."""

    def setUp(self):
        """Setup para tests."""
        self.strategy = MomentumStrategy({"name": "momentum"})

    def test_no_duplicate_signals(self):
        """Verificar que no hay señales duplicadas."""
        base_date = datetime(2024, 1, 1)
        quotes = []
        all_signals = []

        for i in range(50):
            quote = Quote(
                symbol="AAPL",
                timestamp=base_date + timedelta(days=i),
                open=Decimal("200"),
                high=Decimal("202"),
                low=Decimal("198"),
                close=Decimal("200"),
                last=Decimal("200"),
                bid=Decimal("199.8"),
                ask=Decimal("200.2"),
                volume=Decimal("1000000"),
            )
            quotes.append(quote)
            signals = self.strategy.generate_signals(quote)
            all_signals.extend(signals)

        # Verificar no duplicados
        seen = set()
        for signal in all_signals:
            key = (signal.symbol, signal.timestamp, signal.signal_type)
            self.assertNotIn(key, seen, f"Señal duplicada: {signal.signal_id}")
            seen.add(key)

    def test_no_overlapping_signals(self):
        """Verificar que no hay BUY y SELL simultáneos."""
        base_date = datetime(2024, 1, 1)
        quotes = []
        all_signals = []

        for i in range(50):
            quote = Quote(
                symbol="AAPL",
                timestamp=base_date + timedelta(days=i),
                open=Decimal("200"),
                high=Decimal("202"),
                low=Decimal("198"),
                close=Decimal("200"),
                last=Decimal("200"),
                bid=Decimal("199.8"),
                ask=Decimal("200.2"),
                volume=Decimal("1000000"),
            )
            quotes.append(quote)
            signals = self.strategy.generate_signals(quote)
            all_signals.extend(signals)

        # Agrupar por timestamp
        from collections import defaultdict

        signals_by_time = defaultdict(list)
        for signal in all_signals:
            signals_by_time[signal.timestamp].append(signal)

        # Verificar no solapamiento
        for timestamp, signals_at_time in signals_by_time.items():
            signal_types = [s.signal_type for s in signals_at_time]
            if SignalType.BUY in signal_types and SignalType.SELL in signal_types:
                self.fail(f"Señales opuestas simultáneas en {timestamp}")

    def test_parameters_configured(self):
        """Verificar que los parámetros están configurados."""
        self.assertIsNotNone(self.strategy.stop_loss, "stop_loss debe estar configurado")
        self.assertIsNotNone(self.strategy.take_profit, "take_profit debe estar configurado")
        self.assertGreater(self.strategy.stop_loss, 0, "stop_loss debe ser > 0")
        self.assertGreater(self.strategy.take_profit, 0, "take_profit debe ser > 0")


if __name__ == "__main__":
    unittest.main()
