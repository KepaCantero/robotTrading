"""
Unit tests for Advanced Stress Testing Scenarios - Hull Chapter 20

Tests for liquidity, counterparty, and operational risk stress testing.
"""

import pytest
import numpy as np
from unittest.mock import Mock
from app.engines.risk_engine.stress_testers.advanced_stress_scenarios import (
    LiquidityRiskStressTester,
    CounterpartyRiskStressTester,
    OperationalRiskStressTester,
    AdvancedStressTestOrchestrator,
)


class TestLiquidityRiskStressTester:
    """Test suite for liquidity risk stress testing."""

    @pytest.fixture
    def liquidity_tester(self):
        """Create liquidity risk stress tester."""
        return LiquidityRiskStressTester()

    @pytest.fixture
    def mock_portfolio(self):
        """Create mock portfolio."""
        portfolio = Mock()
        portfolio.total_equity = 1000000.0
        portfolio.positions = []

        # Add some mock positions
        for symbol in ['AAPL', 'MSFT', 'GOOGL']:
            position = Mock()
            position.symbol = symbol
            position.market_value = 333333.33
            portfolio.positions.append(position)

        return portfolio

    def test_liquidity_scenario_initialization(self, liquidity_tester):
        """Test that liquidity scenarios are initialized correctly."""
        assert 'baseline' in liquidity_tester.scenarios
        assert 'moderate_liquidity_crisis' in liquidity_tester.scenarios
        assert 'severe_liquidity_crisis' in liquidity_tester.scenarios
        assert 'flash_crash_liquidity' in liquidity_tester.scenarios

    def test_calculate_liquidity_adjusted_var(self, liquidity_tester, mock_portfolio):
        """Test liquidity-adjusted VaR calculation."""
        base_var = -50000.0  # $50,000 VaR

        result = liquidity_tester.calculate_liquidity_adjusted_var(
            portfolio=mock_portfolio,
            base_var=base_var,
            scenario_name='moderate_liquidity_crisis',
        )

        assert 'error' not in result
        assert 'base_var' in result
        assert 'liquidity_cost' in result
        assert 'liquidity_adjusted_var' in result
        assert result['liquidity_adjusted_var'] < base_var  # More negative

    def test_liquidity_adjustment_percentage(self, liquidity_tester, mock_portfolio):
        """Test that liquidity adjustment percentage is calculated."""
        base_var = -50000.0

        result = liquidity_tester.calculate_liquidity_adjusted_var(
            portfolio=mock_portfolio,
            base_var=base_var,
            scenario_name='mild_liquidity_drought',
        )

        assert 'error' not in result
        assert 'liquidity_adjustment_pct' in result
        assert result['liquidity_adjustment_pct'] >= 0

    def test_position_liquidity_costs(self, liquidity_tester, mock_portfolio):
        """Test that position-level liquidity costs are calculated."""
        base_var = -50000.0

        result = liquidity_tester.calculate_liquidity_adjusted_var(
            portfolio=mock_portfolio,
            base_var=base_var,
            scenario_name='severe_liquidity_crisis',
        )

        assert 'error' not in result
        assert 'position_costs' in result
        assert len(result['position_costs']) == len(mock_portfolio.positions)

        for cost in result['position_costs']:
            assert 'symbol' in cost
            assert 'spread_cost' in cost
            assert 'market_impact_cost' in cost
            assert 'total_liquidity_cost' in cost

    def test_run_liquidity_stress_tests(self, liquidity_tester, mock_portfolio):
        """Test running multiple liquidity stress scenarios."""
        base_var = -50000.0

        result = liquidity_tester.run_liquidity_stress_tests(
            portfolio=mock_portfolio,
            base_var=base_var,
            scenario_names=['baseline', 'mild_liquidity_drought', 'moderate_liquidity_crisis'],
        )

        assert 'error' not in result
        assert 'scenarios' in result
        assert 'summary' in result
        assert len(result['scenarios']) == 3

    def test_liquidity_summary_generation(self, liquidity_tester, mock_portfolio):
        """Test liquidity stress test summary generation."""
        base_var = -50000.0

        result = liquidity_tester.run_liquidity_stress_tests(
            portfolio=mock_portfolio,
            base_var=base_var,
        )

        assert 'error' not in result
        summary = result['summary']
        assert 'worst_scenario' in summary
        assert 'best_scenario' in summary
        assert 'avg_adjustment_pct' in summary
        assert 'risk_assessment' in summary

    def test_liquidity_risk_assessment(self, liquidity_tester, mock_portfolio):
        """Test liquidity risk assessment levels."""
        base_var = -50000.0

        result = liquidity_tester.run_liquidity_stress_tests(
            portfolio=mock_portfolio,
            base_var=base_var,
        )

        assert 'error' not in result
        risk_assessment = result['summary']['risk_assessment']
        assert 'level' in risk_assessment
        assert 'action' in risk_assessment
        assert risk_assessment['level'] in ['LOW', 'MODERATE', 'HIGH', 'CRITICAL']

    def test_interpret_lvar_messages(self, liquidity_tester):
        """Test L-VaR interpretation messages."""
        # Test different adjustment levels
        adjustments = [5, 15, 30, 60]

        for adj in adjustments:
            interpretation = liquidity_tester._interpret_lvar(adj)
            assert isinstance(interpretation, str)
            assert len(interpretation) > 0

    def test_unknown_scenario_handling(self, liquidity_tester, mock_portfolio):
        """Test handling of unknown scenario names."""
        base_var = -50000.0

        result = liquidity_tester.calculate_liquidity_adjusted_var(
            portfolio=mock_portfolio,
            base_var=base_var,
            scenario_name='unknown_scenario',
        )

        assert 'error' in result
        assert 'Unknown scenario' in result['error']


class TestCounterpartyRiskStressTester:
    """Test suite for counterparty risk stress testing."""

    @pytest.fixture
    def counterparty_tester(self):
        """Create counterparty risk stress tester."""
        return CounterpartyRiskStressTester()

    @pytest.fixture
    def mock_portfolio(self):
        """Create mock portfolio."""
        portfolio = Mock()
        portfolio.total_equity = 1000000.0
        return portfolio

    @pytest.fixture
    def counterparty_data(self):
        """Create counterparty exposure data."""
        return {
            'Bank_A': {
                'exposure': 200000.0,
                'credit_quality': 'AA',
                'recovery_rate': 0.6,
            },
            'Broker_B': {
                'exposure': 150000.0,
                'credit_quality': 'A',
                'recovery_rate': 0.5,
            },
            'Clearing_House': {
                'exposure': 50000.0,
                'credit_quality': 'AAA',
                'recovery_rate': 0.8,
            },
        }

    def test_counterparty_scenario_initialization(self, counterparty_tester):
        """Test that counterparty scenarios are initialized."""
        assert 'single_minor_default' in counterparty_tester.scenarios
        assert 'single_major_default' in counterparty_tester.scenarios
        assert 'multiple_defaults' in counterparty_tester.scenarios
        assert 'systemic_default_contagion' in counterparty_tester.scenarios

    def test_calculate_counterparty_exposure(self, counterparty_tester, mock_portfolio, counterparty_data):
        """Test counterparty exposure calculation."""
        result = counterparty_tester.calculate_counterparty_exposure(
            portfolio=mock_portfolio,
            counterparty_data=counterparty_data,
            scenario_name='single_major_default',
        )

        assert 'error' not in result
        assert 'total_exposure_at_default' in result
        assert 'expected_loss' in result
        assert 'counterparty_losses' in result
        assert 'risk_assessment' in result

    def test_counterparty_loss_breakdown(self, counterparty_tester, mock_portfolio, counterparty_data):
        """Test counterparty loss breakdown by counterparty."""
        result = counterparty_tester.calculate_counterparty_exposure(
            portfolio=mock_portfolio,
            counterparty_data=counterparty_data,
            scenario_name='multiple_defaults',
        )

        assert 'error' not in result
        assert len(result['counterparty_losses']) == len(counterparty_data)

        for loss in result['counterparty_losses']:
            assert 'counterparty' in loss
            assert 'loss_given_default' in loss
            assert loss['loss_given_default'] >= 0

    def test_systemic_contagion_scenario(self, counterparty_tester, mock_portfolio, counterparty_data):
        """Test systemic default contagion scenario."""
        result = counterparty_tester.calculate_counterparty_exposure(
            portfolio=mock_portfolio,
            counterparty_data=counterparty_data,
            scenario_name='systemic_default_contagion',
        )

        assert 'error' not in result
        # Should have correlation multiplier > 1
        assert result['correlation_multiplier'] > 1.0

    def test_counterparty_risk_assessment(self, counterparty_tester, mock_portfolio, counterparty_data):
        """Test counterparty risk assessment."""
        result = counterparty_tester.calculate_counterparty_exposure(
            portfolio=mock_portfolio,
            counterparty_data=counterparty_data,
            scenario_name='single_major_default',
        )

        assert 'error' not in result
        risk_assessment = result['risk_assessment']
        assert 'level' in risk_assessment
        assert 'loss_percentage' in risk_assessment
        assert 'action' in risk_assessment

    def test_counterparty_risk_levels(self, counterparty_tester, mock_portfolio, counterparty_data):
        """Test different counterparty risk levels."""
        # Create high exposure scenario
        high_exposure_data = {
            'Big_Bank': {
                'exposure': 600000.0,  # 60% of portfolio
                'credit_quality': 'BBB',
                'recovery_rate': 0.3,
            }
        }

        result = counterparty_tester.calculate_counterparty_exposure(
            portfolio=mock_portfolio,
            counterparty_data=high_exposure_data,
            scenario_name='single_major_default',
        )

        assert 'error' not in result
        risk_level = result['risk_assessment']['level']
        assert risk_level in ['LOW', 'MODERATE', 'HIGH', 'CRITICAL']


class TestOperationalRiskStressTester:
    """Test suite for operational risk stress testing."""

    @pytest.fixture
    def operational_tester(self):
        """Create operational risk stress tester."""
        return OperationalRiskStressTester()

    @pytest.fixture
    def mock_portfolio(self):
        """Create mock portfolio."""
        portfolio = Mock()
        portfolio.total_equity = 1000000.0
        return portfolio

    def test_operational_scenario_initialization(self, operational_tester):
        """Test that operational scenarios are initialized."""
        assert 'system_outage' in operational_tester.scenarios
        assert 'data_feed_failure' in operational_tester.scenarios
        assert 'settlement_failure' in operational_tester.scenarios
        assert 'human_error' in operational_tester.scenarios
        assert 'cyber_incident' in operational_tester.scenarios

    def test_system_outage_impact(self, operational_tester, mock_portfolio):
        """Test system outage impact calculation."""
        portfolio_volatility = 0.02  # 2% daily

        result = operational_tester.calculate_operational_risk_impact(
            portfolio=mock_portfolio,
            portfolio_volatility=portfolio_volatility,
            scenario_name='system_outage',
        )

        assert 'error' not in result
        assert 'estimated_loss' in result
        assert 'loss_percentage' in result
        assert 'impact_details' in result
        assert result['impact_type'] == 'trading_halt'

    def test_human_error_impact(self, operational_tester, mock_portfolio):
        """Test human error impact calculation."""
        portfolio_volatility = 0.02

        result = operational_tester.calculate_operational_risk_impact(
            portfolio=mock_portfolio,
            portfolio_volatility=portfolio_volatility,
            scenario_name='human_error',
        )

        assert 'error' not in result
        assert result['impact_type'] == 'adverse_trade'
        assert result['estimated_loss'] > 0

    def test_settlement_failure_impact(self, operational_tester, mock_portfolio):
        """Test settlement failure impact calculation."""
        portfolio_volatility = 0.02

        result = operational_tester.calculate_operational_risk_impact(
            portfolio=mock_portfolio,
            portfolio_volatility=portfolio_volatility,
            scenario_name='settlement_failure',
        )

        assert 'error' not in result
        assert result['impact_type'] == 'settlement_delay'
        assert 'penalty_rate' in result['impact_details']

    def test_cyber_incident_impact(self, operational_tester, mock_portfolio):
        """Test cyber incident impact calculation."""
        portfolio_volatility = 0.02

        result = operational_tester.calculate_operational_risk_impact(
            portfolio=mock_portfolio,
            portfolio_volatility=portfolio_volatility,
            scenario_name='cyber_incident',
        )

        assert 'error' not in result
        assert result['impact_type'] == 'system_compromise'
        # Should include both trading loss and reputation loss
        impact_details = result['impact_details']
        assert 'trading_loss' in impact_details
        assert 'reputation_loss' in impact_details

    def test_operational_risk_assessment(self, operational_tester, mock_portfolio):
        """Test operational risk assessment."""
        portfolio_volatility = 0.02

        result = operational_tester.calculate_operational_risk_impact(
            portfolio=mock_portfolio,
            portfolio_volatility=portfolio_volatility,
            scenario_name='system_outage',
        )

        assert 'error' not in result
        risk_assessment = result['risk_assessment']
        assert 'level' in risk_assessment
        assert 'action' in risk_assessment
        assert risk_assessment['level'] in ['LOW', 'MODERATE', 'HIGH', 'CRITICAL']

    def test_unknown_scenario_handling(self, operational_tester, mock_portfolio):
        """Test handling of unknown scenario names."""
        portfolio_volatility = 0.02

        result = operational_tester.calculate_operational_risk_impact(
            portfolio=mock_portfolio,
            portfolio_volatility=portfolio_volatility,
            scenario_name='unknown_scenario',
        )

        assert 'error' in result


class TestAdvancedStressTestOrchestrator:
    """Test suite for advanced stress test orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create advanced stress test orchestrator."""
        return AdvancedStressTestOrchestrator()

    @pytest.fixture
    def mock_portfolio(self):
        """Create mock portfolio."""
        portfolio = Mock()
        portfolio.total_equity = 1000000.0

        # Add positions
        portfolio.positions = []
        for symbol in ['AAPL', 'MSFT', 'GOOGL']:
            position = Mock()
            position.symbol = symbol
            position.market_value = 333333.33
            portfolio.positions.append(position)

        return portfolio

    @pytest.fixture
    def counterparty_data(self):
        """Create counterparty exposure data."""
        return {
            'Bank_A': {
                'exposure': 100000.0,
                'credit_quality': 'A',
                'recovery_rate': 0.5,
            },
        }

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.liquidity_tester is not None
        assert orchestrator.counterparty_tester is not None
        assert orchestrator.operational_tester is not None

    def test_run_comprehensive_advanced_stress_tests(
        self, orchestrator, mock_portfolio, counterparty_data
    ):
        """Test comprehensive advanced stress testing."""
        base_var = -50000.0
        portfolio_volatility = 0.02

        result = orchestrator.run_comprehensive_advanced_stress_tests(
            portfolio=mock_portfolio,
            base_var=base_var,
            portfolio_volatility=portfolio_volatility,
            counterparty_data=counterparty_data,
        )

        assert 'error' not in result
        assert 'results' in result
        assert 'overall_assessment' in result

        # Check that all risk categories are tested
        results = result['results']
        assert 'liquidity_risk' in results
        assert 'counterparty_risk' in results
        assert 'operational_risk' in results

    def test_overall_assessment_generation(self, orchestrator, mock_portfolio):
        """Test overall risk assessment generation."""
        base_var = -50000.0
        portfolio_volatility = 0.02

        result = orchestrator.run_comprehensive_advanced_stress_tests(
            portfolio=mock_portfolio,
            base_var=base_var,
            portfolio_volatility=portfolio_volatility,
        )

        assert 'error' not in result
        assessment = result['overall_assessment']
        assert 'overall_risk_level' in assessment
        assert 'risk_score' in assessment
        assert 'recommendation' in assessment
        assert 'risk_categories' in assessment

    def test_risk_level_to_score_conversion(self, orchestrator):
        """Test risk level to score conversion."""
        test_cases = [
            ('LOW', 1),
            ('MODERATE', 2),
            ('HIGH', 3),
            ('CRITICAL', 4),
        ]

        for level, expected_score in test_cases:
            score = orchestrator._risk_level_to_score(level)
            assert score == expected_score

    def test_comprehensive_stress_test_without_counterparty_data(
        self, orchestrator, mock_portfolio
    ):
        """Test comprehensive stress testing without counterparty data."""
        base_var = -50000.0
        portfolio_volatility = 0.02

        result = orchestrator.run_comprehensive_advanced_stress_tests(
            portfolio=mock_portfolio,
            base_var=base_var,
            portfolio_volatility=portfolio_volatility,
            counterparty_data=None,
        )

        assert 'error' not in result
        # Counterparty risk should show note
        assert 'note' in result['results']['counterparty_risk']


class TestLiquidityRiskEdgeCases:
    """Test edge cases for liquidity risk."""

    @pytest.fixture
    def liquidity_tester(self):
        return LiquidityRiskStressTester()

    def test_empty_portfolio(self, liquidity_tester):
        """Test liquidity calculation with empty portfolio."""
        portfolio = Mock()
        portfolio.total_equity = 0.0
        portfolio.positions = []

        result = liquidity_tester.calculate_liquidity_adjusted_var(
            portfolio=portfolio,
            base_var=-50000.0,
            scenario_name='moderate_liquidity_crisis',
        )

        # Should handle gracefully
        assert 'error' in result or result.get('liquidity_cost', 0) == 0

    def test_zero_base_var(self, liquidity_tester):
        """Test with zero base VaR."""
        portfolio = Mock()
        portfolio.total_equity = 1000000.0
        portfolio.positions = []

        result = liquidity_tester.calculate_liquidity_adjusted_var(
            portfolio=portfolio,
            base_var=0.0,
            scenario_name='moderate_liquidity_crisis',
        )

        assert 'error' not in result
        # Liquidity cost should still be calculated
        assert 'liquidity_cost' in result


class TestOperationalRiskEdgeCases:
    """Test edge cases for operational risk."""

    @pytest.fixture
    def operational_tester(self):
        return OperationalRiskStressTester()

    def test_zero_volatility(self, operational_tester):
        """Test operational risk with zero volatility."""
        portfolio = Mock()
        portfolio.total_equity = 1000000.0

        result = operational_tester.calculate_operational_risk_impact(
            portfolio=portfolio,
            portfolio_volatility=0.0,
            scenario_name='system_outage',
        )

        # Should handle gracefully
        assert 'error' in result or result.get('estimated_loss', 0) >= 0

    def test_zero_portfolio_value(self, operational_tester):
        """Test operational risk with zero portfolio value."""
        portfolio = Mock()
        portfolio.total_equity = 0.0

        result = operational_tester.calculate_operational_risk_impact(
            portfolio=portfolio,
            portfolio_volatility=0.02,
            scenario_name='human_error',
        )

        # Should handle gracefully
        assert 'error' in result or result.get('estimated_loss', 0) == 0
