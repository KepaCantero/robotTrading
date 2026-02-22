# Production Dashboard - Phase 4.1

## Overview

The Production Dashboard provides real-time monitoring and visibility into the algoTrading system's production operations. It addresses the critical need for system state visibility with comprehensive metrics, alerting, and historical performance tracking.

## Features

### Core Functionality

- **Real-time P&L Display**: Live portfolio value and daily P&L updates with percentage changes
- **Position Tracker**: Current positions with quantity, prices, market value, and unrealized P&L
- **System Health Metrics**: CPU, memory usage, and uptime monitoring
- **Error Rate Tracking**: Order execution metrics (orders, fills, rejects)
- **Latency Monitoring**: Average order execution latency tracking
- **Alert History**: Recent alerts with acknowledge and resolve actions
- **Historical Charts**: 7-day and 30-day performance charts
- **Mobile-Responsive Design**: Optimized for desktop, tablet, and mobile devices

### Real-time Updates

- **WebSocket Connection**: Real-time metrics updates every second
- **Automatic Reconnection**: Handles disconnections with exponential backoff
- **Connection Status**: Visual indicator showing connection state

### Dashboard Components

#### Portfolio Metrics
- Total portfolio value
- Daily P&L with percentage change
- Open positions count
- Available buying power

#### System Health
- CPU usage percentage
- Memory usage (MB and %)
- System uptime

#### Trading Metrics
- Orders placed today
- Orders filled today
- Orders rejected today
- Average execution latency

#### Risk Metrics
- 1-day Value at Risk (VaR)
- VaR limit
- VaR utilization percentage

#### Alert Management
- Active alerts count
- 24-hour alert count
- Alert history with severity levels
- Acknowledge and resolve actions

## Architecture

### Backend Components

#### ProductionDashboard Class
Location: `/app/dashboard/production_dashboard.py`

Main orchestrator that integrates with:
- PortfolioService for P&L and position data
- RiskManager for VaR calculations
- AlertingOrchestrator for alert history
- System monitors for health metrics

#### API Router
Location: `/app/dashboard/api_router.py`

FastAPI router providing:
- REST endpoints for dashboard data
- WebSocket endpoint for real-time updates
- Alert management endpoints

### Frontend Components

#### HTML
Location: `/app/dashboard/frontend/index.html`

Semantic HTML structure with:
- Header with connection status
- Metrics cards grid
- System health section
- Trading metrics section
- Risk metrics section
- Alert status section
- Performance charts
- Positions table
- Alert history

#### CSS
Location: `/app/dashboard/frontend/styles.css`

Responsive design with:
- CSS Grid and Flexbox layouts
- Dark theme optimized for trading floors
- Mobile breakpoints (1024px, 768px, 480px)
- Smooth animations and transitions
- Custom scrollbars

#### JavaScript
Location: `/app/dashboard/frontend/app.js`

Frontend application logic:
- WebSocket connection management
- Real-time data updates
- Chart.js integration
- Alert management actions
- Automatic reconnection logic

## API Reference

### REST Endpoints

#### GET /api/v1/dashboard/
Serve the dashboard frontend HTML

#### GET /api/v1/dashboard/health
Get dashboard health status
```json
{
  "is_running": true,
  "websocket_connections": 2,
  "last_update": "2024-01-25T12:00:00Z",
  "uptime_seconds": 86400.0,
  "components": {...}
}
```

#### GET /api/v1/dashboard/metrics
Get current dashboard metrics
```json
{
  "total_value": "100000.00",
  "daily_pnl": "1500.00",
  "daily_pnl_pct": "1.50",
  "open_positions": 5,
  "buying_power": "50000.00",
  "cpu_percent": 25.5,
  "memory_mb": 512.0,
  "memory_percent": 12.5,
  "uptime_seconds": 86400.0,
  "orders_today": 25,
  "fills_today": 23,
  "rejects_today": 2,
  "avg_latency_ms": 150.0,
  "var_1day": "2000.00",
  "var_limit": "2000.00",
  "var_utilization_pct": 100.0,
  "active_alerts": 0,
  "alerts_last_24h": 5,
  "timestamp": "2024-01-25T12:00:00Z"
}
```

#### GET /api/v1/dashboard/positions
Get current position metrics
```json
[
  {
    "symbol": "AAPL",
    "quantity": "100",
    "avg_price": "150.00",
    "current_price": "155.00",
    "market_value": "15500.00",
    "unrealized_pnl": "500.00",
    "unrealized_pnl_pct": "3.33",
    "currency": "USD"
  }
]
```

#### GET /api/v1/dashboard/alerts?hours=24
Get alert history
```json
[
  {
    "alert_id": "alert_123",
    "rule_id": "high_drawdown",
    "severity": "warning",
    "message": "Drawdown exceeded 10%",
    "triggered_at": "2024-01-25T11:00:00Z",
    "resolved_at": null,
    "status": "active"
  }
]
```

#### GET /api/v1/dashboard/historical?period=7d
Get historical performance data
```json
[
  {
    "timestamp": "2024-01-18T12:00:00Z",
    "portfolio_value": "100000.00",
    "daily_pnl": "0.00",
    "drawdown_pct": "0.00"
  }
]
```

#### POST /api/v1/dashboard/alerts/{alert_id}/acknowledge
Acknowledge an alert

#### POST /api/v1/dashboard/alerts/{alert_id}/resolve
Resolve an alert

### WebSocket Endpoint

#### WS /api/v1/dashboard/ws
Real-time dashboard metrics updates

Connection URL: `ws://localhost:8000/api/v1/dashboard/ws`

Updates received every second with current metrics.

## Installation

### Requirements

- Python 3.9+
- FastAPI
- WebSockets
- psutil (for system metrics)

### Setup

1. The production dashboard is included in the main application
2. Frontend files are located in `/app/dashboard/frontend/`
3. API router is automatically registered with FastAPI

### Configuration

Add to your FastAPI application:

```python
from app.dashboard.api_router import router as dashboard_router

app.include_router(dashboard_router)
```

Initialize the dashboard with required services:

```python
from app.dashboard.production_dashboard import get_production_dashboard

dashboard = get_production_dashboard(
    portfolio_service=portfolio_service,
    position_monitor=position_monitor,
    risk_manager=risk_manager,
    alerting_orchestrator=alerting_orchestrator,
)
```

## Usage

### Accessing the Dashboard

1. Start your FastAPI application
2. Navigate to: `http://localhost:8000/api/v1/dashboard/`
3. The dashboard will load and automatically connect via WebSocket

### Real-time Updates

The dashboard automatically:
- Connects to WebSocket on load
- Receives metrics updates every second
- Handles disconnections with automatic reconnection
- Displays connection status in the header

### Historical Data

- Toggle between 7-day and 30-day views using chart buttons
- Charts update automatically when period changes

### Alert Management

- View recent alerts in the Alert History section
- Acknowledge active alerts to suppress notifications
- Resolve alerts when issues are fixed
- Alert status persists across sessions

## Data Models

### DashboardMetrics
Real-time dashboard metrics with portfolio, system health, trading, and risk data.

### PositionMetric
Individual position data including symbol, quantity, prices, and P&L.

### AlertHistoryItem
Alert history with severity, message, timestamps, and status.

### HistoricalDataPoint
Historical performance data for charts including portfolio value, P&L, and drawdown.

## Integration Points

### Portfolio Service
Provides portfolio value, positions, and P&L data.

### Risk Manager
Calculates Value at Risk (VaR) and risk metrics.

### Alerting Orchestrator
Manages alert lifecycle and history.

### System Monitors
Provides CPU, memory, and uptime metrics.

### Trading Services
Provides order execution metrics and latency data.

## Security Considerations

1. **Authentication**: Add authentication middleware to protect dashboard endpoints
2. **Authorization**: Implement role-based access control for dashboard access
3. **WebSocket Security**: Use WSS for encrypted WebSocket connections
4. **Rate Limiting**: Implement rate limiting on REST endpoints

## Performance

- **WebSocket Updates**: 1-second interval for real-time data
- **Historical Data**: Cached on first load, refreshes on period change
- **Positions/Alerts**: Refresh every 30 seconds via REST API
- **Memory**: Minimal footprint with efficient data structures

## Troubleshooting

### WebSocket Connection Issues

- Check CORS settings in FastAPI
- Verify WebSocket URL matches server address
- Check firewall/proxy settings
- Review browser console for errors

### Metrics Not Updating

- Verify backend services are running
- Check service health status endpoint
- Review application logs for errors
- Ensure WebSocket connection is active

### Chart Not Displaying

- Verify Chart.js is loaded
- Check historical data API endpoint
- Review browser console for JavaScript errors
- Clear browser cache

## Future Enhancements

1. **Customizable Layout**: Drag-and-drop dashboard components
2. **User Preferences**: Save metric preferences and layouts
3. **Advanced Charts**: Add more chart types and indicators
4. **Export Data**: CSV/Excel export for historical data
5. **Mobile App**: Native mobile applications
6. **Multi-User**: Support for multiple user sessions
7. **Alert Rules UI**: Configure alert rules through dashboard
8. **Order Management**: Place and manage orders through dashboard

## Files

- `/app/dashboard/production_dashboard.py` - Main dashboard class
- `/app/dashboard/api_router.py` - FastAPI router
- `/app/dashboard/frontend/index.html` - Frontend HTML
- `/app/dashboard/frontend/styles.css` - Frontend CSS
- `/app/dashboard/frontend/app.js` - Frontend JavaScript
- `/app/dashboard/__init__.py` - Module exports

## Acceptance Criteria

- [x] Web-based dashboard
- [x] Real-time updates (WebSocket)
- [x] Mobile-responsive
- [x] Historical charts (7 days, 30 days)
- [x] Alert configuration (acknowledge, resolve)

## Support

For issues or questions:
1. Check application logs
2. Review API documentation at `/docs`
3. Verify service integration
4. Check browser console for frontend errors
