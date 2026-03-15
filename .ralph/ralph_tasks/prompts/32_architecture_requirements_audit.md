# Architecture Requirements Audit - Prompt

**Tarea ID:** 32_architecture_requirements_audit
**Propósito:** Auditar requirements a nivel de BIG PICTURE (arquitectura, estructura, sistema)
**Tiempo estimado:** 6 horas
**Depends on:** Nada (tarea autónoma)

---

## OBJETIVO

Revisar los requirements existentes y verificar que:
1. **Todas las reglas de `rules/` están cubiertas** en los requirements
2. **Añadir requirements de arquitectura** (capas, dependencias, boundaries)
3. **Añadir requirements de sistema de archivos** (estructura, nomenclatura)
4. **Revisar BASE_RULES.md y CRITICAL_RULES.md** para cobertura completa
5. **Crear documentos de big picture** que complementen los requirements por archivo
6. **Verificar que TODOS los aspectos de la app están cubiertos**

---

## PROBLEMA ACTUAL

Los requirements actuales están a **nivel de archivo individual** (.requirements/app/.../archivo.requirements.md), pero FALTAN:

- **Requirements de arquitectura:** ¿Cómo se relacionan las capas?
- **Requirements de estructura:** ¿Cómo deben organizarse los directorios?
- **Requirements de sistema:** ¿Qué reglas aplican a nivel de proyecto?
- **Mapeo completo de reglas:** ¿Están todas las reglas de `rules/` cubiertas?
- **Cobertura de aspectos:** ¿Están todos los componentes de la app cubiertos?

---

## FLUJO DE EJECUCION

```
┌─────────────────┐
│  RULES SCANNER  │  Descubre todas las reglas en rules/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ STRUCTURE       │  Analiza estructura actual del proyecto
│ ANALYZER        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GAP ANALYZER   │  Identifica qué falta
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ARCH REQ       │  Genera requirements de arquitectura
│  WRITER         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  VALIDATOR      │  Verifica completitud
└─────────────────┘
```

---

## HAT 1: RULES SCANNER

### Objetivo
Crear inventario completo de todas las reglas en `rules/`

### Archivos a escanear

**rules/python/** (26 archivos):
```
00-checklist.md
01-formatting-style.md
02-type-hints.md
03-solid-principles.md
04-design-patterns.md
05-architecture.md
06-testing.md
07-async-patterns.md
08-configuration.md
09-logging-observability.md
10-advanced-patterns.md
11-enterprise-architecture.md
12-logging-observability.md
13-async-patterns.md
14-configuration-management.md
15-testing-comprehensive.md
16-cosmic-python-architecture-patterns.md
17-fluent-python-idiomatic-code.md
18-clean-architecture-structure.md
19-high-performance-python.md
19-enterprise-checklist.md
21-tdd-python-testing.md
22-fluent-python-advanced-idioms.md
23-high-performance-python-optimization.md
25-clean-code-python-trading.md
50-backtesting-framework.md
```

**rules/trading/** (55+ archivos):
```
01-ernest-chan-algorithmic-trading.md
02-ernest-chan-quantitative-trading.md
03-lopez-de-prado-advances-financial-ml.md
... (ver lista completa en rules/trading/)
```

### Output
`.ralph/outputs/RULES_INVENTORY.json` con inventario completo

---

## HAT 2: PROJECT STRUCTURE ANALYZER

### Objetivo
Analizar la estructura actual y comparar con arquitectura ideal

### Arquitectura Esperada (según rules/python/18-clean-architecture-structure.md)

```
app/
├── domain/              # Business entities (NO framework dependencies)
│   ├── entities/
│   ├── value_objects/
│   ├── services/
│   ├── strategies/
│   └── events/
├── services/            # Use cases and orchestration
│   ├── compliance/
│   ├── execution/
│   ├── position_management/
│   └── reconciliation/
├── infrastructure/      # External concerns
│   ├── database/
│   ├── brokers/
│   └── external_apis/
├── api/                 # Interface layer
│   ├── routes/
│   └── schemas/
└── core/               # Config, protocols, utils
    ├── config/
    ├── protocols/
    └── utils/
```

### Verificaciones

1. **Domain Layer Purity:**
   ```bash
   # NO debe haber imports de framework en domain/
   grep -r "from fastapi\|from sqlalchemy\|import httpx" app/domain/
   # Expected: 0 matches
   ```

2. **Dependency Direction:**
   ```bash
   # domain NO debe importar de services/infrastructure
   grep -r "from app.services\|from app.infrastructure" app/domain/
   # Expected: 0 matches
   ```

3. **Layer Boundaries:**
   - [ ] domain/ existe y está aislado
   - [ ] services/ usa domain via interfaces
   - [ ] infrastructure/ implementa interfaces de domain

---

## HAT 3: GAP ANALYZER

### Objetivo
Identificar qué reglas NO están cubiertas en los requirements actuales

### Análisis de Cobertura

#### Cobertura Actual (en BASE_RULES.md)

| Categoría | ¿Cubierto? | Notas |
|-----------|------------|-------|
| Formatting (01) | ✅ | FMT-001 to FMT-008 |
| Type Hints (02) | ✅ | TYP-001 to TYP-006 |
| SOLID (03) | ✅ | SOL-001 to SOL-005 |
| Architecture (05, 11, 18) | ⚠️ Parcial | Falta estructura detallada |
| Testing (06, 15, 21) | ✅ | TST-001 to TST-008 |
| Security (28) | ✅ | SEC-001 to SEC-010 |
| Logging (09, 12) | ✅ | LOG-001 to LOG-007 |
| Async (07, 13, 24) | ✅ | ASYNC-001 to ASYNC-007 |
| Config (08, 14) | ✅ | CFG-001 to CFG-007 |
| Design Patterns (04, 10) | ✅ | DP-001 to DP-006 |
| Code Quality (00, 19) | ✅ | QL-001 to QL-007 |
| Clean Code (05, 25) | ✅ | CC-001 to CC-007 |
| Trading Rules | ⚠️ Parcial | Algunas reglas faltan |
| **File System Structure** | ❌ NO | **GAP CRÍTICO** |
| **Architecture Boundaries** | ❌ NO | **GAP CRÍTICO** |
| **Module Organization** | ❌ NO | **GAP CRÍTICO** |

#### Gaps Identificados

1. **File System Requirements** - NO existe
   - Estructura de directorios obligatoria
   - Convenciones de nomenclatura
   - Organización por capa vs feature

2. **Architecture Boundary Rules** - Parcial
   - Reglas de dependencia entre capas
   - Interfaces entre módulos
   - Anti-patrones arquitectónicos

3. **Module Interaction Rules** - NO existe
   - Cómo se comunican los módulos
   - Eventos vs llamadas directas
   - Inyección de dependencias

4. **Cosmic Python Patterns (16)** - NO cubierto
   - Repository pattern detallado
   - Service Layer pattern
   - Unit of Work pattern

---

## HAT 4: ARCHITECTURE REQUIREMENTS WRITER

### Objetivo
Crear documentos de requirements a nivel de big picture

### Documentos a Crear

#### 1. ARCHITECTURE_REQUIREMENTS.md

```markdown
# ARCHITECTURE_REQUIREMENTS.md - AlgoTrading

## 1. LAYERED ARCHITECTURE

### 1.1 Layer Definitions

| Layer | Directory | Responsibility | Can Import From |
|-------|-----------|----------------|-----------------|
| Domain | app/domain/ | Business entities, rules | (nothing) |
| Application | app/services/ | Use cases, orchestration | Domain |
| Infrastructure | app/infrastructure/ | DB, APIs, brokers | Domain, Application |
| Presentation | app/api/ | REST API, CLI | Application |

### 1.2 Dependency Rules

- **ARCH-DEP-001:** Domain layer has NO dependencies on other layers
- **ARCH-DEP-002:** Application layer depends ONLY on Domain
- **ARCH-DEP-003:** Infrastructure implements Domain interfaces
- **ARCH-DEP-004:** Presentation uses Application layer only

### 1.3 Anti-Patterns (PROHIBITED)

- ❌ Domain importing from infrastructure
- ❌ Domain importing from services
- ❌ Circular imports between modules
- ❌ God classes (> 300 lines)
- ❌ God functions (> 50 lines)

## 2. FILE ORGANIZATION

### 2.1 Directory Structure

```
app/
├── core/               # Shared config, protocols, utils
│   ├── config/
│   ├── protocols/
│   └── utils/
├── domain/             # CORE - No external deps
│   ├── entities/
│   ├── value_objects/
│   ├── services/
│   ├── strategies/
│   └── events/
├── services/           # APPLICATION - Use cases
│   ├── compliance/
│   ├── execution/
│   ├── position_management/
│   └── reconciliation/
├── infrastructure/     # INFRASTRUCTURE - Adapters
│   ├── database/
│   ├── brokers/
│   └── external_apis/
└── api/                # PRESENTATION - Interface
    ├── routes/
    └── schemas/
```

### 2.2 File Naming Conventions

- **ARCH-NAM-001:** Files: `snake_case.py`
- **ARCH-NAM-002:** Classes: `PascalCase`
- **ARCH-NAM-003:** Functions: `snake_case`
- **ARCH-NAM-004:** Constants: `UPPER_SNAKE_CASE`
- **ARCH-NAM-005:** Private: `_leading_underscore`

## 3. MODULE RULES

### 3.1 Module Structure

- **ARCH-MOD-001:** Every package has `__init__.py`
- **ARCH-MOD-002:** `__init__.py` exports public API
- **ARCH-MOD-003:** No business logic in `__init__.py`
- **ARCH-MOD-004:** PROHIBITED circular imports
- **ARCH-MOD-005:** Use dependency injection to avoid cycles

### 3.2 Import Organization

```python
# 1. Standard library
from typing import Protocol, Optional

# 2. Third-party
import pandas as pd
import numpy as np

# 3. Local imports (depth order)
from app.core.config import Settings
from app.domain.entities import Trade
from app.services.execution import ExecutionService
```

## 4. SIZE LIMITS

| Type | Limit | Rule ID |
|------|-------|---------|
| File | 300 lines | ARCH-FILE-001 |
| Function | 50 lines | ARCH-FILE-002 |
| Class | 300 lines | ARCH-FILE-003 |
| Parameters | 7 max | ARCH-FILE-004 |
| Complexity | 10 max | ARCH-FILE-005 |

## 5. TESTING STRUCTURE

```
tests/
├── unit/               # No I/O, pure logic
│   ├── domain/
│   └── services/
├── integration/        # With DB/API mocks
│   ├── database/
│   └── brokers/
└── e2e/               # Full system
```

## 6. CONFIGURATION

```
config/
├── default.yaml
├── development.yaml
├── production.yaml
└── testing.yaml
```

- **ARCH-CFG-001:** NO secrets in config files
- **ARCH-CFG-002:** Use environment variables for secrets
- **ARCH-CFG-003:** Validate config at startup
```

#### 2. FILE_SYSTEM_REQUIREMENTS.md

```markdown
# FILE_SYSTEM_REQUIREMENTS.md - AlgoTrading

## 1. DIRECTORY ORGANIZATION

### 1.1 By Architectural Layer

| Directory | Contains | Examples |
|-----------|----------|----------|
| app/domain/ | Entities, value objects | Trade, Position, Signal |
| app/services/ | Use cases | ExecutionService |
| app/infrastructure/ | Adapters | AlpacaBroker, PostgresRepo |
| app/api/ | Routes, schemas | /api/trade, TradeSchema |
| app/core/ | Shared utilities | config, protocols |

### 1.2 By Feature (alternative for cohesive features)

```
app/features/trading/
├── domain/
│   └── trade.py
├── services/
│   └── trade_service.py
├── infrastructure/
│   └── trade_repository.py
└── api/
    └── trade_routes.py
```

## 2. FILE NAMING PATTERNS

| Type | Pattern | Example |
|------|---------|---------|
| Entity | `{entity}.py` | `trade.py` |
| Service | `{entity}_service.py` | `trade_service.py` |
| Repository | `{entity}_repository.py` | `trade_repository.py` |
| Protocol | `{entity}_protocol.py` | `broker_protocol.py` |
| Test | `test_{entity}.py` | `test_trade.py` |

## 3. SPECIAL FILES

### 3.1 __init__.py

```python
# Exposes public API of module
from .trade import Trade
from .position import Position

__all__ = ["Trade", "Position"]
```

### 3.2 protocol.py (per module)

```python
# Defines interfaces for the module
from typing import Protocol

class TradeRepositoryProtocol(Protocol):
    def save(self, trade: Trade) -> None: ...
    def find_by_id(self, id: str) -> Trade | None: ...
```

## 4. AUXILIARY DIRECTORIES

```
backups/
├── database/
└── configs/

logs/
├── trading/
├── audit/
└── errors/

.tmp/          # Temporary files (not committed)
.cache/        # Cache files (not committed)
```

## 5. RULES

- **FS-001:** Every Python package has `__init__.py`
- **FS-002:** No business logic in `__init__.py`
- **FS-003:** Tests mirror source structure
- **FS-004:** Config separate from code
- **FS-005:** Logs in dedicated directory
```

---

## HAT 5: VALIDATOR

### Checklist de Validación

#### Archivos Creados

- [ ] `.requirements/ARCHITECTURE_REQUIREMENTS.md` existe
- [ ] `.requirements/FILE_SYSTEM_REQUIREMENTS.md` existe
- [ ] `.requirements/BASE_RULES.md` actualizado con sección 15

#### Contenido Verificado

**ARCHITECTURE_REQUIREMENTS.md:**
- [ ] Sección 1: Layered Architecture
- [ ] Sección 2: Dependency Rules (ARCH-DEP-*)
- [ ] Sección 3: File Organization
- [ ] Sección 4: Module Rules (ARCH-MOD-*)
- [ ] Sección 5: Size Limits (ARCH-FILE-*)
- [ ] Sección 6: Testing Structure

**FILE_SYSTEM_REQUIREMENTS.md:**
- [ ] Sección 1: Directory Organization
- [ ] Sección 2: File Naming Patterns
- [ ] Sección 3: Special Files
- [ ] Sección 4: Auxiliary Directories
- [ ] Sección 5: Rules (FS-*)

**BASE_RULES.md:**
- [ ] Nueva sección 15: Architecture & File System
- [ ] Referencias a nuevos archivos
- [ ] Tabla de reglas resumida

---

## CHECKPOINT FORMAT

```json
{
  "task_id": "32_architecture_requirements_audit",
  "task_name": "Architecture Requirements Audit",
  "started_at": "{{timestamp}}",
  "completed_at": "{{timestamp}}",
  "status": "COMPLETED",
  "progress": {
    "rules_scanned": 81,
    "structure_analyzed": true,
    "gaps_identified": 4,
    "requirements_created": 2,
    "requirements_updated": 1
  },
  "outputs": {
    "files_created": [
      ".requirements/ARCHITECTURE_REQUIREMENTS.md",
      ".requirements/FILE_SYSTEM_REQUIREMENTS.md"
    ],
    "files_updated": [
      ".requirements/BASE_RULES.md"
    ],
    "reports": [
      ".ralph/outputs/RULES_INVENTORY.json",
      ".ralph/outputs/ARCHITECTURE_STRUCTURE_ANALYSIS.json",
      ".ralph/outputs/ARCHITECTURE_REQUIREMENTS_AUDIT_REPORT.json"
    ]
  },
  "metrics": {
    "new_architecture_rules": 25,
    "new_file_system_rules": 10,
    "total_new_rules": 35,
    "gaps_resolved": 4
  }
}
```

---

## SUCCESS CRITERIA

La tarea está COMPLETED cuando:

- [ ] Todos los archivos en rules/ escaneados
- [ ] Estructura del proyecto analizada
- [ ] Gaps identificados y documentados
- [ ] ARCHITECTURE_REQUIREMENTS.md creado
- [ ] FILE_SYSTEM_REQUIREMENTS.md creado
- [ ] BASE_RULES.md actualizado con sección 15
- [ ] **TODOS los requirements.md de archivos actualizados** con:
  - [ ] Sección de Architecture Rules según capa
  - [ ] Referencias a ARCH-*, FS-*
  - [ ] Verificación de consistencia con BASE_RULES.md
- [ ] Validación pasa todos los checks
- [ ] Checkpoint creado con status "COMPLETED"

---

## REFERENCIAS

- `rules/python/05-architecture.md` - Arquitectura base
- `rules/python/11-enterprise-architecture.md` - Arquitectura enterprise
- `rules/python/18-clean-architecture-structure.md` - Clean Architecture
- `rules/python/16-cosmic-python-architecture-patterns.md` - Cosmic Python
- `.requirements/BASE_RULES.md` - Reglas base actuales
- `.requirements/CRITICAL_RULES.md` - Reglas críticas actuales

---

## HAT 6: BASE RULES REVIEWER

### Objetivo
Revisar BASE_RULES.md y CRITICAL_RULES.md para cobertura completa de todos los aspectos de la app

### Aspectos a Verificar

#### 6.1 Domain Layer Coverage
- [ ] Entities (Trade, Position, Signal, Order)
- [ ] Value Objects (Money, Price, Quantity)
- [ ] Domain Services (RiskCalculator, PositionSizer)
- [ ] Domain Events (OrderPlaced, TradeExecuted)
- [ ] Strategies (Momentum, MeanReversion, TrendFollowing)

#### 6.2 Application Layer Coverage
- [ ] Use Cases (ExecuteTrade, ClosePosition, RunBacktest)
- [ ] Orchestration Services
- [ ] DTOs and Mappers

#### 6.3 Infrastructure Layer Coverage
- [ ] Database adapters (PostgreSQL, SQLite)
- [ ] Broker adapters (Alpaca, Interactive Brokers)
- [ ] External APIs (market data, news)
- [ ] Cache layer (Redis)

#### 6.4 Presentation Layer Coverage
- [ ] REST API endpoints
- [ ] CLI commands
- [ ] Dashboard UI
- [ ] WebSocket streams

#### 6.5 Cross-cutting Concerns
- [ ] Logging (structured, JSON)
- [ ] Security (auth, secrets management)
- [ ] Error Handling (custom exceptions)
- [ ] Monitoring (metrics, health checks)
- [ ] Configuration (env vars, validation)

#### 6.6 Trading-Specific
- [ ] Risk Management (position sizing, stop loss)
- [ ] Order Execution (market, limit, stop)
- [ ] Backtesting (walk-forward, out-of-sample)
- [ ] Data Feeds (OHLCV, ticks, order book)
- [ ] Position Management (tracking, P&L)
- [ ] Reconciliation (broker vs internal)

#### 6.7 Spain Tax Compliance
- [ ] IRPF calculation (19/21/23%)
- [ ] Dividend treatment (UE vs non-UE)
- [ ] Modelo 720 reporting
- [ ] Loss carryforward

#### 6.8 Performance & SRE
- [ ] Async patterns
- [ ] Caching strategies
- [ ] Rate limiting
- [ ] Circuit breakers

### Output
`.ralph/outputs/BASE_RULES_COVERAGE_REPORT.json` con análisis de cobertura

---

## HAT 7: FINAL REPORTER

### Objetivo
Generar reporte final consolidado de toda la auditoría

### FASE 1: Consolidar todos los outputs

Leer todos los archivos generados:
- `.ralph/outputs/RULES_INVENTORY.json`
- `.ralph/outputs/ARCHITECTURE_STRUCTURE_ANALYSIS.json`
- `.ralph/outputs/ARCHITECTURE_REQUIREMENTS_AUDIT_REPORT.json`
- `.ralph/outputs/BASE_RULES_COVERAGE_REPORT.json`

### FASE 2: Generar reporte final

Crear: `.ralph/outputs/32_ARCHITECTURE_AUDIT_FINAL_REPORT.md`

```markdown
# Architecture Requirements Audit - Final Report

**Date:** {{timestamp}}
**Task:** 32_architecture_requirements_audit
**Status:** COMPLETE

## Executive Summary

- Total rules in rules/: {{total_rules}}
- Coverage in BASE_RULES.md: {{coverage}}%
- New requirements created: {{new_reqs}}
- Gaps resolved: {{gaps_resolved}}

## Files Created

1. ARCHITECTURE_REQUIREMENTS.md - Layer architecture rules
2. FILE_SYSTEM_REQUIREMENTS.md - File organization rules
3. Updated BASE_RULES.md - Added sections 15-18

## Coverage by Aspect

| Aspect | Coverage | Status |
|--------|----------|--------|
| Domain Layer | 95% | ✅ |
| Application Layer | 80% | ✅ |
| Infrastructure Layer | 70% | ⚠️ |
| Presentation Layer | 60% | ⚠️ |
| Cross-cutting | 90% | ✅ |
| Trading Specific | 85% | ✅ |
| Spain Tax | 75% | ⚠️ |
| Performance/SRE | 80% | ✅ |

## Recommendations

1. Add more infrastructure layer requirements
2. Enhance presentation layer coverage
3. Complete Spain tax requirements

## Next Steps

- Run task 25_requirements_generator to create file-level requirements
- Run task 31_production_audit to validate implementation
```

### FASE 3: Emitir completion promise

Emitir "ARCHITECTURE_REQUIREMENTS_AUDIT_COMPLETE"

---

## HAT 8: FILE-LEVEL REQUIREMENTS UPDATER

### Objetivo
Actualizar los requirements.md de CADA archivo individual para incluir:
1. Referencias a las nuevas reglas de arquitectura (ARCH-*)
2. Referencias a las reglas de file system (FS-*)
3. Reglas específicas según la capa (domain, services, infrastructure, api)
4. Verificar consistencia con BASE_RULES.md y ARCHITECTURE_REQUIREMENTS.md

### FASE 1: Descubrir archivos de requirements existentes

```bash
# Listar todos los requirements.md existentes
find .requirements/app -name "*.requirements.md" -type f | sort
```

### FASE 2: Para cada archivo, determinar su capa

```bash
# Mapear archivo a capa
file="app/services/compliance/engine.py"
layer=""  # domain, services, infrastructure, api, core

if [[ "$file" == *"app/domain/"* ]]; then
  layer="domain"
elif [[ "$file" == *"app/services/"* ]]; then
  layer="services"
elif [[ "$file" == *"app/infrastructure/"* ]]; then
  layer="infrastructure"
elif [[ "$file" == *"app/api/"* ]]; then
  layer="api"
elif [[ "$file" == *"app/core/"* ]]; then
  layer="core"
fi
```

### FASE 3: Template de Requirements por Capa

#### Para archivos en app/domain/

```markdown
# Requirements: app/domain/entities/trade.py

## Source Analysis
- **File**: app/domain/entities/trade.py
- **Layer**: domain (CORE - No external dependencies)
- **LOC**: {{loc}}

## Purpose
{{purpose_from_code}}

## Architecture Rules (MANDATORY for this layer)

### Layer Purity (ARCH-DEP-001)
- [ ] NO imports from app/services/
- [ ] NO imports from app/infrastructure/
- [ ] NO imports from app/api/
- [ ] NO framework imports (FastAPI, SQLAlchemy, httpx)

### Allowed Dependencies
- [ ] Standard library only (typing, dataclasses, enum, datetime)
- [ ] app/core/protocols/ (interfaces)
- [ ] app/domain/ (other domain entities/value_objects)

## SOLID Compliance
- [ ] SOL-001: Single Responsibility
- [ ] SOL-005: Dependency Inversion (via Protocol)

## Code Quality
- [ ] QL-001: Complexity < 10
- [ ] QL-005: Functions < 50 lines
- [ ] QL-006: File < 300 lines
- [ ] TYP-001: 100% type hints

## File System Rules
- [ ] FS-001: Package has __init__.py
- [ ] ARCH-NAM-001: File name snake_case.py
- [ ] ARCH-NAM-002: Classes PascalCase

## Status: NEEDS_AUDIT
```

#### Para archivos en app/services/

```markdown
# Requirements: app/services/compliance/engine.py

## Source Analysis
- **File**: app/services/compliance/engine.py
- **Layer**: services (APPLICATION - Use cases)
- **LOC**: {{loc}}

## Purpose
{{purpose_from_code}}

## Architecture Rules (MANDATORY for this layer)

### Dependency Direction (ARCH-DEP-002)
- [ ] Imports from app/domain/ OK
- [ ] Imports from app/core/protocols/ OK
- [ ] NO direct imports from app/infrastructure/
- [ ] Uses Protocol interfaces for infrastructure

### Dependency Injection
- [ ] All dependencies injected via constructor
- [ ] NO direct instantiation of infrastructure classes

## SOLID Compliance
- [ ] SOL-001: Single Responsibility
- [ ] SOL-002: Open/Closed (via Strategy pattern)
- [ ] SOL-005: Dependency Inversion (via Protocol)

## Code Quality
- [ ] QL-001: Complexity < 10
- [ ] QL-005: Functions < 50 lines
- [ ] QL-006: File < 300 lines
- [ ] TYP-001: 100% type hints

## Testing Requirements
- [ ] TST-001: Unit tests exist
- [ ] TST-004: External deps mocked
- [ ] TST-005: Coverage > 80%

## File System Rules
- [ ] FS-001: Package has __init__.py
- [ ] ARCH-NAM-001: File name snake_case.py

## Status: NEEDS_AUDIT
```

#### Para archivos en app/infrastructure/

```markdown
# Requirements: app/infrastructure/brokers/alpaca_adapter.py

## Source Analysis
- **File**: app/infrastructure/brokers/alpaca_adapter.py
- **Layer**: infrastructure (ADAPTERS - External concerns)
- **LOC**: {{loc}}

## Purpose
{{purpose_from_code}}

## Architecture Rules (MANDATORY for this layer)

### Interface Implementation (ARCH-DEP-003)
- [ ] Implements Protocol from app/core/protocols/
- [ ] Imports from app/domain/ OK (for entities)
- [ ] Imports from app/services/ OK (for interfaces)
- [ ] External SDKs OK (alpaca-trade-api, etc.)

### Adapter Pattern
- [ ] Wraps external library/API
- [ ] Transforms external data to domain entities
- [ ] Handles external errors gracefully

## SOLID Compliance
- [ ] SOL-001: Single Responsibility (one adapter per broker)
- [ ] SOL-003: Liskov Substitution (swappable via Protocol)
- [ ] SOL-005: Dependency Inversion (implements Protocol)

## Security Requirements
- [ ] SEC-001: NO hardcoded API keys
- [ ] SEC-002: Secrets from environment variables
- [ ] SEC-003: TLS/SSL for all connections

## Error Handling
- [ ] All external calls have try/except
- [ ] Errors logged with context
- [ ] Retries with exponential backoff

## Code Quality
- [ ] QL-001: Complexity < 10
- [ ] TYP-001: 100% type hints

## Testing Requirements
- [ ] TST-004: External API mocked
- [ ] Integration tests with mock server

## Status: NEEDS_AUDIT
```

#### Para archivos en app/api/

```markdown
# Requirements: app/api/routes/trading.py

## Source Analysis
- **File**: app/api/routes/trading.py
- **Layer**: api (PRESENTATION - Interface)
- **LOC**: {{loc}}

## Purpose
{{purpose_from_code}}

## Architecture Rules (MANDATORY for this layer)

### Layer Boundaries (ARCH-DEP-004)
- [ ] Uses app/services/ for business logic
- [ ] NO direct access to app/infrastructure/
- [ ] NO direct access to app/domain/
- [ ] Uses DTOs/Schemas for input/output

### API Design
- [ ] RESTful conventions followed
- [ ] Proper HTTP status codes
- [ ] Request validation with Pydantic
- [ ] Response serialization

## Security Requirements
- [ ] SEC-007: Input validation at boundaries
- [ ] SEC-009: JWT authentication
- [ ] SEC-006: Rate limiting

## Error Handling
- [ ] All exceptions caught and converted to HTTP errors
- [ ] Error responses follow standard format
- [ ] No stack traces in production

## Code Quality
- [ ] TYP-001: 100% type hints
- [ ] Functions are thin (delegate to services)

## Testing Requirements
- [ ] TST-007: API endpoint tests
- [ ] TST-004: Services mocked

## Status: NEEDS_AUDIT
```

### FASE 4: Proceso de Actualización

Para cada archivo `.requirements/app/**/*.requirements.md`:

```bash
# 1. Leer requirements existente
cat .requirements/app/services/compliance/engine.requirements.md

# 2. Leer archivo fuente
cat app/services/compliance/engine.py

# 3. Determinar capa
layer=$(echo "$file" | grep -oE "(domain|services|infrastructure|api|core)")

# 4. Añadir sección de Architecture Rules según capa
# 5. Añadir referencias a ARCH-*, FS-*
# 6. Verificar consistencia con BASE_RULES.md
# 7. Guardar archivo actualizado
```

### FASE 5: Verificación de Consistencia

```bash
# Verificar que cada requirements.md referencia BASE_RULES.md
grep -l "BASE_RULES.md" .requirements/app/**/*.requirements.md

# Verificar que cada requirements.md tiene sección de Architecture Rules
grep -l "Architecture Rules" .requirements/app/**/*.requirements.md
```

### OUTPUT

`.ralph/outputs/FILE_REQUIREMENTS_UPDATE_REPORT.json`

```json
{
  "timestamp": "{{timestamp}}",
  "total_files": 350,
  "files_updated": 350,
  "files_skipped": 0,
  "updates_by_layer": {
    "domain": 80,
    "services": 120,
    "infrastructure": 60,
    "api": 40,
    "core": 50
  },
  "new_rules_added": {
    "ARCH-DEP-*": 350,
    "ARCH-NAM-*": 350,
    "FS-*": 350
  },
  "status": "COMPLETE"
}
```

Emitir "file_requirements.updated"

