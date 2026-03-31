from __future__ import annotations

"""Production Dashboard API Router.

Provides FastAPI endpoints for the production dashboard including:
- REST API for metrics, positions, alerts, and historical data
- WebSocket endpoint for real-time updates
- Alert management endpoints
"""

import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.presentation.dashboard.production_dashboard import (
    AlertHistoryItem,
    DashboardMetrics,
    HistoricalDataPoint,
    PositionMetric,
    ProductionDashboard,
    get_production_dashboard,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def get_dashboard() -> ProductionDashboard:
    """Dependency to get dashboard instance."""
    return get_production_dashboard()


@router.get("/", response_class=HTMLResponse)
async def get_dashboard_frontend():
    """
    Serve the dashboard frontend HTML.

    Returns:
        HTML content of the dashboard
    """
    try:
        frontend_path = Path(__file__).parent / "frontend" / "index.html"
        if frontend_path.exists():
            with open(frontend_path) as f:
                return f.read()
        raise HTTPException(status_code=404, detail="Dashboard frontend not found")
    except OSError as e:
        logger.error(f"Error loading dashboard frontend: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health")
async def get_health_status(
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> dict:
    """
    Get dashboard health status.

    Returns:
        Dictionary with health status information
    """
    try:
        return dashboard.get_health_status()
    except OSError as e:
        logger.error(f"Error getting health status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> DashboardMetrics:
    """
    Get current dashboard metrics.

    Returns:
        DashboardMetrics object with current values
    """
    try:
        return await dashboard.get_metrics()
    except (asyncio.TimeoutError, OSError) as e:
        logger.error(f"Error getting dashboard metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/positions", response_model=list[PositionMetric])
async def get_positions(
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> list[PositionMetric]:
    """
    Get current position metrics.

    Returns:
        List of PositionMetric objects
    """
    try:
        return await dashboard.get_positions()
    except (asyncio.TimeoutError, OSError) as e:
        logger.error(f"Error getting positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/alerts", response_model=list[AlertHistoryItem])
async def get_alert_history(
    hours: int = 24,
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> list[AlertHistoryItem]:
    """
    Get alert history.

    Args:
        hours: Number of hours of history to retrieve (default: 24)

    Returns:
        List of AlertHistoryItem objects
    """
    try:
        return await dashboard.get_alert_history(hours=hours)
    except (asyncio.TimeoutError, OSError) as e:
        logger.error(f"Error getting alert history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/historical", response_model=list[HistoricalDataPoint])
async def get_historical_data(
    period: str = "7d",
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> list[HistoricalDataPoint]:
    """
    Get historical performance data.

    Args:
        period: Time period ('7d' or '30d', default: '7d')

    Returns:
        List of HistoricalDataPoint objects
    """
    try:
        if period not in ["7d", "30d"]:
            raise HTTPException(status_code=400, detail="Period must be '7d' or '30d'")

        return await dashboard.get_historical_data(period=period)
    except HTTPException:
        raise
    except (asyncio.TimeoutError, OSError) as e:
        logger.error(f"Error getting historical data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> dict[str, bool]:
    """
    Acknowledge an alert.

    Args:
        alert_id: Alert ID to acknowledge

    Returns:
        Dictionary with success status
    """
    try:
        success = await dashboard.acknowledge_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return {"success": True}
    except HTTPException:
        raise
    except (asyncio.TimeoutError, OSError) as e:
        logger.error(f"Error acknowledging alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> dict[str, bool]:
    """
    Resolve an alert.

    Args:
        alert_id: Alert ID to resolve

    Returns:
        Dictionary with success status
    """
    try:
        success = await dashboard.resolve_alert(alert_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        return {"success": True}
    except HTTPException:
        raise
    except (asyncio.TimeoutError, OSError) as e:
        logger.error(f"Error resolving alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    dashboard: ProductionDashboard = Depends(get_dashboard),
):
    """
    WebSocket endpoint for real-time dashboard updates.

    Connects to this endpoint to receive real-time updates of dashboard metrics.
    Updates are sent every second.

    Connection URL: ws://localhost:8000/api/v1/dashboard/ws
    """
    try:
        await dashboard.websocket_endpoint(websocket)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally")
    except (asyncio.TimeoutError, OSError) as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        with contextlib.suppress(asyncio.TimeoutError, OSError):
            await websocket.close()


@router.get("/connections")
async def get_active_connections(
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> dict[str, int]:
    """
    Get number of active WebSocket connections.

    Returns:
        Dictionary with connection count
    """
    try:
        return {"active_connections": dashboard.get_connection_count()}
    except OSError as e:
        logger.error(f"Error getting connection count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats")
async def get_dashboard_statistics(
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> dict:
    """
    Get aggregated dashboard statistics.

    Returns:
        Dictionary with dashboard statistics
    """
    try:
        health = dashboard.get_health_status()
        metrics = await dashboard.get_metrics()

        return {
            "health": health,
            "current_metrics": metrics.model_dump(),
            "active_connections": dashboard.get_connection_count(),
        }
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error getting dashboard statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/refresh")
async def refresh_dashboard_data(
    dashboard: ProductionDashboard = Depends(get_dashboard),
) -> dict[str, bool]:
    """
    Force refresh of all dashboard data.

    Returns:
        Dictionary with success status
    """
    try:
        # Clear historical cache to force refresh
        dashboard._historical_cache = {"7d": [], "30d": []}

        # Broadcast update to all connected clients
        await dashboard.broadcast_update(
            {"type": "refresh", "timestamp": dashboard._last_update.isoformat()}
        )

        return {"success": True}
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error refreshing dashboard data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
