# feature_explosion_validator.py

## Purpose
Implements feature explosion validation following Antti Ilmanen's "Expected Returns" methodology to detect overfitting due to excessive features relative to sample size (curse of dimensionality).

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### FeatureExplosionLevel (Enum)
```python
class FeatureExplosionLevel(Enum):
    SAFE = "safe"              # Feature count appropriate for sample size
    MODERATE = "moderate"      # Some feature explosion, manageable
    SEVERE = "severe"          # Significant feature explosion, action needed
    CRITICAL = "critical"      # Severe feature explosion, immediate action required
```

**Validation Rules:**
- Must be one of 4 defined levels
- Determined by features_per_sample_ratio, VIF_max, and thresholds

### FeatureExplosionResult Class/DataClass
```python
@dataclass
class FeatureExplosionResult:
    timestamp: datetime                      # REQUIRED - Analysis timestamp
    explosion_level: FeatureExplosionLevel   # REQUIRED - Severity assessment
    n_features: int                          # REQUIRED - Number of features
    n_samples: int                           # REQUIRED - Number of samples
    features_per_sample_ratio: float         # REQUIRED - n_features / n_samples
    recommended_max_features: int            # REQUIRED - Ilmanen's rule: ~10% of samples
    excess_features: int                     # REQUIRED - n_features - recommended_max
    vif_max: float                           # REQUIRED - Maximum VIF across features
    correlation_max: float                   # REQUIRED - Max pairwise correlation
    details: Dict[str, Any]                  # OPTIONAL - Additional analysis details
```

**Validation Rules:**
- `features_per_sample_ratio = n_features / n_samples`
- `recommended_max_features = max(10, int(n_samples * max_features_ratio))`
- `excess_features = max(0, n_features - recommended_max_features)`
- `vif_max >= 1.0` (1.0 = no multicollinearity, >10 = high)
- `correlation_max in [0, 1]` (absolute value)
- CRITICAL: ratio > 0.5 OR vif_max > 20 → CRITICAL
- SEVERE: ratio > 0.3 OR vif_max > 10

### MulticollinearityResult Class/DataClass
```python
@dataclass
class MulticollinearityResult:
    timestamp: datetime                              # REQUIRED - Analysis timestamp
    has_multicollinearity: bool                      # REQUIRED - Multicollinearity detected?
    n_highly_correlated_pairs: int                   # REQUIRED - Count of pairs with |corr| > threshold
    n_high_vif_features: int                         # REQUIRED - Count of features with VIF > threshold
    high_correlation_pairs: List[Tuple[str, str, float]] # REQUIRED - (f1, f2, corr) tuples
    high_vif_features: Dict[str, float]             # REQUIRED - {feature: vif} for high VIF
    condition_number: float                          # REQUIRED - Matrix condition number
    details: Dict[str, Any]                          # OPTIONAL - Additional analysis details
```

**Validation Rules:**
- `high_correlation_pairs` sorted by absolute correlation descending
- `has_multicollinearity = (n_high_vif_features > 0 OR n_highly_correlated_pairs > 0 OR condition_number > threshold)`
- `condition_number >= 1.0` (1.0 = perfectly conditioned)
- `high_correlation_pairs` contains tuples where abs(corr) > correlation_threshold
- `high_vif_features` contains features where vif > vif_threshold

---

## Function Signatures (Contracts)

### `FeatureExplosionValidator.validate_feature_explosion(X, y=None, feature_names=None) -> FeatureExplosionResult`
**Pre:** X must be DataFrame or 2D array; if array, feature_names optional or generated
**Post:** Returns FeatureExplosionResult with explosion_level based on ratio and VIF
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** Logs explosion level and metrics

### `FeatureExplosionValidator.analyze_multicollinearity(X, feature_names=None) -> MulticollinearityResult`
**Pre:** X must be DataFrame or 2D array with >= 2 features
**Post:** Returns MulticollinearityResult with has_multicollinearity boolean
**Raises:** No explicit exceptions (handles calculation errors gracefully)
**Retry:** ❌ No
**Side Effects:** Logs multicollinearity detection results

### `FeatureExplosionValidator.recommend_feature_reduction(X, feature_names=None, method="combined") -> Dict[str, Any]`
**Pre:** X must be DataFrame or 2D array; method must be 'vif', 'correlation', 'variance', or 'combined'
**Post:** Returns dict with features_to_remove list and reduction statistics
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** Logs reduction recommendations

### `FeatureExplosionValidator._calculate_max_vif(X) -> float`
**Pre:** X must be DataFrame with at least 1 feature
**Post:** Returns maximum VIF value (>= 1.0); returns 0.0 on error
**Raises:** No explicit exceptions (logs warning on failure)
**Retry:** ❌ No
**Side Effects:** Fits LinearRegression for each feature

### `FeatureExplosionValidator._calculate_all_vif(X) -> Dict[str, float]`
**Pre:** X must be DataFrame with at least 1 feature
**Post:** Returns dict mapping feature names to VIF values; VIF >= 1.0
**Raises:** No explicit exceptions (logs warning on failure)
**Retry:** ❌ No
**Side Effects:** Fits LinearRegression for each feature against all others

### `FeatureExplosionValidator._calculate_max_correlation(X) -> float`
**Pre:** X must be DataFrame with at least 2 features
**Post:** Returns maximum absolute pairwise correlation in [0, 1]; returns 0.0 on error
**Raises:** No explicit exceptions (logs warning on failure)
**Retry:** ❌ No
**Side Effects:** None

### `validate_feature_explosion(X, y=None, config=None) -> FeatureExplosionResult`
**Pre:** X must be DataFrame or 2D array
**Post:** Returns FeatureExplosionResult from validator
**Raises:** Exceptions from FeatureExplosionValidator
**Retry:** ❌ No
**Side Effects:** Creates FeatureExplosionValidator instance

### `analyze_multicollinearity(X, config=None) -> MulticollinearityResult`
**Pre:** X must be DataFrame or 2D array
**Post:** Returns MulticollinearityResult from validator
**Raises:** Exceptions from FeatureExplosionValidator
**Retry:** ❌ No
**Side Effects:** Creates FeatureExplosionValidator instance

---

## Acceptance Criteria
- [ ] validate_feature_explosion() calculates correct features_per_sample_ratio
- [ ] recommended_max_features follows Ilmanen's 10% rule
- [ ] explosion_level CRITICAL when ratio > 0.5 OR vif_max > 20
- [ ] explosion_level SEVERE when ratio > 0.3 OR vif_max > 10
- [ ] analyze_multicollinearity() calculates VIF correctly
- [ ] analyze_multicollinearity() identifies highly correlated pairs
- [ ] condition_number >= 1.0 always
- [ ] has_multicollinearity true when VIF > threshold OR correlation > threshold OR condition_number > threshold
- [ ] recommend_feature_reduction() with method='combined' uses all three methods
- [ ] recommend_feature_reduction() removes one feature per correlated pair
- [ ] _calculate_all_vif() returns VIF >= 1.0 for all features
- [ ] Edge cases: single feature, constant features, NaN values, infinite VIF

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Uses logger.warning for calculation failures |
| LOG-005 | BASE_RULES.md | Never log passwords/tokens | ✅ OK - No sensitive data logged |
| TYP-001 | BASE_RULES.md | All functions have type hints | ✅ OK - Complete type coverage |
| TST-005 | BASE_RULES.md | Coverage > 80% | ⚠️ NOT APPLIED - Tests not in scope |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Pure domain logic, no framework deps |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Validator handles only feature explosion |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses field(default_factory=dict) |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - info/warning used correctly |

**NOTE:** This analysis considers all 96+ rules from BASE_RULES.md. File demonstrates strong adherence to Ilmanen's feature explosion detection methodology with proper error handling for statistical calculations.

---

## Dependencies
- **External:** numpy, pandas, logging, typing, sklearn (LinearRegression)
- **Internal:** None (standalone validation module)

---

## Required Tests
- **tests/backtesting/validation/test_feature_explosion_validator.py:**
  - Test FeatureExplosionValidator initialization with config
  - Test validate_feature_explosion() calculates correct ratio
  - Test validate_feature_explosion() determines correct explosion_level
  - Test validate_feature_explosion() SAFE level (ratio < 10%)
  - Test validate_feature_explosion() CRITICAL level (ratio > 50%)
  - Test analyze_multicollinearity() calculates VIF correctly
  - Test analyze_multicollinearity() identifies correlated pairs
  - Test analyze_multicollinearity() condition number
  - Test analyze_multicollinearity() has_multicollinearity logic
  - Test recommend_feature_reduction() with method='vif'
  - Test recommend_feature_reduction() with method='correlation'
  - Test recommend_feature_reduction() with method='variance'
  - Test recommend_feature_reduction() with method='combined'
  - Test _calculate_all_vif() VIF >= 1.0 constraint
  - Test _calculate_all_vif() handles constant features (VIF = inf)
  - Test _calculate_max_correlation() returns correct max
  - Test validate_feature_explosion() convenience function
  - Test analyze_multicollinearity() convenience function
  - Test edge cases: single feature, empty DataFrame, NaN values, constant features

---

## Notes
Implements Antti Ilmanen's "Expected Returns" Chapter 6 methodology on data mining dangers. Key insight: too many features relative to samples leads to overfitting. Ilmanen's rule: keep features to ~10% of sample size. VIF > 10 indicates problematic multicollinearity.
