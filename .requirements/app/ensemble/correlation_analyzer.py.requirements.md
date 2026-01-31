# correlation_analyzer.py

## Purpose
Analyze correlations between trading strategies to identify redundancy and measure diversification quality.

---

## Type Definitions / Data Classes

### CorrelationAnalyzer Class
```python
class CorrelationAnalyzer:
    strategies: List[str]                     # List of strategy names (min 2)
    correlation_threshold: float              # Threshold for redundancy detection (0-1)
    method: str                               # Correlation method: "pearson", "spearman", "kendall"
```

---

## Function Signatures (Contracts)

### `__init__(strategies, correlation_threshold, method) -> None`
**Pre:** strategies length >= 2, method in ["pearson", "spearman", "kendall"]
**Post:** Analyzer initialized with specified method
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `analyze_correlations(returns_data) -> CorrelationMetrics`
**Pre:** returns_data has all strategies, each array length >= 2
**Post:** Returns CorrelationMetrics with matrix, stats, redundancy
**Raises:** ValueError if data missing/invalid, RuntimeError if analysis fails
**Retry:** No
**Side Effects:** None

### `_calculate_correlation_matrix(returns_data) -> np.ndarray`
**Pre:** returns_data has matching length arrays
**Post:** Returns n x n correlation matrix (diagonal = 1.0)
**Raises:** None (returns identity matrix on error)
**Retry:** No
**Side Effects:** None

### `_detect_redundant_pairs(corr_matrix) -> List[Tuple[str, str, float]]`
**Pre:** corr_matrix is n x n numpy array
**Post:** Returns list of (strat1, strat2, corr) where abs(corr) >= threshold
**Raises:** None (returns [] on error)
**Retry:** No
**Side Effects:** None

### `_calculate_effective_number_bets(corr_matrix) -> float`
**Pre:** corr_matrix is n x n correlation matrix
**Post:** Returns n / (1 + (n-1) * avg_correlation)
**Raises:** None (returns n on error)
**Retry:** No
**Side Effects:** None

### `_calculate_eigenvalues(corr_matrix) -> List[float]`
**Pre:** corr_matrix is symmetric n x n matrix
**Post:** Returns eigenvalues sorted descending
**Raises:** None (returns [1.0] * n on error)
**Retry:** No
**Side Effects:** None

### `_calculate_condition_number(eigenvalues) -> float`
**Pre:** eigenvalues is list of floats
**Post:** Returns max(eigenvalue) / min(eigenvalue)
**Raises:** None (returns inf if min = 0)
**Retry:** No
**Side Effects:** None

### `calculate_partial_correlation(returns_data, strategy1, strategy2) -> float`
**Pre:** Both strategies in returns_data list, returns valid
**Post:** Returns partial correlation controlling for other variables
**Raises:** ValueError if strategy names invalid
**Retry:** No
**Side Effects:** None

### `calculate_rolling_correlation(returns_data, window) -> Dict[str, Dict[str, List[float]]]`
**Pre:** returns_data length >= window, window >= 2
**Post:** Returns rolling correlations for each pair
**Raises:** ValueError if window too large
**Retry:** No
**Side Effects:** None

### `test_stability(returns_data, n_splits) -> Dict[str, float]`
**Pre:** returns_data has enough data for n_splits
**Post:** Returns stability metrics (mean, std, cv of correlations)
**Raises:** ValueError if insufficient data
**Retry:** No
**Side Effects:** None

### `suggest_strategy_removal(metrics, max_to_remove) -> List[str]`
**Pre:** metrics has redundant_pairs
**Post:** Returns list of strategy names to remove (most redundant)
**Raises:** None (returns [] on error)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] At least 2 strategies required
- [ ] Correlation matrix diagonal = 1.0
- [ ] Redundant pairs have abs(corr) >= threshold (default 0.9)
- [ ] Effective number bets = n / (1 + (n-1) * avg_corr)
- [ ] Condition number = max_eigenvalue / min_eigenvalue
- [ ] Partial correlation controls for other variables
- [ ] Rolling correlation uses sliding window
- [ ] Stability test splits data into n periods
- [ ] Suggest removal prioritizes high-correlation strategies
- [ ] Support for pearson, spearman, kendall methods

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate covariance matrix | ✅ OK - Checks for singular matrix |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Only imports models |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-004 | BASE_RULES | Log exceptions | ⚠️ NOT APPLIED - Silent fallbacks |
| SEC-007 | BASE_RULES | Input validation | ✅ OK - _validate_returns_data() |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Try/except with fallbacks |

---

## Dependencies
- **External:** numpy (np), scipy.stats (spearmanr, kendalltau), typing, decimal (Decimal)
- **Internal:** app.ensemble.models (CorrelationMetrics)

---

## Required Tests
- **tests/ensemble/test_correlation_analyzer.py:**
  - Test pearson correlation matrix calculation
  - Test spearman correlation matrix calculation
  - Test kendall correlation matrix calculation
  - Test redundant pair detection
  - Test effective number of bets calculation
  - Test eigenvalue calculation
  - Test condition number calculation
  - Test partial correlation calculation
  - Test rolling correlation calculation
  - Test stability testing across time periods
  - Test strategy removal suggestion
  - Test edge cases: perfect correlation, zero variance, single period

---

## Notes
High correlation (>0.9) indicates redundant strategies. Effective number of bets measures true diversification. Condition number > 100 indicates numerical instability. Partial correlation isolates direct relationships.
