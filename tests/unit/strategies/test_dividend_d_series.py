"""Fase 4 parte 2 — dividend strategy fixes (hallazgos D04/D06/D07/D08/D09/D10).

Each test is the audit's own reproduction turned into the CORRECT behavior
(docs/audits/2026-10-24/auditoria_dividendos_D01-D12.md, §Hallazgos D04-D10).
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.strategies.dividend_core_satellite import DividendCoreSatelliteStrategy


def make_quote(symbol: str, ts: datetime, close: float, volume: float = 1_000_000.0):
    return SimpleNamespace(
        symbol=symbol,
        timestamp=ts,
        close=Decimal(str(close)),
        last=Decimal(str(close)),
        volume=Decimal(str(volume)),
    )


def side(sig) -> str:
    """Signal side as lowercase str, enum or not."""
    return str(getattr(sig.signal_type, "value", sig.signal_type)).lower()


def feed_history(strategy, symbol, days: int, start: datetime, close=100.0, volume=1_000_000.0):
    """Feed `days` daily bars; returns the signals emitted (warm-up only,
    signals_valid_from set far future so nothing fires)."""
    strategy.signals_valid_from = datetime.max
    for i in range(days):
        strategy.generate_signals(make_quote(symbol, start + timedelta(days=i), close, volume))
    strategy.signals_valid_from = None


def write_dividends(tmp_path: Path, symbol: str, events: list[tuple[str, str]]):
    tmp_path.mkdir(parents=True, exist_ok=True)
    with (tmp_path / f"{symbol}.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "amount", "currency", "source"])
        w.writeheader()
        w.writerows(
            {"date": d, "amount": a, "currency": "USD", "source": "test"} for d, a in events
        )


def strategy_with(tmp_path, **config) -> DividendCoreSatelliteStrategy:
    """Strategy whose distribution corpus is the tmp dir."""
    s = DividendCoreSatelliteStrategy({"name": "dividend_tracking", "enabled": True, **config})
    original_load = s._distributions

    def patched_load(symbol):
        from app.backtesting.dividends import load_distributions

        return [(e.ex_date, e.amount_per_share) for e in load_distributions(symbol, tmp_path)]

    s._distributions = patched_load
    del original_load
    return s


@pytest.fixture
def three_symbol_strategy():
    """SCHD+VIG core, VYM/DVY satellites, history fed, ready to rebalance."""
    s = DividendCoreSatelliteStrategy(
        {
            "name": "dividend_tracking",
            "enabled": True,
            "symbols": ["SCHD", "VIG", "VYM", "DVY"],
            "min_history": 10,
        }
    )
    start = datetime(2026, 1, 1)
    feed_history(s, "SCHD", 30, start)
    feed_history(s, "VIG", 30, start)
    feed_history(s, "VYM", 30, start, close=50.0, volume=2_000_000.0)
    feed_history(s, "DVY", 30, start, close=40.0, volume=3_000_000.0)
    return s


class TestD08OwnPricePerSignal:
    def test_each_signal_carries_its_own_price_and_volume(self, three_symbol_strategy):
        s = three_symbol_strategy
        # BND-like trigger bar at price 10 fires the rebalance: the buys of
        # SCHD(100) and VYM(50) must carry their OWN prices, not 10.
        signals = s.generate_signals(make_quote("SCHD", datetime(2026, 2, 15), 100.5))
        buys = {sig.symbol: sig for sig in signals if sig.symbol != "SCHD"}
        assert all(sig.symbol != "" for sig in signals)
        for sym, sig in buys.items():
            own = {"VIG": 100.0, "VYM": 50.0, "DVY": 40.0}[sym]
            assert float(sig.price) == pytest.approx(own, rel=1e-6), (
                f"{sym} priced at {sig.price}, expected its own last close {own}"
            )
        vym_sig = buys.get("VYM")
        if vym_sig:
            assert float(vym_sig.volume) == pytest.approx(2_000_000.0)


class TestD09SessionsNotCalendarDays:
    def test_rebalance_after_n_sessions(self):
        s = DividendCoreSatelliteStrategy(
            {
                "name": "d",
                "enabled": True,
                "symbols": ["SCHD"],
                "min_history": 3,
                "rebalance_days": 5,
            }
        )
        s.signals_valid_from = datetime.max
        base = datetime(2026, 1, 5)
        for i in range(5):
            s.generate_signals(make_quote("SCHD", base + timedelta(days=i), 100))
        s.signals_valid_from = None
        s.generate_signals(make_quote("SCHD", base + timedelta(days=5), 100))
        assert s._last_rebalance is not None  # first rebalance: readiness gate

        # 126 días naturales ≈ 90 sesiones: antes de 5 SESIONES más no hay
        # rebalance aunque pasen 6 días naturales
        s.signals_valid_from = datetime.max
        for i in range(4):
            s.generate_signals(make_quote("SCHD", base + timedelta(days=10 + i), 100))
        s.signals_valid_from = None
        assert not s._rebalance_due(base)
        s.generate_signals(make_quote("SCHD", base + timedelta(days=20), 100))
        assert s._sessions_since_rebalance == 0  # 5ª sesión → rebalanceó


class TestD10SmaSellSurvivesRebalance:
    def test_crash_on_rebalance_day_emits_exactly_one_sell(self):
        s = DividendCoreSatelliteStrategy(
            {
                "name": "d",
                "enabled": True,
                "symbols": ["SCHD"],
                "min_history": 5,
                "sma_guard_days": 3,
                "sma_guard_buffer": 0.02,
                "rebalance_days": 5,
            }
        )
        s.signals_valid_from = datetime.max
        base = datetime(2026, 1, 1)
        for i in range(10):
            s.generate_signals(make_quote("SCHD", base + timedelta(days=i), 100.0))
        s.signals_valid_from = None
        first = s.generate_signals(make_quote("SCHD", base + timedelta(days=10), 100.0))
        assert any(side(sig) == "buy" for sig in first)
        assert "SCHD" in s._holdings

        # 4 sesiones sanas más; la 5ª sesión ES el crash (rebalance debido
        # + SMA armada con precios pre-crash en su ventana)
        s.signals_valid_from = datetime.max
        for i in range(4):
            s.generate_signals(make_quote("SCHD", base + timedelta(days=11 + i), 100.0))
        s.signals_valid_from = None
        out = s.generate_signals(make_quote("SCHD", base + timedelta(days=15), 20.0))

        sells = [sig for sig in out if side(sig) == "sell"]
        buys_of_schd = [sig for sig in out if sig.symbol == "SCHD" and side(sig) == "buy"]
        # exactamente una venta (SMA) conservada por el rebalance que
        # coincide, y ninguna compra contradictoria del símbolo expulsado
        assert len(sells) == 1 and len(buys_of_schd) == 0
        assert "SCHD" not in s._holdings


class TestD06WeightsSumExplained:
    def test_weights_plus_cash_equal_one(self, three_symbol_strategy):
        s = three_symbol_strategy
        s.generate_signals(make_quote("SCHD", datetime(2026, 2, 15), 100.5))
        weights = s._target_weights
        assert weights, "rebalance should have computed weights"
        invested = sum(weights.values())
        assert invested <= s.target_exposure + 1e-6
        # pesos + caja explicada = 100% (el residuo queda declarado)
        assert invested + (1.0 - s.target_exposure) + s._weight_residual == pytest.approx(
            1.0, abs=1e-3
        )

    def test_clamp_redistributes(self):
        s = DividendCoreSatelliteStrategy(
            {
                "name": "d",
                "enabled": True,
                "symbols": ["SCHD", "VIG", "VYM"],
                "min_history": 3,
                "core_share": 0.9,
                "satellite_share": 0.05,
                "target_exposure": 0.95,
            }
        )
        weights = s._compute_weights({"SCHD", "VIG", "VYM"}, datetime.utcnow())
        assert all(0.05 - 1e-9 <= w <= 0.25 + 1e-9 for w in weights.values())
        assert sum(weights.values()) > 0.5  # la redistribución no evapora la manga


class TestD07CashIsTheDefaultShelter:
    def test_defensive_not_in_target_by_default(self, three_symbol_strategy):
        s = three_symbol_strategy
        # todos los cores salen por oso → el refugio por defecto es CAJA:
        # el defensivo (ausente del universo aquí) nunca se inventa
        target = s._desired_holdings(datetime(2026, 2, 15))
        assert "BND" not in target

    def test_opt_in_defensive_enters_when_core_frees(self):
        s = DividendCoreSatelliteStrategy(
            {
                "name": "d",
                "enabled": True,
                "symbols": ["SCHD", "BND"],
                "min_history": 3,
                "use_defensive_refuge": True,
                "lookback_days": 12,
                "skip_recent_days": 1,
            }
        )
        # historia sana → SCHD comprado y mantenido
        s.signals_valid_from = datetime.max
        base = datetime(2026, 1, 1)
        for i in range(12):
            s.generate_signals(make_quote("SCHD", base + timedelta(days=i), 100.0))
        s.signals_valid_from = None
        s.generate_signals(make_quote("SCHD", base + timedelta(days=12), 100.0))
        assert "SCHD" in s._holdings

        # oso profundo: momentum 12-1 = 60/100−1 = −40% < −15% → expulsado
        s.signals_valid_from = datetime.max
        for i in range(6):
            s.generate_signals(make_quote("SCHD", base + timedelta(days=13 + i), 60.0))
        s.signals_valid_from = None
        target = s._desired_holdings(base + timedelta(days=20))
        assert "SCHD" not in target
        assert "BND" in target


class TestD04PointInTimeYields:
    def test_yield_from_real_events_and_cuts_when_known(self, tmp_path):
        # HY1 repartió 4.00/año hasta el recorte: el evento de 2025-05-01
        # cae FUERA del trailing-12m en junio-2026 pero DENTRO en
        # febrero-2026 — el recorte entra en la decisión solo cuando se
        # conoce (point-in-time), nunca retroactivamente.
        write_dividends(
            tmp_path,
            "HY1",
            [("2025-05-01", "1.00"), ("2025-10-01", "1.00"), ("2026-01-05", "1.00")],
        )
        write_dividends(
            tmp_path,
            "HY2",
            [
                ("2025-07-01", "0.50"),
                ("2025-10-01", "0.50"),
                ("2026-01-05", "0.50"),
                ("2026-04-05", "0.50"),
            ],
        )
        s = strategy_with(tmp_path, symbols=["CORE1", "HY1", "HY2"], min_history=3)
        feed_history(s, "HY1", 20, datetime(2026, 1, 1), close=100.0)
        feed_history(s, "HY2", 20, datetime(2026, 1, 1), close=100.0)

        y1 = s._t12m_yield("HY1", datetime(2026, 6, 1))
        y2 = s._t12m_yield("HY2", datetime(2026, 6, 1))
        assert y1 == pytest.approx(2.00 / 100.0, abs=1e-9)  # mayo ya fuera
        assert y2 == pytest.approx(2.00 / 100.0, abs=1e-9)
        y1_early = s._t12m_yield("HY1", datetime(2026, 2, 1))
        assert y1_early == pytest.approx(3.00 / 100.0, abs=1e-9)
        assert y1_early > y1  # el recorte entra cuando se conoce, no antes

    def test_no_distribution_data_is_zero_not_invented(self, tmp_path):
        s = strategy_with(tmp_path, symbols=["SCHD", "VYM"], min_history=3)
        feed_history(s, "SCHD", 5, datetime(2026, 1, 1))
        assert s._t12m_yield("SCHD", datetime(2026, 2, 1)) == 0.0

    def test_core_weights_equal_without_yield_data(self, tmp_path):
        s = strategy_with(tmp_path, symbols=["AAA", "BBB", "HY1"], min_history=3)
        weights = s._compute_weights({"AAA", "BBB"}, datetime.utcnow())
        assert weights["AAA"] == pytest.approx(weights["BBB"])
