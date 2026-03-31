# Domain-Infrastructure Separation Plan

## Current State Analysis

### Problems Identified (from AUDIT_PLAN)

1. **`app/strategies/base.py`** - Imports database modules (infrastructure dependency)
2. **`app/backtesting/`** - Mixes domain logic with infrastructure concerns
3. **`app/engines/`** - Implementation details mixed with domain protocols
4. **`app/services/`** - 119 files, many mixing domain with infrastructure

### Target State

```
app/
├── domain/                    # Pure domain - NO infrastructure dependencies
│   ├── entities/             # ✓ Already clean
│   ├── value_objects/        # ✓ Already clean
│   ├── factories/            # ✓ Already clean
│   ├── repositories/         # Interfaces only (NO implementations)
│   │   ├── order_repository.py       # Abstract protocol
│   │   ├── portfolio_repository.py    # Abstract protocol
│   │   └── position_repository.py     # Abstract protocol
│   └── portfolio_optimization/ # ✓ Already clean
│
├── infrastructure/           # ALL concrete implementations
│   ├── persistence/          # Database implementations
│   │   ├── sql_order_repository.py
│   │   ├── sql_portfolio_repository.py
│   │   └── sql_position_repository.py
│   ├── external/             # External API clients
│   │   ├── yahoo_finance.py
│   │   ├── crypto_api.py
│   │   └── forex_api.py
│   └── messaging/            # Message queues
│       └── redis_pubsub.py
│
└── application/              # Orchestrates domain + infrastructure
    ├── use_cases/            # Business workflows
    └── services/             # Application services
```

## Dependency Rules

1. **Domain → Infrastructure**: ❌ FORBIDDEN
2. **Infrastructure → Domain**: ✅ ALLOWED (implements interfaces)
3. **Application → Domain**: ✅ ALLOWED
4. **Application → Infrastructure**: ✅ ALLOWED (via interfaces)

## Migration Steps

### Step 1: Create Repository Interfaces in Domain

Already exists in `app/domain/repositories/`:
- `order_repository.py` - OrderRepository protocol
- `portfolio_repository.py` - PortfolioRepository protocol
- `position_repository.py` - PositionRepository protocol

### Step 2: Create Concrete Implementations in Infrastructure

Create in `app/infrastructure/persistence/`:
- `sql_order_repository.py` - SQLAlchemy implementation
- `sql_portfolio_repository.py` - SQLAlchemy implementation
- `sql_position_repository.py` - SQLAlchemy implementation

### Step 3: Update Strategies to Remove Infrastructure Dependencies

Problem: `app/strategies/base.py` imports database modules

Solution: Inject repository via constructor instead of importing directly

### Step 4: Update Engines to Use Interfaces

Problem: `app/engines/` mix domain with infrastructure

Solution: Create protocol interfaces in domain, implement in infrastructure

## Verification Checklist

- [ ] No imports from `infrastructure` in `domain/`
- [ ] No imports from `database` in `domain/`
- [ ] No imports from `api` in `domain/`
- [ ] All repositories use interface from domain, implemented in infrastructure
- [ ] All tests pass after separation

---

*Reference: AUDIT_PLAN_COMPLETO.md - FASE 1.5*
