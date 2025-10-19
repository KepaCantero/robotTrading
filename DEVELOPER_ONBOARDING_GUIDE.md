# 🚀 Developer Onboarding Guide - AlgoTrading System

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Trading Concepts for Developers](#trading-concepts-for-developers)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [Current Implementation Status](#current-implementation-status)
5. [Technical Setup](#technical-setup)
6. [Codebase Structure](#codebase-structure)
7. [Implementation Guide for Remaining Tasks](#implementation-guide-for-remaining-tasks)
8. [Testing Strategy](#testing-strategy)
9. [Development Workflow](#development-workflow)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

### What is AlgoTrading?

**AlgoTrading** is a **personal algorithmic trading system** designed to **generate money** through automated trading strategies. This is **NOT** a multi-user platform - it's designed for personal use by a single trader.

### Core Objectives

- **Make Money**: Generate profit through algorithmic trading
- **Automated Strategies**: Momentum and liquidity-based trading strategies
- **Multi-Asset Support**: Stocks, cryptocurrencies, and forex
- **Paper Trading First**: Test strategies safely before risking real money
- **High Performance**: Sub-second response times for trading decisions

### Key Differentiators

- **Personal System**: No user management, authentication, or multi-tenancy
- **Strategy-Focused**: Built around trading strategies, not user interfaces
- **Performance-Oriented**: Optimized for speed and reliability
- **Risk Management**: Built-in circuit breakers and position sizing

---

## 📈 Trading Concepts for Developers

### Essential Trading Terminology

#### **Assets & Markets**

- **Asset**: Any tradable financial instrument (stocks, crypto, forex)
- **Symbol**: Unique identifier for an asset (e.g., "AAPL", "BTCUSDT")
- **Market**: Where assets are traded (NYSE, NASDAQ, Binance)
- **Liquidity**: How easily an asset can be bought/sold without affecting price

#### **Orders & Positions**

- **Order**: Instruction to buy or sell an asset
- **Position**: Current holding of an asset (long = owning, short = borrowing)
- **Portfolio**: Collection of all positions and cash
- **P&L**: Profit and Loss - how much money you've made/lost

#### **Trading Strategies**

- **Momentum**: Buy assets that are going up, sell those going down
- **Liquidity**: Trade assets with high volume and tight spreads
- **Signal**: Mathematical indicator suggesting when to buy/sell
- **Backtesting**: Testing strategies on historical data

#### **Risk Management**

- **Position Sizing**: How much money to risk on each trade
- **Stop Loss**: Automatic sell order to limit losses
- **Circuit Breaker**: System protection against excessive losses
- **Diversification**: Spreading risk across multiple assets

### Trading Strategy Example

```python
# Simple momentum strategy
def momentum_signal(price_data):
    # Calculate RSI (Relative Strength Index)
    rsi = calculate_rsi(price_data, period=14)

    # Buy signal: RSI < 30 (oversold)
    if rsi < 30:
        return "BUY"

    # Sell signal: RSI > 70 (overbought)
    elif rsi > 70:
        return "SELL"

    # Hold signal: RSI between 30-70
    else:
        return "HOLD"
```

---

## 🏗️ Architecture Deep Dive

### System Architecture

```mermaid
graph TB
    subgraph "Trading Engine"
        A[FastAPI App] --> B[Signal Scorer]
        B --> C[Portfolio Service]
        C --> D[Trading Client Interface]
    end

    subgraph "Data Layer"
        E[PostgreSQL] --> F[Portfolio Data]
        G[Redis] --> H[Market Data Cache]
    end

    subgraph "External APIs"
        I[Market Data Feeds]
        J[Broker APIs]
        K[Paper Trading Simulator]
    end

    A --> E
    A --> G
    D --> J
    D --> K
    B --> I
```

### Core Components

#### **1. Signal Scorer System**

- **Purpose**: Evaluates trading opportunities and ranks them by priority
- **Key Features**:
  - Multi-factor confidence scoring (momentum, volume, volatility)
  - Liquidity ranking based on volume and spread analysis
  - Priority queue for efficient signal management
  - Real-time signal evaluation with configurable thresholds

#### **2. Portfolio Management**

- **Purpose**: Manages trading positions and portfolio state
- **Key Features**:
  - Real-time portfolio tracking with P&L calculations
  - Position sizing and risk management
  - Circuit breakers for operational resilience
  - Market regime detection for strategy adaptation

#### **3. Trading Client Interface**

- **Purpose**: Common interface for all trading operations
- **Supported Clients**:
  - Paper Trading (simulation)
  - Interactive Brokers (real trading)
  - Binance (crypto trading)

### Data Flow

```mermaid
sequenceDiagram
    participant MD as Market Data
    participant SS as Signal Scorer
    participant PS as Portfolio Service
    participant TC as Trading Client

    MD->>SS: Real-time price data
    SS->>SS: Calculate confidence score
    SS->>PS: Get portfolio context
    PS->>SS: Portfolio data
    SS->>SS: Calculate priority score
    SS->>TC: Execute signal
    TC->>PS: Update portfolio
```

---

## 📊 Current Implementation Status

### ✅ Completed Tasks (5/10 Foundation Phase)

#### **T001: FastAPI Base Structure** ✅

- **Files**: `app/main.py`, `app/__init__.py`
- **Features**: Health endpoints, CORS configuration, async setup
- **Tests**: 8/8 passing
- **Coverage**: 100%

#### **T002: Configuration System** ✅

- **Files**: `app/core/config.py`
- **Features**: Pydantic BaseSettings, environment management
- **Tests**: 24/24 passing
- **Coverage**: 96%

#### **T003: PostgreSQL Database** ✅

- **Files**: `app/core/database.py`
- **Features**: SQLAlchemy async connection, session management
- **Tests**: 30/30 passing
- **Coverage**: 86%

#### **T004: Portfolio Source of Truth** ✅

- **Files**:
  - `app/models/portfolio.py` (219 lines)
  - `app/providers/paper_trading.py` (239 lines)
  - `app/services/portfolio_service.py` (250 lines)
  - `app/api/portfolio.py` (222 lines)
- **Features**:
  - PortfolioProvider Protocol Interface
  - PaperTradingPortfolioProvider for testing
  - Enhanced Portfolio and Position models
  - Market Regime Detection
  - Asset Universe Management
  - Circuit Breakers for risk management
- **Tests**: 22/22 passing
- **Coverage**: 78%

#### **T005: Signal Scorer System** ✅

- **Files**:
  - `app/models/signal.py` (447 lines)
  - `app/services/signal_scorer.py` (383 lines)
  - `app/api/signals.py` (312 lines)
- **Features**:
  - Multi-factor confidence scoring algorithm
  - Liquidity ranking system
  - Heap-based priority queue
  - Signal scorer service with portfolio integration
  - FastAPI endpoints for signal management
- **Tests**: 32/32 passing
- **Coverage**: 81%
- **Performance**: 493+ signals/second

### 🔄 Next Tasks (T006-T010)

#### **T006: Top 20 Liquid Assets Identification** 🔄 NEXT

- **Goal**: Identify and configure top 20 most liquid assets
- **Files to Create**:
  - `app/models/assets.py` - Asset models and liquidity metrics
  - `app/services/asset_service.py` - Asset identification and ranking service
  - `app/api/assets.py` - FastAPI endpoints for asset management
  - `tests/test_asset_service.py` - Comprehensive test suite

#### **T007: Momentum Strategy Implementation**

- **Goal**: Implement daily momentum strategy with RSI/EMA
- **Dependencies**: T006 (Asset identification)

#### **T008: Analytic Mode (Paper Trading)**

- **Goal**: Complete paper trading simulation
- **Dependencies**: T007 (Strategy implementation)

#### **T009: Market Data Integration**

- **Goal**: Real-time market data feeds
- **Dependencies**: T008 (Paper trading)

#### **T010: Signal Confidence Validation**

- **Goal**: Risk assessment and validation
- **Dependencies**: T009 (Market data)

### 📈 Overall Progress

- **Foundation Phase**: 5/10 tasks completed (50%)
- **Total Tests**: 200 tests (198 passing, 2 failing)
- **Code Coverage**: 89%
- **Architecture**: Solid foundation with async patterns
- **Quality**: High-quality code with comprehensive testing

---

## 🔧 Technical Setup

### Prerequisites

```bash
# Required software
Python 3.11+
PostgreSQL 15+
Redis 7+
Docker & Docker Compose (optional)
Git
```

### Environment Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd algoTrading

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp env.example .env
# Edit .env with your configuration

# 5. Start services with Docker Compose
make up
# OR manually:
# docker-compose up -d postgres redis

# 6. Run database migrations
alembic upgrade head

# 7. Start the application
make dev
# OR manually:
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/algotrading

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
DEBUG=true
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO

# Trading (for future use)
IBKR_API_KEY=your-ibkr-key
BINANCE_API_KEY=your-binance-key
```

### Development Tools

```bash
# Code formatting
make format
# Runs: black . && isort . && ruff check --fix

# Type checking
make type-check
# Runs: mypy app/

# Testing
make test
# Runs: pytest -v --cov=app --cov-report=html

# Full quality check
make quality
# Runs: format + type-check + test
```

---

## 📁 Codebase Structure

### Project Layout

```
algotrading/
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration management
│   │   └── database.py          # Database connection and sessions
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── portfolio.py         # Portfolio and position models
│   │   └── signal.py            # Signal and market data models
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── portfolio_service.py # Portfolio management service
│   │   └── signal_scorer.py     # Signal evaluation service
│   ├── providers/                # External service providers
│   │   ├── __init__.py
│   │   └── paper_trading.py     # Paper trading provider
│   └── api/                      # FastAPI endpoints
│       ├── __init__.py
│       ├── portfolio.py         # Portfolio API endpoints
│       └── signals.py           # Signal API endpoints
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_config.py           # Configuration tests
│   ├── test_database.py         # Database tests
│   ├── test_portfolio.py        # Portfolio tests
│   ├── test_signal_scorer.py    # Signal scorer tests
│   ├── test_api_integration.py  # API integration tests
│   ├── test_service_integration.py # Service integration tests
│   └── test_e2e_integration.py  # End-to-end tests
├── .memory/                      # Project memory bank
│   ├── core/                    # Core documentation
│   ├── specs/                   # Specifications
│   └── lessons/                 # Implementation lessons
├── docs/                        # Additional documentation
├── requirements.txt             # Python dependencies
├── pytest.ini                  # Pytest configuration
├── docker-compose.yml          # Docker services
├── Dockerfile                  # Application container
├── Makefile                    # Development commands
└── PROJECT_README.md           # Project overview
```

### Key Files Explained

#### **app/main.py** - Application Entry Point

```python
from fastapi import FastAPI
from app.api import portfolio, signals

app = FastAPI(
    title="AlgoTrading API",
    description="Personal Algorithmic Trading System",
    version="1.0.0"
)

# Include routers
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(signals.router, prefix="/signals", tags=["signals"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

#### **app/models/signal.py** - Signal Models

```python
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from enum import Enum

class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class Signal(BaseModel):
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float = Field(ge=0, le=100)
    liquidity_score: float = Field(ge=0, le=100)
    priority_score: float = Field(ge=0, le=100)
    source: SignalSource
    price: Decimal
    volume: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

#### **app/services/signal_scorer.py** - Signal Evaluation Service

```python
class SignalScorerService:
    def __init__(self):
        self.priority_queue = SignalPriorityQueue(max_size=1000)
        self.min_confidence_threshold = 50.0
        self.min_liquidity_threshold = 30.0

    async def evaluate_signal(
        self,
        symbol: str,
        signal_type: SignalType,
        market_data: MarketData,
        metadata: dict
    ) -> Optional[Signal]:
        # Calculate confidence score
        confidence = self._calculate_confidence_score(metadata)

        # Calculate liquidity score
        liquidity_score = self._calculate_liquidity_score(market_data)

        # Create signal
        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            liquidity_score=liquidity_score,
            # ... other fields
        )

        # Add to priority queue
        self.priority_queue.add_signal(signal)
        return signal
```

---

## 🛠️ Implementation Guide for Remaining Tasks

### T006: Top 20 Liquid Assets Identification

#### **Goal**

Identify and configure the top 20 most liquid assets for daily momentum trading.

#### **Implementation Steps**

1. **Create Asset Models** (`app/models/assets.py`)

```python
from pydantic import BaseModel
from decimal import Decimal
from enum import Enum

class AssetClass(str, Enum):
    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"

class Asset(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass
    exchange: str
    liquidity_score: float
    avg_volume: Decimal
    avg_spread: Decimal
    market_cap: Optional[Decimal] = None
    is_active: bool = True

class AssetUniverse(BaseModel):
    asset_class: AssetClass
    assets: List[Asset]
    top_n: int = 20
    last_updated: datetime
```

2. **Create Asset Service** (`app/services/asset_service.py`)

```python
class AssetService:
    def __init__(self):
        self.asset_universes: Dict[AssetClass, AssetUniverse] = {}

    async def identify_top_liquid_assets(
        self,
        asset_class: AssetClass,
        top_n: int = 20
    ) -> AssetUniverse:
        # Get market data for all assets in class
        # Calculate liquidity scores
        # Rank by liquidity
        # Return top N assets
        pass

    async def update_liquidity_scores(self, asset_class: AssetClass):
        # Update liquidity scores for all assets
        # Re-rank assets
        # Update asset universe
        pass
```

3. **Create API Endpoints** (`app/api/assets.py`)

```python
from fastapi import APIRouter, Depends
from app.services.asset_service import AssetService

router = APIRouter()

@router.get("/universe/{asset_class}")
async def get_asset_universe(asset_class: AssetClass):
    # Return top liquid assets for asset class
    pass

@router.post("/refresh/{asset_class}")
async def refresh_asset_universe(asset_class: AssetClass):
    # Refresh liquidity scores and rankings
    pass
```

4. **Create Tests** (`tests/test_asset_service.py`)

```python
import pytest
from app.services.asset_service import AssetService
from app.models.assets import AssetClass

class TestAssetService:
    @pytest.fixture
    def asset_service(self):
        return AssetService()

    @pytest.mark.asyncio
    async def test_identify_top_liquid_assets(self, asset_service):
        # Test asset identification
        universe = await asset_service.identify_top_liquid_assets(AssetClass.EQUITY)
        assert len(universe.assets) == 20
        assert universe.asset_class == AssetClass.EQUITY
```

#### **Success Criteria**

- [ ] Top 20 liquid assets identified for each asset class
- [ ] Liquidity ranking system functional
- [ ] Asset universe management per broker
- [ ] Integration with signal scorer for asset validation
- [ ] FastAPI endpoints for asset management
- [ ] > 90% test coverage
- [ ] Ready for T007 implementation

### T007: Momentum Strategy Implementation

#### **Goal**

Implement daily momentum strategy with RSI/EMA indicators.

#### **Implementation Steps**

1. **Create Strategy Models** (`app/models/strategy.py`)

```python
class MomentumStrategy(BaseModel):
    name: str = "Daily Momentum"
    timeframe: str = "1d"
    indicators: Dict[str, Any]
    parameters: Dict[str, float]

class StrategySignal(BaseModel):
    strategy_name: str
    symbol: str
    signal_type: SignalType
    confidence: float
    indicators: Dict[str, float]
    timestamp: datetime
```

2. **Create Strategy Service** (`app/services/strategy_service.py`)

```python
class MomentumStrategyService:
    def __init__(self, signal_scorer: SignalScorerService):
        self.signal_scorer = signal_scorer

    async def evaluate_momentum_signal(
        self,
        symbol: str,
        market_data: List[MarketData]
    ) -> Optional[StrategySignal]:
        # Calculate RSI
        rsi = self._calculate_rsi(market_data)

        # Calculate EMA
        ema_short = self._calculate_ema(market_data, period=12)
        ema_long = self._calculate_ema(market_data, period=26)

        # Determine signal
        if rsi < 30 and ema_short > ema_long:
            return StrategySignal(
                strategy_name="Daily Momentum",
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=self._calculate_confidence(rsi, ema_short, ema_long),
                indicators={"rsi": rsi, "ema_short": ema_short, "ema_long": ema_long}
            )
        # ... more signal logic
```

3. **Integration with Signal Scorer**

```python
# In signal_scorer.py
async def evaluate_strategy_signals(self, symbol: str):
    # Get market data
    market_data = await self._get_market_data(symbol)

    # Evaluate momentum strategy
    momentum_service = MomentumStrategyService(self)
    strategy_signal = await momentum_service.evaluate_momentum_signal(symbol, market_data)

    if strategy_signal:
        # Convert to regular signal and add to queue
        signal = Signal(
            symbol=symbol,
            signal_type=strategy_signal.signal_type,
            confidence=strategy_signal.confidence,
            # ... other fields
        )
        self.priority_queue.add_signal(signal)
```

### T008: Analytic Mode (Paper Trading)

#### **Goal**

Complete paper trading simulation with realistic market conditions.

#### **Implementation Steps**

1. **Enhance Paper Trading Provider** (`app/providers/paper_trading.py`)

```python
class EnhancedPaperTradingProvider(PaperTradingPortfolioProvider):
    def __init__(self):
        super().__init__()
        self.market_simulator = MarketSimulator()
        self.slippage_calculator = SlippageCalculator()

    async def simulate_trade_with_slippage(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        order_type: str
    ) -> TradeResult:
        # Calculate realistic slippage
        slippage = self.slippage_calculator.calculate(symbol, quantity, order_type)

        # Simulate market impact
        execution_price = price * (1 + slippage)

        # Execute trade
        return await self._execute_trade(symbol, quantity, execution_price)
```

2. **Create Market Simulator** (`app/services/market_simulator.py`)

```python
class MarketSimulator:
    def __init__(self):
        self.price_feeds = {}
        self.volatility_models = {}

    async def simulate_market_conditions(self, symbol: str) -> MarketConditions:
        # Simulate realistic market conditions
        # Include volatility, spreads, volume
        pass

    async def apply_market_impact(self, symbol: str, quantity: Decimal) -> Decimal:
        # Calculate market impact based on order size
        pass
```

### T009: Market Data Integration

#### **Goal**

Integrate real-time market data feeds.

#### **Implementation Steps**

1. **Create Market Data Service** (`app/services/market_data_service.py`)

```python
class MarketDataService:
    def __init__(self):
        self.data_feeds = {}
        self.cache = Redis()

    async def get_real_time_data(self, symbol: str) -> MarketData:
        # Check cache first
        cached_data = await self.cache.get(f"market_data:{symbol}")
        if cached_data:
            return MarketData.parse_raw(cached_data)

        # Fetch from data feed
        data = await self._fetch_from_feed(symbol)

        # Cache for 1 second
        await self.cache.setex(f"market_data:{symbol}", 1, data.json())

        return data

    async def subscribe_to_symbols(self, symbols: List[str]):
        # Subscribe to real-time updates
        for symbol in symbols:
            await self._subscribe(symbol)
```

2. **Create Data Feed Interfaces**

```python
class DataFeedInterface(ABC):
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        pass

    @abstractmethod
    async def get_historical_data(self, symbol: str, period: str) -> List[MarketData]:
        pass

class AlphaVantageFeed(DataFeedInterface):
    # Implementation for Alpha Vantage API
    pass

class YahooFinanceFeed(DataFeedInterface):
    # Implementation for Yahoo Finance API
    pass
```

### T010: Signal Confidence Validation

#### **Goal**

Implement risk assessment and signal validation.

#### **Implementation Steps**

1. **Create Risk Assessment Service** (`app/services/risk_service.py`)

```python
class RiskAssessmentService:
    def __init__(self, portfolio_service: PortfolioService):
        self.portfolio_service = portfolio_service
        self.risk_limits = RiskLimits()

    async def validate_signal(self, signal: Signal) -> ValidationResult:
        # Check portfolio risk
        portfolio_risk = await self._calculate_portfolio_risk()

        # Check position size limits
        position_size_ok = await self._check_position_size(signal)

        # Check correlation limits
        correlation_ok = await self._check_correlation(signal)

        # Check volatility limits
        volatility_ok = await self._check_volatility(signal)

        return ValidationResult(
            is_valid=all([position_size_ok, correlation_ok, volatility_ok]),
            risk_score=portfolio_risk,
            warnings=self._get_warnings(signal)
        )
```

2. **Create Risk Models**

```python
class RiskLimits(BaseModel):
    max_position_size: float = 0.1  # 10% of portfolio
    max_correlation: float = 0.7    # 70% correlation limit
    max_volatility: float = 0.3     # 30% volatility limit
    max_drawdown: float = 0.15      # 15% max drawdown

class ValidationResult(BaseModel):
    is_valid: bool
    risk_score: float
    warnings: List[str]
    recommendations: List[str]
```

---

## 🧪 Testing Strategy

### Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_models.py      # Model validation tests
│   ├── test_services.py    # Service logic tests
│   └── test_utils.py       # Utility function tests
├── integration/            # Integration tests
│   ├── test_api_integration.py    # API endpoint tests
│   ├── test_service_integration.py # Service integration tests
│   └── test_e2e_integration.py    # End-to-end workflow tests
└── fixtures/               # Test fixtures and data
    ├── market_data.py      # Sample market data
    └── portfolio_data.py   # Sample portfolio data
```

### Testing Best Practices

#### **1. Test Coverage Requirements**

- **Minimum**: 90% code coverage
- **Target**: 95% code coverage
- **Critical Paths**: 100% coverage for trading logic

#### **2. Test Types**

**Unit Tests**

```python
def test_signal_confidence_calculation():
    scorer = SignalScorer()
    metadata = {"rsi": 70, "volume": 1000000, "volatility": 0.02}
    confidence = scorer._calculate_confidence_score(metadata)
    assert 0 <= confidence <= 100
```

**Integration Tests**

```python
@pytest.mark.asyncio
async def test_signal_evaluation_workflow():
    # Test complete signal evaluation workflow
    signal_data = create_test_signal_data()
    response = await client.post("/signals/evaluate", json=signal_data)
    assert response.status_code == 200
    assert response.json()["success"] is True
```

**End-to-End Tests**

```python
@pytest.mark.asyncio
async def test_complete_trading_workflow():
    # Test complete workflow from signal to execution
    # 1. Evaluate signal
    # 2. Get next actionable signal
    # 3. Execute signal
    # 4. Verify portfolio changes
    pass
```

#### **3. Test Data Management**

**Fixtures**

```python
@pytest.fixture
def sample_market_data():
    return MarketData(
        symbol="AAPL",
        price=Decimal("150.00"),
        volume=Decimal("1000000"),
        bid=Decimal("149.95"),
        ask=Decimal("150.05"),
        spread=Decimal("0.10"),
        timestamp=datetime.utcnow()
    )

@pytest.fixture
def sample_portfolio():
    return Portfolio(
        cash=Decimal("100000"),
        positions=[
            Position(symbol="AAPL", quantity=100, avg_price=Decimal("145.00"))
        ],
        broker="paper_trading"
    )
```

**Mocking External Services**

```python
@pytest.fixture
def mock_market_data_service():
    with patch('app.services.market_data_service.MarketDataService') as mock:
        mock.return_value.get_real_time_data.return_value = sample_market_data()
        yield mock
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_signal_scorer.py

# Run specific test
pytest tests/test_signal_scorer.py::TestSignalScorer::test_confidence_calculation

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf

# Run tests in parallel
pytest -n auto
```

---

## 🔄 Development Workflow

### Git Workflow

#### **Branch Strategy**

```bash
# Main branches
main                    # Production-ready code
develop                 # Integration branch

# Feature branches
feature/T006-assets     # Asset identification feature
feature/T007-momentum   # Momentum strategy feature
feature/T008-paper      # Paper trading enhancement

# Hotfix branches
hotfix/critical-bug     # Critical bug fixes
```

#### **Commit Convention**

```bash
# Format: type(scope): description
feat(signals): add confidence scoring algorithm
fix(portfolio): resolve position calculation bug
test(api): add integration tests for signal endpoints
docs(readme): update setup instructions
refactor(services): extract common signal logic
```

#### **Pull Request Process**

1. **Create Feature Branch**: `git checkout -b feature/T006-assets`
2. **Implement Feature**: Write code and tests
3. **Run Quality Checks**: `make quality`
4. **Create Pull Request**: Include description and test results
5. **Code Review**: Address feedback
6. **Merge**: Squash and merge to develop

### Development Commands

```bash
# Start development environment
make dev

# Run tests
make test

# Format code
make format

# Type checking
make type-check

# Full quality check
make quality

# Start services
make up

# Stop services
make down

# View logs
make logs

# Database operations
make db-migrate
make db-reset
```

### Code Quality Standards

#### **Code Style**

- **Formatter**: Black (line length: 88)
- **Import Sorting**: isort
- **Linting**: ruff
- **Type Checking**: mypy

#### **Documentation**

- **Docstrings**: Google style for all public functions
- **Type Hints**: Required for all function parameters and returns
- **Comments**: Explain complex business logic

#### **Error Handling**

```python
# Good error handling
try:
    result = await risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=500, detail="Operation failed")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 🚨 Troubleshooting

### Common Issues

#### **1. Database Connection Issues**

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check connection
psql -h localhost -p 5432 -U user -d algotrading

# Reset database
make db-reset
```

#### **2. Redis Connection Issues**

```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
redis-cli ping

# Clear Redis cache
redis-cli flushall
```

#### **3. Test Failures**

```bash
# Run tests with verbose output
pytest -v -s

# Run specific failing test
pytest tests/test_signal_scorer.py::TestSignalScorer::test_failing_test -v

# Check test coverage
pytest --cov=app --cov-report=term-missing
```

#### **4. Import Errors**

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt

# Check virtual environment
which python
```

### Debugging Tips

#### **1. Logging**

```python
import logging
from loguru import logger

# Configure logging
logger.add("logs/app.log", rotation="1 day", retention="7 days")

# Use in code
logger.info("Signal evaluated", symbol=symbol, confidence=confidence)
logger.error("Trade execution failed", error=str(e))
```

#### **2. Debug Mode**

```bash
# Enable debug mode
export DEBUG=true

# Run with debug logging
uvicorn app.main:app --reload --log-level debug
```

#### **3. Database Debugging**

```python
# Enable SQL logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Check database queries
from app.core.database import get_db
async with get_db() as db:
    result = await db.execute("SELECT * FROM signals")
    print(result.fetchall())
```

### Performance Issues

#### **1. Slow Signal Processing**

- Check database query performance
- Verify Redis cache is working
- Monitor memory usage
- Profile signal scoring algorithms

#### **2. High Memory Usage**

- Check for memory leaks in signal queue
- Monitor database connection pool
- Verify proper cleanup of resources

#### **3. API Response Times**

- Check database query optimization
- Verify Redis caching
- Monitor external API calls
- Check for blocking operations

---

## 📚 Additional Resources

### Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Pytest Documentation](https://docs.pytest.org/)

### Trading Resources

- [Quantitative Trading](https://www.quantstart.com/)
- [Algorithmic Trading](https://www.investopedia.com/terms/a/algorithmictrading.asp)
- [Technical Analysis](https://www.investopedia.com/technical-analysis-4689657)

### Python Resources

- [Python Async/Await](https://docs.python.org/3/library/asyncio.html)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Python Testing](https://docs.python.org/3/library/unittest.html)

---

## 🎯 Next Steps

### Immediate Actions

1. **Review Codebase**: Familiarize yourself with the current implementation
2. **Run Tests**: Ensure all tests pass locally
3. **Setup Environment**: Get development environment running
4. **Read Documentation**: Review FastAPI, SQLAlchemy, and Pydantic docs

### First Task (T006)

1. **Study Asset Models**: Understand how assets are structured
2. **Implement Asset Service**: Create asset identification logic
3. **Add API Endpoints**: Create REST endpoints for asset management
4. **Write Tests**: Ensure comprehensive test coverage
5. **Integration**: Connect with signal scorer system

### Long-term Goals

1. **Complete Foundation Phase**: Finish T006-T010
2. **Implement Trading Strategies**: Build momentum and liquidity strategies
3. **Add Real Broker Integration**: Connect to Interactive Brokers and Binance
4. **Performance Optimization**: Optimize for speed and reliability
5. **Production Deployment**: Deploy to AWS with monitoring

---

**Welcome to the AlgoTrading team! This system is designed to make money through algorithmic trading. Focus on quality, testing, and performance. Happy coding! 🚀**
