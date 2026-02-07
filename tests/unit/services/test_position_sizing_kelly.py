"""
Unit tests for Kelly Criterion position sizing implementation.

Tests cover Ernest Chan Rule 1.9 requirements:
- Half-Kelly calculation
- 25% maximum position cap
- Fallback to 2% rule when metrics unavailable
- Input validation and error handling
- Edge cases and boundary conditions
"""

from decimal import Decimal

import pytest

from app.services.position_sizing_engine import PositionSizingEngine


class TestKellyPositionSize:
    """Test suite for Kelly Criterion position sizing calculations."""

    @pytest.fixture
    def engine(self):
        """Create PositionSizingEngine instance for testing."""
        return PositionSizingEngine()

    def test_kelly_basic_calculation(self, engine):
        """Test basic Kelly Criterion calculation with valid inputs."""
        result = engine.calculate_kelly_position_size(
            win_rate=0.55,
            avg_win=100.0,
            avg_loss=75.0,
        )

        # Kelly = (0.55 * 100 - 0.45 * 75) / 100
        # Kelly = (55 - 33.75) / 100 = 21.25 / 100 = 0.2125
        # Half-Kelly = 0.10625
        assert float(result["kelly_fraction"]) == pytest.approx(0.2125, rel=1e-4)
        assert float(result["half_kelly_fraction"]) == pytest.approx(0.10625, rel=1e-4)
        assert result["recommendation"] == "BUY"

    def test_kelly_with_capital(self, engine):
        """Test Kelly calculation with capital provided."""
        capital = Decimal("10000")
        result = engine.calculate_kelly_position_size(
            win_rate=0.55,
            avg_win=100.0,
            avg_loss=75.0,
            capital=capital,
        )

        # Position should be ~10.875% of $10,000 = $1,087.50
        assert "position_value" in result
        assert result["position_value"] == capital * Decimal(str(result["half_kelly_fraction"]))

    def test_kelly_half_kelly_safety(self, engine):
        """Test Half-Kelly safety multiplier is applied."""
        result = engine.calculate_kelly_position_size(
            win_rate=0.60,
            avg_win=100.0,
            avg_loss=50.0,
        )

        # Kelly = (0.60 * 100 - 0.40 * 50) / 100 = 0.40
        # Half-Kelly = 0.20
        assert float(result["kelly_fraction"]) == pytest.approx(0.40, rel=1e-4)
        assert float(result["half_kelly_fraction"]) == pytest.approx(0.20, rel=1e-4)

    def test_kelly_25_percent_cap(self, engine):
        """Test that Kelly is capped at 25% maximum."""
        # High win rate and favorable ratio should produce >25% raw Kelly
        result = engine.calculate_kelly_position_size(
            win_rate=0.80,
            avg_win=200.0,
            avg_loss=50.0,
        )

        # Even if raw Kelly > 0.50, Half-Kelly should be capped at 0.25
        assert float(result["half_kelly_fraction"]) <= 0.25
        assert float(result["position_percentage"]) <= 25.0

    def test_kelly_negative_expectancy(self, engine):
        """Test Kelly with negative expectancy (losing system)."""
        result = engine.calculate_kelly_position_size(
            win_rate=0.40,
            avg_win=50.0,
            avg_loss=100.0,
        )

        # Kelly = (0.40 * 50 - 0.60 * 100) / 50 = -1.0
        # Should recommend AVOID
        assert float(result["kelly_fraction"]) < 0
        assert float(result["half_kelly_fraction"]) == 0.0
        assert result["recommendation"] == "AVOID"

    def test_kelly_marginal_edge(self, engine):
        """Test Kelly with marginal edge (0 < Kelly < 0.02)."""
        result = engine.calculate_kelly_position_size(
            win_rate=0.51,
            avg_win=100.0,
            avg_loss=99.0,
        )

        # Small positive Kelly should recommend REDUCE
        # Kelly = (0.51 * 100 - 0.49 * 99) / 100 = (51 - 48.51) / 100 = 0.0249
        assert float(result["kelly_fraction"]) > 0
        assert float(result["kelly_fraction"]) > 0.02  # Above REDUCE threshold
        assert result["recommendation"] == "BUY"

    def test_kelly_input_validation_win_rate(self, engine):
        """Test win_rate input validation."""
        # Win rate > 1.0 should raise error
        with pytest.raises(ValueError, match="win_rate must be between 0 and 1"):
            engine.calculate_kelly_position_size(
                win_rate=1.5,
                avg_win=100.0,
                avg_loss=50.0,
            )

        # Negative win rate should raise error
        with pytest.raises(ValueError, match="win_rate must be between 0 and 1"):
            engine.calculate_kelly_position_size(
                win_rate=-0.1,
                avg_win=100.0,
                avg_loss=50.0,
            )

    def test_kelly_input_validation_avg_win(self, engine):
        """Test avg_win input validation."""
        # Zero avg_win should raise error
        with pytest.raises(ValueError, match="avg_win must be positive"):
            engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=0.0,
                avg_loss=50.0,
            )

        # Negative avg_win should raise error
        with pytest.raises(ValueError, match="avg_win must be positive"):
            engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=-10.0,
                avg_loss=50.0,
            )

    def test_kelly_input_validation_avg_loss(self, engine):
        """Test avg_loss input validation."""
        # Zero avg_loss should raise error
        with pytest.raises(ValueError, match="avg_loss must be positive"):
            engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=100.0,
                avg_loss=0.0,
            )

    def test_kelly_input_type_validation(self, engine):
        """Test type validation for inputs."""
        with pytest.raises(ValueError, match="win_rate must be numeric"):
            engine.calculate_kelly_position_size(
                win_rate="invalid",
                avg_win=100.0,
                avg_loss=50.0,
            )

    def test_kelly_with_decimal_inputs(self, engine):
        """Test Kelly calculation with Decimal inputs."""
        result = engine.calculate_kelly_position_size(
            win_rate=Decimal("0.55"),
            avg_win=Decimal("100.0"),
            avg_loss=Decimal("75.0"),
        )

        assert float(result["kelly_fraction"]) == pytest.approx(0.2125, rel=1e-4)
        assert result["recommendation"] == "BUY"

    def test_kelly_capital_validation(self, engine):
        """Test capital input validation."""
        # Negative capital should raise error
        with pytest.raises(ValueError, match="capital must be positive"):
            engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=100.0,
                avg_loss=75.0,
                capital=Decimal("-1000"),
            )

        # Zero capital should raise error
        with pytest.raises(ValueError, match="capital must be positive"):
            engine.calculate_kelly_position_size(
                win_rate=0.55,
                avg_win=100.0,
                avg_loss=75.0,
                capital=Decimal("0"),
            )

    def test_kelly_position_percentage_calculation(self, engine):
        """Test position_percentage is correctly calculated."""
        result = engine.calculate_kelly_position_size(
            win_rate=0.60,
            avg_win=100.0,
            avg_loss=50.0,
        )

        # Half-Kelly = 0.20, position_percentage should be 20.0
        assert float(result["position_percentage"]) == pytest.approx(20.0, rel=1e-4)

    def test_kelly_absolute_avg_loss(self, engine):
        """Test that avg_loss is treated as absolute value."""
        # avg_loss can be provided as negative value
        result1 = engine.calculate_kelly_position_size(
            win_rate=0.55,
            avg_win=100.0,
            avg_loss=75.0,  # Positive
        )

        result2 = engine.calculate_kelly_position_size(
            win_rate=0.55,
            avg_win=100.0,
            avg_loss=-75.0,  # Negative
        )

        # Both should produce same result
        assert result1["kelly_fraction"] == result2["kelly_fraction"]
        assert result1["half_kelly_fraction"] == result2["half_kelly_fraction"]


class TestKellyFromBacktest:
    """Test suite for Kelly calculation from backtest metrics."""

    @pytest.fixture
    def engine(self):
        """Create PositionSizingEngine instance for testing."""
        return PositionSizingEngine()

    def test_kelly_from_backtest_percentage_win_rate(self, engine):
        """Test Kelly calculation with percentage win_rate (0-100)."""
        metrics = {
            "win_rate": Decimal("55.0"),  # 55% as percentage
            "avg_win": Decimal("100.0"),
            "avg_loss": Decimal("-75.0"),
        }

        result = engine.calculate_kelly_from_backtest(metrics)

        # Should convert 55% to 0.55 decimal
        assert float(result["kelly_fraction"]) == pytest.approx(0.2125, rel=1e-4)

    def test_kelly_from_backtest_decimal_win_rate(self, engine):
        """Test Kelly calculation with decimal win_rate (0-1)."""
        metrics = {
            "win_rate": Decimal("0.55"),  # Already decimal
            "avg_win": Decimal("100.0"),
            "avg_loss": Decimal("-75.0"),
        }

        result = engine.calculate_kelly_from_backtest(metrics)

        # Should use 0.55 as-is
        assert float(result["kelly_fraction"]) == pytest.approx(0.2125, rel=1e-4)

    def test_kelly_from_backtest_with_capital(self, engine):
        """Test Kelly from backtest with capital provided."""
        metrics = {
            "win_rate": 60.0,
            "avg_win": 100.0,
            "avg_loss": -50.0,
        }

        capital = Decimal("10000")
        result = engine.calculate_kelly_from_backtest(metrics, capital=capital)

        assert "position_value" in result
        assert result["position_value"] > 0

    def test_kelly_from_backtest_fallback_2_percent(self, engine):
        """Test fallback to 2% rule when metrics insufficient."""
        # Missing avg_win or avg_loss
        metrics = {
            "win_rate": 55.0,
            "avg_win": 0.0,  # Invalid
            "avg_loss": -75.0,
        }

        result = engine.calculate_kelly_from_backtest(metrics)

        # Should use 2% fallback
        assert result["recommendation"] == "FALLBACK_2PCT"
        assert float(result["half_kelly_fraction"]) == 0.02
        assert "fallback_reason" in result

    def test_kelly_from_backtest_fallback_with_capital(self, engine):
        """Test fallback to 2% rule with capital provided."""
        metrics = {
            "win_rate": 55.0,
            "avg_win": 0.0,  # Invalid
            "avg_loss": -75.0,
        }

        capital = Decimal("10000")
        result = engine.calculate_kelly_from_backtest(metrics, capital=capital)

        # Should calculate 2% of capital
        assert result["position_value"] == capital * Decimal("0.02")
        assert result["recommendation"] == "FALLBACK_2PCT"

    def test_kelly_from_backtest_missing_metrics(self, engine):
        """Test Kelly from backtest with missing metric keys."""
        metrics = {
            "win_rate": 55.0,
            # avg_win and avg_loss missing
        }

        result = engine.calculate_kelly_from_backtest(metrics)

        # Should use fallback with zeros
        assert result["recommendation"] == "FALLBACK_2PCT"

    def test_kelly_from_backtest_negative_avg_loss(self, engine):
        """Test that negative avg_loss is handled correctly."""
        metrics = {
            "win_rate": 55.0,
            "avg_win": 100.0,
            "avg_loss": -75.0,  # Negative (as stored in backtesting)
        }

        result = engine.calculate_kelly_from_backtest(metrics)

        # Should convert to absolute value
        assert float(result["kelly_fraction"]) == pytest.approx(0.2125, rel=1e-4)


class TestKellyEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def engine(self):
        """Create PositionSizingEngine instance for testing."""
        return PositionSizingEngine()

    def test_kelly_zero_win_rate(self, engine):
        """Test Kelly with 0% win rate (always lose)."""
        result = engine.calculate_kelly_position_size(
            win_rate=0.0,
            avg_win=100.0,
            avg_loss=50.0,
        )

        # Should recommend AVOID
        assert result["recommendation"] == "AVOID"
        assert float(result["half_kelly_fraction"]) == 0.0

    def test_kelly_perfect_win_rate(self, engine):
        """Test Kelly with 100% win rate (always win)."""
        result = engine.calculate_kelly_position_size(
            win_rate=1.0,
            avg_win=100.0,
            avg_loss=50.0,
        )

        # Kelly = (1.0 * 100 - 0.0 * 50) / 100 = 1.0
        # Half-Kelly capped at 0.25
        assert float(result["kelly_fraction"]) == 1.0
        assert float(result["half_kelly_fraction"]) == 0.25  # Capped

    def test_kelly_equal_win_loss(self, engine):
        """Test Kelly with equal avg_win and avg_loss."""
        # If avg_win == avg_loss, Kelly = win_rate - (1 - win_rate) = 2*win_rate - 1
        result = engine.calculate_kelly_position_size(
            win_rate=0.60,
            avg_win=100.0,
            avg_loss=100.0,
        )

        # Kelly = 0.60 - 0.40 = 0.20
        # Half-Kelly = 0.10
        assert float(result["kelly_fraction"]) == pytest.approx(0.20, rel=1e-4)
        assert float(result["half_kelly_fraction"]) == pytest.approx(0.10, rel=1e-4)

    def test_kelly_break_even(self, engine):
        """Test Kelly at break-even point."""
        # Kelly = 0 when win_rate * avg_win = (1 - win_rate) * avg_loss
        # 0.50 * 100 = 0.50 * 100 = 50
        result = engine.calculate_kelly_position_size(
            win_rate=0.50,
            avg_win=100.0,
            avg_loss=100.0,
        )

        # Kelly = 0, should recommend AVOID
        assert float(result["kelly_fraction"]) == pytest.approx(0.0, abs=1e-10)
        assert result["recommendation"] == "AVOID"

    def test_kelly_25_percent_exact_boundary(self, engine):
        """Test Kelly at exact 25% Half-Kelly boundary."""
        # Half-Kelly = 0.25 when raw Kelly = 0.50
        # 0.50 = (w * 100 - (1-w) * 50) / 100
        # 50 = 100w - 50 + 50w = 150w - 50
        # 100 = 150w => w = 2/3
        result = engine.calculate_kelly_position_size(
            win_rate=Decimal("2") / Decimal("3"),
            avg_win=100.0,
            avg_loss=50.0,
        )

        # Should be exactly at 25% cap
        assert float(result["half_kelly_fraction"]) == pytest.approx(0.25, rel=1e-4)

    def test_kelly_very_small_edge(self, engine):
        """Test Kelly with very small positive edge."""
        result = engine.calculate_kelly_position_size(
            win_rate=0.502,
            avg_win=100.0,
            avg_loss=99.0,
        )

        # Very small Kelly should recommend REDUCE
        assert float(result["kelly_fraction"]) > 0
        assert result["recommendation"] == "REDUCE"
