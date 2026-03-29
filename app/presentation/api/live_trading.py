"""
Live Trading API Router - Complete REST API for live trading bridge operations.

Endpoints:
  - Bridge lifecycle management (start/stop)
  - Order management (place, cancel, query)
  - Account/position queries
  - Risk validation
  - Execution history
  - Audit trail and compliance reporting
  - Trading statistics and metrics
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
)
from requests.exceptions import (
    HTTPError,
    RequestException,
)

from app.services.live_trading.account_synchronizer import (
    AccountSynchronizer,
    get_account_synchronizer,
)
from app.services.live_trading.alert_to_trade_mapper import (
    AlertToTradeMapper,
    AlertToTradeRule,
    get_alert_to_trade_mapper,
)
from app.services.live_trading.broker_connector import (
    BrokerConnector,
    OrderSide,
    OrderType,
    get_broker_connector,
)
from app.services.live_trading.order_manager import OrderManager, get_order_manager
from app.services.live_trading.risk_gates import RiskGates, get_risk_gates
from app.services.live_trading.trading_audit_trail import TradingAuditTrail, get_trading_audit_trail
from app.services.live_trading.trading_bridge_orchestrator import (
    TradingBridgeOrchestrator,
    get_trading_bridge_orchestrator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live-trading", tags=["live-trading"])


# ============================================================================
# BRIDGE LIFECYCLE ENDPOINTS
# ============================================================================


@router.post("/start")
async def start_live_trading(
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """Start the live trading bridge.

    This initializes all components and begins monitoring for alerts.
    """
    try:
        await orchestrator.start()
        return {
            "status": "started",
            "message": "Live trading bridge started successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to start live trading bridge: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stop")
async def stop_live_trading(
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """Stop the live trading bridge.

    This gracefully shuts down all components and stops processing alerts.
    """
    try:
        await orchestrator.stop()
        return {
            "status": "stopped",
            "message": "Live trading bridge stopped successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to stop live trading bridge: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status")
async def get_bridge_status(
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """Get current bridge status and statistics."""
    try:
        status = orchestrator.get_bridge_statistics()
        return {
            "is_active": orchestrator.is_active,
            "statistics": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get bridge status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# ORDER MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/orders")
async def place_order(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "MARKET",
    price: float | None = None,
    stop_price: float | None = None,
    order_manager: OrderManager = Depends(get_order_manager),
) -> dict:
    """Place a direct order (not from alert).

    Args:
        symbol: Trading symbol (e.g., 'EUR/USD')
        side: Order side - 'BUY' or 'SELL'
        quantity: Order quantity
        order_type: Order type - 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
        price: Limit price (required for LIMIT orders)
        stop_price: Stop price (required for STOP orders)
    """
    try:
        if order_type == "LIMIT" and price is None:
            raise ValueError("Price required for LIMIT orders")
        if order_type == "STOP" and stop_price is None:
            raise ValueError("Stop price required for STOP orders")

        order_side = OrderSide(side.lower())
        order_type_enum = OrderType(order_type.lower())
        quantity_decimal = Decimal(str(quantity))
        price_decimal: Optional[Decimal] = Decimal(str(price)) if price is not None else None
        stop_price_decimal: Optional[Decimal] = Decimal(str(stop_price)) if stop_price is not None else None

        order_id = await order_manager.place_order(
            symbol=symbol,
            side=order_side,
            quantity=quantity_decimal,
            order_type=order_type_enum,
            price=price_decimal,
            stop_price=stop_price_decimal,
        )

        return {
            "order_id": order_id.order_id if order_id else None,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "status": "SUBMITTED",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to place order: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/orders/{order_id}")
async def get_order_status(
    order_id: str,
    order_manager: OrderManager = Depends(get_order_manager),
) -> dict:
    """Get current status of an order."""
    try:
        status = await order_manager.get_order_status(order_id)
        if not status:
            raise HTTPException(status_code=404, detail="Order not found")

        return {
            "order_id": order_id,
            "status": status.value if status else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get order status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    order_manager: OrderManager = Depends(get_order_manager),
) -> dict:
    """Cancel an open order."""
    try:
        success = await order_manager.cancel_order(order_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel order")

        return {
            "order_id": order_id,
            "status": "CANCELED",
            "message": "Order cancelled successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to cancel order: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/orders/cancel-all")
async def cancel_all_orders(
    order_manager: OrderManager = Depends(get_order_manager),
) -> dict:
    """Cancel all pending orders."""
    try:
        count = await order_manager.cancel_all_orders()
        return {
            "cancelled_count": count,
            "message": f"{count} orders cancelled",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to cancel all orders: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/orders")
async def list_orders(
    status: str | None = None,
    symbol: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    order_manager: OrderManager = Depends(get_order_manager),
) -> dict:
    """List orders with optional filtering.

    Args:
        status: Filter by status (PENDING, EXECUTED, CANCELED, etc.)
        symbol: Filter by symbol
        limit: Maximum results to return (default 100, max 1000)
    """
    try:
        if status == "pending":
            orders = await order_manager.get_pending_orders()
        elif status == "executed":
            orders = await order_manager.get_executed_orders()
        else:
            orders = await order_manager.get_order_history()

        if symbol:
            orders = [o for o in orders if o.symbol == symbol]

        return {
            "count": len(orders),
            "orders": [o.to_dict() if hasattr(o, "to_dict") else {
                "order_id": o.order_id,
                "symbol": o.symbol,
                "side": o.side.value,
                "quantity": str(o.quantity),
                "order_type": o.order_type.value,
                "status": o.status.value,
            } for o in orders[:limit]],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list orders: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# ACCOUNT & POSITION ENDPOINTS
# ============================================================================


@router.get("/account", response_model=None)
async def get_account_info(
    broker: BrokerConnector = Depends(get_broker_connector),
) -> dict:
    """Get current account information and balance."""
    try:
        account = await broker.get_account_info()
        return {
            "account_id": account.account_id,
            "broker_type": account.broker_type.value if account.broker_type else None,
            "currency": account.currency,
            "cash_available": str(account.cash_available),
            "portfolio_value": str(account.portfolio_value),
            "buying_power": str(account.buying_power),
            "equity": str(account.equity),
            "margin_used": str(account.margin_used),
            "margin_multiplier": str(account.multiplier),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get account info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/positions", response_model=None)
async def list_positions(
    broker: BrokerConnector = Depends(get_broker_connector),
) -> dict:
    """Get all current positions."""
    try:
        positions = await broker.get_positions()
        return {
            "count": len(positions),
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": str(p.quantity),
                    "average_price": str(p.avg_price),
                    "current_price": str(p.current_price),
                    "market_value": str(p.market_value),
                    "unrealized_pl": str(p.unrealized_pl),
                    "unrealized_pl_pct": str(p.unrealized_pl_pct),
                }
                for p in positions.values()
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list positions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/positions/{symbol}", response_model=None)
async def get_position(
    symbol: str,
    broker: BrokerConnector = Depends(get_broker_connector),
) -> dict:
    """Get a specific position."""
    try:
        position = await broker.get_position(symbol)
        if not position:
            raise HTTPException(status_code=404, detail=f"No position for {symbol}")

        return {
            "symbol": position.symbol,
            "quantity": str(position.quantity),
            "average_price": str(position.avg_price),
            "current_price": str(position.current_price),
            "market_value": str(position.market_value),
            "unrealized_pl": str(position.unrealized_pl),
            "unrealized_pl_pct": str(position.unrealized_pl_pct),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get position: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# RISK MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/risk/validate", response_model=None)
async def validate_order_risk(
    symbol: str,
    side: str,
    quantity: float,
    risk_gates: RiskGates = Depends(get_risk_gates),
    broker: BrokerConnector = Depends(get_broker_connector),
) -> dict:
    """Validate if an order passes all risk checks.

    Returns risk violations, warnings, and recommended adjustments.
    """
    try:
        account = await broker.get_account_info()
        if not account:
            raise HTTPException(status_code=400, detail="Cannot access account information")

        order_side = OrderSide(side.lower())
        quantity_decimal = Decimal(str(quantity))

        # Determine a price for validation (use equity-based conservative estimate)
        price = account.portfolio_value / Decimal("100") if account.portfolio_value > 0 else Decimal("100")

        result = await risk_gates.validate_order(
            symbol=symbol,
            side=order_side,
            quantity=quantity_decimal,
            price=price,
        )

        return {
            "is_valid": result.passed,
            "risk_level": result.risk_level.value,
            "violations": result.violations,
            "warnings": result.warnings,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to validate order risk: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/risk/limits")
async def get_risk_limits(
    risk_gates: RiskGates = Depends(get_risk_gates),
) -> dict:
    """Get current risk gate configuration and limits."""
    try:
        return {
            "limits": {
                "max_position_size": str(risk_gates.max_position_size),
                "max_leverage": str(risk_gates.max_leverage),
                "max_concentration": str(risk_gates.max_concentration),
                "max_daily_loss": str(risk_gates.max_daily_loss),
                "max_drawdown": str(risk_gates.max_drawdown),
                "min_cash_reserve": str(risk_gates.min_cash_reserve),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get risk limits: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/risk/limits")
async def update_risk_limits(
    max_position_size: float | None = None,
    max_leverage: float | None = None,
    max_concentration: float | None = None,
    max_daily_loss: float | None = None,
    max_drawdown: float | None = None,
    min_cash_reserve: float | None = None,
    risk_gates: RiskGates = Depends(get_risk_gates),
) -> dict:
    """Update risk gate limits dynamically.

    Allows traders to adjust risk parameters without restarting.
    """
    try:
        if max_position_size is not None:
            risk_gates.set_max_position_size(Decimal(str(max_position_size)))
        if max_leverage is not None:
            risk_gates.set_max_leverage(Decimal(str(max_leverage)))
        if max_concentration is not None:
            risk_gates.max_concentration = Decimal(str(max_concentration))
        if max_daily_loss is not None:
            risk_gates.set_max_daily_loss(Decimal(str(max_daily_loss)))
        if max_drawdown is not None:
            risk_gates.set_max_drawdown(Decimal(str(max_drawdown)))
        if min_cash_reserve is not None:
            risk_gates.min_cash_reserve = Decimal(str(min_cash_reserve))

        return {
            "message": "Risk limits updated successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to update risk limits: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# EXECUTION HISTORY ENDPOINTS
# ============================================================================


@router.get("/executions")
async def list_executions(
    status: str | None = None,
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """List execution records with optional filtering.

    Args:
        status: Filter by status (EXECUTED, ERROR, etc.)
        symbol: Filter by symbol
        start_date: Start date (ISO format: YYYY-MM-DD)
        end_date: End date (ISO format: YYYY-MM-DD)
        limit: Maximum results (default 100, max 1000)
    """
    try:
        executions = orchestrator.get_recent_executions(limit=limit)
        execution_dicts = [e.to_dict() for e in executions]

        if status:
            execution_dicts = [e for e in execution_dicts if e.get("status") == status]
        if symbol:
            execution_dicts = [e for e in execution_dicts if e.get("symbol") == symbol]

        if start_date or end_date:
            start = datetime.fromisoformat(start_date) if start_date else datetime.min
            end = datetime.fromisoformat(end_date) if end_date else datetime.now()
            execution_dicts = [
                e
                for e in execution_dicts
                if start <= datetime.fromisoformat(e.get("created_at", "")) <= end
            ]

        return {
            "count": len(execution_dicts),
            "executions": execution_dicts[:limit],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """Get details of a specific execution."""
    try:
        execution = orchestrator.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return {
            "execution": execution.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get execution: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# AUDIT TRAIL & COMPLIANCE ENDPOINTS
# ============================================================================


@router.get("/audit/trail")
async def get_audit_trail(
    event_type: str | None = None,
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    audit_trail: TradingAuditTrail = Depends(get_trading_audit_trail),
) -> dict:
    """Get audit trail events with optional filtering.

    Args:
        event_type: Filter by event type (ALERT_RECEIVED, ORDER_PLACED, etc.)
        symbol: Filter by trading symbol
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        limit: Maximum results
    """
    try:
        events = audit_trail.get_recent_events(limit=limit)
        event_dicts = [e.to_dict() for e in events]

        if event_type:
            event_dicts = [e for e in event_dicts if e.get("event_type") == event_type]
        if symbol:
            event_dicts = [e for e in event_dicts if e.get("symbol") == symbol]

        if start_date or end_date:
            start = datetime.fromisoformat(start_date) if start_date else datetime.min
            end = datetime.fromisoformat(end_date) if end_date else datetime.now()
            event_dicts = [
                e for e in event_dicts if start <= datetime.fromisoformat(e.get("timestamp", "")) <= end
            ]

        return {
            "count": len(event_dicts),
            "events": event_dicts[:limit],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get audit trail: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/audit/report")
async def get_compliance_report(
    days: int = Query(30, ge=1, le=365),
    audit_trail: TradingAuditTrail = Depends(get_trading_audit_trail),
) -> dict:
    """Get compliance report for a period.

    Args:
        days: Number of days to report on (default 30, max 365)
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        report = audit_trail.generate_compliance_report(
            start_date=start_date, end_date=end_date
        )

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days,
            },
            "report": {
                "total_alerts": report.total_alerts,
                "total_trades": report.total_trades,
                "total_executions": report.total_executions,
                "failed_risk_checks": report.failed_risk_checks,
                "non_compliant_events": report.non_compliant_events,
                "total_volume": str(report.total_volume),
                "avg_execution_time_ms": report.avg_execution_time,
                "critical_alerts_count": report.critical_alerts_count,
                "high_risk_trades": report.high_risk_trades,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/audit/non-compliant")
async def list_non_compliant_events(
    limit: int = Query(100, ge=1, le=1000),
    audit_trail: TradingAuditTrail = Depends(get_trading_audit_trail),
) -> dict:
    """Get non-compliant events that require review."""
    try:
        events = audit_trail.get_non_compliant_events()

        return {
            "count": len(events),
            "events": [e.to_dict() for e in events[:limit]],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list non-compliant events: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# STATISTICS & METRICS ENDPOINTS
# ============================================================================


@router.get("/statistics")
async def get_trading_statistics(
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """Get overall trading statistics and performance metrics."""
    try:
        stats = orchestrator.get_bridge_statistics()

        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get trading statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/audit/statistics")
async def get_audit_statistics(
    audit_trail: TradingAuditTrail = Depends(get_trading_audit_trail),
) -> dict:
    """Get audit statistics grouped by event type and risk level."""
    try:
        stats = audit_trail.get_audit_statistics()

        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get audit statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/portfolio/snapshot")
async def get_portfolio_snapshot(
    account_sync: AccountSynchronizer = Depends(get_account_synchronizer),
) -> dict:
    """Get current portfolio snapshot."""
    try:
        snapshot = await account_sync.take_snapshot()

        return {
            "timestamp": snapshot.timestamp.isoformat(),
            "total_value": str(snapshot.total_value),
            "cash": str(snapshot.cash),
            "positions_value": str(snapshot.positions_value),
            "margin_used": str(snapshot.margin_used),
            "buying_power": str(snapshot.buying_power),
            "num_positions": snapshot.num_positions,
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get portfolio snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/portfolio/history")
async def get_portfolio_history(
    days: int = Query(30, ge=1, le=365),
    account_sync: AccountSynchronizer = Depends(get_account_synchronizer),
) -> dict:
    """Get portfolio value history.

    Args:
        days: Number of days to retrieve history for
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        history = await account_sync.get_portfolio_history()
        filtered = [
            s
            for s in history
            if start_date <= s.timestamp <= end_date
        ]

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days,
            },
            "count": len(filtered),
            "history": [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "total_value": str(s.total_value),
                    "cash": str(s.cash),
                    "positions_value": str(s.positions_value),
                }
                for s in filtered
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get portfolio history: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/portfolio/daily-return")
async def get_daily_return(
    account_sync: AccountSynchronizer = Depends(get_account_synchronizer),
) -> dict:
    """Get today's daily P&L return."""
    try:
        daily_return = await account_sync.calculate_daily_return()

        if daily_return is not None:
            return {
                "daily_pnl_pct": str(daily_return),
                "timestamp": datetime.utcnow().isoformat(),
            }
        return {
            "daily_pnl_pct": None,
            "message": "Insufficient data to calculate daily return",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get daily return: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# ALERT-TO-TRADE MAPPING ENDPOINTS
# ============================================================================


@router.post("/rules")
async def create_alert_to_trade_rule(
    rule_data: dict,
    mapper: AlertToTradeMapper = Depends(get_alert_to_trade_mapper),
) -> dict:
    """Create a new alert-to-trade rule.

    Defines how alerts are mapped to trade signals with severity scaling.
    """
    try:
        rule = AlertToTradeRule(
            rule_id=rule_data.get("rule_id", ""),
            alert_rule_id=rule_data.get("alert_rule_id", ""),
            enabled=rule_data.get("enabled", True),
            base_quantity=Decimal(str(rule_data.get("base_quantity", 100))),
            max_position_size=Decimal(str(rule_data.get("max_position_size", 50000))),
        )
        mapper.register_rule(rule)
        return {
            "rule_id": rule.rule_id,
            "message": "Rule created successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to create rule: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/rules/{rule_id}")
async def delete_alert_to_trade_rule(
    rule_id: str,
    mapper: AlertToTradeMapper = Depends(get_alert_to_trade_mapper),
) -> dict:
    """Delete an alert-to-trade rule."""
    try:
        mapper.unregister_rule(rule_id)
        return {
            "rule_id": rule_id,
            "message": "Rule deleted successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to delete rule: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/signals/pending")
async def list_pending_signals(
    limit: int = Query(100, ge=1, le=1000),
    mapper: AlertToTradeMapper = Depends(get_alert_to_trade_mapper),
) -> dict:
    """Get pending (unexecuted) trade signals."""
    try:
        signals = mapper.get_pending_signals()
        return {
            "count": len(signals),
            "signals": [s.to_dict() for s in signals[:limit]],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list pending signals: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/signals/statistics")
async def get_signal_statistics(
    mapper: AlertToTradeMapper = Depends(get_alert_to_trade_mapper),
) -> dict:
    """Get trade signal statistics by type and severity."""
    try:
        stats = mapper.get_signal_statistics()
        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (RequestsConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get signal statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
