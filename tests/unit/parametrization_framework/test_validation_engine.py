"""
T5.1: Unit Tests for ValidationEngine

Tests cover:
- Capital viability validation
- Execution cost analysis
- Opportunity cost validation
- Learning capital gating
- Module gating
- Feasibility ratio validation
- Overall validation report
- Edge cases and error handling
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.core.models.investment_profile import (
    CapitalTier,
    InvestmentProfile,
    ObjectivoInversion,
    RiskTolerance,
)
from app.backtesting.models import BacktestConfig, BacktestResult
from app.services.backtesting_orchestration import (
    BacktestOrchestrator,
    ExtendedBacktestResult,
    FeasibilityMetrics,
)
from app.services.validation_orchestration import (
    ValidationEngine,
    ValidationReport,
    GateStatus,
)


@pytest.fixture
def validation_engine():
    """Create ValidationEngine instance."""
    return ValidationEngine()


@pytest.fixture
def sample_investment_profile_small():
    """Create sample InvestmentProfile for small capital."""
    return InvestmentProfile(
        profile_id="val_small_001",
        input_id="input_001",
        capital_initial=Decimal("50000"),
        capital_tier=CapitalTier.SMALL,
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        risk_profile=3,
        investment_horizon=12,
        enabled_modules=["momentum_modular", "mean_reversion_modular"],
        leverage_factor=Decimal("1.0"),
        max_position_size=Decimal("0.10"),
        max_sector_allocation=Decimal("0.20"),
        order_splitting_strategy="twap",
        commission_negotiation=False,
        risk_scaling_enabled=False,
    )


@pytest.fixture
def sample_investment_profile_large():
    """Create sample InvestmentProfile for large capital."""
    return InvestmentProfile(
        profile_id="val_large_001",
        input_id="input_002",
        capital_initial=Decimal("250000"),
        capital_tier=CapitalTier.LARGE,
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.ALTO,
        risk_profile=5,
        investment_horizon=24,
        enabled_modules=[
            "momentum_modular",
            "mean_reversion_modular",
            "pairs_trading_modular",
            "breakout_modular",
        ],
        leverage_factor=Decimal("1.5"),
        max_position_size=Decimal("0.05"),
        max_sector_allocation=Decimal("0.15"),
        order_splitting_strategy="vwap",
        commission_negotiation=True,
        risk_scaling_enabled=True,
    )


@pytest.fixture
def approved_extended_result():
    """Create ExtendedBacktestResult with APPROVED feasibility."""
    base_result = BacktestResult(
        strategy_name="test_approved",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        final_capital=Decimal("62500"),
        total_return=Decimal("25"),
        annualized_return=Decimal("25"),
    )

    metrics = FeasibilityMetrics(
        required_annual_return=Decimal("19.2"),
        required_monthly_return=Decimal("1.6"),
        feasibility_ratio=Decimal("1.30"),
        viability_status="APPROVED",
        risk_adjusted_return=None,
        confidence_level="HIGH",
    )

    return ExtendedBacktestResult(
        **base_result.model_dump(),
        feasibility_metrics=metrics,
    )


@pytest.fixture
def conditional_extended_result():
    """Create ExtendedBacktestResult with CONDITIONAL feasibility."""
    base_result = BacktestResult(
        strategy_name="test_conditional",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        final_capital=Decimal("56000"),
        total_return=Decimal("12"),
        annualized_return=Decimal("12"),
    )

    metrics = FeasibilityMetrics(
        required_annual_return=Decimal("19.2"),
        required_monthly_return=Decimal("1.6"),
        feasibility_ratio=Decimal("0.625"),
        viability_status="CONDITIONAL",
        risk_adjusted_return=None,
        confidence_level="MEDIUM",
    )

    return ExtendedBacktestResult(
        **base_result.model_dump(),
        feasibility_metrics=metrics,
    )


@pytest.fixture
def rejected_extended_result():
    """Create ExtendedBacktestResult with REJECTED feasibility."""
    base_result = BacktestResult(
        strategy_name="test_rejected",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        final_capital=Decimal("52000"),
        total_return=Decimal("4"),
        annualized_return=Decimal("4"),
    )

    metrics = FeasibilityMetrics(
        required_annual_return=Decimal("19.2"),
        required_monthly_return=Decimal("1.6"),
        feasibility_ratio=Decimal("0.21"),
        viability_status="REJECTED",
        risk_adjusted_return=None,
        confidence_level="LOW",
    )

    return ExtendedBacktestResult(
        **base_result.model_dump(),
        feasibility_metrics=metrics,
    )


class TestValidationEngineInitialization:
    """Test ValidationEngine initialization."""

    def test_initialization(self):
        """Test ValidationEngine can be initialized."""
        engine = ValidationEngine()
        assert engine is not None


class TestCapitalViabilityGate:
    """Test capital viability validation."""

    @pytest.mark.asyncio
    async def test_capital_above_minimum_small(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test capital meets minimum for SMALL tier."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        assert result.capital_viability.status == GateStatus.PASSED
        assert "meets minimum" in result.capital_viability.message

    @pytest.mark.asyncio
    async def test_capital_above_minimum_large(
        self, validation_engine, sample_investment_profile_large, approved_extended_result
    ):
        """Test capital meets minimum for LARGE tier."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_large
        )

        assert result.capital_viability.status == GateStatus.PASSED

    @pytest.mark.asyncio
    async def test_capital_below_minimum(
        self, validation_engine, approved_extended_result
    ):
        """Test capital below minimum is rejected."""
        profile = InvestmentProfile(
            profile_id="test",
            input_id="input",
            capital_initial=Decimal("500"),  # Below micro minimum of €1000
            capital_tier=CapitalTier.MICRO,
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            risk_profile=1,
            investment_horizon=6,
            enabled_modules=["momentum_modular"],
            leverage_factor=Decimal("1.0"),
            max_position_size=Decimal("0.10"),
            max_sector_allocation=Decimal("0.25"),
            order_splitting_strategy="market",
            commission_negotiation=False,
            risk_scaling_enabled=False,
        )

        result = await validation_engine.validate_backtest_result(
            approved_extended_result, profile
        )

        assert result.capital_viability.status == GateStatus.FAILED


class TestExecutionCostGate:
    """Test execution cost validation."""

    @pytest.mark.asyncio
    async def test_execution_costs_acceptable(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test execution costs within acceptable range."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        assert result.execution_costs.status in [GateStatus.PASSED, GateStatus.WARNING]

    @pytest.mark.asyncio
    async def test_execution_costs_with_high_slippage(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test execution costs with high slippage."""
        # Create result with high slippage config
        if approved_extended_result.config:
            approved_extended_result.config.slippage_percentage = Decimal("5.0")

        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        # Should pass but may warn about costs
        assert result.execution_costs.status in [GateStatus.PASSED, GateStatus.WARNING]


class TestOpportunityCostGate:
    """Test opportunity cost validation."""

    @pytest.mark.asyncio
    async def test_opportunity_cost_beats_passive(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test strategy beats passive benchmark."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        assert result.opportunity_cost.status in [GateStatus.PASSED, GateStatus.WARNING]

    @pytest.mark.asyncio
    async def test_opportunity_cost_underperforms_passive(
        self, validation_engine, sample_investment_profile_small
    ):
        """Test strategy underperforms passive benchmark."""
        base_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("51000"),
            total_return=Decimal("2"),  # Much lower than passive
            annualized_return=Decimal("2"),
        )

        metrics = FeasibilityMetrics(
            required_annual_return=Decimal("10"),
            required_monthly_return=Decimal("0.83"),
            feasibility_ratio=Decimal("0.2"),
            viability_status="REJECTED",
            risk_adjusted_return=None,
            confidence_level="LOW",
        )

        extended_result = ExtendedBacktestResult(
            **base_result.model_dump(),
            feasibility_metrics=metrics,
        )

        result = await validation_engine.validate_backtest_result(
            extended_result, sample_investment_profile_small
        )

        assert result.opportunity_cost.status == GateStatus.WARNING


class TestLearningCapitalGate:
    """Test learning capital validation."""

    @pytest.mark.asyncio
    async def test_learning_capital_affordable(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test ML infrastructure cost is affordable."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        assert result.learning_capital.status == GateStatus.PASSED


class TestModuleGatingGate:
    """Test module gating validation."""

    @pytest.mark.asyncio
    async def test_modules_suit_small_capital(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test standard modules suit small capital."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        assert result.module_gating.status == GateStatus.PASSED

    @pytest.mark.asyncio
    async def test_modules_suit_large_capital(
        self, validation_engine, sample_investment_profile_large, approved_extended_result
    ):
        """Test modules suit large capital."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_large
        )

        assert result.module_gating.status == GateStatus.PASSED

    @pytest.mark.asyncio
    async def test_expensive_modules_on_small_capital(
        self, validation_engine, approved_extended_result
    ):
        """Test expensive modules on small capital warn."""
        profile = InvestmentProfile(
            profile_id="test",
            input_id="input",
            capital_initial=Decimal("20000"),  # Below threshold
            capital_tier=CapitalTier.SMALL,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            risk_profile=3,
            investment_horizon=12,
            enabled_modules=[
                "momentum_modular",
                "deep_learning_engine",  # Expensive: requires €50k
            ],
            leverage_factor=Decimal("1.0"),
            max_position_size=Decimal("0.10"),
            max_sector_allocation=Decimal("0.20"),
            order_splitting_strategy="twap",
            commission_negotiation=False,
            risk_scaling_enabled=False,
        )

        result = await validation_engine.validate_backtest_result(
            approved_extended_result, profile
        )

        assert result.module_gating.status == GateStatus.WARNING


class TestFeasibilityRatioGate:
    """Test feasibility ratio validation."""

    @pytest.mark.asyncio
    async def test_feasibility_approved(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test APPROVED feasibility status."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        assert result.feasibility_ratio.status == GateStatus.PASSED
        assert "APPROVED" in result.feasibility_ratio.message

    @pytest.mark.asyncio
    async def test_feasibility_conditional(
        self, validation_engine, sample_investment_profile_small, conditional_extended_result
    ):
        """Test CONDITIONAL feasibility status."""
        result = await validation_engine.validate_backtest_result(
            conditional_extended_result, sample_investment_profile_small
        )

        assert result.feasibility_ratio.status == GateStatus.WARNING
        assert "CONDITIONAL" in result.feasibility_ratio.message

    @pytest.mark.asyncio
    async def test_feasibility_rejected(
        self, validation_engine, sample_investment_profile_small, rejected_extended_result
    ):
        """Test REJECTED feasibility status."""
        result = await validation_engine.validate_backtest_result(
            rejected_extended_result, sample_investment_profile_small
        )

        assert result.feasibility_ratio.status == GateStatus.FAILED
        assert "REJECTED" in result.feasibility_ratio.message


class TestOverallValidationReport:
    """Test overall validation report generation."""

    @pytest.mark.asyncio
    async def test_report_approved_status(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test report shows APPROVED overall status."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        assert result.overall_status == "APPROVED"
        assert len(result.critical_failures) == 0
        assert result.passed_gates > 0

    @pytest.mark.asyncio
    async def test_report_conditional_status(
        self, validation_engine, sample_investment_profile_small, conditional_extended_result
    ):
        """Test report shows CONDITIONAL overall status."""
        result = await validation_engine.validate_backtest_result(
            conditional_extended_result, sample_investment_profile_small
        )

        assert result.overall_status == "CONDITIONAL"
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_report_rejected_status(
        self, validation_engine, sample_investment_profile_small, rejected_extended_result
    ):
        """Test report shows REJECTED overall status."""
        result = await validation_engine.validate_backtest_result(
            rejected_extended_result, sample_investment_profile_small
        )

        assert result.overall_status == "REJECTED"
        assert len(result.critical_failures) > 0

    @pytest.mark.asyncio
    async def test_report_has_recommendations(
        self, validation_engine, sample_investment_profile_small, conditional_extended_result
    ):
        """Test report includes recommendations."""
        result = await validation_engine.validate_backtest_result(
            conditional_extended_result, sample_investment_profile_small
        )

        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_report_serialization(
        self, validation_engine, sample_investment_profile_small, approved_extended_result
    ):
        """Test report can be serialized to dict."""
        result = await validation_engine.validate_backtest_result(
            approved_extended_result, sample_investment_profile_small
        )

        result_dict = result.to_dict()
        assert result_dict["overall_status"] == "APPROVED"
        assert "passed_gates" in result_dict
        assert "total_gates" in result_dict


class TestValidationErrorHandling:
    """Test error handling in validation."""

    @pytest.mark.asyncio
    async def test_validation_with_none_feasibility_metrics(
        self, validation_engine, sample_investment_profile_small
    ):
        """Test validation handles missing feasibility metrics."""
        base_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("55000"),
            total_return=Decimal("10"),
            annualized_return=Decimal("10"),
        )

        extended_result = ExtendedBacktestResult(
            **base_result.model_dump(),
            feasibility_metrics=None,
        )

        result = await validation_engine.validate_backtest_result(
            extended_result, sample_investment_profile_small
        )

        assert result.feasibility_ratio.status == GateStatus.WARNING


class TestValidationGateResults:
    """Test individual gate result objects."""

    def test_gate_result_creation(self):
        """Test GateResult can be created."""
        from app.services.validation_orchestration import GateResult, GateStatus

        gate = GateResult(
            gate_name="test_gate",
            status=GateStatus.PASSED,
            message="Test message",
        )

        assert gate.gate_name == "test_gate"
        assert gate.status == GateStatus.PASSED


class TestMultipleValidationRuns:
    """Test multiple validation runs with different inputs."""

    @pytest.mark.asyncio
    async def test_validate_multiple_profiles_approved(
        self, validation_engine, approved_extended_result
    ):
        """Test validating multiple profiles with appropriate capital."""
        profiles = [
            InvestmentProfile(
                profile_id="test_small",
                input_id="input",
                capital_initial=Decimal("50000"),
                capital_tier=CapitalTier.SMALL,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                risk_profile=3,
                investment_horizon=12,
                enabled_modules=["momentum_modular"],
                leverage_factor=Decimal("1.0"),
                max_position_size=Decimal("0.10"),
                max_sector_allocation=Decimal("0.20"),
                order_splitting_strategy="twap",
                commission_negotiation=False,
                risk_scaling_enabled=False,
            ),
            InvestmentProfile(
                profile_id="test_large",
                input_id="input",
                capital_initial=Decimal("250000"),
                capital_tier=CapitalTier.LARGE,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.ALTO,
                risk_profile=5,
                investment_horizon=24,
                enabled_modules=["momentum_modular"],
                leverage_factor=Decimal("1.5"),
                max_position_size=Decimal("0.05"),
                max_sector_allocation=Decimal("0.15"),
                order_splitting_strategy="vwap",
                commission_negotiation=True,
                risk_scaling_enabled=True,
            ),
        ]

        for profile in profiles:
            result = await validation_engine.validate_backtest_result(
                approved_extended_result, profile
            )
            assert result.overall_status in ["APPROVED", "CONDITIONAL"]
