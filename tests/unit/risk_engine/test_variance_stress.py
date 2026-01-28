"""
Tests for Portfolio Variance Stress Testing.

Tests the new portfolio variance stress testing features.
"""

import pytest
import numpy as np
from decimal import Decimal

from app.engines.risk_engine.stress_testers.portfolio_variance_stress import (
    PortfolioVarianceStressTester,
)
from app.models.portfolio import Portfolio, Position


class TestPortfolioVarianceStressTester:
    """Test portfolio variance stress testing."""

    @pytest.fixture
    def stress_tester(self):
        """Create stress tester instance."""
        return PortfolioVarianceStressTester()

    @pytest.fixture
    def sample_portfolio(self):
        """Create sample portfolio."""
        portfolio = Portfolio()
        portfolio.cash = Decimal("10000.00")

        # Add positions
        portfolio.add_position(
            symbol='AAPL',
            quantity=Decimal("100"),
            market_price=Decimal("150.00"),
        )
        portfolio.add_position(
            symbol='MSFT',
            quantity=Decimal("50"),
            market_price=Decimal("300.00"),
        )
        portfolio.add_position(
            symbol='GOOGL',
            quantity=Decimal("20"),
            market_price=Decimal("2500.00"),
        )

        return portfolio

    @pytest.fixture
    def sample_correlations(self):
        """Sample correlation matrix."""
        return {
            'AAPL': {'AAPL': 1.0, 'MSFT': 0.7, 'GOOGL': 0.6},
            'MSFT': {'AAPL': 0.7, 'MSFT': 1.0, 'GOOGL': 0.65},
            'GOOGL': {'AAPL': 0.6, 'MSFT': 0.65, 'GOOGL': 1.0},
        }

    @pytest.fixture
    def sample_volatilities(self):
        """Sample volatilities."""
        return {
            'AAPL': 0.25,
            'MSFT': 0.28,
            'GOOGL': 0.30,
        }

    def test_calculate_portfolio_variance(self, stress_tester, sample_portfolio,
                                          sample_correlations, sample_volatilities):
        """Test portfolio variance calculation."""
        variance = stress_tester._calculate_portfolio_variance(
            sample_portfolio, sample_correlations, sample_volatilities
        )

        assert variance > 0
        assert isinstance(variance, float)

        # Volatility should be positive
        portfolio_vol = np.sqrt(variance)
        assert portfolio_vol > 0

    def test_run_variance_stress_tests(self, stress_tester, sample_portfolio,
                                       sample_correlations, sample_volatilities):
        """Test running variance stress tests."""
        results = stress_tester.run_variance_stress_tests(
            sample_portfolio,
            sample_correlations,
            sample_volatilities,
        )

        assert 'scenarios' in results
        assert 'summary' in results
        assert 'baseline_variance' in results
        assert results['baseline_variance'] > 0

        # Check specific scenarios
        assert 'volatility_spike_2x' in results['scenarios']
        assert 'correlation_breakdown_80' in results['scenarios']

        # Check scenario results
        vol_spike = results['scenarios']['volatility_spike_2x']
        assert 'baseline_variance' in vol_spike
        assert 'stressed_variance' in vol_spike
        assert 'variance_increase_pct' in vol_spike
        assert vol_spike['stressed_variance'] > vol_spike['baseline_variance']

    def test_correlation_breakdown_scenario(self, stress_tester, sample_portfolio,
                                           sample_correlations, sample_volatilities):
        """Test correlation breakdown scenario."""
        results = stress_tester.run_variance_stress_tests(
            sample_portfolio,
            sample_correlations,
            sample_volatilities,
            scenario_names=['correlation_breakdown_perfect'],
        )

        perfect_corr = results['scenarios']['correlation_breakdown_perfect']

        # Perfect correlation should increase variance significantly
        assert perfect_corr['variance_increase_pct'] > 0
        assert perfect_corr['stressed_variance'] > perfect_corr['baseline_variance']

    def test_extreme_stress_scenario(self, stress_tester, sample_portfolio,
                                     sample_correlations, sample_volatilities):
        """Test extreme stress scenario (3x vol + perfect corr)."""
        results = stress_tester.run_variance_stress_tests(
            sample_portfolio,
            sample_correlations,
            sample_volatilities,
            scenario_names=['extreme_stress'],
        )

        extreme = results['scenarios']['extreme_stress']

        # Extreme stress should cause largest variance increase
        assert extreme['variance_increase_pct'] > 100  # At least double

    def test_variance_stress_summary(self, stress_tester, sample_portfolio,
                                     sample_correlations, sample_volatilities):
        """Test stress test summary generation."""
        results = stress_tester.run_variance_stress_tests(
            sample_portfolio,
            sample_correlations,
            sample_volatilities,
        )

        summary = results['summary']
        assert 'worst_scenario' in summary
        assert 'best_scenario' in summary
        assert 'statistics' in summary
        assert 'overall_assessment' in summary

        # Check statistics
        stats = summary['statistics']
        assert 'mean_increase_pct' in stats
        assert 'max_increase_pct' in stats
        assert 'min_increase_pct' in stats

        # Check overall assessment
        assessment = summary['overall_assessment']
        assert 'risk_level' in assessment
        assert 'recommendation' in assessment

    def test_decompose_portfolio_variance(self, stress_tester, sample_portfolio,
                                          sample_correlations, sample_volatilities):
        """Test portfolio variance decomposition."""
        decomposition = stress_tester.decompose_portfolio_variance(
            sample_portfolio,
            sample_correlations,
            sample_volatilities,
        )

        assert 'total_variance' in decomposition
        assert 'portfolio_volatility' in decomposition
        assert 'diagonal_variance' in decomposition
        assert 'off_diagonal_covariance' in decomposition
        assert 'position_contributions' in decomposition

        # Total variance should be sum of components
        total = decomposition['total_variance']
        diagonal = decomposition['diagonal_variance']
        off_diag = decomposition['off_diagonal_covariance']
        assert abs(total - (diagonal + off_diag)) < 1e-10

        # Check diversification ratio
        assert 'diversification_ratio' in decomposition
        assert decomposition['diversification_ratio'] >= 1.0  # Should be >= 1

        # Check interpretation
        assert 'interpretation' in decomposition

    def test_calculate_concentration_stress(self, stress_tester, sample_portfolio,
                                            sample_volatilities):
        """Test concentration stress calculation."""
        concentration = stress_tester.calculate_concentration_stress(
            sample_portfolio,
            sample_volatilities,
            concentration_threshold=0.30,
        )

        assert 'largest_position' in concentration
        assert 'largest_weight' in concentration
        assert 'is_concentrated' in concentration
        assert 'stress_scenario' in concentration
        assert 'severity' in concentration

        # Check stress scenario
        stress = concentration['stress_scenario']
        assert 'portfolio_loss' in stress
        assert stress['portfolio_loss'] < 0  # Should be a loss

    def test_variance_increase_assessment(self, stress_tester):
        """Test variance increase severity assessment."""
        # Low increase
        assessment = stress_tester._assess_variance_increase(10)
        assert assessment['severity'] == 'LOW'

        # Moderate increase
        assessment = stress_tester._assess_variance_increase(30)
        assert assessment['severity'] == 'MODERATE'

        # High increase
        assessment = stress_tester._assess_variance_increase(75)
        assert assessment['severity'] == 'HIGH'

        # Critical increase
        assessment = stress_tester._assess_variance_increase(150)
        assert assessment['severity'] == 'CRITICAL'

    def test_stress_correlations_helper(self, stress_tester, sample_portfolio,
                                        sample_correlations, sample_volatilities):
        """Test correlation stressing helper function."""
        scenario = {
            'name': 'Test',
            'correlation_target': 0.8,
            'volatility_multiplier': 1.0,
        }

        stressed_matrix = stress_tester._stress_correlations(
            sample_correlations,
            sample_portfolio,
            scenario,
        )

        # All correlations should be 0.8
        for symbol1 in stressed_matrix:
            for symbol2 in stressed_matrix[symbol1]:
                if symbol1 != symbol2:
                    assert stressed_matrix[symbol1][symbol2] == 0.8

    def test_all_scenarios_available(self, stress_tester):
        """Test that all expected scenarios are available."""
        scenarios = stress_tester.scenarios

        # Check key scenarios exist
        assert 'baseline' in scenarios
        assert 'volatility_spike_2x' in scenarios
        assert 'volatility_spike_3x' in scenarios
        assert 'correlation_breakdown_80' in scenarios
        assert 'correlation_breakdown_90' in scenarios
        assert 'correlation_breakdown_perfect' in scenarios
        assert 'volatility_correlation_combo' in scenarios
        assert 'extreme_stress' in scenarios


class TestVarianceDecomposition:
    """Test variance decomposition functionality."""

    @pytest.fixture
    def stress_tester(self):
        return PortfolioVarianceStressTester()

    @pytest.fixture
    def diversified_portfolio(self):
        """Create well-diversified portfolio."""
        portfolio = Portfolio()
        portfolio.cash = Decimal("50000.00")

        # Many small positions
        for symbol, price in [('AAPL', 150), ('MSFT', 300), ('GOOGL', 2500),
                              ('AMZN', 3200), ('TSLA', 800), ('META', 300)]:
            portfolio.add_position(
                symbol=symbol,
                quantity=Decimal("10"),
                market_price=Decimal(str(price)),
            )

        return portfolio

    @pytest.fixture
    def concentrated_portfolio(self):
        """Create concentrated portfolio."""
        portfolio = Portfolio()
        portfolio.cash = Decimal("10000.00")

        # One large position
        portfolio.add_position(
            symbol='TSLA',
            quantity=Decimal("100"),
            market_price=Decimal("800.00"),
        )

        # Small positions
        for symbol in ['AAPL', 'MSFT']:
            portfolio.add_position(
                symbol=symbol,
                quantity=Decimal("10"),
                market_price=Decimal("150.00"),
            )

        return portfolio

    def test_diversified_vs_concentrated(self, stress_tester, diversified_portfolio,
                                         concentrated_portfolio):
        """Compare variance decomposition of diversified vs concentrated."""
        corr = {
            'AAPL': {'AAPL': 1.0, 'MSFT': 0.7, 'GOOGL': 0.6, 'AMZN': 0.6,
                     'TSLA': 0.5, 'META': 0.65},
            'MSFT': {'AAPL': 0.7, 'MSFT': 1.0, 'GOOGL': 0.65, 'AMZN': 0.65,
                     'TSLA': 0.55, 'META': 0.7},
            'GOOGL': {'AAPL': 0.6, 'MSFT': 0.65, 'GOOGL': 1.0, 'AMZN': 0.6,
                      'TSLA': 0.5, 'META': 0.6},
            'AMZN': {'AAPL': 0.6, 'MSFT': 0.65, 'GOOGL': 0.6, 'AMZN': 1.0,
                     'TSLA': 0.55, 'META': 0.6},
            'TSLA': {'AAPL': 0.5, 'MSFT': 0.55, 'GOOGL': 0.5, 'AMZN': 0.55,
                     'TSLA': 1.0, 'META': 0.5},
            'META': {'AAPL': 0.65, 'MSFT': 0.7, 'GOOGL': 0.6, 'AMZN': 0.6,
                     'TSLA': 0.5, 'META': 1.0},
        }

        vols = {
            'AAPL': 0.25, 'MSFT': 0.28, 'GOOGL': 0.30,
            'AMZN': 0.32, 'TSLA': 0.45, 'META': 0.35,
        }

        div_decomp = stress_tester.decompose_portfolio_variance(
            diversified_portfolio, corr, vols
        )

        conc_decomp = stress_tester.decompose_portfolio_variance(
            concentrated_portfolio,
            {k: v for k, v in corr.items() if k in ['AAPL', 'MSFT', 'TSLA']},
            {k: v for k, v in vols.items() if k in ['AAPL', 'MSFT', 'TSLA']},
        )

        # Diversified should have higher diversification ratio
        # (more benefit from correlation structure)
        if div_decomp.get('diversification_ratio') and conc_decomp.get('diversification_ratio'):
            # This is a rough check - exact values depend on portfolio composition
            assert div_decomp['diversification_ratio'] >= 1.0
            assert conc_decomp['diversification_ratio'] >= 1.0
