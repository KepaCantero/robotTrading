# AlgoTrading System Architecture

## Overview

The AlgoTrading system is a production-grade algorithmic trading platform designed for multi-market operation (stocks, forex, crypto) with Spain-specific tax compliance.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Key Components](#key-components)
3. [Data Flow](#data-flow)
4. [Spain Tax Compliance](#spain-tax-compliance)
5. [Multi-Market Support](#multi-market-support)
6. [Dependencies](#dependencies)
7. [Technology Stack](#technology-stack)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Health  │  │ Dashboard│  │ Trading  │  │  Admin   │  │
│  │ Endpoint │  │   API    │  │   API    │  │   API    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │  Position  │  │   Risk     │  │   FIFO     │         │
│  │  Monitor   │  │  Manager   │  │ Integrator  │         │
│  └────────────┘  └────────────┘  └────────────┘         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │  Emergency │  │    News    │  │  Task      │         │
│  │   Closer   │  │  Processor │  │   Queue    │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │   Market   │  │    Broker  │  │  Database  │         │
│  │  Services  │  │  Adapters  │  │   (FIFO)   │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Components

### Position Monitor
- **Purpose**: Continuous position monitoring with automatic stop-loss/take-profit
- **File**: `app/services/position_monitor/position_monitor.py`
- **Key Methods**:
  - `start()`: Start monitoring positions
  - `add_position()`: Add a position to monitor
  - `monitor_positions()`: Check and update positions
- **Features**:
  - Real-time position tracking
  - Automatic stop-loss execution
  - Take-profit monitoring
  - Position health checks

### Emergency Closer
- **Purpose**: Close all positions on critical failures
- **File**: `app/services/emergency_handler/emergency_closer.py`
- **Key Methods**:
  - `on_connection_lost()`: Handle connection loss
  - `on_system_shutdown()`: Handle system shutdown
  - `close_all_positions()`: Emergency position closure
- **Features**:
  - Automatic emergency detection
  - Graceful position closure
  - Alert notifications
  - Audit logging

### FIFO Integrator
- **Purpose**: Track trades for Spain Modelo 721 tax compliance
- **File**: `app/services/fifo/fifo_integrator.py`
- **Key Methods**:
  - `on_trade_executed()`: Record executed trades
  - `generate_modelo_721()`: Generate annual tax report
  - `calculate_cost_basis()`: FIFO cost basis calculation
- **Features**:
  - Trade tracking and logging
  - Cost basis calculation
  - Annual report generation
  - Tax compliance automation

### Risk Manager
- **Purpose**: Manage trading risk and exposure
- **File**: `app/services/risk/risk_manager.py`
- **Key Methods**:
  - `check_risk_limits()`: Verify risk constraints
  - `calculate_position_size()`: Determine position sizing
  - `update_exposure()`: Track market exposure
- **Features**:
  - Position sizing limits
  - Exposure tracking
  - Drawdown monitoring
  - Risk limit enforcement

### Strategy Registry
- **Purpose**: Manage multiple trading strategies
- **File**: `app/strategies/base/strategy_registry.py`
- **Key Methods**:
  - `load_strategy()`: Load a strategy
  - `set_active_strategy()`: Set active strategy
  - `get_strategy_status()`: Get strategy status
- **Features**:
  - Multi-strategy support
  - Dynamic strategy loading
  - Strategy lifecycle management
  - Performance tracking

---

## Data Flow

### Trade Execution Flow
```
Signal Generation
       ↓
Risk Check
       ↓
Order Placement
       ↓
Position Monitor
       ↓
Stop Loss/Take Profit
       ↓
Execution & Logging
```

### Emergency Flow
```
Connection Lost
       ↓
Emergency Closer Triggered
       ↓
Close All Positions
       ↓
Alert Notifications
       ↓
Audit Logging
```

### Data Acquisition Flow
```
Market Data Sources
       ↓
Data Engine (Normalization & Validation)
       ↓
Strategy Analysis
       ↓
Signal Generation
       ↓
Risk Management
       ↓
Order Execution
```

---

## Spain Tax Compliance

### Modelo 721 Requirements

The system implements comprehensive tracking for Spain's Modelo 721 tax reporting:

1. **Transaction Recording**: All crypto transactions recorded with timestamp
2. **FIFO Cost Basis**: First-In-First-Out cost calculation
3. **Balance Snapshots**: Automatic December 31 balance recording
4. **Annual Reports**: Automated Modelo 721 report generation

### Tax Rates (Spain 2024)

| Capital Gains Range | Tax Rate |
|---------------------|----------|
| €0 - €33,007.99 | 19% |
| €33,008 - €53,407.99 | 21% |
| €53,408+ | 23% |

### FIFO Implementation

The system uses FIFO (First-In-First-Out) for cost basis calculation:

```python
# Example FIFO calculation
trades = [
    {"date": "2024-01-15", "amount": 1.0, "price": 50000},
    {"date": "2024-03-20", "amount": 0.5, "price": 60000},
    {"date": "2024-06-10", "amount": -1.0, "price": 70000},  # Sale
]

# FIFO: Oldest holdings sold first
# Cost basis = 1.0 * 50000 = 50000
# Capital gain = 70000 - 50000 = 20000
```

### Configuration

Configure Spain residency in `/Users/kepa.cantero/Projects/algoTrading/config/spain_residency_config.yaml`:

```yaml
tax_residency:
  country: "Spain"
  fiscal_year_end: "12-31"
  fifo_method: true
  auto_snapshot: true
```

---

## Multi-Market Support

### 24/7 Markets

#### Crypto
- **Operation**: Continuous 24/7
- **Data Sources**: Multiple exchange APIs
- **Settlement**: Immediate
- **Tax Reporting**: Modelo 721 required

#### Forex
- **Operation**: Continuous 24/5 (Sunday 5pm - Friday 5pm ET)
- **Data Sources**: Interbank feeds
- **Settlement**: T+2
- **Tax Reporting**: Capital gains

### Scheduled Markets

#### US Stocks
- **Hours**: 9:30-16:00 ET (Mon-Fri)
- **Exchanges**: NYSE, NASDAQ
- **Settlement**: T+1
- **Pre-market**: 4:00-9:30 ET
- **After-hours**: 16:00-20:00 ET

#### EU Stocks
- **Hours**: 9:00-17:30 CET (Mon-Fri)
- **Exchanges**: XETRA, Euronext, LSE
- **Settlement**: T+2

### Market Scheduler

The system implements market-aware scheduling:

```python
# Market hours detection
if is_market_open("AAPL"):  # US stock
    execute_strategy()

if is_market_open("BTCUSD"):  # Crypto (always open)
    execute_strategy()
```

---

## Dependencies

### External APIs

#### Market Data
- **Marketaux**: News sentiment analysis
  - Endpoint: `https://api.marketaux.com/v1/news/all`
  - Rate limit: 100 requests/minute
- **Polygon.io**: Real-time market data
  - WebSocket: `wss://socket.polygon.io/stocks`
  - REST: `https://api.polygon.io/v2/aggs/ticker`
- **Alpha Vantage**: Historical data
  - Endpoint: `https://www.alphavantage.co/query`

#### Broker APIs
- **Interactive Brokers (IBKR)**: Stocks, options, futures
  - API: IBKR Python API (ib-insync)
  - Port: 4001 (paper trading), 7497 (production)
- **Alpaca**: US stocks, crypto
  - API: Alpaca-Py SDK
  - Base URL: `https://api.alpaca.markets`

### Internal Services

| Service | Purpose | Port |
|---------|---------|------|
| FastAPI | REST API | 8000 |
| PostgreSQL | Trade database | 5432 |
| Redis | Cache & queue | 6379 |
| Celery | Task queue | N/A |

### Python Dependencies

Key dependencies from `requirements.txt`:

```txt
# Core
fastapi>=0.104.0,<0.110.0
uvicorn[standard]>=0.24.0,<0.30.0
pydantic>=2.0.0,<3.0.0

# Data
pandas>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0
pandas-ta-classic>=0.3.36,<1.0.0

# ML
scikit-learn>=1.3.0,<2.0.0
torch>=2.0.0,<3.0.0
stable-baselines3>=2.0.0,<3.0.0

# Brokers
alpaca-py>=0.1.0
ib-insync>=0.5.0

# Analytics
quantstats>=0.0.62,<1.0.0
```

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn (ASGI)
- **Python**: 3.9+

### Database
- **PostgreSQL**: Trade data
- **SQLite**: FIFO tax tracking

### Task Queue
- **Celery**: Async task processing
- **Redis**: Message broker

### Machine Learning
- **Scikit-learn**: Supervised learning
- **PyTorch**: Deep learning
- **Stable-Baselines3**: Reinforcement learning

### Analytics
- **QuantStats**: Portfolio analytics
- **Pandas-TA**: Technical indicators

### Monitoring
- **Logging**: Python JSON logger
- **Health Checks**: Custom health endpoint
- **Metrics**: Psutil system monitoring

---

## Directory Structure

```
/Users/kepa.cantero/Projects/algoTrading/
├── app/
│   ├── api/                    # API endpoints
│   ├── backtesting/            # Backtesting engine
│   ├── core/                   # Core configuration
│   ├── data/                   # Data services
│   ├── engines/                # Strategy engines
│   ├── models/                 # Pydantic models
│   ├── services/               # Business logic
│   ├── strategies/             # Trading strategies
│   └── tax/                    # Tax compliance
├── config/                     # YAML configurations
├── data/                       # Data files
├── docs/                       # Documentation
├── reports/                    # Backtest reports
├── tests/                      # Test suite
├── .env.example                # Environment template
├── pyproject.toml              # Project config
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

---

## Security Considerations

### API Keys
- Store in environment variables
- Never commit to version control
- Rotate regularly

### Database
- Use strong passwords
- Enable SSL connections
- Regular backups

### Trading
- Paper trading before live
- Risk limits enforced
- Emergency stop procedures

---

## Performance

### Latency Targets
- Market data: <100ms
- Signal generation: <500ms
- Order execution: <1s

### Throughput
- API requests: 1000/minute
- Data processing: 10K ticks/second
- Backtesting: 1M bars/minute

---

## Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-25T10:30:00",
  "checks": {
    "database": {"status": "healthy"},
    "broker": {"status": "healthy"},
    "memory": {"status": "healthy"},
    "positions": {"status": "healthy", "count": 3}
  },
  "uptime_seconds": 3600.5
}
```

### Logs
- Location: `logs/`
- Format: JSON
- Rotation: Daily
- Retention: 30 days

---

## Deployment

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker
```bash
docker-compose up -d
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## License

Proprietary - All rights reserved

---

## Support

For issues or questions, contact the development team.
