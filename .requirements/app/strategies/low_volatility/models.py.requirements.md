# models.py

## Purpose
 file for models

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### SectorDefensiveLevel
**Purpose:** Nivel defensivo de un sector....
### VolatilityRegime
**Purpose:** Régimen de volatilidad del mercado....
### VolatilityMetrics
**Purpose:** Métricas de volatilidad de una acción.

Attributes:
    symbol: Símbolo de la acción
    historical_...
### LowVolatilityProfile
**Purpose:** Perfil completo de baja volatilidad de una acción.

Combina métricas de volatilidad con datos fundam...
### LowVolatilityStock
**Purpose:** Acción de baja volatilidad con datos para toma de decisiones.

Extiende LowVolatilityProfile con sco...
### LowVolatilityStrategyConfig
**Purpose:** Configuración de la estrategia de baja volatilidad.

Define parámetros para screening, análisis y co...
### LowVolatilityScreeningCriteria
**Purpose:** Criterios de screening des-normalizados desde config....
### ScreeningResult
**Purpose:** Resultado del screening de baja volatilidad.

Attributes:
    passed_stocks: Lista de acciones que p...

---

## Function Signatures (Contracts)

### `VolatilityMetrics.average_volatility(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `VolatilityMetrics.is_low_volatility(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `VolatilityMetrics.volatility_score(self) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LowVolatilityProfile.overall_score(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LowVolatilityProfile.is_defensive_stock(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LowVolatilityStrategyConfig.validate_weights_sum(self) -> 'LowVolatilityStrategyConfig'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LowVolatilityStrategyConfig.validate_volatility_range(self) -> 'LowVolatilityStrategyConfig'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LowVolatilityStrategyConfig.get_screening_description(self) -> str`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ScreeningResult.pass_rate(self) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD


---

## Acceptance Criteria
- [ ] **AC-001:** All public methods have complete type hints ✅ OK
- [ ] **AC-002:** NumPy 2.0 compatibility ✅ OK
- [ ] **AC-003:** All functions have docstrings following Google style ✅ OK
- [ ] **AC-004:** Input validation on all public methods ⚠️ PENDING

---

## Audit Status

**Status:** PENDING
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** TBD
**Notes:** Requirements document created. Needs full audit against code.

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ⚠️ PENDING - Needs audit |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ⚠️ PENDING - Needs audit |
| Input validation | BASE_RULES.md (CC-006) | Validate all inputs | ⚠️ PENDING - Needs audit |
| Error logging | BASE_RULES.md (LOG-004) | Log exceptions with stack traces | ⚠️ PENDING - Needs audit |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ⚠️ PENDING - Needs audit |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** TBD (needs audit)
- **Internal:** TBD (needs audit)

---

## Required Tests
- **test_models.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/strategies/low_volatility/models.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
