"""
Tests for Strategy Validator (FASE 5 Task 1)

Tests for Sharpe ratio >= 1.0 validation (Chan #8)
and Max Drawdown <= 25% validation (Chan #10)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.backtesting.validation.strategy_validator import (
    MAX_MAX_DRAWDOWN,
    MIN_SHARPE_RATIO,
    StrategyValidator,
    ValidationLevel,
    ValidationResult,
    validate_strategy,
)


class TestStrategyValidator:
    """Test suite for StrategyValidator class."""

    def test_initialization_with_defaults(self):
        """Test validator initializes with default thresholds."""
        validator = StrategyValidator()
        assert validator.min_sharpe == MIN_SHARPE_RATIO
        assert validator.max_drawdown == MAX_MAX_DRAWDOWN

    def test_initialization_with_custom_thresholds(self):
        """Test validator can be initialized with custom thresholds."""
        validator = StrategyValidator(min_sharpe=Decimal("1.5"), max_drawdown=Decimal("-0.20"))
        assert validator.min_sharpe == Decimal("1.5")
        assert validator.max_drawdown == Decimal("-0.20")

    def test_validate_sharpe_ratio_pass(self):
        """Test Sharpe ratio validation passes for values >= 1.0."""
        validator = StrategyValidator()

        # Edge case: exactly 1.0
        assert validator.validate_sharpe_ratio(Decimal("1.0")) is True

        # Above threshold
        assert validator.validate_sharpe_ratio(Decimal("1.5")) is True
        assert validator.validate_sharpe_ratio(Decimal("2.0")) is True
        assert validator.validate_sharpe_ratio(Decimal("3.5")) is True

    def test_validate_sharpe_ratio_fail(self):
        """Test Sharpe ratio validation fails for values < 1.0."""
        validator = StrategyValidator()

        # Below threshold
        assert validator.validate_sharpe_ratio(Decimal("0.99")) is False
        assert validator.validate_sharpe_ratio(Decimal("0.5")) is False
        assert validator.validate_sharpe_ratio(Decimal("0.0")) is False
        assert validator.validate_sharpe_ratio(Decimal("-1.0")) is False

    def test_validate_max_drawdown_pass(self):
        """Test max drawdown validation passes for losses <= 25%."""
        validator = StrategyValidator()

        # Edge case: exactly -25%
        assert validator.validate_max_drawdown(Decimal("-0.25")) is True

        # Smaller losses (less negative is better)
        assert validator.validate_max_drawdown(Decimal("-0.20")) is True
        assert validator.validate_max_drawdown(Decimal("-0.15")) is True
        assert validator.validate_max_drawdown(Decimal("-0.10")) is True
        assert validator.validate_max_drawdown(Decimal("0.0")) is True

    def test_validate_max_drawdown_fail(self):
        """Test max drawdown validation fails for losses > 25%."""
        validator = StrategyValidator()

        # Larger losses (more negative)
        assert validator.validate_max_drawdown(Decimal("-0.26")) is False
        assert validator.validate_max_drawdown(Decimal("-0.30")) is False
        assert validator.validate_max_drawdown(Decimal("-0.50")) is False

    def test_validate_both_metrics_pass(self):
        """Test validation passes when both metrics meet thresholds."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("1.5"), max_drawdown=Decimal("-0.15"))

        assert result.is_valid is True
        assert result.validation_level == ValidationLevel.PASS
        assert result.sharpe_passes is True
        assert result.drawdown_passes is True
        assert len(result.errors) == 0

    def test_validate_sharpe_fails_only(self):
        """Test validation fails when only Sharpe is below threshold."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("0.8"), max_drawdown=Decimal("-0.15"))

        assert result.is_valid is False
        assert result.validation_level == ValidationLevel.FAIL
        assert result.sharpe_passes is False
        assert result.drawdown_passes is True
        assert len(result.errors) == 1
        assert "Sharpe ratio" in result.errors[0]

    def test_validate_drawdown_fails_only(self):
        """Test validation fails when only max drawdown exceeds threshold."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("1.5"), max_drawdown=Decimal("-0.30"))

        assert result.is_valid is False
        assert result.validation_level == ValidationLevel.FAIL
        assert result.sharpe_passes is True
        assert result.drawdown_passes is False
        assert len(result.errors) == 1
        assert "drawdown" in result.errors[0]

    def test_validate_both_metrics_fail(self):
        """Test validation fails when both metrics exceed thresholds."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("0.5"), max_drawdown=Decimal("-0.40"))

        assert result.is_valid is False
        assert result.validation_level == ValidationLevel.FAIL
        assert result.sharpe_passes is False
        assert result.drawdown_passes is False
        assert len(result.errors) == 2

    def test_validate_edge_case_sharpe_exactly_threshold(self):
        """Test validation for Sharpe ratio exactly at threshold."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("1.0"), max_drawdown=Decimal("-0.20"))

        assert result.is_valid is True
        assert result.sharpe_passes is True

    def test_validate_edge_case_drawdown_exactly_threshold(self):
        """Test validation for max drawdown exactly at threshold."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("1.5"), max_drawdown=Decimal("-0.25"))

        assert result.is_valid is True
        assert result.drawdown_passes is True

    def test_validate_with_warnings_marginal_sharpe(self):
        """Test validation generates warnings for marginal Sharpe (1.0-1.5)."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("1.2"), max_drawdown=Decimal("-0.15"))

        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("marginal" in w.lower() for w in result.warnings)

    def test_validate_with_warnings_elevated_drawdown(self):
        """Test validation generates warnings for elevated drawdown (-20% to -25%)."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("1.5"), max_drawdown=Decimal("-0.22"))

        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("elevated" in w.lower() for w in result.warnings)

    def test_validate_no_metrics_raises_error(self):
        """Test validation raises error when no metrics provided."""
        validator = StrategyValidator()

        with pytest.raises(ValueError, match="At least one metric"):
            validator.validate()

    def test_validate_with_sharpe_only(self):
        """Test validation with only Sharpe ratio provided."""
        validator = StrategyValidator()
        result = validator.validate(sharpe_ratio=Decimal("1.5"))

        assert result.is_valid is True
        assert result.sharpe_ratio == Decimal("1.5")
        assert result.max_drawdown is None
        assert "not provided" in " ".join(result.warnings)

    def test_validate_with_drawdown_only(self):
        """Test validation with only max drawdown provided."""
        validator = StrategyValidator()
        result = validator.validate(max_drawdown=Decimal("-0.15"))

        assert result.is_valid is True
        assert result.sharpe_ratio is None
        assert result.max_drawdown == Decimal("-0.15")

    def test_validate_backtest_result_dict(self):
        """Test validation from backtest result dictionary."""
        validator = StrategyValidator()
        backtest_result = {
            "sharpe_ratio": 1.35,
            "max_drawdown": -0.18,
            "total_return": 0.25,
        }

        result = validator.validate_backtest_result(backtest_result)

        assert result.is_valid is True
        assert result.sharpe_ratio == Decimal("1.35")
        assert result.max_drawdown == Decimal("-0.18")

    def test_validate_backtest_result_with_none_values(self):
        """Test validation handles None values in backtest result."""
        validator = StrategyValidator()
        backtest_result = {
            "sharpe_ratio": None,
            "max_drawdown": -0.15,
        }

        result = validator.validate_backtest_result(backtest_result)

        assert result.is_valid is True
        assert result.sharpe_ratio is None
        assert result.max_drawdown == Decimal("-0.15")

    def test_validation_result_to_dict(self):
        """Test ValidationResult can be serialized to dict."""
        result = ValidationResult(
            is_valid=True,
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal("-0.15"),
            sharpe_passes=True,
            drawdown_passes=True,
            validation_level=ValidationLevel.PASS,
            warnings=["Test warning"],
            errors=[],
            metadata={"test": "value"},
        )

        result_dict = result.to_dict()

        assert result_dict["is_valid"] is True
        assert result_dict["sharpe_ratio"] == 1.5
        assert result_dict["max_drawdown"] == -0.15
        assert result_dict["validation_level"] == "pass"
        assert result_dict["warnings"] == ["Test warning"]
        assert result_dict["metadata"]["test"] == "value"


class TestConvenienceFunction:
    """Test suite for validate_strategy convenience function."""

    def test_convenience_function_pass(self):
        """Test convenience function returns valid result for passing metrics."""
        result = validate_strategy(sharpe_ratio=Decimal("1.8"), max_drawdown=Decimal("-0.12"))

        assert result.is_valid is True
        assert result.validation_level == ValidationLevel.PASS

    def test_convenience_function_fail(self):
        """Test convenience function returns invalid result for failing metrics."""
        result = validate_strategy(sharpe_ratio=Decimal("0.7"), max_drawdown=Decimal("-0.30"))

        assert result.is_valid is False
        assert result.validation_level == ValidationLevel.FAIL
