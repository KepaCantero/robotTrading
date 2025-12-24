"""
Unit tests for Risk Scaling Components (PHASE 3)

Consolidated tests for SharpeRatioMonitor, LossMonitor, and DrawdownMonitor.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from app.services.risk_scaling.sharpe_ratio_monitor import SharpeRatioMonitor
from app.services.risk_scaling.loss_monitor import LossMonitor, TradeResult
from app.services.risk_scaling.drawdown_monitor import DrawdownMonitor, EquityPoint
from app.services.risk_scaling.models import RiskScalingFactors


class TestSharpeRatioMonitor:
    """Test suite for SharpeRatioMonitor."""

    @pytest.fixture
    def monitor(self):
        return SharpeRatioMonitor()

    @pytest.mark.asyncio
    async def test_calculate_rolling_sharpe(self, monitor):
        """Test Sharpe ratio calculation."""
        returns = [Decimal(str(0.01 * (-1 if i % 3 == 0 else 1))) for i in range(30)]
        sharpe = await monitor.calculate_rolling_sharpe(returns, window_days=30)
        assert isinstance(sharpe, Decimal)

    @pytest.mark.asyncio
    async def test_sharpe_with_insufficient_data(self, monitor):
        """Test Sharpe with too few data points."""
        returns = [Decimal("0.01")] * 5
        sharpe = await monitor.calculate_rolling_sharpe(returns, window_days=30)
        assert sharpe == Decimal("0")

    def test_sharpe_scale_mapping(self, monitor):
        """Test Sharpe to scaling factor mapping."""
        assert monitor.calculate_sharpe_scale(Decimal("2.0")) == Decimal("1.0")  # Strong
        assert monitor.calculate_sharpe_scale(Decimal("0.5")) < Decimal("1.0")  # Acceptable
        assert monitor.calculate_sharpe_scale(Decimal("0")) < Decimal("0.5")  # Weak
        assert monitor.calculate_sharpe_scale(Decimal("-1")) == Decimal("0.2")  # Negative

    def test_is_sharpe_declining(self, monitor):
        """Test Sharpe decline detection."""
        current = Decimal("1.0")
        previous = Decimal("1.5")
        is_declining, reason = monitor.is_sharpe_declining(current, previous)
        assert is_declining is True

    def test_get_sharpe_interpretation(self, monitor):
        """Test Sharpe interpretation text."""
        assert "Outstanding" in monitor.get_sharpe_interpretation(Decimal("2.5"))
        assert "Good" in monitor.get_sharpe_interpretation(Decimal("1.0"))
        assert "Poor" in monitor.get_sharpe_interpretation(Decimal("-0.5"))

    def test_information_ratio(self, monitor):
        """Test Information Ratio calculation."""
        portfolio = [Decimal("0.01"), Decimal("0.02"), Decimal("0.015")]
        benchmark = [Decimal("0.005"), Decimal("0.010"), Decimal("0.010")]
        ir = monitor.calculate_information_ratio(portfolio, benchmark)
        assert isinstance(ir, Decimal)


class TestLossMonitor:
    """Test suite for LossMonitor."""

    @pytest.fixture
    def monitor(self):
        return LossMonitor(reset_threshold=3)

    def test_detect_consecutive_losses(self, monitor):
        """Test consecutive loss detection."""
        trades = [
            TradeResult(
                trade_id="1", timestamp=datetime.now(), pnl=Decimal("-100"),
                symbol="TEST", side="buy", entry_price=Decimal("100"),
                exit_price=Decimal("99"), quantity=Decimal("1")
            ),
            TradeResult(
                trade_id="2", timestamp=datetime.now(), pnl=Decimal("-50"),
                symbol="TEST", side="buy", entry_price=Decimal("100"),
                exit_price=Decimal("99.5"), quantity=Decimal("1")
            ),
            TradeResult(
                trade_id="3", timestamp=datetime.now(), pnl=Decimal("100"),
                symbol="TEST", side="buy", entry_price=Decimal("100"),
                exit_price=Decimal("101"), quantity=Decimal("1")
            ),
        ]

        losses = monitor.detect_consecutive_losses(trades)
        assert losses == 0  # Last trade is a win, so no consecutive losses

    def test_loss_scale_calculation(self, monitor):
        """Test loss scale mapping."""
        assert monitor.calculate_loss_scale(0) == Decimal("1.0")
        assert monitor.calculate_loss_scale(1) == Decimal("0.9")
        assert monitor.calculate_loss_scale(2) == Decimal("0.8")
        assert monitor.calculate_loss_scale(3) == Decimal("0.6")
        assert monitor.calculate_loss_scale(5) == Decimal("0.5")  # Max reduction

    def test_should_reset_loss_counter(self, monitor):
        """Test loss counter reset condition."""
        trades = [
            TradeResult("1", datetime.now(), Decimal("100"), "TEST", "buy",
                       Decimal("100"), Decimal("101"), Decimal("1")),
            TradeResult("2", datetime.now(), Decimal("100"), "TEST", "buy",
                       Decimal("100"), Decimal("101"), Decimal("1")),
            TradeResult("3", datetime.now(), Decimal("100"), "TEST", "buy",
                       Decimal("100"), Decimal("101"), Decimal("1")),
        ]

        should_reset = monitor.should_reset_loss_counter(trades)
        assert should_reset is True  # 3 wins meets reset threshold

    def test_calculate_win_rate(self, monitor):
        """Test win rate calculation."""
        trades = [
            TradeResult("1", datetime.now(), Decimal("100"), "TEST", "buy",
                       Decimal("100"), Decimal("101"), Decimal("1")),
            TradeResult("2", datetime.now(), Decimal("-100"), "TEST", "buy",
                       Decimal("100"), Decimal("99"), Decimal("1")),
        ]

        win_rate = monitor.calculate_win_rate(trades)
        assert win_rate == Decimal("50.00")  # 1 win out of 2

    def test_calculate_win_loss_ratio(self, monitor):
        """Test win/loss ratio."""
        trades = [
            TradeResult("1", datetime.now(), Decimal("200"), "TEST", "buy",
                       Decimal("100"), Decimal("101"), Decimal("1")),
            TradeResult("2", datetime.now(), Decimal("-100"), "TEST", "buy",
                       Decimal("100"), Decimal("99"), Decimal("1")),
        ]

        ratio = monitor.calculate_average_win_loss_ratio(trades)
        assert ratio == Decimal("2.00")  # Wins are 2x losses


class TestDrawdownMonitor:
    """Test suite for DrawdownMonitor."""

    @pytest.fixture
    def monitor(self):
        return DrawdownMonitor(max_drawdown_limit=Decimal("0.15"))

    def test_calculate_drawdown(self, monitor):
        """Test drawdown calculation."""
        equity_curve = [
            Decimal("10000"), Decimal("11000"), Decimal("10500"),
            Decimal("9500"), Decimal("9000"),
        ]

        current_dd, max_dd = monitor.calculate_drawdown(equity_curve)
        assert current_dd > Decimal("0")  # Currently underwater
        assert max_dd > Decimal("0")

    def test_calculate_drawdown_no_loss(self, monitor):
        """Test drawdown with only gains."""
        equity_curve = [
            Decimal("10000"), Decimal("11000"), Decimal("12000"),
        ]

        current_dd, max_dd = monitor.calculate_drawdown(equity_curve)
        assert current_dd == Decimal("0")
        assert max_dd == Decimal("0")

    def test_drawdown_scale_normal(self, monitor):
        """Test scaling for normal drawdown."""
        scale = monitor.calculate_drawdown_scale(Decimal("0.03"))
        assert scale == Decimal("1.0")

    def test_drawdown_scale_caution(self, monitor):
        """Test scaling for caution level."""
        scale = monitor.calculate_drawdown_scale(Decimal("0.07"))
        assert scale == Decimal("0.8")

    def test_drawdown_scale_warning(self, monitor):
        """Test scaling for warning level."""
        scale = monitor.calculate_drawdown_scale(Decimal("0.12"))
        assert scale == Decimal("0.5")

    def test_drawdown_scale_halt(self, monitor):
        """Test scaling for halt level."""
        scale = monitor.calculate_drawdown_scale(Decimal("0.20"))
        assert scale == Decimal("0.0")

    def test_should_halt_trading(self, monitor):
        """Test circuit breaker activation."""
        should_halt = monitor.should_halt_trading(Decimal("0.15"))
        assert should_halt is True

        should_halt = monitor.should_halt_trading(Decimal("0.10"))
        assert should_halt is False

    def test_has_recovered(self, monitor):
        """Test recovery detection."""
        equity_curve = [
            Decimal("10000"), Decimal("9000"), Decimal("10500"),
        ]

        has_recovered = monitor.has_recovered(equity_curve)
        assert has_recovered is True

    def test_get_drawdown_level(self, monitor):
        """Test drawdown level classification."""
        assert monitor.get_drawdown_level(Decimal("0.03")) == "NORMAL"
        assert monitor.get_drawdown_level(Decimal("0.07")) == "CAUTION"
        assert monitor.get_drawdown_level(Decimal("0.12")) == "WARNING"
        assert monitor.get_drawdown_level(Decimal("0.20")) == "HALT"

    def test_get_drawdown_timeline(self, monitor):
        """Test drawdown timeline information."""
        equity_points = [
            EquityPoint(datetime.now(), Decimal("10000")),
            EquityPoint(datetime.now(), Decimal("9500")),
            EquityPoint(datetime.now(), Decimal("9000")),
        ]

        timeline = monitor.get_drawdown_timeline(equity_points)
        assert "current_drawdown" in timeline
        assert "max_drawdown" in timeline
        assert "peak_equity" in timeline

    def test_suggest_drawdown_action(self, monitor):
        """Test action suggestions based on drawdown."""
        action, desc = monitor.suggest_drawdown_action(Decimal("0.03"))
        assert action == "NORMAL"

        action, desc = monitor.suggest_drawdown_action(Decimal("0.12"))
        assert action == "REDUCE_50"

        action, desc = monitor.suggest_drawdown_action(Decimal("0.20"))
        assert action == "STOP"


class TestRiskScalingFactorsModel:
    """Test RiskScalingFactors data model."""

    def test_combined_scale_calculation(self):
        """Test combined scaling factor calculation."""
        factors = RiskScalingFactors(
            volatility_scale=Decimal("1.0"),
            sharpe_scale=Decimal("1.0"),
            loss_scale=Decimal("0.8"),
            drawdown_scale=Decimal("1.0"),
        )

        assert factors.combined_scale == Decimal("0.8")

    def test_is_extreme_true(self):
        """Test extreme detection."""
        factors = RiskScalingFactors(
            volatility_scale=Decimal("0.5"),
            sharpe_scale=Decimal("1.0"),
            loss_scale=Decimal("1.0"),
            drawdown_scale=Decimal("1.0"),
        )

        assert factors.is_extreme is True

    def test_is_extreme_false(self):
        """Test non-extreme factors."""
        factors = RiskScalingFactors(
            volatility_scale=Decimal("1.0"),
            sharpe_scale=Decimal("0.9"),
            loss_scale=Decimal("0.9"),
            drawdown_scale=Decimal("1.0"),
        )

        assert factors.is_extreme is False

    def test_is_halted(self):
        """Test halt detection."""
        factors_halted = RiskScalingFactors(
            volatility_scale=Decimal("1.0"),
            sharpe_scale=Decimal("1.0"),
            loss_scale=Decimal("1.0"),
            drawdown_scale=Decimal("0.0"),
        )

        assert factors_halted.is_halted is True

        factors_normal = RiskScalingFactors(
            volatility_scale=Decimal("1.0"),
            sharpe_scale=Decimal("1.0"),
            loss_scale=Decimal("1.0"),
            drawdown_scale=Decimal("0.5"),
        )

        assert factors_normal.is_halted is False
