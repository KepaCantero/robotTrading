# Technical Context - AlgoTrading MVP

## Technology Stack

### Backend Core

- **Language**: Python 3.11+ (compatible with 3.10+)
- **Framework**: FastAPI 0.115+ con async/await patterns
- **ORM**: SQLAlchemy 2.0.x
- **Database**: PostgreSQL 15.x
- **Caching**: Redis 7.x para session management y performance
- **Serialization**: Pydantic 2.x
- **Package Management**: Poetry para dependency management

### Trading & Financial Libraries

- **Data Analysis**: pandas 2.x, numpy 1.24+
- **Technical Analysis**: ta-lib, pandas-ta, yfinance
- **Trading APIs**: Interactive Brokers API, Binance API, Alpha Vantage
- **Backtesting**: backtrader, zipline-reloaded
- **Market Data**: yfinance, alpha_vantage, ccxt
- **Financial Calculations**: quantlib-python, scipy
- **Strategy Framework**: Sistema de Estrategias Múltiples (BaseStrategy, Factory, Registry)
- **Strategy Engines**: Sistema de engines refactorizados (`MomentumStrategyEngine`, `MeanReversionStrategyEngine`, `PairsTradingStrategyEngine`, `ModularMomentumStrategyEngine`, `BreakoutStrategyEngine`, `TrendFollowingStrategyEngine`) sobre `BaseStrategyEngine`
- **Configuración Centralizada**: Sistema de configuración YAML (`config/strategies/*.yaml`) para todos los engines, eliminando magic numbers
- **Walk Forward Analysis**: Implementación custom para validación robusta
- **Bias Detection**: Sistema de detección de Look-Ahead Bias y Data Snooping
- **Next Level Engines (Plan Maestro)**: mlfinlab, riskfolio-lib, PyPortfolioOpt, optuna/ray[tune], stable-baselines3, torch/transformers (según módulo descrito en `docs/PLAN_MAESTRO_NEXT_LEVEL.md`), ya integrados en parte en `DataEngine`, `ContextEngine`, `PortfolioEngine`, `RiskEngine` y el sistema de learning de `momentum_modular`.

### Asynchronous Processing

- **Task Queue**: Celery 5.3+ con Redis/RabbitMQ
- **Message Broker**: RabbitMQ / AWS SQS
- **Background Jobs**: Async task processing para trading
- **Real-time Processing**: WebSockets para market data

### Security

- **Authentication**: OAuth 2.0 + JWT
- **Authorization**: RBAC (Role-Based Access Control)
- **Encryption**: AES-256 para datos sensibles
- **Libraries**: PyJWT 2.x, passlib 1.8.x, cryptography
- **Protection**: XSS, CSRF, SQL Injection prevention
- **API Security**: Rate limiting, API keys management

### Testing & Quality

- **Testing**: pytest 8.x + HTTPX para testing async
- **Coverage**: coverage 7.x con >90% target
- **Code Quality**: black, isort, ruff
- **Type Checking**: mypy strict mode
- **Docstrings**: Google style docstrings
- **Pre-commit**: Hooks para quality gates
- **Code Contracts**: Design by Contract with Pydantic validation
- **Contract Testing**: Comprehensive contract violation testing
- **Data Validation**: Automatic validation of critical trading data

### Frontend & Dashboard

- **Dashboard**: Streamlit 1.37 para análisis y visualización
- **Charts**: plotly, matplotlib, seaborn
- **Real-time Updates**: Streamlit components para live data
- **Deployment**: Streamlit Cloud / AWS EC2

### Infrastructure & DevOps

- **Containerization**: Docker 24.x, Docker Compose 2.x
- **Cloud Platform**: AWS (EC2, RDS, S3, ElastiCache, CloudWatch)
- **CI/CD**: GitHub Actions con build_and_test.yml, docker_push.yml, deploy_aws.yml
- **Load Balancing**: Application Load Balancer
- **Monitoring**: CloudWatch, Prometheus, Grafana
- **Region**: AWS eu-west-1

## Architecture Patterns

### AlgoTrading Architecture

- **Core Engine**: FastAPI con async/await para high-performance trading
- **Strategy Pattern**: Modular trading strategies (Momentum, Liquidity)
- **Event-Driven**: Real-time market data processing con WebSockets
- **Microservices**: Separación clara entre trading, analysis, y dashboard
- **CQRS**: Separate read/write models para trading data

### Trading System Patterns

- **Strategy Factory**: Creación dinámica de estrategias de trading (incluye engines: momentum, mean_reversion, pairs_trading, breakout, trend_following)
- **Strategy Engines Pattern**: Engines refactorizados sobre `BaseStrategyEngine` con integración opcional a Data/Context/Portfolio/Risk/Learning
- **Configuración Centralizada**: Sistema YAML para parámetros de estrategias (`config/strategies/*.yaml`)
- **Signal Processing**: Pipeline para procesamiento de señales de mercado
- **Risk Management**: Sistema de gestión de riesgo integrado
- **Portfolio Management**: Gestión de carteras y posiciones
- **Backtesting Engine**: Motor de backtesting con historical data (integración completa con Strategy Engines)

### Data Processing Patterns

- **Market Data Pipeline**: ETL para datos de mercado en tiempo real
- **Technical Analysis**: Cálculo de indicadores técnicos
- **Signal Generation**: Generación de señales de trading
- **Alert System**: Sistema de alertas y notificaciones
- **Data Caching**: Redis para caching de datos de mercado

### Repository Pattern

- **Data Access**: SQLAlchemy repositories para trading data
- **Market Data**: Repositories para datos de mercado
- **Strategy Data**: Repositories para estrategias y configuraciones
- **User Data**: Repositories para usuarios y portfolios
- **Caching**: Redis integration layer para performance

## Development Standards

### Code Conventions

- **Files/Functions/Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Private Methods**: \_leading_underscore
- **Trading Functions**: Descriptive names con trading context

### AlgoTrading Project Structure

```
/project_root
├── /app
│   ├── /api              # FastAPI endpoints
│   │   ├── /trading      # Trading endpoints
│   │   ├── /strategies   # Strategy management
│   │   └── /portfolio    # Portfolio management
│   ├── /models           # SQLAlchemy models
│   │   ├── /trading      # Trading models
│   │   ├── /users        # User models
│   │   └── /market_data  # Market data models
│   ├── /schemas          # Pydantic schemas
│   ├── /services         # Business logic
│   │   ├── /trading      # Trading services
│   │   ├── /strategies   # Strategy services
│   │   └── /market_data  # Market data services
│   ├── /strategies       # Trading strategies
│   │   ├── /base         # Base strategy classes
│   │   ├── /momentum     # Momentum strategies
│   │   └── /liquidity    # Liquidity strategies
│   ├── /core             # Configuration, security
│   ├── /utils            # Helper functions
│   └── /workers          # Celery workers
├── /dashboard            # Streamlit dashboard
│   ├── /pages            # Dashboard pages
│   ├── /components       # Reusable components
│   └── /utils            # Dashboard utilities
├── /tests
│   ├── /unit             # Unit tests
│   ├── /integration      # Integration tests
│   └── /e2e              # End-to-end tests
├── /docs                 # Documentation
├── /scripts              # Deployment scripts
├── /docker               # Docker configurations
└── /requirements         # Dependencies
```

### Database Design

- **Primary Database**: PostgreSQL 15.x para trading data
- **Caching Layer**: Redis 7.x para market data y sessions
- **Connection Pooling**: SQLAlchemy engine con async support
- **Migrations**: Alembic para schema management
- **Backup Strategy**: Daily automated backups con point-in-time recovery
- **Trading Tables**: Optimized para high-frequency data

### Security Implementation

- **Authentication Flow**: OAuth 2.0 + JWT tokens
- **Role Management**: Database-driven RBAC para traders
- **Data Encryption**: AES-256 para sensitive trading data
- **API Security**: Rate limiting, CORS, input validation
- **Audit Logging**: Comprehensive trading activity tracking
- **API Keys**: Secure management de broker API keys

## Performance Requirements

- **Response Time**: < 1.5s para trading decisions
- **Concurrent Users**: 1,000+ simultaneous connections
- **Market Data**: Real-time processing de market feeds
- **Scalability**: Horizontal scaling con load balancers
- **Caching**: Multi-layer caching para market data
- **Backtesting**: Efficient historical data processing

## Deployment Architecture

- **Containerization**: Docker containers con multi-stage builds
- **Orchestration**: Docker Compose (dev) / AWS ECS (prod)
- **Load Balancing**: Application Load Balancer
- **Auto Scaling**: Based on CPU/memory metrics
- **Health Checks**: Comprehensive monitoring
- **Blue-Green Deployment**: Zero-downtime updates
- **Streamlit Deployment**: Separate container para dashboard

## Monitoring & Observability

- **Application Metrics**: Trading performance, strategy metrics
- **Infrastructure Metrics**: CPU, memory, disk, network
- **Logging**: Structured JSON logging con trading context
- **Alerting**: Proactive issue detection para trading systems
- **Tracing**: Distributed request tracing
- **Health Endpoints**: Kubernetes readiness/liveness probes
- **Trading Metrics**: P&L, drawdown, Sharpe ratio tracking

## CI/CD Pipeline

### GitHub Actions Workflows

- **build_and_test.yml**: Build, test, y quality checks
- **docker_push.yml**: Build y push Docker images
- **deploy_aws.yml**: Deploy a AWS infrastructure
- **security_scan.yml**: Security scanning y vulnerability checks

### Quality Gates

- **Test Coverage**: >90% con pytest + HTTPX
- **Code Quality**: black, isort, ruff, mypy
- **Security**: bandit security scanning
- **Performance**: Load testing con trading scenarios
- **Integration**: End-to-end testing con mock brokers
