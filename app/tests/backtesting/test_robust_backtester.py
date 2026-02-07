"""
Comprehensive tests for the Robust Backtesting Engine.

This test suite covers all functionality of the robust backtesting engine:
- Corporate actions handling
- Dividend reinvestment (DRIP)
- Survivorship bias correction
- Performance metrics calculation
- Checkpoint/resume functionality
- Memory-efficient chunking

Target: 60+ tests
"""

from __future__ import annotations

import pickle
from datetime import date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.backtesting.robust_engine import (
    CorporateActionHandler,
    CorporateActionType,
    DividendHandler,
    DripConfig,
    PerformanceMetrics,
    PerformanceTracker,
    RobustBacktestConfig,
    RobustBacktester,
    SurvivorshipAdjuster,
)
from app.backtesting.robust_engine.models import (
    BacktestCheckpoint,
    DelistedStock,
    DelistingReason,
    ProgressUpdate,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_config():
    """Create a sample backtest configuration."""
    return RobustBacktestConfig(
        initial_capital=Decimal("100000"),
        start_date=date(2020, 1, 1),
        end_date=date(2024, 12, 31),
        commission_per_trade=Decimal("1.0"),
        slippage_bps=Decimal("5"),
        enable_checkpointing=False,  # Disable for faster tests
        chunk_size_days=90,  # Smaller chunks for tests
    )


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    dates = pd.date_range(start="2020-01-01", end="2020-12-31", freq="D")

    np.random.seed(42)
    n = len(dates)

    data = pd.DataFrame(
        {
            "open": 100 + np.random.randn(n).cumsum() * 0.5,
            "high": 100 + np.random.randn(n).cumsum() * 0.5 + 1,
            "low": 100 + np.random.randn(n).cumsum() * 0.5 - 1,
            "close": 100 + np.random.randn(n).cumsum() * 0.5,
            "volume": np.random.randint(100000, 1000000, n),
        },
        index=dates,
    )

    # Ensure OHLC consistency
    data["high"] = data[["open", "close"]].max(axis=1) + 0.5
    data["low"] = data[["open", "close"]].min(axis=1) - 0.5

    return data


@pytest.fixture
def sample_signals():
    """Create sample trading signals."""
    signals = []

    class Signal:
        def __init__(self, symbol, signal_type, price, timestamp):
            self.symbol = symbol
            self.signal_type = signal_type
            self.price = price
            self.timestamp = timestamp

    # Generate some buy/sell signals
    for i, date in enumerate(pd.date_range("2020-01-01", "2020-12-31", freq="W")):
        if i % 2 == 0:
            signals.append(Signal("TEST", "buy", 100.0, date))
        else:
            signals.append(Signal("TEST", "sell", 100.0, date))

    return signals


@pytest.fixture
def corporate_action_handler():
    """Create a corporate action handler."""
    return CorporateActionHandler()


@pytest.fixture
def dividend_handler():
    """Create a dividend handler."""
    return DividendHandler(
        drip_config=DripConfig(
            enable_drip=True,
            reinvest_same_stock=True,
        )
    )


@pytest.fixture
def survivorship_adjuster():
    """Create a survivorship adjuster."""
    return SurvivorshipAdjuster()


@pytest.fixture
def performance_tracker():
    """Create a performance tracker."""
    return PerformanceTracker(
        initial_capital=Decimal("100000"),
        risk_free_rate=Decimal("0.02"),
    )


# ============================================================================
# CORPORATE ACTION HANDLER TESTS (15 tests)
# ============================================================================


class TestCorporateActionHandler:
    """Tests for CorporateActionHandler."""

    def test_add_stock_split(self, corporate_action_handler):
        """Test adding a stock split."""
        split = corporate_action_handler.add_split(
            symbol="AAPL",
            split_ratio=Decimal("4"),
            ex_date=date(2020, 8, 31),
        )

        assert split.symbol == "AAPL"
        assert split.split_ratio == Decimal("4")
        assert split.adjustment_factor == Decimal("0.25")
        assert split.action_type == CorporateActionType.STOCK_SPLIT

    def test_add_merger(self, corporate_action_handler):
        """Test adding a merger."""
        merger = corporate_action_handler.add_merger(
            target="TARGET",
            acquirer="ACQR",
            exchange_ratio=Decimal("1.5"),
            ex_date=date(2020, 6, 15),
            cash_consideration=Decimal("10.0"),
        )

        assert merger.target_symbol == "TARGET"
        assert merger.acquirer_symbol == "ACQR"
        assert merger.exchange_ratio == Decimal("1.5")
        assert merger.cash_consideration == Decimal("10.0")

    def test_add_spinoff(self, corporate_action_handler):
        """Test adding a spin-off."""
        spinoff = corporate_action_handler.add_spinoff(
            parent="PARENT",
            spinoff="SPIN",
            distribution_ratio=Decimal("0.1"),
            ex_date=date(2020, 3, 1),
        )

        assert spinoff.parent_symbol == "PARENT"
        assert spinoff.spinoff_symbol == "SPIN"
        assert spinoff.distribution_ratio == Decimal("0.1")

    def test_handle_split_adjustment(self, corporate_action_handler):
        """Test handling a stock split for a position."""
        adjustment = corporate_action_handler.handle_split(
            symbol="AAPL",
            split_ratio=Decimal("2"),
            ex_date=date(2020, 8, 31),
            shares=Decimal("100"),
            cost_basis=Decimal("15000"),
        )

        assert adjustment.new_quantity == Decimal("200")
        assert adjustment.new_cost_basis == Decimal("7500")
        assert adjustment.adjustment_type == "stock_split"

    def test_handle_merger_adjustment(self, corporate_action_handler):
        """Test handling a merger for a position."""
        adjustment = corporate_action_handler.handle_merger(
            target="TARGET",
            acquirer="ACQR",
            ratio=Decimal("0.5"),
            cash=Decimal("5.0"),
            target_shares=Decimal("100"),
            target_cost_basis=Decimal("10000"),
            acquirer_price=Decimal("50"),
        )

        assert adjustment.new_symbol == "ACQR"
        assert adjustment.new_quantity == Decimal("50")
        assert adjustment.cash_received == Decimal("500")

    def test_handle_spinoff_adjustment(self, corporate_action_handler):
        """Test handling a spin-off for a position."""
        parent_adj, spinoff_adj = corporate_action_handler.handle_spinoff(
            parent="PARENT",
            spinoff="SPIN",
            ratio=Decimal("0.1"),
            parent_shares=Decimal("100"),
            parent_cost_basis=Decimal("10000"),
            parent_price=Decimal("100"),
            spinoff_price=Decimal("10"),
        )

        assert parent_adj.new_symbol == "PARENT"
        assert spinoff_adj.new_symbol == "SPIN"
        assert spinoff_adj.new_quantity == Decimal("10")

    def test_adjust_history_for_splits_empty(self, corporate_action_handler, sample_market_data):
        """Test adjusting prices when no splits exist."""
        adjusted = corporate_action_handler.adjust_history_for_splits(sample_market_data)

        # Should return unchanged data
        pd.testing.assert_frame_equal(adjusted, sample_market_data)

    def test_adjust_history_for_splits_with_splits(self, corporate_action_handler):
        """Test adjusting prices for stock splits."""
        # Create simple price data
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        prices = pd.DataFrame(
            {"close": np.ones(len(dates)) * 100},
            index=dates,
        )

        # Add a split
        corporate_action_handler.add_split(
            symbol="TEST",
            split_ratio=Decimal("2"),
            ex_date=date(2020, 6, 1),
        )

        adjusted = corporate_action_handler.adjust_history_for_splits(prices)

        # Prices before split should be adjusted
        pre_split = adjusted[adjusted.index < pd.Timestamp("2020-06-01")]
        assert (pre_split["close"] == 50).all()  # Adjusted for 2:1 split

    def test_get_adjustment_factor_no_splits(self, corporate_action_handler):
        """Test getting adjustment factor when no splits."""
        factor = corporate_action_handler.get_adjustment_factor(
            symbol="AAPL",
            as_of_date=date(2020, 1, 1),
        )

        assert factor == Decimal("1")

    def test_get_adjustment_factor_with_splits(self, corporate_action_handler):
        """Test getting adjustment factor with splits."""
        corporate_action_handler.add_split(
            symbol="AAPL",
            split_ratio=Decimal("2"),
            ex_date=date(2020, 6, 1),
        )

        # Before split
        factor_before = corporate_action_handler.get_adjustment_factor(
            symbol="AAPL",
            as_of_date=date(2020, 1, 1),
        )
        assert factor_before == Decimal("0.5")

        # After split
        factor_after = corporate_action_handler.get_adjustment_factor(
            symbol="AAPL",
            as_of_date=date(2020, 7, 1),
        )
        assert factor_after == Decimal("1")

    def test_get_pending_actions_empty(self, corporate_action_handler):
        """Test getting pending actions when none exist."""
        pending = corporate_action_handler.get_pending_actions(
            symbol="AAPL",
            current_date=date(2020, 1, 1),
            lookahead_days=30,
        )

        assert pending == []

    def test_get_pending_actions_with_actions(self, corporate_action_handler):
        """Test getting pending actions."""
        corporate_action_handler.add_split(
            symbol="AAPL",
            split_ratio=Decimal("2"),
            ex_date=date(2020, 2, 1),
        )

        pending = corporate_action_handler.get_pending_actions(
            symbol="AAPL",
            current_date=date(2020, 1, 15),
            lookahead_days=30,
        )

        assert len(pending) == 1
        assert pending[0].symbol == "AAPL"

    def test_load_actions_from_csv_file_not_found(self, corporate_action_handler, tmp_path):
        """Test loading actions from non-existent file."""
        count = corporate_action_handler.load_actions_from_csv(str(tmp_path / "nonexistent.csv"))

        assert count == 0

    def test_load_actions_from_csv_valid(self, corporate_action_handler, tmp_path):
        """Test loading actions from valid CSV."""
        csv_file = tmp_path / "actions.csv"
        csv_file.write_text(
            "action_type,symbol,target,ratio,ex_date,declaration_date\n"
            "split,AAPL,,4.0,2020-08-31,2020-07-30\n"
            "merger,TARGET,ACQR,1.5,2020-06-15,2020-05-15\n"
        )

        count = corporate_action_handler.load_actions_from_csv(str(csv_file))

        assert count == 2


# ============================================================================
# DIVIDEND HANDLER TESTS (15 tests)
# ============================================================================


class TestDividendHandler:
    """Tests for DividendHandler."""

    def test_handle_dividend_no_reinvestment(self):
        """Test handling dividend without DRIP."""
        handler = DividendHandler(drip_config=DripConfig(enable_drip=False))

        action = handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        assert action.symbol == "AAPL"
        assert action.amount == Decimal("0.92")
        assert action.total_amount == Decimal("92")
        assert action.reinvested is False

    def test_handle_dividend_with_reinvestment(self, dividend_handler):
        """Test handling dividend with DRIP."""
        action = dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        assert action.reinvested is True
        assert action.reinvestment_price == Decimal("185")
        assert action.reinvestment_shares is not None
        assert action.reinvestment_shares > 0

    def test_reinvest_dividend_fractional_shares(self, dividend_handler):
        """Test dividend reinvestment with fractional shares."""
        result = dividend_handler.reinvest_dividend(
            symbol="AAPL",
            cash=Decimal("92"),
            price=Decimal("185"),
            ex_date=date(2024, 1, 1),
        )

        assert result["shares"] == Decimal("92") / Decimal("185")

    def test_reinvest_dividend_whole_shares(self):
        """Test dividend reinvestment with whole shares only."""
        handler = DividendHandler(
            drip_config=DripConfig(
                enable_drip=True,
                fractional_shares=False,
            )
        )

        result = handler.reinvest_dividend(
            symbol="AAPL",
            cash=Decimal("500"),
            price=Decimal("185"),
            ex_date=date(2024, 1, 1),
        )

        # Should be 2 shares (500 / 185 = 2.7, rounded down)
        assert result["shares"] == Decimal("2")

    def test_calculate_yield_on_cost(self, dividend_handler):
        """Test calculating yield on cost."""
        # Add some dividends
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("1.00"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("100"),
        )

        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("1.00"),
            ex_date=date(2024, 4, 1),
            shares=Decimal("100"),
            current_price=Decimal("100"),
        )

        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("1.00"),
            ex_date=date(2024, 7, 1),
            shares=Decimal("100"),
            current_price=Decimal("100"),
        )

        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("1.00"),
            ex_date=date(2024, 10, 1),
            shares=Decimal("100"),
            current_price=Decimal("100"),
        )

        yield_cost = dividend_handler.calculate_yield_on_cost(
            symbol="AAPL",
            original_cost=Decimal("10000"),
        )

        # $400 annually / $10000 cost = 4%
        assert yield_cost == Decimal("4.00")

    def test_calculate_current_yield(self, dividend_handler):
        """Test calculating current dividend yield."""
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        current_yield = dividend_handler.calculate_current_yield(
            symbol="AAPL",
            current_price=Decimal("185"),
        )

        # $0.92 * 4 / $185 = ~1.99%
        assert current_yield > Decimal("1.9")
        assert current_yield < Decimal("2.1")

    def test_get_total_dividends_received(self, dividend_handler):
        """Test getting total dividends received."""
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        dividend_handler.handle_dividend(
            symbol="MSFT",
            amount=Decimal("0.68"),
            ex_date=date(2024, 1, 15),
            shares=Decimal("50"),
            current_price=Decimal("400"),
        )

        total = dividend_handler.get_total_dividends_received()

        assert total == Decimal("92") + Decimal("34")  # 100*0.92 + 50*0.68

    def test_get_total_dividends_reinvested(self, dividend_handler):
        """Test getting total dividends reinvested."""
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        reinvested = dividend_handler.get_total_dividends_reinvested()

        assert reinvested == Decimal("92")  # 100 * 0.92

    def test_get_dividend_history_single_symbol(self, dividend_handler):
        """Test getting dividend history for a single symbol."""
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        dividend_handler.handle_dividend(
            symbol="MSFT",
            amount=Decimal("0.68"),
            ex_date=date(2024, 1, 15),
            shares=Decimal("50"),
            current_price=Decimal("400"),
        )

        aapl_history = dividend_handler.get_dividend_history(symbol="AAPL")

        assert len(aapl_history) == 1
        assert aapl_history[0].symbol == "AAPL"

    def test_get_dividend_history_all(self, dividend_handler):
        """Test getting all dividend history."""
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        dividend_handler.handle_dividend(
            symbol="MSFT",
            amount=Decimal("0.68"),
            ex_date=date(2024, 1, 15),
            shares=Decimal("50"),
            current_price=Decimal("400"),
        )

        all_history = dividend_handler.get_dividend_history()

        assert len(all_history) == 2

    def test_calculate_portfolio_dividend_yield(self, dividend_handler):
        """Test calculating portfolio dividend yield."""
        # Add dividends for two stocks
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        dividend_handler.handle_dividend(
            symbol="MSFT",
            amount=Decimal("0.68"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("50"),
            current_price=Decimal("400"),
        )

        portfolio_yield = dividend_handler.calculate_portfolio_dividend_yield(
            positions={"AAPL": Decimal("100"), "MSFT": Decimal("50")},
            prices={"AAPL": Decimal("185"), "MSFT": Decimal("400")},
        )

        # Weighted average of yields
        assert portfolio_yield > 0
        assert portfolio_yield < 5  # Should be reasonable

    def test_get_annual_dividend_income(self, dividend_handler):
        """Test getting annual dividend income."""
        # Add dividends across two years
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2023, 6, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.96"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        annual_income = dividend_handler.get_annual_dividend_income()

        assert 2023 in annual_income
        assert 2024 in annual_income

    def test_get_dividend_statistics(self, dividend_handler):
        """Test getting comprehensive dividend statistics."""
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        stats = dividend_handler.get_dividend_statistics()

        assert "total_dividends_received" in stats
        assert "dividend_count" in stats
        assert "drip_enabled" in stats
        assert stats["drip_enabled"] is True

    def test_reset(self, dividend_handler):
        """Test resetting the dividend handler."""
        dividend_handler.handle_dividend(
            symbol="AAPL",
            amount=Decimal("0.92"),
            ex_date=date(2024, 1, 1),
            shares=Decimal("100"),
            current_price=Decimal("185"),
        )

        dividend_handler.reset()

        assert dividend_handler.get_total_dividends_received() == Decimal("0")
        assert dividend_handler.get_dividend_history() == []


# ============================================================================
# SURVIVORSHIP ADJUSTER TESTS (10 tests)
# ============================================================================


class TestSurvivorshipAdjuster:
    """Tests for SurvivorshipAdjuster."""

    def test_add_delisted_stock(self, survivorship_adjuster):
        """Test adding a delisted stock."""
        stock = DelistedStock(
            symbol="BKSY",
            delisting_date=date(2020, 6, 1),
            reason=DelistingReason.BANKRUPTCY,
            last_price=Decimal("1.50"),
            recovery_rate=Decimal("0.10"),
        )

        survivorship_adjuster.add_delisted_stock(stock)

        assert "BKSY" in survivorship_adjuster._delisted_stocks

    def test_get_adjusted_universe_no_delisted(self, survivorship_adjuster):
        """Test getting adjusted universe with no delisted stocks."""
        universe = survivorship_adjuster.get_adjusted_universe(
            current_universe=["AAPL", "MSFT", "GOOGL"],
            as_of_date=date(2020, 1, 1),
        )

        assert set(universe) == {"AAPL", "MSFT", "GOOGL"}

    def test_get_adjusted_universe_with_delisted(self, survivorship_adjuster):
        """Test getting adjusted universe including delisted stocks."""
        # Add a delisted stock
        survivorship_adjuster.add_delisted_stock(
            DelistedStock(
                symbol="DELST",
                delisting_date=date(2020, 12, 31),
                reason=DelistingReason.BANKRUPTCY,
                last_price=Decimal("1.0"),
            )
        )

        universe = survivorship_adjuster.get_adjusted_universe(
            current_universe=["AAPL", "MSFT"],
            as_of_date=date(2020, 6, 1),
        )

        # Should include the delisted stock
        assert "AAPL" in universe
        assert "MSFT" in universe
        assert "DELST" in universe

    def test_calculate_survivorship_free_returns_empty_data(self, survivorship_adjuster):
        """Test calculating survivorship-free returns with empty data."""
        result = survivorship_adjuster.calculate_survivorship_free_returns(
            current_universe=["AAPL", "MSFT"],
            returns_data=pd.DataFrame(),
            backtest_start=date(2020, 1, 1),
            backtest_end=date(2020, 12, 31),
        )

        assert result.original_returns.empty
        assert result.adjusted_returns.empty

    def test_calculate_survivorship_free_returns_with_data(self, survivorship_adjuster):
        """Test calculating survivorship-free returns."""
        dates = pd.date_range("2020-01-01", "2020-12-31", freq="D")
        returns_data = pd.DataFrame(
            np.random.randn(len(dates)) * 0.01,
            index=dates,
            columns=["AAPL"],
        )

        result = survivorship_adjuster.calculate_survivorship_free_returns(
            current_universe=["AAPL"],
            returns_data=returns_data,
            backtest_start=date(2020, 1, 1),
            backtest_end=date(2020, 12, 31),
        )

        assert len(result.original_returns) > 0
        assert len(result.adjusted_returns) > 0
        assert result.bias_factor >= 1.0

    def test_create_point_in_time_universe(self, survivorship_adjuster):
        """Test creating point-in-time universe."""
        pit = survivorship_adjuster.create_point_in_time_universe(
            current_universe=["AAPL", "MSFT"],
            backtest_start=date(2020, 1, 1),
            backtest_end=date(2020, 12, 31),
            frequency="M",
        )

        # Should have 12 monthly dates
        assert len(pit) == 12

    def test_get_delisting_events(self, survivorship_adjuster):
        """Test getting delisting events."""
        survivorship_adjuster.add_delisted_stock(
            DelistedStock(
                symbol="DELST",
                delisting_date=date(2020, 6, 15),
                reason=DelistingReason.BANKRUPTCY,
                last_price=Decimal("1.0"),
            )
        )

        events = survivorship_adjuster.get_delisting_events(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )

        assert len(events) == 1
        assert events[0].symbol == "DELST"

    def test_get_delisting_events_by_reason(self, survivorship_adjuster):
        """Test getting delisting events filtered by reason."""
        survivorship_adjuster.add_delisted_stock(
            DelistedStock(
                symbol="DELST1",
                delisting_date=date(2020, 6, 15),
                reason=DelistingReason.BANKRUPTCY,
                last_price=Decimal("1.0"),
            )
        )

        survivorship_adjuster.add_delisted_stock(
            DelistedStock(
                symbol="DELST2",
                delisting_date=date(2020, 7, 15),
                reason=DelistingReason.ACQUISITION,
                last_price=Decimal("50.0"),
            )
        )

        bankruptcy_events = survivorship_adjuster.get_delisting_events(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            reason=DelistingReason.BANKRUPTCY,
        )

        assert len(bankruptcy_events) == 1
        assert bankruptcy_events[0].symbol == "DELST1"

    def test_calculate_universe_statistics(self, survivorship_adjuster):
        """Test calculating universe statistics."""
        stats = survivorship_adjuster.calculate_universe_statistics(
            current_universe=["AAPL", "MSFT", "GOOGL"],
            backtest_start=date(2000, 1, 1),
            backtest_end=date(2024, 12, 31),
        )

        assert "original_universe_size" in stats
        assert "current_universe_size" in stats
        assert "bias_factor" in stats
        assert stats["current_universe_size"] == 3

    def test_load_delisted_database_file_not_found(self, survivorship_adjuster, tmp_path):
        """Test loading from non-existent database."""
        count = survivorship_adjuster.load_delisted_database(filepath=tmp_path / "nonexistent.csv")

        assert count == 0


# ============================================================================
# PERFORMANCE TRACKER TESTS (10 tests)
# ============================================================================


class TestPerformanceTracker:
    """Tests for PerformanceTracker."""

    def test_update_equity_curve(self, performance_tracker):
        """Test updating equity curve."""
        performance_tracker.update(date(2024, 1, 1), Decimal("105000"))

        assert len(performance_tracker.equity_curve) == 1
        assert performance_tracker.equity_curve[0][1] == Decimal("105000")

    def test_update_with_trades(self, performance_tracker):
        """Test updating with trades."""
        performance_tracker.update(
            date(2024, 1, 1),
            Decimal("105000"),
            trades=[{"pnl": 500}, {"pnl": -200}],
        )

        assert performance_tracker._max_winning_streak == 1
        assert performance_tracker._max_losing_streak == 1

    def test_calculate_metrics_empty(self, performance_tracker):
        """Test calculating metrics with no data."""
        metrics = performance_tracker.calculate_metrics()

        assert isinstance(metrics, PerformanceMetrics)

    def test_calculate_metrics_with_data(self, performance_tracker):
        """Test calculating metrics with equity curve."""
        # Add some equity data
        for i in range(10):
            value = Decimal(str(100000 + i * 1000))
            performance_tracker.update(date(2024, 1, 1 + i), value)

        metrics = performance_tracker.calculate_metrics()

        assert metrics.total_return > 0
        assert metrics.volatility >= 0

    def test_calculate_max_drawdown(self, performance_tracker):
        """Test maximum drawdown calculation."""
        # Create drawdown scenario
        performance_tracker.update(date(2024, 1, 1), Decimal("110000"))  # Peak
        performance_tracker.update(date(2024, 1, 2), Decimal("100000"))  # Drawdown
        performance_tracker.update(date(2024, 1, 3), Decimal("105000"))  # Recovery

        metrics = performance_tracker.calculate_metrics()

        assert metrics.max_drawdown < 0
        assert metrics.max_drawdown >= -0.1  # ~9% drawdown

    def test_get_yearly_breakdown(self, performance_tracker):
        """Test getting yearly breakdown."""
        # Add data across two years
        for i in range(10):
            date_obj = date(2023, 1, 1 + i)
            value = Decimal(str(100000 + i * 1000))
            performance_tracker.update(date_obj, value)

        for i in range(10):
            date_obj = date(2024, 1, 1 + i)
            value = Decimal(str(110000 + i * 1000))
            performance_tracker.update(date_obj, value)

        yearly = performance_tracker.get_yearly_breakdown()

        assert len(yearly) == 2
        assert any(y.year == 2023 for y in yearly)
        assert any(y.year == 2024 for y in yearly)

    def test_get_rolling_metrics(self, performance_tracker):
        """Test getting rolling metrics."""
        # Add enough data for rolling calculations
        for i in range(300):
            date_obj = date(2024, 1, 1) + timedelta(days=i)
            value = Decimal(str(100000 + i * 100))
            performance_tracker.update(date_obj, value)

        rolling = performance_tracker.get_rolling_metrics()

        assert rolling.window_1y is not None

    def test_sharpe_ratio_calculation(self, performance_tracker):
        """Test Sharpe ratio calculation."""
        # Add volatile data
        np.random.seed(42)
        for i in range(50):
            date_obj = date(2024, 1, 1) + timedelta(days=i)
            change = Decimal(str(np.random.randn() * 1000))
            value = Decimal("100000") + change
            performance_tracker.update(date_obj, value)

        metrics = performance_tracker.calculate_metrics()

        # Sharpe should be calculated
        assert metrics.sharpe_ratio is not None

    def test_sortino_ratio_calculation(self, performance_tracker):
        """Test Sortino ratio calculation."""
        # Add data with downside volatility
        np.random.seed(42)
        for i in range(50):
            date_obj = date(2024, 1, 1) + timedelta(days=i)
            # Use random variation to ensure we have varied downside returns
            change = int((i % 3 - 1) * 2000 + np.random.randn() * 1000)
            value = Decimal(str(100000 + change))
            performance_tracker.update(date_obj, value)

        metrics = performance_tracker.calculate_metrics()

        assert metrics.sortino_ratio is not None

    def test_trade_statistics(self, performance_tracker):
        """Test trade statistics calculation."""
        # Add some equity data first so we have at least 2 points
        performance_tracker.update(date(2023, 12, 31), Decimal("100000"))

        # Add trades with equity update
        performance_tracker.update(
            date(2024, 1, 1),
            Decimal("105000"),
            trades=[{"pnl": 1000}, {"pnl": 2000}, {"pnl": -500}],
        )

        metrics = performance_tracker.calculate_metrics()

        assert metrics.total_trades == 3
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 1
        assert metrics.win_rate > 0


# ============================================================================
# ROBUST BACKTESTER TESTS (10 tests)
# ============================================================================


class TestRobustBacktester:
    """Tests for RobustBacktester."""

    def test_initialization(self, sample_config):
        """Test backtester initialization."""
        backtester = RobustBacktester(sample_config)

        assert backtester.config == sample_config
        assert backtester._capital == sample_config.initial_capital

    def test_config_validation_invalid_dates(self):
        """Test config validation with invalid dates."""
        with pytest.raises(ValueError):
            RobustBacktestConfig(
                initial_capital=Decimal("100000"),
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),  # End before start
            )

    def test_config_validation_invalid_capital(self):
        """Test config validation with invalid capital."""
        with pytest.raises(ValueError):
            RobustBacktestConfig(
                initial_capital=Decimal("-1000"),  # Negative
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )

    def test_reset_state(self, sample_config):
        """Test resetting backtester state."""
        backtester = RobustBacktester(sample_config)

        # Modify state
        backtester._capital = Decimal("50000")
        backtester._positions["AAPL"] = Decimal("100")

        # Reset
        backtester._reset_state()

        assert backtester._capital == sample_config.initial_capital
        assert backtester._positions == {}

    def test_split_data_into_chunks(self, sample_config, sample_market_data):
        """Test splitting data into chunks."""
        backtester = RobustBacktester(sample_config)
        chunks = backtester._split_data_into_chunks(sample_market_data)

        assert len(chunks) > 1  # Should be split into multiple chunks
        assert all(len(chunk) > 0 for chunk in chunks)

    def test_save_checkpoint(self, sample_config, tmp_path):
        """Test saving checkpoints."""
        sample_config.checkpoint_dir = tmp_path
        sample_config.enable_checkpointing = True  # Enable for this test
        backtester = RobustBacktester(sample_config)

        backtester._current_date = date(2024, 6, 1)
        backtester._capital = Decimal("105000")
        backtester._positions["AAPL"] = Decimal("100")

        backtester._save_checkpoint()

        # Check file exists
        checkpoint_files = list(tmp_path.glob("checkpoint_*.pkl"))
        assert len(checkpoint_files) == 1

    def test_load_checkpoint(self, sample_config, tmp_path):
        """Test loading checkpoints."""
        sample_config.checkpoint_dir = tmp_path
        sample_config.enable_checkpointing = True  # Enable for this test
        backtester = RobustBacktester(sample_config)

        # Save a checkpoint
        backtester._current_date = date(2024, 6, 1)
        backtester._capital = Decimal("105000")
        backtester._positions["AAPL"] = Decimal("100")
        backtester._save_checkpoint()

        # Create new backtester and load
        new_backtester = RobustBacktester(sample_config)
        loaded = new_backtester._load_latest_checkpoint()

        assert loaded is True
        assert new_backtester._current_date == date(2024, 6, 1)
        assert new_backtester._capital == Decimal("105000")

    def test_execute_buy(self, sample_config):
        """Test executing a buy order."""
        backtester = RobustBacktester(sample_config)

        backtester._execute_buy("AAPL", Decimal("150.0"), None)

        assert "AAPL" in backtester._positions
        assert backtester._positions["AAPL"] > 0
        assert backtester._capital < sample_config.initial_capital

    def test_execute_sell(self, sample_config):
        """Test executing a sell order."""
        backtester = RobustBacktester(sample_config)

        # First buy
        backtester._execute_buy("AAPL", Decimal("150.0"), None)
        initial_capital = backtester._capital
        initial_shares = backtester._positions["AAPL"]

        # Then sell
        backtester._execute_sell("AAPL", Decimal("155.0"), None)

        assert backtester._positions["AAPL"] < initial_shares
        assert backtester._capital > initial_capital

    def test_convert_to_dataframe(self, sample_config):
        """Test converting list data to DataFrame."""
        backtester = RobustBacktester(sample_config)

        # Create mock data objects
        class MockData:
            def __init__(self, timestamp, close):
                self.timestamp = timestamp
                self.close = close
                self.open = close
                self.high = close + 1
                self.low = close - 1
                self.volume = 1000000
                self.symbol = "TEST"

        data = [
            MockData(datetime(2024, 1, 1), 100.0),
            MockData(datetime(2024, 1, 2), 101.0),
        ]

        df = backtester._convert_to_dataframe(data)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "close" in df.columns


# ============================================================================
# BACKTEST CHECKPOINT TESTS (5 tests)
# ============================================================================


class TestBacktestCheckpoint:
    """Tests for BacktestCheckpoint."""

    def test_checkpoint_creation(self):
        """Test creating a checkpoint."""
        checkpoint = BacktestCheckpoint(
            current_date=date(2024, 6, 1),
            capital=Decimal("105000"),
            positions={"AAPL": Decimal("100")},
        )

        assert checkpoint.current_date == date(2024, 6, 1)
        assert checkpoint.capital == Decimal("105000")

    def test_checkpoint_to_dict(self):
        """Test converting checkpoint to dict."""
        checkpoint = BacktestCheckpoint(
            current_date=date(2024, 6, 1),
            capital=Decimal("105000"),
        )

        data = checkpoint.to_dict()

        assert "current_date" in data
        assert "capital" in data
        assert data["capital"] == 105000.0

    def test_checkpoint_from_dict(self):
        """Test creating checkpoint from dict."""
        data = {
            "checkpoint_id": "12345678-1234-5678-1234-567812345678",
            "timestamp": "2024-06-01T12:00:00",
            "current_date": "2024-06-01",
            "capital": 105000.0,
            "positions": {"AAPL": 100.0},
            "year": 1,
            "progress": 50.0,
            "metrics_snapshot": {},
        }

        checkpoint = BacktestCheckpoint.from_dict(data)

        assert checkpoint.current_date == date(2024, 6, 1)
        assert checkpoint.capital == Decimal("105000")

    def test_checkpoint_serialization_roundtrip(self, tmp_path):
        """Test checkpoint pickle serialization."""
        checkpoint = BacktestCheckpoint(
            current_date=date(2024, 6, 1),
            capital=Decimal("105000"),
            positions={"AAPL": Decimal("100")},
        )

        # Save and load
        filepath = tmp_path / "checkpoint.pkl"
        with open(filepath, "wb") as f:
            pickle.dump(checkpoint.to_dict(), f)

        with open(filepath, "rb") as f:
            data = pickle.load(f)

        loaded = BacktestCheckpoint.from_dict(data)

        assert loaded.current_date == checkpoint.current_date
        assert loaded.capital == checkpoint.capital

    def test_checkpoint_with_complex_positions(self):
        """Test checkpoint with complex position data."""
        positions = {
            "AAPL": Decimal("100"),
            "MSFT": Decimal("50"),
            "GOOGL": Decimal("25"),
        }

        checkpoint = BacktestCheckpoint(
            current_date=date(2024, 6, 1),
            capital=Decimal("100000"),
            positions=positions,
        )

        data = checkpoint.to_dict()
        loaded = BacktestCheckpoint.from_dict(data)

        assert loaded.positions == positions


# ============================================================================
# PROGRESS UPDATE TESTS (5 tests)
# ============================================================================


class TestProgressUpdate:
    """Tests for ProgressUpdate."""

    def test_progress_update_creation(self):
        """Test creating a progress update."""
        update = ProgressUpdate(
            current_year=5,
            total_years=25,
            current_date=date(2024, 6, 1),
            capital=Decimal("110000"),
        )

        assert update.current_year == 5
        assert update.total_years == 25

    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        update = ProgressUpdate(
            current_year=5,
            total_years=25,
            total_days=252 * 25,
            current_date=date(2024, 6, 1),
        )

        progress = update.progress_percentage()

        assert 0 <= progress <= 100

    def test_progress_update_to_dict(self):
        """Test converting progress update to dict."""
        update = ProgressUpdate(
            current_year=5,
            total_years=25,
            capital=Decimal("110000"),
            return_pct=Decimal("10.5"),
        )

        data = update.to_dict()

        assert "current_year" in data
        assert "progress_percentage" in data
        assert "return_pct" in data

    def test_progress_update_with_messages(self):
        """Test progress update with informational messages."""
        update = ProgressUpdate(
            current_year=5,
            total_years=25,
            messages=["Processing year 5", "Loading data"],
        )

        data = update.to_dict()

        assert "messages" in data
        assert len(data["messages"]) == 2

    def test_progress_update_estimated_time(self):
        """Test progress update with estimated time remaining."""
        update = ProgressUpdate(
            current_year=10,
            total_years=25,
            estimated_time_remaining=3600.0,  # 1 hour
        )

        assert update.estimated_time_remaining == 3600.0
