# Architecture Guide - AlgoTrading System

## Layered Architecture

This system follows Clean Architecture principles with clear separation of concerns:

```
app/
├── domain/                    # Domain Layer (Pure business logic)
│   ├── entities/             # Domain entities (Order, Portfolio, Position)
│   ├── value_objects/        # Value objects (Money, Capital, RiskParameters)
│   ├── factories/            # Entity factories
│   ├── models/               # Domain models (Pydantic models)
│   ├── configurators/        # Domain configurators
│   ├── portfolio_optimization/  # Portfolio optimization algorithms
│   └── repositories/         # Repository interfaces (not implementations)
│
├── application/              # Application Layer (Use cases)
│   ├── use_cases/            # Use case orchestrators
│   ├── services/             # Application services
│   ├── dto/                  # Data Transfer Objects
│   ├── interfaces/           # Application interfaces
│   └── routers/              # API routers
│
├── infrastructure/           # Infrastructure Layer (External concerns)
│   ├── persistence/          # Database implementations
│   ├── external/             # External APIs
│   ├── repositories/         # Repository implementations
│   └── messaging/            # Message queues
│
├── presentation/             # Presentation Layer (API/UI)
│   ├── controllers/          # API endpoints
│   ├── views/                # Views/dashboards
│   └── dto/                  # Request/Response DTOs
│
├── strategies/               # Trading Strategies (Domain protocols)
│   ├── base.py               # Strategy protocol/interface
│   ├── momentum/             # Momentum strategy implementations
│   ├── mean_reversion/       # Mean reversion strategy
│   ├── dividend/             # Dividend strategy
│   └── multi_factor/         # Multi-factor strategy
│
├── engines/                  # Trading Engines (Orchestration)
│   ├── execution_engine/     # Order execution
│   ├── risk_engine/          # Risk management
│   ├── portfolio_engine/     # Portfolio management
│   └── data_engine/          # Data acquisition
│
└── services/                 # Shared Services (being phased out)
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

## Migration Path

The current `app/services/` directory (119 files) is being refactored:
- Domain services → `domain/services/`
- Application services → `application/services/`
- Infrastructure services → `infrastructure/`

## Import Aliases (for backward compatibility)

```python
# Old imports (still work during migration)
from app.services.portfolio_service import PortfolioService

# New imports (preferred)
from app.application.services.portfolio_service import PortfolioService
```

---

*Reference: AUDIT_PLAN_COMPLETO.md - FASE 1.4*
