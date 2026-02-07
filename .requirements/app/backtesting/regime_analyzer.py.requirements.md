# Requirements: backtesting/regime_analyzer.py

## Audit Status: PASSED
**Audit Date:** 2026-02-07T05:30:00Z
**Auditor:** GAP Audit System

## Source File Analysis
- **File Path:** `app/backtesting/regime_analyzer.py`
- **Lines of Code:** 384
- **Type:** Module

## Purpose
Detects and analyzes market regimes based on volatility and trend using K-Means clustering. Provides regime transition analysis, performance metrics by regime, and walk-forward robustness testing.

## Dependencies
### Internal
- None

### External
- `sklearn.cluster.KMeans` - K-Means clustering
- `sklearn.preprocessing.StandardScaler` - Feature standardization
- `numpy` - Numerical computations
- `pandas` - Data manipulation
- `logging` - Logging
- `typing` - Type hints

## Classes/Functions
### Classes
- `RegimeAnalyzer` - Main regime analyzer class

  #### Methods
  - `__init__(n_regimes, window, random_state)` - Initialize analyzer
  - `detect_regimes(returns)` - Detect market regimes using K-Means
  - `analyze_regime_performance(returns, regime_labels)` - Analyze performance per regime
  - `regime_transition_analysis(regime_labels)` - Analyze regime transitions
  - `out_of_sample_regime_robustness(returns, test_periods, train_window)` - Walk-forward robustness testing
  - `_calculate_max_drawdown(returns)` - Calculate maximum drawdown (static)
  - `get_regime_names()` - Get regime name mapping
  - `get_regime_labels()` - Get last detected regime labels

## BASE_RULES Compliance
✅ **R099 (Absolute imports):** No relative imports
✅ **R098 (No relative imports):** All imports are absolute from standard library or external packages
✅ **R100 (Modern type hints):** Uses `Optional[pd.Series]`, `Dict[str, Any]`, `Optional[KMeans]`
⚠️ **R102 (Any without docs):** `Dict[str, Any]` used but documented and acceptable for flexible return data
✅ **R103 (No type comments):** No type comments used
✅ **R104 (No bare except):** Uses specific exception tuples
✅ **R105 (No print statements):** Uses `logger` instead of print
✅ **R107 (No mutable defaults):** `regime_labels: Optional[pd.Series] = None` (immutable)
✅ **R108 (Exception handling):** Specific exceptions caught: `(ValueError, TypeError, KeyError, AttributeError, IndexError)`
✅ **R110 (Google docstrings):** All classes and methods have Google-style docstrings
✅ **R111 (No circular imports):** No circular imports detected

## Type Hints Analysis
- Uses `Optional[T]` syntax (traditional, but acceptable)
- `Dict[str, Any]` used appropriately for flexible data structures
- Return types specified for all methods
- `pd.Series`, `KMeans`, `StandardScaler` properly annotated

## Exception Handling
- Line 125: `(ValueError, TypeError, KeyError, AttributeError, IndexError)` with logging
- Line 277: `(ValueError, TypeError, KeyError, AttributeError)` with logging
- Line 365: `(ValueError, TypeError, KeyError, AttributeError)` with logging
- All exceptions are logged with `exc_info=True` for proper stack traces

## Docstrings
- Module docstring present and clear
- Class docstring with description
- Method docstrings with Args, Returns sections
- Clear parameter descriptions

## Regime Detection Logic
1. Calculates rolling volatility (annualized)
2. Calculates rolling returns (annualized)
3. Creates feature matrix
4. Standardizes features
5. Fits K-Means
6. Maps regimes: 0=Bear, 1=Neutral, 2=Bull (based on mean return)
7. Handles NaN values (first window rows)

## Notes
- Well-documented regime mapping logic
- Proper handling of edge cases (insufficient data, NaN values)
- Comprehensive performance analysis by regime
- Transition probability calculation
- Walk-forward robustness testing for validation

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Updated for GAP Audit on 2026-02-07*
