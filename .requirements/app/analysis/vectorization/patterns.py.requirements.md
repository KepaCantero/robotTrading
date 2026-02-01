# patterns.py

## Purpose
Provide a library of common vectorization patterns and anti-patterns in numerical computing, serving as a reference and suggestion generator for the vectorization auditor.

---

## Type Definitions / Data Classes
None - This module contains only static methods returning documentation strings.

---

## Function Signatures (Contracts)

### `elementwise_operation() -> str`
**Pre:** None
**Post:** Returns documentation string for element-wise operations pattern
**Raises:** None
**Retry:** No
**Side Effects:** None

### `filtering() -> str`
**Pre:** None
**Post:** Returns documentation string for filtering with boolean conditions
**Raises:** None
**Retry:** No
**Side Effects:** None

### `rolling_calculation() -> str`
**Pre:** None
**Post:** Returns documentation string for rolling window calculations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `groupby_aggregation() -> str`
**Pre:** None
**Post:** Returns documentation string for group-by operations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `correlation_matrix() -> str`
**Pre:** None
**Post:** Returns documentation string for correlation matrix calculation
**Raises:** None
**Retry:** No
**Side Effects:** None

### `conditional_assignment() -> str`
**Pre:** None
**Post:** Returns documentation string for np.where conditional assignment
**Raises:** None
**Retry:** No
**Side Effects:** None

### `exponential_weighted() -> str`
**Pre:** None
**Post:** Returns documentation string for exponentially weighted operations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `percentage_change() -> str`
**Pre:** None
**Post:** Returns documentation string for percentage change calculation
**Raises:** None
**Retry:** No
**Side Effects:** None

### `cumulative_operations() -> str`
**Pre:** None
**Post:** Returns documentation string for cumulative operations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `shift_lag() -> str`
**Pre:** None
**Post:** Returns documentation string for shift/lag operations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `rank_percentile() -> str`
**Pre:** None
**Post:** Returns documentation string for ranking and percentile calculations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `distance_matrix() -> str`
**Pre:** None
**Post:** Returns documentation string for distance matrix calculation
**Raises:** None
**Retry:** No
**Side Effects:** None

### `interpolation() -> str`
**Pre:** None
**Post:** Returns documentation string for interpolation operations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `difference_operations() -> str`
**Pre:** None
**Post:** Returns documentation string for difference operations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `value_counts_mode() -> str`
**Pre:** None
**Post:** Returns documentation string for value counting and mode
**Raises:** None
**Retry:** No
**Side Effects:** None

### `outer_product() -> str`
**Pre:** None
**Post:** Returns documentation string for outer product and broadcasting
**Raises:** None
**Retry:** No
**Side Effects:** None

### `datetime_operations() -> str`
**Pre:** None
**Post:** Returns documentation string for datetime operations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_all_patterns() -> dict[str, str]`
**Pre:** None
**Post:** Returns dict mapping pattern names to documentation
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_suggestion_for_issue(issue_type: str) -> str`
**Pre:** None
**Post:** Returns pattern documentation for given issue type
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_trading_specific_examples() -> dict[str, str]`
**Pre:** None
**Post:** Returns dict of trading-specific vectorization examples
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_performance_comparison() -> dict[str, tuple[str, str]]`
**Pre:** None
**Post:** Returns dict of (non_vectorized_time, vectorized_time) estimates
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All pattern methods return non-empty strings with before/after examples
- [ ] Performance estimates show significant speedups (typically >10x)
- [ ] Trading examples cover common operations (returns, volatility, Sharpe, etc.)
- [ ] get_all_patterns includes all 17 documented patterns
- [ ] get_suggestion_for_issue handles all valid issue types
- [ ] Code examples are syntactically correct Python
- [ ] Use cases mention trading context where applicable

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear pattern names |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All methods have return types |
| CC-003 | BASE_RULES | KISS - Keep it simple | ✅ OK - Simple static methods |
| PERF-001 | BASE_RULES | List comprehensions | ✅ OK - Uses dict/list comprehensions |
| LOG-005 | BASE_RULES | No sensitive data logging | ⚠️ NOT APPLIED - No logging |

---

## Dependencies
- **External:** typing
- **Internal:** None

---

## Required Tests
- **tests/unit/analysis/test_vectorization_patterns.py:**
  - Test all 17 pattern methods return non-empty strings
  - Test get_all_patterns returns correct number of patterns
  - Test get_suggestion_for_issue with valid issue types
  - Test get_suggestion_for_issue with unknown type (returns default)
  - Test get_trading_specific_examples returns expected keys
  - Test get_performance_comparison returns valid time tuples
  - Verify all code examples are syntactically valid Python

---

## Notes
- This is a documentation/reference module, not computation logic
- Patterns emphasize NumPy and Pandas vectorized operations
- Performance estimates are approximate for large datasets
- Trading examples focus on common quantitative finance operations
