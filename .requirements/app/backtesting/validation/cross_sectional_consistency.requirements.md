# cross_sectional_consistency.py

## Purpose
Implements cross-sectional consistency validation following Antti Ilmanen's "Expected Returns" methodology to validate signal reliability across assets, sectors, and time periods.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### ConsistencyLevel (Enum)
```python
class ConsistencyLevel(Enum):
    EXCELLENT = "excellent"    # IC > 0.1 or p-value < 0.01
    GOOD = "good"              # IC > 0.05 or p-value < 0.05
    MODERATE = "moderate"      # IC > 0.02 or p-value < 0.1
    WEAK = "weak"              # IC > 0 or p-value < 0.2
    POOR = "poor"              # IC <= 0 or p-value >= 0.2
```

**Validation Rules:**
- Must be one of the 5 defined levels
- Determined by IC threshold AND p-value

### CrossSectionalResult Class/DataClass
```python
@dataclass
class CrossSectionalResult:
    timestamp: datetime                  # REQUIRED - Analysis timestamp
    test_name: str                       # REQUIRED - Name of consistency test
    consistency_level: ConsistencyLevel  # REQUIRED - Assessment level
    information_coefficient: float       # REQUIRED - Spearman correlation (signal vs returns)
    p_value: float                       # REQUIRED, [0, 1] - Statistical significance
    rank_ic: float                       # REQUIRED - Pearson correlation on ranks
    sample_size: int                     # REQUIRED - Number of observations
    assets_tested: int                   # REQUIRED - Number of assets in test
    details: Dict[str, Any]              # OPTIONAL - Additional test details
```

**Validation Rules:**
- `information_coefficient in [-1, 1]` (Spearman correlation)
- `p_value in [0, 1]`
- `rank_ic in [-1, 1]`
- `sample_size >= min_sample_size` (default 50)
- `assets_tested >= min_sample_size`

### DecileAnalysisResult Class/DataClass
```python
@dataclass
class DecileAnalysisResult:
    timestamp: datetime                  # REQUIRED - Analysis timestamp
    signal_name: str                     # REQUIRED - Name of signal analyzed
    decile_returns: Dict[int, float]     # REQUIRED - Returns by decile (1-10)
    long_short_return: float             # REQUIRED - Return of top vs bottom decile
    monotonicity_score: float            # REQUIRED, [0, 1] - Higher = more monotonic
    sharpe_ratio: float                  # REQUIRED - Sharpe of long-short returns
    max_drawdown: float                  # REQUIRED - Maximum drawdown
    hit_rate: float                      # REQUIRED, [0, 1] - % positive returns
    is_monotonic: bool                   # REQUIRED - Monotonic pattern detected?
    details: Dict[str, Any]              # OPTIONAL - Additional analysis details
```

**Validation Rules:**
- `decile_returns` must have keys 1 to n_deciles
- `monotonicity_score in [0, 1]`
- `is_monotonic = monotonicity_score > 0.7`
- `hit_rate in [0, 1]`
- `long_short_return = decile_returns[n] - decile_returns[1]`

---

## Function Signatures (Contracts)

### `CrossSectionalConsistencyChecker.validate_ic_consistency(signals, returns, periods=None) -> CrossSectionalResult`
**Pre:** signals and returns must have matching assets (index); must be DataFrames or Series
**Post:** Returns CrossSectionalResult with IC = spearman(signal, returns) averaged across periods
**Raises:** Returns POOR result with error details if no valid periods
**Retry:** ❌ No
**Side Effects:** Appends result to `self._history`

### `CrossSectionalConsistencyChecker.validate_decile_monotonicity(signals, returns, n_deciles=None) -> DecileAnalysisResult`
**Pre:** signals and returns must be Series with matching index; len(common_assets) >= n_deciles * 5
**Post:** Returns DecileAnalysisResult with monotonicity_score in [0, 1]
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** None

### `CrossSectionalConsistencyChecker.validate_sector_consistency(signals, returns, sectors, min_sectors=3) -> Dict[str, CrossSectionalResult]`
**Pre:** signals, returns, sectors must have matching index; unique sectors >= min_sectors
**Post:** Returns dict mapping sector names to CrossSectionalResult for each sector
**Raises:** Returns empty dict if insufficient sectors
**Retry:** ❌ No
**Side Effects:** Logs warnings for sectors with insufficient samples

### `CrossSectionalConsistencyChecker.validate_time_stability(signals, returns, window=252, min_periods=20) -> Dict[str, Any]`
**Pre:** signals and returns must be DataFrames with time columns
**Post:** Returns dict with is_stable = (std_ic < abs(mean_ic) * 2 AND sign_change_ratio < 0.3)
**Raises:** Returns dict with is_stable=False and error details if no valid periods
**Retry:** ❌ No
**Side Effects:** None

### `CrossSectionalConsistencyChecker._align_data(signals, returns) -> Tuple[pd.DataFrame, pd.DataFrame]`
**Pre:** signals and returns must be Series or DataFrames
**Post:** Returns tuple of aligned DataFrames on common index (assets)
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** Converts Series to DataFrame if needed

### `CrossSectionalConsistencyChecker._calculate_monotonicity_score(returns) -> float`
**Pre:** returns must be list of floats ordered by decile
**Post:** Returns monotonicity_score in [0, 1]; 1 = perfectly monotonic
**Raises:** Returns 0.0 if len(returns) < 2
**Retry:** ❌ No
**Side Effects:** None

### `validate_cross_sectional_consistency(signals, returns, sectors=None, config=None) -> Dict[str, Any]`
**Pre:** signals and returns must have matching assets; sectors optional
**Post:** Returns dict with ic_consistency, decile_analysis, sector_consistency, time_stability
**Raises:** Exceptions from CrossSectionalConsistencyChecker methods
**Retry:** ❌ No
**Side Effects:** Creates CrossSectionalConsistencyChecker instance

---

## Acceptance Criteria
- [ ] validate_ic_consistency() calculates Spearman correlation correctly
- [ ] IC consistency level determined by IC threshold AND p-value
- [ ] validate_decile_monotonicity() forms n_deciles groups
- [ ] long_short_return = decile[n] - decile[1]
- [ ] monotonicity_score in [0, 1]; is_monotonic > 0.7
- [ ] validate_sector_consistency() tests each sector independently
- [ ] validate_time_stability() calculates rolling IC
- [ ] is_stable requires low std IC AND low sign change ratio
- [ ] _calculate_monotonicity_score() counts directional changes
- [ ] validate_cross_sectional_consistency() runs appropriate tests
- [ ] Edge cases: insufficient samples, missing sectors, single period

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Uses logger.warning for insufficient samples |
| LOG-005 | BASE_RULES.md | Never log passwords/tokens | ✅ OK - No sensitive data logged |
| TYP-001 | BASE_RULES.md | All functions have type hints | ✅ OK - Complete type coverage |
| TST-005 | BASE_RULES.md | Coverage > 80% | ⚠️ NOT APPLIED - Tests not in scope |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Pure domain logic, no framework deps |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Checker handles only cross-sectional validation |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses field(default_factory=dict) |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - info/warning used correctly |

**NOTE:** This analysis considers all 96+ rules from BASE_RULES.md. File demonstrates strong adherence to Ilmanen's cross-sectional validation methodology with proper statistical testing.

---

## Dependencies
- **External:** numpy, pandas, logging, typing, scipy (stats)
- **Internal:** None (standalone validation module)

---

## Required Tests
- **tests/backtesting/validation/test_cross_sectional_consistency.py:**
  - Test CrossSectionalConsistencyChecker initialization with config
  - Test validate_ic_consistency() calculates correct IC
  - Test validate_ic_consistency() determines correct consistency level
  - Test validate_ic_consistency() handles missing periods
  - Test validate_decile_monotonicity() forms deciles correctly
  - Test validate_decile_monotonicity() calculates long_short_return
  - Test validate_decile_monotonicity() monotonicity_score calculation
  - Test validate_sector_consistency() tests each sector
  - Test validate_sector_consistency() handles insufficient sectors
  - Test validate_time_stability() calculates rolling IC
  - Test validate_time_stability() stability criteria
  - Test _calculate_monotonicity_score() edge cases
  - Test _align_data() handles Series and DataFrame
  - Test validate_cross_sectional_consistency() comprehensive test
  - Test ConsistencyLevel enum thresholds
  - Test edge cases: empty data, single asset, NaN handling

---

## Notes
Implements Antti Ilmanen's "Expected Returns" Chapters 4-5 methodology. Key metric: Information Coefficient (IC) = Spearman correlation between signal and subsequent returns. Cross-sectional validation critical for factor investing and signal reliability assessment.
