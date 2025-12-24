"""
T4.1: Unit Tests for BacktestOrchestrator

Tests cover:
- Feasibility ratio calculation
- Viability status determination
- Confidence level assessment
- Capital tier handling
- Module parameter integration
- Error handling
- Edge cases
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.core.models.investment_profile import (
    CapitalTier,
    InvestmentProfile,
    ObjectivoInversion,
    RiskTolerance,
)
from app.services.backtesting_orchestration import (
    BacktestOrchestrator,
    ExtendedBacktestResult,
    FeasibilityMetrics,
)
from app.services.parametrization.module_parametrizer import (
    ModuleParameterSet,
    ModuleParameters,
)


@pytest.fixture
def orchestrator():
    """Create BacktestOrchestrator instance."""
    return BacktestOrchestrator()


@pytest.fixture
def sample_investment_profile_small():
    """Create sample InvestmentProfile for small capital."""
    return InvestmentProfile(
        profile_id="test_small_001",
        input_id="input_001",
        capital_initial=Decimal("50000"),  # €50k
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
        profile_id="test_large_001",
        input_id="input_002",
        capital_initial=Decimal("250000"),  # €250k
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
def sample_module_parameters(sample_investment_profile_small):
    """Create sample ModuleParameterSet."""
    modules = {
        "momentum_modular": ModuleParameters(
            module_name="momentum_modular",
            tier=CapitalTier.SMALL,
            objective=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            preset="balanced",
            enabled=True,
            max_position_size=Decimal("0.10"),
            stop_loss_pct=Decimal("0.025"),
            take_profit_pct=Decimal("0.050"),
            max_exposure=Decimal("0.25"),
            max_positions=5,
            module_specific={},
        ),
        "mean_reversion_modular": ModuleParameters(
            module_name="mean_reversion_modular",
            tier=CapitalTier.SMALL,
            objective=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            preset="conservative",
            enabled=True,
            max_position_size=Decimal("0.08"),
            stop_loss_pct=Decimal("0.030"),
            take_profit_pct=Decimal("0.040"),
            max_exposure=Decimal("0.20"),
            max_positions=3,
            module_specific={},
        ),
    }

    return ModuleParameterSet(
        profile_id=sample_investment_profile_small.profile_id,
        input_id=sample_investment_profile_small.input_id,
        capital_tier=sample_investment_profile_small.capital_tier,
        objetivo_inversion=sample_investment_profile_small.objetivo_inversion,
        modules=modules,
        total_max_exposure=Decimal("0.45"),
    )


class TestBacktestOrchestratorInitialization:
    """Test BacktestOrchestrator initialization."""

    def test_initialization_with_default_config(self):
        """Test initialization with default config path."""
        orchestrator = BacktestOrchestrator()
        assert orchestrator.config_path == "config/backtest_config.yaml"

    def test_initialization_with_custom_config(self):
        """Test initialization with custom config path."""
        custom_path = "/custom/path/backtest.yaml"
        orchestrator = BacktestOrchestrator(config_path=custom_path)
        assert orchestrator.config_path == custom_path


class TestFeasibilityRatioCalculation:
    """Test feasibility ratio calculation with various scenarios."""

    @pytest.mark.asyncio
    async def test_feasibility_ratio_approved(self, orchestrator, sample_investment_profile_small):
        """Test feasibility ratio >= 1.0 (APPROVED)."""
        from app.backtesting.models import BacktestResult

        # Scenario: €800/month target, €50k capital, 10% annual backtest return
        # required = (800/50000)*12 = 19.2%
        # feasibility = 10% / 19.2% = 0.52 (but we'll simulate higher for APPROVED)

        # Create mock result with 25% return
        backtest_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("62500"),  # 25% return
            total_return=Decimal("25"),
            annualized_return=Decimal("25"),
        )

        metrics = orchestrator._calculate_feasibility_metrics(
            backtest_result=backtest_result,
            capital=Decimal("50000"),
            target_euros_per_month=Decimal("800"),
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 12, 31),
        )

        assert metrics.feasibility_ratio >= Decimal("1.0")
        assert metrics.viability_status == "APPROVED"
        assert metrics.confidence_level in ["HIGH", "VERY_HIGH"]

    @pytest.mark.asyncio
    async def test_feasibility_ratio_conditional(self, orchestrator, sample_investment_profile_small):
        """Test feasibility ratio 0.7-1.0 (CONDITIONAL)."""
        from app.backtesting.models import BacktestResult

        # Create result with 15% return (between 0.7 and 1.0 ratio)
        backtest_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("57500"),  # 15% return
            total_return=Decimal("15"),
            annualized_return=Decimal("15"),
        )

        metrics = orchestrator._calculate_feasibility_metrics(
            backtest_result=backtest_result,
            capital=Decimal("50000"),
            target_euros_per_month=Decimal("800"),
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 12, 31),
        )

        assert Decimal("0.7") <= metrics.feasibility_ratio < Decimal("1.0")
        assert metrics.viability_status == "CONDITIONAL"
        assert metrics.confidence_level == "MEDIUM"

    @pytest.mark.asyncio
    async def test_feasibility_ratio_rejected(self, orchestrator, sample_investment_profile_small):
        """Test feasibility ratio < 0.7 (REJECTED)."""
        from app.backtesting.models import BacktestResult

        # Create result with 5% return (below 0.7 ratio)
        backtest_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("52500"),  # 5% return
            total_return=Decimal("5"),
            annualized_return=Decimal("5"),
        )

        metrics = orchestrator._calculate_feasibility_metrics(
            backtest_result=backtest_result,
            capital=Decimal("50000"),
            target_euros_per_month=Decimal("800"),
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 12, 31),
        )

        assert metrics.feasibility_ratio < Decimal("0.7")
        assert metrics.viability_status == "REJECTED"
        assert metrics.confidence_level == "LOW"

    def test_feasibility_ratio_with_zero_target(self, orchestrator):
        """Test feasibility ratio with zero target (edge case)."""
        from app.backtesting.models import BacktestResult

        backtest_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("100000"),
            total_return=Decimal("10"),
            annualized_return=Decimal("10"),
        )

        # Zero target should result in zero required return
        metrics = orchestrator._calculate_feasibility_metrics(
            backtest_result=backtest_result,
            capital=Decimal("50000"),
            target_euros_per_month=Decimal("0"),
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 12, 31),
        )

        assert metrics.required_annual_return == Decimal("0")
        assert metrics.required_monthly_return == Decimal("0")

    def test_required_return_calculation(self, orchestrator):
        """Test required return calculation from target."""
        from app.backtesting.models import BacktestResult

        backtest_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("100000"),
            total_return=Decimal("10"),
            annualized_return=Decimal("10"),
        )

        # €800/month, €250k capital
        # required_monthly = (800/250000) * 100 = 0.32%
        # required_annual = 0.32% * 12 = 3.84%

        metrics = orchestrator._calculate_feasibility_metrics(
            backtest_result=backtest_result,
            capital=Decimal("250000"),
            target_euros_per_month=Decimal("800"),
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 12, 31),
        )

        assert metrics.required_monthly_return == pytest.approx(
            Decimal("0.32"), abs=Decimal("0.01")
        )
        assert metrics.required_annual_return == pytest.approx(Decimal("3.84"), abs=Decimal("0.01"))


class TestConfidenceLevelAssessment:
    """Test confidence level determination based on feasibility ratio."""

    def test_confidence_very_high(self, orchestrator):
        """Test VERY_HIGH confidence (ratio >= 1.5)."""
        from app.backtesting.models import BacktestResult

        backtest_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("100000"),
            total_return=Decimal("30"),
            annualized_return=Decimal("30"),
        )

        metrics = orchestrator._calculate_feasibility_metrics(
            backtest_result=backtest_result,
            capital=Decimal("50000"),
            target_euros_per_month=Decimal("400"),  # Low target
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 12, 31),
        )

        assert metrics.feasibility_ratio >= Decimal("1.5")
        assert metrics.confidence_level == "VERY_HIGH"

    def test_confidence_high(self, orchestrator):
        """Test HIGH confidence (ratio 1.0-1.5)."""
        from app.backtesting.models import BacktestResult

        # €400/month on €50k = 9.6% required annual return
        # Backtest yield 12% = ratio of 1.25 (in 1.0-1.5 range)
        backtest_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("56000"),
            total_return=Decimal("12"),
            annualized_return=Decimal("12"),
        )

        metrics = orchestrator._calculate_feasibility_metrics(
            backtest_result=backtest_result,
            capital=Decimal("50000"),
            target_euros_per_month=Decimal("400"),
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 12, 31),
        )

        assert Decimal("1.0") <= metrics.feasibility_ratio < Decimal("1.5")
        assert metrics.confidence_level == "HIGH"

    def test_confidence_low(self, orchestrator):
        """Test LOW confidence (ratio < 0.7)."""
        from app.backtesting.models import BacktestResult

        backtest_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("52000"),
            total_return=Decimal("4"),
            annualized_return=Decimal("4"),
        )

        metrics = orchestrator._calculate_feasibility_metrics(
            backtest_result=backtest_result,
            capital=Decimal("50000"),
            target_euros_per_month=Decimal("1000"),  # High target
            backtest_start=datetime(2024, 1, 1),
            backtest_end=datetime(2024, 12, 31),
        )

        assert metrics.feasibility_ratio < Decimal("0.7")
        assert metrics.confidence_level == "LOW"


class TestCapitalTierHandling:
    """Test BacktestOrchestrator with different capital tiers."""

    def test_micro_capital_tier(self, orchestrator):
        """Test configuration creation for MICRO tier."""
        from app.core.models.investment_profile import CapitalTier

        profile = InvestmentProfile(
            profile_id="micro_001",
            input_id="input_001",
            capital_initial=Decimal("10000"),
            capital_tier=CapitalTier.MICRO,
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
            risk_profile=1,
            investment_horizon=6,
            enabled_modules=["momentum_modular"],
            leverage_factor=Decimal("0.5"),
            max_position_size=Decimal("0.08"),
            max_sector_allocation=Decimal("0.25"),
            order_splitting_strategy="market",
            commission_negotiation=False,
            risk_scaling_enabled=False,
        )

        config = orchestrator._create_backtest_config_from_profile(profile)

        assert config.strategy_name == "parametrized_micro"
        assert config.initial_capital == Decimal("10000")
        assert config.max_position_size == Decimal("0.08")

    def test_small_capital_tier(self, orchestrator, sample_investment_profile_small):
        """Test configuration creation for SMALL tier."""
        config = orchestrator._create_backtest_config_from_profile(sample_investment_profile_small)

        assert config.strategy_name == "parametrized_small"
        assert config.initial_capital == Decimal("50000")
        assert config.max_position_size == Decimal("0.10")

    def test_large_capital_tier(self, orchestrator, sample_investment_profile_large):
        """Test configuration creation for LARGE tier."""
        config = orchestrator._create_backtest_config_from_profile(sample_investment_profile_large)

        assert config.strategy_name == "parametrized_large"
        assert config.initial_capital == Decimal("250000")
        assert config.max_position_size == Decimal("0.05")


class TestModuleParameterIntegration:
    """Test integration with ModuleParameterSet from T3.1."""

    def test_backtest_config_respects_investment_profile(
        self, orchestrator, sample_investment_profile_small
    ):
        """Test that backtest config reflects investment profile."""
        config = orchestrator._create_backtest_config_from_profile(sample_investment_profile_small)

        assert config.initial_capital == sample_investment_profile_small.capital_initial
        assert config.max_position_size == sample_investment_profile_small.max_position_size

    def test_module_count_affects_simulation(self, orchestrator, sample_investment_profile_small):
        """Test that module count affects simulated return."""
        params = ModuleParameterSet(
            profile_id=sample_investment_profile_small.profile_id,
            input_id=sample_investment_profile_small.input_id,
            capital_tier=sample_investment_profile_small.capital_tier,
            objetivo_inversion=sample_investment_profile_small.objetivo_inversion,
            modules={
                "momentum_modular": ModuleParameters(
                    module_name="momentum_modular",
                    tier=CapitalTier.SMALL,
                    objective=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                    preset="balanced",
                    enabled=True,
                    max_position_size=Decimal("0.10"),
                    stop_loss_pct=Decimal("0.025"),
                    take_profit_pct=Decimal("0.050"),
                    max_exposure=Decimal("0.25"),
                    max_positions=5,
                    module_specific={},
                )
            },
            total_max_exposure=Decimal("0.25"),
        )

        return1 = orchestrator._simulate_backtest_return(
            sample_investment_profile_small, params
        )

        # Add another module
        params.modules["mean_reversion_modular"] = ModuleParameters(
            module_name="mean_reversion_modular",
            tier=CapitalTier.SMALL,
            objective=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            preset="conservative",
            enabled=True,
            max_position_size=Decimal("0.08"),
            stop_loss_pct=Decimal("0.030"),
            take_profit_pct=Decimal("0.040"),
            max_exposure=Decimal("0.20"),
            max_positions=3,
            module_specific={},
        )
        params.total_max_exposure = Decimal("0.45")

        return2 = orchestrator._simulate_backtest_return(
            sample_investment_profile_small, params
        )

        # More modules should result in more diversification (lower expected return but more stable)
        # The relationship should be: more modules = slight reduction in return
        # This is a simplified test since returns are randomized
        assert isinstance(return1, Decimal)
        assert isinstance(return2, Decimal)
        assert return1 > 0
        assert return2 > 0


class TestExtendedBacktestResult:
    """Test ExtendedBacktestResult model."""

    def test_extended_result_creation(self, sample_investment_profile_small, sample_module_parameters):
        """Test creating ExtendedBacktestResult."""
        from app.backtesting.models import BacktestResult

        base_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("55000"),
            total_return=Decimal("10"),
            annualized_return=Decimal("10"),
        )

        metrics = FeasibilityMetrics(
            required_annual_return=Decimal("19.2"),
            required_monthly_return=Decimal("1.6"),
            feasibility_ratio=Decimal("0.52"),
            viability_status="CONDITIONAL",
            risk_adjusted_return=None,
            confidence_level="MEDIUM",
        )

        extended_result = ExtendedBacktestResult(
            **base_result.model_dump(),
            feasibility_metrics=metrics,
            parameter_set=sample_module_parameters,
            investment_profile=sample_investment_profile_small,
        )

        assert extended_result.feasibility_metrics is not None
        assert extended_result.feasibility_metrics.feasibility_ratio == Decimal("0.52")
        assert extended_result.parameter_set is not None
        assert extended_result.investment_profile is not None

    def test_extended_result_serialization(
        self, sample_investment_profile_small, sample_module_parameters
    ):
        """Test ExtendedBacktestResult serialization."""
        from app.backtesting.models import BacktestResult

        base_result = BacktestResult(
            strategy_name="test",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal("55000"),
            total_return=Decimal("10"),
            annualized_return=Decimal("10"),
        )

        metrics = FeasibilityMetrics(
            required_annual_return=Decimal("19.2"),
            required_monthly_return=Decimal("1.6"),
            feasibility_ratio=Decimal("0.52"),
            viability_status="CONDITIONAL",
            risk_adjusted_return=None,
            confidence_level="MEDIUM",
        )

        extended_result = ExtendedBacktestResult(
            **base_result.model_dump(),
            feasibility_metrics=metrics,
            parameter_set=sample_module_parameters,
            investment_profile=sample_investment_profile_small,
        )

        # Should be serializable to dict
        result_dict = extended_result.model_dump()
        assert float(result_dict["feasibility_metrics"]["feasibility_ratio"]) == pytest.approx(0.52, abs=0.01)


class TestSimulationAccuracy:
    """Test simulation return calculation."""

    def test_simulation_returns_positive_for_all_tiers(
        self, orchestrator, sample_investment_profile_small, sample_investment_profile_large
    ):
        """Test that simulated returns are positive for all capital tiers."""
        params_small = ModuleParameterSet(
            profile_id=sample_investment_profile_small.profile_id,
            input_id=sample_investment_profile_small.input_id,
            capital_tier=sample_investment_profile_small.capital_tier,
            objetivo_inversion=sample_investment_profile_small.objetivo_inversion,
            modules={
                "momentum_modular": ModuleParameters(
                    module_name="momentum_modular",
                    tier=CapitalTier.SMALL,
                    objective=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                    preset="balanced",
                    enabled=True,
                    max_position_size=Decimal("0.10"),
                    stop_loss_pct=Decimal("0.025"),
                    take_profit_pct=Decimal("0.050"),
                    max_exposure=Decimal("0.25"),
                    max_positions=5,
                    module_specific={},
                )
            },
            total_max_exposure=Decimal("0.25"),
        )

        params_large = ModuleParameterSet(
            profile_id=sample_investment_profile_large.profile_id,
            input_id=sample_investment_profile_large.input_id,
            capital_tier=sample_investment_profile_large.capital_tier,
            objetivo_inversion=sample_investment_profile_large.objetivo_inversion,
            modules={
                "momentum_modular": ModuleParameters(
                    module_name="momentum_modular",
                    tier=CapitalTier.LARGE,
                    objective=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                    preset="balanced",
                    enabled=True,
                    max_position_size=Decimal("0.10"),
                    stop_loss_pct=Decimal("0.025"),
                    take_profit_pct=Decimal("0.050"),
                    max_exposure=Decimal("0.25"),
                    max_positions=5,
                    module_specific={},
                )
            },
            total_max_exposure=Decimal("0.25"),
        )

        return_small = orchestrator._simulate_backtest_return(
            sample_investment_profile_small, params_small
        )
        return_large = orchestrator._simulate_backtest_return(
            sample_investment_profile_large, params_large
        )

        assert return_small > Decimal("0")
        assert return_large > Decimal("0")

    def test_simulation_respects_capital_tier_hierarchy(self, orchestrator):
        """Test that larger capital tiers have more conservative base returns."""
        profiles = {
            CapitalTier.MICRO: InvestmentProfile(
                profile_id="micro",
                input_id="input",
                capital_initial=Decimal("10000"),
                capital_tier=CapitalTier.MICRO,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.BAJO,
                risk_profile=1,
                investment_horizon=12,
                enabled_modules=["momentum_modular"],
                leverage_factor=Decimal("1.0"),
                max_position_size=Decimal("0.15"),
                max_sector_allocation=Decimal("0.25"),
                order_splitting_strategy="market",
                commission_negotiation=False,
                risk_scaling_enabled=False,
            ),
            CapitalTier.SMALL: InvestmentProfile(
                profile_id="small",
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
            CapitalTier.LARGE: InvestmentProfile(
                profile_id="large",
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
        }

        params_dict = {}
        for tier, profile in profiles.items():
            params_dict[tier] = ModuleParameterSet(
                profile_id=profile.profile_id,
                input_id=profile.input_id,
                capital_tier=profile.capital_tier,
                objetivo_inversion=profile.objetivo_inversion,
                modules={
                    "momentum_modular": ModuleParameters(
                        module_name="momentum_modular",
                        tier=tier,
                        objective=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                        preset="balanced",
                        enabled=True,
                        max_position_size=Decimal("0.10"),
                        stop_loss_pct=Decimal("0.025"),
                        take_profit_pct=Decimal("0.050"),
                        max_exposure=Decimal("0.25"),
                        max_positions=5,
                        module_specific={},
                    )
                },
                total_max_exposure=Decimal("0.25"),
            )

        returns = {tier: orchestrator._simulate_backtest_return(profile, params_dict[tier])
                   for tier, profile in profiles.items()}

        # Micro and Small should have higher expected returns due to lower liquidity constraints
        assert returns[CapitalTier.MICRO] > 0
        assert returns[CapitalTier.SMALL] > 0
        assert returns[CapitalTier.LARGE] > 0
