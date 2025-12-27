"""Unit tests for T9.1 PyFolioIntegrator component"""

from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from app.services.reporting_generator.pyfolio_integrator import (
    CapacityFade,
    FactorAnalysis,
    FactorExposure,
    PositionConcentration,
    PyFolioIntegrator,
    Tearsheet,
    get_pyfolio_integrator,
)


class TestFactorExposure:
    """Test FactorExposure data class."""

    def test_initialization(self):
        """Test factor exposure initialization."""
        exposure = FactorExposure(
            factor_name="Market",
            coefficient=Decimal("1.2"),
            t_stat=Decimal("5.5"),
            p_value=Decimal("0.001"),
            significant=True,
        )

        assert exposure.factor_name == "Market"
        assert exposure.coefficient == Decimal("1.2")
        assert exposure.significant is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        exposure = FactorExposure(
            factor_name="Momentum",
            coefficient=Decimal("0.5"),
            t_stat=Decimal("2.1"),
            p_value=Decimal("0.05"),
            significant=True,
        )

        result_dict = exposure.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["factor_name"] == "Momentum"
        assert result_dict["coefficient"] == 0.5
        assert isinstance(result_dict["t_stat"], float)


class TestFactorAnalysis:
    """Test FactorAnalysis data class."""

    def test_initialization(self):
        """Test factor analysis initialization."""
        analysis = FactorAnalysis(
            analysis_date=datetime.utcnow(),
            num_periods=252,
            residual_return_pct=Decimal("2.5"),
            model_r_squared=Decimal("0.75"),
        )

        assert analysis.num_periods == 252
        assert analysis.residual_return_pct == Decimal("2.5")
        assert len(analysis.factors) == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        analysis = FactorAnalysis(
            analysis_date=datetime.utcnow(),
            num_periods=252,
            factors=[
                FactorExposure(
                    factor_name="Market",
                    coefficient=Decimal("1.0"),
                    t_stat=Decimal("10"),
                    p_value=Decimal("0.001"),
                    significant=True,
                )
            ],
            residual_return_pct=Decimal("1.5"),
            model_r_squared=Decimal("0.85"),
        )

        result_dict = analysis.to_dict()

        assert isinstance(result_dict, dict)
        assert "factors" in result_dict
        assert len(result_dict["factors"]) == 1
        assert result_dict["model_r_squared"] == 0.85


class TestPositionConcentration:
    """Test PositionConcentration data class."""

    def test_initialization(self):
        """Test position concentration initialization."""
        concentration = PositionConcentration(
            largest_position_pct=Decimal("35"),
            herfindahl_index=Decimal("0.15"),
            effective_num_positions=Decimal("6.7"),
            top_5_concentration_pct=Decimal("75"),
            diversification_ratio=Decimal("1.4"),
        )

        assert concentration.largest_position_pct == Decimal("35")
        assert concentration.herfindahl_index == Decimal("0.15")

    def test_to_dict(self):
        """Test conversion to dictionary."""
        concentration = PositionConcentration(
            largest_position_pct=Decimal("40"),
            herfindahl_index=Decimal("0.18"),
            effective_num_positions=Decimal("5.5"),
            top_5_concentration_pct=Decimal("80"),
            diversification_ratio=Decimal("1.3"),
        )

        result_dict = concentration.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["largest_position_pct"] == 40.0
        assert isinstance(result_dict["herfindahl_index"], float)


class TestCapacityFade:
    """Test CapacityFade data class."""

    def test_initialization(self):
        """Test capacity fade initialization."""
        fade = CapacityFade(
            backtest_period="2023-2024",
            backtest_ann_return_pct=Decimal("15"),
            backtest_sharpe=Decimal("1.5"),
            simulated_current_return_pct=Decimal("14"),
            simulated_target_return_pct=Decimal("12"),
            fade_ratio=Decimal("0.8"),
            projected_feasible=True,
            confidence_level="high",
        )

        assert fade.backtest_period == "2023-2024"
        assert fade.projected_feasible is True
        assert len(fade.constraints) == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        fade = CapacityFade(
            backtest_period="2024",
            backtest_ann_return_pct=Decimal("10"),
            backtest_sharpe=Decimal("1.0"),
            simulated_current_return_pct=Decimal("9"),
            simulated_target_return_pct=Decimal("7"),
            fade_ratio=Decimal("0.7"),
            projected_feasible=False,
            confidence_level="medium",
            constraints=["Liquidity constraint"],
        )

        result_dict = fade.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["backtest_ann_return_pct"] == 10.0
        assert result_dict["projected_feasible"] is False
        assert "Liquidity constraint" in result_dict["constraints"]


class TestTearsheet:
    """Test Tearsheet data class."""

    def test_initialization(self):
        """Test tearsheet initialization."""
        tearsheet = Tearsheet(
            generation_date=datetime.utcnow(),
            strategy_name="Momentum",
            period_start=datetime.utcnow() - timedelta(days=252),
            period_end=datetime.utcnow(),
            total_return_pct=Decimal("15"),
            annual_return_pct=Decimal("15"),
            annual_volatility_pct=Decimal("10"),
            sharpe_ratio=Decimal("1.5"),
            calmar_ratio=Decimal("1.2"),
            sortino_ratio=Decimal("2.0"),
            max_drawdown_pct=Decimal("12"),
            win_rate_pct=Decimal("55"),
        )

        assert tearsheet.strategy_name == "Momentum"
        assert tearsheet.annual_return_pct == Decimal("15")

    def test_to_dict(self):
        """Test conversion to dictionary."""
        tearsheet = Tearsheet(
            generation_date=datetime.utcnow(),
            strategy_name="Test",
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow(),
            total_return_pct=Decimal("20"),
            annual_return_pct=Decimal("20"),
            annual_volatility_pct=Decimal("12"),
            sharpe_ratio=Decimal("1.67"),
            calmar_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("2.5"),
            max_drawdown_pct=Decimal("15"),
            win_rate_pct=Decimal("60"),
        )

        result_dict = tearsheet.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["annual_return_pct"] == 20.0
        assert "strategy_name" in result_dict


class TestPyFolioIntegrator:
    """Test PyFolioIntegrator component."""

    def setup_method(self):
        """Setup test fixtures."""
        self.integrator = PyFolioIntegrator()
        # Generate sample returns data (252 days)
        np.random.seed(42)
        self.returns = [Decimal(str(r)) for r in np.random.normal(0.0005, 0.01, 252)]
        self.strategy_name = "TestStrategy"

    def test_initialization(self):
        """Test integrator initialization."""
        assert self.integrator.tearsheets_generated == 0
        assert self.integrator.analysis_completed == 0

    # Tearsheet Tests
    def test_generate_tearsheet_basic(self):
        """Test basic tearsheet generation."""
        tearsheet = self.integrator.generate_tearsheet(
            strategy_name=self.strategy_name,
            returns=self.returns,
            annual_return_pct=Decimal("12"),
            annual_volatility_pct=Decimal("10"),
            sharpe_ratio=Decimal("1.2"),
            max_drawdown_pct=Decimal("15"),
        )

        assert tearsheet.strategy_name == self.strategy_name
        assert tearsheet.annual_return_pct == Decimal("12")
        assert len(tearsheet.monthly_returns) > 0

    def test_generate_tearsheet_increments_counter(self):
        """Test that tearsheet generation increments counter."""
        initial_count = self.integrator.tearsheets_generated

        self.integrator.generate_tearsheet(
            strategy_name="Test1",
            returns=self.returns,
            annual_return_pct=Decimal("10"),
            annual_volatility_pct=Decimal("8"),
            sharpe_ratio=Decimal("1.25"),
        )

        assert self.integrator.tearsheets_generated == initial_count + 1

    def test_generate_tearsheet_multiple_generations(self):
        """Test multiple tearsheet generations."""
        for i in range(3):
            self.integrator.generate_tearsheet(
                strategy_name=f"Strategy_{i}",
                returns=self.returns,
                annual_return_pct=Decimal("10") + Decimal(str(i)),
                annual_volatility_pct=Decimal("8"),
                sharpe_ratio=Decimal("1.2"),
            )

        assert self.integrator.tearsheets_generated == 3

    def test_generate_tearsheet_with_positions(self):
        """Test tearsheet generation with position data."""
        positions = [
            {"name": "AAPL", "value": 5000},
            {"name": "GOOGL", "value": 3000},
            {"name": "MSFT", "value": 2000},
        ]

        tearsheet = self.integrator.generate_tearsheet(
            strategy_name="Concentrated",
            returns=self.returns,
            positions=positions,
            annual_return_pct=Decimal("15"),
            annual_volatility_pct=Decimal("12"),
            sharpe_ratio=Decimal("1.25"),
        )

        assert tearsheet.position_concentration is not None
        assert tearsheet.position_concentration.largest_position_pct > Decimal("0")

    def test_generate_tearsheet_empty_positions(self):
        """Test tearsheet with empty positions."""
        tearsheet = self.integrator.generate_tearsheet(
            strategy_name="NoPositions",
            returns=self.returns,
            positions=[],
            annual_return_pct=Decimal("10"),
            annual_volatility_pct=Decimal("8"),
            sharpe_ratio=Decimal("1.1"),
        )

        assert tearsheet.position_concentration is None

    def test_generate_tearsheet_defaults_missing_metrics(self):
        """Test that missing metrics get default values."""
        tearsheet = self.integrator.generate_tearsheet(
            strategy_name="Minimal",
            returns=self.returns,
        )

        assert tearsheet.annual_return_pct == Decimal("0")
        assert tearsheet.sharpe_ratio == Decimal("0")
        assert tearsheet.strategy_name == "Minimal"

    # Factor Analysis Tests
    def test_analyze_factor_exposure_no_factors(self):
        """Test factor analysis with no factors provided."""
        analysis = self.integrator.analyze_factor_exposure(returns=self.returns, factor_data={})

        assert analysis.num_periods == len(self.returns)
        assert len(analysis.factors) == 0

    def test_analyze_factor_exposure_single_factor(self):
        """Test factor analysis with single factor."""
        market_factor = np.random.normal(0.0003, 0.01, len(self.returns))

        analysis = self.integrator.analyze_factor_exposure(
            returns=self.returns,
            factor_data={"Market": market_factor.tolist()},
        )

        assert len(analysis.factors) == 1
        assert analysis.factors[0].factor_name == "Market"
        assert analysis.model_r_squared >= Decimal("0")
        assert analysis.model_r_squared <= Decimal("1")

    def test_analyze_factor_exposure_multiple_factors(self):
        """Test factor analysis with multiple factors."""
        market_factor = np.random.normal(0.0003, 0.01, len(self.returns))
        size_factor = np.random.normal(0.0001, 0.008, len(self.returns))
        momentum_factor = np.random.normal(0.0002, 0.009, len(self.returns))

        analysis = self.integrator.analyze_factor_exposure(
            returns=self.returns,
            factor_data={
                "Market": market_factor.tolist(),
                "Size": size_factor.tolist(),
                "Momentum": momentum_factor.tolist(),
            },
        )

        assert len(analysis.factors) == 3
        assert len(analysis.factor_contribution_pct) == 3

    def test_analyze_factor_exposure_significance_testing(self):
        """Test that significance testing works."""
        # Create highly correlated factor (convert Decimal to float for numpy operations)
        returns_float = [float(r) for r in self.returns]
        highly_correlated = [r * 0.9 for r in returns_float]

        analysis = self.integrator.analyze_factor_exposure(
            returns=self.returns,
            factor_data={"CorrelatedFactor": highly_correlated},
            confidence_level=0.95,
        )

        assert len(analysis.factors) == 1
        # Highly correlated factor should have low p-value (significant)
        assert analysis.factors[0].p_value < Decimal("0.2")

    # Position Concentration Tests
    def test_calculate_position_concentration_concentrated(self):
        """Test concentration metrics for concentrated portfolio."""
        positions = [
            {"value": 5000},
            {"value": 3000},
            {"value": 1000},
            {"value": 500},
            {"value": 500},
        ]

        concentration = self.integrator.calculate_position_concentration(positions)

        assert concentration.largest_position_pct == Decimal("50")
        assert concentration.herfindahl_index > Decimal("0.1")
        assert concentration.effective_num_positions < Decimal("5")

    def test_calculate_position_concentration_diversified(self):
        """Test concentration metrics for diversified portfolio."""
        positions = [
            {"value": 2000},
            {"value": 2000},
            {"value": 2000},
            {"value": 2000},
            {"value": 2000},
        ]

        concentration = self.integrator.calculate_position_concentration(positions)

        assert concentration.largest_position_pct == Decimal("20")
        # Use approximate equality due to floating point precision
        assert abs(float(concentration.herfindahl_index) - 0.2) < 0.0001
        assert abs(float(concentration.effective_num_positions) - 5.0) < 0.0001

    def test_calculate_position_concentration_empty(self):
        """Test concentration with empty positions."""
        concentration = self.integrator.calculate_position_concentration([])

        assert concentration.largest_position_pct == Decimal("0")
        assert concentration.effective_num_positions == Decimal("0")

    def test_calculate_position_concentration_single_position(self):
        """Test concentration with single position."""
        positions = [{"value": 10000}]

        concentration = self.integrator.calculate_position_concentration(positions)

        assert concentration.largest_position_pct == Decimal("100")
        assert concentration.herfindahl_index == Decimal("1")
        assert concentration.effective_num_positions == Decimal("1")

    def test_calculate_position_concentration_top_5(self):
        """Test top 5 concentration calculation."""
        positions = [
            {"value": 3000},
            {"value": 2500},
            {"value": 2000},
            {"value": 1500},
            {"value": 1000},
            {"value": 500},
            {"value": 500},
        ]

        concentration = self.integrator.calculate_position_concentration(positions)

        # Top 5: 3000 + 2500 + 2000 + 1500 + 1000 = 10000 out of 11000 = 90.9%
        assert concentration.top_5_concentration_pct > Decimal("85")
        assert concentration.top_5_concentration_pct < Decimal("95")

    # Capacity Fade Tests
    def test_analyze_capacity_fade_no_live_data(self):
        """Test capacity fade with backtest data only."""
        fade = self.integrator.analyze_capacity_fade(
            backtest_returns=self.returns,
            backtest_capital=Decimal("100000"),
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
            required_return_pct=Decimal("3.9"),
        )

        assert fade.backtest_period == "Historical"
        assert fade.backtest_ann_return_pct is not None
        assert fade.fade_ratio is not None

    def test_analyze_capacity_fade_with_live_data(self):
        """Test capacity fade with live trading data."""
        live_returns = [Decimal(str(r)) for r in np.random.normal(0.0003, 0.008, 60)]

        fade = self.integrator.analyze_capacity_fade(
            backtest_returns=self.returns,
            live_returns=live_returns,
            backtest_capital=Decimal("100000"),
            current_capital=Decimal("120000"),
            target_capital=Decimal("250000"),
            required_return_pct=Decimal("3.9"),
        )

        assert fade.simulated_current_return_pct > Decimal("0")
        assert fade.simulated_target_return_pct > Decimal("0")
        # With 60 live returns, confidence should be "high"
        assert fade.confidence_level == "high"

    def test_analyze_capacity_fade_feasibility(self):
        """Test capacity fade feasibility assessment."""
        # High return scenario
        positive_returns = [Decimal("0.001") for _ in range(252)]

        fade_high = self.integrator.analyze_capacity_fade(
            backtest_returns=positive_returns,
            backtest_capital=Decimal("100000"),
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
            required_return_pct=Decimal("2.0"),
        )

        assert fade_high.projected_feasible is True

    def test_analyze_capacity_fade_zero_returns(self):
        """Test capacity fade with zero returns."""
        zero_returns = [Decimal("0") for _ in range(252)]

        fade = self.integrator.analyze_capacity_fade(
            backtest_returns=zero_returns,
            backtest_capital=Decimal("100000"),
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
            required_return_pct=Decimal("3.9"),
        )

        assert fade.backtest_ann_return_pct == Decimal("0")
        assert fade.fade_ratio == Decimal("0")

    def test_analyze_capacity_fade_constraints(self):
        """Test that constraints are identified."""
        fade = self.integrator.analyze_capacity_fade(
            backtest_returns=self.returns,
            backtest_capital=Decimal("100000"),
            current_capital=Decimal("100000"),
            target_capital=Decimal("500000"),
            required_return_pct=Decimal("10.0"),  # High requirement
        )

        assert len(fade.constraints) > 0

    # Status Tests
    def test_get_integrator_status(self):
        """Test integrator status reporting."""
        status = self.integrator.get_integrator_status()

        assert status["status"] == "operational"
        assert "tearsheets_generated" in status
        assert "analyses_completed" in status
        assert "last_update" in status

    # Singleton Tests
    def test_singleton_pattern(self):
        """Test singleton pattern for integrator."""
        integrator1 = get_pyfolio_integrator()
        integrator2 = get_pyfolio_integrator()

        assert integrator1 is integrator2

    # Integration Tests
    def test_full_workflow_tearsheet_and_analysis(self):
        """Test complete workflow: tearsheet + factor analysis + concentration."""
        # Generate tearsheet
        tearsheet = self.integrator.generate_tearsheet(
            strategy_name="CompleteWorkflow",
            returns=self.returns,
            annual_return_pct=Decimal("12"),
            annual_volatility_pct=Decimal("10"),
            sharpe_ratio=Decimal("1.2"),
            calmar_ratio=Decimal("0.8"),
            sortino_ratio=Decimal("1.8"),
            max_drawdown_pct=Decimal("15"),
            win_rate_pct=Decimal("55"),
        )

        # Add factor analysis
        market_factor = np.random.normal(0.0003, 0.01, len(self.returns))
        factor_analysis = self.integrator.analyze_factor_exposure(
            returns=self.returns,
            factor_data={"Market": market_factor.tolist()},
        )

        # Add position concentration
        positions = [
            {"value": 4000},
            {"value": 3000},
            {"value": 2000},
            {"value": 1000},
        ]
        concentration = self.integrator.calculate_position_concentration(positions)

        # Add capacity fade analysis
        fade = self.integrator.analyze_capacity_fade(
            backtest_returns=self.returns,
            backtest_capital=Decimal("100000"),
            current_capital=Decimal("100000"),
            target_capital=Decimal("250000"),
        )

        # Verify all components
        assert tearsheet.annual_return_pct == Decimal("12")
        assert len(factor_analysis.factors) == 1
        assert concentration.largest_position_pct == Decimal("40")
        assert fade.fade_ratio is not None

    # Edge Cases
    def test_generate_tearsheet_short_returns(self):
        """Test tearsheet with minimal returns data."""
        short_returns = [Decimal("0.001") for _ in range(10)]

        tearsheet = self.integrator.generate_tearsheet(
            strategy_name="Short",
            returns=short_returns,
            annual_return_pct=Decimal("5"),
            annual_volatility_pct=Decimal("5"),
        )

        assert tearsheet.strategy_name == "Short"
        assert len(tearsheet.monthly_returns) == 0  # Too short for monthly

    def test_analyze_factor_exposure_mismatched_lengths(self):
        """Test factor analysis with mismatched return/factor lengths."""
        short_factor = np.random.normal(0, 0.01, len(self.returns) - 10)

        # Should handle gracefully
        with pytest.raises(Exception):
            self.integrator.analyze_factor_exposure(
                returns=self.returns,
                factor_data={"ShortFactor": short_factor.tolist()},
            )

    def test_position_concentration_zero_values(self):
        """Test concentration with zero-value positions."""
        positions = [
            {"value": 0},
            {"value": 5000},
            {"value": 0},
            {"value": 5000},
        ]

        concentration = self.integrator.calculate_position_concentration(positions)

        # Should only count non-zero positions
        assert concentration.effective_num_positions == Decimal("2")

    def test_capacity_fade_large_capital_jump(self):
        """Test capacity fade with very large capital increase."""
        fade = self.integrator.analyze_capacity_fade(
            backtest_returns=self.returns,
            backtest_capital=Decimal("100000"),
            current_capital=Decimal("100000"),
            target_capital=Decimal("1000000"),  # 10x increase
            required_return_pct=Decimal("5.0"),
        )

        # With sqrt(capacity) decay, fade should be significant
        assert len(fade.constraints) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
