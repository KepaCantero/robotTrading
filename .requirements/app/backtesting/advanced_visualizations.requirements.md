# advanced_visualizations.py

## Purpose
Comprehensive visualization suite for backtest analysis including correlation networks, parallel coordinates, 3D scatter plots, underwater drawdown charts, rolling metrics, regime performance, and seasonality heatmaps.

---

## Type Definitions / Data Classes

### AdvancedVisualizer Class
```python
class AdvancedVisualizer:
    output_dir: Path                        # REQUIRED - Directory for saving visualizations
    dpi: int                                # REQUIRED - DPI for matplotlib figures (default: 150)
```

**Validation Rules:**
- `output_dir` must be writable, creates if not exists
- `dpi` must be positive integer (default: 150)
- Dependencies (matplotlib, plotly, networkx) are optional with graceful fallbacks

---

## Function Signatures (Contracts)

### `__init__(output_dir: str = "reports/meta_analyzer", dpi: int = 150) -> None`
**Pre:** output_dir path is valid or can be created
**Post:** Output directory exists, visualizer configured
**Raises:** OSError if directory cannot be created (caught and logged)
**Retry:** ❌ No
**Side Effects:** Creates filesystem directory, configures matplotlib style

### `plot_correlation_network(data: pd.DataFrame, threshold: float = 0.3, figsize: Tuple[int, int] = (14, 10), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** data has at least 2 numeric columns
**Post:** Creates correlation network PNG file, returns figure or None
**Raises:** None (returns None on error, logs warning)
**Retry:** ❌ No
**Side Effects:** Writes PNG file to output_dir

### `plot_parallel_coordinates(data: pd.DataFrame, color_col: Optional[str] = None, max_cols: int = 10, output_file: Optional[str] = None) -> Optional[str]`
**Pre:** data has numeric columns
**Post:** Creates interactive HTML parallel coordinates plot, returns path or None
**Raises:** None (returns None on error, logs warning)
**Retry:** ❌ No
**Side Effects:** Writes HTML file to output_dir

### `plot_3d_scatter(data: pd.DataFrame, x_col: str, y_col: str, z_col: str, color_col: Optional[str] = None, size_col: Optional[str] = None, output_file: Optional[str] = None) -> Optional[str]`
**Pre:** data contains x_col, y_col, z_col columns
**Post:** Creates interactive 3D scatter HTML plot, returns path or None
**Raises:** None (returns None on error, logs warning)
**Retry:** ❌ No
**Side Effects:** Writes HTML file to output_dir

### `plot_underwater_drawdown(equity_curve: pd.Series, figsize: Tuple[int, int] = (14, 6), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** equity_curve has numeric values
**Post:** Creates underwater drawdown PNG chart, returns figure or None
**Raises:** None (returns None on error, logs warning)
**Retry:** ❌ No
**Side Effects:** Writes PNG file to output_dir

### `plot_rolling_metrics(equity_curve: pd.Series, window: int = 252, figsize: Tuple[int, int] = (14, 8), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** equity_curve has enough data for rolling window
**Post:** Creates rolling metrics PNG chart (3 subplots), returns figure or None
**Raises:** None (returns None on error, logs warning)
**Retry:** ❌ No
**Side Effects:** Writes PNG file to output_dir

### `plot_regime_performance(returns: pd.Series, regime_labels: pd.Series, regime_names: Optional[Dict[int, str]] = None, figsize: Tuple[int, int] = (12, 6), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** returns and regime_labels have same length
**Post:** Creates regime performance PNG chart (4 subplots), returns figure or None
**Raises:** None (returns None on error, logs warning)
**Retry:** ❌ No
**Side Effects:** Writes PNG file to output_dir

### `plot_seasonality_heatmap(returns: pd.Series, figsize: Tuple[int, int] = (14, 8), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** returns has DatetimeIndex
**Post:** Creates seasonality heatmap PNG chart, returns figure or None
**Raises:** None (returns None on error, logs warning)
**Retry:** ❌ No
**Side Effects:** Writes PNG file to output_dir

### `generate_interactive_dashboard(data: pd.DataFrame, equity_curve: Optional[pd.Series] = None, output_file: str = "dashboard.html") -> Optional[str]`
**Pre:** data has numeric columns
**Post:** Creates comprehensive interactive HTML dashboard, returns path or None
**Raises:** None (returns None on error, logs warning)
**Retry:** ❌ No
**Side Effects:** Writes HTML file to output_dir

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] No hardcoded secrets or sensitive data (SEC-001)
- [ ] All file operations use proper error handling
- [ ] Optional dependencies (matplotlib, plotly, networkx) have graceful fallbacks
- [ ] Missing dependencies logged as warnings, not errors
- [ ] Output directory created if not exists
- [ ] All plot methods return None on failure (not crash)
- [ ] Correlation network requires minimum 2 numeric columns
- [ ] Rolling metrics requires window size <= data length
- [ ] Seasonality heatmap requires DatetimeIndex
- [ ] 3D scatter validates x_col, y_col, z_col exist
- [ ] Export availability constants (MATPLOTLIB_AVAILABLE, PLOTLY_AVAILABLE, NETWORKX_AVAILABLE)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage on all functions | ✅ OK |
| TYP-003 | BASE_RULES.md | No Any without justification | ❌ GAP - Uses `Optional[Any]` return types |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK |
| LOG-001 | BASE_RULES.md | Structured logging with context | ✅ OK |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK |
| FMT-008 | BASE_RULES.md | Context managers for file operations | ⚠️ NOT APPLIED - Uses plt.savefig() without explicit context (matplotlib manages file handle) |
| PERF-002 | BASE_RULES.md | Use generators for large data | ⚠️ NOT APPLIED - Visualization requires materialized data |

**GAP Violations Found:**

1. **TYP-003** (P1 - High): Uses `Any` type in return values
   - **Location 1**: Line 106: `def plot_correlation_network(...) -> Optional[Any]`
   - **Location 2**: Line 351: `def plot_underwater_drawdown(...) -> Optional[Any]`
   - **Location 3**: Line 420: `def plot_rolling_metrics(...) -> Optional[Any]`
   - **Fix**: Use more specific type:
   ```python
   from matplotlib.figure import Figure

   def plot_correlation_network(...) -> Optional[Figure]:
   ```

2. **Missing Return Statement** (P0 - Critical): Several functions don't return on error path
   - **Location 1**: Line 177 - `plot_correlation_network` missing return after exception
   - **Location 2**: Line 241 - `plot_parallel_coordinates` missing return after exception
   - **Location 3**: Line 332 - `plot_3d_scatter` missing return after exception
   - **Location 4**: Line 400 - `plot_underwater_drawdown` missing return after exception
   - **Location 5**: Line 483 - `plot_rolling_metrics` missing return after exception
   - **Location 6**: Line 600 - `plot_regime_performance` missing return after exception
   - **Location 7**: Line 686 - `plot_seasonality_heatmap` missing return after exception
   - **Location 8**: Line 749 - `generate_interactive_dashboard` missing return after exception
   - **Fix**: Add `return None` after each `logger.error(...)` call in except blocks

3. **Silent Warnings** (P2 - Medium): Some validation warnings don't return early
   - **Location 1**: Line 205 - `plot_parallel_coordinates` logs warning but continues
   - **Location 2**: Line 276 - `plot_3d_scatter` logs warning but continues
   - **Location 3**: Line 429 - `plot_rolling_metrics` logs warning but continues
   - **Location 4**: Line 513 - `plot_regime_performance` logs warning but continues
   - **Location 5**: Line 627 - `plot_seasonality_heatmap` logs warning but continues
   - **Fix**: Add `return None` after validation warnings

---

## Dependencies
- **External:**
  - **Required:** numpy, pandas, logging, pathlib, typing
  - **Optional:** matplotlib (HAS_MATPLOTLIB flag), plotly (HAS_PLOTLY flag), networkx (HAS_NETWORKX flag)
- **Internal:** None (standalone visualization module)

---

## Required Tests
- **tests/unit/backtesting/test_advanced_visualizations.py:**
  - Test initialization creates output directory
  - Test correlation network with valid data
  - Test correlation network with insufficient columns (returns None)
  - Test parallel coordinates plot generation
  - Test 3D scatter plot with valid columns
  - Test 3D scatter plot with missing columns (returns None)
  - Test underwater drawdown calculation
  - Test rolling metrics with various window sizes
  - Test regime performance with valid regime labels
  - Test regime performance with mismatched lengths (returns None)
  - Test seasonality heatmap with DatetimeIndex
  - Test seasonality heatmap without DatetimeIndex (returns None)
  - Test interactive dashboard generation
  - Test matplotlib unavailable fallback (HAS_MATPLOTLIB = False)
  - Test plotly unavailable fallback (HAS_PLOTLY = False)
  - Test networkx unavailable fallback (HAS_NETWORKX = False)
  - Test all error paths return None (not crash)

---

## Notes
- **Optional Dependencies**: All plotting libraries are optional with graceful fallbacks
- **Export Constants**: `MATPLOTLIB_AVAILABLE`, `PLOTLY_AVAILABLE`, `NETWORKX_AVAILABLE` for testing
- **Return Type Issue**: Many functions have `Optional[Any]` return type should be `Optional[Figure]`
- **Missing Returns**: Critical bug - exception handlers don't return None, causing implicit None returns
- **Style Configuration**: Uses `seaborn-v0_8-darkgrid` style, handles FileNotFoundError gracefully
- **Output Formats**: Static plots (PNG via matplotlib) and interactive plots (HTML via plotly)
