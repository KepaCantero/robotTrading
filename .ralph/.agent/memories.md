# Memories - AlgoTrading Project

## Project Context

**Project Type:** Algorithmic Trading System
**Main Goal:** 1000€ → 500k (living from trading)

**Tech Stack:** Python 3.12+, AsyncIO, Pydantic, Pandas, NumPy

## Architecture Patterns

### Layer Architecture
```
app/
├── core/           # Domain primitives, protocols
├── domain/        # Business entities
├── application/    # Use cases,├── infrastructure/  # External integrations
├── services/       # Domain services
└── shared/        # Shared utilities
```

### Key Protocols
- `IComplianceEngine`: Valida trades against R1-R29
- `IRiskValidator`: Valida risk (Kelly, DD, R:R)
- `ITaxEngine`: Spain tax calculations
- `IDecisionLogger`: Append-only logging

## Coding Conventions

### Naming
- Files: snake_case
- Classes: PascalCase
- Functions: snake_case
- Constants: UPPER_SNAKE_CASE

### Type Hints
- Siempre usar type hints
- Prefer Protocol sobre abc.ABC
- Usar Pydantic para validación

### Imports
```python
# Standard order
from __future__ import annotations
from typing import Protocol, Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
```

## Trading Rules (R1-R29)

### Risk Management
- **R1:** Kelly Criterion + 2% max position
- **R2:** Drawdown 15% stop trading
- **R3:** Stop loss SIEMPRE
- **R4:** R:R 2:1 minimum

### Logging
- **R15:** Append-only logging
- **R28:** 5 años retención para### Spain Tax
- **IRPF:** Progressive 19/21/23%
- **Dividendos UE:** 0% withholding
- **Modelo 720:** >€50k extranjeros

## Known Issues

### Technical Debt
- [ ] Algunos archivos usan abc.ABC en lugar de Protocol
- [ ] Magic numbers en algunos archivos
- [ ] Imports circulares en algunos módulos

### TODOs
- [ ] Migrar abc.ABC a typing.Protocol
- [ ] Centralizar todos los magic numbers
- [ ] Añadir tests para backtesting

## Session Learnings

<!-- Add learnings from each session here -->
