# regime_analyzer.py

## Purpose
Market regime detection and analysis using K-Means clustering on volatility and trend to identify Bull/Neutral/Bear market conditions with transition analysis and robustness testing.

---

## Type Definitions / Data Classes

None - uses sklearn's KMeans and StandardScaler, no custom dataclasses.

---

## Function Signatures (Contracts)

### `RegimeAnalyzer.__init__(n_regimes: int = 3, window: int = 20, random_state: int = 42) -> None`
**Pre:** `n_regimes` >= 2; `window` >= 1
**Post:** Analyzer initialized with KMeans and StandardScaler (not fitted)
**Raises:** None
**Retry:** No
**Side Effects:** None (initialization only)

### `RegimeAnalyzer.detect_regimes(returns: pd.Series) -> pd.Series`
**Pre:** `returns` has DatetimeIndex or numeric index; length >= `window`
**Post:** Returns Series with regime labels (0=Bear, 1=Neutral, 2=Bull) same index as input
**Raises:** Returns Series of zeros on error
**Retry:** No
**Side Effects:** Fits `self.kmeans_model` and `self.scaler`; sets `self.regime_labels`

### `RegimeAnalyzer.analyze_regime_performance(returns: pd.Series, regime_labels: Optional[pd.Series] = None) -> Dict[str, Any]`
**Pre:** `returns` and `regime_labels` have same length; both indexed
**Post:** Returns dict with performance metrics per regime (total_return, sharpe, max_dd, win_rate, etc.)
**Raises:** Returns empty dict on mismatched lengths or no labels
**Retry:** No
**Side Effects:** None (analysis only)

### `RegimeAnalyzer.regime_transition_analysis(regime_labels: pd.Series) -> Dict[str, Any]`
**Pre:** `regime_labels` has >= 2 elements
**Post:** Returns dict with transition matrix, probabilities, duration statistics
**Raises:** Returns empty dict on insufficient data
**Retry:** No
**Side Effects:** None (analysis only)

### `RegimeAnalyzer.out_of_sample_regime_robustness(returns: pd.Series, test_periods: int = 5, train_window: int = 252) -> Dict[str, Any]`
**Pre:** `returns` length >= `train_window + 50`
**Post:** Returns dict with walk-forward test results (avg_return, consistency, period_results)
**Raises:** Returns empty dict on insufficient data
**Retry:** No
**Side Effects:** Fits model multiple times (walk-forward validation)

### `RegimeAnalyzer._calculate_max_drawdown(returns: pd.Series) -> float` (static)
**Pre:** `returns` has >= 2 elements
**Post:** Returns maximum drawdown as negative decimal
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `RegimeAnalyzer.get_regime_names() -> Dict[int, str]` (static)
**Pre:** None
**Post:** Returns `{0: "Bear Market", 1: "Neutral Market", 2: "Bull Market"}`
**Raises:** None
**Retry:** No
**Side Effects:** None

### `RegimeAnalyzer.get_regime_labels() -> Optional[pd.Series]`
**Pre:** None
**Post:** Returns last detected regime labels or None if not fitted
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] K-Means clustering on rolling volatility (annualized) and rolling returns (annualized)
- [ ] Regime mapping: 0=Bear (lowest mean return), 1=Neutral, 2=Bull (highest mean return)
- [ ] Rolling window: `window` days for volatility/trend calculation
- [ ] StandardScaler normalizes features before clustering
- [ ] Handles NaN values from rolling window (first `window` rows mapped to neutral)
- [ ] Performance analysis: total_return, annualized_return, volatility, sharpe, max_dd, win_rate
- [ ] Transition matrix: probabilities of regime switches
- [ ] Duration statistics: mean, median, min, max duration per regime
- [ ] Walk-forward robustness: train on rolling window, test on subsequent period
- [ ] Consistency metric: `1 - std(returns) / mean(abs(returns))`
- [ ] All methods handle edge cases (insufficient data, errors)
- [ ] Regime labels have same index as input returns

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
| BT-005 | BASE_RULES.md | Test across different market regimes | ✅ OK - Regime detection and analysis |
| TRD-007 | BASE_RULES.md | Annualization uses TRADING_DAYS = 252 | ✅ OK - sqrt(252) in rolling calc |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - try/except with logging |
| LOG-004 | BASE_RULES.md | Log all exceptions | ✅ OK - logger.error with exc_info=True |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All methods have hints |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each method has one purpose |
| ARCH-004 | BASE_RULES.md | Small functions | ✅ OK - Most methods < 20 lines |
| BT-002 | BASE_RULES.md | Out-of-sample testing | ✅ OK - Walk-forward robustness testing |

**NOTE:** All 96 BASE_RULES apply. Critical for regime analysis:
- **BT-005:** Regime-aware backtesting prevents overfitting to specific market conditions
- **BT-002:** Walk-forward validation ensures regime detection works out-of-sample
- **TRD-007:** Consistent annualization enables cross-regime comparison
- **CC-006:** Explicit error handling prevents silent failures in clustering

---

## Dependencies
- **External:** `numpy`, `pandas`, `sklearn.cluster` (KMeans), `sklearn.preprocessing` (StandardScaler), `logging`, `typing` (Any, Dict, Optional)
- **Internal:** None (standalone analyzer)

---

## Required Tests
- **tests/backtesting/test_regime_analyzer.py:**
  - Test regime detection with synthetic returns (3 distinct regimes)
  - Test regime detection with insufficient data (< window)
  - Test regime mapping: 0=Bear, 1=Neutral, 2=Bull based on mean returns
  - Test performance analysis per regime
  - Test transition matrix calculation
  - Test duration statistics (mean, median, min, max)
  - Test walk-forward robustness with multiple periods
  - Test consistency metric calculation
  - Test max drawdown calculation
  - Test get_regime_names returns correct mapping
  - Test get_regime_labels returns fitted labels or None
  - Test NaN handling in rolling window
  - Test error handling (ValueError, TypeError, etc.)
  - Test logging on errors
  - Test StandardScaler applied before clustering
  - Test KMeans reproducibility with random_state

---

## Notes
- Regime detection helps understand strategy performance across market conditions
- K-Means is unsupervised: finds natural clusters in volatility-return space
- Regime mapping post-hoc: sorts by mean return to assign Bear/Neutral/Bull
- Rolling window: 20 days default (~1 month of trading days)
- Annualization: multiply daily stats by 252 (trading days per year)
- Transition matrix: Markov chain representation of regime switches
- Duration analysis: how long regimes typically last (persistence)
- Walk-forward: tests if regime detection is stable over time
- Consistency metric: lower std/mean = more consistent across periods
- All methods return sensible defaults on error (empty dict, zeros)
- Static methods don't depend on fitted state
- Regime labels preserve input index (aligns with returns for analysis)
