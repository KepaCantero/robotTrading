# advanced_visualizations.py

## Purpose
Comprehensive visualization suite for backtest analysis including correlation networks, parallel coordinates, 3D scatter plots, underwater drawdown charts, rolling metrics, regime performance, and seasonality heatmaps.

---

## Type Definitions / Data Classes

No dataclasses defined - uses pandas DataFrames and Series.

---

## Function Signatures (Contracts)

### `AdvancedVisualizer.__init__(output_dir: str = "reports/meta_analyzer", dpi: int = 150)`
**Pre:** output_dir valid path, dpi > 0
**Post:** Visualizer initialized, output_dir created
**Raises:** OSError on directory creation failure
**Retry:** No
**Side Effects:** Creates output_dir, sets matplotlib style

### `plot_correlation_network(data: pd.DataFrame, threshold: float = 0.3, figsize: Tuple[int, int] = (14, 10), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** data has numeric columns
**Post:** Creates correlation network plot, saves to file
**Raises:** None (returns None on failure, logs error)
**Retry:** No
**Side Effects:** Creates PNG file in output_dir

### `plot_parallel_coordinates(data: pd.DataFrame, color_col: Optional[str] = None, max_cols: int = 10, output_file: Optional[str] = None) -> Optional[str]`
**Pre:** data non-empty
**Post:** Creates interactive parallel coordinates plot (HTML)
**Raises:** None (returns None on failure, logs error)
**Retry:** No
**Side Effects:** Creates HTML file in output_dir

### `plot_3d_scatter(data: pd.DataFrame, x_col: str, y_col: str, z_col: str, color_col: Optional[str] = None, size_col: Optional[str] = None, output_file: Optional[str] = None) -> Optional[str]`
**Pre:** data has x_col, y_col, z_col
**Post:** Creates interactive 3D scatter plot (HTML)
**Raises:** None (returns None on failure, logs error)
**Retry:** No
**Side Effects:** Creates HTML file in output_dir

### `plot_underwater_drawdown(equity_curve: pd.Series, figsize: Tuple[int, int] = (14, 6), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** equity_curve non-empty
**Post:** Creates underwater drawdown chart
**Raises:** None (returns None on failure, logs error)
**Retry:** No
**Side Effects:** Creates PNG file in output_dir

### `plot_rolling_metrics(equity_curve: pd.Series, window: int = 252, figsize: Tuple[int, int] = (14, 8), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** equity_curve has >= window data points
**Post:** Creates rolling metrics chart (returns, volatility, Sharpe)
**Raises:** None (returns None on failure, logs error)
**Retry:** No
**Side Effects:** Creates PNG file in output_dir

### `plot_regime_performance(returns: pd.Series, regime_labels: pd.Series, regime_names: Optional[Dict[int, str]] = None, figsize: Tuple[int, int] = (12, 6), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** returns and regime_labels same length
**Post:** Creates regime performance comparison chart
**Raises:** None (returns None on failure, logs error)
**Retry:** No
**Side Effects:** Creates PNG file in output_dir

### `plot_seasonality_heatmap(returns: pd.Series, figsize: Tuple[int, int] = (14, 8), output_file: Optional[str] = None) -> Optional[Any]`
**Pre:** returns has DatetimeIndex
**Post:** Creates monthly returns heatmap
**Raises:** None (returns None on failure, logs error)
**Retry:** No
**Side Effects:** Creates PNG file in output_dir

### `generate_interactive_dashboard(data: pd.DataFrame, equity_curve: Optional[pd.Series] = None, output_file: str = "dashboard.html") -> Optional[str]`
**Pre:** data non-empty
**Post:** Creates interactive dashboard with histograms and box plots
**Raises:** None (returns None on failure, logs error)
**Retry:** No
**Side Effects:** Creates HTML file in output_dir

---

## Acceptance Criteria
- [ ] Correlation network shows edges for correlations >= threshold
- [ ] Network edge width correlates with correlation strength
- [ ] Parallel coordinates normalized for better visualization
- [ ] 3D scatter plot with color and size options
- [ ] Underwater chart shows drawdown from peak
- [ ] Rolling metrics: returns, volatility, Sharpe ratio
- [ ] Regime performance: cumulative returns, distribution, statistics
- [ ] Seasonality heatmap: monthly returns by year
- [ ] All matplotlib plots use seaborn-v0_8-darkgrid style
- [ ] All plots saved with specified DPI (default 150)
- [ ] Optional dependencies handled gracefully (networkx, plotly)
- [ ] Missing dependencies return None with warning log
- [ ] HTML files created for interactive plots (plotly)
- [ ] PNG files created for static plots (matplotlib)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ⚠️ NOT APPLIED - Some functions > 20 lines |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ✅ OK - Each plot one function |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK - exc_info=True |
| LOG-005 | 09-logging-observability.md | Never log sensitive data | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| PERF-002 | Custom | Handle optional dependencies gracefully | ✅ OK - HAS_* flags |
| UI-001 | Custom | Plots have proper labels and titles | ✅ OK |

**Optional Dependencies:**
- ✅ matplotlib (HAS_MATPLOTLIB flag)
- ✅ plotly (HAS_PLOTLY flag)
- ✅ networkx (HAS_NETWORKX flag)
- ✅ Graceful fallback when dependencies missing

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** logging, pathlib, typing, numpy, pandas
- **Optional:** matplotlib, seaborn, networkx, plotly
- **Internal:** None (standalone visualization module)

---

## Required Tests
- **test_advanced_visualizations.py:**
  - Success: Correlation network plot creation
  - Success: Parallel coordinates plot creation
  - Success: 3D scatter plot creation
  - Success: Underwater drawdown chart
  - Success: Rolling metrics chart
  - Success: Regime performance chart
  - Success: Seasonality heatmap
  - Success: Interactive dashboard
  - Success: All plots saved to output_dir
  - Success: Matplotlib style applied
  - Error: Empty DataFrame (returns None)
  - Error: Missing columns (returns None)
  - Edge: Missing matplotlib (HAS_MATPLOTLIB = False)
  - Edge: Missing plotly (HAS_PLOTLY = False)
  - Edge: Missing networkx (HAS_NETWORKX = False)
  - Edge: High threshold in correlation network (fewer edges)
  - Integration: Regime labels length matches returns
  - Integration: DatetimeIndex for seasonality heatmap

---

## Notes
- Optional dependencies with graceful fallbacks
- Default DPI: 150 for publication-quality plots
- Default style: seaborn-v0_8-darkgrid
- Correlation network uses spring layout (k=2)
- Rolling window: 252 days (1 trading year)
- Seasonality: monthly returns grouped by year
- Export availability constants for tests: MATPLOTLIB_AVAILABLE, PLOTLY_AVAILABLE, NETWORKX_AVAILABLE
