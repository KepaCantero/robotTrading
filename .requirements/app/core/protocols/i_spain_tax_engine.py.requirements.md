# i_spain_tax_engine.py

## Purpose
Protocol interface for Spain tax calculations. Defines contract for IRPF capital gains tax (19/21/23% progressive), dividend withholding (EU 0% vs non-EU 19%), and Modelo 720 reporting (>€50k foreign assets).

---

## Type Definitions / Data Classes

### ISpainTaxEngine (Protocol)
```python
class ISpainTaxEngine(Protocol):
    def calculate_capital_gains_tax(self, profit: Decimal) -> Decimal:
        """IRPF-001: Progresivo 19/21/23%"""

    def calculate_dividend_tax(self, symbol: str, amount: Decimal) -> Decimal:
        """DIV-001: UE 0% vs No-UE 19%"""

    def is_eu_country(self, symbol: str) -> bool:
        """Verificar si país es UE"""

    def check_modelo_720_threshold(self, foreign_assets: Decimal) -> bool:
        """MOD720-001: > €50k extranjeros"""

    def generate_modelo_720_report(self) -> dict:
        """Generar reporte Modelo 720"""
```

**Contract Rules:**
- Methods are NOT async (synchronous tax calculations)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (Decimal, bool, dict)
- 5 methods maximum (as noted in class docstring)
- IRPF-001, DIV-001, MOD720-001 compliance for Spain tax rules

---

## Function Signatures (Contracts)

### `calculate_capital_gains_tax(profit: Decimal) -> Decimal`
**Pre:** profit must be non-negative Decimal
**Post:** Returns tax amount based on IRPF progressive rates (19/21/23%)
**Raises:** NotImplementedError if not implemented, ValueError if profit negative
**Retry:** No
**Side Effects:** None (pure calculation function)
**Rates:**
- 19% for profits up to €X threshold
- 21% for profits €X to €Y
- 23% for profits above €Y

### `calculate_dividend_tax(symbol: str, amount: Decimal) -> Decimal`
**Pre:** symbol must be valid ticker, amount must be positive Decimal
**Post:** Returns withholding tax amount (0% for EU, 19% for non-EU)
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May call external API for country verification
**Side Effects:** None (pure calculation function)
**DIV-001 Rule:** EU dividends = 0% withholding, non-EU = 19%

### `is_eu_country(symbol: str) -> bool`
**Pre:** symbol must be valid ticker
**Post:** Returns True if company is incorporated in EU country, False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May query external data source
**Side Effects:** None (read-only lookup)

### `check_modelo_720_threshold(foreign_assets: Decimal) -> bool`
**Pre:** foreign_assets must be non-negative Decimal in EUR
**Post:** Returns True if foreign assets > €50,000 (MOD720-001 threshold), False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (pure comparison function)

### `generate_modelo_720_report() -> dict`
**Pre:** Foreign asset data must be available
**Post:** Returns dictionary with Modelo 720 report data (breakdown by asset type, country, etc.)
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (pure data generation function)
**MOD720-001 Rule:** Must report foreign assets >€50k to Hacienda annually

---

## Acceptance Criteria
- [ ] All 5 methods are defined as def (not async - tax calc is synchronous)
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified (Decimal, bool, dict)
- [ ] Methods align with IRPF-001, DIV-001, MOD720-001 requirements
- [ ] calculate_capital_gains_tax uses progressive rates (19/21/23%)
- [ ] calculate_dividend_tax distinguishes EU (0%) vs non-EU (19%)
- [ ] check_modelo_720_threshold uses €50,000 threshold
- [ ] Implementations handle EUR/USD currency conversions for foreign assets

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 1 P3 |
| **Notes** | Well-defined Protocol interface for Spain tax compliance. IRPF/DIV/Mod720 rules properly documented. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| IRPF-001 | SERVICE_REQUIREMENTS | IRPF Progresivo 19/21/23% | ✅ OK - calculate_capital_gains_tax |
| DIV-001 | SERVICE_REQUIREMENTS | Dividendos UE 0% vs No-UE 19% | ✅ OK - calculate_dividend_tax, is_eu_country |
| MOD720-001 | SERVICE_REQUIREMENTS | Modelo 720 >€50k extranjeros | ✅ OK - check_modelo_720_threshold, generate_modelo_720_report |
| SEC-005 | BASE_RULES | Audit logging | ⚠️ P3 - Should specify logging requirements |
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused tax methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ P3 - Add type hints for dict return |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Method names clearly describe purpose |

---

## Dependencies
- **External:** typing (Protocol)
- **Internal:** decimal (Decimal)

---

## Required Tests
- **tests/core/protocols/test_i_spain_tax_engine.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required (NotImplementedError raised)
  - Test methods can be called on mock implementation
  - Test IRPF-001: calculate_capital_gains_tax uses correct rates
  - Test DIV-001: calculate_dividend_tax for EU (0%) vs non-EU (19%)
  - Test MOD720-001: check_modelo_720_threshold at €50,000 boundary
  - Test is_eu_country returns correct boolean
  - Test generate_modelo_720_report returns dict structure

---

## Notes

**P3 - Type hints for dict return:**
```python
# CURRENT:
def generate_modelo_720_report(self) -> dict:

# SUGGESTED:
from typing import Any
def generate_modelo_720_report(self) -> dict[str, Any]:
```

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Motor de impuestos España") but file-level comments use English. Consider standardizing to English for consistency with rest of codebase.

**Trading Context:** This Protocol implements Spain-specific tax rules:
- **IRPF-001**: Progressive capital gains tax (19% up to €X, 21% €X-€Y, 23% above €Y)
- **DIV-001**: Dividend withholding (0% for EU companies, 19% for non-EU)
- **MOD720-001**: Modelo 720 declaration required for foreign assets >€50,000 (annual reporting to Hacienda)

These rules are mandatory for Spanish tax residents trading foreign assets.
