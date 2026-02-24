# Architecture Guide - AlgoTrading System

## Layered Architecture

This system follows Clean Architecture principles with clear separation of concerns.

### Current Structure (After Reorganization)

```
app/
├── domain/                    # Domain Layer (Pure business logic)
│   ├── entities/             # Domain entities (Order, Portfolio, Position)
│   ├── value_objects/        # Value objects (Money, Capital, RiskParameters)
│   ├── factories/            # Entity factories
│   ├── models/               # Domain models (Pydantic models) + app/models migrated
│   ├── configurators/        # Domain configurators
│   ├── portfolio_optimization/  # Portfolio optimization algorithms
│   ├── repositories/         # Repository interfaces (not implementations)
│   ├── strategies/           # Trading strategies (migrated from app/strategies)
│   ├── analysis/             # Analysis tools (migrated from app/analysis)
│   ├── optimization/         # Optimization algorithms (migrated from app/optimization)
│   ├── portfolio/            # Portfolio management (migrated from app/portfolio)
│   ├── tax/                  # Tax calculations (migrated from app/tax)
│   ├── ensemble/             # Strategy ensembles (migrated from app/ensemble)
│   ├── trading/              # Trading logic
│   │   └── market_making/    # Market making strategies
│   └── market_analysis/      # Market analysis (consolidated microstructure)
│       └── microstructure/   # Market microstructure + OFI
│
├── application/              # Application Layer (Use cases)
│   ├── use_cases/            # Use case orchestrators
│   ├── services/             # Application services
│   ├── dto/                  # Data Transfer Objects
│   ├── interfaces/           # Application interfaces
│   ├── routers/              # API routers
│   └── orchestration/        # Orchestration logic (migrated from app/maestro)
│
├── infrastructure/           # Infrastructure Layer (External concerns)
│   ├── persistence/          # Database implementations
│   │   └── database/         # Database models (migrated from app/database)
│   ├── external/             # External APIs
│   ├── repositories/         # Repository implementations
│   ├── messaging/            # Message queues
│   ├── providers/            # Service providers (migrated from app/providers)
│   ├── data/                 # Data infrastructure (migrated from app/data)
│   ├── middleware/           # Middleware (migrated from app/middleware)
│   └── config/               # Infrastructure config (migrated from app/user_config)
│
├── presentation/             # Presentation Layer (API/UI)
│   ├── controllers/          # API endpoints
│   ├── views/                # Views/dashboards
│   ├── dto/                  # Request/Response DTOs
│   ├── api/                  # API routes (migrated from app/api)
│   └── dashboard/            # Dashboard UI (migrated from app/dashboard)
│
├── shared/                   # Shared utilities (NEW)
│   ├── config/               # Shared configuration
│   ├── logging/              # Logging utilities
│   ├── exceptions/           # Shared exceptions (migrated from app/exceptions)
│   ├── constants/            # Global constants
│   └── utils/                # Utility functions
│
├── backtesting/              # Backtesting framework (specialized layer)
│   ├── core/                 # Core backtesting logic
│   ├── execution/            # Execution simulation
│   ├── services/             # Backtesting services
│   └── shared/               # Shared backtesting utilities
│
├── engines/                  # Trading Engines (Orchestration)
│   ├── execution_engine/     # Order execution
│   ├── risk_engine/          # Risk management
│   ├── portfolio_engine/     # Portfolio management
│   └── strategy_engines/     # Strategy-specific engines
│
├── security/                 # Security layer (cross-cutting)
│
├── sre/                      # Site Reliability Engineering
│
├── simulation/               # Simulation tools
│
└── core/                     # Core module (backward compatibility only)
```

**Note:** The `core/` directory has been migrated. Contents moved to:
- Config → `shared/config/`
- Auth/Security → `security/`
- Database → `infrastructure/persistence/`
- Utils → `shared/utils/`
- Protocols → `shared/protocols/`
- Models → `domain/models/`

## Directory Count Progress

| Stage | Directories | Notes |
|-------|-------------|-------|
| Before | 42 | Cluttered, many orphans |
| After Phase 1-3 | 14 | Clean Architecture layers |
| After Phase 4 | 11 | services/ migrated and removed |
| Target | ~10 | Almost complete |

## Import Migration

Use the migration script for automatic import updates:

```bash
# Dry run to see changes
python scripts/migrate_imports.py --dry-run

# Apply changes
python scripts/migrate_imports.py
```

### Import Mapping Examples

```python
# OLD → NEW
from app.strategies import X     → from app.domain.strategies import X
from app.models import X         → from app.domain.models import X
from app.api import X            → from app.presentation.api import X
from app.dashboard import X      → from app.presentation.dashboard import X
from app.database import X       → from app.infrastructure.persistence.database import X
from app.microstructure import X → from app.domain.market_analysis.microstructure import X
```

## Dependency Rules

1. **Domain** → No dependencies on other layers
2. **Application** → Can depend on Domain
3. **Infrastructure** → Can depend on Domain (implements interfaces)
4. **Presentation** → Can depend on Application and Domain

## Key Principles

1. **Dependency Inversion**: High-level modules shouldn't depend on low-level modules
2. **Single Responsibility**: Each module has one reason to change
3. **Interface Segregation**: Small, focused interfaces
4. **Open/Closed**: Open for extension, closed for modification

## Migration Status

### Completed
- [x] Consolidated microstructure/ + market_microstructure/ → domain/market_analysis/microstructure/
- [x] Migrated strategies/ → domain/strategies/
- [x] Migrated models/ → domain/models/
- [x] Migrated api/ → presentation/api/
- [x] Migrated dashboard/ → presentation/dashboard/
- [x] Migrated database/ → infrastructure/persistence/database/
- [x] Migrated providers/ → infrastructure/providers/
- [x] Migrated analysis/ → domain/analysis/
- [x] Migrated optimization/ → domain/optimization/
- [x] Created shared/ directory
- [x] Migrated services/ → domain/services/, application/, infrastructure/
- [x] Removed services/ directory (333 files migrated)
- [x] Migrated core/ → shared/config/, security/, infrastructure/, shared/utils/, etc.
- [x] Updated 848+ imports total

### Pending
- [ ] Review engines/ directory structure (optional)
- [ ] Remove remaining duplicate code (optional)

---

*Last updated: 2024-02-22*
*Reference: Plan de Reorganización de app/ - AlgoTrading*
