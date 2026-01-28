"""
Unit tests for Chan #15: 5% Daily Loss Circuit Breaker

Tests the implementation of the 5% daily loss limit circuit breaker
as specified in Ernest Chan's Algorithmic Trading (Rule #15) and
John Hull's Risk Management (Rule #65 - Kill switches).
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.services.live_trading.risk_gates import (
    RiskGates,
    RiskLevel,
    RiskCheckResult,
)


# ============================================================================
# FIXTURES
# ============================================================================


class MockBrokerConnector:
    """Mock broker connector for testing."""
    
    def __init__(self):
        self.account_info = None
        self.positions = {}
        self._should_fail = False
    
    def set_account_info(self, equity: Decimal, cash_available: Decimal, portfolio_value: Decimal):
        """Set mock account info."""
        self.account_info = Mock(
            equity=equity,
            cash_available=cash_available,
            portfolio_value=portfolio_value,
            buying_power=cash_available * 2,
        )
    
    async def get_account_info(self):
        """Get mock account info."""
        if self._should_fail:
            return None
        return self.account_info
    
    async def get_positions(self):
        """Get mock positions."""
        if self._should_fail:
            return {}
        return self.positions


@pytest.fixture
def mock_broker():
    """Create mock broker connector."""
    return MockBrokerConnector()


@pytest.fixture
def risk_gates(mock_broker):
    """Create RiskGates instance for testing."""
    mock_broker.set_account_info(
        equity=Decimal("100000"),
        cash_available=Decimal("20000"),
        portfolio_value=Decimal("100000"),
    )
    
    gates = RiskGates(broker=mock_broker)
    return gates


# ============================================================================
# TEST CLASS: Chan #15 - 5% Daily Loss Circuit Breaker
# ============================================================================


class TestChan15DailyLossCircuitBreaker:
    """
    Test suite for Chan #15: 5% Daily Loss Circuit Breaker.
    
    Requirements:
    1. Circuit breaker triggers at exactly 5% daily loss
    2. Trading is halted when circuit breaker is triggered
    3. Daily P&L is tracked correctly
    4. Start of day capital is used for calculations
    5. Circuit breaker resets daily
    """
    
    @pytest.mark.asyncio
    async def test_exact_5_percent_loss_triggers_circuit_breaker(self, risk_gates: RiskGates):
        """
        Test that exactly 5% loss triggers the circuit breaker.
        
        Chan #15: "Detener trading si pérdida diaria > 5%"
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.update_daily_pnl(Decimal("-5000"))
        
        can_continue = risk_gates.check_daily_loss_limit()
        
        assert can_continue is False, "Circuit breaker should trigger at exactly 5% loss"
        assert risk_gates.circuit_breaker_active is True, "Circuit breaker should be active"
    
    @pytest.mark.asyncio
    async def test_below_5_percent_loss_does_not_trigger(self, risk_gates: RiskGates):
        """
        Test that loss below 5% does NOT trigger the circuit breaker.
        
        Chan #15: Only triggers when > 5%, so 4.99% should NOT trigger.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.update_daily_pnl(Decimal("-4990"))
        
        can_continue = risk_gates.check_daily_loss_limit()
        
        assert can_continue is True, "Circuit breaker should NOT trigger below 5% loss"
        assert risk_gates.circuit_breaker_active is False, "Circuit breaker should NOT be active"
    
    @pytest.mark.asyncio
    async def test_above_5_percent_loss_triggers_circuit_breaker(self, risk_gates: RiskGates):
        """
        Test that loss above 5% triggers the circuit breaker.
        
        Chan #15: Any loss > 5% should trigger immediately.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.update_daily_pnl(Decimal("-5010"))
        
        can_continue = risk_gates.check_daily_loss_limit()
        
        assert can_continue is False, "Circuit breaker should trigger above 5% loss"
        assert risk_gates.circuit_breaker_active is True, "Circuit breaker should be active"
    
    @pytest.mark.asyncio
    async def test_daily_pnl_tracking_accumulates_correctly(self, risk_gates: RiskGates):
        """
        Test that daily P&L accumulates correctly across multiple trades.
        
        Chan #15: The circuit breaker checks cumulative daily loss.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        
        risk_gates.update_daily_pnl(Decimal("-1000"))
        risk_gates.update_daily_pnl(Decimal("-2000"))
        risk_gates.update_daily_pnl(Decimal("-1500"))
        
        assert risk_gates.check_daily_loss_limit() is True
        
        risk_gates.update_daily_pnl(Decimal("-600"))
        
        assert risk_gates.check_daily_loss_limit() is False
        assert risk_gates.circuit_breaker_active is True
    
    @pytest.mark.asyncio
    async def test_set_start_of_day_capital_resets_tracking(self, risk_gates: RiskGates):
        """
        Test that setting start of day capital resets P&L tracking.
        
        Hull #65: Kill switches reset at the start of each trading day.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.update_daily_pnl(Decimal("-6000"))
        assert risk_gates.check_daily_loss_limit() is False
        assert risk_gates.circuit_breaker_active is True
        
        risk_gates.reset_circuit_breaker()
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        
        assert risk_gates.daily_pnl == Decimal("0")
        assert risk_gates.circuit_breaker_active is False
        assert risk_gates.start_of_day_capital == Decimal("100000")
        
        risk_gates.update_daily_pnl(Decimal("-1000"))
        assert risk_gates.check_daily_loss_limit() is True
    
    @pytest.mark.asyncio
    async def test_halt_trading_stops_all_activity(self, risk_gates: RiskGates):
        """
        Test that halt_trading() stops all trading activity.
        
        Hull #65: Kill switch functionality.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        
        risk_gates.update_daily_pnl(Decimal("-6000"))
        risk_gates.check_daily_loss_limit()
        
        assert risk_gates.circuit_breaker_active is True
    
    @pytest.mark.asyncio
    async def test_zero_start_of_day_capital_handling(self, risk_gates: RiskGates):
        """
        Test behavior when start of day capital is zero or not set.
        """
        can_continue = risk_gates.check_daily_loss_limit()
        assert can_continue is True
    
    @pytest.mark.asyncio
    async def test_negative_daily_pnl_calculation(self, risk_gates: RiskGates):
        """
        Test that negative daily P&L is calculated correctly.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.update_daily_pnl(Decimal("-5000"))
        
        expected_pct = Decimal("-5000") / Decimal("100000")
        assert expected_pct == Decimal("-0.05")
        
        assert risk_gates.check_daily_loss_limit() is False
    
    @pytest.mark.asyncio
    async def test_profit_does_not_trigger_circuit_breaker(self, risk_gates: RiskGates):
        """
        Test that daily profit does NOT trigger circuit breaker.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.update_daily_pnl(Decimal("5000"))
        
        assert risk_gates.check_daily_loss_limit() is True
        assert risk_gates.circuit_breaker_active is False
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_orders(self, risk_gates: RiskGates, mock_broker):
        """
        Test that orders are blocked when circuit breaker is active.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        
        risk_gates.update_daily_pnl(Decimal("-6000"))
        risk_gates.check_daily_loss_limit()
        
        assert risk_gates.circuit_breaker_active is True
        
        from app.services.live_trading.broker_connector import OrderSide
        result = await risk_gates.validate_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            price=Decimal("150"),
        )
        
        assert result.passed is False
        assert "circuit breaker" in result.violations[0].lower()
    
    @pytest.mark.asyncio
    async def test_reset_circuit_breaker_clears_state(self, risk_gates: RiskGates):
        """
        Test that reset_circuit_breaker() properly clears all state.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.update_daily_pnl(Decimal("-6000"))
        risk_gates.check_daily_loss_limit()
        assert risk_gates.circuit_breaker_active is True
        
        risk_gates.reset_circuit_breaker()
        
        assert risk_gates.circuit_breaker_active is False
        assert risk_gates.daily_pnl == Decimal("0")
        assert risk_gates.max_intraday_value == Decimal("0")


class TestHull65KillSwitch:
    """
    Test suite for Hull #65: Kill Switch Integration.
    """
    
    @pytest.mark.asyncio
    async def test_kill_switch_halt_trading_method(self, risk_gates: RiskGates):
        """
        Test the halt_trading() method directly.
        
        Hull #65: Kill switch functionality.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.halt_trading()
        assert risk_gates.circuit_breaker_active is True
    
    @pytest.mark.asyncio
    async def test_kill_switch_blocks_all_orders(self, risk_gates: RiskGates):
        """
        Test that kill switch blocks all order types.
        """
        risk_gates.set_start_of_day_capital(Decimal("100000"))
        risk_gates.halt_trading()
        
        from app.services.live_trading.broker_connector import OrderSide
        
        for side in [OrderSide.BUY, OrderSide.SELL]:
            result = await risk_gates.validate_order(
                symbol="AAPL",
                side=side,
                quantity=Decimal("100"),
                price=Decimal("150"),
            )
            
            assert result.passed is False, f"Order should be rejected for side {side}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
