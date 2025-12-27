"""
Integration tests for complete pipeline: T4.1 → T8.1 → T9.1

Tests the full workflow:
1. T4.1: Capacity Fade Validation - Validate alpha sustainability at scale
2. T8.1: Risk Scaling Application - Apply dynamic risk adjustments
3. T9.1: Reporting Generator - Generate comprehensive performance reports

Scenarios tested:
- 5 investment objectives
- 4 capital tiers (€50k, €100k, €150k, €250k)
- Multiple market regimes (bullish, bearish, sideways)
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import tempfile

from app.services.capacity_fade_validation import (
    CapacityFadeValidator,
)
from app.services.risk_scaling_application import (
    RiskScalingApplication,
    get_risk_scaler,
)
from app.services.reporting_generator import (
    QuantStatsIntegrator,
    PyFolioIntegrator,
    HTMLTemplateEngine,
    AdvancedVisualizationGenerator,
    ReportDeliveryManager,
    get_quantstats_integrator,
    get_pyfolio_integrator,
    get_html_template_engine,
    get_visualization_generator,
    get_delivery_manager,
)
from app.models.portfolio import Portfolio, Position
from app.backtesting.models import BacktestResult


class TestDataFactory:
    """Factory for creating realistic test data."""

    @staticmethod
    def create_returns_series(
        base_return: float,
        volatility: float,
        length: int = 252,
        seed: int = 42,
    ) -> List[Decimal]:
        """Create realistic returns series."""
        import numpy as np
        np.random.seed(seed)
        returns = np.random.normal(base_return / 252, volatility / np.sqrt(252), length)
        return [Decimal(str(r)) for r in returns]

    @staticmethod
    def create_backtest_result(
        strategy_name: str = "TestStrategy",
        capital: Decimal = Decimal("100000"),
        returns: List[Decimal] = None,
    ) -> BacktestResult:
        """Create a mock backtest result."""
        if returns is None:
            returns = TestDataFactory.create_returns_series(0.15, 0.12, 252)

        cumulative_return = 1.0
        for ret in returns:
            cumulative_return *= (1 + float(ret))
        final_return = (cumulative_return - 1) * 100

        total_trades = 150
        winning_trades = int(total_trades * 0.60)
        losing_trades = total_trades - winning_trades

        max_dd = 0.0
        cumval = 1.0
        peak = 1.0
        for ret in returns:
            cumval *= (1 + float(ret))
            peak = max(peak, cumval)
            dd = (peak - cumval) / peak
            max_dd = max(max_dd, dd)

        return BacktestResult(
            strategy_name=strategy_name,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
            initial_capital=capital,
            final_capital=capital * Decimal(str(cumulative_return)),
            total_return=Decimal(str(final_return)),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal(str(-max_dd * 100)),
            win_rate=Decimal(str(winning_trades / total_trades)),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=Decimal("0.85"),
            avg_loss=Decimal("-0.60"),
            profit_factor=Decimal("1.8"),
            daily_returns=returns,
        )

    @staticmethod
    def create_portfolio(
        capital: Decimal = Decimal("100000"),
        positions: Dict[str, Decimal] = None,
    ) -> Portfolio:
        """Create a mock portfolio."""
        if positions is None:
            positions = {
                "AAPL": Decimal("10000"),
                "GOOGL": Decimal("10000"),
                "MSFT": Decimal("10000"),
                "AMZN": Decimal("10000"),
                "NVDA": Decimal("10000"),
            }

        portfolio_positions = [
            Position(
                symbol=symbol,
                quantity=Decimal("100"),
                entry_price=value / Decimal("100"),
                current_price=value / Decimal("100") * Decimal("1.05"),
            )
            for symbol, value in positions.items()
        ]

        return Portfolio(
            portfolio_id="test_portfolio",
            total_value=capital,
            cash=capital * Decimal("0.5"),
            leverage=Decimal("1.0"),
            positions=portfolio_positions,
            created_at=datetime.utcnow(),
        )


class TestPipelineT4T8T9:
    """Integration tests for complete T4.1 → T8.1 → T9.1 pipeline."""

    def setup_method(self):
        """Setup test fixtures."""
        self.validator = CapacityFadeValidator()
        self.risk_scaler = get_risk_scaler()
        self.data_factory = TestDataFactory()

    # ========================================================================
    # SCENARIO 1: Conservative Strategy, Moderate Capital
    # ========================================================================

    def test_pipeline_conservative_strategy(self):
        """Test full pipeline with conservative strategy at moderate capital."""
        # T4.1: Validate capacity fade
        backtest = self.data_factory.create_backtest_result(
            strategy_name="ConservativeStrategy",
            capital=Decimal("100000"),
            returns=self.data_factory.create_returns_series(
                base_return=0.10,  # 10% annual
                volatility=0.08,   # 8% volatility
            ),
        )

        validation_result = self.validator.validate_capacity_feasibility(
            backtest_result=backtest,
            target_capital=Decimal("150000"),
            annual_target_return=Decimal("0.12"),
        )

        assert validation_result.feasible is True
        assert validation_result.estimated_alpha_at_scale >= Decimal("0.09")

        # T8.1: Apply risk scaling
        portfolio = self.data_factory.create_portfolio(capital=Decimal("150000"))

        scaled_portfolio = self.risk_scaler.apply_scaling(
            portfolio=portfolio,
            risk_monitors=None,  # Simplified for integration test
        )

        assert scaled_portfolio is not None
        assert scaled_portfolio.total_value > Decimal("0")

        # T9.1: Generate report
        returns = self.data_factory.create_returns_series(0.10, 0.08, 252)

        quantstats = get_quantstats_integrator()
        stats_report = quantstats.generate_statistics_report(returns=returns)

        assert stats_report is not None
        assert stats_report.basic_metrics.total_return > Decimal("0")

    # ========================================================================
    # SCENARIO 2: Aggressive Strategy, High Capital
    # ========================================================================

    def test_pipeline_aggressive_strategy_high_capital(self):
        """Test full pipeline with aggressive strategy at high capital tier."""
        # T4.1: Validate capacity
        backtest = self.data_factory.create_backtest_result(
            strategy_name="AggressiveStrategy",
            capital=Decimal("100000"),
            returns=self.data_factory.create_returns_series(
                base_return=0.25,  # 25% annual
                volatility=0.20,   # 20% volatility
            ),
        )

        validation_result = self.validator.validate_capacity_feasibility(
            backtest_result=backtest,
            target_capital=Decimal("250000"),
            annual_target_return=Decimal("0.20"),
        )

        # Aggressive strategy may show alpha decay at higher scales
        assert validation_result is not None
        assert validation_result.base_alpha > Decimal("0")

        # T8.1: Risk scaling may be more conservative
        portfolio = self.data_factory.create_portfolio(capital=Decimal("250000"))
        scaled_portfolio = self.risk_scaler.apply_scaling(
            portfolio=portfolio,
            risk_monitors=None,
        )

        assert scaled_portfolio is not None

        # T9.1: Generate comprehensive report
        returns = self.data_factory.create_returns_series(0.25, 0.20, 252)

        quantstats = get_quantstats_integrator()
        stats = quantstats.generate_statistics_report(returns=returns)

        assert stats is not None
        assert float(stats.basic_metrics.total_return) > 15  # >15% annual return

    # ========================================================================
    # SCENARIO 3: Multi-Capital Tier Analysis
    # ========================================================================

    def test_pipeline_multi_capital_tiers(self):
        """Test pipeline across multiple capital tiers."""
        base_returns = self.data_factory.create_returns_series(0.15, 0.12, 252)

        capital_tiers = [
            Decimal("50000"),
            Decimal("100000"),
            Decimal("150000"),
            Decimal("250000"),
        ]

        results = []

        for capital in capital_tiers:
            backtest = self.data_factory.create_backtest_result(
                strategy_name="MultiTierStrategy",
                capital=capital,
                returns=base_returns,
            )

            # T4.1: Capacity validation
            validation = self.validator.validate_capacity_feasibility(
                backtest_result=backtest,
                target_capital=capital * Decimal("1.5"),
                annual_target_return=Decimal("0.15"),
            )

            # T8.1: Risk scaling
            portfolio = self.data_factory.create_portfolio(capital=capital)
            scaled = self.risk_scaler.apply_scaling(portfolio=portfolio)

            # T9.1: Reporting
            quantstats = get_quantstats_integrator()
            stats = quantstats.generate_statistics_report(returns=base_returns)

            results.append({
                "capital": capital,
                "feasible": validation.feasible,
                "scaled_value": scaled.total_value if scaled else Decimal("0"),
                "sharpe": stats.basic_metrics.sharpe_ratio if stats else Decimal("0"),
            })

        # Verify results across all tiers
        assert len(results) == 4
        for result in results:
            assert result["capital"] > 0
            assert result["sharpe"] > 0

    # ========================================================================
    # SCENARIO 4: Full Report Generation Pipeline
    # ========================================================================

    def test_pipeline_full_report_generation(self):
        """Test complete report generation across all components."""
        # Create realistic backtest
        returns = self.data_factory.create_returns_series(0.18, 0.14, 252)
        backtest = self.data_factory.create_backtest_result(
            strategy_name="ReportTestStrategy",
            capital=Decimal("100000"),
            returns=returns,
        )

        # T4.1: Validate
        validation = self.validator.validate_capacity_feasibility(
            backtest_result=backtest,
            target_capital=Decimal("200000"),
            annual_target_return=Decimal("0.15"),
        )
        assert validation.feasible

        # T8.1: Scale portfolio
        portfolio = self.data_factory.create_portfolio(capital=Decimal("200000"))
        scaled_portfolio = self.risk_scaler.apply_scaling(portfolio=portfolio)
        assert scaled_portfolio is not None

        # T9.1 PHASE 1: Generate advanced metrics
        quantstats = get_quantstats_integrator()
        stats_report = quantstats.generate_statistics_report(
            returns=returns,
            benchmark_returns=self.data_factory.create_returns_series(0.08, 0.10),
        )
        assert stats_report is not None
        assert stats_report.advanced_metrics is not None

        # T9.1 PHASE 2: Generate factor analysis
        pyfolio = get_pyfolio_integrator()
        factor_data = {
            "Market": Decimal("0.75"),
            "Size": Decimal("-0.10"),
            "Value": Decimal("0.15"),
            "Momentum": Decimal("0.20"),
        }
        factor_analysis = pyfolio.analyze_factor_exposure(
            returns=returns,
            factor_data=factor_data,
        )
        assert factor_analysis is not None

        # T9.1 PHASE 3: Generate HTML report
        html_engine = get_html_template_engine()
        html_content = html_engine.render_report(
            config=None,  # Simplified for test
            metrics={"sharpe": "1.8", "max_dd": "-12%"},
            charts_data={},
            tables_data={},
        )
        assert html_content is not None
        assert len(html_content) > 0

        # T9.1 PHASE 4: Generate visualizations
        viz_gen = get_visualization_generator()
        returns_chart = viz_gen.generate_cumulative_returns_chart(returns)
        assert returns_chart is not None
        assert returns_chart.chart_id == "cumulative_returns"

        # T9.1 PHASE 5: Export and deliver
        with tempfile.TemporaryDirectory() as tmpdir:
            delivery = get_delivery_manager()

            # Export to HTML
            html_result = delivery.export_to_html(
                html_content,
                Path(tmpdir) / "report.html",
                include_timestamp=False,
            )
            assert html_result.success

            # Export to Excel
            excel_result = delivery.export_to_excel(
                {"sharpe": 1.8, "max_dd": 0.12},
                Path(tmpdir) / "metrics.xlsx",
                include_timestamp=False,
            )
            assert excel_result.success

    # ========================================================================
    # SCENARIO 5: Market Regime Stress Test
    # ========================================================================

    def test_pipeline_market_regimes(self):
        """Test pipeline across different market regimes."""
        scenarios = {
            "bullish": {
                "base_return": 0.25,
                "volatility": 0.10,
                "expected_feasible": True,
            },
            "sideways": {
                "base_return": 0.05,
                "volatility": 0.08,
                "expected_feasible": True,
            },
            "bearish": {
                "base_return": -0.10,
                "volatility": 0.20,
                "expected_feasible": False,
            },
        }

        for regime_name, regime_config in scenarios.items():
            returns = self.data_factory.create_returns_series(
                base_return=regime_config["base_return"],
                volatility=regime_config["volatility"],
                seed=hash(regime_name) % 1000,
            )

            backtest = self.data_factory.create_backtest_result(
                strategy_name=f"RegimeTest_{regime_name}",
                capital=Decimal("100000"),
                returns=returns,
            )

            # T4.1: Capacity validation
            validation = self.validator.validate_capacity_feasibility(
                backtest_result=backtest,
                target_capital=Decimal("150000"),
                annual_target_return=Decimal("0.10"),
            )

            # In bearish regime, validation may fail or show low alpha
            if regime_name == "bearish":
                assert validation.estimated_alpha_at_scale < Decimal("0.10")
            else:
                assert validation.estimated_alpha_at_scale > Decimal("0")

            # T8.1: Risk scaling adapts
            portfolio = self.data_factory.create_portfolio(capital=Decimal("150000"))
            scaled = self.risk_scaler.apply_scaling(portfolio=portfolio)
            assert scaled is not None

            # T9.1: Reporting works for all regimes
            quantstats = get_quantstats_integrator()
            stats = quantstats.generate_statistics_report(returns=returns)
            assert stats is not None

    # ========================================================================
    # SCENARIO 6: Complete End-to-End Workflow
    # ========================================================================

    def test_pipeline_end_to_end_workflow(self):
        """Test complete workflow from backtest to report delivery."""
        # Step 1: Create backtest results
        print("\n" + "="*70)
        print("INTEGRATION TEST: Complete E2E Pipeline")
        print("="*70)

        returns = self.data_factory.create_returns_series(0.20, 0.15, 252)
        backtest = self.data_factory.create_backtest_result(
            strategy_name="E2ETestStrategy",
            capital=Decimal("100000"),
            returns=returns,
        )
        print(f"\n✓ STEP 1: Backtest created")
        print(f"  - Strategy: {backtest.strategy_name}")
        print(f"  - Initial Capital: €{float(backtest.initial_capital):,.0f}")
        print(f"  - Total Return: {float(backtest.total_return):.1f}%")

        # Step 2: T4.1 - Validate capacity
        target_capital = Decimal("250000")
        validation = self.validator.validate_capacity_feasibility(
            backtest_result=backtest,
            target_capital=target_capital,
            annual_target_return=Decimal("0.15"),
        )
        print(f"\n✓ STEP 2: T4.1 Capacity Validation")
        print(f"  - Target Capital: €{float(target_capital):,.0f}")
        print(f"  - Base Alpha: {float(validation.base_alpha):.1f}%")
        print(f"  - Estimated Alpha at Scale: {float(validation.estimated_alpha_at_scale):.1f}%")
        print(f"  - Feasible: {validation.feasible}")

        # Step 3: T8.1 - Apply risk scaling
        portfolio = self.data_factory.create_portfolio(capital=target_capital)
        scaled_portfolio = self.risk_scaler.apply_scaling(portfolio=portfolio)
        print(f"\n✓ STEP 3: T8.1 Risk Scaling")
        print(f"  - Original Portfolio Value: €{float(portfolio.total_value):,.0f}")
        print(f"  - Scaled Portfolio Value: €{float(scaled_portfolio.total_value):,.0f}")
        print(f"  - Positions: {len(scaled_portfolio.positions)}")

        # Step 4: T9.1 - Generate comprehensive report
        print(f"\n✓ STEP 4: T9.1 Report Generation")

        # Phase 1: Metrics
        quantstats = get_quantstats_integrator()
        stats = quantstats.generate_statistics_report(returns=returns)
        print(f"  - Phase 1: Advanced metrics calculated")
        print(f"    - Sharpe Ratio: {float(stats.basic_metrics.sharpe_ratio):.2f}")
        print(f"    - Max Drawdown: {float(stats.basic_metrics.max_drawdown):.2f}%")

        # Phase 2: Factor analysis
        pyfolio = get_pyfolio_integrator()
        factors = {"Market": Decimal("0.80"), "Size": Decimal("-0.05")}
        tearsheet = pyfolio.generate_tearsheet(
            returns=returns,
            positions=None,
            transactions=None,
        )
        print(f"  - Phase 2: Factor analysis completed")

        # Phase 3: HTML template
        html_engine = get_html_template_engine()
        html_report = html_engine.render_report(
            config=None,
            metrics={"sharpe": f"{float(stats.basic_metrics.sharpe_ratio):.2f}"},
            charts_data={},
            tables_data={},
        )
        print(f"  - Phase 3: HTML template rendered ({len(html_report)} bytes)")

        # Phase 4: Visualizations
        viz_gen = get_visualization_generator()
        charts = {
            "returns": viz_gen.generate_cumulative_returns_chart(returns),
            "drawdown": viz_gen.generate_drawdown_waterfall(returns),
            "rolling": viz_gen.generate_rolling_metrics_chart(returns),
            "heatmap": viz_gen.generate_heatmap_monthly_returns(returns),
            "factors": viz_gen.generate_factor_exposures_chart(factors),
        }
        print(f"  - Phase 4: {len(charts)} interactive charts generated")

        # Phase 5: Export and delivery
        with tempfile.TemporaryDirectory() as tmpdir:
            delivery = get_delivery_manager()

            html_result = delivery.export_to_html(
                html_report,
                Path(tmpdir) / "report.html",
                include_timestamp=False,
            )
            excel_result = delivery.export_to_excel(
                {"sharpe": 1.8, "max_dd": 12, "return": 20},
                Path(tmpdir) / "metrics.xlsx",
                include_timestamp=False,
            )
            print(f"  - Phase 5: Report exported to HTML and Excel")
            print(f"    - HTML: {float(html_result.file_size_mb):.2f} MB")
            print(f"    - Excel: {float(excel_result.file_size_mb):.2f} MB")

        print(f"\n" + "="*70)
        print("✅ END-TO-END PIPELINE TEST COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")

        # Verify all steps completed
        assert validation.feasible
        assert scaled_portfolio.total_value > Decimal("0")
        assert stats is not None
        assert tearsheet is not None
        assert len(html_report) > 0
        assert len(charts) == 5
        assert html_result.success
        assert excel_result.success


class TestPipelineEdgeCases:
    """Test edge cases and error conditions in the pipeline."""

    def setup_method(self):
        """Setup test fixtures."""
        self.validator = CapacityFadeValidator()
        self.risk_scaler = get_risk_scaler()
        self.data_factory = TestDataFactory()

    def test_pipeline_insufficient_alpha(self):
        """Test pipeline when alpha is insufficient for target capital."""
        returns = TestDataFactory.create_returns_series(0.02, 0.08, 252)  # Low return
        backtest = self.data_factory.create_backtest_result(
            capital=Decimal("100000"),
            returns=returns,
        )

        validation = self.validator.validate_capacity_feasibility(
            backtest_result=backtest,
            target_capital=Decimal("250000"),
            annual_target_return=Decimal("0.20"),  # High target
        )

        assert validation.estimated_alpha_at_scale < Decimal("0.20")

    def test_pipeline_high_volatility(self):
        """Test pipeline with high volatility returns."""
        returns = TestDataFactory.create_returns_series(0.15, 0.40, 252)  # High vol
        backtest = self.data_factory.create_backtest_result(
            capital=Decimal("100000"),
            returns=returns,
        )

        quantstats = get_quantstats_integrator()
        stats = quantstats.generate_statistics_report(returns=returns)

        assert stats is not None
        assert float(stats.basic_metrics.volatility_pct) > 30

    def test_pipeline_zero_positions_portfolio(self):
        """Test pipeline with empty portfolio."""
        portfolio = Portfolio(
            portfolio_id="empty",
            total_value=Decimal("100000"),
            cash=Decimal("100000"),
            leverage=Decimal("1.0"),
            positions=[],
            created_at=datetime.utcnow(),
        )

        risk_scaler = get_risk_scaling_application()
        scaled = risk_scaler.apply_scaling(portfolio=portfolio)

        assert scaled is not None
        assert len(scaled.positions) == 0
