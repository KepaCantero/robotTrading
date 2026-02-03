# models.py

## Purpose
Define data models and value objects for the Fundamental Law of Active Management analysis, including IC metrics, breadth metrics, and strategy analysis components.

---

## Type Definitions / Data Classes

### FundamentalLawComponents Class/DataClass
```python
@dataclass(frozen=True)
class FundamentalLawComponents:
    information_ratio: Decimal        # REQUIRED - The Information Ratio (active return / tracking error)
    information_coefficient: Decimal  # REQUIRED - The Information Coefficient (forecasting skill)
    breadth: Decimal                  # REQUIRED - Number of independent bets per year
    breadth_sqrt: Decimal             # REQUIRED - Square root of breadth
    transfer_coefficient: Decimal     # REQUIRED - Implementation efficiency [0, 1]
```

**Validation Rules:**
- All components must be non-negative
- information_coefficient must be in [-1, 1] range
- transfer_coefficient should be in [0, 1] range
- validate() method verifies IR ≈ IC × √BR × TC within tolerance

### ICMetrics Class/DataClass
```python
@dataclass
class ICMetrics:
    ic: Decimal                          # REQUIRED - Pearson correlation coefficient
    ic_rank: Decimal                     # REQUIRED - Spearman rank correlation
    ic_decay: List[Decimal]              # REQUIRED - IC over forward horizons
    statistical_significance: float      # REQUIRED - P-value for H0: IC=0
    confidence_interval: Tuple[Decimal, Decimal]  # REQUIRED - 95% CI bounds
```

**Validation Rules:**
- ic must be in [-1, 1]
- ic_rank must be in [-1, 1]
- statistical_significance must be in [0, 1]
- confidence_interval[0] <= confidence_interval[1]

### BreadthMetrics Class/DataClass
```python
@dataclass
class BreadthMetrics:
    annual_breadth: Decimal              # REQUIRED - Total bets per year
    independence_factor: Decimal         # REQUIRED - Correlation adjustment [0, 1]
    effective_breadth: Decimal           # REQUIRED - annual_breadth × independence_factor
    notes: str = ""                      # OPTIONAL - Additional context
```

**Validation Rules:**
- All breadth values must be non-negative
- independence_factor must be in [0, 1]
- effective_breadth = annual_breadth × independence_factor

### StrategyAnalysis Class/DataClass
```python
@dataclass
class StrategyAnalysis:
    strategy_name: str                   # REQUIRED - Strategy identifier
    components: FundamentalLawComponents # REQUIRED - FL components for this strategy
    skill_level: str                     # REQUIRED - "excellent", "good", "fair", or "poor"
    breadth_assessment: str              # REQUIRED - "high", "medium", or "low"
    improvement_suggestions: List[str]   # OPTIONAL - Actionable recommendations
```

**Validation Rules:**
- skill_level must be one of: "excellent", "good", "fair", "poor"
- breadth_assessment must be one of: "high", "medium", "low"

---

## Function Signatures (Contracts)

### `FundamentalLawComponents.validate(tolerance: Decimal = Decimal("0.01")) -> bool`
**Pre:** All components are non-negative
**Post:** Returns True if IR ≈ IC × √BR × TC within tolerance
**Raises:** ValueError if any component is negative
**Retry:** No
**Side Effects:** None

### `FundamentalLawComponents.get_theoretical_ir() -> Decimal`
**Pre:** None
**Post:** Returns IC × √BR × TC
**Raises:** None
**Retry:** No
**Side Effects:** None

### `FundamentalLawComponents.get_efficiency_gap() -> Decimal`
**Pre:** None
**Post:** Returns theoretical_ir - information_ratio
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ICMetrics.is_significant(alpha: float = 0.05) -> bool`
**Pre:** alpha in (0, 1)
**Post:** Returns statistical_significance < alpha
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ICMetrics.get_skill_level() -> str`
**Pre:** None
**Post:** Returns "excellent" if IC>=0.05, "good" if IC>=0.03, "fair" if IC>=0.01, else "poor"
**Raises:** None
**Retry:** No
**Side Effects:** None

### `ICMetrics.get_signal_persistence() -> str`
**Pre:** ic_decay has at least 2 elements
**Post:** Returns "long", "medium", or "short" based on decay ratio
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BreadthMetrics.get_breadth_category() -> str`
**Pre:** None
**Post:** Returns "high" if BR>=1000, "medium" if BR>=100, else "low"
**Raises:** None
**Retry:** No
**Side Effects:** None

### `BreadthMetrics.get_breadth_sqrt() -> Decimal`
**Pre:** effective_breadth >= 0
**Post:** Returns √(effective_breadth) rounded to 2 decimals
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyAnalysis.get_improvement_plan() -> str`
**Pre:** None
**Post:** Returns formatted improvement suggestions
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyAnalysis.get_summary() -> str`
**Pre:** None
**Post:** Returns formatted summary of strategy analysis
**Raises:** None
**Retry:** No
**Side Effects:** None

### `StrategyAnalysis.get_ir_decomposition() -> dict`
**Pre:** None
**Post:** Returns dict with IR, IC, BR, TC contributions
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All dataclasses are frozen where appropriate (FundamentalLawComponents)
- [ ] FundamentalLawComponents validates the Fundamental Law equation
- [ ] ICMetrics skill levels follow industry thresholds (0.05, 0.03, 0.01)
- [ ] BreadthMetrics categories follow industry thresholds (1000, 100)
- [ ] All methods have proper type hints
- [ ] All numeric operations use Decimal for precision
- [ ] StrategyAnalysis generates actionable suggestions
- [ ] Value objects are immutable where appropriate

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
| **Notes** | All BASE_RULES verified. Data models file - no exception handling needed. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ OK - FundamentalLawComponents is frozen |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All methods have type hints |
| TYP-005 | BASE_RULES | Class attribute types | ✅ OK - All attributes typed |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear field names |
| TRD-001 | BASE_RULES | Validate mathematical relationships | ✅ OK - validate() method checks FL equation |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Each class has one purpose |

---

## Dependencies
- **External:** dataclasses, decimal, typing, math
- **Internal:** None

---

## Required Tests
- **tests/unit/analysis/test_fundamental_law_models.py:**
  - Test FundamentalLawComponents validation (success and failure)
  - Test FundamentalLawComponents get_theoretical_ir()
  - Test FundamentalLawComponents get_efficiency_gap()
  - Test ICMetrics is_significant() with various p-values
  - Test ICMetrics get_skill_level() threshold boundaries
  - Test ICMetrics get_signal_persistence() with decay patterns
  - Test BreadthMetrics get_breadth_category() thresholds
  - Test BreadthMetrics get_breadth_sqrt() calculation
  - Test StrategyAnalysis get_improvement_plan() formatting
  - Test StrategyAnalysis get_summary() output
  - Test StrategyAnalysis get_ir_decomposition() dictionary structure

---

## Notes
- Reference: Grinold & Kahn (2000), "Active Portfolio Management"
- Fundamental Law: IR = IC × √BR × TC
- frozen=True for FundamentalLawComponents ensures immutability of core metrics
