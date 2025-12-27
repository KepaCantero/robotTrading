"""
T4.1: BacktestOrchestrator Tests

Tests for BacktestOrchestrator, backtesting execution, and feasibility calculation.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.backtest_orchestration import (
    BacktestOrchestrationRequest,
    BacktestOrchestrator,
    BacktestStatus,
    get_backtest_orchestrator,
)


# ORCHESTRATOR INITIALIZATION TESTS
class TestBacktestOrchestratorInitialization:
    def test_orchestrator_init(self):
        """Test orchestrator initialization."""
        orchestrator = BacktestOrchestrator()
        assert len(orchestrator.execution_history) == 0

    def test_orchestrator_singleton(self):
        """Test orchestrator singleton pattern."""
        o1 = get_backtest_orchestrator()
        o2 = get_backtest_orchestrator()
        assert o1 is o2

    def test_orchestrator_status(self):
        """Test orchestrator status reporting."""
        orchestrator = BacktestOrchestrator()
        status = orchestrator.get_orchestrator_status()

        assert "total_backtests" in status
        assert "successful_backtests" in status
        assert "success_rate" in status


# REQUEST VALIDATION TESTS
class TestBacktestRequestValidation:
    def test_validate_valid_request(self):
        """Test validation of valid request."""
        orchestrator = BacktestOrchestrator()
        request = BacktestOrchestrationRequest(
            profile_id="test_profile",
            input_id="user_001",
            module_parameter_set_id="params_001",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            objective="balanced_growth",
            risk_profile="moderate",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31),
        )

        errors = orchestrator._validate_request(request)
        assert len(errors) == 0

    def test_validate_negative_capital(self):
        """Test validation rejects negative capital."""
        orchestrator = BacktestOrchestrator()
        request = BacktestOrchestrationRequest(
            profile_id="test_profile",
            input_id="user_001",
            module_parameter_set_id="params_001",
            initial_capital=Decimal("-50000"),
            target_monthly_return_eur=Decimal("1000"),
            objective="balanced_growth",
            risk_profile="moderate",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31),
        )

        errors = orchestrator._validate_request(request)
        assert len(errors) > 0
        assert any("capital" in err.lower() for err in errors)

    def test_validate_invalid_date_range(self):
        """Test validation rejects invalid date range."""
        orchestrator = BacktestOrchestrator()
        request = BacktestOrchestrationRequest(
            profile_id="test_profile",
            input_id="user_001",
            module_parameter_set_id="params_001",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            objective="balanced_growth",
            risk_profile="moderate",
            start_date=date(2023, 12, 31),
            end_date=date(2022, 1, 1),  # End before start
        )

        errors = orchestrator._validate_request(request)
        assert len(errors) > 0
        assert any("date" in err.lower() for err in errors)


# FEASIBILITY RATIO TESTS
class TestFeasibilityRatioCalculation:
    def test_feasibility_ratio_approved(self):
        """Test feasibility ratio >= 1.0 is APPROVED."""
        orchestrator = BacktestOrchestrator()

        # Required: €1000/month on €250k = 4.8% annual
        # Achieved: 6% annual
        # Ratio: 6 / 4.8 = 1.25 ✅ APPROVED
        ratio = orchestrator._calculate_feasibility_ratio(
            target_monthly_return_eur=Decimal("1000"),
            initial_capital=Decimal("250000"),
            achieved_annual_return_pct=Decimal("6.0"),
        )

        assert ratio >= Decimal("1.0")
        status = orchestrator._determine_feasibility_status(ratio)
        assert status == "APPROVED"

    def test_feasibility_ratio_conditional(self):
        """Test 0.7 <= feasibility ratio < 1.0 is CONDITIONAL."""
        orchestrator = BacktestOrchestrator()

        # Required: €1000/month on €250k = 4.8% annual
        # Achieved: 3.8% annual
        # Ratio: 3.8 / 4.8 = 0.79 ⚠️ CONDITIONAL
        ratio = orchestrator._calculate_feasibility_ratio(
            target_monthly_return_eur=Decimal("1000"),
            initial_capital=Decimal("250000"),
            achieved_annual_return_pct=Decimal("3.8"),
        )

        assert Decimal("0.7") <= ratio < Decimal("1.0")
        status = orchestrator._determine_feasibility_status(ratio)
        assert status == "CONDITIONAL"

    def test_feasibility_ratio_rejected(self):
        """Test feasibility ratio < 0.7 is REJECTED."""
        orchestrator = BacktestOrchestrator()

        # Required: €1000/month on €250k = 4.8% annual
        # Achieved: 2% annual
        # Ratio: 2 / 4.8 = 0.42 ❌ REJECTED
        ratio = orchestrator._calculate_feasibility_ratio(
            target_monthly_return_eur=Decimal("1000"),
            initial_capital=Decimal("250000"),
            achieved_annual_return_pct=Decimal("2.0"),
        )

        assert ratio < Decimal("0.7")
        status = orchestrator._determine_feasibility_status(ratio)
        assert status == "REJECTED"

    def test_feasibility_ratio_zero_target(self):
        """Test feasibility ratio with zero return target."""
        orchestrator = BacktestOrchestrator()

        # Required: €0/month on €250k = 0% annual
        # Achieved: 3% annual
        # Ratio: 1.0 (any positive return satisfies zero target)
        ratio = orchestrator._calculate_feasibility_ratio(
            target_monthly_return_eur=Decimal("0"),
            initial_capital=Decimal("250000"),
            achieved_annual_return_pct=Decimal("3.0"),
        )

        assert ratio >= Decimal("1.0")

    def test_feasibility_ratio_edge_case_threshold(self):
        """Test feasibility ratio at exact threshold."""
        orchestrator = BacktestOrchestrator()

        # Test at 0.7 threshold
        ratio = orchestrator._calculate_feasibility_ratio(
            target_monthly_return_eur=Decimal("1000"),
            initial_capital=Decimal("250000"),
            achieved_annual_return_pct=Decimal("3.36"),  # Exactly 0.7x required
        )

        # Should be exactly 0.7
        assert abs(ratio - Decimal("0.7")) < Decimal("0.01")


# ORCHESTRATION TESTS
class TestBacktestOrchestration:
    @pytest.mark.asyncio
    async def test_orchestrate_successful_request(self):
        """Test orchestration of successful backtest request."""
        orchestrator = BacktestOrchestrator()
        request = BacktestOrchestrationRequest(
            profile_id="test_profile_success",
            input_id="user_success",
            module_parameter_set_id="params_success",
            initial_capital=Decimal("250000"),
            target_monthly_return_eur=Decimal("1000"),
            objective="balanced_growth",
            risk_profile="moderate",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31),
        )

        result = await orchestrator.orchestrate(request)

        assert result.success
        assert result.backtest_result is not None
        assert result.backtest_result.status == BacktestStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_orchestrate_with_invalid_request(self):
        """Test orchestration rejects invalid request."""
        orchestrator = BacktestOrchestrator()
        request = BacktestOrchestrationRequest(
            profile_id="test_profile_invalid",
            input_id="user_invalid",
            module_parameter_set_id="params_invalid",
            initial_capital=Decimal("-100"),  # Invalid
            target_monthly_return_eur=Decimal("1000"),
            objective="balanced_growth",
            risk_profile="moderate",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31),
        )

        result = await orchestrator.orchestrate(request)

        assert not result.success
        assert result.error_message

    @pytest.mark.asyncio
    async def test_orchestrate_with_different_objectives(self):
        """Test orchestration works for different objectives."""
        orchestrator = BacktestOrchestrator()
        objectives = [
            "maximizar_capital",
            "maximizar_dividendos",
            "capital_preservation",
            "balanced_growth",
            "income_generation",
        ]

        for objective in objectives:
            request = BacktestOrchestrationRequest(
                profile_id=f"test_{objective}",
                input_id=f"user_{objective}",
                module_parameter_set_id=f"params_{objective}",
                initial_capital=Decimal("250000"),
                target_monthly_return_eur=Decimal("500"),
                objective=objective,
                risk_profile="moderate",
                start_date=date(2022, 1, 1),
                end_date=date(2023, 12, 31),
            )

            result = await orchestrator.orchestrate(request)
            # Should not crash, may succeed or fail depending on backtest engine
            assert isinstance(result.feasibility_ratio, Decimal)


# BACKTEST RESULT VALIDATION TESTS
class TestBacktestResultValidation:
    def test_validate_result_good_sharpe(self):
        """Test validation accepts good Sharpe ratio."""
        orchestrator = BacktestOrchestrator()

        # Create a mock result with good Sharpe ratio
        from app.services.backtest_orchestration.models import BacktestMetrics, BacktestResult

        metrics = BacktestMetrics(
            total_return_pct=Decimal("15.0"),
            annual_return_pct=Decimal("15.0"),
            monthly_return_pct=Decimal("1.2"),
            sharpe_ratio=Decimal("2.5"),  # Good
            sortino_ratio=Decimal("3.0"),
            calmar_ratio=Decimal("2.0"),
            max_drawdown_pct=Decimal("7.5"),
            volatility_pct=Decimal("6.0"),
            var_95_pct=Decimal("4.5"),
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            win_rate_pct=Decimal("65.0"),
            avg_win_pct=Decimal("1.0"),
            avg_loss_pct=Decimal("0.6"),
            profit_factor=Decimal("2.5"),
            expectancy_pct=Decimal("0.3"),
            recovery_factor=Decimal("2.0"),
            ulcer_index=Decimal("3.0"),
            consecutive_wins=12,
            consecutive_losses=4,
        )

        result = BacktestResult(
            test_id="test_001",
            profile_id="profile_001",
            input_id="input_001",
            status=BacktestStatus.COMPLETED,
            success=True,
            metrics=metrics,
        )

        warnings = orchestrator._validate_backtest_result(result, Decimal("1.2"))
        # Should not warn about Sharpe ratio
        assert not any("sharpe" in w.lower() for w in warnings)

    def test_validate_result_low_sharpe(self):
        """Test validation warns about low Sharpe ratio."""
        orchestrator = BacktestOrchestrator()

        from app.services.backtest_orchestration.models import BacktestMetrics, BacktestResult

        metrics = BacktestMetrics(
            total_return_pct=Decimal("5.0"),
            annual_return_pct=Decimal("5.0"),
            monthly_return_pct=Decimal("0.4"),
            sharpe_ratio=Decimal("0.5"),  # Low
            sortino_ratio=Decimal("0.6"),
            calmar_ratio=Decimal("0.4"),
            max_drawdown_pct=Decimal("10.0"),
            volatility_pct=Decimal("10.0"),
            var_95_pct=Decimal("7.5"),
            total_trades=50,
            winning_trades=25,
            losing_trades=25,
            win_rate_pct=Decimal("50.0"),
            avg_win_pct=Decimal("0.5"),
            avg_loss_pct=Decimal("0.5"),
            profit_factor=Decimal("1.0"),
            expectancy_pct=Decimal("0.0"),
            recovery_factor=Decimal("0.5"),
            ulcer_index=Decimal("5.0"),
            consecutive_wins=3,
            consecutive_losses=4,
        )

        result = BacktestResult(
            test_id="test_002",
            profile_id="profile_002",
            input_id="input_002",
            status=BacktestStatus.COMPLETED,
            success=True,
            metrics=metrics,
        )

        warnings = orchestrator._validate_backtest_result(result, Decimal("1.0"))
        # Should warn about low Sharpe ratio
        assert any("sharpe" in w.lower() for w in warnings)


# HISTORY & STATUS TESTS
class TestExecutionHistoryTracking:
    @pytest.mark.asyncio
    async def test_execution_history_tracking(self):
        """Test that execution history is tracked."""
        orchestrator = BacktestOrchestrator()

        for i in range(3):
            request = BacktestOrchestrationRequest(
                profile_id=f"test_hist_{i}",
                input_id=f"user_hist_{i}",
                module_parameter_set_id=f"params_hist_{i}",
                initial_capital=Decimal("250000"),
                target_monthly_return_eur=Decimal("500"),
                objective="balanced_growth",
                risk_profile="moderate",
                start_date=date(2022, 1, 1),
                end_date=date(2023, 12, 31),
            )
            await orchestrator.orchestrate(request)

        history = await orchestrator.get_execution_history()
        assert len(history) >= 3

    @pytest.mark.asyncio
    async def test_execution_history_limit(self):
        """Test execution history with limit."""
        orchestrator = BacktestOrchestrator()

        for i in range(5):
            request = BacktestOrchestrationRequest(
                profile_id=f"test_limit_{i}",
                input_id=f"user_limit_{i}",
                module_parameter_set_id=f"params_limit_{i}",
                initial_capital=Decimal("250000"),
                target_monthly_return_eur=Decimal("500"),
                objective="balanced_growth",
                risk_profile="moderate",
                start_date=date(2022, 1, 1),
                end_date=date(2023, 12, 31),
            )
            await orchestrator.orchestrate(request)

        history = await orchestrator.get_execution_history(limit=2)
        assert len(history) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
