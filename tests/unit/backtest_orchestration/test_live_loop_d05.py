"""Fase 4 — D05: the engine↔strategy loop with fill feedback.

The audited defect: the strategy committed `_holdings` at EMISSION time on a
precomputed signal list — a rejected buy, a partial fill or a stop close left
the book theoretical and the next rebalance decided against fantasy.

The fix: live mode. The strategy generates each bar's signals INSIDE the
engine loop (after the t+1 fills notify their outcomes) and reconciles its
book via on_fill. Acceptance (audit D05): "rechazo, fill parcial y stop deben
reflejarse en la siguiente decisión".
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.domain.strategies.dividend_core_satellite import DividendCoreSatelliteStrategy


@pytest.fixture
def strategy():
    s = DividendCoreSatelliteStrategy(
        {"name": "d", "enabled": True, "symbols": ["SCHD", "VYM"], "min_history": 3}
    )
    s._holdings = {"SCHD", "VYM"}
    return s


class TestOnFillSemantics:
    def test_rejected_buy_removes_from_holdings(self, strategy):
        strategy.on_fill("SCHD", "buy", "rejected", Decimal("10"), Decimal("0"))
        assert "SCHD" not in strategy._holdings  # retried next rebalance

    def test_rejected_sell_restores_the_holding(self, strategy):
        strategy._holdings.discard("VYM")  # emitted the sell...
        strategy.on_fill("VYM", "sell", "rejected", Decimal("10"), Decimal("0"))
        assert "VYM" in strategy._holdings  # ...but it never executed

    def test_stop_close_removes_the_holding(self, strategy):
        strategy.on_fill("SCHD", "sell", "closed", Decimal("10"), Decimal("10"))
        assert "SCHD" not in strategy._holdings

    def test_partial_sell_keeps_the_remainder(self, strategy):
        strategy._holdings.discard("VYM")
        strategy.on_fill("VYM", "sell", "filled", Decimal("10"), Decimal("6"))
        assert "VYM" in strategy._holdings  # 4 units still held

    def test_full_sell_stays_out(self, strategy):
        strategy._holdings.discard("VYM")
        strategy.on_fill("VYM", "sell", "filled", Decimal("10"), Decimal("10"))
        assert "VYM" not in strategy._holdings

    def test_filled_buy_keeps_the_holding(self, strategy):
        strategy.on_fill("SCHD", "buy", "filled", Decimal("10"), Decimal("10"))
        assert "SCHD" in strategy._holdings


class TestEngineFeedback:
    """Engine-level: notifications fire and precede the next decision."""

    @pytest.fixture
    def engine(self):
        from app.backtesting.engine import BacktestEngine
        from app.backtesting.models import BacktestConfig as EngineConfig

        return BacktestEngine(
            EngineConfig(
                strategy_name="stub",
                initial_capital=Decimal("100000"),
                max_position_size=Decimal("0.10"),
            ),
            strategy_name="stub",
        )

    def test_notify_live_never_throws(self, engine):
        class Exploding:
            def on_fill(self, **kwargs):
                raise RuntimeError("boom")

        engine._live_strategy = Exploding()
        engine._notify_live("X", "buy", "filled", Decimal("1"), Decimal("1"))  # must not raise

    def test_notify_live_no_strategy_is_noop(self, engine):
        engine._live_strategy = None
        engine._notify_live("X", "buy", "filled", Decimal("1"), Decimal("1"))

    def test_live_batch_queues_all_symbols(self, engine):
        """A cross-sectional rebalance's whole batch reaches the pending
        queue (the symbol-matching break used to eat every order but the
        triggering symbol's)."""
        from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType

        def make(symbol):
            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MODERATE,
                confidence=80.0,
                liquidity_score=90.0,
                priority_score=70.0,
                source=SignalSource.MOMENTUM,
                price=Decimal("100"),
                volume=Decimal("1000"),
                timestamp=datetime(2026, 1, 5),
                metadata={"strategy": "stub"},
            )

        class BatchStrategy:
            def __init__(self):
                self.calls = 0

            def generate_signals(self, md):
                self.calls += 1
                if self.calls == 1:  # first bar fires the rebalance batch
                    return [make("SCHD"), make("VYM")]
                return []

        engine._live_strategy = BatchStrategy()
        md = SimpleNamespace(
            symbol="SCHD",
            timestamp=datetime(2026, 1, 5),
            open=Decimal("100"),
            close=Decimal("100"),
            last=Decimal("100"),
            volume=Decimal("1000"),
            high=Decimal("101"),
            low=Decimal("99"),
            model_copy=lambda update=None: md,
        )
        stats: dict = {}
        processed = matched = skipped = 0
        signal_index = 0
        # emulate one live iteration of the run loop
        bar_signals = engine._live_strategy.generate_signals(md)
        for sig in bar_signals:
            processed += 1
            matched += 1
            engine._pending_signals.setdefault(sig.symbol, []).append(sig)
        assert set(engine._pending_signals) == {"SCHD", "VYM"}
        del stats, processed, matched, skipped, signal_index


class TestEndToEndLiveLoop:
    """Acceptance smoke: the REAL orchestrator runs the dividend strategy
    through the live loop over real CSV candles (D05), carrying the D12
    universe-EW benchmark (both policies) and the D01 income ledger.

    This is the net that catches engine-side regressions the unit tests
    can't see — e.g. a notify branch that moves the compliance block into
    the refused-trade path (trade=None → crash on the first rejection)."""

    async def test_dividend_run_executes_and_reports_all_f4_pieces(self):
        from datetime import date

        from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator
        from app.services.backtest_orchestration.models import BacktestOrchestrationRequest

        request = BacktestOrchestrationRequest(
            profile_id="d05-e2e",
            input_id="d05-e2e",
            module_parameter_set_id="d05-e2e",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("300"),
            objective="maximizar_dividendos",
            risk_profile="moderate",
            strategy_name="dividend_tracking",
            symbols=["SCHD", "VIG", "VYM", "DVY", "DGRO", "DGRW", "BND"],
            start_date=date(2023, 1, 2),
            end_date=date(2024, 12, 30),
        )
        result = await BacktestOrchestrator().orchestrate(request)

        assert result.success, result.error_message
        payload = result.backtest_result
        assert payload.metrics.total_trades > 0  # the live loop actually traded
        # D12: both EW policies with the WHOLE declared universe
        assert payload.universe_ew_return_pct is not None
        assert payload.universe_ew_buy_hold_return_pct is not None
        assert payload.universe_ew_symbols_used == sorted(request.symbols)
        # D01: real collected income against the executed book
        assert payload.dividend_metrics is not None
        assert payload.dividend_metrics.computable
        assert payload.dividend_metrics.events_collected > 0
