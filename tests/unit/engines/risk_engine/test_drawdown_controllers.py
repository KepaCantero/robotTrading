"""
Unit tests for Drawdown Controllers.

Tests for drawdown calculation and control mechanisms.
"""
import pytest
import numpy as np
from unittest.mock import Mock

from app.engines.risk_engine.drawdown_controllers.drawdown_controllers import (
    DrawdownController,
    CircuitBreakerController,
    PeakDrawdownController,
)


@pytest.fixture
def sample_equity_curve():
    """Create sample equity curve."""
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.02, 500)
    equity = [100000.0]
    for r in returns:
        equity.append(equity[-1] * (1 + r))
    return equity


@pytest.fixture
def drawdown_controller():
    """Create DrawdownController instance."""
    return DrawdownController({})


@pytest.mark.unit
class TestDrawdownController:
    """Test drawdown controller functionality."""

    def test_calculate_drawdown(self, drawdown_controller, sample_equity_curve):
        """Test drawdown calculation."""
        result = drawdown_controller.calculate_drawdown(sample_equity_curve)

        assert 'current_drawdown' in result
        assert 'max_drawdown' in result
        assert 'peak_equity' in result

    def test_drawdown_range(self, drawdown_controller, sample_equity_curve):
        """Test that drawdown is in valid range."""
        result = drawdown_controller.calculate_drawdown(sample_equity_curve)

        assert -1 <= result['current_drawdown'] <= 0

    def test_max_drawdown_larger_than_current(self, drawdown_controller, sample_equity_curve):
        """Test that max drawdown >= current drawdown."""
        result = drawdown_controller.calculate_drawdown(sample_equity_curve)

        assert abs(result['max_drawdown']) >= abs(result['current_drawdown'])


@pytest.mark.unit
class TestCircuitBreakerController:
    """Test circuit breaker controller."""

    def test_circuit_breaker_activation(self):
        """Test circuit breaker activates on severe drawdown."""
        controller = CircuitBreakerController({'threshold': 0.10})

        equity = [100000, 90000, 80000, 70000]  # 30% drop
        result = controller.check_circuit_breaker(equity)

        assert 'should_halt' in result

    def test_circuit_breaker_not_triggered(self):
        """Test circuit breaker not triggered on minor drawdown."""
        controller = CircuitBreakerController({'threshold': 0.20})

        equity = [100000, 95000, 90000]  # 10% drop
        result = controller.check_circuit_breaker(equity)

        assert result['should_halt'] is False
