"""
Tests for ProfitAndLossCalculator service.

Tests P&L calculation, commission calculations, and edge cases.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.backtesting.models import BacktestConfig, Trade, TradeStatus
from app.backtesting.services.pnl_calculator import ProfitAndLossCalculator


class TestProfitAndLossCalculator:
    """Test suite for ProfitAndLossCalculator service."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
        )

    @pytest.fixture
    def pnl_calculator(self, config):
        """Create P&L calculator instance."""
        return ProfitAndLossCalculator(config)

    @pytest.fixture
    def sample_buy_trade(self, default_symbol):
        """Create sample buy trade."""
        return Trade(
            trade_id="trade_1",
            symbol=default_symbol,
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("150"),
            entry_time=datetime(2024, 1, 1, 10, 0),
            status=TradeStatus.OPEN,
            commission=Decimal("1.0"),
        )

    @pytest.fixture
    def sample_buy_trades(self, default_symbol):
        """Create multiple sample buy trades."""
        return [
            Trade(
                trade_id=f"trade_{i}",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1, 10, 0),
                status=TradeStatus.OPEN,
                commission=Decimal("1.0"),
            )
            for i in range(3)
        ]

    def test_initialization(self, config):
        """Test calculator initialization."""
        calculator = ProfitAndLossCalculator(config)
        assert calculator.config == config

    def test_calculate_sell_pnl_with_buy_trades(self, pnl_calculator, sample_buy_trades):
        """Test P&L calculation with existing buy trades."""
        result = pnl_calculator.calculate_sell_pnl(
            trades=sample_buy_trades,
            symbol="AAPL",
            sell_quantity=Decimal("100"),
            execution_price=Decimal("160"),
            commission=Decimal("1.0"),
        )

        # Average buy price = 150
        # Total cost = 150 * 100 + 1 = 15001
        # Proceeds = 160 * 100 - 1 = 15999
        # P&L = 15999 - 15001 = 998
        assert result["pnl"] == Decimal("998")
        assert result["avg_buy_price"] == Decimal("150")
        assert result["pnl_percentage"] == Decimal("998") / Decimal("15000") * 100
        assert len(result["buy_trades"]) == 3
        assert result["entry_time"] is not None

    def test_calculate_sell_pnl_no_buy_trades(self, pnl_calculator, default_symbol):
        """Test P&L calculation with no buy trades."""
        result = pnl_calculator.calculate_sell_pnl(
            trades=[],
            symbol=default_symbol,
            sell_quantity=Decimal("100"),
            execution_price=Decimal("160"),
            commission=Decimal("1.0"),
        )

        # Should return 0 P&L when no buy trades
        assert result["pnl"] == Decimal("0")
        assert result["avg_buy_price"] == Decimal("160")  # Execution price as fallback
        assert result["pnl_percentage"] == Decimal("0")
        assert len(result["buy_trades"]) == 0
        assert result["entry_time"] is None

    def test_calculate_sell_pnl_loss(self, pnl_calculator, sample_buy_trades, default_symbol):
        """Test P&L calculation for losing trade."""
        result = pnl_calculator.calculate_sell_pnl(
            trades=sample_buy_trades,
            symbol=default_symbol,
            sell_quantity=Decimal("100"),
            execution_price=Decimal("140"),
            commission=Decimal("1.0"),
        )

        # Avg buy = 150, sell at 140 = loss
        assert result["pnl"] < 0
        assert result["avg_buy_price"] == Decimal("150")
        assert result["pnl_percentage"] < 0

    def test_calculate_sell_pnl_different_quantities(
        self, pnl_calculator, sample_buy_trades, default_symbol
    ):
        """Test P&L calculation with different buy quantities."""
        # Create trades with different quantities
        trades = [
            Trade(
                trade_id="trade_1",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("50"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
            ),
            Trade(
                trade_id="trade_2",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("150"),
                entry_price=Decimal("160"),
                entry_time=datetime(2024, 1, 2),
                status=TradeStatus.OPEN,
            ),
        ]

        result = pnl_calculator.calculate_sell_pnl(
            trades=trades,
            symbol=default_symbol,
            sell_quantity=Decimal("100"),
            execution_price=Decimal("165"),
            commission=Decimal("1.0"),
        )

        # Weighted average = (50*150 + 150*160) / 200 = 157.5
        expected_avg = (Decimal("50") * Decimal("150") + Decimal("150") * Decimal("160")) / Decimal(
            "200"
        )
        assert result["avg_buy_price"] == expected_avg

    def test_calculate_close_position_pnl_with_trades(self, pnl_calculator, sample_buy_trades):
        """Test close position P&L calculation."""
        result = pnl_calculator.calculate_close_position_pnl(
            symbol="AAPL",
            quantity=Decimal("100"),
            exit_price=Decimal("160"),
            trades=sample_buy_trades,
        )

        assert result["pnl"] > 0  # Profit
        assert result["avg_entry_price"] == Decimal("150")
        assert result["entry_time"] is not None
        assert result["total_commission"] > 0

    def test_calculate_close_position_pnl_no_trades(self, pnl_calculator, default_symbol):
        """Test close position P&L with no trades."""
        result = pnl_calculator.calculate_close_position_pnl(
            symbol=default_symbol,
            quantity=Decimal("100"),
            exit_price=Decimal("160"),
            trades=[],
        )

        assert result["pnl"] == Decimal("0")
        assert result["pnl_percentage"] == Decimal("0")
        assert result["avg_entry_price"] == Decimal("160")
        assert result["total_commission"] == Decimal("0")
        assert result["entry_time"] is None

    def test_calculate_close_position_pnl_loss(
        self, pnl_calculator, sample_buy_trades, default_symbol
    ):
        """Test close position P&L for losing trade."""
        result = pnl_calculator.calculate_close_position_pnl(
            symbol=default_symbol,
            quantity=Decimal("100"),
            exit_price=Decimal("140"),
            trades=sample_buy_trades,
        )

        assert result["pnl"] < 0
        assert result["pnl_percentage"] < 0

    def test_calculate_average_entry_price(self, pnl_calculator, sample_buy_trades, default_symbol):
        """Test average entry price calculation."""
        avg_price = pnl_calculator.calculate_average_entry_price(sample_buy_trades, default_symbol)

        assert avg_price == Decimal("150")

    def test_calculate_average_entry_price_no_trades(self, pnl_calculator, default_symbol):
        """Test average entry price with no trades."""
        avg_price = pnl_calculator.calculate_average_entry_price([], default_symbol)

        assert avg_price is None

    def test_calculate_average_entry_price_different_symbols(self, pnl_calculator, default_symbol):
        """Test average entry price filters by symbol."""
        trades = [
            Trade(
                trade_id="trade_1",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
            ),
            Trade(
                trade_id="trade_2",
                symbol="MSFT",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("300"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
            ),
        ]

        avg_price = pnl_calculator.calculate_average_entry_price(trades, default_symbol)

        assert avg_price == Decimal("150")

    def test_calculate_average_entry_price_ignores_closed_trades(
        self, pnl_calculator, default_symbol
    ):
        """Test average entry price ignores closed trades."""
        trades = [
            Trade(
                trade_id="trade_1",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
            ),
            Trade(
                trade_id="trade_2",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("200"),
                exit_price=Decimal("210"),  # Required for CLOSED
                entry_time=datetime(2024, 1, 2),
                exit_time=datetime(2024, 1, 3),
                status=TradeStatus.CLOSED,  # Should be ignored
            ),
        ]

        avg_price = pnl_calculator.calculate_average_entry_price(trades, default_symbol)

        # Should only consider open trades
        assert avg_price == Decimal("150")

    def test_calculate_round_trip_commission(
        self, pnl_calculator, sample_buy_trades, default_symbol
    ):
        """Test round trip commission calculation."""
        commission = pnl_calculator.calculate_round_trip_commission(
            sample_buy_trades, default_symbol
        )

        # 3 trades with $1 commission each
        assert commission == Decimal("3")

    def test_calculate_round_trip_commission_no_commission(self, pnl_calculator, default_symbol):
        """Test round trip commission with no commission."""
        trades = [
            Trade(
                trade_id="trade_1",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
                commission=Decimal("0"),  # No commission
            )
        ]

        commission = pnl_calculator.calculate_round_trip_commission(trades, default_symbol)

        assert commission == Decimal("0")

    def test_calculate_round_trip_commission_filters_by_symbol(
        self, pnl_calculator, default_symbol
    ):
        """Test round trip commission filters by symbol."""
        trades = [
            Trade(
                trade_id="trade_1",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
                commission=Decimal("1.0"),
            ),
            Trade(
                trade_id="trade_2",
                symbol="MSFT",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("300"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
                commission=Decimal("2.0"),
            ),
        ]

        commission = pnl_calculator.calculate_round_trip_commission(trades, default_symbol)

        # Should only include default_symbol commission
        assert commission == Decimal("1")

    def test_calculate_commission_ratio(self, pnl_calculator, sample_buy_trades, default_symbol):
        """Test commission ratio calculation."""
        position_value = Decimal("15000")  # 100 shares at $150

        ratio = pnl_calculator.calculate_commission_ratio(
            position_value, sample_buy_trades, default_symbol
        )

        # $3 commission on $15000 = 0.0002
        assert ratio == Decimal("3") / Decimal("15000")

    def test_calculate_commission_ratio_zero_position(
        self, pnl_calculator, sample_buy_trades, default_symbol
    ):
        """Test commission ratio with zero position value."""
        ratio = pnl_calculator.calculate_commission_ratio(
            Decimal("0"), sample_buy_trades, default_symbol
        )

        assert ratio == Decimal("0")

    def test_calculate_commission_ratio_no_trades(self, pnl_calculator, default_symbol):
        """Test commission ratio with no trades."""
        ratio = pnl_calculator.calculate_commission_ratio(Decimal("15000"), [], default_symbol)

        assert ratio == Decimal("0")

    def test_percentage_based_commission_detection(self, config, pnl_calculator, default_symbol):
        """Test detection of percentage-based commission."""
        # Create a trade with high commission (percentage-based)
        trades = [
            Trade(
                trade_id="trade_1",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
                commission=Decimal("75"),  # 0.5% of $15000
            )
        ]

        result = pnl_calculator.calculate_close_position_pnl(
            symbol=default_symbol,
            quantity=Decimal("100"),
            exit_price=Decimal("160"),
            trades=trades,
        )

        # Should detect percentage-based commission
        assert result["total_commission"] > Decimal("75")

    def test_edge_case_zero_quantity(self, pnl_calculator, sample_buy_trades, default_symbol):
        """Test P&L calculation with zero quantity."""
        result = pnl_calculator.calculate_sell_pnl(
            trades=sample_buy_trades,
            symbol=default_symbol,
            sell_quantity=Decimal("0"),
            execution_price=Decimal("160"),
            commission=Decimal("1.0"),
        )

        # P&L should be negative (just commission)
        assert result["pnl"] <= 0

    def test_edge_case_empty_trades_list(self, pnl_calculator, default_symbol):
        """Test with empty trades list."""
        result = pnl_calculator.calculate_sell_pnl(
            trades=[],
            symbol=default_symbol,
            sell_quantity=Decimal("100"),
            execution_price=Decimal("160"),
            commission=Decimal("1.0"),
        )

        assert result["pnl"] == Decimal("0")
        assert result["avg_buy_price"] == Decimal("160")

    def test_edge_case_zero_commission(self, config, default_symbol):
        """Test with zero commission."""
        config.commission_per_trade = Decimal("0")
        calculator = ProfitAndLossCalculator(config)

        trades = [
            Trade(
                trade_id="trade_1",
                symbol=default_symbol,
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
                commission=Decimal("0"),
            )
        ]

        result = calculator.calculate_sell_pnl(
            trades=trades,
            symbol=default_symbol,
            sell_quantity=Decimal("100"),
            execution_price=Decimal("160"),
            commission=Decimal("0"),
        )

        # P&L = (160 - 150) * 100 = 1000 (no commission)
        assert result["pnl"] == Decimal("1000")
