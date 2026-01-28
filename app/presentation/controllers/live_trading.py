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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from requests.exceptions import ConnectionError, HTTPError, RequestException

from app.services.live_trading.account_synchronizer import (
    AccountSynchronizer,
    get_account_synchronizer,
)
from app.services.live_trading.alert_to_trade_mapper import (
    AlertToTradeMapper,
    get_alert_to_trade_mapper,
)
from app.services.live_trading.broker_connector import BrokerConnector, get_broker_connector
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
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to start live trading bridge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to stop live trading bridge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_bridge_status(
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """Get current bridge status and statistics."""
    try:
        status = orchestrator.get_bridge_statistics()
        return {
            "is_active": orchestrator.is_running,
            "statistics": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get bridge status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ORDER MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/orders")
async def place_order(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "MARKET",
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
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

        order_id = await order_manager.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
        )

        return {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "status": "SUBMITTED",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to place order: {e}")
        raise HTTPException(status_code=400, detail=str(e))


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
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get order status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to cancel order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to cancel all orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def list_orders(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
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
            orders = await order_manager.get_order_history(limit=limit)

        if symbol:
            orders = [o for o in orders if o.get("symbol") == symbol]

        return {
            "count": len(orders),
            "orders": orders[:limit],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            "broker_type": account.broker_type,
            "currency": account.currency,
            "cash_available": account.cash_available,
            "portfolio_value": account.portfolio_value,
            "buying_power": account.buying_power,
            "equity": account.equity,
            "margin_used": account.margin_used,
            "margin_multiplier": account.multiplier,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get account info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                    "quantity": p.quantity,
                    "average_price": p.avg_price,
                    "current_price": p.current_price,
                    "market_value": p.market_value,
                    "unrealized_pl": p.unrealized_pl,
                    "unrealized_pl_pct": p.unrealized_pl_pct,
                }
                for p in positions
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            "quantity": position.quantity,
            "average_price": position.avg_price,
            "current_price": position.current_price,
            "market_value": position.market_value,
            "unrealized_pl": position.unrealized_pl,
            "unrealized_pl_pct": position.unrealized_pl_pct,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        result = risk_gates.validate_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            account=account,
        )

        return {
            "is_valid": result.is_valid,
            "risk_level": result.risk_level,
            "violations": result.violations,
            "warnings": result.warnings,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to validate order risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/limits")
async def get_risk_limits(
    risk_gates: RiskGates = Depends(get_risk_gates),
) -> dict:
    """Get current risk gate configuration and limits."""
    try:
        config = risk_gates.config

        return {
            "limits": {
                "max_position_size": config.max_position_size,
                "max_leverage": config.max_leverage,
                "max_concentration": config.max_concentration,
                "max_daily_loss": config.max_daily_loss,
                "max_drawdown": config.max_drawdown,
                "min_cash_reserve": config.min_cash_reserve,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get risk limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/risk/limits")
async def update_risk_limits(
    max_position_size: Optional[float] = None,
    max_leverage: Optional[float] = None,
    max_concentration: Optional[float] = None,
    max_daily_loss: Optional[float] = None,
    max_drawdown: Optional[float] = None,
    min_cash_reserve: Optional[float] = None,
    risk_gates: RiskGates = Depends(get_risk_gates),
) -> dict:
    """Update risk gate limits dynamically.

    Allows traders to adjust risk parameters without restarting.
    """
    try:
        if max_position_size is not None:
            risk_gates.set_max_position_size(max_position_size)
        if max_leverage is not None:
            risk_gates.set_max_leverage(max_leverage)
        if max_concentration is not None:
            risk_gates.set_max_concentration(max_concentration)
        if max_daily_loss is not None:
            risk_gates.set_max_daily_loss(max_daily_loss)
        if max_drawdown is not None:
            risk_gates.set_max_drawdown(max_drawdown)
        if min_cash_reserve is not None:
            risk_gates.set_min_cash_reserve(min_cash_reserve)

        return {
            "message": "Risk limits updated successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to update risk limits: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# EXECUTION HISTORY ENDPOINTS
# ============================================================================


@router.get("/executions")
async def list_executions(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
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
        executions = await orchestrator.get_recent_executions(limit=limit)

        if status:
            executions = [e for e in executions if e.get("status") == status]
        if symbol:
            executions = [e for e in executions if e.get("symbol") == symbol]

        if start_date or end_date:
            start = datetime.fromisoformat(start_date) if start_date else datetime.min
            end = datetime.fromisoformat(end_date) if end_date else datetime.now()
            executions = [
                e
                for e in executions
                if start <= datetime.fromisoformat(e.get("created_at", "")) <= end
            ]

        return {
            "count": len(executions),
            "executions": executions[:limit],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """Get details of a specific execution."""
    try:
        execution = await orchestrator.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return {
            "execution": execution,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AUDIT TRAIL & COMPLIANCE ENDPOINTS
# ============================================================================


@router.get("/audit/trail")
async def get_audit_trail(
    event_type: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
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
        events = await audit_trail.get_recent_events(limit=limit)

        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        if symbol:
            events = [e for e in events if e.get("symbol") == symbol]

        if start_date or end_date:
            start = datetime.fromisoformat(start_date) if start_date else datetime.min
            end = datetime.fromisoformat(end_date) if end_date else datetime.now()
            events = [
                e for e in events if start <= datetime.fromisoformat(e.get("timestamp", "")) <= end
            ]

        return {
            "count": len(events),
            "events": events[:limit],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get audit trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

        report = await audit_trail.generate_compliance_report(
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
                "total_volume": report.total_volume,
                "avg_execution_time_ms": report.avg_execution_time_ms,
                "critical_alerts_count": report.critical_alerts_count,
                "high_risk_trades": report.high_risk_trades,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/non-compliant")
async def list_non_compliant_events(
    limit: int = Query(100, ge=1, le=1000),
    audit_trail: TradingAuditTrail = Depends(get_trading_audit_trail),
) -> dict:
    """Get non-compliant events that require review."""
    try:
        events = await audit_trail.get_non_compliant_events()

        return {
            "count": len(events),
            "events": events[:limit],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list non-compliant events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATISTICS & METRICS ENDPOINTS
# ============================================================================


@router.get("/statistics")
async def get_trading_statistics(
    orchestrator: TradingBridgeOrchestrator = Depends(get_trading_bridge_orchestrator),
) -> dict:
    """Get overall trading statistics and performance metrics."""
    try:
        stats = await orchestrator.get_bridge_statistics()

        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get trading statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/statistics")
async def get_audit_statistics(
    audit_trail: TradingAuditTrail = Depends(get_trading_audit_trail),
) -> dict:
    """Get audit statistics grouped by event type and risk level."""
    try:
        stats = await audit_trail.get_audit_statistics()

        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get audit statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/snapshot")
async def get_portfolio_snapshot(
    account_sync: AccountSynchronizer = Depends(get_account_synchronizer),
) -> dict:
    """Get current portfolio snapshot."""
    try:
        snapshot = await account_sync.take_snapshot()

        return {
            "timestamp": snapshot.timestamp.isoformat(),
            "total_value": snapshot.total_value,
            "cash": snapshot.cash,
            "positions_value": snapshot.positions_value,
            "margin_used": snapshot.margin_used,
            "buying_power": snapshot.buying_power,
            "num_positions": snapshot.num_positions,
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get portfolio snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            h
            for h in history
            if start_date <= datetime.fromisoformat(h.get("timestamp", "")) <= end_date
        ]

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days,
            },
            "count": len(filtered),
            "history": filtered,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get portfolio history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/daily-return")
async def get_daily_return(
    account_sync: AccountSynchronizer = Depends(get_account_synchronizer),
) -> dict:
    """Get today's daily P&L return."""
    try:
        daily_return = await account_sync.calculate_daily_return()

        return {
            "daily_pnl": daily_return.get("pnl", 0),
            "daily_pnl_pct": daily_return.get("pnl_pct", 0),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get daily return: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        rule_id = mapper.register_rule(rule_data)
        return {
            "rule_id": rule_id,
            "message": "Rule created successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to create rule: {e}")
        raise HTTPException(status_code=400, detail=str(e))


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
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to delete rule: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/signals/pending")
async def list_pending_signals(
    limit: int = Query(100, ge=1, le=1000),
    mapper: AlertToTradeMapper = Depends(get_alert_to_trade_mapper),
) -> dict:
    """Get pending (unexecuted) trade signals."""
    try:
        signals = await mapper.get_pending_signals(limit=limit)
        return {
            "count": len(signals),
            "signals": signals,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to list pending signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/statistics")
async def get_signal_statistics(
    mapper: AlertToTradeMapper = Depends(get_alert_to_trade_mapper),
) -> dict:
    """Get trade signal statistics by type and severity."""
    try:
        stats = await mapper.get_signal_statistics()
        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get signal statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
