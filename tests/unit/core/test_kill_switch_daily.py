"""Circuit breaker diario del motor (kill switch, Hull Rule 13.1, FASE5).

El kill switch mide la pérdida de HOY (threshold default -5%), no la
acumulada desde el inicio: un día malo detiene el trading ese día y al día
siguiente el breaker arranca limpio. Antes sumaba todo el histórico del
proceso y bloqueaba el resto del backtest para siempre.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.services.compliance.compliance_engine import ComplianceEngine

T0 = datetime(2024, 3, 4, 10, 0)


def make_engine() -> ComplianceEngine:
    engine = ComplianceEngine()
    engine.set_starting_capital(100_000.0)
    return engine


def close_loss(engine: ComplianceEngine, when: datetime, pnl: float) -> None:
    engine.track_daily_pnl(
        symbol="SPY",
        side="SELL",
        quantity=D("10"),
        entry_price=D("100"),
        exit_price=D("100"),
        realized_pnl=pnl,
        trade_time=when,
    )


class TestDailyCircuitBreaker:
    def test_bad_day_trips_the_breaker(self):
        engine = make_engine()
        close_loss(engine, T0, -6_000.0)  # -6% del capital en un día
        assert engine.check_kill_switch() is True

    def test_rollover_resets_next_day(self):
        engine = make_engine()
        close_loss(engine, T0, -6_000.0)
        assert engine.check_kill_switch() is True
        # día siguiente: la misma pérdida YA no cuenta (solo la de hoy)
        close_loss(engine, T0 + timedelta(days=1), +100.0)
        assert engine.check_kill_switch() is False

    def test_losses_within_day_accumulate(self):
        engine = make_engine()
        close_loss(engine, T0, -3_000.0)
        assert engine.check_kill_switch() is False  # -3% < 5%
        close_loss(engine, T0 + timedelta(hours=2), -2_500.0)
        assert engine.check_kill_switch() is True  # -5.5% acumulado del día

    def test_small_daily_losses_never_trip(self):
        engine = make_engine()
        for day in range(30):  # un mes de días flojos no debe disparar nada
            close_loss(engine, T0 + timedelta(days=day), -400.0)  # -0.4%/día
        assert engine.check_kill_switch() is False
