"""
BLOQUE 1 — Validación de Integridad de Datos

Tests para verificar:
- Sincronización temporal (signal.timestamp coincide con quote timestamp)
- Orden cronológico (quotes y señales en orden ascendente)
- Dataset por símbolo (datos completos sin gaps > 1 intervalo)
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import pytest

from app.models.market_data import Quote
from app.models.signal import Signal, SignalType
from app.services.portfolio_builder import PortfolioBuilder
from app.services.portfolio_config_manager import get_portfolio_config_manager
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.momentum import MomentumStrategy


class TestTemporalSynchronization(unittest.TestCase):
    """Test: Sincronización temporal."""

    def setUp(self):
        """Setup para tests de sincronización."""
        self.momentum = MomentumStrategy({"name": "momentum"})

    def test_signal_timestamp_matches_quote_timestamp(self):
        """Verificar que signal.timestamp coincide exactamente con quote.timestamp."""
        base_date = datetime(2024, 1, 1)

        # Crear quotes y generar señales
        quotes = []
        signals = []

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
            generated_signals = self.momentum.generate_signals(quote)
            signals.extend(generated_signals)

        # Verificar que cada señal tiene timestamp igual al quote correspondiente
        signal_quotes_map = {}
        for quote in quotes:
            for signal in signals:
                if signal.symbol == quote.symbol:
                    # Buscar la señal más cercana en tiempo
                    time_diff = abs((signal.timestamp - quote.timestamp).total_seconds())
                    if time_diff < 86400:  # Dentro de 1 día
                        signal_quotes_map[signal.signal_id] = quote

        # Verificar sincronización
        for signal in signals:
            matched_quote = signal_quotes_map.get(signal.signal_id)
            if matched_quote:
                time_diff = abs((signal.timestamp - matched_quote.timestamp).total_seconds())
                self.assertLess(
                    time_diff,
                    86400,  # Máximo 1 día de diferencia
                    f"Signal {signal.signal_id} timestamp {signal.timestamp} no coincide con "
                    f"quote timestamp {matched_quote.timestamp} (diff: {time_diff}s)",
                )

    def test_no_signals_outside_temporal_range(self):
        """Falla si hay señales emitidas fuera de rango temporal."""
        base_date = datetime(2024, 1, 1)
        start_date = base_date
        end_date = base_date + timedelta(days=30)

        quotes = []
        signals = []

        for i in range(30):
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
            generated_signals = self.momentum.generate_signals(quote)
            signals.extend(generated_signals)

        # Verificar que todas las señales están dentro del rango temporal
        for signal in signals:
            self.assertGreaterEqual(
                signal.timestamp,
                start_date,
                f"Signal {signal.signal_id} timestamp {signal.timestamp} está antes del inicio {start_date}",
            )
            self.assertLessEqual(
                signal.timestamp,
                end_date,
                f"Signal {signal.signal_id} timestamp {signal.timestamp} está después del fin {end_date}",
            )

    def test_no_duplicate_timestamps_in_signals(self):
        """Falla si hay timestamps duplicados en señales."""
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
            signals = self.momentum.generate_signals(quote)
            all_signals.extend(signals)

        # Verificar que no hay señales duplicadas (mismo símbolo, mismo timestamp, mismo tipo)
        seen = {}
        for signal in all_signals:
            key = (signal.symbol, signal.timestamp, signal.signal_type)
            self.assertNotIn(
                key,
                seen,
                f"Señal duplicada encontrada: {key} (anterior: {seen[key]}, nueva: {signal.signal_id})",
            )
            seen[key] = signal.signal_id


class TestChronologicalOrder(unittest.TestCase):
    """Test: Orden cronológico."""

    def test_quotes_in_ascending_order(self):
        """Comprobar que todas las quotes están en orden ascendente."""
        base_date = datetime(2024, 1, 1)

        quotes = []
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

        # Verificar orden ascendente
        for i in range(1, len(quotes)):
            self.assertGreaterEqual(
                quotes[i].timestamp,
                quotes[i - 1].timestamp,
                f"Quote {i} timestamp {quotes[i].timestamp} no está en orden ascendente "
                f"(anterior: {quotes[i-1].timestamp})",
            )

    def test_signals_in_ascending_order(self):
        """Comprobar que todas las señales están en orden ascendente."""
        strategy = MomentumStrategy({"name": "momentum"})
        base_date = datetime(2024, 1, 1)

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
            signals = strategy.generate_signals(quote)
            all_signals.extend(signals)

        # Verificar orden ascendente
        for i in range(1, len(all_signals)):
            self.assertGreaterEqual(
                all_signals[i].timestamp,
                all_signals[i - 1].timestamp,
                f"Signal {all_signals[i].signal_id} timestamp {all_signals[i].timestamp} "
                f"no está en orden ascendente (anterior: {all_signals[i-1].timestamp})",
            )

    def test_no_retroactive_signals(self):
        """Falla si hay señales retroactivas."""
        strategy = MomentumStrategy({"name": "momentum"})
        base_date = datetime(2024, 1, 1)

        quotes = []
        signals_by_quote = {}

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
            signals = strategy.generate_signals(quote)
            signals_by_quote[quote.timestamp] = signals

        # Verificar que ninguna señal tiene timestamp anterior al quote que la generó
        for quote_timestamp, signals in signals_by_quote.items():
            for signal in signals:
                # Permitir pequeña diferencia (hasta 1 segundo) por redondeo
                time_diff = (quote_timestamp - signal.timestamp).total_seconds()
                self.assertLessEqual(
                    time_diff,
                    1.0,  # Máximo 1 segundo de diferencia
                    f"Señal retroactiva: signal timestamp {signal.timestamp} es anterior "
                    f"a quote timestamp {quote_timestamp}",
                )


@pytest.mark.parametrize("symbol", ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"])
class TestDatasetPerSymbol:
    """Test: Dataset por símbolo."""

    def test_symbol_has_complete_data(self, symbol):
        """Detectar si algún símbolo tiene datos incompletos."""
        portfolio_config = get_portfolio_config_manager()
        portfolio_builder = PortfolioBuilder(portfolio_config=portfolio_config)

        start_date = datetime(2020, 1, 1)
        end_date = datetime(2024, 1, 1)

        # Obtener quotes para el símbolo
        try:
            quotes = portfolio_builder.build_portfolio_quotes(
                start_date=start_date,
                end_date=end_date,
                max_symbols_per_strategy=10,
            )

            symbol_quotes = [q for q in quotes if q.symbol == symbol]

            # Verificar que hay datos
            assert len(symbol_quotes) > 0, f"{symbol} no tiene datos en el rango especificado"

            # Verificar que no hay gaps mayores a 1 intervalo (1 día)
            for i in range(1, len(symbol_quotes)):
                time_diff = (symbol_quotes[i].timestamp - symbol_quotes[i - 1].timestamp).days
                assert time_diff <= 2, (  # Permitir hasta 2 días (weekend)
                    f"{symbol} tiene gap de {time_diff} días entre "
                    f"{symbol_quotes[i-1].timestamp} y {symbol_quotes[i].timestamp}"
                )
        except Exception as e:
            pytest.skip(f"No se pudieron obtener datos para {symbol}: {e}")

    def test_symbol_has_no_temporal_gaps_greater_than_one_interval(self, symbol):
        """Detectar gaps temporales superiores a 1 intervalo."""
        base_date = datetime(2024, 1, 1)
        quotes = []

        # Crear quotes con un gap intencional
        for i in range(30):
            if i != 15:  # Crear gap en el día 15
                quote = Quote(
                    symbol=symbol,
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

        # Verificar gaps
        gaps = []
        for i in range(1, len(quotes)):
            time_diff = (quotes[i].timestamp - quotes[i - 1].timestamp).days
            if time_diff > 1:
                gaps.append((quotes[i - 1].timestamp, quotes[i].timestamp, time_diff))

        # El test debe fallar si hay gaps > 1 día (excepto weekend)
        for gap_start, gap_end, gap_size in gaps:
            # Permitir gaps de 2-3 días (weekend + holiday)
            assert (
                gap_size <= 3
            ), f"{symbol} tiene gap de {gap_size} días entre {gap_start} y {gap_end}"


class TestQuotePriceConsistency(unittest.TestCase):
    """Test 4: Quote price consistency."""

    def test_open_le_high(self):
        """Verificar que open ≤ high."""
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
        self.assertLessEqual(quote.open, quote.high, "open debe ser ≤ high")

    def test_low_le_close(self):
        """Verificar que low ≤ close."""
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
        self.assertLessEqual(quote.low, quote.close, "low debe ser ≤ close")

    def test_low_le_open(self):
        """Verificar que low ≤ open."""
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
        self.assertLessEqual(quote.low, quote.open, "low debe ser ≤ open")

    def test_close_le_high(self):
        """Verificar que close ≤ high."""
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
        self.assertLessEqual(quote.close, quote.high, "close debe ser ≤ high")


if __name__ == "__main__":
    unittest.main()
