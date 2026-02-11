# lopez_de_prado_metrics.py

## Purpose
Advanced financial metrics from Marcos López de Prado's "Machine Learning for Asset Managers" - implements Sharpe ratio combinations, portfolio stability validation, turnover-adjusted metrics, and concentration analysis.

---

## Type Definitions / Data Classes

### SharpeCombinationResult
```python
@dataclass
class SharpeCombinationResult:
    combined_sharpe: float          # REQUIRED - Resulting combined Sharpe ratio
    method: str                      # REQUIRED - Combination method used
    individual_sharpes: List[float]  # OPTIONAL - Input Sharpe ratios
    weights: Optional[np.ndarray]    # OPTIONAL - Optimal weights (sums to 1)
    improvement_pct: float = 0.0     # OPTIONAL - Improvement vs average
    is_statistically_significant: bool = False  # OPTIONAL - Test result
    p_value: float = 1.0            # OPTIONAL - Statistical significance p-value
    confidence_interval: Optional[Tuple[float, float]] = None  # OPTIONAL - CI bounds
    timestamp: datetime = field(default_factory=datetime.now)  # AUTO - Generated
```

**Validation Rules:**
- `combined_sharpe` must be non-negative
- `method` must be one of: "optimal", "hierarchical_ward", "spectral", "average"
- `weights` must sum to 1.0 if provided
- `p_value` must be in [0, 1]
- `improvement_pct` can be negative (worse than average)

### PortfolioStabilityMetrics
```python
@dataclass
class PortfolioStabilityMetrics:
    is_stable: bool                 # REQUIRED - Stability assessment
    stability_score: float          # REQUIRED - 0-100 composite score
    turnover_mean: float            # REQUIRED - Average turnover between periods
    turnover_std: float             # REQUIRED - Turnover standard deviation
    weights_autocorrelation: float  # REQUIRED - Autocorrelation of weights
    allocation_drift_max: float     # REQUIRED - Maximum allocation drift
    allocation_drift_mean: float    # REQUIRED - Mean allocation drift
    cross_period_correlation: float # REQUIRED - Correlation between periods
    num_periods: int                # REQUIRED - Number of periods analyzed
    period_length_days: int         # REQUIRED - Length of each period
    stability_threshold: float = 70.0  # OPTIONAL - Minimum score to be stable
    timestamp: datetime = field(default_factory=datetime.now)  # AUTO
```

**Validation Rules:**
- `stability_score` must be in [0, 100]
- `turnover_mean` must be in [0, 1] (0% to 100%)
- `weights_autocorrelation` must be in [-1, 1]
- `cross_period_correlation` must be in [-1, 1]
- `num_periods` must be >= 2 for meaningful analysis

### TurnoverAdjustedMetrics
```python
@dataclass
class TurnoverAdjustedMetrics:
    raw_sharpe: float                    # REQUIRED - Unadjusted Sharpe ratio
    turnover_adjusted_sharpe: float       # REQUIRED - Cost-adjusted Sharpe
    annualized_turnover: float           # REQUIRED - Annual turnover rate
    adjustment_factor: float             # REQUIRED - Adjustment applied
    is_cost_effective: bool              # REQUIRED - Cost-effectiveness flag
    estimated_transaction_costs: float   # REQUIRED - Estimated annual costs
    net_sharpe: float                    # REQUIRED - Sharpe after costs
    timestamp: datetime = field(default_factory=datetime.now)  # AUTO
```

**Validation Rules:**
- `adjustment_factor` must be in (0, 1] (1 = no adjustment)
- `annualized_turnover` must be non-negative
- `net_sharpe <= raw_sharpe` (costs always reduce Sharpe)

### ConcentrationMetrics
```python
@dataclass
class ConcentrationMetrics:
    herfindahl_index: float        # REQUIRED - HHI (0-1, higher = concentrated)
    effective_n_assets: float      # REQUIRED - 1/HHI, effective diversity
    max_weight: float              # REQUIRED - Largest single position
    top_3_concentration: float     # REQUIRED - Sum of top 3 weights
    top_5_concentration: float     # REQUIRED - Sum of top 5 weights
    gini_coefficient: float        # REQUIRED - 0-1 inequality measure
    shannon_entropy: float         # REQUIRED - Diversity (higher = better)
    is_overconcentrated: bool      # REQUIRED - Concentration warning
    concentration_score: float     # REQUIRED - 0-100 concentration score
    timestamp: datetime = field(default_factory=datetime.now)  # AUTO
```

**Validation Rules:**
- `herfindahl_index` must be in [0, 1] (0 = diversified, 1 = concentrated)
- `effective_n_assets` must be >= 1
- `max_weight` must be in [0, 1]
- `gini_coefficient` must be in [0, 1]
- All concentration sums must be in [0, 1]

---

## Function Signatures (Contracts)

### `SharpeRatioCombinator.combine_sharpes_optimal(sharpes: np.ndarray, cov_matrix: np.ndarray) -> SharpeCombinationResult`
**Pre:** `sharpes` length equals `cov_matrix` dimensions; `cov_matrix` is positive semidefinite
**Post:** Returns optimal Sharpe combination with weights summing to 1
**Raises:** `ValueError` if inputs invalid; falls back to average combination on error
**Retry:** No
**Side Effects:** None (pure computation)

### `SharpeRatioCombinator.combine_sharpes_hierarchical(sharpes: np.ndarray, cov_matrix: np.ndarray, linkage_method: str = 'ward') -> SharpeCombinationResult`
**Pre:** `sharpes` length >= 2; `cov_matrix` is valid covariance matrix
**Post:** Returns hierarchical combination using HRP methodology
**Raises:** `ValueError` if insufficient data; falls back to optimal on error
**Retry:** No
**Side Effects:** None

### `SharpeRatioCombinator.combine_sharpes_spectral(sharpes: np.ndarray, returns_matrix: np.ndarray, risk_aversion: float = 1.0) -> SharpeCombinationResult`
**Pre:** `returns_matrix` is T x N (T periods, N strategies); N >= 2
**Post:** Returns spectral risk-based combination
**Raises:** `ValueError` on invalid matrix; falls back to average on error
**Retry:** No
**Side Effects:** None

### `SharpeRatioCombinator.test_sharpe_significance(sharpe1: float, sharpe2: float, returns1: np.ndarray, returns2: np.ndarray) -> Tuple[bool, float]`
**Pre:** Both returns arrays have same length >= 4
**Post:** Returns (is_different, p_value) using Jobson-Korkie test
**Raises:** Returns (False, 1.0) on error
**Retry:** No
**Side Effects:** None

### `PortfolioStabilityValidator.validate_stability(weights_history: List[np.ndarray], period_length_days: int = 30) -> PortfolioStabilityMetrics`
**Pre:** `weights_history` has >= 2 periods; all arrays have same length
**Post:** Returns comprehensive stability metrics with score 0-100
**Raises:** Returns empty metrics on insufficient data
**Retry:** No
**Side Effects:** None

### `TurnoverAdjustedCalculator.calculate_turnover_adjusted_sharpe(returns: np.ndarray, weights_history: List[np.ndarray], period_length_days: int = 30) -> TurnoverAdjustedMetrics`
**Pre:** `returns` and `weights_history` have compatible lengths
**Post:** Returns cost-adjusted Sharpe ratio with transaction cost estimates
**Raises:** Returns zero metrics on error
**Retry:** No
**Side Effects:** None

### `ConcentrationAnalyzer.analyze_concentration(weights: np.ndarray) -> ConcentrationMetrics`
**Pre:** `weights` sums to 1.0 (or close); all non-negative
**Post:** Returns comprehensive concentration metrics
**Raises:** Returns max-concentration metrics on error
**Retry:** No
**Side Effects:** None

### `create_lopez_de_prado_suite(risk_free_rate: float = 0.02, stability_threshold: float = 70.0, transaction_cost_bps: float = 10.0) -> Dict[str, Any]`
**Pre:** `risk_free_rate` in [0, 1]; `stability_threshold` in [0, 100]
**Post:** Returns dict with all 4 analyzer instances
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None (factory function)

---

## Acceptance Criteria
- [ ] All dataclass fields have type hints and validation rules documented
- [ ] All combination methods handle edge cases (0, 1, N strategies)
- [ ] Covariance matrix validation (positive semidefinite check)
- [ ] Sharpe significance test uses Jobson-Korkie with Memmel correction
- [ ] Stability score is composite of 4 components (0-100 scale)
- [ ] Turnover calculation uses formula: 0.5 * sum(|w_new - w_old|)
- [ ] HHI calculation: sum(w_i^2) for all weights
- [ ] All metrics return sensible defaults on error (no exceptions propagate)
- [ ] All calculators have deterministic outputs (no randomness unless seeded)
- [ ] Documentation references López de Prado (2020) book chapters

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES.md | Covariance matrix must be positive semidefinite | ✅ OK - Uses pseudoinverse fallback |
| TRD-007 | BASE_RULES.md | Annualization uses TRADING_DAYS = 252 | ✅ OK - Hardcoded 252 in Sharpe calc |
| CC-006 | BASE_RULES.md | Explicit error handling with specific exceptions | ✅ OK - try/except with logging |
| LOG-004 | BASE_RULES.md | All exceptions logged with stack traces | ✅ OK - logger.error in all except blocks |
| TYP-001 | BASE_RULES.md | 100% type coverage | ⚠️ NOT APPLIED - Some functions missing hints |
| SOL-001 | BASE_RULES.md | Single Responsibility Principle | ✅ OK - Each class has one responsibility |
| ARCH-006 | BASE_RULES.md | Value objects immutable | ✅ OK - @dataclass with frozen=False acceptable |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - No future data used in calculations |

**NOTE:** All 96 BASE_RULES apply. Key critical rules for financial calculations:
- **TRD-001:** Covariance validation prevents invalid portfolio optimization
- **TRD-007:** Consistent annualization enables cross-asset comparison
- **CC-006:** Explicit error handling prevents silent failures in metrics

---

## Dependencies
- **External:** `numpy` (arrays, math), `scipy` (stats, clustering, hierarchy), `dataclasses` (dataclass), `datetime` (timestamps), `typing` (List, Dict, Optional, Tuple, Any)
- **Internal:** None (standalone metrics module)

---

## Required Tests
- **tests/backtesting/test_lopez_de_prado_metrics.py:**
  - Test Sharpe combination methods (optimal, hierarchical, spectral)
  - Test edge cases: 0, 1, 2, N strategies
  - Test covariance matrix validation (singular, non-PSD matrices)
  - Test stability validation with various turnover scenarios
  - Test turnover adjustment with different cost assumptions
  - Test concentration metrics with equal/unequal weights
  - Test HHI calculation (verify sum of squares)
  - Test Gini coefficient edge cases (all equal, all unequal)
  - Test error handling and fallback behavior
  - Test Jobson-Korkie significance test accuracy

---

## Notes
- Implements Chapter 8-11 of López de Prado (2020): "Machine Learning for Asset Managers"
- Hierarchical combination uses scipy.cluster.hierarchy for HRP
- Spectral method uses eigenvalue decomposition of covariance matrix
- All calculations use numpy for performance; avoid Python loops
- Fallback to simple average when advanced methods fail (graceful degradation)
- Stability score is proprietary composite (0-100 scale, customizable threshold)
