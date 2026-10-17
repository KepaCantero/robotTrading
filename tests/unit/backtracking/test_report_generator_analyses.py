"""Tests for the BacktestReportGenerator analysis sections.

Covers the analyses that replaced the former placeholder strings: they must
compute real statistics from BacktestResult trades, and the two that need
data the result does not carry must say so explicitly instead of faking.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.backtesting.models import BacktestConfig, BacktestResult, Trade
from app.backtesting.report_generator import BacktestReportGenerator


def _trade(
    trade_id: str,
    symbol: str,
    quantity: str,
    entry_price: str,
    pnl: str,
    reason: str,
    entry_day: int,
    exit_day: int,
) -> Trade:
    entry = datetime(2024, 1, entry_day, 15, 0)
    exit_ = datetime(2024, 1, exit_day, 15, 0)
    return Trade(
        trade_id=trade_id,
        symbol=symbol,
        side="buy",
        quantity=Decimal(quantity),
        entry_price=Decimal(entry_price),
        exit_price=Decimal(entry_price),
        entry_time=entry,
        exit_time=exit_,
        pnl=Decimal(pnl),
        pnl_percentage=None,
        reason=reason,
    )


def _result(trades: list[Trade]) -> BacktestResult:
    return BacktestResult(
        strategy_name="test",
        trades=trades,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 2, 1),
        final_capital=Decimal("110000"),
        total_return=Decimal("10"),
    )


def _generator(tmp_path: Path) -> BacktestReportGenerator:
    return BacktestReportGenerator(output_dir=tmp_path)


def test_trade_distribution_computes_real_statistics(tmp_path: Path) -> None:
    result = _result(
        [
            _trade("1", "AAPL", "10", "150", "200", "signal_exit", 1, 5),
            _trade("2", "GE", "100", "15", "100", "take_profit_hit", 2, 6),
            _trade("3", "F", "50", "12", "-150", "stop_loss_triggered", 3, 4),
        ]
    )

    analysis = _generator(tmp_path)._analyze_trade_distribution(result)

    assert "placeholder" not in analysis.lower()
    assert "3 (2 wins / 1 losses)" in analysis
    assert "66.7%" in analysis
    assert "**Profit Factor:** 2.00" in analysis
    assert "AAPL" in analysis and "F" in analysis
    assert "Avg Holding Period" in analysis


def test_trade_risks_reports_tail_streaks_and_costs(tmp_path: Path) -> None:
    result = _result(
        [
            _trade("1", "AAPL", "10", "150", "200", "signal_exit", 1, 5),
            _trade("2", "F", "50", "12", "-150", "stop_loss", 2, 3),
            _trade("3", "GE", "20", "15", "-50", "stop_loss", 4, 5),
        ]
    )

    analysis = _generator(tmp_path)._analyze_trade_risks(result)

    assert "placeholder" not in analysis.lower()
    assert "**Worst Trade:** $-150.00" in analysis
    assert "**Max Consecutive Losing Trades:** 2" in analysis
    assert "Cost Drag" in analysis


def test_stop_losses_buckets_exit_reasons(tmp_path: Path) -> None:
    config = BacktestConfig(stop_loss_percentage=Decimal("2"), take_profit_percentage=Decimal("5"))
    result = _result(
        [
            _trade("1", "AAPL", "10", "150", "200", "take_profit_hit", 1, 5),
            _trade("2", "F", "50", "12", "-150", "stop_loss_triggered", 2, 3),
            _trade("3", "GE", "20", "15", "40", "signal_exit", 4, 8),
        ]
    )

    analysis = _generator(tmp_path)._analyze_stop_losses(result, config)

    assert "placeholder" not in analysis.lower()
    assert "SL 2.0% / TP 5.0%" in analysis
    assert "**stop_loss:** 1 trades, avg P&L $-150.00" in analysis
    assert "**take_profit:** 1 trades, avg P&L $200.00" in analysis
    assert "**signal/other:** 1 trades, avg P&L $40.00" in analysis


def test_position_sizing_compares_exposure_to_limit(tmp_path: Path) -> None:
    config = BacktestConfig(initial_capital=Decimal("100000"), max_position_size=Decimal("0.1"))
    result = _result(
        [
            _trade("1", "AAPL", "100", "150", "200", "signal_exit", 1, 5),  # 15% exposure
            _trade("2", "GE", "100", "15", "100", "signal_exit", 2, 6),  # 1.5% exposure
        ]
    )

    analysis = _generator(tmp_path)._analyze_position_sizing(result, config)

    assert "placeholder" not in analysis.lower()
    assert "**Max Position Limit (config):** 10.0%" in analysis
    assert "max 15.0%" in analysis
    assert "**Trades Over Limit:** 1 of 2" in analysis


def test_unavailable_analyses_state_why_instead_of_faking(tmp_path: Path) -> None:
    result = _result([])

    market = _generator(tmp_path)._analyze_market_conditions(result)
    correlations = _generator(tmp_path)._analyze_correlations(result)

    assert "not available" in market
    assert "not available" in correlations
    assert "placeholder" not in (market + correlations).lower()
