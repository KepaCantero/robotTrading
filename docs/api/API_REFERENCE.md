# API Reference Documentation

## Overview

The AlgoTrading system provides a comprehensive REST API built with FastAPI for managing algorithmic trading operations, portfolio monitoring, backtesting, and system health.

**Base URL**: `http://localhost:8000`

**API Documentation**: `http://localhost:8000/docs` (Interactive Swagger UI)

**Alternative Documentation**: `http://localhost:8000/redoc`

## Authentication

Currently, the API operates in development mode. Production deployment will require:
- JWT token authentication
- API key validation
- OAuth2 integration

## Response Format

All endpoints return JSON responses with the following structure:

```json
{
  "status": "success|error",
  "data": {},
  "message": "Optional message",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Authentication required |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Invalid input data |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Circuit breaker open |

---

## Health & Monitoring

### GET /health

Check system health status.

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database OK (15 tables)",
      "file_size_mb": 2.5
    },
    "broker": {
      "status": "healthy",
      "message": "Broker connected: AlpacaAdapter"
    },
    "memory": {
      "status": "healthy",
      "memory_mb": 512.5,
      "memory_percent": 2.5,
      "available_mb": 8192.0
    },
    "positions": {
      "status": "healthy",
      "count": 5,
      "message": "5 open positions"
    }
  },
  "uptime_seconds": 3600.5
}
```

**Status Codes:**
- 200: System is healthy or degraded
- 503: System is unhealthy

---

## Portfolio Management

### GET /portfolio/

Get portfolio summary including equity, positions, and circuit breaker status.

**Response:**
```json
{
  "total_equity": 100000.00,
  "cash_balance": 50000.00,
  "positions_count": 5,
  "unrealized_pnl": 1500.50,
  "circuit_breakers": {
    "portfolio_service": {
      "state": "closed",
      "failure_count": 0,
      "last_failure_time": null
    }
  }
}
```

### GET /portfolio/positions

Get all positions in the portfolio.

**Response:**
```json
[
  {
    "symbol": "AAPL",
    "quantity": 100,
    "average_cost": 150.00,
    "current_price": 155.00,
    "market_value": 15500.00,
    "unrealized_pnl": 500.00,
    "side": "long"
  }
]
```

### GET /portfolio/positions/{symbol}

Get specific position by symbol.

**Parameters:**
- `symbol` (path): Trading symbol (e.g., AAPL)

**Response:**
```json
{
  "symbol": "AAPL",
  "quantity": 100,
  "average_cost": 150.00,
  "current_price": 155.00,
  "market_value": 15500.00,
  "unrealized_pnl": 500.00,
  "side": "long"
}
```

### POST /portfolio/simulate-trade

Simulate a trade execution without executing it.

**Request Body:**
```json
{
  "symbol": "AAPL",
  "quantity": 10,
  "price": 155.00
}
```

**Response:**
```json
{
  "success": true,
  "message": "Trade simulated successfully",
  "symbol": "AAPL",
  "quantity": 10,
  "price": 155.00
}
```

### GET /portfolio/circuit-breakers

Get status of all circuit breakers.

**Response:**
```json
{
  "portfolio_service": {
    "state": "closed",
    "failure_count": 0,
    "last_failure_time": null
  },
  "data_service": {
    "state": "closed",
    "failure_count": 2,
    "last_failure_time": "2024-01-01T12:00:00Z"
  }
}
```

### POST /portfolio/circuit-breakers/{name}/reset

Reset a specific circuit breaker.

**Parameters:**
- `name` (path): Circuit breaker name

**Response:**
```json
{
  "message": "Circuit breaker portfolio_service reset successfully"
}
```

---

## Market Data

### GET /market-data/symbols/{symbol}

Get market data for a specific symbol.

**Parameters:**
- `symbol` (path): Trading symbol
- `start_date` (query): Start date (ISO format)
- `end_date` (query): End date (ISO format)
- `interval` (query): Data interval (1d, 1h, 5m, etc.)

**Response:**
```json
{
  "symbol": "AAPL",
  "data": [
    {
      "timestamp": "2024-01-01T09:30:00Z",
      "open": 150.00,
      "high": 152.00,
      "low": 149.50,
      "close": 151.00,
      "volume": 1000000
    }
  ]
}
```

### GET /market-data/symbols

Get list of available symbols.

**Query Parameters:**
- `market` (optional): Filter by market (US, EU, ASIA)
- `sector` (optional): Filter by sector
- `limit` (optional): Maximum results (default: 100)

**Response:**
```json
{
  "symbols": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "market": "US"
    }
  ],
  "total": 5000
}
```

---

## Trading Signals

### GET /signals

Get latest trading signals.

**Query Parameters:**
- `symbol` (optional): Filter by symbol
- `strategy` (optional): Filter by strategy
- `limit` (optional): Maximum signals (default: 50)

**Response:**
```json
{
  "signals": [
    {
      "symbol": "AAPL",
      "strategy": "momentum",
      "action": "buy",
      "confidence": 0.85,
      "timestamp": "2024-01-01T12:00:00Z",
      "price": 150.00,
      "reason": "Strong momentum breakout"
    }
  ]
}
```

### POST /signals/generate

Generate trading signals for specified symbols.

**Request Body:**
```json
{
  "symbols": ["AAPL", "GOOGL", "MSFT"],
  "strategy": "momentum",
  "parameters": {
    "lookback_period": 20,
    "threshold": 0.02
  }
}
```

**Response:**
```json
{
  "signals_generated": 3,
  "signals": [
    {
      "symbol": "AAPL",
      "action": "buy",
      "confidence": 0.85
    }
  ]
}
```

---

## Backtesting

### POST /backtesting/run

Run a backtest with specified configuration.

**Request Body:**
```json
{
  "strategy": "momentum",
  "symbols": ["AAPL", "GOOGL"],
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 100000,
  "parameters": {
    "lookback_period": 20,
    "threshold": 0.02
  }
}
```

**Response:**
```json
{
  "backtest_id": "bt_20240101_120000",
  "status": "running",
  "estimated_completion": "2024-01-01T12:05:00Z"
}
```

### GET /backtesting/results/{backtest_id}

Get backtest results.

**Parameters:**
- `backtest_id` (path): Backtest ID

**Response:**
```json
{
  "backtest_id": "bt_20240101_120000",
  "status": "completed",
  "metrics": {
    "total_return": 0.15,
    "sharpe_ratio": 1.5,
    "max_drawdown": -0.08,
    "win_rate": 0.60
  },
  "trades": [
    {
      "symbol": "AAPL",
      "entry_date": "2023-01-15",
      "exit_date": "2023-02-01",
      "entry_price": 150.00,
      "exit_price": 155.00,
      "quantity": 100,
      "pnl": 500.00
    }
  ]
}
```

### GET /backtesting/configurations

Get available backtest configurations.

**Response:**
```json
{
  "configurations": [
    {
      "name": "conservative",
      "description": "Low risk, conservative parameters",
      "initial_capital": 100000,
      "max_position_size": 0.02
    },
    {
      "name": "moderate",
      "description": "Moderate risk profile",
      "initial_capital": 100000,
      "max_position_size": 0.05
    }
  ]
}
```

---

## Optimization

### POST /optimization/run

Run parameter optimization for a strategy.

**Request Body:**
```json
{
  "strategy": "momentum",
  "symbols": ["AAPL", "GOOGL"],
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "parameters": {
    "lookback_period": {
      "min": 10,
      "max": 30,
      "step": 5
    },
    "threshold": {
      "min": 0.01,
      "max": 0.05,
      "step": 0.01
    }
  },
  "optimization_method": "bayesian"
}
```

**Response:**
```json
{
  "optimization_id": "opt_20240101_120000",
  "status": "running",
  "estimated_iterations": 100
}
```

### GET /optimization/results/{optimization_id}

Get optimization results.

**Response:**
```json
{
  "optimization_id": "opt_20240101_120000",
  "status": "completed",
  "best_parameters": {
    "lookback_period": 20,
    "threshold": 0.02
  },
  "best_score": 1.5,
  "all_results": [
    {
      "parameters": {"lookback_period": 20, "threshold": 0.02},
      "score": 1.5,
      "sharpe_ratio": 1.5,
      "total_return": 0.15
    }
  ]
}
```

---

## Paper Trading

### POST /paper-trading/start

Start paper trading session.

**Request Body:**
```json
{
  "initial_capital": 100000,
  "strategy": "momentum",
  "symbols": ["AAPL", "GOOGL", "MSFT"]
}
```

**Response:**
```json
{
  "session_id": "paper_20240101_120000",
  "status": "running",
  "starting_capital": 100000.00
}
```

### POST /paper-trading/stop

Stop paper trading session.

**Request Body:**
```json
{
  "session_id": "paper_20240101_120000"
}
```

**Response:**
```json
{
  "session_id": "paper_20240101_120000",
  "status": "stopped",
  "final_capital": 105000.00,
  "total_return": 0.05
}
```

### GET /paper-trading/performance

Get paper trading performance metrics.

**Query Parameters:**
- `session_id` (optional): Session ID

**Response:**
```json
{
  "session_id": "paper_20240101_120000",
  "starting_capital": 100000.00,
  "current_capital": 105000.00,
  "total_return": 0.05,
  "win_rate": 0.60,
  "total_trades": 25,
  "profitable_trades": 15
}
```

---

## Live Trading

### POST /live-trading/start

Start live trading session (requires broker authentication).

**Request Body:**
```json
{
  "broker": "alpaca",
  "strategy": "momentum",
  "symbols": ["AAPL", "GOOGL"],
  "risk_parameters": {
    "max_position_size": 0.05,
    "max_daily_loss": 0.02,
    "stop_loss": 0.03
  }
}
```

**Response:**
```json
{
  "session_id": "live_20240101_120000",
  "status": "running",
  "broker": "alpaca"
}
```

### POST /live-trading/stop

Stop live trading session immediately.

**Request Body:**
```json
{
  "session_id": "live_20240101_120000",
  "close_positions": true
}
```

**Response:**
```json
{
  "session_id": "live_20240101_120000",
  "status": "stopped",
  "positions_closed": 5
}
```

### GET /live-trading/status

Get live trading session status.

**Response:**
```json
{
  "session_id": "live_20240101_120000",
  "status": "running",
  "broker": "alpaca",
  "connected": true,
  "positions": 5,
  "equity": 105000.00,
  "daily_pnl": 500.00
}
```

---

## Cost Analysis

### POST /cost-analysis/estimate

Estimate trading costs for a strategy.

**Request Body:**
```json
{
  "strategy": "momentum",
  "symbols": ["AAPL", "GOOGL"],
  "average_trade_size": 10000,
  "expected_trades_per_day": 10,
  "broker": "alpaca"
}
```

**Response:**
```json
{
  "estimated_daily_costs": 25.50,
  "estimated_monthly_costs": 510.00,
  "breakdown": {
    "commissions": 15.00,
    "fees": 5.00,
    "slippage": 5.50
  }
}
```

---

## Deployment

### POST /deployment/deploy

Deploy strategy to production.

**Request Body:**
```json
{
  "strategy": "momentum",
  "environment": "production",
  "configuration": "moderate",
  "validation_required": true
}
```

**Response:**
```json
{
  "deployment_id": "deploy_20240101_120000",
  "status": "validating",
  "validation_steps": [
    "Configuration validation",
    "Risk checks",
    "Performance validation"
  ]
}
```

### GET /deployment/status/{deployment_id}

Get deployment status.

**Response:**
```json
{
  "deployment_id": "deploy_20240101_120000",
  "status": "deployed",
  "deployment_time": "2024-01-01T12:00:00Z",
  "health_status": "healthy"
}
```

---

## API Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default**: 100 requests per minute
- **Burst**: Up to 200 requests in a short burst
- **Window**: Rolling 60-second window

When rate limited, you'll receive:
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 30
}
```

---

## Webhooks

The system supports webhooks for real-time notifications:

### POST /webhooks/register

Register a webhook endpoint.

**Request Body:**
```json
{
  "url": "https://your-domain.com/webhook",
  "events": ["trade_executed", "signal_generated", "error"]
}
```

**Response:**
```json
{
  "webhook_id": "wh_20240101_120000",
  "status": "active"
}
```

---

## SDK Examples

### Python

```python
import requests

# Initialize client
base_url = "http://localhost:8000"
client = requests.Session()

# Get portfolio
response = client.get(f"{base_url}/portfolio/")
portfolio = response.json()

# Generate signals
response = client.post(f"{base_url}/signals/generate", json={
    "symbols": ["AAPL", "GOOGL"],
    "strategy": "momentum"
})
signals = response.json()
```

### JavaScript

```javascript
const axios = require('axios');

const client = axios.create({
  baseURL: 'http://localhost:8000'
});

// Get portfolio
const portfolio = await client.get('/portfolio/');

// Generate signals
const signals = await client.post('/signals/generate', {
  symbols: ['AAPL', 'GOOGL'],
  strategy: 'momentum'
});
```

---

## Changelog

### Version 1.0.0 (Current)
- Initial API release
- Core trading functionality
- Portfolio management
- Backtesting endpoints
- Health monitoring

---

## Support

For API support:
- Documentation: `/docs`
- Email: support@algotrading.com
- GitHub Issues: github.com/algotrading/issues
