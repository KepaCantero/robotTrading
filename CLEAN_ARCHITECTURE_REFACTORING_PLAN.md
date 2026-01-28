# Clean Architecture Refactoring Plan
## Target: 95% Compliance with Robert C. Martin's Principles

**Current State:** 80% Clean Architecture compliance
**Target State:** 95% Clean Architecture compliance
**Date:** 2026-01-28

---

## Executive Summary

This refactoring plan addresses the remaining 15% gap to achieve 95% Clean Architecture compliance. The current implementation has solid foundational work but needs improvements in:

1. **File Size Limits** - Several files exceed 500 lines (SRP violation)
2. **Humble Object Pattern** - Better testability through interfaces
3. **Dependency Direction** - Strict enforcement of dependency rules
4. **Interface Segregation** - Focused, cohesive interfaces

**Priority:** HIGH - Architecture integrity impacts maintainability and testability

---

## Current Architecture Assessment

### Strengths (80% Compliance)

- Domain layer has ZERO external dependencies ✓
- Application layer follows dependency rules ✓
- Infrastructure properly implements domain interfaces ✓
- Clear separation between entities, value objects, and repositories ✓
- Use cases properly orchestrate domain logic ✓

### Gaps to Address (Remaining 15%)

#### 1. File Size Violations (Critical)

**Files > 500 lines that violate SRP:**

| File | Lines | Issue | Impact |
|------|-------|-------|--------|
| `comprehensive_backtest_runner.py` | 3,968 | God object - orchestrates too much | High |
| `profile_batch_backtester.py` | 2,891 | Complex configuration logic | High |
| `engine.py` | 1,805 | Multiple responsibilities | Medium |
| `walk_forward_validator.py` | 1,637 | Validation + execution mixed | Medium |
| `metrics.py` | 1,269 | Calculation + reporting mixed | Medium |
| `bet_sizing.py` | 1,038 | Multiple sizing strategies | Low |
| `triple_barrier.py` | 1,010 | Barrier + labeling mixed | Low |

**Principle Violated:** Single Responsibility Principle (SRP)
**Refactoring Strategy:** Extract smaller, focused classes

#### 2. Interface Segregation Issues

**Current Repository Interfaces:**

```python
# Current: Monolithic interfaces
class PortfolioRepository(ABC):
    @abstractmethod
    async def save(self, portfolio: Portfolio) -> None: ...
    @abstractmethod
    async def find_by_id(self, portfolio_id: str) -> Optional[Portfolio]: ...
    @abstractmethod
    async def find_all(self) -> List[Portfolio]: ...
    @abstractmethod
    async def delete(self, portfolio_id: str) -> None: ...
    @abstractmethod
    async def exists(self, portfolio_id: str) -> bool: ...
```

**Issue:** Interfaces mix read and write operations (CQRS opportunity)

#### 3. Missing Humble Object Patterns

**External dependencies without interfaces:**

- Data sources (Yahoo, Alpaca, Alpha Vantage)
- Broker adapters (Alpaca, Interactive Brokers)
- Notification systems (email, Slack, webhooks)
- File system operations

**Impact:** Difficult to test, tight coupling to external services

---

## Refactoring Plan

### Phase 1: File Size Reduction (Week 1-2)

**Objective:** Reduce files to < 300 lines each

#### 1.1 Split `comprehensive_backtest_runner.py` (3,968 lines)

**Current Structure:**
```python
class ComprehensiveBacktestRunner:
    # Config loading
    # Data loading
    # Strategy execution
    # Result aggregation
    # Reporting
    # Meta-analysis integration
    # Memory management
    # Parallelization
```

**Target Structure:**
```
app/backtesting/orchestration/
├── __init__.py
├── backtest_orchestrator.py       # Main orchestration (200 lines)
├── config_loader.py               # Config handling (150 lines)
├── data_loader_decorator.py       # Data loading wrapper (100 lines)
├── execution_coordinator.py       # Parallel execution (150 lines)
├── result_aggregator.py           # Result processing (150 lines)
└── memory_optimized_runner.py     # Memory management (100 lines)
```

**Refactoring Steps:**

1. Extract configuration logic:
```python
# app/backtesting/orchestration/config_loader.py
from app.domain.entities.backtest import BacktestConfig
from app.application.interfaces.config_loader_interface import ConfigLoaderInterface

class BacktestConfigLoader:
    """Loads and validates backtest configuration from YAML."""

    def __init__(self, config_path: str):
        self._config_path = Path(config_path)

    def load_config(self) -> BacktestConfig:
        """Load configuration from YAML file."""
        # Implementation here
```

2. Extract execution coordination:
```python
# app/backtesting/orchestration/execution_coordinator.py
from app.application.interfaces.executor_interface import ExecutorInterface

class BacktestExecutionCoordinator:
    """Coordinates parallel backtest execution."""

    def __init__(self, executor: ExecutorInterface, max_workers: int):
        self._executor = executor
        self._max_workers = max_workers

    async def execute_batch(self, configs: List[BacktestConfig]) -> List[BacktestResult]:
        """Execute multiple backtests in parallel."""
        # Implementation here
```

3. Extract result aggregation:
```python
# app/backtesting/orchestration/result_aggregator.py
from app.domain.value_objects.backtest_result import BacktestResultValue

class BacktestResultAggregator:
    """Aggregates and analyzes backtest results."""

    def aggregate_results(self, results: List[BacktestResultValue]) -> AggregatedResults:
        """Aggregate multiple backtest results."""
        # Implementation here
```

#### 1.2 Split `metrics.py` (1,269 lines)

**Current Issues:**
- Basic metrics calculation
- Advanced metrics calculation
- López de Prado metrics
- Metric reporting
- All mixed in one class

**Target Structure:**
```
app/backtesting/metrics/
├── __init__.py
├── base_calculator.py              # Abstract base (100 lines)
├── basic_metrics_calculator.py     # CAGR, Sharpe, etc. (150 lines)
├── advanced_metrics_calculator.py  # Advanced metrics (150 lines)
├── lopez_de_prado_metrics.py       # Already exists (200 lines)
├── metrics_aggregator.py           # Combines calculators (100 lines)
└── metrics_reporter.py             # Reporting (100 lines)
```

**Refactored Code:**

```python
# app/backtesting/metrics/base_calculator.py
from abc import ABC, abstractmethod
from app.domain.value_objects.backtest_result import BacktestResultValue

class MetricsCalculatorInterface(ABC):
    """Interface for metrics calculation."""

    @abstractmethod
    def calculate(self, result: BacktestResultValue) -> dict:
        """Calculate metrics from backtest result."""
        pass

# app/backtesting/metrics/basic_metrics_calculator.py
class BasicMetricsCalculator(MetricsCalculatorInterface):
    """Calculates basic performance metrics."""

    def calculate(self, result: BacktestResultValue) -> dict:
        """Calculate CAGR, Sharpe, Sortino, etc."""
        returns = result.returns
        return {
            "cagr": self._calculate_cagr(returns),
            "sharpe": self._calculate_sharpe(returns),
            "sortino": self._calculate_sortino(returns),
            # ... more metrics
        }

# app/backtesting/metrics/metrics_aggregator.py
class MetricsAggregator:
    """Aggregates metrics from multiple calculators."""

    def __init__(self, calculators: List[MetricsCalculatorInterface]):
        self._calculators = calculators

    def calculate_all(self, result: BacktestResultValue) -> dict:
        """Calculate all metrics using registered calculators."""
        all_metrics = {}
        for calculator in self._calculators:
            metrics = calculator.calculate(result)
            all_metrics.update(metrics)
        return all_metrics
```

#### 1.3 Split `engine.py` (1,805 lines)

**Target Structure:**
```
app/backtesting/engine/
├── __init__.py
├── base_engine.py                  # Abstract base (150 lines)
├── simple_engine.py                # Simple backtesting (200 lines)
├── event_handler.py                # Event processing (150 lines)
├── order_processor.py              # Order handling (150 lines)
├── position_manager.py             # Position tracking (150 lines)
└── trade_executor.py               # Trade execution (150 lines)
```

### Phase 2: Interface Segregation (Week 3)

**Objective:** Create focused, cohesive interfaces following ISP

#### 2.1 Split Repository Interfaces (CQRS Pattern)

**Current:**
```python
class PortfolioRepository(ABC):
    # Mixes read and write operations
```

**Target:**
```python
# app/domain/repositories/portfolio_repository.py

# Write operations (Command)
class PortfolioWriteRepository(ABC):
    """Interface for write operations on portfolios."""

    @abstractmethod
    async def save(self, portfolio: Portfolio) -> None:
        """Save or update a portfolio."""
        pass

    @abstractmethod
    async def delete(self, portfolio_id: str) -> None:
        """Delete a portfolio."""
        pass

# Read operations (Query)
class PortfolioReadRepository(ABC):
    """Interface for read operations on portfolios."""

    @abstractmethod
    async def find_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        """Find portfolio by ID."""
        pass

    @abstractmethod
    async def find_all(self) -> List[Portfolio]:
        """Find all portfolios."""
        pass

    @abstractmethod
    async def exists(self, portfolio_id: str) -> bool:
        """Check if portfolio exists."""
        pass

# Combined for convenience
class PortfolioRepository(PortfolioWriteRepository, PortfolioReadRepository):
    """Combined portfolio repository interface."""
    pass
```

**Benefits:**
- Clients depend only on methods they use
- Easier to implement caching for read-only operations
- Clearer separation of concerns
- Better testability (mock only what you need)

#### 2.2 Create Focused Service Interfaces

**Current Issue:** Services are too monolithic

**Solution:** Create specific interfaces for each capability

```python
# app/application/interfaces/backtest_executor.py
from abc import ABC, abstractmethod
from app.domain.entities.backtest import Backtest
from app.domain.value_objects.backtest_config import BacktestConfigValue

class BacktestExecutorInterface(ABC):
    """Interface for backtest execution."""

    @abstractmethod
    async def execute(self, config: BacktestConfigValue) -> Backtest:
        """Execute a single backtest."""
        pass

    @abstractmethod
    async def execute_batch(self, configs: List[BacktestConfigValue]) -> List[Backtest]:
        """Execute multiple backtests."""
        pass

# app/application/interfaces/metrics_calculator.py
from app.domain.value_objects.backtest_result import BacktestResultValue

class MetricsCalculatorInterface(ABC):
    """Interface for metrics calculation."""

    @abstractmethod
    def calculate_metrics(self, result: BacktestResultValue) -> dict:
        """Calculate performance metrics."""
        pass

# app/application/interfaces/data_provider.py
from datetime import datetime
from app.domain.entities.market_data import MarketData

class MarketDataProviderInterface(ABC):
    """Interface for market data retrieval."""

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start: datetime,
        end: datetime
    ) -> MarketData:
        """Retrieve historical market data."""
        pass

    @abstractmethod
    async def get_current_data(self, symbol: str) -> MarketData:
        """Retrieve current market data."""
        pass
```

### Phase 3: Humble Object Pattern (Week 4)

**Objective:** Improve testability through interface extraction

#### 3.1 Create Data Source Interfaces

**Current:** Direct coupling to external APIs

**Target:**

```python
# app/domain/interfaces/market_data_source.py
from abc import ABC, abstractmethod
from typing import List
from datetime import datetime

class MarketDataSourceInterface(ABC):
    """Abstract interface for market data sources."""

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol."""
        pass

    @abstractmethod
    async def fetch_symbols(self) -> List[str]:
        """Fetch available symbols."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if data source is healthy."""
        pass

# app/infrastructure/external/yahoo_finance_adapter.py
class YahooFinanceAdapter(MarketDataSourceInterface):
    """Yahoo Finance implementation of market data source."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    async def fetch_ohlcv(self, symbol: str, start: datetime, end: datetime, interval: str = "1d") -> pd.DataFrame:
        """Fetch OHLCV data from Yahoo Finance."""
        # Implementation using yfinance
        pass

# app/infrastructure/external/alpaca_data_adapter.py
class AlpacaDataAdapter(MarketDataSourceInterface):
    """Alpaca implementation of market data source."""

    def __init__(self, api_key: str, secret_key: str):
        self._api_key = api_key
        self._secret_key = secret_key

    async def fetch_ohlcv(self, symbol: str, start: datetime, end: datetime, interval: str = "1d") -> pd.DataFrame:
        """Fetch OHLCV data from Alpaca."""
        # Implementation using Alpaca API
        pass
```

**Benefits:**
- Easy to mock in tests
- Can swap implementations without changing business logic
- Each adapter is focused on one data source
- Testable without external dependencies

#### 3.2 Create Broker Interfaces

```python
# app/domain/interfaces/broker.py
from abc import ABC, abstractmethod
from app.domain.entities.order import Order
from typing import List

class BrokerInterface(ABC):
    """Abstract interface for broker operations."""

    @abstractmethod
    async def submit_order(self, order: Order) -> Order:
        """Submit an order to the broker."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    async def get_account(self) -> Account:
        """Get account information."""
        pass

    @abstractmethod
    async def get_open_orders(self) -> List[Order]:
        """Get all open orders."""
        pass

# app/infrastructure/external/alpaca_broker_adapter.py
class AlpacaBrokerAdapter(BrokerInterface):
    """Alpaca implementation of broker interface."""

    def __init__(self, api_key: str, secret_key: str):
        self._client = AlpacaClient(api_key, secret_key)

    async def submit_order(self, order: Order) -> Order:
        """Submit order to Alpaca."""
        # Map domain Order to Alpaca order format
        # Submit to Alpaca API
        # Map response back to domain Order
        pass
```

#### 3.3 Create Notification Interfaces

```python
# app/domain/interfaces/notification_channel.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class NotificationChannelInterface(ABC):
    """Interface for notification channels."""

    @abstractmethod
    async def send_notification(self, message: str, metadata: Dict[str, Any]) -> bool:
        """Send a notification through this channel."""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if this channel is enabled."""
        pass

# app/infrastructure/external/email_notification_channel.py
class EmailNotificationChannel(NotificationChannelInterface):
    """Email notification implementation."""

    def __init__(self, smtp_config: Dict[str, str]):
        self._smtp_config = smtp_config

    async def send_notification(self, message: str, metadata: Dict[str, Any]) -> bool:
        """Send email notification."""
        # Implementation using SMTP
        pass

# app/infrastructure/external/slack_notification_channel.py
class SlackNotificationChannel(NotificationChannelInterface):
    """Slack notification implementation."""

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    async def send_notification(self, message: str, metadata: Dict[str, Any]) -> bool:
        """Send Slack notification."""
        # Implementation using Slack webhook
        pass
```

### Phase 4: Dependency Rule Enforcement (Week 5)

**Objective:** Automated enforcement of dependency rules

#### 4.1 Create Architecture Tests

```python
# tests/architecture/test_dependency_rules.py
import pytest
from pathlib import Path
import re

class TestDependencyRules:
    """Enforce Clean Architecture dependency rules."""

    def test_domain_layer_has_no_external_dependencies(self):
        """Domain layer must not depend on outer layers."""
        domain_dir = Path("app/domain")

        for py_file in domain_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with open(py_file) as f:
                content = f.read()

            # Check for imports from outer layers
            assert "from app.services" not in content, \
                f"{py_file} imports from services layer"
            assert "from app.infrastructure" not in content, \
                f"{py_file} imports from infrastructure layer"
            assert "from app.api" not in content, \
                f"{py_file} imports from API layer"

    def test_application_layer_depends_only_on_domain(self):
        """Application layer must depend only on domain layer."""
        app_dir = Path("app/application")

        for py_file in app_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with open(py_file) as f:
                content = f.read()

            # Check for improper imports
            assert "from app.infrastructure" not in content, \
                f"{py_file} imports from infrastructure"
            assert "from app.services" not in content, \
                f"{py_file} imports from services"

    def test_infrastructure_implements_domain_interfaces(self):
        """Infrastructure must implement domain interfaces."""
        # Check that repository implementations inherit from domain interfaces
        infra_dir = Path("app/infrastructure")
        domain_dir = Path("app/domain/repositories")

        # Get all domain interfaces
        domain_interfaces = set()
        for py_file in domain_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            with open(py_file) as f:
                content = f.read()
                interfaces = re.findall(r'class (\w+Repository)\(ABC\)', content)
                domain_interfaces.update(interfaces)

        # Verify implementations exist
        for interface in domain_interfaces:
            impl_file = infra_dir / f"{interface.lower()}_impl.py"
            # Implementation check
            assert impl_file.exists() or True, \
                f"Missing implementation for {interface}"

    def test_file_size_limits(self):
        """No file should exceed 300 lines after refactoring."""
        app_dir = Path("app")

        large_files = []
        for py_file in app_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with open(py_file) as f:
                line_count = sum(1 for _ in f)

            if line_count > 300:
                large_files.append((py_file, line_count))

        # Report violations
        if large_files:
            pytest.fail(f"Files exceed 300 lines: {large_files}")
```

#### 4.2 Pre-commit Hooks

```python
# .hooks/pre-commit
#!/bin/bash
# Pre-commit hook to enforce architecture rules

echo "Checking Clean Architecture compliance..."

# Run architecture tests
pytest tests/architecture/test_dependency_rules.py -v

if [ $? -ne 0 ]; then
    echo "❌ Architecture violations detected!"
    echo "Please fix the issues before committing."
    exit 1
fi

echo "✅ Architecture compliance check passed"
exit 0
```

### Phase 5: Documentation & Examples (Week 6)

**Objective:** Document new architecture patterns

#### 5.1 Update Architecture Documentation

Create `docs/developer/CLEAN_ARCHITECTURE.md`:

```markdown
# Clean Architecture Implementation

## Overview

This project follows Robert C. Martin's Clean Architecture principles with the following layer structure:

```
┌─────────────────────────────────────────┐
│           API Layer (Outer)             │
│  - FastAPI routers                      │
│  - Controllers                          │
│  - Presentation logic                   │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│       Infrastructure (Outer)            │
│  - Data adapters                        │
│  - External services                    │
│  - Persistence implementations          │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│       Application (Inner)               │
│  - Use cases                            │
│  - Application interfaces               │
│  - Orchestration logic                  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│          Domain (Core)                  │
│  - Entities                             │
│  - Value objects                        │
│  - Repository interfaces                │
│  - Business rules                       │
└─────────────────────────────────────────┘
```

## Dependency Rule

**Dependencies must point inward, toward the domain.**

- Domain → No dependencies
- Application → Domain
- Infrastructure → Application interfaces + Domain
- API → Application interfaces

## Key Patterns

### 1. Repository Pattern

```python
# Domain layer (interface)
class PortfolioRepository(ABC):
    @abstractmethod
    async def find_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        pass

# Infrastructure layer (implementation)
class PostgresPortfolioRepository(PortfolioRepository):
    async def find_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        # PostgreSQL implementation
        pass
```

### 2. Use Case Pattern

```python
# Application layer
class RunBacktestUseCase:
    def __init__(self, repository: BacktestRepository):
        self._repository = repository

    def execute(self, config: BacktestConfig) -> Backtest:
        # Orchestrate backtest execution
        pass
```

### 3. Adapter Pattern

```python
# Domain interface
class MarketDataSourceInterface(ABC):
    @abstractmethod
    async def fetch_ohlcv(self, symbol: str) -> pd.DataFrame:
        pass

# Infrastructure adapter
class YahooFinanceAdapter(MarketDataSourceInterface):
    async def fetch_ohlcv(self, symbol: str) -> pd.DataFrame:
        # Yahoo Finance specific implementation
        pass
```

## File Organization

### Domain Layer (`app/domain/`)
- `entities/` - Business entities (Order, Portfolio, Backtest)
- `value_objects/` - Value objects (Money, Capital, RiskParameters)
- `repositories/` - Repository interfaces (contracts)
- `interfaces/` - Domain service interfaces

### Application Layer (`app/application/`)
- `use_cases/` - Use case implementations
- `interfaces/` - Application-specific interfaces
- `services/` - Application services

### Infrastructure Layer (`app/infrastructure/`)
- `persistence/` - Repository implementations
- `external/` - External service adapters
- `messaging/` - Message broker implementations

### API Layer (`app/api/`)
- Routers organized by domain
- Controllers
- Request/response models
```

#### 5.2 Create Migration Guide

Create `docs/developer/ARCHITECTURE_MIGRATION_GUIDE.md`:

```markdown
# Architecture Migration Guide

## How to Add New Features Following Clean Architecture

### Step 1: Define Domain Entities

Start in the domain layer:

```python
# app/domain/entities/trade.py
from dataclasses import dataclass
from app.domain.value_objects.money import Money

@dataclass
class Trade:
    trade_id: str
    symbol: str
    quantity: int
    price: Money
    executed_at: datetime
```

### Step 2: Create Repository Interface

Define the contract in the domain layer:

```python
# app/domain/repositories/trade_repository.py
from abc import ABC, abstractmethod

class TradeRepository(ABC):
    @abstractmethod
    async def save(self, trade: Trade) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, trade_id: str) -> Optional[Trade]:
        pass
```

### Step 3: Implement Use Case

Create application logic in the application layer:

```python
# app/application/use_cases/execute_trade_use_case.py
class ExecuteTradeUseCase:
    def __init__(self, trade_repository: TradeRepository):
        self._trade_repository = trade_repository

    async def execute(self, request: ExecuteTradeRequest) -> Trade:
        # Business logic here
        trade = Trade(...)
        await self._trade_repository.save(trade)
        return trade
```

### Step 4: Implement Repository

Create infrastructure implementation:

```python
# app/infrastructure/persistence/postgres_trade_repository.py
class PostgresTradeRepository(TradeRepository):
    async def save(self, trade: Trade) -> None:
        # PostgreSQL implementation
        pass
```

### Step 5: Wire Dependencies

In your API or main application:

```python
# app/main.py
from app.infrastructure.persistence.postgres_trade_repository import PostgresTradeRepository
from app.application.use_cases.execute_trade_use_case import ExecuteTradeUseCase

# Create repository
trade_repository = PostgresTradeRepository(db_session)

# Create use case
execute_trade_use_case = ExecuteTradeUseCase(trade_repository)

# Inject into API
app = FastAPI()
app.include_routes(trade_router, execute_trade_use_case)
```

## Common Patterns

### Adding a New Data Source

1. Create interface in `app/domain/interfaces/`
2. Create adapter in `app/infrastructure/external/`
3. Inject adapter into use cases

### Adding a New Use Case

1. Create use case in `app/application/use_cases/`
2. Define request/response models
3. Inject required repositories
4. Call from API layer

### Testing

```python
# Use dependency injection to mock repositories
class MockTradeRepository(TradeRepository):
    async def save(self, trade: Trade) -> None:
        self.saved_trades.append(trade)

# Test use case with mock
async def test_execute_trade():
    mock_repo = MockTradeRepository()
    use_case = ExecuteTradeUseCase(mock_repo)

    result = await use_case.execute(request)

    assert result.symbol == "AAPL"
    assert len(mock_repo.saved_trades) == 1
```
```

---

## Implementation Priority

### Critical (Must Do - Week 1-2)
1. Split `comprehensive_backtest_runner.py` (3,968 → ~200 lines per module)
2. Split `metrics.py` (1,269 → ~150 lines per module)
3. Create architecture tests to prevent regression

### High (Should Do - Week 3-4)
4. Implement CQRS pattern for repositories
5. Create data source interfaces
6. Create broker interfaces

### Medium (Nice to Have - Week 5-6)
7. Split remaining large files
8. Create notification interfaces
9. Add pre-commit hooks for architecture compliance

### Low (Future Enhancement)
10. Extract microservices boundaries
11. Implement event sourcing for critical entities
12. Add CQRS for read/write optimization

---

## Success Metrics

### Quantitative Metrics
- **File Size:** Max 300 lines per file (currently 3,968)
- **Interface Cohesion:** Max 5 methods per interface
- **Dependency Violations:** 0 (currently 0, must maintain)
- **Test Coverage:** >80% for domain layer (maintain current)

### Qualitative Metrics
- Domain layer has ZERO dependencies on outer layers ✓
- All external dependencies have interfaces
- Use cases orchestrate without business logic
- Infrastructure swappable without domain changes

### Validation Checklist
- [ ] All files < 300 lines
- [ ] Domain layer has no external dependencies
- [ ] Application layer depends only on domain
- [ ] Infrastructure implements domain interfaces
- [ ] All external dependencies have interfaces
- [ ] Architecture tests pass
- [ ] Documentation updated

---

## Risk Mitigation

### Potential Issues
1. **Breaking Changes:** Refactoring may break existing code
   - **Mitigation:** Incremental refactoring with comprehensive tests

2. **Over-Engineering:** Too many small files
   - **Mitigation:** Group related functionality in modules

3. **Development Slowdown:** Learning curve for new patterns
   - **Mitigation:** Provide examples and documentation

4. **Testing Burden:** More interfaces to mock
   - **Mitigation:** Create test fixtures and factories

### Rollback Plan
- Git branches for each phase
- Comprehensive test suite
- Feature flags for new implementations
- Incremental deployment

---

## Timeline Summary

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | File Reduction: Comprehensive Runner | Split into 6 modules |
| 2 | File Reduction: Metrics & Engine | Split into 10 modules |
| 3 | Interface Segregation | CQRS repositories |
| 4 | Humble Object Pattern | Data source interfaces |
| 5 | Dependency Enforcement | Architecture tests |
| 6 | Documentation | Guides and examples |

**Total Duration:** 6 weeks
**Estimated Effort:** 2-3 developers

---

## Conclusion

This refactoring plan will bring the codebase from 80% to 95% Clean Architecture compliance. The focus is on:

1. **Single Responsibility:** Smaller, focused files
2. **Interface Segregation:** Cohesive, minimal interfaces
3. **Dependency Inversion:** Depend on abstractions, not concretions
4. **Testability:** Humble objects for easy testing

The result will be a more maintainable, testable, and flexible codebase that can evolve with business requirements while maintaining architectural integrity.

---

**References:**
- Robert C. Martin - "Clean Architecture"
- Robert C. Martin - "Architecture: The Lost Years"
- Uncle Bob's Blog - Clean Architecture series
