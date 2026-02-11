# __init__.py - Strategy Configuration Module

## Purpose
Package initialization file that exports modular configuration classes for individual trading strategies. Enables importing strategy-specific configs (Momentum, Dividend, FX Carry) independently.

---

## Type Definitions / Data Classes

This is a package init file with no custom classes.

---

## Function Signatures (Contracts)

### Module Exports
```python
from .momentum_config import MomentumModularConfig
from .dividend_config import DividendStrategyConfig
from .fx_carry_config import FXCarryTradeStrategyConfig

__all__ = [
    "MomentumModularConfig",
    "DividendStrategyConfig",
    "FXCarryTradeStrategyConfig",
]
```

**Pre:** All imported config modules must exist and define their respective classes
**Post:** Module exposes the three strategy config classes via __all__
**Raises:** ImportError if any dependency module is missing
**Retry:** No
**Side Effects:** None (module-level imports only)

---

## Acceptance Criteria
- [ ] Module successfully imports all three config classes
- [ ] __all__ exactly matches the exported class names
- [ ] No circular imports exist
- [ ] Module can be imported without side effects

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | Clean package init file with proper exports. No issues found. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | BASE_RULES | Layered architecture dependencies inward | ✅ OK - Only imports from sibling modules |
| CFG-001 | BASE_RULES | Pydantic Settings for config | ✅ OK - All configs use Pydantic BaseModel |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ImportError propagated if modules missing |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All config classes are typed |
| FMT-001 | BASE_RULES | Black formatting | ✅ OK - Properly formatted |

---

## Dependencies
- **Internal:**
  - `.momentum_config.MomentumModularConfig`
  - `.dividend_config.DividendStrategyConfig`
  - `.fx_carry_config.FXCarryTradeStrategyConfig`

---

## Required Tests
- **tests/core/strategy_config/test_init.py:**
  - Test all three config classes are importable
  - Test __all__ contains expected exports
  - Test module has no side effects on import

---

## Notes
This is a pure package init file that only serves to aggregate exports. The actual configuration logic is in the individual config modules. No hardcoded values, all configuration is delegated to the specific strategy config classes.
