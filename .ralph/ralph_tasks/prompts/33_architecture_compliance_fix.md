# Architecture & File System Compliance Fix - Ralph Task Prompts

# Version: 2.0
# Created: 2026-03-15
# Based on: ARCHITECTURE_AUDIT_REPORT.md + FILE_SYSTEM_AUDIT_REPORT.md

# COVERAGE MATRIX:
# | Issue ID | Description | Report | Severity | Hat | Status |
# |---------|-------------|--------|----------|-----|--------|
# | ARCH-DEP-001 | Domain purity (40+ files) | ARCH | P0 | HAT 2 | COVERED |
# | ARCH-ANTI-006 | SQLAlchemy in domain | ARCH | P0 | HAT 3 | COVERED |
# | ARCH-FILE-001 | Files > 300 lines (30+) | ARCH | P1 | HAT 5 | COVERED |
# | ARCH-DIR | Non-standard dirs (9) | ARCH | P2 | HAT 7 | COVERED |
# | FS-DIR-005 | Directory depth > 4 (30+) | FS | P1 | HAT 8 | COVERED |
# | FS-BAN-001 | Prohibited names (2) | FS | P1 | HAT 6 | COVERED |
# | FS-DIR-004 | Code in root (1) | FS | P2 | HAT 6 | COVERED |

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
# ARCH-DEP-001: Domain importing from services/infrastructure/api/application
grep -rn "from app\.services\|from app\.infrastructure\|from app\.api\|from app\.application" app/domain/

# ARCH-ANTI-006: Framework in domain (SQLAlchemy, FastAPI)
grep -rn "from sqlalchemy\|from fastapi" app/domain/

# ARCH-FILE-001: Files > 300 lines
find app -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'

# FS-BAN-001: Prohibited file names (utils.py, helpers.py, common.py, misc.py)
find app -type f \( -name "utils.py" -o -name "helpers.py" -o -name "common.py" -o -name "misc.py" \)

# FS-DIR-005: Directory depth > 4 (app/level1/level2/level3/level4/level5 = 6 levels)
find app -type d | awk -F/ '{if(NF>5) print}'

# FS-DIR-004: Code in project root
ls -la *.py 2>/dev/null | grep -v "__"
```

3. **Create violations JSON at `.ralph/outputs/compliance_violations.json`:**

```json
{
  "scan_timestamp": "2026-03-15T...",
  "source_reports": {
    "architecture": ".ralph/outputs/ARCHITECTURE_AUDIT_REPORT.md",
    "file_system": ".ralph/outputs/FILE_SYSTEM_AUDIT_REPORT.md"
  },
  "violations": {
    "architecture": {
      "domain_purity": [
        {"file": "app/domain/strategies/carver_robust_rules.py", "line": 25, "import": "from app.application.scheduling"},
        {"file": "app/domain/strategies/automated_backtest.py", "line": 18, "import": "from app.services.portfolio_config_manager"},
        {"file": "app/domain/strategies/momentum.py", "line": 22, "import": "from app.services.signal_scoring_engine"},
        {"file": "app/domain/services/compliance/compliance_engine.py", "lines": "multiple", "count": 20},
        "... (40+ total)"
      ],
      "framework_in_domain": [
        {"file": "app/domain/tax/database/fifo_schema.py", "line": 36, "import": "from sqlalchemy.*"}
      ],
      "oversized_files": [
        {"file": "app/domain/services/compliance/compliance_engine.py", "lines": 3500},
        {"file": "app/services/optimization_chan.py", "lines": 2612},
        {"file": "app/services/risk_models_narang.py", "lines": 2117},
        "... (30+ total)"
      ]
    },
    "file_system": {
      "prohibited_names": [
        {"file": "app/presentation/api/utils.py", "rename_to": "api_helpers.py"},
        {"file": "app/services/hurst_analysis/utils.py", "rename_to": "hurst_calculations.py"}
      ],
      "deep_directories": [
        {"path": "app/backtesting/...", "depth": 10},
        {"path": "app/domain/services/risk/validators/", "depth": 9},
        {"path": "app/sre/oncall/runbooks/", "depth": 9},
        "... (30+ total)"
      ],
      "misplaced_files": [
        {"file": "app.py", "issue": "Code in root", "action": "move or delete"}
      ]
    }
  },
  "totals": {
    "critical": 41,
    "high": 62,
    "medium": 10
  }
}
```

4. **Publish event:** `violations.scanned` with count of violations found.

---

## HAT 2: Domain Purity Fixer (ARCH-DEP-001)
### Role
Remove all service/infrastructure imports from domain layer files.

### Files to Fix (from audit report)
| File | Line | Current Import |
|------|------|----------------|
| `domain/strategies/carver_robust_rules.py` | 25 | `from app.application.scheduling.market_scheduler` |
| `domain/strategies/automated_backtest.py` | 18 | `from app.services.portfolio_config_manager` |
| `domain/strategies/momentum.py` | 22 | `from app.services.signal_scoring_engine` |
| `domain/strategies/optimization/hyperparameter_optimizer.py` | 304 | `from app.infrastructure.data.feeds` |
| `domain/optimization/multi_strategy_optimizer_v2.py` | 24-25 | `from app.services.*` |
| `domain/repositories/unit_of_work.py` | 432-433 | `from app.infrastructure.persistence.sql_*` |
| `domain/services/signals/scoring.py` | 7 | `from app.services.signal_scoring_engine` |
| `domain/services/compliance/compliance_engine.py` | Multiple | 20+ imports |
| `domain/services/compliance/service_registry.py` | Multiple | 10+ imports |
| `domain/services/execution/*.py` | Multiple | Multiple imports |

### Fix Pattern
```python
# BEFORE (VIOLATION)
from app.services.signal_scoring_engine import get_signal_scoring_engine

class MomentumStrategy:
    def __init__(self):
        self._scorer = get_signal_scoring_engine()  # VIOLATION

# AFTER (FIXED)
# Step 1: Create Protocol in app/core/protocols/
from typing import Protocol

class SignalScorerProtocol(Protocol):
    def score(self, signal: Signal) -> float: ...

# Step 2: Update domain to use Protocol
from app.core.protocols.signal_scorer_protocol import SignalScorerProtocol

class MomentumStrategy:
    def __init__(self, scorer: SignalScorerProtocol):  # FIXED - DI
        self._scorer = scorer
```

### Instructions
1. Read violations JSON from HAT 1
2. For each domain file with service/infrastructure imports:
   - Create Protocol interface if not exists
   - Refactor to use dependency injection
   - Update constructor to accept Protocol
3. Log all fixes to `FIX_LOG`
4. **DO NOT modify the actual implementation** - only change import sources and add DI
5. Publish event: `domain.purified`

---

## HAT 3: Infrastructure Extractor (ARCH-ANTI-006)
### Role
Move infrastructure files out of domain layer.

### Files to Move
| Current Location | Target Location |
|-----------------|-----------------|
| `app/domain/tax/database/fifo_schema.py` | `app/infrastructure/database/schemas/fifo_schema.py` |

### Instructions
1. Create target directory: `app/infrastructure/database/schemas/`
2. Move file: `mv app/domain/tax/database/fifo_schema.py app/infrastructure/database/schemas/`
3. Update all imports referencing this file
4. Log move to `FIX_LOG`
5. Publish event: `infrastructure.extracted`

---

## HAT 4: Protocol Creator
### Role
Create missing Protocol interfaces for dependency inversion.

### Protocols to Create in `app/core/protocols/`

```python
# app/core/protocols/broker_protocol.py
from typing import Protocol
from app.domain.entities.order import Order
from app.domain.entities.execution import Execution
from app.domain.entities.position import Position

class BrokerProtocol(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def get_positions(self) -> list[Position]: ...
    def execute_order(self, order: Order) -> Execution: ...

# app/core/protocols/signal_scorer_protocol.py
class SignalScorerProtocol(Protocol):
    def score(self, signal: "Signal") -> float: ...
    def get_scores(self, signals: list["Signal"]) -> list[float]: ...

# app/core/protocols/portfolio_config_protocol.py
class PortfolioConfigProtocol(Protocol):
    def get_config(self, portfolio_id: str) -> "PortfolioConfig": ...
    def save_config(self, config: "PortfolioConfig") -> None: ...

# app/core/protocols/repository_protocol.py
from typing import Protocol, Generic, TypeVar

T = TypeVar("T")

class RepositoryProtocol(Protocol, Generic[T]):
    def save(self, entity: T) -> None: ...
    def find_by_id(self, id: str) -> T | None: ...
    def find_all(self) -> list[T]: ...

# app/core/protocols/market_data_protocol.py
class MarketDataProtocol(Protocol):
    def get_bars(self, symbol: str, timeframe: str) -> list["Bar"]: ...
    def get_current_price(self, symbol: str) -> float: ...
```

### Instructions
1. Create `app/core/protocols/` directory if not exists
2. Create Protocol files for each external dependency
3. Ensure Protocols use domain types only
4. Publish event: `protocols.created`

---

## HAT 5: God File Splitter (ARCH-FILE-001)
### Role
Split oversized files (>300 lines) into smaller, focused modules.

### Files to Split (from audit report)
| File | Lines | Split Strategy |
|------|-------|----------------|
| `domain/services/compliance/compliance_engine.py` | 3500+ | Split into checker.py, rules.py, validators.py, service.py |
| `services/optimization_chan.py` | 2612 | Split into optimizer.py, constraints.py, solver.py |
| `services/risk_models_narang.py` | 2117 | Split into risk_model.py, calculator.py, aggregator.py |
| `services/execution_narang.py` | 2089 | Split into executor.py, algorithms.py, router.py |
| `services/portfolio_construction_narang.py` | 2066 | Split into constructor.py, allocator.py, rebalancer.py |
| `services/transaction_costs.py` | 1998 | Split into cost_model.py, estimator.py, calculator.py |
| `services/regime_detection_chan.py` | 1952 | Split into detector.py, features.py, classifier.py |
| `services/alerting_system.py` | 1828 | Split into alerter.py, notifiers.py, rules.py |
| `services/portfolio_optimizer.py` | 1799 | Split into optimizer.py, objectives.py, constraints.py |
| `services/live_trading/broker_connector.py` | 1721 | Split into connector.py, authenticator.py, session.py |

### Split Pattern
```python
# BEFORE: compliance_engine.py (3500 lines) - GOD CLASS
class ComplianceEngine:
    def check_pre_trade(self, order): ...
    def check_post_trade(self, execution): ...
    def check_risk_limits(self, portfolio): ...
    def check_position_limits(self, position): ...
    def calculate_var(self, positions): ...
    def calculate_stress(self, positions): ...
    # ... 3000+ more lines

# AFTER: Split into focused modules
# domain/services/compliance/checker.py (200 lines)
class ComplianceChecker:
    def check(self, context: ComplianceContext) -> ComplianceResult: ...

# domain/services/compliance/rules.py (150 lines)
class ComplianceRules:
    def get_pre_trade_rules(self) -> list[Rule]: ...
    def get_post_trade_rules(self) -> list[Rule]: ...

# domain/services/compliance/validators.py (150 lines)
class PreTradeValidator:
    def validate(self, order: Order) -> ValidationResult: ...

# services/compliance/service.py (200 lines)
class ComplianceService:
    def __init__(self, checker: ComplianceChecker, repo: RepositoryProtocol): ...
    def run_compliance_check(self, order: Order) -> ComplianceResult: ...
```

### Instructions
1. For each oversized file:
   - Identify distinct responsibilities
   - Create new files < 300 lines
   - Move code to appropriate layer (domain vs services vs infrastructure)
2. Maintain backward compatibility via `__init__.py` re-exports
3. Log all splits to `FIX_LOG`
4. **DO NOT split all files** - focus on top 10 worst offenders
5. Publish event: `files.splitted`

---

## HAT 6: File Renamer (FS-BAN-001, FS-DIR-004)
### Role
Rename prohibited files and move misplaced files.

### Files to Rename
| Current | New | Reason |
|---------|-----|--------|
| `app/presentation/api/utils.py` | `app/presentation/api/api_helpers.py` | FS-BAN-001 |
| `app/services/hurst_analysis/utils.py` | `app/services/hurst_analysis/hurst_calculations.py` | FS-BAN-001 |

### Files to Move
| Current | New | Reason |
|---------|-----|--------|
| `app.py` (root) | `app/main.py` or delete | FS-DIR-004 |

### Instructions
1. For each file to rename:
   - `git mv old_path new_path`
   - Find all files importing from old path
   - Update imports
2. For `app.py`:
   - Check if it's used
   - If used, move to `app/main.py`
   - If not used, delete
3. Log all changes to `FIX_LOG`
4. Publish event: `files.renamed`

---

## HAT 7: Directory Consolidator
### Role
Create consolidation plan for overlapping directories (Phase 1 only - rename utils.py already done).

### Non-Standard Directories (from audit)
| Directory | Issue | Recommended Action |
|-----------|-------|-------------------|
| `app/application/` | Overlaps with `services/` | PHASE 2: Merge into `services/` |
| `app/backtesting/` | Not in spec | KEEP - domain-specific for quant |
| `app/engines/` | Overlaps with `services/` | PHASE 2: Merge into `services/` |
| `app/models/` | Should be in `domain/` | PHASE 3: Move to `domain/models/` |
| `app/presentation/` | Overlaps with `api/` | PHASE 3: Merge into `api/` |
| `app/security/` | Not in spec | PHASE 2: Move to `services/security/` |
| `app/shared/` | Overlaps with `core/` | PHASE 2: Merge into `core/` |
| `app/simulation/` | Not in spec | KEEP - domain-specific for quant |
| `app/sre/` | Not in spec | PHASE 3: Move to `infrastructure/monitoring/` |

### Instructions
1. **DO NOT execute Phase 2/3** - only create the plan
2. Document migration steps for each directory
3. Save plan to `.ralph/outputs/directory_consolidation_plan.md`
4. Publish event: `directories.consolidated`

---

## HAT 8: Depth Flattener (FS-DIR-005)
### Role
Flatten directory structures exceeding depth 4.

### Deep Directories (from audit)
| Depth | Directory | Flattening Strategy |
|-------|-----------|-------------------|
| 10 | `app/backtesting/.../models.py` | Flatten intermediate dirs |
| 9 | `app/domain/services/risk/validators/` | Merge validators into parent |
| 9 | `app/sre/oncall/runbooks/` | Flatten to `app/sre/runbooks/` |
| 8 | `app/domain/strategies/learning/` | Keep - justified depth |
| 8 | `app/presentation/dashboard/frontend/` | Flatten intermediate dirs |

### Flattening Pattern
```bash
# BEFORE: depth 9
app/domain/services/risk/validators/pre_trade/
app/domain/services/risk/validators/post_trade/

# AFTER: depth 5
app/domain/services/risk/pre_trade_validators.py
app/domain/services/risk/post_trade_validators.py
```

### Instructions
1. Identify directories with depth > 5
2. For each deep directory:
   - Merge subdirectories into parent as files
   - OR flatten intermediate directories
3. **DO NOT flatten justified structures** (e.g., learning/ has many subdirs but is justified)
4. Update imports after moves
5. Log changes to `FIX_LOG`
6. Publish event: `depth.flattened`

---

## HAT 9: Import Fixer
### Role
Fix all broken imports after file moves and renames.

### Import Fixes Required
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

# After flattening validators
# BEFORE
from app.domain.services.risk.validators.pre_trade import PreTradeValidator
# AFTER
from app.domain.services.risk.pre_trade_validators import PreTradeValidator
```

### Instructions
1. Find all files importing from moved/renamed paths:
   ```bash
   grep -rn "from app.domain.tax.database" app/
   grep -rn "from app.presentation.api.utils" app/
   ```
2. For each broken import:
   - Update to new path
   - Verify with Python AST if possible
3. Run `python -c "import app"` to verify no import errors
4. Log all fixes to `FIX_LOG`
5. Publish event: `imports.fixed`

---

## HAT 10: Requirements Updater
### Role
Update `.requirements/app/` files after structural changes.

### Instructions
1. For each moved/renamed file:
   - Find corresponding `.requirements/app/` file
   - Update file path references
   - Update layer classification if changed
2. Create requirements files for new Protocol files
3. Log updates to `FIX_LOG`
4. Publish event: `requirements.updated`

---

## HAT 11: Compliance Verifier
### Role
Verify all violations are fixed.

### Verification Commands
```bash
# 1. ARCH-DEP-001: Domain purity check
grep -rn "from app\.services\|from app\.infrastructure\|from app\.api\|from app\.application" app/domain/
# Expected: 0 matches (or only in documented exceptions)

# 2. ARCH-ANTI-006: No SQLAlchemy/FastAPI in domain
grep -rn "from sqlalchemy\|from fastapi" app/domain/
# Expected: 0 matches

# 3. ARCH-FILE-001: File sizes
find app -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'
# Expected: Only documented exceptions (or significantly reduced)

# 4. FS-BAN-001: No prohibited file names
find app -type f \( -name "utils.py" -o -name "helpers.py" -o -name "common.py" -o -name "misc.py" \)
# Expected: 0 matches

# 5. FS-DIR-005: Directory depth
find app -type d | awk -F/ '{if(NF>5) print}'
# Expected: Only justified exceptions

# 6. Import integrity
python -c "import app; print('OK')"
# Expected: "OK"
```

### Instructions
1. Run all verification commands
2. Compare results with original violations from HAT 1
3. Calculate compliance score:
   - Before: 50% (architecture) + 75% (file system) = ~62.5%
   - Target: >= 90%
4. List any remaining violations
5. Save verification results to `.ralph/outputs/compliance_verification.json`
6. Publish event: `compliance.verified` with score

---

## HAT 12: Final Reporter
### Role
Generate final compliance report.

### Report Template
```markdown
# Architecture & File System Compliance Report

**Date:** 2026-03-15
**Status:** COMPLETE
**Initial Score:** 62.5%
**Final Score:** X%
**Improvement:** Y%

---

## Summary

| Category | Before | After | Fixed |
|----------|--------|-------|-------|
| Domain Purity Violations (ARCH-DEP-001) | 40+ | X | Y |
| Framework in Domain (ARCH-ANTI-006) | 1 | 0 | 1 |
| Oversized Files (ARCH-FILE-001) | 30+ | X | Y |
| Prohibited Names (FS-BAN-001) | 2 | 0 | 2 |
| Deep Directories (FS-DIR-005) | 30+ | X | Y |
| Misplaced Files (FS-DIR-004) | 1 | 0 | 1 |

---

## Files Modified

- [List all modified files]

## Files Created

- [List all new Protocol files]
- [List all new split files]

## Files Moved

- [List all moved files]

## Files Renamed

- [List all renamed files]

## Remaining Issues (if any)

- [List any violations that could not be fixed]

## Phase 2/3 Recommendations

- [Directory consolidation plan]
- [Future refactoring needs]

---

## Verification Results

[Include output of verification commands]
```

### Instructions
1. Read `FIX_LOG` from previous hats
2. Read `compliance_verification.json` from HAT 11
3. Generate comprehensive report
4. Save to `.ralph/outputs/COMPLIANCE_FIX_REPORT.md`
5. Publish event: `audit.complete`

---

## SUCCESS CRITERIA

| Criterion | Target |
|-----------|--------|
| Domain Purity | 0 violations (or documented exceptions) |
| Framework in Domain | 0 violations |
| File Sizes | All < 300 lines (or documented exceptions) |
| Prohibited Names | 0 files |
| Import Integrity | All imports resolve |
| Compliance Score | >= 90% |

---

## ROLLBACK PLAN

If issues arise:

1. All changes logged in `FIX_LOG`
2. Git commits made after each hat
3. Use `git revert` to rollback specific commits
4. Original locations documented in audit reports

---

## SPECIFIC FILES FROM AUDIT REPORTS

### ARCHITECTURE_AUDIT_REPORT.md - P0 CRITICAL

**Domain files with service/infrastructure imports:**
- `app/domain/strategies/carver_robust_rules.py:25`
- `app/domain/strategies/automated_backtest.py:18`
- `app/domain/strategies/momentum.py:22`
- `app/domain/strategies/optimization/hyperparameter_optimizer.py:304`
- `app/domain/optimization/multi_strategy_optimizer_v2.py:24-25`
- `app/domain/optimization/multi_strategy_optimizer.py:21`
- `app/domain/repositories/unit_of_work.py:432-433`
- `app/domain/services/signals/scoring.py:7`
- `app/domain/services/compliance/compliance_engine.py` (20+ imports)
- `app/domain/services/compliance/service_registry.py` (10+ imports)
- `app/domain/services/execution/trading_bridge_adapter.py:17,21-22`
- `app/domain/services/execution/execution_adapter.py:18`
- `app/domain/services/execution/order_manager_adapter.py:25-26`

**SQLAlchemy in domain:**
- `app/domain/tax/database/fifo_schema.py:36-38`

### FILE_SYSTEM_AUDIT_REPORT.md - P1 HIGH

**Prohibited file names:**
- `app/presentation/api/utils.py`
- `app/services/hurst_analysis/utils.py`

**Code in root:**
- `/app.py`

**Deep directories (depth > 4):**
- `app/backtesting/...` (depth 10)
- `app/domain/services/risk/validators/` (depth 9)
- `app/sre/oncall/runbooks/` (depth 9)
- `app/domain/strategies/learning/` (depth 8)
- `app/presentation/dashboard/frontend/` (depth 8)

---

*Generated by Claude Code - Version 2.0*
