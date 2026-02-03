# breadth_calculator.py

## Purpose
Calculate and analyze strategy breadth, which measures the number of independent betting opportunities per year, a critical component of the Fundamental Law of Active Management.

---

## Type Definitions / Data Classes

### BreadthMetrics Class/DataClass (imported from models.py)
```python
@dataclass
class BreadthMetrics:
    annual_breadth: Decimal              # REQUIRED - Total bets per year
    independence_factor: Decimal         # REQUIRED - Correlation adjustment [0, 1]
    effective_breadth: Decimal           # REQUIRED - annual_breadth × independence_factor
    notes: str = ""                      # OPTIONAL - Additional context
```

**Validation Rules:**
- All values must be non-negative
- independence_factor must be in [0, 1]
- effective_breadth = annual_breadth × independence_factor

---

## Function Signatures (Contracts)

### `__init__() -> BreadthCalculator`
**Pre:** None
**Post:** BreadthCalculator initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_breadth(n_assets: int, rebalance_frequency: str, asset_correlation: Optional[pd.DataFrame] = None) -> BreadthMetrics`
**Pre:** n_assets > 0; rebalance_frequency in PERIODS_PER_YEAR keys
**Post:** Returns BreadthMetrics with calculated breadth
**Raises:** ValueError if invalid frequency or n_assets
**Retry:** No
**Side Effects:** None

### `calculate_independence_factor(correlation_matrix: pd.DataFrame) -> Decimal`
**Pre:** correlation_matrix is square NxN DataFrame
**Post:** Returns independence factor in [0, 1]
**Raises:** ValueError if matrix invalid or not square
**Retry:** No
**Side Effects:** None

### `calculate_from_returns(returns: pd.DataFrame, min_position: float = 0.01) -> BreadthMetrics`
**Pre:** returns has >=2 columns and >=2 rows
**Post:** Returns BreadthMetrics inferred from historical data
**Raises:** None
**Retry:** No
**Side Effects:** None

### `estimate_required_breadth(target_ir: Decimal, information_coefficient: Decimal, transfer_coefficient: Decimal = Decimal("1.0")) -> Decimal`
**Pre:** target_ir >= 0; IC > 0; TC > 0
**Post:** Returns required BR = (IR / (IC × TC))²
**Raises:** ValueError if IC or TC is zero/negative
**Retry:** No
**Side Effects:** None

### `calculate_optimal_breadth(information_coefficient: Decimal, transfer_coefficient: Decimal = Decimal("1.0"), max_ir: Decimal = Decimal("2.0")) -> Decimal`
**Pre:** IC > 0; TC > 0; max_ir > 0
**Post:** Returns breadth needed to achieve max_ir
**Raises:** None
**Retry:** No
**Side Effects:** None

### `decompose_breadth(returns: pd.DataFrame, positions: Optional[pd.DataFrame] = None) -> dict`
**Pre:** returns has >=2 columns
**Post:** Returns dict with breadth breakdown components
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Breadth calculation correctly multiplies periods_per_year × n_assets × independence_factor
- [ ] Independence factor uses upper triangle of correlation matrix (excludes diagonal)
- [ ] Invalid rebalance frequencies raise ValueError with list of valid options
- [ ] Correlation matrix validation checks for square shape
- [ ] Returns DataFrame inference handles both DatetimeIndex and numeric indices
- [ ] Required breadth calculation prevents division by zero
- [ ] Breadth decomposition returns all expected keys
- [ ] Periods per year constants are accurate (daily=252, weekly=52, etc.)
- [ ] Independence factor is clamped to [0, 1] range
- [ ] Notes field provides useful context about the calculation

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05 |
| **Auditor** | Claude Code (GAP Fix) |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. File uses explicit ValueError raising (no try/except needed). |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate mathematical relationships | ✅ OK - Independence formula validated |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError with descriptive messages |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ N/A - No try/except blocks (uses explicit ValueError) |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear variable and function names |
| PERF-002 | BASE_RULES | Use vectorized operations | ✅ OK - Uses pandas/numpy vectorized ops |
| TRD-007 | BASE_RULES | Document TRADING_DAYS | ✅ OK - Uses documented constants (PERIODS_PER_YEAR) |

---

## Dependencies
- **External:** numpy, pandas, decimal, logging, typing
- **Internal:** app.analysis.fundamental_law.models.BreadthMetrics, app.core.decimal_utils.to_decimal

---

## Required Tests
- **tests/unit/analysis/test_breadth_calculator.py:**
  - Test calculate_breadth with weekly frequency (success)
  - Test calculate_breadth with invalid frequency (raises ValueError)
  - Test calculate_breadth with n_assets <= 0 (raises ValueError)
  - Test calculate_independence_factor with uncorrelated assets (returns ~1.0)
  - Test calculate_independence_factor with perfect correlation (returns ~1/n)
  - Test calculate_independence_factor with non-square matrix (raises ValueError)
  - Test calculate_from_returns with DatetimeIndex (success)
  - Test calculate_from_returns with numeric index (success)
  - Test estimate_required_breadth (success)
  - Test estimate_required_breadth with zero IC (raises ValueError)
  - Test calculate_optimal_breadth (success)
  - Test decompose_breadth returns all expected keys (success)
  - Test BreadthMetrics category thresholds (boundary tests)

---

## Notes
- Reference: Grinold & Kahn (2000), "Active Portfolio Management", Chapter 9
- Independence factor formula: IF = 1 / (1 + avg_correlation × (n - 1))
- Periods per year: daily=252, weekly=52, biweekly=26, monthly=12, quarterly=4, annually=1
