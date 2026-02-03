# __init__.py (Domain Models)

## Purpose
Module initialization for domain models - exports all domain model classes (InputProfile, RiskConfig, StrategyType, TaxConfig, SystemConfiguration, enums, validators) with proper public API documentation.

---

## Type Definitions / Data Classes

### Module Exports (Public API)
```python
# From input_profile.py
InputProfile                          # REQUIRED - User investment parameters domain model
InputProfileValidator                 # REQUIRED - Validator for creating InputProfile from user input
InvestmentObjective                   # REQUIRED - Enum of investment objectives
RiskTolerance                         # REQUIRED - Enum of risk tolerance levels

# From risk_config.py
RiskConfig                            # REQUIRED - Risk parameters Pydantic model

# From strategy_type.py
StrategyType                          # REQUIRED - Enum of trading strategy types

# From system_configuration.py
SystemConfiguration                   # REQUIRED - Complete system configuration Pydantic model

# From tax_config.py
TaxConfig                             # REQUIRED - Tax optimization parameters Pydantic model
```

**Export Organization:**
- All domain models exported in `__all__` list
- Clear module docstring explaining domain models purpose
- Organized imports by source file
- No implementation details in `__init__.py`

---

## Function Signatures (Contracts)

### Module Import
**Pre:** None
**Post:** All domain model classes available via `from app.domain.models import ClassName`
**Raises:** ImportError if any submodule cannot be imported
**Retry:** N/A (module initialization)
**Side Effects:** Imports all domain model submodules

---

## Acceptance Criteria
- [ ] All domain models exported in `__all__` list
- [ ] Module docstring explains domain models purpose
- [ ] Imports organized by source file (input_profile, risk_config, strategy_type, system_configuration, tax_config)
- [ ] No implementation logic in `__init__.py` (only exports)
- [ ] All required classes exported: InputProfile, InputProfileValidator, InvestmentObjective, RiskTolerance, RiskConfig, StrategyType, SystemConfiguration, TaxConfig
- [ ] Module imports successfully without circular dependencies

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` for universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-003 | 05-architecture.md | Domain has no framework dependencies | ✅ OK - Pure domain imports |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK - Clear export names |
| MOD-001 | BASE_RULES.md | __init__.py exports public API | ✅ OK - Uses __all__ |
| MOD-002 | BASE_RULES.md | No implementation in __init__.py | ✅ OK - Only exports |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK - Module level, no functions |

---

## Dependencies
- **External:** None (module initialization only)
- **Internal:**
  - `.input_profile` (InputProfile, InputProfileValidator, InvestmentObjective, RiskTolerance)
  - `.risk_config` (RiskConfig)
  - `.strategy_type` (StrategyType)
  - `.system_configuration` (SystemConfiguration)
  - `.tax_config` (TaxConfig)

---

## Required Tests
- **test_models_init.py:**
  - Test all exports in `__all__` are importable
  - Test InputProfile can be imported from app.domain.models
  - Test RiskConfig can be imported from app.domain.models
  - Test StrategyType can be imported from app.domain.models
  - Test SystemConfiguration can be imported from app.domain.models
  - Test TaxConfig can be imported from app.domain.models
  - Test InvestmentObjective enum is accessible
  - Test RiskTolerance enum is accessible
  - Test InputProfileValidator is accessible
  - Test module has proper docstring
  - Test no circular imports exist

---

## Notes
- This is a pure module initialization file - no implementation logic
- Exports the complete public API for domain models
- Follows Python best practices for package organization
- All domain models are pure domain objects (no framework dependencies)
