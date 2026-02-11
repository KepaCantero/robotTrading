# __init__.py

## Purpose
Core module initialization file that provides centralized imports for all core functionality including configuration, database connections, timezone utilities, and the Compliance Engine. This module serves as the main entry point for core dependencies.

---

## Module Exports

### Compliance Engine Components
```python
from app.core.compliance_engine import (
    ComplianceEngine,          # Main compliance checking engine
    PortfolioOptimization,     # Portfolio optimization analysis
    PostTradeAnalysis,         # Post-trade execution analysis
    PreTradeAnalysis,          # Pre-trade validation
    SystemAvailability,        # System availability checks
    get_compliance_engine,     # Get global compliance engine instance
    get_execution_plan,        # Get execution plan for trades
    quick_check,              # Fast compliance check
)
```

### Timezone Utilities (Phase 0.3)
```python
from app.core.timezone_utils import (
    format_market_time,        # Format datetime for market timezone
    format_utc,               # Format datetime as UTC
    get_market_open_close_time, # Get market hours
    get_market_timezone,       # Get timezone for market
    is_market_open,           # Check if market is open
    to_market_time,           # Convert to market timezone
    to_utc,                   # Convert to UTC
    utc_now,                  # Get current UTC time
)
```

### Configuration Utilities
```python
from app.core.config_loader import (
    YAMLConfigLoader,          # YAML configuration loader
    get_config_loader,         # Get global loader instance
    load_strategy_stock_allocator_config,  # Load strategy config
)

from app.core.yaml_config_updater import YAMLConfigUpdater  # YAML update utility
```

### Legacy Components (DEPRECATED)
```python
from app.core.compliance_integration import (
    ComplianceIntegrationEngine as ComplianceIntegrationEngineDeprecated,
    get_compliance_integration_engine as get_compliance_integration_engine_deprecated,
    get_execution_recommendation,  # Get execution recommendation
    quick_pre_trade_check,         # Quick pre-trade validation
)
```

---

## Function Signatures (Contracts)

### Module `__init__` Behavior
**Pre:** None (module initialization)
**Post:** All imports available or gracefully degraded if dependencies missing
**Raises:** ImportError (handled gracefully with try/except)
**Retry:** N/A
**Side Effects:** Sets availability flags (`_compliance_engine_available`, `_compliance_integration_available`)

---

## Acceptance Criteria
- [ ] Module imports successfully even if ComplianceEngine dependencies are missing
- [ ] ImportError is caught and handled gracefully for optional components
- [ ] `__all__` exports list is complete and accurate
- [ ] Deprecated components are clearly marked in docstrings
- [ ] Timezone utilities are always available (no optional imports)

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Audit Status** | ✅ PASSED |
| **BASE_RULES Version** | 96+ rules (2026-02-05) |
| **Audited By** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 0 P0, 0 P1, 1 P2, 0 P3 |
| **Critical GAPs** | None |

### GAP Details
**P2 (Medium):**
- TYP-004: Type ignore comments lack justification (lines 56-63, 79-83)
  - Current: `ComplianceEngine = None  # type: ignore`
  - Recommendation: Add `# type: ignore[assignment] - assigning None to typed variable due to ImportError handling`

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-005 | BASE_RULES | Early returns to avoid nesting | ✅ OK - Try/except used correctly |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ FIXED - 2026-02-03 - Added exc_info=True for proper error logging |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ImportError caught |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ PARTIAL - `# type: ignore` used |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - No defaults in __init__ |

---

## Dependencies
- **External:** None (this is an __init__.py file)
- **Internal:** 
  - app.core.compliance_engine
  - app.core.compliance_integration
  - app.core.timezone_utils
  - app.core.config_loader
  - app.core.yaml_config_updater

---

## Required Tests
- **tests/unit/core/test_init.py:**
  - Test module imports successfully with all dependencies
  - Test module imports handles missing ComplianceEngine gracefully
  - Test __all__ exports are accessible
  - Test deprecated imports are available with warning

---

## Notes
- **ImportError Handling:** The module gracefully handles missing dependencies by setting components to None
- **Legacy Support:** Deprecated compliance_integration is still available but marked as deprecated
- **Phase 0.3:** Timezone utilities added for multi-market operations
- **Critical:** ComplianceEngine is marked as "THE ONLY Compliance Engine - USE THIS FOR EVERYTHING"

---
