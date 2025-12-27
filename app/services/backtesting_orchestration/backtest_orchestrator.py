"""
T4.1: BacktestOrchestrator - Parametrized Backtest Execution

Executes backtests with parameters from ModuleParametrizer and calculates
feasibility_ratio for deployment decisions in T10.1.

Key Responsibility:
- Accept ModuleParameterSet from T3.1
- Execute backtest with those parameters
- Calculate feasibility_ratio = (backtest_return / required_return)
- Return BacktestResult with feasibility metrics

Feasibility Ratio Formula:
  required_return = (target_euros_per_month / capital) * 12
  feasibility_ratio = annualized_return / required_return

  Example: €800/month, €250k capital
    required_return = (800/250000) * 12 = 3.84%
    If backtest yields 5.2%: feasibility_ratio = 5.2% / 3.84% = 1.35 ✅
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.backtesting.models import BacktestConfig, BacktestResult
from app.core.models.investment_profile import InvestmentProfile
from app.services.parametrization.module_parametrizer import ModuleParameterSet

logger = logging.getLogger(__name__)


class FeasibilityMetrics(BaseModel):
    """Extended metrics for feasibility analysis."""

    required_annual_return: Decimal = Field(
        ..., description="Annual return required to meet target (percentage)"
    )
    required_monthly_return: Decimal = Field(
        ..., description="Monthly return required to meet target (percentage)"
    )
    feasibility_ratio: Decimal = Field(
        ..., description="Backtest return / Required return (≥1.0 viable)"
    )
    viability_status: str = Field(
        ...,
        description="APPROVED (≥1.0) | CONDITIONAL (0.7-1.0) | REJECTED (<0.7)",
    )
    risk_adjusted_return: Optional[Decimal] = Field(
        None, description="Return adjusted for risk (sharpe-weighted)"
    )
    confidence_level: str = Field(
        ..., description="VERY_HIGH (≥1.5) | HIGH (1.0-1.5) | MEDIUM (0.7-1.0) | LOW (<0.7)"
    )


class ExtendedBacktestResult(BacktestResult):
    """BacktestResult extended with feasibility metrics from T4.1."""

    feasibility_metrics: Optional[FeasibilityMetrics] = Field(
        None, description="Feasibility analysis metrics"
    )
    parameter_set: Optional[ModuleParameterSet] = Field(
        None, description="Module parameters used in backtest"
    )
    investment_profile: Optional[InvestmentProfile] = Field(
        None, description="Investment profile used"
    )

    class Config:
        arbitrary_types_allowed = True


class BacktestOrchestrator:
    """
    T4.1: Execute backtests with parametrized module configurations.

    Orchestrates the complete backtest execution pipeline:
    1. Accept ModuleParameterSet from T3.1
    2. Execute backtest with parameters applied to strategy
    3. Calculate feasibility metrics
    4. Return ExtendedBacktestResult for T5.1 validation

    Critical Decision: Use existing comprehensive_backtest_runner.py infrastructure
    rather than building from scratch (DRY principle).
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize BacktestOrchestrator.

        Args:
            config_path: Path to backtest configuration YAML (uses comprehensive_backtest_runner)
                        If None, uses sensible defaults.
        """
        self.config_path = config_path or "config/backtest_config.yaml"
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"📊 BacktestOrchestrator initialized (config: {self.config_path})")

    async def execute_backtest(
        self,
        investment_profile: InvestmentProfile,
        module_parameters: ModuleParameterSet,
        data_start_date: datetime,
        data_end_date: datetime,
        target_euros_per_month: Optional[Decimal] = None,
    ) -> ExtendedBacktestResult:
        """
        Execute backtest with parametrized modules.

        Args:
            investment_profile: InvestmentProfile from T2.1
            module_parameters: ModuleParameterSet from T3.1
            data_start_date: Start date for historical backtest
            data_end_date: End date for historical backtest
            target_euros_per_month: Monthly EUR target (optional, uses profile if None)

        Returns:
            ExtendedBacktestResult with feasibility metrics

        Raises:
            ValueError: If parameters are invalid or backtest fails
        """
        try:
            # Step 1: Prepare backtest configuration from investment profile
            self.logger.info(
                f"⚙️  Preparing backtest for {investment_profile.capital_tier} "
                f"with {len(module_parameters.parameters)} modules"
            )

            backtest_config = self._create_backtest_config_from_profile(investment_profile)

            # Step 2: Execute backtest with the comprehensive runner
            # For now, we'll create a simulated backtest result
            # In production, this would integrate with comprehensive_backtest_runner
            backtest_result = await self._execute_with_comprehensive_runner(
                investment_profile=investment_profile,
                module_parameters=module_parameters,
                backtest_config=backtest_config,
                data_start_date=data_start_date,
                data_end_date=data_end_date,
            )

            # Step 3: Calculate feasibility metrics
            target_euros = target_euros_per_month or investment_profile.capital_initial * Decimal(
                "0.04"
            ) / Decimal("12")
            feasibility_metrics = self._calculate_feasibility_metrics(
                backtest_result=backtest_result,
                capital=investment_profile.capital_initial,
                target_euros_per_month=target_euros,
                backtest_start=data_start_date,
                backtest_end=data_end_date,
            )

            # Step 4: Create extended result with feasibility metrics
            extended_result = ExtendedBacktestResult(
                **backtest_result.model_dump(),
                feasibility_metrics=feasibility_metrics,
                parameter_set=module_parameters,
                investment_profile=investment_profile,
            )

            self.logger.info(
                f"✅ Backtest complete: "
                f"return={extended_result.total_return:.2f}%, "
                f"feasibility_ratio={feasibility_metrics.feasibility_ratio:.2f}"
            )

            return extended_result

        except Exception as e:
            self.logger.error(f"❌ Backtest execution failed: {e}", exc_info=True)
            raise ValueError(f"Backtest execution failed: {e}") from e

    def _create_backtest_config_from_profile(
        self, investment_profile: InvestmentProfile
    ) -> BacktestConfig:
        """Create BacktestConfig from InvestmentProfile."""
        return BacktestConfig(
            strategy_name=f"parametrized_{investment_profile.capital_tier}",
            initial_capital=investment_profile.capital_initial,
            max_position_size=investment_profile.max_position_size,
            stop_loss_percentage=Decimal("2.5"),  # Default conservative
            take_profit_percentage=Decimal("5.0"),  # Default conservative
            commission_per_trade=Decimal("10.0"),  # Platform-dependent
            slippage_percentage=Decimal("0.1"),  # Market-dependent
        )

    async def _execute_with_comprehensive_runner(
        self,
        investment_profile: InvestmentProfile,
        module_parameters: ModuleParameterSet,
        backtest_config: BacktestConfig,
        data_start_date: datetime,
        data_end_date: datetime,
    ) -> BacktestResult:
        """
        Execute backtest using comprehensive_backtest_runner infrastructure.

        In production, this integrates with existing ComprehensiveBacktestRunner
        to execute actual backtests. For now, returns simulation result.
        """
        # TODO T4.1.1: Integrate with ComprehensiveBacktestRunner
        # For MVP, create simulation based on module type + capital tier
        simulated_return = self._simulate_backtest_return(
            investment_profile=investment_profile,
            module_parameters=module_parameters,
        )

        # Create result
        result = BacktestResult(
            strategy_name=backtest_config.strategy_name,
            config=backtest_config,
            trades=[],  # Will be populated by actual backtest
            performance=None,  # Will be calculated by backtest engine
            equity_curve=[],  # Will be calculated by backtest engine
            start_date=data_start_date,
            end_date=data_end_date,
            final_capital=backtest_config.initial_capital
            * (Decimal("1") + simulated_return / Decimal("100")),
            total_return=simulated_return,
            annualized_return=simulated_return,  # Simplified for MVP
        )

        return result

    def _simulate_backtest_return(
        self,
        investment_profile: InvestmentProfile,
        module_parameters: ModuleParameterSet,
    ) -> Decimal:
        """
        Simulate backtest return based on module type and capital tier.

        This is a simplified model for MVP. In production, actual backtest engine
        would execute historical simulation.

        Returns:
            Simulated annual return (percentage)
        """
        # Base return by capital tier (higher capital = slightly lower returns due to liquidity)
        base_returns = {
            "micro": Decimal("15"),  # 15% for small accounts with tight execution
            "small": Decimal("12"),  # 12% for small accounts
            "medium": Decimal("8"),  # 8% for medium accounts (capacity fade)
            "large": Decimal("5"),  # 5% for large accounts (capacity fade)
        }

        base = base_returns.get(investment_profile.capital_tier, Decimal("8"))

        # Adjust by number of enabled modules (more = more diversification = slightly lower sharpe but more stable)
        module_count = len(module_parameters.modules)
        diversification_factor = Decimal("1") - (Decimal(module_count) * Decimal("0.02"))
        diversification_factor = max(diversification_factor, Decimal("0.8"))

        # Adjust by risk profile (higher risk = potentially higher return, but more volatility)
        risk_adjustment = Decimal("1") + (
            Decimal(investment_profile.risk_profile) * Decimal("0.05")
        )

        simulated_return = base * diversification_factor * risk_adjustment

        # Add realistic variance (+/- 20%)
        import random

        variance = random.uniform(-0.2, 0.2)
        simulated_return = simulated_return * (Decimal("1") + Decimal(str(variance)))

        return simulated_return

    def _calculate_feasibility_metrics(
        self,
        backtest_result: BacktestResult,
        capital: Decimal,
        target_euros_per_month: Decimal,
        backtest_start: datetime,
        backtest_end: datetime,
    ) -> FeasibilityMetrics:
        """
        Calculate feasibility metrics for deployment decision.

        Formula:
          required_return = (target_euros_per_month / capital) * 12
          feasibility_ratio = annualized_return / required_return

        Args:
            backtest_result: Backtest execution result
            capital: Initial capital (EUR)
            target_euros_per_month: Monthly profit target (EUR)
            backtest_start: Backtest start date
            backtest_end: Backtest end date

        Returns:
            FeasibilityMetrics with viability assessment
        """
        # Calculate required annual return
        required_monthly_return = (target_euros_per_month / capital) * Decimal("100")
        required_annual_return = required_monthly_return * Decimal("12")

        # Get backtest annual return
        backtest_return = backtest_result.annualized_return or backtest_result.total_return
        if backtest_return is None:
            backtest_return = Decimal("0")

        # Calculate feasibility ratio
        if required_annual_return > 0:
            feasibility_ratio = backtest_return / required_annual_return
        else:
            feasibility_ratio = Decimal("0")

        # Determine viability status
        if feasibility_ratio >= Decimal("1.0"):
            viability_status = "APPROVED"
        elif feasibility_ratio >= Decimal("0.7"):
            viability_status = "CONDITIONAL"
        else:
            viability_status = "REJECTED"

        # Determine confidence level
        if feasibility_ratio >= Decimal("1.5"):
            confidence_level = "VERY_HIGH"
        elif feasibility_ratio >= Decimal("1.0"):
            confidence_level = "HIGH"
        elif feasibility_ratio >= Decimal("0.7"):
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        # Risk-adjusted return (if sharpe available)
        risk_adjusted_return = None
        if backtest_result.performance and backtest_result.performance.sharpe_ratio:
            risk_adjusted_return = (
                backtest_result.performance.sharpe_ratio * backtest_return / Decimal("100")
            )

        return FeasibilityMetrics(
            required_annual_return=required_annual_return,
            required_monthly_return=required_monthly_return,
            feasibility_ratio=feasibility_ratio,
            viability_status=viability_status,
            risk_adjusted_return=risk_adjusted_return,
            confidence_level=confidence_level,
        )
