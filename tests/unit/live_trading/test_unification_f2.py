"""Fase 2 unification (hallazgos A03/A17).

- A03: ONE authoritative RiskGates per account. The OrderManager singleton,
  the TradingBridgeOrchestrator and the API's PATCH /live-trading/risk/limits
  all share get_risk_gates(); a limit change reaches the orders (audit
  acceptance: "cambiar el límite y comprobar el rechazo de una orden").
- A17: every open order keeps its own monitor task — a new order no longer
  cancels the previous order's watcher, and stop() cancels them all.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.services.live_trading.order_manager as order_manager_module
import app.services.live_trading.risk_gates as risk_gates_module
from app.services.alerting_system import AlertEvent, AlertSeverity
from app.services.live_trading.alert_to_trade_mapper import AlertToTradeRule
from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerConnector,
    BrokerType,
    OrderSide,
    OrderStatus,
)
from app.services.live_trading.order_manager import get_order_manager
from app.services.live_trading.risk_gates import get_risk_gates
from app.services.live_trading.trading_bridge_orchestrator import TradingBridgeOrchestrator
from tests.unit.live_trading.test_trading_bridge_orchestrator import _fresh_quote


@pytest.fixture
def singletons_reset():
    """Isolate the OrderManager/RiskGates singletons around each test."""
    manager_orig = order_manager_module._manager
    gates_orig = risk_gates_module._gates
    order_manager_module._manager = None
    risk_gates_module._gates = None
    yield
    order_manager_module._manager = manager_orig
    risk_gates_module._gates = gates_orig


class TestSingleRiskGates:
    """A03: one authoritative risk service shared by every path."""

    def test_order_manager_shares_the_risk_gates_singleton(self, singletons_reset):
        manager = get_order_manager()
        assert manager.risk_gates is get_risk_gates()

    @pytest.mark.asyncio
    async def test_limit_change_reaches_new_orders(self, singletons_reset):
        # Same effect as PATCH /live-trading/risk/limits (it mutates the
        # shared singleton): lower the position cap, then an order that
        # used to pass must now be rejected by the SAME gates the
        # OrderManager validates against.
        manager = get_order_manager()
        gates = get_risk_gates()
        assert manager.risk_gates is gates

        gates.set_max_position_size(Decimal("1000"))
        # The shared paper connector must be connected for account info.
        await manager.broker.adapter.connect()
        # SPY quote ~763 (fresh repo CSV): 5 shares ~= 3815 > 1000 cap.
        order = await manager.place_order("SPY", OrderSide.BUY, Decimal("5"))
        assert order is None
        assert any(
            "Projected SPY exposure" in v or "exceeds max position size" in v
            for v in [manager.last_rejection or ""]
        )


class TestPerOrderMonitors:
    """A17: monitors keyed by order, cancelled only on shutdown."""

    @pytest.fixture
    def bridge(self):
        mock_broker = MagicMock(spec=BrokerConnector)
        mock_broker.get_account_info = AsyncMock(
            return_value=BrokerAccount(
                account_id="acc",
                broker_type=BrokerType.PAPER,
                cash_available=Decimal("50000"),
                portfolio_value=Decimal("100000"),
                buying_power=Decimal("100000"),
                equity=Decimal("100000"),
                connected=True,
            )
        )
        mock_broker.get_positions = AsyncMock(return_value={})
        mock_broker.get_quote = AsyncMock(return_value=_fresh_quote("AAPL", "150"))
        mock_broker.calculate_portfolio_value = AsyncMock(return_value=Decimal("100000"))
        placed = []

        async def place_order(**kwargs):
            placed.append(kwargs)
            order = MagicMock()
            order.order_id = f"ord_{len(placed)}"
            order.status = OrderStatus.SUBMITTED
            return order

        mock_broker.place_order = place_order
        mock_broker.get_order_status = AsyncMock(return_value=OrderStatus.PENDING)

        orchestrator = TradingBridgeOrchestrator(broker=mock_broker)
        orchestrator.mapper.register_rule(
            AlertToTradeRule(
                rule_id="rule_001",
                alert_rule_id="rule_001",
                base_quantity=Decimal("10"),
            )
        )
        return orchestrator

    @pytest.mark.asyncio
    async def test_second_order_does_not_cancel_first_monitor(self, bridge):
        import asyncio

        await bridge.start()
        first = await bridge.process_alert(
            AlertEvent(
                event_id="evt_1",
                rule_id="rule_001",
                severity=AlertSeverity.WARNING,
                symbol="AAPL",
                metric_value=Decimal("150"),
            )
        )
        second = await bridge.process_alert(
            AlertEvent(
                event_id="evt_2",
                rule_id="rule_001",
                severity=AlertSeverity.WARNING,
                symbol="AAPL",
                metric_value=Decimal("150"),
            )
        )
        assert first is not None and second is not None
        assert first.order_id != second.order_id
        # Both monitors alive simultaneously — the old code cancelled the
        # first one when the second order arrived.
        await asyncio.sleep(0)  # let tasks start
        assert len(bridge._monitor_tasks) == 2
        for task in bridge._monitor_tasks.values():
            assert not task.done()

        await bridge.stop()
        assert len(bridge._monitor_tasks) == 0
