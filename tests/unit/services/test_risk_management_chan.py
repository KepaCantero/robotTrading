"""
Unit tests for Risk Management - Ernest Chan methodologies
"""

import numpy as np
import pytest

from app.services.risk_management_chan import (
    ChanDrawdownController,
    ChanPositionSizer,
    ChanRiskMetrics,
    ChanStopLossCalculator,
    PositionSizeResult,
    RiskMetrics,
    StopLossResult,
    calculate_optimal_position_size,
    calculate_optimal_stop_loss,
)


class TestChanStopLossCalculator:
    """Tests for ChanStopLossCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create a ChanStopLossCalculator instance."""
        return ChanStopLossCalculator(
            atr_multiplier=2.0,
            fixed_stop_pct=0.05,
        )

    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.atr_multiplier == 2.0
        assert calculator.fixed_stop_pct == 0.05

    def test_atr_stop_loss_long(self, calculator):
        """Test ATR-based stop loss for long position."""
        result = calculator.calculate_atr_stop_loss(
            entry_price=100.0,
            atr=2.5,
            direction="long",
        )

        assert isinstance(result, StopLossResult)
        assert result.stop_loss_price == 95.0  # 100 - (2.5 * 2)
        assert result.stop_loss_distance == 5.0
        assert result.method_used == "ATR-based"

    def test_atr_stop_loss_short(self, calculator):
        """Test ATR-based stop loss for short position."""
        result = calculator.calculate_atr_stop_loss(
            entry_price=100.0,
            atr=2.5,
            direction="short",
        )

        assert isinstance(result, StopLossResult)
        assert result.stop_loss_price == 105.0  # 100 + (2.5 * 2)
        assert result.stop_loss_distance == 5.0

    def test_atr_stop_loss_custom_multiplier(self, calculator):
        """Test ATR stop loss with custom multiplier."""
        result = calculator.calculate_atr_stop_loss(
            entry_price=100.0,
            atr=3.0,
            direction="long",
            multiplier=3.0,
        )

        assert result.stop_loss_price == 91.0  # 100 - (3.0 * 3)
        assert result.stop_loss_distance == 9.0

    def test_fixed_percentage_stop(self, calculator):
        """Test fixed percentage stop loss."""
        result = calculator.calculate_fixed_percentage_stop(
            entry_price=100.0,
            direction="long",
            stop_pct=0.10,
        )

        assert isinstance(result, StopLossResult)
        assert result.stop_loss_price == 90.0  # 100 * (1 - 0.10)
        assert result.stop_loss_percentage == 0.10
        assert result.method_used == "Fixed percentage"

    def test_fixed_stop_short(self, calculator):
        """Test fixed percentage stop for short position."""
        result = calculator.calculate_fixed_percentage_stop(
            entry_price=100.0,
            direction="short",
            stop_pct=0.08,
        )

        assert result.stop_loss_price == 108.0  # 100 * (1 + 0.08)

    def test_trailing_stop_long(self, calculator):
        """Test trailing stop loss for long position."""
        result = calculator.calculate_trailing_stop(
            current_price=110.0,
            highest_price_since_entry=105.0,
            atr=2.0,
            direction="long",
        )

        assert isinstance(result, StopLossResult)
        # Stop should be below the highest price
        assert result.stop_loss_price < 105.0
        assert result.method_used == "Trailing ATR"

    def test_trailing_stop_short(self, calculator):
        """Test trailing stop for short position."""
        result = calculator.calculate_trailing_stop(
            current_price=90.0,
            highest_price_since_entry=95.0,  # For shorts, this is the lowest
            atr=2.0,
            direction="short",
        )

        assert isinstance(result, StopLossResult)
        # Stop should be above the lowest price
        assert result.stop_loss_price > 95.0

    def test_invalid_direction(self, calculator):
        """Test handling of invalid direction."""
        result = calculator.calculate_atr_stop_loss(
            entry_price=100.0,
            atr=2.5,
            direction="invalid",
        )

        # Should return fallback result
        assert isinstance(result, StopLossResult)


class TestChanPositionSizer:
    """Tests for ChanPositionSizer class."""

    @pytest.fixture
    def sizer(self):
        """Create a ChanPositionSizer instance."""
        return ChanPositionSizer(
            risk_per_trade=0.02,
            max_position_pct=0.25,
        )

    def test_initialization(self, sizer):
        """Test sizer initialization."""
        assert sizer.risk_per_trade == 0.02
        assert sizer.max_position_pct == 0.25

    def test_risk_based_position(self, sizer):
        """Test risk-based position sizing."""
        result = sizer.calculate_risk_based_position(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=95.0,
        )

        assert isinstance(result, PositionSizeResult)
        assert result.shares > 0
        assert result.dollar_amount > 0
        assert result.risk_amount == 2000  # 100000 * 0.02
        assert result.method_used == "Risk-based"

    def test_risk_based_position_with_custom_risk(self, sizer):
        """Test risk-based sizing with custom risk percentage."""
        result = sizer.calculate_risk_based_position(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=95.0,
            risk_per_trade=0.01,
        )

        assert result.risk_amount == 1000  # 100000 * 0.01
        assert result.risk_percentage == 0.01

    def test_position_capped_at_max(self, sizer):
        """Test that position is capped at maximum size."""
        # Small stop loss would normally result in large position
        result = sizer.calculate_risk_based_position(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=99.5,  # Only $0.50 risk per share
        )

        # Should be capped at 25% of capital = $25000
        assert result.dollar_amount <= 25000

    def test_kelly_position(self, sizer):
        """Test Kelly Criterion position sizing."""
        result = sizer.calculate_kelly_position(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=95.0,
            win_rate=0.55,
            avg_win=5.0,
            avg_loss=3.0,
            kelly_fraction=0.5,
        )

        assert isinstance(result, PositionSizeResult)
        assert hasattr(result, 'kelly_fraction')
        assert result.method_used == "Kelly (50% of full)"

    def test_kelly_with_edge_case(self, sizer):
        """Test Kelly with edge case (zero average win)."""
        result = sizer.calculate_kelly_position(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=95.0,
            win_rate=0.5,
            avg_win=0.0,  # Edge case
            avg_loss=3.0,
        )

        assert isinstance(result, PositionSizeResult)
        # Should handle gracefully

    def test_volatility_adjusted_position(self, sizer):
        """Test volatility-adjusted position sizing."""
        result = sizer.calculate_volatility_adjusted_position(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=95.0,
            volatility=0.03,  # 3% daily volatility
        )

        assert isinstance(result, PositionSizeResult)
        assert result.shares > 0
        assert "volatility" in result.method_used.lower()

    def test_volatility_adjusted_with_low_vol(self, sizer):
        """Test volatility adjustment with low volatility."""
        result = sizer.calculate_volatility_adjusted_position(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=95.0,
            volatility=0.01,  # 1% daily volatility
        )

        # Should allow larger position with low volatility
        assert isinstance(result, PositionSizeResult)


class TestChanDrawdownController:
    """Tests for ChanDrawdownController class."""

    @pytest.fixture
    def controller(self):
        """Create a ChanDrawdownController instance."""
        return ChanDrawdownController(
            max_drawdown=0.25,
            peak_equity=100000.0,
        )

    def test_initialization(self, controller):
        """Test controller initialization."""
        assert controller.max_drawdown == 0.25
        assert controller.peak_equity == 100000.0
        assert controller.current_equity == 100000.0

    def test_update_equity_increases_peak(self, controller):
        """Test that increasing equity updates peak."""
        controller.update_equity(105000.0)

        assert controller.current_equity == 105000.0
        assert controller.peak_equity == 105000.0
        assert controller.get_current_drawdown() == 0.0

    def test_update_equity_decreases(self, controller):
        """Test that decreasing equity creates drawdown."""
        controller.update_equity(90000.0)

        assert controller.current_equity == 90000.0
        assert controller.peak_equity == 100000.0
        assert controller.get_current_drawdown() == 0.10  # 10%

    def test_should_halt_trading(self, controller):
        """Test trading halt condition."""
        # Drawdown of 25% should halt trading
        controller.update_equity(75000.0)

        assert controller.should_halt_trading() is True

    def test_should_not_halt_below_max(self, controller):
        """Test that trading is not halted below max drawdown."""
        controller.update_equity(80000.0)  # 20% drawdown

        assert controller.should_halt_trading() is False

    def test_position_size_multiplier(self, controller):
        """Test position size multiplier based on drawdown."""
        # At 10% drawdown, multiplier should be 0.75
        controller.update_equity(90000.0)

        multiplier = controller.get_position_size_multiplier()
        assert multiplier == 0.75

    def test_multiplier_at_15_percent_drawdown(self, controller):
        """Test multiplier at 15% drawdown."""
        controller.update_equity(85000.0)

        multiplier = controller.get_position_size_multiplier()
        # 15% drawdown falls in the 10-20% range, so multiplier is 0.75
        assert multiplier == 0.75

    def test_risk_of_ruin_calculation(self, controller):
        """Test risk of ruin calculation."""
        risk = controller.calculate_risk_of_ruin(
            win_rate=0.55,
            avg_win=5.0,
            avg_loss=3.0,
            capital_units=100,
        )

        assert isinstance(risk, float)
        assert 0 <= risk <= 1

    def test_risk_of_ruin_negative_edge(self, controller):
        """Test risk of ruin with negative edge."""
        # Negative edge should result in certain ruin
        risk = controller.calculate_risk_of_ruin(
            win_rate=0.4,
            avg_win=3.0,
            avg_loss=5.0,
            capital_units=100,
        )

        assert risk == 1.0


class TestChanRiskMetrics:
    """Tests for ChanRiskMetrics class."""

    @pytest.fixture
    def calculator(self):
        """Create a ChanRiskMetrics instance."""
        return ChanRiskMetrics(confidence_level=0.95)

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns."""
        np.random.seed(42)
        return pd.Series(np.random.randn(252) * 0.01)

    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.confidence_level == 0.95

    def test_calculate_all_metrics(self, calculator, sample_returns):
        """Test comprehensive risk metrics calculation."""
        result = calculator.calculate_all_metrics(sample_returns)

        assert isinstance(result, RiskMetrics)
        assert hasattr(result, 'daily_var_95')
        assert hasattr(result, 'max_drawdown')
        assert hasattr(result, 'sharpe_ratio')

    def test_var_calculation(self, calculator, sample_returns):
        """Test Value at Risk calculation."""
        var = calculator._calculate_var(sample_returns, 0.95)

        assert isinstance(var, float)
        # VaR at 95% should be negative (loss)
        assert var < 0

    def test_cvar_calculation(self, calculator, sample_returns):
        """Test Conditional VaR calculation."""
        cvar = calculator._calculate_cvar(sample_returns, 0.95)

        assert isinstance(cvar, float)
        # CVaR should be more negative than VaR
        var = calculator._calculate_var(sample_returns, 0.95)
        assert cvar <= var

    def test_max_drawdown_from_returns(self, calculator, sample_returns):
        """Test max drawdown calculation from returns."""
        max_dd = calculator._calculate_max_drawdown_from_returns(sample_returns)

        assert isinstance(max_dd, float)
        assert max_dd <= 0  # Drawdown is negative

    def test_sharpe_calculation(self, calculator, sample_returns):
        """Test Sharpe ratio calculation."""
        sharpe = calculator._calculate_sharpe(sample_returns, 0.02)

        assert isinstance(sharpe, float)
        # Sharpe can be positive or negative
        assert -10 < sharpe < 10

    def test_sortino_calculation(self, calculator, sample_returns):
        """Test Sortino ratio calculation."""
        sortino = calculator._calculate_sortino(sample_returns, 0.02)

        assert isinstance(sortino, float)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_calculate_optimal_stop_loss(self):
        """Test optimal stop loss convenience function."""
        result = calculate_optimal_stop_loss(
            entry_price=100.0,
            atr=2.5,
            direction="long",
            method="atr",
        )

        assert isinstance(result, StopLossResult)

    def test_calculate_optimal_stop_loss_fixed(self):
        """Test optimal stop loss with fixed method."""
        result = calculate_optimal_stop_loss(
            entry_price=100.0,
            atr=2.5,
            direction="long",
            method="fixed",
        )

        assert isinstance(result, StopLossResult)
        assert result.method_used == "Fixed percentage"

    def test_calculate_optimal_position_size(self):
        """Test optimal position size convenience function."""
        result = calculate_optimal_position_size(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=95.0,
            method="risk_based",
        )

        assert isinstance(result, PositionSizeResult)

    def test_calculate_optimal_position_size_kelly(self):
        """Test optimal position size with Kelly method."""
        result = calculate_optimal_position_size(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=95.0,
            method="kelly",
            win_rate=0.55,
            avg_win=5.0,
            avg_loss=3.0,
        )

        assert isinstance(result, PositionSizeResult)
        assert result.kelly_fraction is not None


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_capital(self):
        """Test handling of zero capital."""
        sizer = ChanPositionSizer()
        result = sizer.calculate_risk_based_position(
            capital=0,
            entry_price=100.0,
            stop_loss_price=95.0,
        )

        assert isinstance(result, PositionSizeResult)

    def test_stop_equals_entry(self):
        """Test when stop loss equals entry price."""
        sizer = ChanPositionSizer()
        result = sizer.calculate_risk_based_position(
            capital=100000,
            entry_price=100.0,
            stop_loss_price=100.0,  # Same as entry
        )

        # Should handle gracefully
        assert isinstance(result, PositionSizeResult)

    def test_negative_prices(self):
        """Test handling of negative prices."""
        calculator = ChanStopLossCalculator()
        result = calculator.calculate_atr_stop_loss(
            entry_price=-100.0,
            atr=2.5,
            direction="long",
        )

        assert isinstance(result, StopLossResult)

    def test_zero_atr(self):
        """Test handling of zero ATR."""
        calculator = ChanStopLossCalculator()
        result = calculator.calculate_atr_stop_loss(
            entry_price=100.0,
            atr=0.0,
            direction="long",
        )

        assert isinstance(result, StopLossResult)
        # Should use fixed stop fallback

    def test_empty_returns(self):
        """Test with empty returns series."""
        calculator = ChanRiskMetrics()
        import pandas as pd

        result = calculator.calculate_all_metrics(pd.Series([]))

        assert isinstance(result, RiskMetrics)


# Import pandas for tests
import pandas as pd
