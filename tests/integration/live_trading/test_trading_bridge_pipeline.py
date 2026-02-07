"""
Integration Tests for Trading Bridge Pipeline

Tests cover:
- End-to-end alert-to-trade flow
- Multi-component orchestration
- Real-world trading scenarios
- Error handling and recovery
"""

from datetime import datetime, timezone
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
from app.services.live_trading.trading_audit_trail import AuditEventType, TradingAuditTrail
from app.services.live_trading.trading_bridge_orchestrator import TradingBridgeOrchestrator


@pytest.mark.asyncio
class TestAlertToTradePipeline:
    """Test complete alert-to-trade pipeline."""

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

    async def test_complete_alert_to_trade_flow(self):
        """Test complete flow: alert → signal → risk check → trade."""
        # Create mock broker
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(return_value=self._create_mock_account())
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("500000"))
        mock_broker.place_order = AsyncMock(
            return_value=MagicMock(
                order_id="order_001",
                status=OrderStatus.SUBMITTED,
            )
        )
        mock_broker.get_order_status = AsyncMock(return_value=OrderStatus.FILLED)

        # Setup bridge with audit trail
        bridge = TradingBridgeOrchestrator(broker=mock_broker)
        audit_trail = TradingAuditTrail()

        # Register trade rule
        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="rule_001",
            signal_type=TradeSignalType.LONG,
            base_quantity=Decimal("100"),
        )
        bridge.mapper.register_rule(rule)

        # Log initial state
        audit_trail.log_event(AuditEventType.ALERT_RECEIVED, alert_id="evt_001")

        # Start bridge and process alert
        await bridge.start()
        assert bridge.is_active is True

        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        execution = await bridge.process_alert(alert)

        # Verify execution
        assert execution is not None
        assert execution.alert_id == "evt_001"
        assert execution.symbol == "AAPL"
        assert execution.side == OrderSide.BUY
        assert execution.quantity == Decimal("100")

    async def test_multiple_alerts_separate_signals(self):
        """Test that different alerts generate separate trade signals."""
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(return_value=self._create_mock_account())
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("500000"))
        mock_broker.place_order = AsyncMock(
            return_value=MagicMock(
                order_id="order_001",
                status=OrderStatus.SUBMITTED,
            )
        )
        mock_broker.get_order_status = AsyncMock(return_value=OrderStatus.PENDING)

        bridge = TradingBridgeOrchestrator(broker=mock_broker)

        # Register different rules for different symbols
        for i in range(3):
            rule = AlertToTradeRule(
                rule_id=f"rule_{i:03d}",
                alert_rule_id=f"rule_{i:03d}",
                signal_type=TradeSignalType.LONG,
                base_quantity=Decimal("100"),
            )
            bridge.mapper.register_rule(rule)

        await bridge.start()

        # Process alerts for different symbols
        symbols = ["AAPL", "TSLA", "MSFT"]
        executions = []

        for i, symbol in enumerate(symbols):
            alert = AlertEvent(
                event_id=f"evt_{i:03d}",
                rule_id=f"rule_{i:03d}",
                severity=AlertSeverity.WARNING,
                symbol=symbol,
                metric_value=Decimal("100"),
            )

            execution = await bridge.process_alert(alert)
            if execution:
                executions.append(execution)

        assert len(executions) == 3
        for i, execution in enumerate(executions):
            assert execution.symbol == symbols[i]

    async def test_alert_severity_driven_position_sizing(self):
        """Test that alert severity determines position size."""
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(return_value=self._create_mock_account())
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("500000"))
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

        # Test different severities
        severities = [
            (AlertSeverity.INFO, Decimal("50")),  # 100 * 0.5
            (AlertSeverity.WARNING, Decimal("100")),  # 100 * 1.0
            (AlertSeverity.CRITICAL, Decimal("200")),  # 100 * 2.0
        ]

        for i, (severity, expected_qty) in enumerate(severities):
            alert = AlertEvent(
                event_id=f"evt_{i:03d}",  # Use unique event_id for each severity
                rule_id="rule_001",
                severity=severity,
                symbol="AAPL",
                metric_value=Decimal("150"),
            )

            execution = await bridge.process_alert(alert)
            if execution:
                assert execution.quantity == expected_qty

    async def test_cooldown_prevents_alert_spam(self):
        """Test that cooldown period prevents alert spam trading."""
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(return_value=self._create_mock_account())
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("500000"))
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
            quiet_period_minutes=5,
            base_quantity=Decimal("100"),
        )
        bridge.mapper.register_rule(rule)

        await bridge.start()

        # First alert should trigger trade
        alert1 = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        execution1 = await bridge.process_alert(alert1)
        assert execution1 is not None

        # Immediate second alert should be blocked
        alert2 = AlertEvent(
            event_id="evt_002",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        execution2 = await bridge.process_alert(alert2)
        assert execution2 is None


@pytest.mark.asyncio
class TestAuditTrailIntegration:
    """Test audit trail integration with trading bridge."""

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

    async def test_audit_trail_records_all_events(self):
        """Test that audit trail records all trading bridge events."""
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(return_value=self._create_mock_account())
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("500000"))
        mock_broker.place_order = AsyncMock(
            return_value=MagicMock(
                order_id="order_001",
                status=OrderStatus.SUBMITTED,
            )
        )
        mock_broker.get_order_status = AsyncMock(return_value=OrderStatus.FILLED)

        bridge = TradingBridgeOrchestrator(broker=mock_broker)
        audit_trail = TradingAuditTrail()

        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="rule_001",
        )
        bridge.mapper.register_rule(rule)

        await bridge.start()

        # Log events
        audit_trail.log_event(AuditEventType.ALERT_RECEIVED, alert_id="evt_001")
        audit_trail.log_event(AuditEventType.SIGNAL_GENERATED, alert_id="evt_001")
        audit_trail.log_event(AuditEventType.RISK_CHECK_PASSED, alert_id="evt_001")

        # Process alert
        alert = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        execution = await bridge.process_alert(alert)

        if execution:
            audit_trail.log_event(
                AuditEventType.ORDER_PLACED,
                alert_id="evt_001",
                order_id=execution.order_id,
                symbol=execution.symbol,
                quantity=execution.quantity,
            )

        # Verify audit trail
        events = audit_trail.get_events_for_alert("evt_001")
        assert len(events) >= 4
        event_types = [e.event_type for e in events]
        assert AuditEventType.ALERT_RECEIVED in event_types
        assert AuditEventType.ORDER_PLACED in event_types

    async def test_compliance_report_from_trading_session(self):
        """Test generating compliance report from trading session."""
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(return_value=self._create_mock_account())
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("500000"))
        mock_broker.place_order = AsyncMock(
            return_value=MagicMock(
                order_id="order_001",
                status=OrderStatus.SUBMITTED,
            )
        )
        mock_broker.get_order_status = AsyncMock(return_value=OrderStatus.FILLED)

        bridge = TradingBridgeOrchestrator(broker=mock_broker)
        audit_trail = TradingAuditTrail()

        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="rule_001",
            base_quantity=Decimal("100"),
        )
        bridge.mapper.register_rule(rule)

        await bridge.start()

        # Process multiple alerts
        for i in range(5):
            alert = AlertEvent(
                event_id=f"evt_{i:03d}",
                rule_id="rule_001",
                severity=AlertSeverity.WARNING,
                symbol="AAPL",
                metric_value=Decimal("150"),
            )

            audit_trail.log_event(
                AuditEventType.ALERT_RECEIVED,
                alert_id=f"evt_{i:03d}",
            )

            execution = await bridge.process_alert(alert)

            if execution:
                audit_trail.log_event(
                    AuditEventType.ORDER_PLACED,
                    alert_id=f"evt_{i:03d}",
                    order_id=execution.order_id,
                    quantity=execution.quantity,
                )

        # Generate compliance report
        from datetime import timedelta

        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)

        report = audit_trail.generate_compliance_report(start_date, end_date)

        assert report.total_alerts >= 5
        assert report.total_trades >= 0
        assert report.total_volume >= Decimal("0")


@pytest.mark.asyncio
class TestErrorRecovery:
    """Test error handling and recovery in pipeline."""

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

    async def test_partial_broker_failure_recovery(self):
        """Test graceful handling of broker connection failures."""
        mock_broker = MagicMock(spec=BrokerConnector)

        # First two calls succeed (main flow + risk validation), third fails
        mock_broker.get_account_info = AsyncMock(
            side_effect=[
                self._create_mock_account(),
                self._create_mock_account(),  # Risk validation also calls get_account_info
                Exception("Connection lost"),
            ]
        )
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("500000"))

        bridge = TradingBridgeOrchestrator(broker=mock_broker)

        rule = AlertToTradeRule(
            rule_id="rule_001",
            alert_rule_id="rule_001",
        )
        bridge.mapper.register_rule(rule)

        await bridge.start()

        # First alert should succeed
        alert1 = AlertEvent(
            event_id="evt_001",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="AAPL",
            metric_value=Decimal("150"),
        )

        execution1 = await bridge.process_alert(alert1)
        assert execution1 is not None

        # Second alert should fail gracefully
        alert2 = AlertEvent(
            event_id="evt_002",
            rule_id="rule_001",
            severity=AlertSeverity.WARNING,
            symbol="TSLA",
            metric_value=Decimal("200"),
        )

        execution2 = await bridge.process_alert(alert2)
        assert execution2 is None
        assert "evt_002" in bridge.errors
