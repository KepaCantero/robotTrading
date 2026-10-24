"""Fase 2 risk-gates semantics (plan de producción paper, hallazgos A06/A07/A08/A18).

Acceptance straight from docs/audits/2026-10-24/auditoria_general_A01-A24.md:

- A07: +600 profit never trips the daily-loss breaker; the limit is measured
  against the session base (start-of-day capital), not current equity; ONE
  implementation of the limit.
- A08: with the breaker active, verified reduce-only closes pass; position
  increases and short flips are rejected; pending sells reduce reducible
  quantity.
- A18: non-finite, zero or negative quantity/price never cross the gates.
- A06: reserved (in-flight) orders consume buying power, symbol exposure and
  leverage headroom; releasing a reservation restores capacity.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.live_trading.broker_connector import BrokerAccount, BrokerType, OrderSide
from app.services.live_trading.risk_gates import RiskGates


class FakeRiskBroker:
    """Minimal async broker double with configurable account and positions."""

    def __init__(
        self,
        equity: Decimal = Decimal("10000"),
        positions: dict[str, SimpleNamespace] | None = None,
    ):
        self.equity = equity
        self.positions = positions or {}

    async def get_account_info(self):
        return BrokerAccount(
            account_id="fake",
            broker_type=BrokerType.PAPER,
            cash_available=self.equity,
            portfolio_value=self.equity,
            buying_power=self.equity,
            equity=self.equity,
            connected=True,
        )

    async def get_positions(self):
        return self.positions

    async def place_order(self, **kwargs):  # pragma: no cover - not used here
        raise AssertionError("risk tests never send orders")


def position(quantity: Decimal, market_value: Decimal) -> SimpleNamespace:
    return SimpleNamespace(quantity=quantity, market_value=market_value)


@pytest.fixture
def gates():
    """RiskGates on a clean 10k account, generous defaults for focused tests."""
    g = RiskGates(broker=FakeRiskBroker())
    g.set_start_of_day_capital(Decimal("10000"))
    return g


class TestDailyLossSessionSemantics:
    """A07: max(0, -pnl) over the session base — gains never trip the breaker."""

    @pytest.mark.asyncio
    async def test_profitable_session_never_trips(self, gates):
        gates.update_daily_pnl(Decimal("600"))  # +6% session on 10k base
        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("1"), Decimal("100"))
        assert result.passed, result.violations

    @pytest.mark.asyncio
    async def test_loss_measured_against_session_base_not_current_equity(self, gates):
        # Base 10k, -600 loss = 6% of the session base. Equity has since
        # grown to 20k: the old implementation (abs(pnl)/current_equity = 3%)
        # let it pass — the session base must govern.
        gates.broker.equity = Decimal("20000")
        gates.update_daily_pnl(Decimal("-600"))
        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("1"), Decimal("100"))
        assert not result.passed
        assert any("Daily loss" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_equal_loss_trips_at_limit(self, gates):
        gates.update_daily_pnl(Decimal("-600"))  # exactly 6% > 5% limit
        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("1"), Decimal("100"))
        assert not result.passed


class TestBreakerReduceOnly:
    """A08: breaker blocks risk increases, allows verified reduce-only closes."""

    @pytest.fixture
    def halted_gates(self):
        g = RiskGates(
            broker=FakeRiskBroker(positions={"AAPL": position(Decimal("10"), Decimal("1000"))})
        )
        g.set_start_of_day_capital(Decimal("10000"))
        g.halt_trading()
        return g

    @pytest.mark.asyncio
    async def test_reduce_only_close_passes(self, halted_gates):
        result = await halted_gates.validate_order(
            "AAPL", OrderSide.SELL, Decimal("5"), Decimal("100")
        )
        assert result.passed, result.violations
        assert any("reduce-only" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_position_increase_rejected(self, halted_gates):
        result = await halted_gates.validate_order(
            "AAPL", OrderSide.BUY, Decimal("1"), Decimal("100")
        )
        assert not result.passed
        assert any("circuit breaker" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_short_flip_rejected(self, halted_gates):
        # Held 10, selling 12 would open a short: rejected under the breaker.
        result = await halted_gates.validate_order(
            "AAPL", OrderSide.SELL, Decimal("12"), Decimal("100")
        )
        assert not result.passed

    @pytest.mark.asyncio
    async def test_pending_sells_reduce_reducible_quantity(self, halted_gates):
        halted_gates.reserve("AAPL", OrderSide.SELL, Decimal("6"), Decimal("100"))
        # 5 > 10 held - 6 pending sells = 4 reducible -> rejected
        over = await halted_gates.validate_order(
            "AAPL", OrderSide.SELL, Decimal("5"), Decimal("100")
        )
        assert not over.passed
        # exactly 4 passes
        exact = await halted_gates.validate_order(
            "AAPL", OrderSide.SELL, Decimal("4"), Decimal("100")
        )
        assert exact.passed, exact.violations


class TestNumericValidation:
    """A18: finite, positive quantity and price — always."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "quantity,price",
        [
            (Decimal("-10"), Decimal("100")),
            (Decimal("0"), Decimal("100")),
            (Decimal(10), Decimal("-5")),
            (Decimal(10), Decimal("0")),
            (Decimal("NaN"), Decimal("100")),
            (Decimal("Infinity"), Decimal("100")),
            (Decimal(10), Decimal("NaN")),
            (Decimal(10), Decimal("Infinity")),
        ],
    )
    async def test_invalid_numbers_rejected(self, gates, quantity, price):
        result = await gates.validate_order("AAPL", OrderSide.BUY, quantity, price)
        assert not result.passed
        assert result.risk_level.value == "critical"


class TestReservations:
    """A06: in-flight orders reserve risk capacity until terminal state."""

    @pytest.mark.asyncio
    async def test_reserved_buys_consume_buying_power(self, gates):
        # 10k buying power; a reserved 6k buy leaves 4k — a second 6k buy fails.
        gates.reserve("MSFT", OrderSide.BUY, Decimal("60"), Decimal("100"))
        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("60"), Decimal("100"))
        assert not result.passed
        assert any("pending buys" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_release_restores_capacity(self, gates):
        reservation_id = gates.reserve("MSFT", OrderSide.BUY, Decimal("60"), Decimal("100"))
        gates.release(reservation_id)
        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("60"), Decimal("100"))
        assert result.passed, result.violations

    @pytest.mark.asyncio
    async def test_projected_symbol_exposure_counts_reservations(self, gates):
        gates.set_max_position_size(Decimal("10000"))
        gates.broker.positions = {"AAPL": position(Decimal("10"), Decimal("6000"))}
        gates.reserve("AAPL", OrderSide.BUY, Decimal("30"), Decimal("100"))  # +3k pending
        # 6k held + 3k reserved + 2k new = 11k > 10k cap
        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("20"), Decimal("100"))
        assert not result.passed
        assert any("Projected AAPL exposure" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_projected_leverage_counts_reservations(self, gates):
        # equity 10k, holdings 10k; a reserved 8k buy plus a 3k buy projects
        # (10k + 8k + 3k)/10k = 2.1x > 2x limit.
        gates.reserve("MSFT", OrderSide.BUY, Decimal("80"), Decimal("100"))
        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("30"), Decimal("100"))
        assert not result.passed
        assert any("Projected leverage" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_sells_do_not_consume_buying_power(self, gates):
        gates.reserve("MSFT", OrderSide.SELL, Decimal("60"), Decimal("100"))
        result = await gates.validate_order("AAPL", OrderSide.BUY, Decimal("90"), Decimal("100"))
        assert result.passed, result.violations
