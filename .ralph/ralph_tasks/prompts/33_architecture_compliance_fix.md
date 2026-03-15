# Architecture & File System Compliance Fix - Ralph Task Prompts

**Version:** 1.0
**Created:** 2026-03-15
**Task:** 33_architecture_compliance_fix.yml

---

## HAT 1: Violation Scanner

### Role
Scan all files in `app/` for architecture and file system violations.

### Instructions

1. **Read the audit reports:**
   - `.ralph/outputs/ARCHITECTURE_AUDIT_REPORT.md`
   - `.ralph/outputs/FILE_SYSTEM_AUDIT_REPORT.md`

2. **Scan for violations:**

```bash
# ARCH-DEP-001: Domain importing from services/infrastructure/api
grep -rn "from app\.services\|from app\.infrastructure\|from app\.api\|from app\.application" app/domain/

# ARCH-ANTI-006: Framework in domain
grep -rn "from sqlalchemy\|from fastapi" app/domain/

# ARCH-FILE-001: Files > 300 lines
find app -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'

# FS-BAN-001: Prohibited file names
find app -type f \( -name "utils.py" -o -name "helpers.py" -o -name "common.py" -o -name "misc.py" \)

# FS-DIR-005: Directory depth > 4
find app -type d | awk -F/ '{if(NF>5) print}'
```

3. **Create violations JSON:**

```json
{
  "scan_timestamp": "2026-03-15T...",
  "violations": {
    "architecture": {
      "domain_purity": [...],
      "framework_in_domain": [...],
      "oversized_files": [...]
    },
    "file_system": {
      "prohibited_names": [...],
      "deep_directories": [...],
      "misplaced_files": [...]
    }
  },
  "totals": {
    "critical": 0,
    "high": 0,
    "medium": 0
  }
}
```

4. **Publish event:** `violations.scanned` with count of violations found.

---

## HAT 2: Architecture Fixer

### Role
Fix all architecture violations found by the scanner.

### Priority Order

#### P0 - CRITICAL (Fix First)

1. **SQLAlchemy in domain** (`app/domain/tax/database/fifo_schema.py`)
   - Move to `app/infrastructure/database/schemas/fifo_schema.py`
   - Update all imports

2. **Domain importing from services/infrastructure**
   - Create Protocol interfaces in `app/core/protocols/`
   - Replace direct imports with Protocol dependencies
   - Use dependency injection

#### P1 - HIGH (Fix Second)

3. **Oversized files (>300 lines)**
   - Split `compliance_engine.py` (3500 lines) into:
     - `ComplianceChecker` (domain)
     - `ComplianceService` (services)
     - `ComplianceRepository` (infrastructure)
   - Split other large files similarly

### Fix Patterns

**Pattern 1: Replace direct imports with Protocols**

```python
# BEFORE (VIOLATION)
# app/domain/services/compliance/compliance_engine.py
from app.services.live_trading.broker_connector import BrokerConnector

class ComplianceEngine:
    def __init__(self):
        self._broker = BrokerConnector()  # VIOLATION

# AFTER (FIXED)
# app/core/protocols/broker_protocol.py
class BrokerProtocol(Protocol):
    def connect(self) -> None: ...
    def get_positions(self) -> list[Position]: ...

# app/domain/services/compliance/compliance_engine.py
from app.core.protocols.broker_protocol import BrokerProtocol

class ComplianceEngine:
    def __init__(self, broker: BrokerProtocol):  # FIXED - DI
        self._broker = broker
```

**Pattern 2: Move database schemas to infrastructure**

```python
# BEFORE: app/domain/tax/database/fifo_schema.py
# AFTER: app/infrastructure/database/schemas/fifo_schema.py
```

### Instructions

1. Read violations JSON from HAT 1
2. For each P0 violation:
   - Create Protocol if needed
   - Refactor to use DI
   - Update imports
3. For each P1 violation:
   - Split large files
   - Maintain backward compatibility
4. Log all fixes to `FIX_LOG`
5. Publish event: `architecture.fixed`

---

## HAT 3: File System Fixer

### Role
Fix all file system violations.

### Fixes

#### FS-BAN-001: Rename prohibited files

| Current | New |
|---------|-----|
| `app/presentation/api/utils.py` | `app/presentation/api/api_helpers.py` |
| `app/services/hurst_analysis/utils.py` | `app/services/hurst_analysis/hurst_calculations.py` |

#### FS-DIR-004: Move misplaced files

| Current | New |
|---------|-----|
| `app.py` (root) | `app/main.py` or delete if not needed |

#### Directory Consolidation (P2 - Future)

| Current | Target |
|---------|--------|
| `app/application/` | Merge into `app/services/` |
| `app/shared/` | Merge into `app/core/` |
| `app/presentation/` | Merge into `app/api/` |
| `app/sre/` | Move to `app/infrastructure/monitoring/` |

### Instructions

1. Rename `utils.py` files to specific names
2. Update all imports referencing renamed files
3. Move `app.py` if it exists
4. Log all fixes
5. Publish event: `filesystem.fixed`

---

## HAT 4: Protocol Creator

### Role
Create missing Protocol interfaces for dependency inversion.

### Protocols to Create

```python
# app/core/protocols/broker_protocol.py
class BrokerProtocol(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def get_positions(self) -> list[Position]: ...
    def execute_order(self, order: Order) -> Execution: ...

# app/core/protocols/repository_protocol.py
class RepositoryProtocol(Protocol, Generic[T]):
    def save(self, entity: T) -> None: ...
    def find_by_id(self, id: str) -> T | None: ...
    def find_all(self) -> list[T]: ...

# app/core/protocols/cache_protocol.py
class CacheProtocol(Protocol):
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
```

### Instructions

1. Identify all direct instantiations in domain layer
2. Create Protocol for each external dependency
3. Place in `app/core/protocols/`
4. Update domain files to use Protocols
5. Publish event: `protocols.created`

---

## HAT 5: God File Splitter

### Role
Split oversized files into smaller, focused modules.

### Files to Split

| File | Lines | Split Into |
|------|-------|------------|
| `domain/services/compliance/compliance_engine.py` | 3500+ | `ComplianceChecker`, `ComplianceService`, `ComplianceRepository` |
| `services/optimization_chan.py` | 2612 | `PortfolioOptimizer`, `OptimizerService` |
| `services/portfolio_analytics_service.py` | 1231 | `PortfolioAnalytics`, `AnalyticsCalculator` |
| `backtesting/ensemble_methods.py` | 1227 | `EnsembleStrategy`, `EnsembleEvaluator` |

### Split Pattern

```python
# BEFORE: compliance_engine.py (3500 lines)

# AFTER:
# domain/services/compliance/
# ├── __init__.py
# ├── checker.py          # ComplianceChecker class (200 lines)
# ├── rules.py            # Compliance rules (150 lines)
# ├── validators.py       # Pre-trade validators (150 lines)
# └── protocols.py        # Compliance protocols (50 lines)

# services/compliance/
# ├── __init__.py
# ├── service.py          # ComplianceService (200 lines)
# └── repository.py       # ComplianceRepository (100 lines)
```

### Instructions

1. Identify file's responsibilities
2. Split by single responsibility
3. Create new files < 300 lines
4. Update imports in all dependent files
5. Maintain backward compatibility via __init__.py re-exports
6. Publish event: `files.split`

---

## HAT 6: Directory Consolidator

### Role
Consolidate overlapping directories.

### Consolidation Plan

```
PHASE 1 (Immediate):
- Rename utils.py files (DONE by HAT 3)

PHASE 2 (After testing):
- app/application/ → app/services/application/
- app/shared/ → app/core/shared/
- app/engines/ → app/services/engines/

PHASE 3 (Future - requires more refactoring):
- app/presentation/ → app/api/
- app/sre/ → app/infrastructure/monitoring/
- app/models/ → app/domain/models/
```

### Instructions

1. Start with Phase 1 only
2. Create migration plan for Phase 2 and 3
3. Do NOT execute Phase 2/3 without explicit approval
4. Publish event: `directories.consolidated`

---

## HAT 7: Import Fixer

### Role
Fix all broken imports after file moves and renames.

### Common Import Fixes

```python
# After moving fifo_schema.py
# BEFORE
from app.domain.tax.database.fifo_schema import FIFOSchema
# AFTER
from app.infrastructure.database.schemas.fifo_schema import FIFOSchema

# After renaming utils.py
# BEFORE
from app.presentation.api.utils import format_response
# AFTER
from app.presentation.api.api_helpers import format_response
```

### Instructions

1. Find all files importing from moved/renamed files
2. Update import statements
3. Verify imports work with Python AST
4. Run `python -c "import app"` to verify
5. Publish event: `imports.fixed`

---

## HAT 8: Compliance Verifier

### Role
Verify all violations are fixed.

### Verification Commands

```bash
# 1. Domain purity check
grep -rn "from app\.services\|from app\.infrastructure\|from app\.api" app/domain/
# Expected: 0 matches (or only in allowed exceptions)

# 2. No SQLAlchemy in domain
grep -rn "from sqlalchemy" app/domain/
# Expected: 0 matches

# 3. No oversized files
find app -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'
# Expected: Only allowed exceptions

# 4. No prohibited file names
find app -type f \( -name "utils.py" -o -name "helpers.py" \)
# Expected: 0 matches
```

### Instructions

1. Run all verification commands
2. Compare results with original violations
3. Calculate compliance score
4. If score < 90%, list remaining violations
5. Publish event: `compliance.verified` with score

---

## HAT 9: Final Reporter

### Role
Generate final compliance report.

### Report Template

```markdown
# Architecture & File System Compliance Report

**Date:** 2026-03-15
**Status:** COMPLETE

## Summary

| Category | Before | After | Fixed |
|----------|--------|-------|-------|
| Domain Purity Violations | 40+ | X | Y |
| Framework in Domain | 1 | 0 | 1 |
| Oversized Files | 30+ | X | Y |
| Prohibited Names | 2 | 0 | 2 |
| Misplaced Files | 1 | 0 | 1 |

## Compliance Score

- Before: 50%
- After: X%
- Improvement: Y%

## Files Modified

- List all files that were modified

## Files Created

- List all new Protocol files
- List all new split files

## Remaining Issues (if any)

- List any violations that could not be fixed

## Recommendations

- Next steps for Phase 2/3 consolidation
```

### Instructions

1. Read fix log from previous hats
2. Run final verification
3. Generate report
4. Save to `.ralph/outputs/COMPLIANCE_FIX_REPORT.md`
5. Publish event: `audit.complete`

---

## SUCCESS CRITERIA

1. **Domain Purity:** No imports from services/infrastructure/api in domain
2. **No Framework in Domain:** No SQLAlchemy/FastAPI imports in domain
3. **File Sizes:** All files < 300 lines (or documented exceptions)
4. **File Names:** No utils.py, helpers.py, common.py, misc.py
5. **Import Integrity:** All imports resolve correctly
6. **Compliance Score:** >= 90%

---

## ROLLBACK PLAN

If issues arise:

1. All changes are logged in `FIX_LOG`
2. Git commits are made after each major change
3. Use `git revert` to rollback specific commits
4. Original file locations documented in audit reports

---

## LEARNINGS FROM AUDITS

### Architecture Audit Learnings

1. **Domain layer has many service imports** - Need Protocol pattern
2. **SQLAlchemy in domain/tax/database** - Should be in infrastructure
3. **compliance_engine.py is 3500+ lines** - God class, needs splitting
4. **Dependency injection not used** - Direct instantiation everywhere

### File System Audit Learnings

1. **utils.py files are vague** - Need specific names
2. **Directory depth > 4** - Need flattening
3. **Overlapping directories** - application/services, shared/core
4. **Code in root** - app.py should move

### Best Practices for Fixes

1. **Always create Protocols first** - Before refactoring imports
2. **Use DI for external dependencies** - Never direct instantiation
3. **Keep files < 300 lines** - Split early, split often
4. **Maintain backward compatibility** - Use __init__.py re-exports
5. **Commit after each hat** - Easy rollback
6. **Test imports after moves** - Python -c "import app"

---

*Generated by Claude Code*
