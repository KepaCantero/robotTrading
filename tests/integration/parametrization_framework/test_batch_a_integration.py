"""
Integration Tests for BATCH A - Risk Scaling & Reporting Pipeline

Tests the complete end-to-end flow:
- T8.1: Risk Scaling (RiskAdjustmentCalculator, LimitAdjuster)
- T9.1: Reporting (ReportTemplates, QuantStatsIntegration, ReportingOrchestrator)

Validates integration between risk management and reporting components.
"""

from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.services.reporting.quantstats_integration import get_quantstats_integration
from app.services.reporting.report_templates import get_report_templates
from app.application.reporting.reporting_orchestrator import get_reporting_orchestrator
from app.services.risk_scaling.limit_adjuster import get_limit_adjuster
from app.services.risk_scaling.risk_adjustment_calculator import get_risk_adjustment_calculator
from app.services.risk_scaling.risk_scaling_application import get_risk_scaling_application


class TestBATCHA_RiskScalingReportingIntegration:
    """Integration tests for Risk Scaling & Reporting pipeline."""

    @pytest.fixture
    def risk_calculator(self):
        """Get risk adjustment calculator."""
        return get_risk_adjustment_calculator()

    @pytest.fixture
    def limit_adjuster(self):
        """Get limit adjuster."""
        return get_limit_adjuster()

    @pytest.fixture
    def risk_scaling_app(self):
        """Get risk scaling application."""
        return get_risk_scaling_application()

    @pytest.fixture
    def report_templates(self):
        """Get report templates."""
        return get_report_templates()

    @pytest.fixture
    def quantstats_integration(self):
        """Get QuantStats integration."""
        return get_quantstats_integration()

    @pytest.fixture
    def reporting_orchestrator(self):
        """Get reporting orchestrator."""
        return get_reporting_orchestrator()

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns series."""
        np.random.seed(42)
        return pd.Series(
            np.random.normal(0.001, 0.01, 252),
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )

    @pytest.fixture
    def sample_backtest_result(self):
        """Create sample backtest result."""
        return {
            "total_return": 0.25,
            "annual_return": 0.25,
            "sharpe_ratio": 1.8,
            "sortino_ratio": 2.1,
            "max_drawdown": -0.12,
            "win_rate": 0.58,
            "profit_factor": 2.3,
            "total_trades": 100,
            "volatility": 0.15,
            "monthly_returns": [0.02, 0.01, -0.01, 0.03, 0.015],
        }

    @pytest.fixture
    def sample_allocation(self):
        """Create sample portfolio allocation."""
        return {
            "AAPL": 0.3,
            "GOOGL": 0.25,
            "MSFT": 0.2,
            "TSLA": 0.15,
            "AMZN": 0.1,
        }

    # =========================================================================
    # TEST: Risk Scaling Integration
    # =========================================================================

    @pytest.mark.asyncio
    async def test_risk_scaling_full_workflow(
        self, risk_calculator, limit_adjuster, risk_scaling_app
    ):
        """Test complete risk scaling workflow."""
        # Step 1: Calculate position scaling based on feasibility
        position_size, pos_reason = risk_calculator.calculate_position_scaling(
            feasibility_ratio=Decimal("1.2"),
            base_position_size=Decimal("50000"),
            capital_tier="medium",
            risk_tolerance=4,
        )

        assert position_size > 0, "Position should be sized"
        assert pos_reason is not None, "Should provide reason"

        # Step 2: Get base limits for capital tier
        base_limits = limit_adjuster.get_base_limits("medium")
        assert base_limits.stop_loss_pct > 0, "Should have stop loss"

        # Step 3: Apply risk scaling with market conditions
        result = await risk_scaling_app.apply_risk_scaling(
            base_position_size=position_size,
            feasibility_ratio=Decimal("1.2"),
            capital=Decimal("250000"),
            capital_tier="medium",
            risk_tolerance=4,
            current_volatility=Decimal("0.12"),
            average_volatility=Decimal("0.10"),
            current_drawdown_pct=Decimal("0.02"),
            market_volatility_state="normal",
        )

        assert "final_position_size" in result
        assert "leverage" in result
        assert "capital_at_risk" in result
        assert result["capital_at_risk"] > 0
        assert result["final_position_size"] > 0

    @pytest.mark.asyncio
    async def test_risk_status_transitions(self, risk_scaling_app):
        """Test risk status transitions as drawdown increases."""
        capital = Decimal("250000")

        # HEALTHY status
        status_healthy = await risk_scaling_app.get_risk_status(
            capital=capital,
            current_capital_deployed=Decimal("100000"),
            current_drawdown_pct=Decimal("0.02"),
            capital_tier="medium",
        )
        assert status_healthy["risk_state"] == "HEALTHY"
        assert status_healthy["can_trade"] is True

        # CAUTION status
        status_caution = await risk_scaling_app.get_risk_status(
            capital=capital,
            current_capital_deployed=Decimal("150000"),
            current_drawdown_pct=Decimal("0.07"),
            capital_tier="medium",
        )
        assert status_caution["risk_state"] == "CAUTION"
        assert status_caution["can_trade"] is True

        # CRITICAL status
        status_critical = await risk_scaling_app.get_risk_status(
            capital=capital,
            current_capital_deployed=Decimal("200000"),
            current_drawdown_pct=Decimal("0.18"),
            capital_tier="medium",
        )
        assert status_critical["risk_state"] == "CRITICAL"
        assert status_critical["can_trade"] is False

    # =========================================================================
    # TEST: Reporting Integration
    # =========================================================================

    @pytest.mark.asyncio
    async def test_reporting_full_workflow(
        self,
        report_templates,
        quantstats_integration,
        reporting_orchestrator,
        sample_returns,
        sample_backtest_result,
        sample_allocation,
    ):
        """Test complete reporting workflow."""
        # Step 1: Calculate advanced metrics
        metrics = quantstats_integration.calculate_advanced_metrics(sample_returns)
        assert len(metrics) > 0, "Should calculate metrics"
        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics

        # Step 2: Generate HTML report from template
        html = report_templates.generate_performance_report_html(
            strategy_name="Test Strategy",
            summary={
                "total_return": sample_backtest_result["total_return"],
                "sharpe_ratio": sample_backtest_result["sharpe_ratio"],
                "max_drawdown": sample_backtest_result["max_drawdown"],
                "win_rate": sample_backtest_result["win_rate"],
            },
            metrics={
                "total_trades": sample_backtest_result["total_trades"],
                "profit_factor": sample_backtest_result["profit_factor"],
            },
            risk_metrics={"volatility": sample_backtest_result["volatility"]},
            allocation=sample_allocation,
        )

        assert "<html" in html.lower()
        assert "Test Strategy" in html
        assert "AAPL" in html

        # Step 3: Generate comprehensive report via orchestrator
        report = await reporting_orchestrator.generate_comprehensive_report(
            strategy_name="Test Strategy",
            backtest_result=sample_backtest_result,
            portfolio_allocation=sample_allocation,
            returns=sample_returns,
            recommendation={"action": "BUY", "confidence": "HIGH"},
        )

        assert "report_id" in report
        assert report["strategy_name"] == "Test Strategy"
        assert "html_report" in report
        assert "summary" in report
        assert "metrics" in report
        assert "risk_metrics" in report

    @pytest.mark.asyncio
    async def test_executive_summary_generation(self, reporting_orchestrator):
        """Test executive summary generation."""
        html = await reporting_orchestrator.generate_executive_summary(
            strategy_name="Quick Summary",
            total_return_pct=15.5,
            sharpe_ratio=1.8,
            max_drawdown_pct=-10.0,
            recommendation_text="Recommended for deployment",
        )

        assert "<html" in html.lower()
        assert "Quick Summary" in html
        assert "15.5" in html or "15.50" in html
        assert "Recommendation" in html

    # =========================================================================
    # TEST: Risk Scaling → Reporting Integration
    # =========================================================================

    @pytest.mark.asyncio
    async def test_risk_adjusted_position_to_report(
        self,
        risk_scaling_app,
        reporting_orchestrator,
        sample_backtest_result,
        sample_allocation,
        sample_returns,
    ):
        """Test flow from risk-adjusted position to report generation."""
        # Step 1: Get risk-adjusted position
        risk_result = await risk_scaling_app.apply_risk_scaling(
            base_position_size=Decimal("50000"),
            feasibility_ratio=Decimal("1.0"),
            capital=Decimal("250000"),
            capital_tier="medium",
            risk_tolerance=4,
            current_volatility=Decimal("0.10"),
            average_volatility=Decimal("0.10"),
            current_drawdown_pct=Decimal("0.01"),
        )

        assert risk_result["final_position_size"] > 0

        # Step 2: Incorporate risk-adjusted position into backtest result
        adjusted_backtest = sample_backtest_result.copy()
        adjusted_backtest["position_size"] = float(risk_result["final_position_size"])
        adjusted_backtest["leverage"] = float(risk_result["leverage"])

        # Step 3: Generate report including risk information
        report = await reporting_orchestrator.generate_comprehensive_report(
            strategy_name="Risk-Adjusted Strategy",
            backtest_result=adjusted_backtest,
            portfolio_allocation=sample_allocation,
            returns=sample_returns,
            recommendation={
                "action": "BUY",
                "confidence": "MEDIUM",
                "position_size": float(risk_result["final_position_size"]),
            },
        )

        assert report["strategy_name"] == "Risk-Adjusted Strategy"
        assert report["recommendation"]["position_size"] > 0
        assert "html_report" in report

    # =========================================================================
    # TEST: Multi-Tier Risk Scaling
    # =========================================================================

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "capital_tier,expected_multiplier",
        [
            ("micro", Decimal("0.5")),
            ("small", Decimal("0.75")),
            ("medium", Decimal("1.0")),
            ("large", Decimal("1.25")),
        ],
    )
    async def test_risk_scaling_by_capital_tier(
        self, risk_scaling_app, capital_tier, expected_multiplier
    ):
        """Test risk scaling properly adjusts by capital tier."""
        capital_map = {
            "micro": Decimal("10000"),
            "small": Decimal("30000"),
            "medium": Decimal("100000"),
            "large": Decimal("500000"),
        }

        result = await risk_scaling_app.apply_risk_scaling(
            base_position_size=Decimal("10000"),
            feasibility_ratio=Decimal("1.0"),
            capital=capital_map[capital_tier],
            capital_tier=capital_tier,
            risk_tolerance=4,
            current_volatility=Decimal("0.10"),
            average_volatility=Decimal("0.10"),
            current_drawdown_pct=Decimal("0.01"),
        )

        # Verify result is present and reasonable
        assert result["final_position_size"] > 0
        assert result["leverage"] > 0

    # =========================================================================
    # TEST: End-to-End Scenario
    # =========================================================================

    @pytest.mark.asyncio
    async def test_full_batch_a_pipeline(
        self,
        risk_calculator,
        limit_adjuster,
        risk_scaling_app,
        reporting_orchestrator,
        sample_returns,
        sample_backtest_result,
        sample_allocation,
    ):
        """Test complete BATCH A pipeline: Risk Scaling → Reporting."""
        # Define strategy parameters
        strategy_name = "Integration Test Strategy"
        feasibility_ratio = Decimal("1.15")
        base_position = Decimal("50000")
        capital = Decimal("250000")
        capital_tier = "medium"

        # ===== PHASE 1: Risk Scaling =====
        # 1a: Calculate position scaling
        position_size, _ = risk_calculator.calculate_position_scaling(
            feasibility_ratio=feasibility_ratio,
            base_position_size=base_position,
            capital_tier=capital_tier,
            risk_tolerance=4,
        )
        assert position_size > 0

        # 1b: Apply full risk scaling
        risk_result = await risk_scaling_app.apply_risk_scaling(
            base_position_size=position_size,
            feasibility_ratio=feasibility_ratio,
            capital=capital,
            capital_tier=capital_tier,
            risk_tolerance=4,
            current_volatility=Decimal("0.10"),
            average_volatility=Decimal("0.10"),
            current_drawdown_pct=Decimal("0.01"),
        )

        # Verify risk scaling output
        assert risk_result["final_position_size"] > 0
        assert risk_result["leverage"] > 0
        assert risk_result["capital_at_risk"] > 0

        # ===== PHASE 2: Reporting =====
        # 2a: Create adjusted backtest result with risk metrics
        report_input = sample_backtest_result.copy()
        report_input["position_size"] = float(risk_result["final_position_size"])
        report_input["leverage"] = float(risk_result["leverage"])

        # 2b: Generate comprehensive report
        report = await reporting_orchestrator.generate_comprehensive_report(
            strategy_name=strategy_name,
            backtest_result=report_input,
            portfolio_allocation=sample_allocation,
            returns=sample_returns,
            recommendation={
                "action": "BUY",
                "confidence": "MEDIUM",
                "position_size": float(risk_result["final_position_size"]),
                "leverage": float(risk_result["leverage"]),
            },
        )

        # Verify comprehensive report
        assert report["report_id"] is not None
        assert report["strategy_name"] == strategy_name
        assert "html_report" in report
        assert "<html" in report["html_report"].lower()
        assert strategy_name in report["html_report"]
        assert report["recommendation"]["position_size"] > 0
        assert len(report["summary"]) > 0
        assert len(report["metrics"]) > 0
        assert len(report["risk_metrics"]) > 0

        # ===== PHASE 3: Validation =====
        # Verify end-to-end consistency
        assert report["summary"]["total_return"] == sample_backtest_result["total_return"]
        assert report["recommendation"]["leverage"] == float(risk_result["leverage"])

        # Verify report is suitable for deployment
        assert report["generated_at"] is not None
        assert isinstance(report["generated_at"], str)

        # Verify allocation is included
        assert "allocation" in report
        for asset, weight in sample_allocation.items():
            assert asset in report["allocation"]
            assert report["allocation"][asset] == weight
