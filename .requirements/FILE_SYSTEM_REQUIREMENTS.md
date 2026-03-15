# FILE_SYSTEM_REQUIREMENTS.md - AlgoTrading

**Last Updated:** 2026-03-15
**Source Files:** rules/python/05-architecture.md, 18-clean-architecture-structure.md

---

## Purpose

This document defines the **FILE SYSTEM** organization rules that EVERY file in algoTrading MUST follow. These rules ensure:
- Consistent project structure
- Predictable file locations
- Clean module organization
- Easy navigation and discovery

---

## 1. DIRECTORY ORGANIZATION

### 1.1 By Architectural Layer

| Directory | Contains | Examples |
|-----------|----------|----------|
| `app/domain/` | Entities, value objects, domain services | `Trade`, `Position`, `Signal` |
| `app/services/` | Use cases, orchestration services | `ExecutionService`, `ComplianceService` |
| `app/infrastructure/` | Adapters for DB, brokers, APIs | `AlpacaBroker`, `PostgresRepository` |
| `app/api/` | REST routes, schemas, middleware | `/api/trade`, `TradeSchema` |
| `app/core/` | Shared config, protocols, utilities | `Settings`, `BrokerProtocol` |

### 1.2 Domain Subdirectories

```
app/domain/
├── entities/           # Business entities with identity
│   ├── trade.py
│   ├── position.py
│   ├── order.py
│   └── signal.py
├── value_objects/      # Immutable objects without identity
│   ├── money.py
│   ├── price.py
│   └── quantity.py
├── services/           # Domain services (cross-entity logic)
│   ├── risk_calculator.py
│   └── position_sizer.py
├── strategies/         # Trading strategies
│   ├── momentum.py
│   ├── mean_reversion.py
│   └── trend_following.py
└── events/             # Domain events
    ├── order_placed.py
    └── trade_executed.py
```

### 1.3 Services Subdirectories

```
app/services/
├── compliance/         # Tax compliance, regulatory
│   ├── engine.py
│   ├── irpf_calculator.py
│   └── modelo_720_generator.py
├── execution/          # Order execution
│   ├── engine.py
│   └── order_validator.py
├── position_management/  # Position tracking
│   ├── manager.py
│   └── pnl_calculator.py
└── reconciliation/     # Broker vs internal
    └── reconciler.py
```

### 1.4 Infrastructure Subdirectories

```
app/infrastructure/
├── database/           # Database adapters
│   ├── postgres/
│   ├── sqlite/
│   └── questdb/
├── brokers/            # Broker adapters
│   ├── alpaca_adapter.py
│   └── ibkr_adapter.py
├── external_apis/      # External API clients
│   ├── market_data.py
│   └── news_feed.py
└── cache/              # Cache implementations
    └── redis_cache.py
```

### 1.5 API Subdirectories

```
app/api/
├── routes/             # REST API endpoints
│   ├── trading.py
│   ├── positions.py
│   └── health.py
├── schemas/            # Pydantic schemas
│   ├── trade_schema.py
│   └── position_schema.py
└── middleware/         # API middleware
    ├── auth.py
    └── rate_limit.py
```

### 1.6 Core Subdirectories

```
app/core/
├── config/             # Configuration
│   ├── settings.py
│   └── logging_config.py
├── protocols/          # Interface definitions
│   ├── broker_protocol.py
│   ├── repository_protocol.py
│   └── cache_protocol.py
└── utils/              # Shared utilities
    ├── datetime_utils.py
    └── math_utils.py
```

---

## 2. FILE NAMING PATTERNS

### 2.1 File Naming Rules

| Rule ID | Rule | Pattern | Example |
|---------|------|---------|---------|
| **FS-NAM-001** | File name | `snake_case.py` | `trade_executor.py` |
| **FS-NAM-002** | Test file | `test_{module}.py` | `test_trade_executor.py` |
| **FS-NAM-003** | Protocol file | `{entity}_protocol.py` | `broker_protocol.py` |
| **FS-NAM-004** | Repository file | `{entity}_repository.py` | `trade_repository.py` |
| **FS-NAM-005** | Service file | `{entity}_service.py` | `execution_service.py` |
| **FS-NAM-006** | Schema file | `{entity}_schema.py` | `trade_schema.py` |
| **FS-NAM-007** | Adapter file | `{provider}_{type}_adapter.py` | `alpaca_broker_adapter.py` |

### 2.2 File Naming by Type

| Type | Pattern | Example |
|------|---------|---------|
| Entity | `{entity}.py` | `trade.py` |
| Value Object | `{value_object}.py` | `money.py` |
| Service | `{domain}_service.py` | `execution_service.py` |
| Repository | `{entity}_repository.py` | `trade_repository.py` |
| Protocol | `{entity}_protocol.py` | `broker_protocol.py` |
| Adapter | `{provider}_{type}_adapter.py` | `alpaca_broker_adapter.py` |
| Schema | `{entity}_schema.py` | `trade_schema.py` |
| Route | `{resource}_routes.py` | `trading_routes.py` |
| Test | `test_{module}.py` | `test_trade.py` |
| Config | `{purpose}_config.py` | `logging_config.py` |
| Utils | `{domain}_utils.py` | `datetime_utils.py` |

---

## 3. SPECIAL FILES

### 3.1 `__init__.py` Requirements

| Rule ID | Rule | Requirement |
|---------|------|------------|
| **FS-INIT-001** | Every package has `__init__.py` | Required for all Python packages |
| **FS-INIT-002** | Exports public API | Use `__all__` for explicit exports |
| **FS-INIT-003** | No business logic | `__init__.py` should only import and export |
| **FS-INIT-004** | Avoid star imports | Use explicit imports, not `from .module import *` |

```python
# ✅ CORRECT - __init__.py with explicit exports
# app/domain/entities/__init__.py
"""Domain entities - business objects."""

from .trade import Trade
from .position import Position
from .order import Order
from .signal import Signal

__all__ = ["Trade", "Position", "Order", "Signal"]

# ❌ INCORRECT - Business logic in __init__.py
# app/domain/entities/__init__.py
def create_trade(symbol: str, quantity: int):  # PROHIBITED!
    return Trade(symbol, quantity)
```

### 3.2 `protocol.py` Pattern

Each module that defines interfaces should have a `protocols/` subdirectory:

```python
# app/core/protocols/broker_protocol.py
"""Interface for broker adapters."""
from typing import Protocol

class BrokerProtocol(Protocol):
    """Protocol for broker implementations."""

    def execute_order(self, order: "Order") -> "Execution":
        """Execute an order."""
        ...

    def get_positions(self) -> list["Position"]:
        """Get current positions."""
        ...

    def get_account_balance(self) -> "Money":
        """Get account balance."""
        ...
```

### 3.3 `py.typed` for Type Hints

```
app/
├── py.typed           # Marker file for PEP 561
└── ...
```

---

## 4. AUXILIARY DIRECTORIES

### 4.1 Project Root Directories

```
algoTrading/
├── app/               # Main application code
├── tests/             # Test files
├── config/            # Configuration files (YAML, etc.)
├── scripts/           # Utility scripts
├── docs/              # Documentation
├── logs/              # Log files (gitignored)
├── data/              # Data files (gitignored)
├── backups/           # Backup files (gitignored)
├── .cache/            # Cache files (gitignored)
├── .tmp/              # Temporary files (gitignored)
├── .requirements/     # Requirements documentation
├── .ralph/            # Ralph orchestration files
├── rules/             # Rule files for development
└── examples/          # Example usage scripts
```

### 4.2 Test Directory Structure

```
tests/
├── unit/              # Unit tests (no I/O)
│   ├── domain/        # Mirror app/domain structure
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── strategies/
│   └── services/      # Mirror app/services structure
│       ├── compliance/
│       └── execution/
├── integration/       # Integration tests (with mocks)
│   ├── database/
│   ├── brokers/
│   └── external_apis/
├── e2e/               # End-to-end tests
│   ├── test_trading_flow.py
│   └── test_reconciliation.py
├── fixtures/          # Test fixtures
│   ├── sample_data.py
│   └── mock_factories.py
└── conftest.py        # Pytest configuration
```

### 4.3 Log Directory Structure

```
logs/
├── trading/           # Trading activity logs
│   ├── orders.log
│   └── executions.log
├── audit/             # Audit logs
│   └── compliance.log
├── errors/            # Error logs
│   └── errors.log
└── performance/       # Performance logs
    └── metrics.log
```

---

## 5. DIRECTORY RULES

### 5.1 Core Rules

| Rule ID | Rule | Requirement |
|---------|------|------------|
| **FS-DIR-001** | Tests mirror source | `tests/unit/domain/` mirrors `app/domain/` |
| **FS-DIR-002** | Config separate from code | Config files in `config/`, not `app/` |
| **FS-DIR-003** | Logs in dedicated directory | Log files in `logs/`, not scattered |
| **FS-DIR-004** | No code in root | Only config/scripts in project root |
| **FS-DIR-005** | Max depth 4 | `app/services/execution/` = 3 levels max |

### 5.2 Prohibited Patterns

| Rule ID | Prohibited Pattern | Reason |
|---------|-------------------|--------|
| **FS-BAN-001** | `app/utils.py` (single file) | Use `app/core/utils/` directory |
| **FS-BAN-002** | `app/helpers.py` | Too vague, use specific naming |
| **FS-BAN-003** | `app/common.py` | Too vague, organize by purpose |
| **FS-BAN-004** | `app/misc.py` | PROHIBITED - no misc files |
| **FS-BAN-005** | Nested `__init__.py` logic | Keep `__init__.py` minimal |

---

## 6. REQUIREMENTS FILES STRUCTURE

### 6.1 Requirements Documentation

```
.requirements/
├── BASE_RULES.md              # Universal rules for all files
├── CRITICAL_RULES.md          # Security and critical rules
├── ARCHITECTURE_REQUIREMENTS.md  # Layer architecture rules (this file)
├── FILE_SYSTEM_REQUIREMENTS.md   # File organization rules (this file)
└── app/                       # Per-file requirements
    ├── domain/
    │   └── entities/
    │       └── trade.requirements.md
    ├── services/
    │   └── execution/
    │       └── engine.requirements.md
    └── infrastructure/
        └── brokers/
            └── alpaca_adapter.requirements.md
```

### 6.2 Requirements File Format

```markdown
# Requirements: app/domain/entities/trade.py

## Source Analysis
- **File**: app/domain/entities/trade.py
- **Layer**: domain (CORE - No external dependencies)
- **LOC**: 85

## Purpose
Business entity representing a trade transaction.

## Architecture Rules (MANDATORY for this layer)
- [ ] ARCH-DEP-001: Domain layer purity
- [ ] ARCH-NAM-002: Class names PascalCase

## File System Rules
- [ ] FS-NAM-001: File name snake_case.py
- [ ] FS-INIT-001: Package has __init__.py

## Code Quality
- [ ] QL-006: File < 300 lines
- [ ] TYP-001: 100% type hints

## Status: VERIFIED
```

---

## 7. FILE SYSTEM CHECKLIST

Before any commit, verify:

### Package Structure
- [ ] Every package has `__init__.py`
- [ ] `__init__.py` exports public API with `__all__`
- [ ] No business logic in `__init__.py`

### File Naming
- [ ] Files use `snake_case.py`
- [ ] Test files use `test_{module}.py`
- [ ] Protocol files use `{entity}_protocol.py`

### Directory Structure
- [ ] Tests mirror source structure
- [ ] Config in `config/`, not in `app/`
- [ ] Logs in `logs/`, not scattered
- [ ] Max directory depth of 4

### Prohibited Patterns
- [ ] No `utils.py`, `helpers.py`, `common.py`, `misc.py`
- [ ] No star imports in `__init__.py`
- [ ] No code in project root

---

## CROSS-REFERENCES

- See `.requirements/ARCHITECTURE_REQUIREMENTS.md` for layer and dependency rules
- See `.requirements/BASE_RULES.md` for code quality rules
- See `.requirements/CRITICAL_RULES.md` for security rules
- See `rules/python/05-architecture.md` for architecture patterns
- See `rules/python/18-clean-architecture-structure.md` for Clean Architecture rules
