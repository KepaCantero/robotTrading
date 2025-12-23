# Technical Context - AlgoTrading

## Technology Stack

### Backend Core

- Language: Python 3.11+ (compatible with 3.10+)
- Framework: FastAPI 0.115+ con async/await patterns
- ORM: SQLAlchemy 2.0.x
- Database: PostgreSQL 15.x
- Caching: Redis 7.x para session management y performance
- Serialization: Pydantic 2.x
- Package Management: Poetry para dependency management

### Trading & Financial Libraries

- Data Analysis: pandas 2.x, numpy 1.24+
- Technical Analysis: ta-lib, pandas-ta, yfinance
- Trading APIs: Interactive Brokers API, Binance API, Alpha Vantage
- Backtesting: backtrader, zipline-reloaded
- Market Data: yfinance, alpha_vantage, ccxt
- Financial Calculations: quantlib-python, scipy
- Strategy Framework: Sistema de Estrategias Múltiples (BaseStrategy, Factory, Registry)
- Strategy Engines: Sistema de engines refactorizados sobre `BaseStrategyEngine`
- Configuración Centralizada: Sistema de configuración YAML (`config/strategies/*.yaml`)
- Walk Forward Analysis: Implementación custom para validación robusta
- Drift Detection: Sistema completo de detección de drift para ML models (PSI, ADWIN, KS Test, MMD)
- Next Level Engines: mlfinlab, riskfolio-lib, PyPortfolioOpt, optuna/ray[tune], stable-baselines3, torch/transformers

### Asynchronous Processing

- Task Queue: Celery 5.3+ con Redis/RabbitMQ
- Message Broker: RabbitMQ / AWS SQS
- Background Jobs: Async task processing para trading
- Real-time Processing: WebSockets para market data

### Security

- Authentication: OAuth 2.0 + JWT
- Authorization: RBAC (Role-Based Access Control)
- Encryption: AES-256 para datos sensibles
- Libraries: PyJWT 2.x, passlib 1.8.x, cryptography
- Protection: XSS, CSRF, SQL Injection prevention
- API Security: Rate limiting, API keys management

### Testing & Quality

- Testing: pytest 8.x + HTTPX para testing async
- Coverage: coverage 7.x con >90% target
- Code Quality: black, isort, ruff
- Type Checking: mypy strict mode
- Docstrings: Google style docstrings
- Pre-commit: Hooks para quality gates
- Code Contracts: Design by Contract with Pydantic validation

### Frontend & Dashboard

- Dashboard: Streamlit 1.37 para análisis y visualización
- Charts: plotly, matplotlib, seaborn
- Real-time Updates: Streamlit components para live data
- Deployment: Streamlit Cloud / AWS EC2

### Infrastructure & DevOps

- Containerization: Docker 24.x, Docker Compose 2.x
- Cloud Platform: AWS (EC2, RDS, S3, ElastiCache, CloudWatch)
- CI/CD: GitHub Actions con build_and_test.yml, docker_push.yml, deploy_aws.yml
- Load Balancing: Application Load Balancer
- Monitoring: CloudWatch, Prometheus, Grafana
- Region: AWS eu-west-1

## Architecture Patterns

### AlgoTrading Architecture

- Core Engine: FastAPI con async/await para high-performance trading
- Strategy Pattern: Modular trading strategies
- Event-Driven: Real-time market data processing con WebSockets
- Microservices: Separación clara entre trading, analysis, y dashboard
- CQRS: Separate read/write models para trading data

### Trading System Patterns

- Strategy Factory: Creación dinámica de estrategias de trading (incluye engines)
- Strategy Engines Pattern: Engines refactorizados sobre `BaseStrategyEngine`
- Configuración Centralizada: Sistema YAML para parámetros de estrategias
- Signal Processing: Pipeline para procesamiento de señales de mercado
- Risk Management: Sistema de gestión de riesgo integrado
- Portfolio Management: Gestión de carteras y posiciones
- Backtesting Engine: Motor de backtesting con historical data

### Data Processing Patterns

- Market Data Pipeline: ETL para datos de mercado en tiempo real
- Technical Analysis: Cálculo de indicadores técnicos
- Signal Generation: Generación de señales de trading
- Alert System: Sistema de alertas y notificaciones
- Data Caching: Redis para caching de datos de mercado

## Development Standards

### Code Conventions

- Files/Functions/Variables: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Private Methods: \_leading_underscore
- Trading Functions: Descriptive names con trading context

## Performance Requirements

- Response Time: < 1.5s para trading decisions
- Concurrent Users: 1,000+ simultaneous connections
- Market Data: Real-time processing de market feeds
- Scalability: Horizontal scaling con load balancers
- Caching: Multi-layer caching para market data
- Backtesting: Efficient historical data processing
