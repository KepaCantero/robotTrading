# constants.py

## Purpose
Centralized configuration for all hardcoded constants in backtesting modules, replacing magic numbers with documented, configurable values for capital scale analysis and execution engine.

---

## Type Definitions / Data Classes

### CapitalScaleConstants Class
```python
@dataclass
class CapitalScaleConstants:
    DEFAULT_CAPITAL_LEVELS: List[Decimal]                         # REQUIRED - Capital tiers for analysis
    ADV_LIMIT_PCT_DEFAULT: Decimal                                # REQUIRED - 2% ADV rule (0.02)
    ADV_FILL_RATIO_REJECT_THRESHOLD: Decimal                      # REQUIRED - Reject fill < 50% (0.5)
    COMMISSION_IMPACT_WARNING_THRESHOLD: Decimal                  # REQUIRED - 15% warning (0.15)
    COMMISSION_IMPACT_CRITICAL_THRESHOLD: Decimal                 # REQUIRED - 20% reject (0.20)
    COMMISSION_IMPACT_OPTIMAL_THRESHOLD: Decimal                  # REQUIRED - 15% optimal (0.15)
    ALPHA_DEGRADATION_THRESHOLD: Decimal                          # REQUIRED - 50% max degradation (0.50)
    COMMISSION_MODELS: Dict[Decimal, Dict[str, Any]]              # REQUIRED - Commission by capital level
    SCALABILITY_ALPHA_DEGRADATION_MAX_POINTS: Decimal             # REQUIRED - 40 points max
    SCALABILITY_COMMISSION_MAX_POINTS: Decimal                    # REQUIRED - 30 points max
    SCALABILITY_STABILITY_MAX_POINTS: Decimal                     # REQUIRED - 30 points max
    COMMISSION_IMPACT_EXCELLENT_THRESHOLD: Decimal                # REQUIRED - <10% excellent (0.10)
    COMMISSION_IMPACT_GOOD_THRESHOLD: Decimal                     # REQUIRED - <15% good (0.15)
    COMMISSION_IMPACT_POOR_THRESHOLD: Decimal                     # REQUIRED - >=15% poor (0.15)
    WIN_RATE_STABILITY_PENALTY_FACTOR: Decimal                    # REQUIRED - 100x multiplier
```

**Validation Rules:**
- All Decimal values must be non-negative
- Threshold percentages expressed as decimals (0.15 = 15%)
- Capital levels sorted ascending: [1000, 5000, 10000, 50000, 100000]
- Commission model types: "fixed", "hybrid", "tiered"

### ExecutionEngineConstants Class
```python
@dataclass
class ExecutionEngineConstants:
    BASE_SLIPPAGE_BPS: Decimal                                    # REQUIRED - 5 bps base slippage
    OPTIMISTIC_SLIPPAGE_BPS: Decimal                              # REQUIRED - 2 bps optimistic
    STOP_SLIPPAGE_MULTIPLIER: Decimal                             # REQUIRED - 2x on stops
    VOLATILITY_MULTIPLIER: Decimal                                # REQUIRED - 2x for high volatility
    ENABLE_NEXT_DAY_EXECUTION: bool                               # REQUIRED - Signal at t, execute at t+1
```

**Validation Rules:**
- Slippage values in basis points (1 bps = 0.01%)
- Multipliers must be >= 1.0
- Boolean flag controls execution timing behavior

### BacktestingConstants Class
```python
@dataclass
class BacktestingConstants:
    capital_scale: CapitalScaleConstants                          # REQUIRED - Capital scale config
    execution: ExecutionEngineConstants                           # REQUIRED - Execution engine config
```

**Validation Rules:**
- Singleton instance `BACKTESTING_CONSTANTS` for easy import
- Convenience functions for backward compatibility

---

## Function Signatures (Contracts)

### `get_default_capital_levels() -> List[Decimal]`
**Pre:** None
**Post:** Returns copy of default capital levels [1000, 5000, 10000, 50000, 100000]
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (returns copy to prevent mutation)

### `get_commission_models() -> Dict[Decimal, Dict[str, Any]]`
**Pre:** None
**Post:** Returns copy of commission models by capital level
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (returns copy to prevent mutation)

### `get_base_slippage_bps() -> Decimal`
**Pre:** None
**Post:** Returns base slippage in basis points (5)
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

### `get_adv_limit_pct() -> Decimal`
**Pre:** None
**Post:** Returns default ADV limit as percentage (2% = 0.02)
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] No hardcoded secrets or sensitive data (SEC-001)
- [ ] All constants use Decimal type for financial precision (CC-001)
- [ ] Capital levels are sorted ascending
- [ ] Percentage values expressed as decimals (0.15 = 15%)
- [ ] Commission models have valid types: "fixed", "hybrid", "tiered"
- [ ] Singleton instance BACKTESTING_CONSTANTS is immutable
- [ ] Convenience functions return copies (prevent mutation)
- [ ] Slippage values in basis points (BPS) clearly documented
- [ ] Threshold values documented with business meaning

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage on all functions | ✅ OK |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ FIXED - 2026-02-03 - Created proper TypedDict definitionsDict[str, Any]` in COMMISSION_MODELS |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ NOT APPLIED - No exception handling needed (constants only) |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ NOT APPLIED - No error conditions (constants only) |
| ARCH-006 | BASE_RULES.md | Value objects immutable | ✅ FIXED - 2026-02-03 - Added frozen=True for immutability |
| TRD-003 | BASE_RULES.md | Position limits enforced | ✅ OK - ADV_LIMIT_PCT_DEFAULT |

**GAP Violations Found:**

1. **TYP-003** (P1 - High): Uses `Any` type in COMMISSION_MODELS
   - **Location**: Line 47: `COMMISSION_MODELS: Dict[Decimal, Dict[str, Any]]`
   - **Fix**: Define specific schema for commission models:
   ```python
   from typing import TypedDict, Literal

   class CommissionModel(TypedDict):
       type: Literal["fixed", "hybrid", "tiered"]
       cost: Optional[Decimal]
       rate: Optional[Decimal]
       min_cost: Optional[Decimal]
       brackets: Optional[List[Dict[str, Any]]]
       description: str

   COMMISSION_MODELS: Dict[Decimal, CommissionModel]
   ```

2. **ARCH-006** (P1 - High): dataclass not frozen, allowing mutation
   - **Location**: Lines 17, 109, 125 - All dataclasses lack `frozen=True`
   - **Issue**: Constants can be modified at runtime
   - **Fix**: Add `frozen=True` to all dataclasses:
   ```python
   @dataclass(frozen=True)
   class CapitalScaleConstants:
       ...
   ```

3. **Missing Validation** (P2): No validation for Decimal values
   - **Issue**: Negative percentages or invalid capital levels not validated
   - **Fix**: Add `__post_init__` validation:
   ```python
   def __post_init__(self):
       if any(level <= 0 for level in self.DEFAULT_CAPITAL_LEVELS):
           raise ValueError("Capital levels must be positive")
       if self.COMMISSION_IMPACT_CRITICAL_THRESHOLD < 0:
           raise ValueError("Thresholds must be non-negative")
   ```

4. **Magic Number in Tiered Pricing** (P2): Uses `float("inf")` for max volume
   - **Location**: Lines 71, 84
   - **Issue**: Should use Decimal for consistency
   - **Fix**: Use `Decimal("Infinity")` or define constant



**FIXED VIOLATIONS:**

✅ **TYP-003** (P1 - High): Dict[str, Any] replaced with proper TypedDict definitions - FIXED 2026-02-03
   - **Fixed**: Created specific TypedDict classes for all return types
   - **Implementation**: 
     - awesome_quant_integrator.py: QuantstatsMetrics, EmpyricalMetrics, PyfolioMetrics, AwesomeQuantMetricsDict, FallbackMetrics
     - report_generator.py: PeriodInfoDict, ConfigInfoDict, ReturnsDict, PerformanceDict, RiskDict, DetailedMetrics
     - professional_reporter.py: ChartDataDict, ChartDict, ReportSectionCharts
     - constants.py: FixedCommissionModel, HybridCommissionModel, TierBracket, TieredCommissionModel, CommissionModel
   - **Validation**: All files compile successfully with proper type hints
---

## Dependencies
- **External:** dataclasses, decimal, typing (stdlib)
- **Internal:** None (standalone constants module)

---

## Required Tests
- **tests/unit/backtesting/test_constants.py:**
  - Test BACKTESTING_CONSTANTS singleton is accessible
  - Test get_default_capital_levels returns correct list
  - Test get_default_capital_levels returns copy (mutation doesn't affect original)
  - Test get_commission_models returns copy (mutation doesn't affect original)
  - Test get_base_slippage_bps returns 5
  - Test get_adv_limit_pct returns 0.02 (2%)
  - Test commission models have all required fields
  - Test commission model types are valid (fixed, hybrid, tiered)
  - Test capital levels are sorted ascending
  - Test percentage thresholds are documented (0.15 = 15%)
  - Test slippage values in basis points (BPS)
  - Test execution timing flag (ENABLE_NEXT_DAY_EXECUTION)

---

## Notes
- **Centralized Constants**: Replaces magic numbers across capital_scale_analyzer.py and execution_engine.py
- **Decimal Type**: All financial values use Decimal for precision (not float)
- **Singleton Pattern**: `BACKTESTING_CONSTANTS` provides easy import access
- **Backward Compatibility**: Convenience functions (`get_default_capital_levels()`, etc.) maintain existing API
- **Immutability Issue**: dataclasses not frozen, allowing runtime mutation (should add `frozen=True`)
- **Commission Models**: Three-tier pricing structure (fixed, hybrid, tiered) by capital level
- **ADV Rule**: 2% of Average Daily Volume limit prevents market impact
- **Slippage**: 5 bps base, 2 bps optimistic, 2x multiplier on stop orders
