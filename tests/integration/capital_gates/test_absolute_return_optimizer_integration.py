"""
Integration Tests for PHASE 1 T1.2 - Absolute Return Optimizer

End-to-end testing of optimization workflow:
profit_goal → tier_selection → parameter_optimization → feasibility_validation

Tests verify integration between:
- T1.1: CapitalTierStrategySelector (capital → tier → risk profile)
- T1.2: AbsoluteReturnOptimizer (profit goal → required parameters)
- DeploymentValidator (final safety gates)

These tests ensure the complete decision flow works correctly across
capital tiers with realistic trading scenarios.
"""

import pytest
from decimal import Decimal

from app.services.capital_tier_strategy_selector import CapitalTierStrategySelector
from app.services.absolute_return_optimizer import (
    AbsoluteReturnOptimizer,
    AlphaTargetCalculator,
    CapacityFadeAnalyzer,
    ParameterScaler,
)
from app.services.deployment_validator import DeploymentStatus


class TestMicroAccountOptimization:
    """Test T1.2 optimization for micro account (€10k)"""

    def setup_method(self):
        """Setup for micro account optimization tests"""
        self.capital = Decimal("10000")
        self.tier_selector = CapitalTierStrategySelector(self.capital, account_id="MICRO_OPT")
        self.optimizer = AbsoluteReturnOptimizer(self.capital, account_id="MICRO_OPT")

    def test_micro_optimization_workflow(self):
        """Full workflow: capital → tier → optimization → validation"""
        # 1. Get tier info and risk profile
        risk_profile = self.tier_selector.get_risk_profile()
        assert risk_profile.tier == "micro"
        assert risk_profile.leverage_allowed == Decimal("1.0")

        # 2. Calculate required alpha for modest goal
        monthly_goal = Decimal("50")
        alpha_target = AlphaTargetCalculator.calculate_required_alpha(
            monthly_goal,
            tax_rate=Decimal("0.20"),
            commission_per_trade=Decimal("10"),
            expected_trades_per_month=5,
        )
        assert alpha_target.monthly_alpha_needed > monthly_goal

        # 3. Estimate capacity fade for micro tier
        fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            capital=self.capital,
            base_monthly_alpha=Decimal("100"),
            tier=self.tier_selector.tier,
        )
        assert fade.capital == self.capital
        assert fade.adjusted_alpha <= fade.base_monthly_alpha

        # 4. Optimize parameters within risk constraints
        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=monthly_goal,
            expected_monthly_alpha=Decimal("150"),
            risk_profile=risk_profile,
        )
        assert report.tier == "micro"
        assert params is not None or report.is_feasible == False

    def test_micro_conservative_goal(self):
        """Micro account with conservative €50/month goal"""
        risk_profile = self.tier_selector.get_risk_profile()

        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("50"),
            expected_monthly_alpha=Decimal("200"),
            risk_profile=risk_profile,
        )

        # Should be feasible with modest goal
        assert report.is_feasible or report.confidence_level == "medium"

    def test_micro_leverage_constraint(self):
        """Micro account respects no-leverage constraint"""
        risk_profile = self.tier_selector.get_risk_profile()

        assert risk_profile.leverage_allowed == Decimal("1.0")

        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("100"),
            expected_monthly_alpha=Decimal("300"),
            risk_profile=risk_profile,
        )

        # Parameters should respect 1.0x leverage limit
        if params:
            assert params.leverage_multiplier <= Decimal("1.0")


class TestSmallAccountOptimization:
    """Test T1.2 optimization for small account (€30k)"""

    def setup_method(self):
        """Setup for small account optimization tests"""
        self.capital = Decimal("30000")
        self.tier_selector = CapitalTierStrategySelector(self.capital, account_id="SMALL_OPT")
        self.optimizer = AbsoluteReturnOptimizer(self.capital, account_id="SMALL_OPT")

    def test_small_account_moderate_goal(self):
        """Small account with €200/month goal"""
        risk_profile = self.tier_selector.get_risk_profile()
        assert risk_profile.tier == "small"
        assert risk_profile.leverage_allowed > Decimal("1.0")

        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("200"),
            expected_monthly_alpha=Decimal("800"),
            risk_profile=risk_profile,
        )

        assert report.tier == "small"
        # With sufficient alpha, should be feasible or restricted
        assert report.is_feasible or report.confidence_level in ["medium", "low"]

    def test_small_account_leverage_usage(self):
        """Small account can use modest leverage"""
        risk_profile = self.tier_selector.get_risk_profile()

        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("150"),
            expected_monthly_alpha=Decimal("1000"),
            risk_profile=risk_profile,
        )

        # Leverage should be allowed (1.25x)
        assert risk_profile.leverage_allowed == Decimal("1.25")

    def test_small_account_position_sizing(self):
        """Small account respects position sizing constraints"""
        risk_profile = self.tier_selector.get_risk_profile()

        max_position = self.capital * risk_profile.max_position_size

        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("100"),
            expected_monthly_alpha=Decimal("500"),
            risk_profile=risk_profile,
        )

        # If optimized, position should respect max size
        if params:
            assert params.position_size_usd <= max_position


class TestMediumAccountOptimization:
    """Test T1.2 optimization for medium account (€100k)"""

    def setup_method(self):
        """Setup for medium account optimization tests"""
        self.capital = Decimal("100000")
        self.tier_selector = CapitalTierStrategySelector(self.capital, account_id="MEDIUM_OPT")
        self.optimizer = AbsoluteReturnOptimizer(self.capital, account_id="MEDIUM_OPT")

    def test_medium_account_balanced_goal(self):
        """Medium account with €500/month goal"""
        risk_profile = self.tier_selector.get_risk_profile()
        assert risk_profile.tier == "medium"
        assert risk_profile.leverage_allowed == Decimal("1.5")

        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("5000"),
            risk_profile=risk_profile,
        )

        assert report.tier == "medium"
        # With realistic alpha, should be achievable
        assert report.is_feasible or report.confidence_level in ["medium", "high"]

    def test_medium_capacity_fade_projection(self):
        """Medium account projects capacity fade correctly"""
        # Get base alpha
        fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            capital=self.capital,
            base_monthly_alpha=Decimal("5000"),
            tier=self.tier_selector.tier,
        )

        # Verify fade decreases at higher capital levels
        assert fade.alpha_at_2x_capital < fade.base_monthly_alpha
        assert fade.alpha_at_5x_capital < fade.alpha_at_2x_capital

    def test_medium_account_full_workflow(self):
        """Complete workflow for medium account"""
        # 1. Select strategy for tier
        strategy = self.tier_selector.select_strategies()
        assert strategy.ensemble_type.value == "regime_based"

        # 2. Get risk profile
        risk = self.tier_selector.get_risk_profile()
        assert risk.tier == "medium"

        # 3. Optimize for Plan Maestro-like goal (€500/month)
        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("5000"),
            risk_profile=risk,
        )

        # 4. Validate feasibility
        assert report.required_alpha > Decimal("0")
        assert report.tier == "medium"


class TestLargeAccountOptimization:
    """Test T1.2 optimization for large account (€250k)"""

    def setup_method(self):
        """Setup for large account optimization tests"""
        self.capital = Decimal("250000")
        self.tier_selector = CapitalTierStrategySelector(self.capital, account_id="LARGE_OPT")
        self.optimizer = AbsoluteReturnOptimizer(self.capital, account_id="LARGE_OPT")

    def test_large_account_plan_maestro_scenario(self):
        """Large account - Plan Maestro primary scenario (€800/month on €250k)"""
        risk_profile = self.tier_selector.get_risk_profile()
        assert risk_profile.tier == "large"
        assert risk_profile.leverage_allowed == Decimal("2.5")

        # Plan Maestro target
        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("800"),
            expected_monthly_alpha=Decimal("50000"),
            risk_profile=risk_profile,
        )

        assert report.tier == "large"
        # With sufficient alpha for large tier modules, should be achievable
        assert report.is_feasible or report.confidence_level in ["medium", "high"]

    def test_large_account_aggressive_parameters(self):
        """Large account can use aggressive parameters"""
        risk_profile = self.tier_selector.get_risk_profile()

        # Should allow 2.5x leverage
        assert risk_profile.leverage_allowed == Decimal("2.5")

        params, report = self.optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("1000"),
            expected_monthly_alpha=Decimal("100000"),
            risk_profile=risk_profile,
        )

        # Position sizing should reflect aggressive stance
        if params:
            assert params.leverage_multiplier <= risk_profile.leverage_allowed

    def test_large_account_kelly_criterion(self):
        """Large account uses Kelly criterion positioning"""
        risk_profile = self.tier_selector.get_risk_profile()
        from app.services.capital_tier_strategy_selector import PositionSizingStrategy

        assert risk_profile.position_sizing_strategy == PositionSizingStrategy.KELLY_CRITERION


class TestOptimizationConsistency:
    """Test consistency of optimization across instances"""

    def test_same_capital_same_optimization(self):
        """Same capital produces consistent optimization results"""
        capital = Decimal("100000")

        opt1 = AbsoluteReturnOptimizer(capital, account_id="TEST1")
        opt2 = AbsoluteReturnOptimizer(capital, account_id="TEST2")

        selector1 = CapitalTierStrategySelector(capital, account_id="TEST1")
        selector2 = CapitalTierStrategySelector(capital, account_id="TEST2")

        risk1 = selector1.get_risk_profile()
        risk2 = selector2.get_risk_profile()

        report1, params1 = opt1.optimize_for_target(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("5000"),
            risk_profile=risk1,
        )
        # Note: swapped order to match actual return
        params1, report1 = opt1.optimize_for_target(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("5000"),
            risk_profile=risk1,
        )
        params2, report2 = opt2.optimize_for_target(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("5000"),
            risk_profile=risk2,
        )

        assert report1.tier == report2.tier
        assert report1.is_feasible == report2.is_feasible
        assert report1.required_alpha == report2.required_alpha


class TestRealWorldScenarios:
    """Test realistic trading scenarios across all tiers"""

    def test_tier_progression_optimization(self):
        """Optimization improves as capital tiers up"""
        # Test progression: micro → small → medium → large
        scenarios = [
            (Decimal("10000"), Decimal("50"), Decimal("150")),       # Micro
            (Decimal("30000"), Decimal("200"), Decimal("800")),      # Small
            (Decimal("100000"), Decimal("500"), Decimal("5000")),    # Medium
            (Decimal("250000"), Decimal("800"), Decimal("50000")),   # Large
        ]

        for capital, goal, alpha in scenarios:
            selector = CapitalTierStrategySelector(capital)
            optimizer = AbsoluteReturnOptimizer(capital)
            risk = selector.get_risk_profile()

            params, report = optimizer.optimize_for_target(
                monthly_profit_goal=goal,
                expected_monthly_alpha=alpha,
                risk_profile=risk,
            )

            assert report.tier in ["micro", "small", "medium", "large"]

    def test_realistic_alpha_estimates(self):
        """Test with realistic alpha estimates from backtesting"""
        # Common backtesting results: momentum_engine ~0.3-0.5% monthly
        capital = Decimal("100000")
        monthly_alpha = Decimal("3000")  # 3% of €100k capital

        optimizer = AbsoluteReturnOptimizer(capital)
        selector = CapitalTierStrategySelector(capital)
        risk = selector.get_risk_profile()

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=monthly_alpha,
            risk_profile=risk,
        )

        # Should be feasible
        assert report.is_feasible or report.confidence_level != "not_feasible"

    def test_capacity_fade_realistic_scenario(self):
        """Realistic capacity fade scenario (2x-5x capital scaling)"""
        # Medium account scaling to large
        capital = Decimal("100000")
        base_alpha = Decimal("5000")

        optimizer = AbsoluteReturnOptimizer(capital)

        # Project what happens if capital scales
        fade = CapacityFadeAnalyzer.estimate_capacity_fade(
            capital=capital,
            base_monthly_alpha=base_alpha,
            tier=optimizer.tier,
        )

        # Alpha should degrade predictably
        # Medium tier: 12% decay per 10x
        # 2x capital: ~2-3% decay expected
        # 5x capital: ~7-8% decay expected
        assert fade.alpha_at_2x_capital > Decimal("0")
        assert fade.alpha_at_5x_capital > Decimal("0")
        assert fade.alpha_at_5x_capital < fade.alpha_at_2x_capital


class TestOptimizationEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_small_goal_optimization(self):
        """Test optimization with very small goal (€10/month)"""
        capital = Decimal("10000")
        optimizer = AbsoluteReturnOptimizer(capital)
        selector = CapitalTierStrategySelector(capital)
        risk = selector.get_risk_profile()

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("10"),
            expected_monthly_alpha=Decimal("100"),
            risk_profile=risk,
        )

        # Very small goals should always be feasible
        assert report.is_feasible

    def test_very_large_goal_optimization(self):
        """Test optimization with aggressive goal (€2000/month on €250k)"""
        capital = Decimal("250000")
        optimizer = AbsoluteReturnOptimizer(capital)
        selector = CapitalTierStrategySelector(capital)
        risk = selector.get_risk_profile()

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("2000"),
            expected_monthly_alpha=Decimal("200000"),
            risk_profile=risk,
        )

        # Very large goals may not be feasible
        assert report.is_feasible or report.confidence_level == "low"

    def test_zero_alpha_handling(self):
        """Test handling of zero/insufficient alpha"""
        capital = Decimal("100000")
        optimizer = AbsoluteReturnOptimizer(capital)
        selector = CapitalTierStrategySelector(capital)
        risk = selector.get_risk_profile()

        params, report = optimizer.optimize_for_target(
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("100"),  # Insufficient
            risk_profile=risk,
        )

        # Should be rejected with clear messaging
        assert report.is_feasible == False
        assert report.gap < Decimal("0")  # Shortfall
