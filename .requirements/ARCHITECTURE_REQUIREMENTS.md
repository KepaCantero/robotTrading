# ARCHITECTURE_REQUIREMENTS.md - AlgoTrading

**Last Updated:** 2026-03-15
**Source Files:** rules/python/05-architecture.md, 16-cosmic-python-architecture-patterns.md, 18-clean-architecture-structure.md

---

## Purpose

This document defines the **LAYERED ARCHITECTURE** rules that EVERY production file in algoTrading MUST follow. These rules ensure:
- Separation of concerns
- Dependency inversion
- Testability
- Maintainability

---

## 1. LAYERED ARCHITECTURE

### 1.1 Layer Definitions

| Layer | Directory | Responsibility | Can Import From |
|-------|-----------|----------------|-----------------|
| Domain | `app/domain/` | Business entities, value objects, domain rules | **NOTHING** (pure Python only) |
| Application | `app/services/` | Use cases, orchestration, business workflows | Domain, Core/Protocols |
| Infrastructure | `app/infrastructure/` | DB adapters, broker adapters, external APIs | Domain, Application, Core |
| Presentation | `app/api/` | REST API routes, CLI, schemas | Application only |
| Core | `app/core/` | Shared config, protocols, utilities | Nothing app-specific |

### 1.2 Dependency Rules

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| **ARCH-DEP-001** | Domain layer purity | Domain has NO dependencies on other layers | P0 |
| **ARCH-DEP-002** | Application layer dependencies | Application depends ONLY on Domain + Core/Protocols | P0 |
| **ARCH-DEP-003** | Infrastructure implements interfaces | Infrastructure implements Domain/Core Protocols | P0 |
| **ARCH-DEP-004** | Presentation uses Application | Presentation layer uses Application services only | P0 |
| **ARCH-DEP-005** | Dependency direction | All dependencies point INWARD toward Domain | P0 |

**Verification Commands:**
```bash
# Domain NO debe importar de services/infrastructure/api
grep -r "from app.services\|from app.infrastructure\|from app.api" app/domain/
# Expected: 0 matches

# Domain NO debe importar frameworks externos
grep -r "from fastapi\|from sqlalchemy\|import httpx\|from alpaca" app/domain/
# Expected: 0 matches
```

### 1.3 Anti-Patterns (PROHIBITED)

| Anti-Pattern | Rule ID | Description |
|--------------|---------|-------------|
| Domain importing infrastructure | ARCH-ANTI-001 | Domain files importing from app/infrastructure/ |
| Domain importing services | ARCH-ANTI-002 | Domain files importing from app/services/ |
| Circular imports | ARCH-ANTI-003 | Module A imports B, B imports A |
| God classes | ARCH-ANTI-004 | Classes > 300 lines |
| God functions | ARCH-ANTI-005 | Functions > 50 lines |
| Framework in domain | ARCH-ANTI-006 | FastAPI, SQLAlchemy, httpx imports in domain/ |
| Hardcoded dependencies | ARCH-ANTI-007 | Direct instantiation instead of DI |

---

## 2. FILE ORGANIZATION

### 2.1 Directory Structure

```
app/
├── core/               # Shared config, protocols, utils
│   ├── config/         # Settings, environment config
│   ├── protocols/      # Interface definitions (Protocol classes)
│   └── utils/          # Shared utilities
├── domain/             # CORE - No external deps
│   ├── entities/       # Business entities (Trade, Position, Order)
│   ├── value_objects/  # Immutable value objects (Money, Price)
│   ├── services/       # Domain services (RiskCalculator)
│   ├── strategies/     # Trading strategies (Momentum, MeanReversion)
│   └── events/         # Domain events (OrderPlaced, TradeExecuted)
├── services/           # APPLICATION - Use cases
│   ├── compliance/     # Tax compliance, regulatory
│   ├── execution/      # Order execution orchestration
│   ├── position_management/  # Position tracking
│   └── reconciliation/ # Broker vs internal reconciliation
├── infrastructure/     # INFRASTRUCTURE - Adapters
│   ├── database/       # PostgreSQL, SQLite adapters
│   ├── brokers/        # Alpaca, IBKR adapters
│   └── external_apis/  # Market data, news APIs
└── api/                # PRESENTATION - Interface
    ├── routes/         # REST API endpoints
    └── schemas/        # Pydantic request/response schemas
```

### 2.2 File Naming Conventions

| Rule ID | Rule | Pattern | Example |
|---------|------|---------|---------|
| **ARCH-NAM-001** | File names | `snake_case.py` | `trade_executor.py` |
| **ARCH-NAM-002** | Class names | `PascalCase` | `TradeExecutor` |
| **ARCH-NAM-003** | Function names | `snake_case` | `execute_trade()` |
| **ARCH-NAM-004** | Constants | `UPPER_SNAKE_CASE` | `MAX_POSITION_SIZE` |
| **ARCH-NAM-005** | Private members | `_leading_underscore` | `_internal_calc()` |
| **ARCH-NAM-006** | Protocol files | `{entity}_protocol.py` | `broker_protocol.py` |
| **ARCH-NAM-007** | Repository files | `{entity}_repository.py` | `trade_repository.py` |
| **ARCH-NAM-008** | Service files | `{entity}_service.py` | `execution_service.py` |
| **ARCH-NAM-009** | Test files | `test_{entity}.py` | `test_trade.py` |

---

## 3. MODULE RULES

### 3.1 Module Structure

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| **ARCH-MOD-001** | Package initialization | Every package has `__init__.py` | P1 |
| **ARCH-MOD-002** | Public API exports | `__init__.py` exports public API | P1 |
| **ARCH-MOD-003** | No logic in init | No business logic in `__init__.py` | P1 |
| **ARCH-MOD-004** | No circular imports | PROHIBITED circular imports between modules | P0 |
| **ARCH-MOD-005** | DI for cycles | Use dependency injection to avoid cycles | P0 |

### 3.2 Import Organization

```python
# 1. Standard library (alphabetical)
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Optional

# 2. Third-party (alphabetical)
import numpy as np
import pandas as pd

# 3. Local imports (depth order: core → domain → services → infrastructure)
from app.core.config import Settings
from app.core.protocols.broker import BrokerProtocol
from app.domain.entities.trade import Trade
from app.services.execution import ExecutionService
```

### 3.3 __init__.py Pattern

```python
# app/domain/entities/__init__.py
"""Domain entities - business objects with no external dependencies."""

from .trade import Trade
from .position import Position
from .order import Order
from .signal import Signal

__all__ = ["Trade", "Position", "Order", "Signal"]
```

---

## 4. SIZE LIMITS

| Rule ID | Type | Limit | Rationale |
|---------|------|-------|-----------|
| **ARCH-FILE-001** | File | 300 lines max | Readability, single responsibility |
| **ARCH-FILE-002** | Function | 50 lines max | Testability, comprehension |
| **ARCH-FILE-003** | Class | 300 lines max | Single responsibility |
| **ARCH-FILE-004** | Parameters | 7 max | Complexity reduction |
| **ARCH-FILE-005** | Cyclomatic complexity | 10 max | Maintainability |

**Verification:**
```bash
# Check file lengths
find app -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'

# Check complexity (requires radon)
radon cc app -a -nc
```

---

## 5. DOMAIN LAYER RULES

### 5.1 Domain Purity (ARCH-DOMAIN-001)

Domain layer MUST be pure:
- NO framework imports (FastAPI, SQLAlchemy, httpx)
- NO database imports
- NO network imports
- ONLY standard library + dataclasses + typing

```python
# ✅ CORRECT - Pure domain entity
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    """Value object for monetary amounts."""
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

# ❌ INCORRECT - Domain with external dependency
from sqlalchemy import Column, Integer  # PROHIBITED in domain!
from fastapi import HTTPException  # PROHIBITED in domain!
```

### 5.2 Value Objects (ARCH-DOMAIN-002)

Use immutable value objects for:
- `Money` (amount + currency)
- `Price` (with validation)
- `Quantity` (with unit)
- `Symbol` (with validation)

```python
@dataclass(frozen=True)
class Price:
    """Immutable price value object."""
    value: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Price cannot be negative")
```

### 5.3 Domain Events (ARCH-DOMAIN-003)

Domain events represent things that happened:
- Past tense naming: `OrderPlaced`, `TradeExecuted`
- Immutable dataclasses
- No behavior, just data

```python
@dataclass(frozen=True)
class OrderPlaced:
    """Domain event - order was placed."""
    order_id: str
    symbol: str
    quantity: int
    price: Decimal
    timestamp: datetime
```

---

## 6. APPLICATION LAYER RULES

### 6.1 Service Layer (ARCH-SVC-001)

Services orchestrate use cases:
- Depend on abstractions (Protocols)
- Inject dependencies via constructor
- NO direct infrastructure instantiation

```python
# ✅ CORRECT - Service with DI
class ExecutionService:
    """Orchestrates order execution."""

    def __init__(
        self,
        broker: BrokerProtocol,
        order_repo: OrderRepositoryProtocol,
        risk_checker: RiskCheckerProtocol,
    ):
        self._broker = broker
        self._order_repo = order_repo
        self._risk_checker = risk_checker

    def execute(self, order: Order) -> Execution:
        if not self._risk_checker.check(order):
            raise RiskLimitExceeded()
        execution = self._broker.execute_order(order)
        self._order_repo.save(order)
        return execution

# ❌ INCORRECT - Direct instantiation
class ExecutionService:
    def __init__(self):
        self._broker = AlpacaBroker("key", "secret")  # PROHIBITED!
```

### 6.2 Unit of Work (ARCH-SVC-002)

Use Unit of Work for atomic operations:

```python
class TradingUnitOfWork:
    """Manages atomic trading transactions."""

    def __enter__(self):
        self.session = self.session_factory()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.session.commit()
        else:
            self.session.rollback()
```

---

## 7. INFRASTRUCTURE LAYER RULES

### 7.1 Adapter Pattern (ARCH-INFRA-001)

Infrastructure implements Domain interfaces:
- Wraps external libraries
- Transforms external data to domain entities
- Handles external errors gracefully

```python
# app/infrastructure/brokers/alpaca_adapter.py
class AlpacaBrokerAdapter(BrokerProtocol):
    """Adapter for Alpaca API."""

    def __init__(self, api_key: str, api_secret: str):
        self._client = AlpacaClient(api_key, api_secret)

    def execute_order(self, order: Order) -> Execution:
        try:
            response = self._client.submit_order(
                symbol=order.symbol,
                qty=order.quantity,
                side=order.side,
            )
            return Execution.from_response(response)
        except AlpacaAPIError as e:
            raise BrokerError(f"Alpaca error: {e}") from e
```

### 7.2 Repository Pattern (ARCH-INFRA-002)

Repositories abstract data access:

```python
# app/core/protocols/trade_repository.py
class TradeRepositoryProtocol(Protocol):
    """Interface for trade persistence."""

    def save(self, trade: Trade) -> None: ...
    def find_by_id(self, trade_id: str) -> Trade | None: ...
    def find_by_symbol(self, symbol: str) -> list[Trade]: ...

# app/infrastructure/database/postgres_trade_repository.py
class PostgresTradeRepository(TradeRepositoryProtocol):
    """PostgreSQL implementation."""

    def __init__(self, session: Session):
        self._session = session

    def save(self, trade: Trade) -> None:
        entity = TradeEntity.from_domain(trade)
        self._session.add(entity)
```

---

## 8. PRESENTATION LAYER RULES

### 8.1 Thin Controllers (ARCH-API-001)

API routes should be thin:
- Delegate to services
- Handle HTTP concerns only
- Use Pydantic schemas for validation

```python
# ✅ CORRECT - Thin controller
@router.post("/orders")
async def create_order(
    request: CreateOrderRequest,
    service: ExecutionService = Depends(get_execution_service),
) -> OrderResponse:
    order = Order.from_request(request)
    execution = service.execute(order)
    return OrderResponse.from_execution(execution)

# ❌ INCORRECT - Fat controller
@router.post("/orders")
async def create_order(request: CreateOrderRequest):
    # NO business logic in controllers!
    if request.quantity <= 0:
        raise HTTPException(400, "Invalid quantity")
    broker = AlpacaBroker(...)  # PROHIBITED!
    broker.execute(...)
```

### 8.2 Schema Separation (ARCH-API-002)

Use separate schemas for:
- Request (input validation)
- Response (output serialization)
- NEVER expose domain entities directly

---

## 9. TESTING STRUCTURE

```
tests/
├── unit/               # No I/O, pure logic
│   ├── domain/         # Domain entity tests
│   └── services/       # Service tests with mocks
├── integration/        # With DB/API mocks
│   ├── database/       # Repository tests
│   └── brokers/        # Broker adapter tests
└── e2e/               # Full system tests
```

| Rule ID | Rule | Requirement |
|---------|------|------------|
| ARCH-TEST-001 | Unit tests | Domain has unit tests without mocks |
| ARCH-TEST-002 | Integration tests | Infrastructure has integration tests with mocks |
| ARCH-TEST-003 | Test isolation | Tests don't depend on external services |

---

## 10. CONFIGURATION

| Rule ID | Rule | Requirement | Priority |
|---------|------|------------|----------|
| **ARCH-CFG-001** | No secrets in code | NO hardcoded API keys, passwords | P0 |
| **ARCH-CFG-002** | Environment variables | Secrets from environment variables | P0 |
| **ARCH-CFG-003** | Config validation | Validate config at startup | P1 |
| **ARCH-CFG-004** | Single source of truth | Use pydantic-settings | P1 |

```python
# app/core/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings from environment."""

    database_url: str
    alpaca_api_key: str
    alpaca_api_secret: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

# Usage
settings = Settings()  # Validates at startup
```

---

## 11. ARCHITECTURE CHECKLIST

Before any code review, verify:

### Layer Purity
- [ ] Domain has NO external imports (FastAPI, SQLAlchemy, httpx)
- [ ] Domain has NO imports from app/services, app/infrastructure, app/api
- [ ] Services use Protocol interfaces, not concrete implementations

### Dependency Direction
- [ ] All dependencies point toward Domain
- [ ] Infrastructure implements Domain/Core Protocols
- [ ] No circular imports

### Size Limits
- [ ] Files < 300 lines
- [ ] Functions < 50 lines
- [ ] Classes < 300 lines
- [ ] Complexity < 10

### Naming
- [ ] Files use snake_case.py
- [ ] Classes use PascalCase
- [ ] Functions use snake_case
- [ ] Constants use UPPER_SNAKE_CASE

### Configuration
- [ ] No hardcoded secrets
- [ ] Config from environment variables
- [ ] Config validated at startup

---

## CROSS-REFERENCES

- See `.requirements/FILE_SYSTEM_REQUIREMENTS.md` for file naming and directory rules
- See `.requirements/BASE_RULES.md` for code quality rules
- See `.requirements/CRITICAL_RULES.md` for security rules
- See `rules/python/16-cosmic-python-architecture-patterns.md` for DDD patterns
- See `rules/python/18-clean-architecture-structure.md` for Clean Architecture rules
