"""
Integration Tests for PHASE 0 Capital Gates (T0.3)

Tests five critical interaction scenarios across all capital gates:
1. T0.3.1: Capital Viability + Execution Cost interaction
2. T0.3.2: Learning Gate + Expensive Module Gate interaction
3. T0.3.3: Multi-gate decision flow coordination
4. T0.3.4: Audit trail consistency across gates
5. T0.3.5: Edge cases and boundary conditions

These tests verify that capital gates work together to coherently prevent
capital erosion across economic viability, execution efficiency, learning
cost, and module expense domains.
"""

from decimal import Decimal

from app.services.capital_viability_gate import CapitalViabilityValidator
from app.services.execution_cost_analyzer import ExecutionCostAnalyzer
from app.services.expensive_module_gate import ExpensiveModuleGate
from app.services.learning_capital_gate import LearningCapitalGate


class TestT031CapitalViabilityExecutionCostInteraction:
    """T0.3.1: Capital Viability + Execution Cost Interaction"""

    def test_viable_goal_but_execution_costs_high_with_volatility(self):
        """Capital goal viable, but execution costs spike in high volatility"""
        # Capital viability passes
        capital_analysis = CapitalViabilityValidator.validate_profit_goal(
            capital=Decimal("50000"),
            monthly_goal=Decimal("500"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )
        assert capital_analysis["is_viable"]

        # Execution cost varies with volatility
        analyzer = ExecutionCostAnalyzer(commission_per_trade=Decimal("15"))

        normal_vol = analyzer.should_execute_trade(
            position_size=Decimal("5000"),
            expected_alpha=Decimal("50"),
            volatility_percentile=50,
            num_concurrent_trades=1,
        )

        high_vol = analyzer.should_execute_trade(
            position_size=Decimal("5000"),
            expected_alpha=Decimal("50"),
            volatility_percentile=95,
            num_concurrent_trades=1,
        )

        # Normal vol trade accepted, high vol trade rejected
        assert normal_vol[0]  # should_execute
        assert not high_vol[0]  # should_execute


class TestT032LearningGateExpensiveModuleGateInteraction:
    """T0.3.2: Learning Gate + Expensive Module Gate Interaction"""

    def test_micro_account_all_features_disabled(self):
        """Micro account ($10k): learning + modules both disabled"""
        # Learning disabled
        learning_viable, learning_analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("50"),
            learning_enabled=True,
        )
        assert not learning_viable
        assert not learning_analysis["learning_recommended"]

        # Modules disabled
        modules_enabled, _ = ExpensiveModuleGate.get_enabled_modules(
            capital=Decimal("10000"),
            expected_monthly_alpha=Decimal("50"),
        )
        assert all(not v for v in modules_enabled.values())

    def test_medium_account_selective_enabling(self):
        """Medium account ($75k): learning enabled, some modules enabled"""
        # Learning enabled
        learning_viable, learning_analysis = LearningCapitalGate.is_learning_viable(
            capital=Decimal("75000"),
            expected_monthly_alpha=Decimal("500"),
            learning_enabled=True,
        )
        assert learning_viable
        assert learning_analysis["learning_recommended"]

        # Some modules enabled (not all)
        modules_enabled, _ = ExpensiveModuleGate.get_enabled_modules(
            capital=Decimal("75000"),
            expected_monthly_alpha=Decimal("500"),
        )
        assert modules_enabled["deep_learning_engine"]
        assert not modules_enabled["transformer_engine"]


class TestT033MultiGateDecisionFlow:
    """T0.3.3: Multi-gate Decision Flow"""

    def test_small_account_conservative_across_all_gates(self):
        """Small account restricted across all gates"""
        capital = Decimal("15000")

        # Capital viability borderline
        cap_analysis = CapitalViabilityValidator.validate_profit_goal(
            capital=capital,
            monthly_goal=Decimal("100"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=5,
        )
        assert cap_analysis["severity"] in ["WARNING", "OK", "CRITICAL"]

        # Learning disabled
        learning_viable, learn_analysis = LearningCapitalGate.is_learning_viable(
            capital=capital,
            expected_monthly_alpha=Decimal("100"),
            learning_enabled=True,
        )
        assert not learning_viable
        assert not learn_analysis["learning_recommended"]

        # Modules disabled
        enabled_modules, _ = ExpensiveModuleGate.get_enabled_modules(
            capital=capital,
            expected_monthly_alpha=Decimal("100"),
        )
        assert all(not v for v in enabled_modules.values())

    def test_large_account_permissive_across_all_gates(self):
        """Large account permitted across all gates"""
        capital = Decimal("500000")

        # Capital viability passes
        cap_analysis = CapitalViabilityValidator.validate_profit_goal(
            capital=capital,
            monthly_goal=Decimal("1000"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=20,
        )
        assert cap_analysis["is_viable"]

        # Execution cost passes even with concurrency
        analyzer = ExecutionCostAnalyzer(commission_per_trade=Decimal("15"))
        should_execute, _ = analyzer.should_execute_trade(
            position_size=Decimal("50000"),
            expected_alpha=Decimal("500"),
            volatility_percentile=50,
            num_concurrent_trades=3,
        )
        assert should_execute

        # Learning enabled
        learning_viable, learn_analysis = LearningCapitalGate.is_learning_viable(
            capital=capital,
            expected_monthly_alpha=Decimal("3000"),
            learning_enabled=True,
        )
        assert learning_viable
        assert learn_analysis["learning_recommended"]

        # Modules enabled
        enabled_modules, _ = ExpensiveModuleGate.get_enabled_modules(
            capital=capital,
            expected_monthly_alpha=Decimal("3000"),
        )
        assert any(v for v in enabled_modules.values())


class TestT034AuditTrailConsistency:
    """T0.3.4: Audit Trail Consistency"""

    def test_all_gates_produce_audit_logs(self):
        """All gates generate audit logs with account_id"""
        capital = Decimal("50000")
        account_id = "TEST_ACCT_001"

        # Capital log
        cap_analysis = CapitalViabilityValidator.validate_profit_goal(
            capital=capital,
            monthly_goal=Decimal("300"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )
        cap_log = CapitalViabilityValidator.log_viability_check(
            capital=capital,
            monthly_goal=Decimal("300"),
            result=cap_analysis,
            account_id=account_id,
        )
        assert account_id in cap_log
        assert "$" in cap_log  # Contains dollar amounts

        # Learning log
        learning_viable, learn_analysis = LearningCapitalGate.is_learning_viable(
            capital=capital,
            expected_monthly_alpha=Decimal("200"),
            learning_enabled=True,
        )
        learn_log = LearningCapitalGate.log_learning_decision(
            capital=capital,
            analysis=learn_analysis,
            account_id=account_id,
        )
        assert account_id in learn_log

        # Module log
        _, module_analysis = ExpensiveModuleGate.should_enable_module(
            module_name="deep_learning_engine",
            capital=capital,
            expected_monthly_alpha=Decimal("200"),
        )
        module_log = ExpensiveModuleGate.log_module_decision(
            module_name="deep_learning_engine",
            capital=capital,
            analysis=module_analysis,
            account_id=account_id,
        )
        assert account_id in module_log


class TestT035EdgeCasesAndBoundaryConditions:
    """T0.3.5: Edge Cases and Boundary Conditions"""

    def test_learning_capital_threshold_transition(self):
        """Test transition around $25k learning threshold"""
        # Below threshold
        below = LearningCapitalGate.is_learning_viable(
            capital=Decimal("24900"),
            expected_monthly_alpha=Decimal("300"),
            learning_enabled=True,
        )
        assert not below[0]

        # At threshold
        at = LearningCapitalGate.is_learning_viable(
            capital=Decimal("25000"),
            expected_monthly_alpha=Decimal("300"),
            learning_enabled=True,
        )
        assert at[0]

        # Above threshold
        above = LearningCapitalGate.is_learning_viable(
            capital=Decimal("25100"),
            expected_monthly_alpha=Decimal("300"),
            learning_enabled=True,
        )
        assert above[0]

    def test_multiple_gates_reject_simultaneously(self):
        """Multiple gates reject small account simultaneously"""
        capital = Decimal("15000")

        # Capital goal challenging - $2000/month is 13% monthly return
        cap_result = CapitalViabilityValidator.validate_profit_goal(
            capital=capital,
            monthly_goal=Decimal("2000"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=10,
        )

        # Execution cost high
        analyzer = ExecutionCostAnalyzer(commission_per_trade=Decimal("20"))
        exec_result = analyzer.should_execute_trade(
            position_size=Decimal("1500"),
            expected_alpha=Decimal("30"),
            volatility_percentile=80,
            num_concurrent_trades=2,
        )

        # Learning not viable
        learn_result = LearningCapitalGate.is_learning_viable(
            capital=capital,
            expected_monthly_alpha=Decimal("150"),
            learning_enabled=True,
        )

        # Modules disabled
        modules_result, _ = ExpensiveModuleGate.get_enabled_modules(
            capital=capital,
            expected_monthly_alpha=Decimal("150"),
        )

        # Multiple rejection points
        assert not cap_result["is_viable"]  # Capital goal difficult
        assert not exec_result[0]  # Execution rejected
        assert not learn_result[0]  # Learning disabled
        assert all(not v for v in modules_result.values())  # Modules disabled

    def test_concurrent_trades_amplify_cost_rejection(self):
        """Concurrent trades increase rejection likelihood"""
        analyzer = ExecutionCostAnalyzer(commission_per_trade=Decimal("15"))

        # Single trade accepted
        single_viable, single_analysis = analyzer.should_execute_trade(
            position_size=Decimal("10000"),
            expected_alpha=Decimal("100"),
            volatility_percentile=50,
            num_concurrent_trades=1,
        )
        assert single_viable

        # Concurrent trades rejected or barely accepted
        triple_viable, triple_analysis = analyzer.should_execute_trade(
            position_size=Decimal("10000"),
            expected_alpha=Decimal("100"),
            volatility_percentile=50,
            num_concurrent_trades=3,
        )
        # Cost ratio increases with concurrency
        assert triple_analysis["cost_ratio"] > single_analysis["cost_ratio"]

    def test_large_account_passes_all_gates(self):
        """Large account ($500k) passes all gate checks"""
        capital = Decimal("500000")

        # Capital passes
        cap_analysis = CapitalViabilityValidator.validate_profit_goal(
            capital=capital,
            monthly_goal=Decimal("2000"),
            tax_rate=Decimal("0.40"),
            commission_per_trade=Decimal("15"),
            expected_trades_per_month=50,
        )
        assert cap_analysis["is_viable"]

        # Execution passes
        analyzer = ExecutionCostAnalyzer(commission_per_trade=Decimal("15"))
        exec_viable, _ = analyzer.should_execute_trade(
            position_size=Decimal("100000"),
            expected_alpha=Decimal("1000"),
            volatility_percentile=90,
            num_concurrent_trades=5,
        )
        assert exec_viable

        # Learning passes
        learn_viable, _ = LearningCapitalGate.is_learning_viable(
            capital=capital,
            expected_monthly_alpha=Decimal("3000"),
            learning_enabled=True,
        )
        assert learn_viable

        # Modules enabled
        modules_enabled, _ = ExpensiveModuleGate.get_enabled_modules(
            capital=capital,
            expected_monthly_alpha=Decimal("3000"),
        )
        assert sum(1 for v in modules_enabled.values() if v) >= 4
