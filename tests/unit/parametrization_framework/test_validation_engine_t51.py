"""
BATCH E - T5.1: Unit Tests for ValidationEngine with Validation Gates

Tests:
- Feasibility ratio validation (APPROVED, CONDITIONAL, REJECTED)
- Capital viability validation
- Learning viability validation
- Module viability (expensive module gating)
- Risk metrics validation
- Overall status determination
"""

import pytest
from decimal import Decimal
from app.services.validation_engine.validation_engine import ValidationEngine
from app.services.validation_engine.models import (
    ValidationRequest,
    CapitalViabilityAnalysis,
    FeasibilityAnalysis,
)


@pytest.fixture
def validation_engine():
    """Create ValidationEngine instance for tests."""
    return ValidationEngine()


class TestFeasibilityRatioValidation:
    """Test feasibility ratio validation."""

    @pytest.mark.asyncio
    async def test_feasibility_ratio_approved(self, validation_engine):
        """Test feasibility ratio >= 1.0 results in APPROVED."""
        request = ValidationRequest(
            profile_id="PROF-20251225100000",
            input_id="test_001",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("800"),
            backtest_feasibility_ratio=Decimal("1.35"),  # 35% above target
            backtest_sharpe_ratio=Decimal("1.5"),
            backtest_max_drawdown_pct=Decimal("15"),
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.feasibility is not None
        assert result.feasibility.feasibility_status == "APPROVED"
        assert result.feasibility.is_viable is True

    @pytest.mark.asyncio
    async def test_feasibility_ratio_conditional(self, validation_engine):
        """Test feasibility ratio 0.7-1.0 results in CONDITIONAL."""
        request = ValidationRequest(
            profile_id="PROF-20251225100001",
            input_id="test_002",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("300"),
            backtest_feasibility_ratio=Decimal("0.85"),  # 15% below target
            backtest_sharpe_ratio=Decimal("1.0"),
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.feasibility is not None
        assert result.feasibility.feasibility_status == "CONDITIONAL"
        assert result.feasibility.is_viable is True

    @pytest.mark.asyncio
    async def test_feasibility_ratio_rejected(self, validation_engine):
        """Test feasibility ratio < 0.7 results in REJECTED."""
        request = ValidationRequest(
            profile_id="PROF-20251225100002",
            input_id="test_003",
            initial_capital=Decimal("50000"),
            target_monthly_return_eur=Decimal("500"),
            backtest_feasibility_ratio=Decimal("0.55"),  # 45% below target
            backtest_sharpe_ratio=Decimal("0.5"),
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.feasibility is not None
        assert result.feasibility.feasibility_status == "REJECTED"
        assert result.feasibility.is_viable is False
        assert len(result.critical_failures) > 0

    @pytest.mark.asyncio
    async def test_feasibility_ratio_exactly_at_threshold(self, validation_engine):
        """Test feasibility ratio exactly at 1.0 threshold."""
        request = ValidationRequest(
            profile_id="PROF-20251225100003",
            input_id="test_004",
            initial_capital=Decimal("200000"),
            target_monthly_return_eur=Decimal("500"),
            backtest_feasibility_ratio=Decimal("1.00"),  # Exactly at threshold
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.feasibility.feasibility_status == "APPROVED"

    @pytest.mark.asyncio
    async def test_feasibility_ratio_at_conditional_lower_bound(self, validation_engine):
        """Test feasibility ratio exactly at 0.7 threshold."""
        request = ValidationRequest(
            profile_id="PROF-20251225100004",
            input_id="test_005",
            initial_capital=Decimal("150000"),
            target_monthly_return_eur=Decimal("400"),
            backtest_feasibility_ratio=Decimal("0.70"),  # At conditional threshold
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.feasibility.feasibility_status == "CONDITIONAL"


class TestRiskMetricsValidation:
    """Test risk metrics validation."""

    @pytest.mark.asyncio
    async def test_low_sharpe_ratio_warning(self, validation_engine):
        """Test low Sharpe ratio generates warning."""
        request = ValidationRequest(
            profile_id="PROF-20251225100005",
            input_id="test_006",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("250"),
            backtest_feasibility_ratio=Decimal("1.1"),
            backtest_sharpe_ratio=Decimal("0.5"),  # Low Sharpe
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert len(result.warnings) > 0
        assert any("Sharpe" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_high_max_drawdown_warning(self, validation_engine):
        """Test high max drawdown generates warning."""
        request = ValidationRequest(
            profile_id="PROF-20251225100006",
            input_id="test_007",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("250"),
            backtest_feasibility_ratio=Decimal("1.1"),
            backtest_max_drawdown_pct=Decimal("30"),  # High drawdown
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert len(result.warnings) > 0
        assert any("drawdown" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_acceptable_risk_metrics(self, validation_engine):
        """Test acceptable risk metrics don't generate warnings."""
        request = ValidationRequest(
            profile_id="PROF-20251225100007",
            input_id="test_008",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("250"),
            backtest_feasibility_ratio=Decimal("1.1"),
            backtest_sharpe_ratio=Decimal("1.5"),  # Good Sharpe
            backtest_max_drawdown_pct=Decimal("10"),  # Low drawdown
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        # May have no risk warnings
        risk_warnings = [w for w in result.warnings if any(x in w.lower() for x in ["sharpe", "drawdown"])]
        assert len(risk_warnings) == 0


class TestOverallValidationStatus:
    """Test overall validation status determination."""

    @pytest.mark.asyncio
    async def test_approved_recommendation_high_confidence(self, validation_engine):
        """Test APPROVED recommendation with high confidence."""
        request = ValidationRequest(
            profile_id="PROF-20251225100008",
            input_id="test_009",
            initial_capital=Decimal("300000"),
            target_monthly_return_eur=Decimal("800"),
            backtest_feasibility_ratio=Decimal("1.5"),  # Strong approval
            backtest_sharpe_ratio=Decimal("2.0"),
            backtest_max_drawdown_pct=Decimal("8"),
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.passed is True
        assert result.overall_recommendation == "APPROVE"
        assert result.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_conditional_recommendation_medium_confidence(self, validation_engine):
        """Test CONDITIONAL recommendation with medium confidence."""
        request = ValidationRequest(
            profile_id="PROF-20251225100009",
            input_id="test_010",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("300"),
            backtest_feasibility_ratio=Decimal("0.85"),
            backtest_sharpe_ratio=Decimal("0.8"),
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.passed is True
        assert result.overall_recommendation == "CONDITIONAL"
        assert result.confidence_level == "medium"

    @pytest.mark.asyncio
    async def test_rejected_recommendation(self, validation_engine):
        """Test REJECTED recommendation."""
        request = ValidationRequest(
            profile_id="PROF-20251225100010",
            input_id="test_011",
            initial_capital=Decimal("50000"),
            target_monthly_return_eur=Decimal("1000"),  # Unrealistic target
            backtest_feasibility_ratio=Decimal("0.4"),  # Far below target
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.passed is False
        assert result.overall_recommendation == "REJECT"

    @pytest.mark.asyncio
    async def test_multiple_warnings_lower_confidence(self, validation_engine):
        """Test multiple warnings lower confidence level."""
        request = ValidationRequest(
            profile_id="PROF-20251225100011",
            input_id="test_012",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("250"),
            backtest_feasibility_ratio=Decimal("1.1"),  # Would normally APPROVE
            backtest_sharpe_ratio=Decimal("0.5"),  # Warning
            backtest_max_drawdown_pct=Decimal("25"),  # Warning
            learning_enabled=False,  # Additional consideration
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert len(result.warnings) >= 2
        # Multiple warnings should lower confidence
        assert result.confidence_level == "low"


class TestLearningViability:
    """Test learning viability validation."""

    @pytest.mark.asyncio
    async def test_learning_enabled_sufficient_capital(self, validation_engine):
        """Test learning viability with sufficient capital."""
        request = ValidationRequest(
            profile_id="PROF-20251225100012",
            input_id="test_013",
            initial_capital=Decimal("500000"),  # Large capital
            target_monthly_return_eur=Decimal("1000"),
            learning_enabled=True,
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.learning_viability is not None

    @pytest.mark.asyncio
    async def test_learning_disabled_small_capital(self, validation_engine):
        """Test learning viability with small capital."""
        request = ValidationRequest(
            profile_id="PROF-20251225100013",
            input_id="test_014",
            initial_capital=Decimal("10000"),  # Small capital
            target_monthly_return_eur=Decimal("50"),
            learning_enabled=False,
        )

        result = await validation_engine.validate(request)

        assert result.success is True
        assert result.learning_viability is not None


class TestValidationHistory:
    """Test validation history tracking."""

    @pytest.mark.asyncio
    async def test_validation_history_tracked(self, validation_engine):
        """Test validation results are tracked in history."""
        request = ValidationRequest(
            profile_id="PROF-20251225100014",
            input_id="test_015",
            initial_capital=Decimal("100000"),
            target_monthly_return_eur=Decimal("250"),
            backtest_feasibility_ratio=Decimal("1.0"),
        )

        await validation_engine.validate(request)
        history = await validation_engine.get_validation_history()

        assert len(history) > 0
        assert history[-1].profile_id == "PROF-20251225100014"

    def test_validation_engine_status(self, validation_engine):
        """Test validation engine status reporting."""
        status = validation_engine.get_validation_engine_status()

        assert "total_validations" in status
        assert "passed_validations" in status
        assert "validation_pass_rate" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
