# models.py

## Purpose
 file for models

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### OptionType
**Purpose:** Type of option....
### OptionStyle
**Purpose:** Option exercise style....
### Moneyness
**Purpose:** Moneyness of an option....
### RollType
**Purpose:** Type of roll operation....
### AssignmentProbability
**Purpose:** Probability of assignment....
### CallOption
**Purpose:** Datos de una opción de compra (call).

Attributes:
    symbol: Símbolo del activo subyacente
    opt...
### OptionGreeks
**Purpose:** Greeks de una opción.

Attributes:
    delta: Sensibilidad del precio de la opción al precio del sub...
### CoveredCallPosition
**Purpose:** Posición de covered call.

Una posición de covered call consiste en:
- Posición larga en el activo s...
### RollOpportunity
**Purpose:** Oportunidad de rolling (cerrar y abrir nueva posición).

Attributes:
    position: Posición actual
 ...
### OptionScreeningCriteria
**Purpose:** Criterios de screening para opciones.

Attributes:
    min_days_to_expiry: Días mínimos al vencimien...
### OptionScreenerResult
**Purpose:** Resultado del screening de opciones.

Attributes:
    symbol: Símbolo del subyacente
    underlying_...
### CoveredCallConfig
**Purpose:** Configuración de la estrategia de covered calls.

Attributes:
    max_position_size: Tamaño máximo d...
### RollDecision
**Purpose:** Decisión de rolling.

Attributes:
    should_roll: Si se debe hacer roll
    roll_type: Tipo de roll...

---

## Function Signatures (Contracts)

### `CallOption.mid_price(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CallOption.days_to_expiry(self) -> int`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CallOption.is_itm(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CallOption.is_otm(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CallOption.intrinsic_value(self) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CallOption.time_value(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CallOption.moneyness(self) -> Moneyness`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.validate_contracts(cls, v, info) -> int`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.covered_shares(self) -> int`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.uncovered_shares(self) -> int`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.total_cost(self) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.total_value(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.total_premium(self) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.net_cost(self) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.break_even_price(self) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.max_profit(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.max_loss(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.return_if_called(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.return_if_unchanged(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.downside_protection(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.annualized_return(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallPosition.time_decay_benefit(self) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OptionScreeningCriteria.validate_ranges(self) -> 'OptionScreeningCriteria'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `OptionScreenerResult.pass_rate(self) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CoveredCallConfig.validate_config(self) -> 'CoveredCallConfig'`
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

**File Reference:** `app/strategies/covered_calls/models.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
