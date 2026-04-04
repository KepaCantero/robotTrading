"""
Unit tests for Risk Limits Enforcer.

Tests for automatic risk limit enforcement based on VaR thresholds.
"""

from unittest.mock import Mock

import pytest

from app.domain.models.portfolio import Portfolio
from app.engines.risk_engine.risk_limits_enforcer import RiskLimitsEnforcer


@pytest.fixture
def mock_position():
    """Create mock position."""
    position = Mock()
    position.symbol = 'AAPL'
    position.market_value = 20000.0
    return position


@pytest.fixture
def mock_portfolio():
    """Create mock portfolio."""
    portfolio = Mock(spec=Portfolio)
    portfolio.total_equity = 100000.0
    portfolio.positions = []
    return portfolio


@pytest.fixture
def sample_portfolio():
    """Create portfolio with sample positions."""
    portfolio = Mock(spec=Portfolio)
    portfolio.total_equity = 100000.0

    # Create mock positions
    positions = []
    for i, (symbol, value) in enumerate(
        [
            ('AAPL', 30000.0),
            ('MSFT', 25000.0),
            ('GOOGL', 20000.0),
            ('TSLA', 15000.0),
        ]
    ):
        pos = Mock()
        pos.symbol = symbol
        pos.market_value = value
        positions.append(pos)

    portfolio.positions = positions
    return portfolio


@pytest.fixture
def enforcer():
    """Create RiskLimitsEnforcer with default config."""
    return RiskLimitsEnforcer()


@pytest.fixture
def custom_enforcer():
    """Create RiskLimitsEnforcer with custom config."""
    config = {
        'var_warning_limit': 0.01,
        'var_critical_limit': 0.02,
        'var_halt_limit': 0.03,
        'max_position_pct': 0.15,
        'max_concentration_pct': 0.30,
    }
    return RiskLimitsEnforcer(config)


@pytest.mark.unit
class TestRiskLimitsEnforcerInitialization:
    """Test RiskLimitsEnforcer initialization."""

    def test_default_initialization(self, enforcer):
        """Test initialization with default config."""
        assert enforcer.var_warning_limit == 0.02
        assert enforcer.var_critical_limit == 0.03
        assert enforcer.var_halt_limit == 0.05
        assert enforcer.max_position_pct == 0.20
        assert enforcer.max_concentration_pct == 0.40
        assert enforcer.max_leverage == 2.0

    def test_custom_initialization(self, custom_enforcer):
        """Test initialization with custom config."""
        assert custom_enforcer.var_warning_limit == 0.01
        assert custom_enforcer.var_critical_limit == 0.02
        assert custom_enforcer.var_halt_limit == 0.03

    def test_trading_halt_initial_state(self, enforcer):
        """Test initial trading halt state."""
        assert enforcer.trading_halted is False
        assert enforcer.halt_reason is None

    def test_enforcement_history_initialization(self, enforcer):
        """Test enforcement history is initialized."""
        assert isinstance(enforcer.enforcement_history, list)
        assert len(enforcer.enforcement_history) == 0


@pytest.mark.unit
class TestVaRLimitsChecking:
    """Test VaR limit checking."""

    def test_var_within_limits(self, enforcer, mock_portfolio):
        """Test VaR within acceptable limits."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.01)

        assert result['severity'] == 'NORMAL'
        assert result['action'] is None
        assert result['trading_halted'] is False

    def test_var_warning_limit(self, enforcer, mock_portfolio):
        """Test VaR at warning limit."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.025)

        assert result['severity'] == 'WARNING'
        assert result['action'] == 'MONITOR'
        assert result['trading_halted'] is False

    def test_var_critical_limit(self, enforcer, mock_portfolio):
        """Test VaR at critical limit."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.035)

        assert result['severity'] == 'CRITICAL'
        assert result['action'] == 'REDUCE_POSITIONS'
        assert 'reduction_needed' in result['messages'][1]

    def test_var_halt_limit(self, enforcer, mock_portfolio):
        """Test VaR at halt limit."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.06)

        assert result['severity'] == 'CRITICAL'
        assert result['action'] == 'HALT_TRADING'
        assert result['trading_halted'] is True
        assert enforcer.trading_halted is True
        assert enforcer.halt_reason is not None

    def test_var_amount_calculation(self, enforcer, mock_portfolio):
        """Test VaR amount is calculated correctly."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.05)

        assert result['var_amount'] == 5000.0  # 5% of 100,000

    def test_var_utilization_calculation(self, enforcer, mock_portfolio):
        """Test VaR utilization is calculated correctly."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.03)

        # 0.03 / 0.03 (critical limit) = 1.0
        assert result['var_utilization'] == 1.0

    def test_var_with_custom_portfolio_value(self, enforcer, mock_portfolio):
        """Test VaR check with custom portfolio value."""
        result = enforcer.check_var_limits(
            mock_portfolio, current_var=0.05, portfolio_value=200000.0
        )

        assert result['var_amount'] == 10000.0  # 5% of 200,000

    def test_var_limits_in_result(self, enforcer, mock_portfolio):
        """Test that limits are included in result."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.03)

        assert 'limits' in result
        assert 'warning' in result['limits']
        assert 'critical' in result['limits']
        assert 'halt' in result['limits']


@pytest.mark.unit
class TestRequiredReductionCalculation:
    """Test required position reduction calculation."""

    def test_no_reduction_needed(self, enforcer):
        """Test when target >= current."""
        reduction = enforcer._calculate_required_reduction(current_var=0.02, target_var=0.03)

        assert reduction == 0.0

    def test_reduction_calculation(self, enforcer):
        """Test reduction percentage calculation."""
        # To go from 0.05 to 0.02: (0.02/0.05)^2 = 0.16
        # Required reduction = (1 - 0.16) * 100 = 84%
        reduction = enforcer._calculate_required_reduction(current_var=0.05, target_var=0.02)

        assert 83 <= reduction <= 85

    def test_significant_reduction(self, enforcer):
        """Test when significant reduction is needed."""
        reduction = enforcer._calculate_required_reduction(current_var=0.10, target_var=0.02)

        # Should require > 90% reduction
        assert reduction > 90.0


@pytest.mark.unit
class TestPositionLimitsEnforcement:
    """Test position limits enforcement."""

    def test_no_violations(self, enforcer, sample_portfolio):
        """Test portfolio with no position limit violations."""
        result = enforcer.enforce_position_limits(sample_portfolio)

        assert result['compliance'] is True
        assert len(result['violations']) == 0

    def test_position_size_violation(self, enforcer, sample_portfolio):
        """Test position size exceeding limit."""
        # Add a large position
        large_pos = Mock()
        large_pos.symbol = 'AMZN'
        large_pos.market_value = 30000.0  # 30% of portfolio
        sample_portfolio.positions.append(large_pos)

        result = enforcer.enforce_position_limits(sample_portfolio)

        assert result['compliance'] is False

        position_violations = [v for v in result['violations'] if v['type'] == 'position_size']
        assert len(position_violations) > 0
        assert position_violations[0]['symbol'] == 'AMZN'

    def test_concentration_violation(self, enforcer, sample_portfolio):
        """Test concentration limit violation."""
        # Create highly concentrated portfolio
        for pos in sample_portfolio.positions:
            pos.market_value = 10000.0  # Equalize

        # Add one very large position
        large_pos = Mock()
        large_pos.symbol = 'NVDA'
        large_pos.market_value = 50000.0  # 50% of portfolio
        sample_portfolio.positions.append(large_pos)

        result = enforcer.enforce_position_limits(sample_portfolio)

        concentration_violations = [v for v in result['violations'] if v['type'] == 'concentration']
        assert len(concentration_violations) > 0

    def test_position_limits_calculation(self, enforcer, sample_portfolio):
        """Test position limits are calculated for all positions."""
        result = enforcer.enforce_position_limits(sample_portfolio)

        assert 'position_limits' in result
        assert len(result['position_limits']) == len(sample_portfolio.positions)

        for symbol, limits in result['position_limits'].items():
            assert 'current_weight' in limits
            assert 'limit' in limits
            assert 'utilization' in limits
            assert 'status' in limits

    def test_top_concentration_calculation(self, enforcer, sample_portfolio):
        """Test top 3 concentration is calculated."""
        result = enforcer.enforce_position_limits(sample_portfolio)

        assert 'top_concentration' in result
        assert 'concentration_limit' in result

        # Top 3 should sum to less than or equal to total
        assert result['top_concentration'] <= 1.0

    def test_zero_portfolio_value_error(self, enforcer, mock_portfolio):
        """Test error handling for zero portfolio value."""
        mock_portfolio.total_equity = 0

        result = enforcer.enforce_position_limits(mock_portfolio)

        assert 'error' in result


@pytest.mark.unit
class TestRiskHeatmap:
    """Test risk heatmap generation."""

    def test_heatmap_generation(self, enforcer, sample_portfolio):
        """Test heatmap is generated."""
        result = enforcer.generate_risk_heatmap(sample_portfolio)

        assert 'heatmap' in result
        assert len(result['heatmap']) == len(sample_portfolio.positions)

    def test_risk_level_classification(self, enforcer, sample_portfolio):
        """Test risk levels are classified correctly."""
        result = enforcer.generate_risk_heatmap(sample_portfolio)

        for item in result['heatmap']:
            assert 'risk_level' in item
            assert item['risk_level'] in ['LOW', 'MEDIUM', 'HIGH']

    def test_risk_color_assignment(self, enforcer, sample_portfolio):
        """Test risk colors are assigned."""
        result = enforcer.generate_risk_heatmap(sample_portfolio)

        for item in result['heatmap']:
            assert 'risk_color' in item
            assert item['risk_color'] in ['green', 'yellow', 'red']

    def test_high_weight_gets_high_risk(self, enforcer, sample_portfolio):
        """Test that high weight positions get HIGH risk."""
        # Modify to have one high weight position
        for pos in sample_portfolio.positions:
            pos.market_value = 10000.0

        large_pos = Mock()
        large_pos.symbol = 'BIG'
        large_pos.market_value = 25000.0  # 25% weight
        sample_portfolio.positions.append(large_pos)

        result = enforcer.generate_risk_heatmap(sample_portfolio)

        big_item = next(item for item in result['heatmap'] if item['symbol'] == 'BIG')
        assert big_item['risk_level'] == 'HIGH'
        assert big_item['risk_color'] == 'red'

    def test_heatmap_sorted_by_risk(self, enforcer, sample_portfolio):
        """Test heatmap is sorted by risk contribution."""
        result = enforcer.generate_risk_heatmap(sample_portfolio)

        heatmap = result['heatmap']
        # Should be sorted in descending order
        for i in range(len(heatmap) - 1):
            assert abs(heatmap[i]['risk_contribution']) >= abs(heatmap[i + 1]['risk_contribution'])

    def test_risk_distribution_analysis(self, enforcer, sample_portfolio):
        """Test risk distribution is analyzed."""
        result = enforcer.generate_risk_heatmap(sample_portfolio)

        assert 'risk_distribution' in result
        assert 'top_3_concentration' in result['risk_distribution']
        assert 'top_5_concentration' in result['risk_distribution']
        assert 'concentration_level' in result['risk_distribution']

    def test_with_risk_contributions(self, enforcer, sample_portfolio):
        """Test heatmap with provided risk contributions."""
        risk_contributions = {
            'AAPL': 0.30,
            'MSFT': 0.25,
            'GOOGL': 0.20,
            'TSLA': 0.15,
        }

        result = enforcer.generate_risk_heatmap(sample_portfolio, risk_contributions)

        for item in result['heatmap']:
            assert 'risk_contribution' in item


@pytest.mark.unit
class TestRiskAttribution:
    """Test risk attribution by asset class."""

    def test_default_asset_class_mapping(self, enforcer, sample_portfolio):
        """Test default asset class mapping."""
        returns_history = {
            'AAPL': [0.01, -0.01, 0.02],
            'MSFT': [0.02, 0.01, -0.01],
        }

        result = enforcer.attribute_risk_by_asset_class(sample_portfolio, returns_history)

        assert 'by_asset_class' in result
        assert len(result['by_asset_class']) > 0

    def test_custom_asset_class_mapping(self, enforcer, sample_portfolio):
        """Test with custom asset class mapping."""
        mapping = {
            'AAPL': 'technology',
            'MSFT': 'technology',
            'GOOGL': 'technology',
            'TSLA': 'consumer_discretionary',
        }

        returns_history = {
            'AAPL': [0.01, -0.01, 0.02],
            'MSFT': [0.02, 0.01, -0.01],
        }

        result = enforcer.attribute_risk_by_asset_class(sample_portfolio, returns_history, mapping)

        assert 'technology' in result['by_asset_class']

    def test_risk_contribution_calculation(self, enforcer, sample_portfolio):
        """Test risk contribution by asset class."""
        returns_history = {
            'AAPL': [0.01, -0.01, 0.02],
            'MSFT': [0.02, 0.01, -0.01],
        }

        result = enforcer.attribute_risk_by_asset_class(sample_portfolio, returns_history)

        for asset_class, attribution in result['by_asset_class'].items():
            assert 'exposure' in attribution
            assert 'weight' in attribution
            assert 'avg_volatility' in attribution
            assert 'risk_contribution' in attribution

    def test_dominant_risk_identification(self, enforcer, sample_portfolio):
        """Test dominant risk is identified."""
        returns_history = {
            'AAPL': [0.01, -0.01, 0.02],
            'MSFT': [0.02, 0.01, -0.01],
        }

        result = enforcer.attribute_risk_by_asset_class(sample_portfolio, returns_history)

        assert 'dominant_risk' in result
        assert result['dominant_risk'] is not None


@pytest.mark.unit
class TestDynamicPositionSizing:
    """Test dynamic position sizing based on VaR utilization."""

    def test_no_scaling_at_low_utilization(self, enforcer):
        """Test no scaling when VaR utilization is low."""
        base_size = 10000.0
        utilization = 0.3  # 30%

        adjusted = enforcer.calculate_dynamic_position_size(base_size, utilization)

        # Should be close to base size
        assert adjusted > base_size * 0.6

    def test_scaling_at_high_utilization(self, enforcer):
        """Test scaling when VaR utilization is high."""
        base_size = 10000.0
        utilization = 0.9  # 90%

        adjusted = enforcer.calculate_dynamic_position_size(base_size, utilization)

        # Should be significantly reduced
        assert adjusted < base_size * 0.2

    def test_no_position_at_max_utilization(self, enforcer):
        """Test no new positions when at max utilization."""
        base_size = 10000.0
        utilization = 1.0  # 100%

        adjusted = enforcer.calculate_dynamic_position_size(base_size, utilization)

        assert adjusted == 0.0

    def test_custom_max_utilization(self, enforcer):
        """Test with custom max utilization."""
        base_size = 10000.0
        utilization = 0.5
        max_util = 0.7

        adjusted = enforcer.calculate_dynamic_position_size(base_size, utilization, max_util)

        # Should be reduced but not to zero
        assert 0 < adjusted < base_size

    def test_scale_factor_calculation(self, enforcer):
        """Test scale factor is calculated correctly."""
        base_size = 10000.0
        utilization = 0.5

        adjusted = enforcer.calculate_dynamic_position_size(base_size, utilization)

        # Scale factor should be (1 - 0.5/0.8) = 0.375
        expected = base_size * 0.375
        assert abs(adjusted - expected) < 1


@pytest.mark.unit
class TestEnforcementLogging:
    """Test enforcement action logging."""

    def test_enforcement_logged(self, enforcer, mock_portfolio):
        """Test that enforcement actions are logged."""
        enforcer.check_var_limits(mock_portfolio, current_var=0.06)

        assert len(enforcer.enforcement_history) > 0

    def test_log_entry_structure(self, enforcer, mock_portfolio):
        """Test log entry has required structure."""
        enforcer.check_var_limits(mock_portfolio, current_var=0.06)

        entry = enforcer.enforcement_history[0]

        assert 'type' in entry
        assert 'timestamp' in entry
        assert 'result' in entry

    def test_multiple_enforcements_logged(self, enforcer, mock_portfolio):
        """Test multiple enforcement actions are logged."""
        enforcer.check_var_limits(mock_portfolio, current_var=0.06)
        enforcer.check_var_limits(mock_portfolio, current_var=0.04)

        assert len(enforcer.enforcement_history) == 2


@pytest.mark.unit
class TestTradingHaltManagement:
    """Test trading halt functionality."""

    def test_trading_halt_triggered(self, enforcer, mock_portfolio):
        """Test trading halt is triggered."""
        enforcer.check_var_limits(mock_portfolio, current_var=0.06)

        assert enforcer.trading_halted is True
        assert enforcer.halt_reason is not None

    def test_reset_trading_halt(self, enforcer, mock_portfolio):
        """Test trading halt can be reset."""
        enforcer.check_var_limits(mock_portfolio, current_var=0.06)
        assert enforcer.trading_halted is True

        enforcer.reset_trading_halt()

        assert enforcer.trading_halted is False
        assert enforcer.halt_reason is None

    def test_halt_reason_includes_var(self, enforcer, mock_portfolio):
        """Test halt reason includes VaR information."""
        enforcer.check_var_limits(mock_portfolio, current_var=0.06)

        assert 'VaR' in enforcer.halt_reason
        assert '%' in enforcer.halt_reason


@pytest.mark.unit
class TestGetEnforcementStatus:
    """Test enforcement status reporting."""

    def test_get_status(self, enforcer):
        """Test getting enforcement status."""
        status = enforcer.get_enforcement_status()

        assert 'trading_halted' in status
        assert 'halt_reason' in status
        assert 'enforcement_count' in status
        assert 'limits' in status

    def test_status_limits_match_config(self, custom_enforcer):
        """Test status limits match configuration."""
        status = custom_enforcer.get_enforcement_status()

        assert status['limits']['var_warning'] == 1.0
        assert status['limits']['var_critical'] == 2.0
        assert status['limits']['var_halt'] == 3.0


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_negative_var(self, enforcer, mock_portfolio):
        """Test handling of negative VaR."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=-0.01)

        # Should handle gracefully
        assert 'severity' in result

    def test_very_high_var(self, enforcer, mock_portfolio):
        """Test handling of very high VaR."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.50)

        assert result['action'] == 'HALT_TRADING'
        assert result['trading_halted'] is True

    def test_empty_portfolio(self, enforcer):
        """Test handling of empty portfolio."""
        portfolio = Mock(spec=Portfolio)
        portfolio.total_equity = 100000.0
        portfolio.positions = []

        result = enforcer.enforce_position_limits(portfolio)

        assert 'compliance' in result
        assert result['compliance'] is True  # No violations

    def test_portfolio_with_zero_positions(self, enforcer):
        """Test heatmap with no positions."""
        portfolio = Mock(spec=Portfolio)
        portfolio.total_equity = 100000.0
        portfolio.positions = []

        result = enforcer.generate_risk_heatmap(portfolio)

        assert 'heatmap' in result
        assert len(result['heatmap']) == 0


@pytest.mark.unit
class TestRiskDistributionAnalysis:
    """Test risk distribution analysis."""

    def test_concentration_levels(self, enforcer, sample_portfolio):
        """Test concentration level classification."""
        result = enforcer.generate_risk_heatmap(sample_portfolio)
        distribution = result['risk_distribution']

        assert distribution['concentration_level'] in ['LOW', 'MEDIUM', 'HIGH']

    def test_top_concentration_calculations(self, enforcer, sample_portfolio):
        """Test top concentration calculations."""
        result = enforcer.generate_risk_heatmap(sample_portfolio)
        distribution = result['risk_distribution']

        assert distribution['top_3_concentration'] <= 100
        assert distribution['top_5_concentration'] <= 100

        # Top 5 should be >= top 3
        assert distribution['top_5_concentration'] >= distribution['top_3_concentration']

    def test_n_positions_counted(self, enforcer, sample_portfolio):
        """Test number of positions is counted."""
        result = enforcer.generate_risk_heatmap(sample_portfolio)
        distribution = result['risk_distribution']

        assert distribution['n_positions'] == len(sample_portfolio.positions)


@pytest.mark.unit
class TestRequiredReductionMessages:
    """Test required reduction messages."""

    def test_reduction_message_format(self, enforcer, mock_portfolio):
        """Test reduction message is formatted correctly."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.035)

        reduction_msg = [m for m in result['messages'] if 'Reduce positions' in m]
        assert len(reduction_msg) > 0
        assert '%' in reduction_msg[0]

    def test_monitor_message(self, enforcer, mock_portfolio):
        """Test monitor message at warning level."""
        result = enforcer.check_var_limits(mock_portfolio, current_var=0.025)

        assert 'MONITOR' in result['action']
        assert 'exceeds warning limit' in result['messages'][0]
