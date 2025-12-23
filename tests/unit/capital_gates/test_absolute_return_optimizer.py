"""
Unit Tests for PHASE 1 T1.2: Absolute Return Optimizer

Tests core service class, data validation, and specialist components.
"""

import pytest
from decimal import Decimal

from app.services.absolute_return_optimizer import (
    AbsoluteReturnOptimizer,
    AlphaTargetCalculator,
    CapacityFadeAnalyzer,
    ParameterScaler,
    ReturnDistributionValidator,
    MonthlyProfitForecaster,
    AlphaTarget,
    CapacityFadeEstimate,
    OptimizedParameters,
    MonthlyProfitForecast,
    FeasibilityReport,
)
from app.services.capital_tier_strategy_selector import RiskProfile, PositionSizingStrategy
from app.services.account_configuration import AccountTier


class TestAbsoluteReturnOptimizerInitialization:
    """Test optimizer initialization"""

    def test_init_valid_capital(self):
        """Initialize with valid capital"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"))
        assert optimizer.capital == Decimal("250000")
        assert optimizer.tier == AccountTier.LARGE

    def test_init_with_account_id(self):
        """Initialize with account ID"""
        optimizer = AbsoluteReturnOptimizer(
            Decimal("100000"),
            account_id="ACC_001"
        )
        assert optimizer.account_id == "ACC_001"

    def test_init_zero_capital_raises(self):
        """Initialize with zero capital should raise"""
        with pytest.raises(ValueError):
            AbsoluteReturnOptimizer(Decimal("0"))

    def test_init_negative_capital_raises(self):
        """Initialize with negative capital should raise"""
        with pytest.raises(ValueError):
            AbsoluteReturnOptimizer(Decimal("-10000"))

    def test_tier_classification(self):
        """Verify tier classification during init"""
        for capital, expected_tier in [
            (Decimal("10000"), AccountTier.MICRO),
            (Decimal("30000"), AccountTier.SMALL),
            (Decimal("100000"), AccountTier.MEDIUM),
            (Decimal("500000"), AccountTier.LARGE),
        ]:
            optimizer = AbsoluteReturnOptimizer(capital)
            assert optimizer.tier == expected_tier


class TestAlphaTargetCalculator:
    """Test alpha target calculation"""

    def test_simple_goal_calculation(self):
        """Calculate alpha for simple goal"""
        target = AlphaTargetCalculator.calculate_required_alpha(
            monthly_profit_goal=Decimal("800"),
            tax_rate=Decimal("0.20"),
            commission_per_trade=Decimal("10"),
            expected_trades_per_month=10,
        )

        assert target.monthly_profit_goal == Decimal("800")
        assert target.net_profit_expected == Decimal("800")
        # Gross = 800 / 0.8 = 1000
        assert target.gross_profit_needed == Decimal("1000")
        # Alpha = 1000 + (10 * 10) = 1100
        assert target.monthly_alpha_needed == Decimal("1100")

    def test_confidence_scoring(self):
        """Confidence score reflects goal realism"""
        low_goal = AlphaTargetCalculator.calculate_required_alpha(Decimal("100"))
        high_goal = AlphaTargetCalculator.calculate_required_alpha(Decimal("5000"))

        # Higher goals = lower confidence
        assert low_goal.confidence_score > high_goal.confidence_score

    def test_different_tax_rates(self):
        """Alpha calculation adjusts for tax rate"""
        alpha_20pct = AlphaTargetCalculator.calculate_required_alpha(
            Decimal("800"),
            tax_rate=Decimal("0.20")
        )
        alpha_30pct = AlphaTargetCalculator.calculate_required_alpha(
            Decimal("800"),
            tax_rate=Decimal("0.30")
        )

        # Higher tax = more gross profit needed = more alpha
        assert alpha_30pct.monthly_alpha_needed > alpha_20pct.monthly_alpha_needed

    def test_goal_validation(self):
        """AlphaTarget validates correctly"""
        target = AlphaTargetCalculator.calculate_required_alpha(Decimal("800"))
        is_valid, msg = target.validate()

        assert is_valid
        assert "valid" in msg.lower()

    def test_zero_goal_raises(self):
        """Zero goal should raise"""
        with pytest.raises(ValueError):
            AlphaTargetCalculator.calculate_required_alpha(Decimal("0"))


class TestCapacityFadeAnalyzer:
    """Test capacity fade estimation"""

    def test_decay_at_same_capital(self):
        """No decay when capital same"""
        fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            capital=Decimal("100000"),
            base_monthly_alpha=Decimal("1000"),
            tier=AccountTier.MEDIUM,
            current_capital_reference=Decimal("100000"),
        )

        # At same capital, adjusted_alpha should equal base
        assert fade.adjusted_alpha == Decimal("1000")

    def test_decay_scales_with_tier(self):
        """Decay rate increases with tier"""
        micro_fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            Decimal("250000"), Decimal("1000"), AccountTier.MICRO
        )
        large_fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            Decimal("250000"), Decimal("1000"), AccountTier.LARGE
        )

        # Larger tier should have more decay (smaller adjusted_alpha)
        assert micro_fade.adjusted_alpha > large_fade.adjusted_alpha

    def test_decay_projects_5x_capital(self):
        """Generates projection for 5x capital"""
        fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            capital=Decimal("250000"),
            base_monthly_alpha=Decimal("2500"),
            tier=AccountTier.LARGE,
        )

        # 5x capital should have significantly less alpha
        assert fade.alpha_at_5x_capital < fade.base_monthly_alpha

    def test_fade_validation(self):
        """Capacity fade validates correctly"""
        fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            capital=Decimal("250000"),
            base_monthly_alpha=Decimal("2500"),
            tier=AccountTier.LARGE,
        )
        is_valid, msg = fade.validate()

        assert is_valid

    def test_zero_alpha_raises(self):
        """Zero alpha should raise"""
        with pytest.raises(ValueError):
            CapacityFadeAnalyzer.estimate_capacity_fade(
                Decimal("250000"),
                Decimal("0"),
                AccountTier.LARGE,
            )


class TestParameterScaler:
    """Test parameter scaling"""

    def test_scale_basic(self):
        """Basic parameter scaling"""
        risk_profile = RiskProfile(
            tier="large",
            max_position_size=Decimal("0.10"),
            max_concurrent_trades=5,
            max_daily_loss_pct=Decimal("0.05"),
            max_drawdown_pct=Decimal("0.15"),
            leverage_allowed=Decimal("2.5"),
            learning_enabled=True,
            modules_enabled={},
            position_sizing_strategy=PositionSizingStrategy.KELLY_CRITERION,
        )

        params = ParameterScaler.scale_for_target(
            capital=Decimal("250000"),
            monthly_target_return=Decimal("0.0032"),  # 0.32% for €800
            expected_win_rate=Decimal("0.55"),
            risk_profile=risk_profile,
        )

        assert params.position_size_usd == Decimal("250000") * Decimal("0.10")
        assert params.monthly_target_return == Decimal("0.0032")

    def test_leverage_respected(self):
        """Parameter scaling respects leverage limits"""
        risk_profile = RiskProfile(
            tier="small",
            max_position_size=Decimal("0.05"),
            max_concurrent_trades=2,
            max_daily_loss_pct=Decimal("0.02"),
            max_drawdown_pct=Decimal("0.08"),
            leverage_allowed=Decimal("1.25"),  # Limited leverage
            learning_enabled=False,
            modules_enabled={},
            position_sizing_strategy=PositionSizingStrategy.FIXED_PCT,
        )

        params = ParameterScaler.scale_for_target(
            capital=Decimal("30000"),
            monthly_target_return=Decimal("0.01"),  # 1% aggressive
            expected_win_rate=Decimal("0.50"),
            risk_profile=risk_profile,
        )

        assert params.leverage_multiplier == Decimal("1.25")

    def test_parameters_validate(self):
        """Scaled parameters validate correctly"""
        risk_profile = RiskProfile(
            tier="medium",
            max_position_size=Decimal("0.08"),
            max_concurrent_trades=3,
            max_daily_loss_pct=Decimal("0.03"),
            max_drawdown_pct=Decimal("0.10"),
            leverage_allowed=Decimal("1.5"),
            learning_enabled=True,
            modules_enabled={},
            position_sizing_strategy=PositionSizingStrategy.VOLATILITY_ADJUSTED,
        )

        params = ParameterScaler.scale_for_target(
            Decimal("100000"),
            Decimal("0.005"),
            Decimal("0.55"),
            risk_profile,
        )
        is_valid, msg = params.validate()

        assert is_valid


class TestReturnDistributionValidator:
    """Test return achievability validation"""

    def test_achievable_target(self):
        """Achievable target passes validation"""
        is_achievable, reason = ReturnDistributionValidator.validate_achievability(
            target_monthly_return=Decimal("500"),
            expected_monthly_alpha=Decimal("2000"),
        )

        assert is_achievable
        assert "achievable" in reason.lower()

    def test_unachievable_target(self):
        """Unachievable target fails validation"""
        is_achievable, reason = ReturnDistributionValidator.validate_achievability(
            target_monthly_return=Decimal("2000"),
            expected_monthly_alpha=Decimal("500"),
        )

        assert not is_achievable

    def test_zero_alpha_fails(self):
        """Zero expected alpha fails"""
        is_achievable, reason = ReturnDistributionValidator.validate_achievability(
            target_monthly_return=Decimal("500"),
            expected_monthly_alpha=Decimal("0"),
        )

        assert not is_achievable


class TestMonthlyProfitForecaster:
    """Test profit forecasting"""

    def test_basic_forecast(self):
        """Generate basic profit forecast"""
        forecast = MonthlyProfitForecaster.forecast_profit(
            position_size=Decimal("5000"),
            expected_win_rate=Decimal("0.55"),
            avg_win_loss_ratio=Decimal("1.5"),
            expected_monthly_trades=15,
        )

        assert forecast.expected_monthly_profit > Decimal("0")
        assert forecast.percentile_5 < forecast.expected_monthly_profit
        assert forecast.percentile_95 > forecast.expected_monthly_profit

    def test_forecast_win_rate_impact(self):
        """Higher win rate increases expected profit"""
        low_wr = MonthlyProfitForecaster.forecast_profit(
            position_size=Decimal("5000"),
            expected_win_rate=Decimal("0.50"),
        )
        high_wr = MonthlyProfitForecaster.forecast_profit(
            position_size=Decimal("5000"),
            expected_win_rate=Decimal("0.60"),
        )

        assert high_wr.expected_monthly_profit > low_wr.expected_monthly_profit

    def test_forecast_validates(self):
        """Forecast validates correctly"""
        forecast = MonthlyProfitForecaster.forecast_profit(
            position_size=Decimal("5000"),
            expected_win_rate=Decimal("0.55"),
        )
        is_valid, msg = forecast.validate()

        assert is_valid


class TestOptimizerOptimizeForTarget:
    """Test main optimization workflow"""

    def test_optimize_250k_800_month(self):
        """Optimize €250k for €800/month target (Plan Maestro scenario)"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"), account_id="LARGE_TEST")

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500"),
        )

        assert params is not None
        assert report is not None
        assert report.tier == "large"
        assert report.deployment_status in ["APPROVED", "RESTRICTED"]

    def test_optimize_100k_500_month(self):
        """Optimize €100k for €500/month target"""
        optimizer = AbsoluteReturnOptimizer(Decimal("100000"))

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("1500"),
        )

        assert report.tier == "medium"

    def test_optimize_30k_100_month(self):
        """Optimize €30k for €100/month target"""
        optimizer = AbsoluteReturnOptimizer(Decimal("30000"))

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("100"),
            expected_monthly_alpha=Decimal("300"),
        )

        assert report.tier == "small"

    def test_feasibility_report_structure(self):
        """Feasibility report has all required fields"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"))
        _, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500"),
        )

        assert hasattr(report, "is_feasible")
        assert hasattr(report, "confidence_level")
        assert hasattr(report, "required_alpha")
        assert hasattr(report, "available_alpha")
        assert hasattr(report, "gap")
        assert hasattr(report, "deployment_status")


class TestOptimizerValidateFeasibility:
    """Test feasibility validation"""

    def test_feasible_goal(self):
        """Feasible goal returns APPROVED"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"))

        report = optimizer.validate_feasibility(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500"),
        )

        assert report.is_feasible
        assert report.deployment_status == "APPROVED"

    def test_infeasible_goal(self):
        """Infeasible goal returns REJECTED"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"))

        report = optimizer.validate_feasibility(
            monthly_profit_goal=Decimal("5000"),  # Aggressive goal
            expected_monthly_alpha=Decimal("500"),  # Insufficient alpha
        )

        assert not report.is_feasible
        assert report.deployment_status == "REJECTED"


class TestOptimizerForecastProfit:
    """Test profit forecasting through optimizer"""

    def test_forecast_generation(self):
        """Optimizer generates profit forecast"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"))

        forecast = optimizer.forecast_monthly_profit(
            position_size=Decimal("25000"),
            expected_win_rate=Decimal("0.55"),
        )

        assert forecast.expected_monthly_profit > Decimal("0")
        assert forecast.expected_monthly_trades >= 0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_small_goal(self):
        """Optimizer handles very small profit goals"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"))

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("10"),  # Very small
            expected_monthly_alpha=Decimal("100"),
        )

        assert report.is_feasible

    def test_very_aggressive_goal(self):
        """Optimizer rejects unrealistic goals"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"))

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("50000"),  # 20% monthly - unrealistic
            expected_monthly_alpha=Decimal("500"),
        )

        assert not report.is_feasible

    def test_different_tax_rates(self):
        """Optimizer respects different tax rates"""
        optimizer = AbsoluteReturnOptimizer(Decimal("250000"))

        params_20, report_20 = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500"),
            tax_rate=Decimal("0.20"),
        )

        params_30, report_30 = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("2500"),
            tax_rate=Decimal("0.30"),
        )

        # Higher tax should require more alpha
        assert report_30.required_alpha > report_20.required_alpha


class TestDataClassValidation:
    """Test data class validation"""

    def test_alpha_target_validation(self):
        """AlphaTarget validates all fields"""
        target = AlphaTarget(
            monthly_profit_goal=Decimal("800"),
            monthly_alpha_needed=Decimal("1100"),
            gross_profit_needed=Decimal("1000"),
            net_profit_expected=Decimal("800"),
            confidence_score=Decimal("85"),
        )
        is_valid, msg = target.validate()

        assert is_valid

    def test_capacity_fade_validation(self):
        """CapacityFadeEstimate validates correctly"""
        fade = CapacityFadeEstimate(
            capital=Decimal("250000"),
            base_monthly_alpha=Decimal("2500"),
            estimated_decay_rate=Decimal("0.15"),
            adjusted_alpha=Decimal("2000"),
            alpha_at_2x_capital=Decimal("1800"),
            alpha_at_5x_capital=Decimal("1500"),
        )
        is_valid, msg = fade.validate()

        assert is_valid

    def test_optimized_parameters_validation(self):
        """OptimizedParameters validates correctly"""
        params = OptimizedParameters(
            position_size_pct=Decimal("0.10"),
            position_size_usd=Decimal("25000"),
            leverage_multiplier=Decimal("2.5"),
            max_concurrent_trades=5,
            monthly_target_return=Decimal("0.0032"),
            required_monthly_alpha=Decimal("800"),
            feasibility_score=Decimal("85"),
            confidence_level="high",
            risk_level="aggressive",
        )
        is_valid, msg = params.validate()

        assert is_valid
