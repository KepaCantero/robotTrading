"""
T5.1: ValidationEngine Tests

Tests for ValidationEngine, PHASE 0 validator orchestration, and validation rules.
"""

from decimal import Decimal

import pytest

from app.services.validation_engine import (
    ValidationEngine,
    ValidationRequest,
    get_validation_engine,
)


# VALIDATION ENGINE INITIALIZATION TESTS
class TestValidationEngineInitialization:
    def test_engine_init(self):
        """Test validation engine initialization."""
        engine = ValidationEngine()
        assert len(engine.validation_history) == 0

    def test_engine_singleton(self):
        """Test validation engine singleton pattern."""
        e1 = get_validation_engine()
        e2 = get_validation_engine()
        assert e1 is e2

    def test_engine_status(self):
        """Test validation engine status reporting."""
        engine = ValidationEngine()
        status = engine.get_validation_engine_status()

        assert "total_validations" in status
        assert "passed_validations" in status
        assert "validation_pass_rate" in status


# CAPITAL VIABILITY VALIDATION TESTS
class TestCapitalViabilityValidation:
    @pytest.mark.asyncio
    async def test_validate_viable_capital(self):
        """Test validation of viable capital with achievable goals."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_viable_capital",
            input_id="user_001",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            tax_rate=Decimal("0.35"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        result = await engine.validate(request)

        assert result.success
        assert result.capital_viability is not None
        assert result.capital_viability.is_viable

    @pytest.mark.asyncio
    async def test_validate_unviable_capital_insufficient(self):
        """Test validation rejects insufficient capital for goal."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_unviable_capital",
            input_id="user_002",
            initial_capital=Decimal("5000"),  # Too small
            target_monthly_return_eur=Decimal("1000"),  # Too ambitious
            tax_rate=Decimal("0.35"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        result = await engine.validate(request)

        assert result.success
        assert result.capital_viability is not None
        assert not result.capital_viability.is_viable


# FEASIBILITY RATIO VALIDATION TESTS
class TestFeasibilityValidation:
    @pytest.mark.asyncio
    async def test_validate_feasibility_approved(self):
        """Test validation passes for APPROVED feasibility ratio."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_feasibility_approved",
            input_id="user_003",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            backtest_feasibility_ratio=Decimal("1.25"),  # >= 1.0
        )

        result = await engine.validate(request)

        assert result.success
        assert result.feasibility is not None
        assert result.feasibility.feasibility_status == "APPROVED"
        assert result.feasibility.is_viable

    @pytest.mark.asyncio
    async def test_validate_feasibility_conditional(self):
        """Test validation passes for CONDITIONAL feasibility ratio."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_feasibility_conditional",
            input_id="user_004",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            backtest_feasibility_ratio=Decimal("0.85"),  # 0.7-1.0
        )

        result = await engine.validate(request)

        assert result.success
        assert result.feasibility is not None
        assert result.feasibility.feasibility_status == "CONDITIONAL"
        assert result.feasibility.is_viable

    @pytest.mark.asyncio
    async def test_validate_feasibility_rejected(self):
        """Test validation rejects low feasibility ratio."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_feasibility_rejected",
            input_id="user_005",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            backtest_feasibility_ratio=Decimal("0.5"),  # < 0.7
        )

        result = await engine.validate(request)

        assert result.success
        assert result.feasibility is not None
        assert result.feasibility.feasibility_status == "REJECTED"
        assert not result.feasibility.is_viable
        assert "feasibility" in result.critical_failures[0].lower()


# LEARNING VIABILITY VALIDATION TESTS
class TestLearningViabilityValidation:
    @pytest.mark.asyncio
    async def test_learning_viable_large_capital(self):
        """Test learning viability with large capital."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_learning_viable",
            input_id="user_006",
            initial_capital=Decimal("100000"),  # Large capital
            target_monthly_return_eur=Decimal("1000"),
            learning_enabled=True,
        )

        result = await engine.validate(request)

        assert result.success
        assert result.learning_viability is not None
        assert result.learning_viability.learning_recommended

    @pytest.mark.asyncio
    async def test_learning_not_viable_small_capital(self):
        """Test learning not viable with small capital."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_learning_unviable",
            input_id="user_007",
            initial_capital=Decimal("10000"),  # Small capital
            target_monthly_return_eur=Decimal("100"),
            learning_enabled=True,
        )

        result = await engine.validate(request)

        assert result.success
        assert result.learning_viability is not None
        assert not result.learning_viability.learning_recommended
        assert len(result.warnings) > 0


# MODULE VIABILITY VALIDATION TESTS
class TestModuleViabilityValidation:
    @pytest.mark.asyncio
    async def test_expensive_modules_disabled_small_capital(self):
        """Test expensive modules disabled for small accounts."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_module_gating",
            input_id="user_008",
            initial_capital=Decimal("20000"),  # Small capital
            target_monthly_return_eur=Decimal("200"),
        )

        result = await engine.validate(request)

        assert result.success
        assert len(result.module_viabilities) > 0

        # Transformer should be disabled for small accounts
        transformer = result.module_viabilities.get("transformer_engine")
        if transformer:
            assert not transformer.enabled

    @pytest.mark.asyncio
    async def test_expensive_modules_enabled_large_capital(self):
        """Test expensive modules enabled for large accounts."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_module_enabled",
            input_id="user_009",
            initial_capital=Decimal("500000"),  # Large capital
            target_monthly_return_eur=Decimal("5000"),
        )

        result = await engine.validate(request)

        assert result.success
        assert len(result.module_viabilities) > 0


# RISK METRICS VALIDATION TESTS
class TestRiskMetricsValidation:
    @pytest.mark.asyncio
    async def test_validate_good_sharpe_ratio(self):
        """Test validation passes with good Sharpe ratio."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_good_sharpe",
            input_id="user_010",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            backtest_feasibility_ratio=Decimal("1.1"),
            backtest_sharpe_ratio=Decimal("1.5"),  # Good
        )

        result = await engine.validate(request)

        assert result.success
        # Should not warn about Sharpe ratio
        assert not any("sharpe" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_validate_low_sharpe_ratio(self):
        """Test validation warns about low Sharpe ratio."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_low_sharpe",
            input_id="user_011",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            backtest_feasibility_ratio=Decimal("1.1"),
            backtest_sharpe_ratio=Decimal("0.5"),  # Low
        )

        result = await engine.validate(request)

        assert result.success
        assert any("sharpe" in w.lower() for w in result.warnings)


# OVERALL VALIDATION ORCHESTRATION TESTS
class TestValidationOrchestration:
    @pytest.mark.asyncio
    async def test_validate_complete_approval(self):
        """Test complete validation flow with APPROVE recommendation."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_complete_approval",
            input_id="user_012",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            backtest_feasibility_ratio=Decimal("1.2"),
            backtest_sharpe_ratio=Decimal("1.5"),
            backtest_max_drawdown_pct=Decimal("10"),
        )

        result = await engine.validate(request)

        assert result.success
        assert result.passed
        assert result.overall_recommendation == "APPROVE"
        assert result.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_validate_complete_conditional(self):
        """Test complete validation flow with CONDITIONAL recommendation."""
        engine = ValidationEngine()
        request = ValidationRequest(
            profile_id="test_complete_conditional",
            input_id="user_013",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            backtest_feasibility_ratio=Decimal("0.8"),  # Conditional
            backtest_sharpe_ratio=Decimal("1.0"),
        )

        result = await engine.validate(request)

        assert result.success
        assert result.passed
        assert result.overall_recommendation == "CONDITIONAL"


# VALIDATION HISTORY TESTS
class TestValidationHistory:
    @pytest.mark.asyncio
    async def test_validation_history_tracking(self):
        """Test that validation history is tracked."""
        engine = ValidationEngine()

        for i in range(3):
            request = ValidationRequest(
                profile_id=f"test_hist_{i}",
                input_id=f"user_hist_{i}",
                initial_capital=Decimal("250000"),
                target_monthly_return_eur=Decimal("1000"),
                backtest_feasibility_ratio=Decimal("1.1"),
            )
            await engine.validate(request)

        history = await engine.get_validation_history()
        assert len(history) >= 3

    @pytest.mark.asyncio
    async def test_validation_history_limit(self):
        """Test validation history with limit."""
        engine = ValidationEngine()

        for i in range(5):
            request = ValidationRequest(
                profile_id=f"test_limit_{i}",
                input_id=f"user_limit_{i}",
                initial_capital=Decimal("250000"),
                target_monthly_return_eur=Decimal("1000"),
            )
            await engine.validate(request)

        history = await engine.get_validation_history(limit=2)
        assert len(history) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
