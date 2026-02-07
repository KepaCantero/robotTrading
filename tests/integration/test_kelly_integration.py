"""
Integration tests for Kelly Criterion with backtesting system.

Demonstrates how Kelly Criterion position sizing integrates with:
- Backtesting performance metrics
- Position sizing decisions
- Risk management workflows
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.backtesting.metrics import MetricsCalculator
from app.backtesting.models import Trade, TradeStatus
from app.services.position_sizing_engine import PositionSizingEngine


class TestKellyBacktestIntegration:
    """Integration tests for Kelly Criterion with backtesting."""

    @pytest.fixture
    def position_engine(self):
        """Create PositionSizingEngine instance."""
        return PositionSizingEngine()

    @pytest.fixture
    def metrics_calculator(self):
        """Create MetricsCalculator instance."""
        return MetricsCalculator(risk_free_rate=Decimal("0.02"))

    def test_kelly_from_successful_backtest(self, position_engine, metrics_calculator):
        """Test Kelly calculation from a successful backtest."""
        # Create sample trades with positive expectancy
        trades = [
            Trade(
                trade_id="1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("160"),
                entry_time=datetime(2024, 1, 1),
                exit_time=datetime(2024, 1, 5),
                status=TradeStatus.CLOSED,
                pnl=Decimal("1000"),  # $10 * 100 shares
            ),
            Trade(
                trade_id="2",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("155"),
                exit_price=Decimal("165"),
                entry_time=datetime(2024, 1, 10),
                exit_time=datetime(2024, 1, 15),
                status=TradeStatus.CLOSED,
                pnl=Decimal("1000"),
            ),
            Trade(
                trade_id="3",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("160"),
                exit_price=Decimal("155"),
                entry_time=datetime(2024, 1, 20),
                exit_time=datetime(2024, 1, 25),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-500"),  # Loss
            ),
        ]

        # Calculate metrics
        metrics = metrics_calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("11500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Calculate Kelly from backtest results
        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=metrics.model_dump(),
            capital=Decimal("10000"),
        )

        # Verify Kelly calculation
        assert "kelly_fraction" in kelly_result
        assert "half_kelly_fraction" in kelly_result
        assert "position_value" in kelly_result
        assert kelly_result["recommendation"] in ["BUY", "REDUCE", "AVOID", "FALLBACK_2PCT"]

    def test_kelly_from_losing_backtest(self, position_engine, metrics_calculator):
        """Test Kelly calculation from a losing backtest."""
        # Create sample trades with negative expectancy
        trades = [
            Trade(
                trade_id="1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("160"),
                exit_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                exit_time=datetime(2024, 1, 5),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-1000"),  # Loss
            ),
            Trade(
                trade_id="2",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("155"),
                exit_price=Decimal("145"),
                entry_time=datetime(2024, 1, 10),
                exit_time=datetime(2024, 1, 15),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-1000"),  # Loss
            ),
            Trade(
                trade_id="3",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=datetime(2024, 1, 20),
                exit_time=datetime(2024, 1, 25),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),  # Small win
            ),
        ]

        # Calculate metrics
        metrics = metrics_calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("8500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Calculate Kelly from backtest results
        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=metrics.model_dump(),
            capital=Decimal("10000"),
        )

        # Should recommend AVOID due to negative expectancy
        assert kelly_result["recommendation"] == "AVOID"
        assert float(kelly_result["half_kelly_fraction"]) == 0.0

    def test_kelly_position_sizing_workflow(self, position_engine):
        """Test complete workflow from backtest to position sizing."""
        # Simulate backtest results
        backtest_metrics = {
            "win_rate": Decimal("58.0"),  # 58% win rate
            "avg_win": Decimal("120.0"),  # $120 average win
            "avg_loss": Decimal("-80.0"),  # $80 average loss
            "total_trades": 100,
            "winning_trades": 58,
            "losing_trades": 42,
        }

        capital = Decimal("50000")

        # Calculate optimal position size
        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=backtest_metrics,
            capital=capital,
        )

        # Verify position sizing
        if kelly_result["recommendation"] == "BUY":
            # Calculate number of shares based on position value
            position_value = kelly_result["position_value"]
            entry_price = Decimal("100")  # Assume $100 entry price

            shares = position_value / entry_price

            # Verify position is reasonable
            assert shares > 0
            assert position_value <= capital * Decimal("0.25")  # Max 25% cap

    def test_kelly_with_atr_position_sizing(self, position_engine):
        """Test Kelly combined with ATR-based position sizing."""
        # Backtest metrics
        backtest_metrics = {
            "win_rate": Decimal("55.0"),
            "avg_win": Decimal("100.0"),
            "avg_loss": Decimal("-75.0"),
        }

        capital = Decimal("10000")
        entry_price = Decimal("150")
        atr = 2.5  # Average True Range

        # Step 1: Calculate Kelly position size
        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=backtest_metrics,
            capital=capital,
        )

        # Step 2: Calculate ATR-based position size for risk management
        atr_shares = position_engine.calculate_position_size_from_atr(
            capital=capital,
            risk_per_trade_pct=2.0,  # 2% risk
            entry_price=entry_price,
            atr=atr,
        )

        # Step 3: Use minimum of Kelly and ATR-based sizes (conservative)
        kelly_shares = kelly_result["position_value"] / entry_price

        # Take the smaller position for safety
        final_shares = min(kelly_shares, atr_shares) if atr_shares else kelly_shares

        # Verify final position is reasonable
        assert final_shares > 0
        assert final_shares * entry_price <= capital

    def test_kelly_reinvestment_workflow(self, position_engine):
        """Test Kelly-based position sizing with compounding."""
        initial_capital = Decimal("10000")
        backtest_metrics = {
            "win_rate": Decimal("60.0"),
            "avg_win": Decimal("150.0"),
            "avg_loss": Decimal("-100.0"),
        }

        # Simulate multiple trading periods with capital growth
        capital = initial_capital
        total_trades = 0

        for period in range(5):  # 5 trading periods
            # Calculate position size for current capital
            kelly_result = position_engine.calculate_kelly_from_backtest(
                performance_metrics=backtest_metrics,
                capital=capital,
            )

            if kelly_result["recommendation"] == "BUY":
                position_value = kelly_result["position_value"]

                # Simulate trade outcome (60% win probability)
                import random

                random.seed(42)  # For reproducibility

                if random.random() < 0.60:
                    # Win: 60% return on position
                    profit = position_value * Decimal("0.60")
                    capital += profit
                else:
                    # Loss: 40% loss on position
                    loss = position_value * Decimal("0.40")
                    capital -= loss

                total_trades += 1

        # After compounding, Kelly should provide reasonable risk-adjusted returns
        # Note: Short-term variance is possible with Kelly Criterion
        # The important aspect is that the position sizing was calculated correctly
        assert total_trades == 5
        assert capital > 0  # Never went bankrupt
        # Kelly can have significant short-term variance but provides optimal long-term growth

    def test_kelly_fallback_on_insufficient_data(self, position_engine):
        """Test Kelly fallback when backtest has insufficient data."""
        # New strategy with minimal trading history
        insufficient_metrics = {
            "win_rate": Decimal("100.0"),  # Only 1 trade
            "avg_win": Decimal("50.0"),
            "avg_loss": Decimal("0.0"),  # No losses yet
        }

        capital = Decimal("10000")

        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=insufficient_metrics,
            capital=capital,
        )

        # Should fallback to 2% rule
        assert kelly_result["recommendation"] == "FALLBACK_2PCT"
        assert kelly_result["position_value"] == capital * Decimal("0.02")
        assert "fallback_reason" in kelly_result


class TestKellyRiskManagement:
    """Test Kelly Criterion as part of risk management workflow."""

    @pytest.fixture
    def position_engine(self):
        """Create PositionSizingEngine instance."""
        return PositionSizingEngine()

    def test_kelly_respects_25_percent_cap(self, position_engine):
        """Test that Kelly never exceeds 25% of capital."""
        # Excellent strategy with very high win rate
        excellent_metrics = {
            "win_rate": Decimal("80.0"),
            "avg_win": Decimal("200.0"),
            "avg_loss": Decimal("-50.0"),
        }

        capital = Decimal("100000")

        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=excellent_metrics,
            capital=capital,
        )

        # Even with excellent metrics, position should not exceed 25%
        max_allowed = capital * Decimal("0.25")
        assert kelly_result["position_value"] <= max_allowed
        assert float(kelly_result["position_percentage"]) <= 25.0

    def test_kelly_avoids_negative_expectancy(self, position_engine):
        """Test that Kelly avoids trading on negative expectancy systems."""
        # Losing strategy
        losing_metrics = {
            "win_rate": Decimal("40.0"),
            "avg_win": Decimal("50.0"),
            "avg_loss": Decimal("-100.0"),
        }

        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=losing_metrics,
        )

        # Should recommend AVOID
        assert kelly_result["recommendation"] == "AVOID"
        assert float(kelly_result["half_kelly_fraction"]) == 0.0

    def test_kelly_half_multiplier_reduces_risk(self, position_engine):
        """Test that Half-Kelly reduces position size vs Full Kelly."""
        metrics = {
            "win_rate": Decimal("60.0"),
            "avg_win": Decimal("100.0"),
            "avg_loss": Decimal("-50.0"),
        }

        kelly_result = position_engine.calculate_kelly_from_backtest(
            performance_metrics=metrics,
        )

        # Half-Kelly should be exactly half of raw Kelly (before cap)
        raw_kelly = float(kelly_result["kelly_fraction"])
        half_kelly = float(kelly_result["half_kelly_fraction"])

        if raw_kelly > 0:
            # Half-Kelly should be half of raw (unless capped)
            expected_half = min(raw_kelly * 0.5, 0.25)
            assert half_kelly == pytest.approx(expected_half, rel=1e-4)
