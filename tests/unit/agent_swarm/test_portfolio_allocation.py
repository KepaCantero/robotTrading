"""La allocation de T7.1 sale de los trades REALES del backtest.

La fantasía anterior: pesos por "características de módulo" inventadas →
tres módulos al 33% y un Sharpe de 92 que nadie calculó. Ahora: exposición
media ponderada por tiempo (notional × días mantenido) y los estadísticos
realizados del run.
"""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.services.agent_swarm.portfolio_allocation import allocation_from_backtest


def _trade(symbol, qty, price, entry, exit_, **extra):
    return {
        "symbol": symbol,
        "quantity": str(qty),
        "entry_price": str(price),
        "entry_time": entry,
        "exit_time": exit_,
        **extra,
    }


class TestAllocationFromBacktest:
    def test_weights_are_time_weighted_exposure(self):
        trades = [
            # AAA: 100€ × 100 días = 10_000 exposure-days
            _trade("AAA", 10, "10", "2024-01-01", "2024-04-10"),
            # BBB: 100€ × 300 días = 30_000 exposure-days → 75%
            _trade("BBB", 100, "1", "2024-01-01", "2024-10-27"),
        ]
        alloc = allocation_from_backtest("p", D("1000"), trades, D("7.5"), D("1.1"), D("-0.15"))
        by_symbol = {a.module_name: a for a in alloc.allocations}
        assert float(by_symbol["BBB"].weight_pct) == pytest.approx(75.0)
        assert float(by_symbol["AAA"].weight_pct) == pytest.approx(25.0)
        assert float(by_symbol["BBB"].capital_allocation_eur) == pytest.approx(750.0)

    def test_realized_stats_pass_through(self):
        trades = [_trade("AAA", 1, "1", "2024-01-01", "2024-02-01")]
        alloc = allocation_from_backtest("p", D("1000"), trades, D("7.5"), D("1.1"), D("-0.15"))
        assert alloc.allocation_method == "backtest_positions"
        assert alloc.expected_portfolio_return_pct == D("7.5")
        assert alloc.expected_portfolio_sharpe == D("1.1")
        assert alloc.expected_portfolio_drawdown_pct == D("-0.15")

    def test_same_symbol_trades_aggregate(self):
        trades = [
            _trade("AAA", 1, "1", "2024-01-01", "2024-02-01"),  # 31
            _trade("AAA", 1, "1", "2024-03-01", "2024-04-01"),  # 31
            _trade("BBB", 1, "1", "2024-01-01", "2024-02-01"),  # 31
        ]
        alloc = allocation_from_backtest("p", D("300"), trades, D("5"), D("0.5"), D("-0.1"))
        by_symbol = {a.module_name: a for a in alloc.allocations}
        assert float(by_symbol["AAA"].weight_pct) == pytest.approx(66.67, abs=0.02)
        assert float(by_symbol["BBB"].weight_pct) == pytest.approx(33.33, abs=0.02)

    def test_diversification_one_for_concentrated(self):
        trades = [_trade("AAA", 1, "1", "2024-01-01", "2024-02-01")]
        alloc = allocation_from_backtest("p", D("100"), trades, D("5"), D("0.5"), D("-0.1"))
        assert alloc.diversification_ratio == D("1.00")

    def test_no_exposure_raises(self):
        with pytest.raises(ValueError):
            allocation_from_backtest("p", D("100"), [], D("5"), D("0.5"), D("-0.1"))
        with pytest.raises(ValueError):
            allocation_from_backtest(
                "p",
                D("100"),
                [_trade("AAA", 0, "0", "2024-01-01", "2024-02-01")],
                D("5"),
                D("0.5"),
                D("-0.1"),
            )
