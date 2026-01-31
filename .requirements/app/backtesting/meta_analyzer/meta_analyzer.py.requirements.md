# meta_analyzer.py

## Purpose
Meta-analysis system for backtesting results. Performs pattern analysis, clustering, and optimal combination detection across multiple backtest results using statistical methods and machine learning.

---

## Type Definitions / Data Classes

### BacktestMetaAnalyzer Class
```python
class BacktestMetaAnalyzer:
    data_dir: Path                          # REQUIRED - Directory with result files
    output_dir: Path                        # REQUIRED - Directory for reports
    enable_visualizations: bool             # OPTIONAL - Enable matplotlib plots (default: True)
    _lock: threading.RLock                 # Thread-safe lock for shared state
    results: List[Dict[str, Any]]           # Loaded backtest results
    df_results: pd.DataFrame | None         # Pandas DataFrame for analysis
    analysis_results: Dict[str, Any]        # Cached analysis results
```

**Validation Rules:**
- `data_dir` must exist or be empty (returns 0 if doesn't exist)
- `output_dir` is created with `parents=True, exist_ok=True`
- Thread-safe operations use RLock for reentrant locking

---

## Function Signatures (Contracts)

### `BacktestMetaAnalyzer.load_results(path) -> int`
**Pre:** None (path optional, uses self.data_dir if None)
**Post:** Returns count of loaded files, updates self.results and self.df_results
**Raises:** None (returns 0 on errors)
**Retry:** ❌ No
**Side Effects:** Reads JSON and CSV files, updates shared state thread-safely

### `BacktestMetaAnalyzer.analyze_performance() -> Dict[str, Any]`
**Pre:** df_results must be loaded (non-empty)
**Post:** Returns dict with summary_stats, correlations, best/worst performers
**Raises:** None (returns empty dict if no results)
**Retry:** ❌ No
**Side Effects:** Updates self.analysis_results, performs vectorized computations

### `BacktestMetaAnalyzer.detect_clusters(n_clusters, features) -> Dict[str, Any]`
**Pre:** sklearn must be available, df_results must be loaded
**Post:** Returns dict with cluster assignments and characteristics
**Raises:** None (returns empty dict if sklearn unavailable or insufficient data)
**Retry:** ❌ No
**Side Effects:** Updates df_results with 'cluster' column

### `BacktestMetaAnalyzer.suggest_optimal_combinations(top_n, criteria) -> List[Dict[str, Any]]`
**Pre:** df_results must be loaded
**Post:** Returns list of top_n result dicts sorted by composite score
**Raises:** None (returns empty list if no results)
**Retry:** ❌ No
**Side Effects:** None (read-only operation)

### `BacktestMetaAnalyzer.export_report(output_path, format) -> str`
**Pre:** analysis_results must be populated (run analyze_performance first)
**Post:** Returns path to exported file, generates visualizations if enabled
**Raises:** None (returns empty string on errors)
**Retry:** ❌ No
**Side Effects:** Writes JSON/CSV file, generates PNG plots if enabled

### `BacktestMetaAnalyzer.run_parallel_analysis(max_workers, include_clustering, n_clusters) -> Dict[str, Any]`
**Pre:** data_dir must contain valid files
**Post:** Returns dict with performance, clustering, suggestions
**Raises:** None (logs errors, continues with partial results)
**Retry:** ❌ No
**Side Effects:** Loads data, runs CPU-bound tasks in parallel

---

## Acceptance Criteria
- [ ] load_results() loads both JSON and CSV files
- [ ] load_results() uses asyncio for parallel file reading
- [ ] Thread-safe state management with RLock
- [ ] analyze_performance() calculates summary stats for all numeric metrics
- [ ] analyze_performance() performs correlation analysis
- [ ] analyze_performance() identifies best and worst performers by Sharpe and PnL
- [ ] detect_clusters() requires sklearn (graceful fallback if unavailable)
- [ ] detect_clusters() normalizes features before clustering
- [ ] suggest_optimal_combinations() uses vectorized operations (not iterrows)
- [ ] suggest_optimal_combinations() supports custom criteria weights
- [ ] export_report() generates matplotlib visualizations if enabled
- [ ] export_report() handles matplotlib unavailability gracefully
- [ ] run_parallel_analysis() uses ThreadPoolExecutor for CPU-bound tasks
- [ ] All shared state access is protected by RLock
- [ ] Optional dependencies (sklearn, matplotlib) have graceful fallbacks

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ PARTIAL - Some errors lack exc_info |
| TYP-001 | BASE_RULES.md | 100% type coverage | ❌ GAP - Missing type hints in some methods |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ASYNC-001 | BASE_RULES.md | Use async def | ✅ OK - load_results is async |
| PERF-002 | BASE_RULES.md | Generators for large data | ⚠️ PARTIAL - Uses pandas, not generators |
| PERF-006 | BASE_RULES.md | Async I/O | ✅ OK - Async file loading |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Infrastructure component |
| QL-001 | BASE_RULES.md | Complexity < 10 | ⚠️ PARTIAL - Some methods are complex |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** pandas, numpy, logging, asyncio, threading, concurrent.futures
- **Optional:** sklearn (HAS_SKLEARN flag), matplotlib/seaborn (HAS_MATPLOTLIB flag)
- **Internal:** None

---

## Required Tests
- **tests/backtesting/meta_analyzer/test_meta_analyzer.py:**
  - Test load_results() loads JSON files
  - Test load_results() loads CSV files
  - Test load_results() uses parallel async loading
  - Test load_results() handles non-existent directory
  - Test load_results() thread-safe state updates
  - Test analyze_performance() calculates correct summary stats
  - Test analyze_performance() performs correlation analysis
  - Test analyze_performance() identifies best/worst performers
  - Test analyze_performance() handles empty results
  - Test detect_clusters() performs KMeans clustering
  - Test detect_clusters() normalizes features
  - Test detect_clusters() returns empty dict when sklearn unavailable
  - Test detect_clusters() handles insufficient data gracefully
  - Test suggest_optimal_combinations() uses vectorized operations
  - Test suggest_optimal_combinations() applies custom criteria weights
  - Test suggest_optimal_combinations() sorts by composite score
  - Test export_report() exports JSON format
  - Test export_report() exports CSV format
  - Test export_report() generates matplotlib plots
  - Test export_report() handles matplotlib unavailability
  - Test export_report() returns empty string when no analysis
  - Test run_parallel_analysis() executes all tasks
  - Test run_parallel_analysis() uses ThreadPoolExecutor
  - Test run_parallel_analysis() handles task failures gracefully
  - Test all RLock-protected methods are thread-safe
  - Test _analyze_by_category() handles missing categories
  - Test _generate_visualizations() creates all plot types
  - Test _generate_visualizations() handles plot errors gracefully

---

## Notes
- Optional dependencies checked at import time (HAS_SKLEARN, HAS_MATPLOTLIB flags)
- Thread-safety implemented with threading.RLock for reentrant locking
- suggest_optimal_combinations() uses vectorized pandas operations (line 423-441)
- Matplotlib style uses 'seaborn-v0_8-darkgrid' (line 525)
- Visualizations: Sharpe distribution, Sharpe vs PnL scatter, correlation heatmap
- All async methods use asyncio.gather for parallel execution
- run_parallel_analysis() mixes I/O-bound (async) and CPU-bound (ThreadPoolExecutor)
- Line 143: 'git dif' typo in audit_trail.py (not this file, but related)
- Line 580: catches asyncio.TimeoutError but method is not async
