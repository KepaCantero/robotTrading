# AlgoTrading - Personal Algorithmic Trading System

## 🎯 Project Overview

**AlgoTrading** es un sistema personal de trading algorítmico diseñado para **generar dinero** mediante estrategias automatizadas de momentum y liquidez en acciones, criptomonedas y forex.

### Core Value Proposition

- **Trading Algorítmico**: Estrategias de liquidez y momentum para múltiples activos
- **Stack Moderno**: Python 3.11, FastAPI 0.115+, PostgreSQL 15, Redis 7, Celery 5.3
- **Paper Trading First**: Simulación antes de ejecución real
- **Personal System**: Enfocado en uso personal, sin complejidad multi-usuario

## 🧱 Arquitectura Base

### Backend Stack

- **Framework**: FastAPI 0.115+ (High-performance async API)
- **Database**: PostgreSQL 15+ (ACID compliance, trading data)
- **Caching**: Redis 7+ (Market data caching, session management)
- **ORM**: SQLAlchemy 2.0+ (Database abstraction, migrations)
- **Serialization**: Pydantic 2+ (Data validation, API schemas)

### Trading Engine

- **Strategy Framework**: Abstract base classes para estrategias
- **Market Data**: Real-time data feeds con WebSockets
- **Execution Engine**: Async order execution con retry logic
- **Risk Engine**: Real-time risk calculation y position management

### Asynchronous Processing

- **Task Queue**: Celery 5+ (Background trading tasks)
- **Message Broker**: Redis/RabbitMQ (Reliable message delivery)
- **Event Processing**: Event-driven architecture para coordinación

### Security Framework

- **API Security**: Rate limiting, input validation
- **Data Protection**: Encryption para datos sensibles
- **Audit Trail**: Logging completo de todas las operaciones
- **Broker Security**: Secure API key management

## 🪄 Estrategias Actuales

### Implemented Strategies

- **Momentum Strategy**: RSI, EMA crossover signals, Volume analysis
- **Liquidity Strategy**: Bid-ask spread analysis, Volume profile analysis
- **Signal Scorer**: Confidence and liquidity-based signal ranking

### Strategy Framework

```python
# Common interface for all trading clients
class TradingClientInterface(ABC):
    async def place_order(self, order: Order) -> str
    async def get_positions(self) -> List[Position]
    async def get_market_data(self, symbol: str) -> MarketData
    # ... more methods
```

### Supported Brokers

- **Paper Trading**: Simulation mode for testing
- **Interactive Brokers**: Real trading with IBKR API
- **Binance**: Crypto trading with Binance API

## 🔧 Setup Local Rápido

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd algoTrading

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the application
make up
```

### Make Commands

```bash
# Start all services
make up

# Start only API
make api

# Start with database
make db

# Stop all services
make down

# View logs
make logs

# Clean up
make clean
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/algotrading

# Redis
REDIS_URL=redis://localhost:6379/0

# Trading
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key

# Debug
DEBUG=true
LOG_LEVEL=INFO
```

## 🧪 Cómo Correr Tests

### Test Suite

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_database.py -v

# Run tests with async support
pytest -v --asyncio-mode=auto

# Run tests in parallel
pytest -n auto
```

### Test Structure

```
tests/
├── test_config.py          # Configuration tests
├── test_database.py         # Database tests
├── test_main.py            # FastAPI tests
├── test_portfolio.py       # Portfolio tests (T004)
├── test_signals.py         # Signal tests (T005)
├── test_strategies.py      # Strategy tests (T007)
└── test_trading.py         # Trading interface tests
```

### Test Coverage

- **Target**: >90% coverage for all new code
- **Current**: 66/66 tests passing (100%)
- **Coverage**: T001-T003 implemented with high coverage

## 🧭 Roadmap Técnico (T001-T036)

### MVP Strategy

- **MVP1: Paper Trader (T001-T008)** - 3 semanas
- **MVP2: Live Broker (T009-T014)** - 4 semanas
- **MVP3: Analytics & Dashboard (T015-T020)** - 3 semanas
- **MVP4: ML & Optimization (T021-T028)** - 4 semanas
- **MVP5: Production Ready (T029-T036)** - 3 semanas

### Phase 1: Foundation (T001-T010) - ✅ 3/10 Completed

- **T001**: ✅ FastAPI Base Structure & Health Endpoints
- **T002**: ✅ Configuration Management with Pydantic
- **T003**: ✅ PostgreSQL Database Setup with SQLAlchemy
- **T004**: 🔄 Portfolio Source of Truth (NEXT)
- **T005**: ⏳ Signal Scorer System
- **T006**: ⏳ Top 20 Liquid Assets Identification
- **T007**: ⏳ Momentum Strategy Implementation
- **T008**: ⏳ Analytic Mode (Paper Trading)
- **T009**: ⏳ Market Data Integration
- **T010**: ⏳ Signal Confidence Validation

### Phase 2: Trading Engine (T011-T020)

- **T011**: Broker API Integration (IBKR)
- **T012**: Broker API Integration (Binance)
- **T013**: Order Execution Engine
- **T014**: Position Management System
- **T015**: Risk Management Engine
- **T016**: Backtesting Engine
- **T017**: Performance Analytics
- **T018**: Portfolio Management
- **T019**: Real-time Monitoring
- **T020**: Dashboard Development

### Phase 3: Advanced Features (T021-T030)

- **T021**: Multi-Asset Strategy Support
- **T022**: Machine Learning Integration
- **T023**: Advanced Analytics
- **T024**: Performance Optimization
- **T025**: Compliance Features
- **T026**: Alert System
- **T027**: Data Pipeline Optimization
- **T028**: Strategy Optimization
- **T029**: Advanced Risk Models
- **T030**: System Integration Testing

### Phase 4: Production Ready (T031-T036)

- **T031**: Security Hardening
- **T032**: Monitoring & Observability
- **T033**: Disaster Recovery
- **T034**: Load Testing
- **T035**: Production Deployment
- **T036**: Final Validation

## 📊 Current Status

### Progress

- **Completed**: 3/36 tasks (8.3%)
- **Current Phase**: Foundation (T001-T010)
- **Next Task**: T004 - Portfolio Source of Truth
- **Tests**: 66/66 passing (100%)

### Architecture Decisions

- **TradingClientInterface**: Common interface for all trading clients
- **Concurrency**: asyncio.Queue for market data processing
- **Early Testing**: pytest + coverage from the start
- **Docker Early**: docker-compose.yml for reproducible environment
- **Structured Logging**: FastAPI + loguru for better observability
- **CI/CD Early**: GitHub Actions before connecting real brokers

## 🚀 Quick Commands

### Development

```bash
# Start development environment
make dev

# Run API in development mode
make api-dev

# Run database migrations
make migrate

# Create new migration
make migration name="add_portfolio_table"
```

### Testing

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run specific test
make test-file file=tests/test_portfolio.py
```

### Production

```bash
# Build production image
make build

# Deploy to production
make deploy

# Run production environment
make prod
```

## 📚 Documentation

### Key Documents

- **`.memory/specs/tasks/complete_tasks_definition.md`** - Complete task breakdown
- **`.memory/specs/mvp_roadmap_detailed.md`** - MVP roadmap
- **`.memory/core/active_context.md`** - Current work focus
- **`.memory/core/progress.md`** - Project progress

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🤝 Contributing

### Development Workflow

1. Create feature branch: `git checkout -b feature/T004-portfolio-source`
2. Implement changes with tests
3. Run tests: `pytest -v`
4. Check coverage: `pytest --cov=app`
5. Create pull request

### Code Quality

- **Linting**: `black . && flake8 .`
- **Type Checking**: `mypy app/`
- **Testing**: `pytest -v --cov=app`

## 📈 Success Metrics

### Trading Performance

- **Profitability**: Sharpe ratio > 1.5
- **Win Rate**: > 60% de trades exitosos
- **Max Drawdown**: < 15%
- **Annual Return**: > 20% anual

### System Performance

- **Latency**: < 100ms para decisiones de trading
- **Uptime**: 99.99% availability
- **Accuracy**: > 95% order execution accuracy
- **Reliability**: < 0.1% system errors

## 📞 Support

### Issues

- **Bug Reports**: Create issue with detailed description
- **Feature Requests**: Use feature request template
- **Questions**: Use discussion forum

### Contact

- **Project Lead**: [Your Name]
- **Email**: [your-email@domain.com]
- **Documentation**: [Link to docs]

---

**AlgoTrading** - Personal Algorithmic Trading System  
_Generating money through automated trading strategies_
