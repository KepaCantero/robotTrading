"""
Tests for TradingBridgeOrchestrator - Alert-to-Trade Orchestration

Tests cover:
- Bridge lifecycle (start/stop)
- Alert processing and trade execution
- Risk validation integration
- Order execution and monitoring
- Error handling and recovery
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.alerting_system import AlertEvent, AlertSeverity
from app.services.live_trading.alert_to_trade_mapper import AlertToTradeRule, TradeSignalType
from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerConnector,
    BrokerType,
    OrderSide,
    OrderStatus,
)
from app.services.live_trading.trading_bridge_orchestrator import (
    BridgeStatus,
    TradingBridgeOrchestrator,
)


@pytest.mark.asyncio
class TestBridgeLifecycle:
    """Test bridge startup and shutdown."""

    async def test_bridge_start(self):
        """Test starting the trading bridge."""
        bridge = TradingBridgeOrchestrator()
        assert bridge.is_active is False

        result = await bridge.start()
        assert result is True
        assert bridge.is_active is True
        assert bridge.status == BridgeStatus.MONITORING

    async def test_bridge_stop(self):
        """Test stopping the trading bridge."""
        bridge = TradingBridgeOrchestrator()
        await bridge.start()
        assert bridge.is_active is True

        result = await bridge.stop()
        assert result is True
        assert bridge.is_active is False
        assert bridge.status == BridgeStatus.IDLE

    async def test_start_already_active(self):
        """Test starting when already active."""
        bridge = TradingBridgeOrchestrator()
        await bridge.start()

        # Try to start again
        result = await bridge.start()
        assert result is False


class TestAlertProcessing:
    """Test alert processing and trade signal generation."""

    def _create_mock_account(
        self,
        cash: str = "100000",
        portfolio: str = "500000",
    ) -> BrokerAccount:
        """Helper to create properly configured mock BrokerAccount."""
        return BrokerAccount(
            account_id="acc_001",
            broker_type=BrokerType.PAPER,
            cash_available=Decimal(cash),
            portfolio_value=Decimal(portfolio),
            buying_power=Decimal("200000"),
            equity=Decimal(portfolio),
        )

    @pytest.mark.asyncio
    async def test_process_alert_inactive_bridge(self):
        """Test processing alert when bridge is inactive."""
        bridge = TradingBridgeOrchestrator()
        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        result = await bridge.process_alert(alert)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_alert_no_matching_rule(self):
        """Test processing alert with no matching trade rule."""
        bridge = TradingBridgeOrchestrator()
        await bridge.start()

        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
        )

        result = await bridge.process_alert(alert)
        # No matching rule, so no trade execution
        assert result is None

    @pytest.mark.asyncio
    async def test_process_alert_with_rule(self):
        """Test processing alert with matching trade rule."""
        # Create mock broker
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(return_value=self._create_mock_account("50000", "100000"))
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("100000"))
        mock_broker.place_order = AsyncMock(
            return_value=MagicMock(
                order_id="order_001",
                status=OrderStatus.SUBMITTED,
            )
        )
        mock_broker.get_order_status = AsyncMock(return_value=OrderStatus.PENDING)

        bridge = TradingBridgeOrchestrator(broker=mock_broker)

        # Register trade rule
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="rule_001",
            signal_type=TradeSignalType.LONG,
            base_quantity=Decimal("100"),
        )
        bridge.mapper.register_rule(rule)

        await bridge.start()

        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        result = await bridge.process_alert(alert)
        assert result is not None
        assert result.execution_status == OrderStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_alert_severity_affects_quantity(self):
        """Test that alert severity affects trade quantity."""
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(return_value=self._create_mock_account())
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("100000"))
        mock_broker.place_order = AsyncMock(
            return_value=MagicMock(
                order_id="order_001",
                status=OrderStatus.SUBMITTED,
            )
        )
        mock_broker.get_order_status = AsyncMock(return_value=OrderStatus.PENDING)

        bridge = TradingBridgeOrchestrator(broker=mock_broker)

        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="rule_001",
            base_quantity=Decimal("100"),
        )
        bridge.mapper.register_rule(rule)

        await bridge.start()

        # Critical alert should result in larger quantity (2x multiplier)
        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.CRITICAL,
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        result = await bridge.process_alert(alert)
        assert result is not None
        # Quantity should be 100 * 2.0 (critical multiplier) = 200
        assert result.quantity == Decimal("200")


class TestRiskValidation:
    """Test risk gate validation."""

    @pytest.mark.asyncio
    async def test_position_size_validation(self):
        """Test position size against risk limits."""
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_account = MagicMock()
        mock_account.cash_available = Decimal("10000")
        mock_account.portfolio_value = Decimal("50000")

        mock_broker.get_account_info = AsyncMock(return_value=mock_account)
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("50000"))

        bridge = TradingBridgeOrchestrator(broker=mock_broker)

        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="rule_001",
            base_quantity=Decimal("100"),
            max_position_size=Decimal("5000"),
        )
        bridge.mapper.register_rule(rule)

        await bridge.start()

        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        result = await bridge.process_alert(alert)
        # Should either pass or be constrained by risk limits
        if result is not None:
            position_value = result.quantity * Decimal("150")
            assert position_value <= Decimal("5000")

    @pytest.mark.asyncio
    async def test_insufficient_cash_blocks_trade(self):
        """Test that insufficient cash blocks trade execution."""
        mock_broker = MagicMock(spec=BrokerConnector)
        # Use proper BrokerAccount with limited buying power
        mock_broker.get_account_info = AsyncMock(
            return_value=BrokerAccount(
                account_id="acc_001",
                broker_type=BrokerType.PAPER,
                cash_available=Decimal("1000"),  # Not enough for trade
                portfolio_value=Decimal("50000"),
                buying_power=Decimal("1000"),  # Limited buying power
                equity=Decimal("50000"),
            )
        )
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("50000"))

        bridge = TradingBridgeOrchestrator(broker=mock_broker)

        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="rule_001",
            base_quantity=Decimal("100"),
        )
        bridge.mapper.register_rule(rule)

        await bridge.start()

        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.CRITICAL,  # 100 * 2.0 = 200 shares
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        result = await bridge.process_alert(alert)
        # Should fail due to insufficient buying power for 200 * 150 = 30000
        assert result is None


class TestExecutionRecords:
    """Test execution record management."""

    @pytest.mark.asyncio
    async def test_get_execution(self):
        """Test retrieving execution record."""
        bridge = TradingBridgeOrchestrator()
        # Manually add execution for testing
        from app.services.live_trading.trading_bridge_orchestrator import AlertToTradeExecution

        execution = AlertToTradeExecution(
            execution_id="exec_001",
            alert_id="evt_001",
            signal_id="signal_001",
            order_id="order_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
        )
        bridge.executions["exec_001"] = execution

        retrieved = bridge.get_execution("exec_001")
        assert retrieved is not None
        assert retrieved.execution_id == "exec_001"

    def test_get_recent_executions(self):
        """Test retrieving recent executions."""
        from app.services.live_trading.trading_bridge_orchestrator import AlertToTradeExecution

        bridge = TradingBridgeOrchestrator()

        # Add multiple executions
        for i in range(5):
            execution = AlertToTradeExecution(
                execution_id=f"exec_{i:03d}",
                alert_id=f"evt_{i:03d}",
                signal_id=f"signal_{i:03d}",
                order_id=f"order_{i:03d}",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=Decimal("100"),
            )
            bridge.execution_history.append(execution)

        recent = bridge.get_recent_executions(limit=3)
        assert len(recent) == 3
        # Most recent is at index 0 (after reversing)
        assert recent[0].execution_id == "exec_004"

    def test_bridge_statistics(self):
        """Test bridge statistics collection."""
        from app.services.live_trading.trading_bridge_orchestrator import AlertToTradeExecution

        bridge = TradingBridgeOrchestrator()

        # Add executions with different statuses
        execution1 = AlertToTradeExecution(
            execution_id="exec_001",
            alert_id="evt_001",
            signal_id="signal_001",
            order_id="order_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            execution_status=OrderStatus.FILLED,
        )
        bridge.execution_history.append(execution1)

        execution2 = AlertToTradeExecution(
            execution_id="exec_002",
            alert_id="evt_002",
            signal_id="signal_002",
            order_id="order_002",
            symbol="TSLA",
            side=OrderSide.SELL,
            quantity=Decimal("50"),
            execution_status=OrderStatus.CANCELED,
        )
        bridge.execution_history.append(execution2)

        stats = bridge.get_bridge_statistics()
        assert stats["total_executions"] == 2
        assert stats["successful_trades"] == 1
        assert stats["failed_trades"] == 1
        assert stats["status"] == "idle"


class TestErrorHandling:
    """Test error handling and recovery."""

    def _create_mock_account(
        self,
        cash: str = "100000",
        portfolio: str = "500000",
    ) -> BrokerAccount:
        """Helper to create properly configured mock BrokerAccount."""
        return BrokerAccount(
            account_id="acc_001",
            broker_type=BrokerType.PAPER,
            cash_available=Decimal(cash),
            portfolio_value=Decimal(portfolio),
            buying_power=Decimal(cash),
            equity=Decimal(portfolio),
        )

    @pytest.mark.asyncio
    async def test_alert_processing_error(self):
        """Test graceful handling of alert processing errors."""
        mock_broker = MagicMock(spec=BrokerConnector)
        # Use ConnectionError which is a caught exception type
        mock_broker.get_account_info = AsyncMock(side_effect=ConnectionError("Connection error"))

        bridge = TradingBridgeOrchestrator(broker=mock_broker)
        await bridge.start()

        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        result = await bridge.process_alert(alert)
        assert result is None
        assert bridge.status == BridgeStatus.ERROR

    @pytest.mark.asyncio
    async def test_error_recorded(self):
        """Test that errors are recorded for audit."""
        mock_broker = MagicMock(spec=BrokerConnector)
        # Use ConnectionError which is a caught exception type
        mock_broker.get_account_info = AsyncMock(side_effect=ConnectionError("Broker connection failed"))

        bridge = TradingBridgeOrchestrator(broker=mock_broker)
        await bridge.start()

        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
        )

        await bridge.process_alert(alert)
        assert "evt_001" in bridge.errors
        assert "connection" in bridge.errors["evt_001"][1].lower()
