# fundamental_law.py

## Purpose
Implement the Fundamental Law of Active Management calculator, decomposing Information Ratio into skill (IC), breadth (BR), and transfer coefficient (TC) components to evaluate and improve trading strategies.

---

## Type Definitions / Data Classes

### FundamentalLawComponents (imported from models.py)
```python
@dataclass(frozen=True)
class FundamentalLawComponents:
    information_ratio: Decimal        # REQUIRED - The Information Ratio
    information_coefficient: Decimal  # REQUIRED - Forecasting skill
    breadth: Decimal                  # REQUIRED - Independent bets per year
    breadth_sqrt: Decimal             # REQUIRED - √BR
    transfer_coefficient: Decimal     # REQUIRED - Implementation efficiency [0, 1]
```

### StrategyAnalysis (imported from models.py)
```python
@dataclass
class StrategyAnalysis:
    strategy_name: str                   # REQUIRED - Strategy identifier
    components: FundamentalLawComponents # REQUIRED - FL components
    skill_level: str                     # REQUIRED - Assessment category
    breadth_assessment: str              # REQUIRED - Breadth category
    improvement_suggestions: List[str]   # OPTIONAL - Recommendations
```

---

## Function Signatures (Contracts)

### `__init__() -> FundamentalLawCalculator`
**Pre:** None
**Post:** Calculator initialized with ICCalculator and BreadthCalculator
**Raises:** None
**Retry:** No
**Side Effects:** Instantiates ICCalculator and BreadthCalculator

### `calculate_fundamental_law(information_ratio: Decimal, information_coefficient: Decimal, breadth: Decimal, transfer_coefficient: Decimal = Decimal("1.0")) -> FundamentalLawComponents`
**Pre:** information_ratio >= 0; IC in [-1, 1]; breadth >= 0; TC in [0, 1]
**Post:** Returns FundamentalLawComponents with √BR calculated
**Raises:** ValueError if any input is invalid
**Retry:** No
**Side Effects:** None

### `decompose_ir(returns: pd.Series, forecasts: pd.Series, benchmark_returns: pd.Series, rebalance_frequency: str = "monthly") -> FundamentalLawComponents`
**Pre:** All Series have same length >= 2; DatetimeIndex recommended
**Post:** Returns components with IR, IC, BR, TC decomposed from data
**Raises:** ValueError if series lengths differ or insufficient data
**Retry:** No
**Side Effects:** None

### `analyze_strategy(components: FundamentalLawComponents, strategy_name: str) -> StrategyAnalysis`
**Pre:** components.validate() returns True
**Post:** Returns StrategyAnalysis with skill/breadth assessments and suggestions
**Raises:** None
**Retry:** No
**Side Effects:** None

### `compare_strategies(strategies: dict[str, FundamentalLawComponents]) -> pd.DataFrame`
**Pre:** strategies dict has at least 1 entry
**Post:** Returns DataFrame with comparison metrics indexed by strategy name
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_required_ic_for_target_ir(target_ir: Decimal, breadth: Decimal, transfer_coefficient: Decimal = Decimal("1.0")) -> Decimal`
**Pre:** target_ir >= 0; breadth > 0; transfer_coefficient > 0
**Post:** Returns required IC = IR / (√BR × TC), clamped to [-1, 1]
**Raises:** ValueError if denominator is zero
**Retry:** No
**Side Effects:** None

### `_calculate_breadth_sqrt(breadth: Decimal) -> Decimal`
**Pre:** breadth >= 0
**Post:** Returns √(breadth) rounded to 4 decimals
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> Decimal`
**Pre:** Series have same length >= 2
**Post:** Returns annualized IR = mean(active_return) / std(active_return) × √252
**Raises:** ValueError if insufficient data or zero tracking error
**Retry:** No
**Side Effects:** None

### `_estimate_periods_per_year(returns: pd.Series) -> float`
**Pre:** returns is a Series with index
**Post:** Returns estimated trading periods per year
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_assess_skill_level(ic: Decimal) -> str`
**Pre:** ic >= 0
**Post:** Returns "excellent" if IC>=0.05, "good" if IC>=0.03, "fair" if IC>=0.01, else "poor"
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_assess_breadth(breadth: Decimal) -> str`
**Pre:** breadth >= 0
**Post:** Returns "high" if BR>=1000, "medium" if BR>=100, else "low"
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_assess_ir(ir: Decimal) -> str`
**Pre:** ir >= 0
**Post:** Returns "excellent" if IR>=1.0, "good" if IR>=0.5, "fair" if IR>=0.25, else "poor"
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_assess_tc(tc: Decimal) -> str`
**Pre:** tc in [0, 1]
**Post:** Returns "excellent" if TC>=0.8, "good" if TC>=0.6, "fair" if TC>=0.4, else "poor"
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_generate_suggestions(...) -> List[str]`
**Pre:** All assessment inputs are valid
**Post:** Returns list of actionable improvement suggestions
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Fundamental Law equation IR = IC × √BR × TC is validated
- [ ] IR calculation annualizes using √252 for daily data
- [ ] Negative IR is handled by clamping to 0 or using absolute IC
- [ ] Transfer coefficient is clamped to [0, 1] range
- [ ] Breadth sqrt is calculated accurately with proper rounding
- [ ] Strategy analysis provides specific, actionable suggestions
- [ ] All edge cases (zero TE, insufficient data, negative values) are handled
- [ ] Comparison DataFrame includes all relevant metrics
- [ ] Required IC calculation prevents division by zero
- [ ] Periods per year estimation handles non-DatetimeIndex

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
| TRD-001 | BASE_RULES | Validate mathematical relationships | ✅ OK - Validates FL equation |
| TRD-007 | BASE_RULES | Document TRADING_DAYS constant | ✅ OK - Comments document the 252 annualization factor |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError with messages |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ N/A - No try/except blocks (uses explicit ValueError) |
| SOL-004 | BASE_RULES | Interface segregation | ✅ OK - Focused public methods |
| DP-004 | BASE_RULES | Dependency injection | ✅ OK - ICCalculator/BreadthCalculator via __init__ |

---

## Dependencies
- **External:** numpy, pandas, decimal, logging, typing
- **Internal:** 
  - app.analysis.fundamental_law.ic_calculator.ICCalculator
  - app.analysis.fundamental_law.breadth_calculator.BreadthCalculator
  - app.analysis.fundamental_law.models.FundamentalLawComponents, StrategyAnalysis
  - app.core.decimal_utils.to_decimal

---

## Required Tests
- **tests/unit/analysis/test_fundamental_law_calculator.py:**
  - Test calculate_fundamental_law with valid inputs (success)
  - Test calculate_fundamental_law with invalid IR (raises ValueError)
  - Test calculate_fundamental_law with IC outside [-1, 1] (raises ValueError)
  - Test decompose_ir with realistic data (success)
  - Test decompose_ir with mismatched series lengths (raises ValueError)
  - Test analyze_strategy with good strategy (success)
  - Test analyze_strategy with poor strategy (generates suggestions)
  - Test compare_strategies with multiple strategies (success)
  - Test calculate_required_ic_for_target_ir (success)
  - Test calculate_required_ic with zero denominator (raises ValueError)
  - Test _calculate_information_ratio annualization (success)
  - Test _calculate_information_ratio with zero TE (returns 0)
  - Test assessment functions with various thresholds (boundary tests)

---

## Notes
- Reference: Grinold & Kahn (2000), "Active Portfolio Management", Chapter 9
- Fundamental Law: IR = IC × √BR × TC
- Annualization assumes 252 trading days (hardcoded, consider extracting to constant)
