"""
Shared fixtures and configuration for risk engine tests.

This module provides common fixtures used across all risk engine test modules.
"""
from unittest.mock import Mock

import numpy as np
import pytest

from app.models.portfolio import Portfolio


@pytest.fixture(scope="session")
def random_seed():
    """Set random seed for reproducibility."""
    np.random.seed(42)


@pytest.fixture
def mock_portfolio():
    """Create a mock portfolio for testing."""
    portfolio = Mock(spec=Portfolio)
    portfolio.total_equity = 100000.0
    portfolio.positions = []
    return portfolio


@pytest.fixture
def sample_position():
    """Create a mock position for testing."""
    position = Mock()
    position.symbol = 'TEST'
    position.market_value = 10000.0
    position.quantity = 100
    return position


@pytest.fixture
def sample_returns():
    """Create sample returns for testing."""
    np.random.seed(42)
    return np.random.normal(0.001, 0.02, 500)


@pytest.fixture
def sample_returns_bullish():
    """Create bullish returns (positive drift)."""
    np.random.seed(42)
    return np.random.normal(0.0015, 0.015, 500)


@pytest.fixture
def sample_returns_bearish():
    """Create bearish returns (negative drift)."""
    np.random.seed(42)
    return np.random.normal(-0.0005, 0.025, 500)


@pytest.fixture
def sample_returns_volatile():
    """Create highly volatile returns."""
    np.random.seed(42)
    return np.random.normal(0, 0.05, 500)


@pytest.fixture
def default_var_config():
    """Default VaR calculator configuration."""
    return {
        'confidence_level': 0.95,
        'time_horizon': 1,
    }


@pytest.fixture
def default_alert_config():
    """Default alert system configuration."""
    return {
        'thresholds': {
            'var_breach': 0.05,
            'drawdown_limit': 0.15,
            'exposure_limit': 0.20,
            'leverage_limit': 1.0,
            'correlation_limit': 0.8,
            'violation_count': 5,
        },
        'enable_email': False,
        'enable_slack': False,
        'enable_logging': True,
        'cooldown_period_minutes': 60,
    }


@pytest.fixture
def default_limits_config():
    """Default risk limits configuration."""
    return {
        'var_warning_limit': 0.02,
        'var_critical_limit': 0.03,
        'var_halt_limit': 0.05,
        'max_position_pct': 0.20,
        'max_concentration_pct': 0.40,
        'max_leverage': 2.0,
        'max_drawdown_pct': 0.15,
    }


def pytest_configure(config):
    """
    Configure pytest with custom markers.

    This adds the 'unit' marker for unit tests.
    """
    config.addinivalue_line("markers", "unit: Unit test")


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test location.

    Automatically marks all tests in this directory as unit tests.
    """
    for item in items:
        # Mark all tests in risk_engine directory as unit tests
        if "risk_engine" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
