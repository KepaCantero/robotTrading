# Requirements: backtesting/advanced_visualizations.py

## Source File Analysis
- **File Path**: `app/backtesting/advanced_visualizations.py`
- **Lines of Code**: 773
- **Status**: PASSED
- **Audit Date**: 2025-02-07T00:00:00Z

## Purpose
Provides comprehensive visualization suite for backtest analysis including:
- Correlation networks using networkx
- Parallel coordinates plots using plotly
- 3D scatter plots
- Underwater drawdown analysis
- Rolling metrics visualization
- Regime performance analysis
- Seasonality heatmaps
- Interactive dashboard generation

## Dependencies
### External
- `logging` (stdlib)
- `pathlib.Path` (stdlib)
- `typing` (stdlib) - Dict, Optional, TYPE_CHECKING, Tuple
- `numpy` (np)
- `pandas` (pd)
- `networkx` (nx, optional) - HAS_NETWORKX
- `matplotlib.pyplot` (plt, optional) - HAS_MATPLOTLIB
- `seaborn` (sns, optional) - HAS_MATPLOTLIB
- `matplotlib.dates.DateFormatter` (optional)
- `plotly.graph_objects` (go, optional) - HAS_PLOTLY
- `plotly.subplots.make_subplots` (optional)

### Internal
None

## Classes/Functions

### Classes
- `AdvancedVisualizer`: Main visualization class with graceful dependency fallbacks
  - Methods return None if dependencies unavailable
  - Comprehensive error handling with specific exception types
  - All plotting methods return Figure/str for type safety

### Main Methods
- `plot_correlation_network()`: Network-based correlation visualization
- `plot_parallel_coordinates()`: Interactive parallel coordinates plot
- `plot_3d_scatter()`: 3D scatter plot with color/size dimensions
- `plot_underwater_drawdown()`: Drawdown visualization from peak
- `plot_rolling_metrics()`: Rolling return/volatility/Sharpe visualization
- `plot_regime_performance()`: Performance analysis by market regime
- `plot_seasonality_heatmap()`: Monthly returns heatmap (year x month)
- `generate_interactive_dashboard()`: Comprehensive plotly dashboard

## Business Logic
1. **Graceful Dependency Handling**: Optional dependencies with try/except blocks
2. **Validation**: Checks data availability before plotting (e.g., numeric columns, minimum samples)
3. **Flexible Output**: Supports both static (matplotlib) and interactive (plotly) outputs
4. **Performance**: Subsamples large datasets for visualization performance

## Data Models
- Input: `pd.DataFrame`, `pd.Series` for time series data
- Output: `matplotlib.figure.Figure` or `str` (HTML file paths)

## Error Handling
- Specific exception catching: `(RuntimeError, ValueError, TypeError, KeyError)`
- Specific exception catching: `(FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError)`
- Comprehensive logging: `logger.warning()` for missing dependencies
- Returns `None` on failure instead of raising exceptions

## Performance Considerations
- Maximum columns limit for parallel coordinates (default: 10)
- DPI configuration for matplotlib figures (default: 150)
- Subsampling for large datasets in dashboard generation

## Testing Strategy
- Mock optional dependencies for unit tests
- Test graceful degradation when dependencies unavailable
- Validate file path creation and saving
- Test with edge cases (empty DataFrames, single column, etc.)

## BASE_RULES Compliance

### Critical Rules Check

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| R099 | Absolute imports only | ✅ PASS | All imports are absolute |
| R098 | No relative imports | ✅ PASS | No relative imports found |
| R100 | Modern type hints (X \| None) | ✅ PASS | Uses Optional[T] which is compatible |
| R102 | No Any without docs | ✅ PASS | No Any types used |
| R103 | No type comments | ✅ PASS | No type comments found |
| R104 | No bare except | ✅ PASS | All excepts catch specific exceptions |
| R105 | No print() in production | ✅ PASS | No print() statements found |
| R107 | No mutable defaults | ✅ PASS | No mutable default arguments |
| R108 | Proper exception handling | ✅ PASS | Catches specific exception types |
| R110 | Google docstrings | ✅ PASS | All methods have Google-style docstrings |
| R111 | No circular imports | ✅ PASS | No circular imports detected |

### Additional Notes
- **Type Hints**: All methods have complete type hints including return types
- **Logging**: Proper use of logging module (no print statements)
- **Code Quality**: Clean, well-documented code with clear separation of concerns
- **Error Handling**: Comprehensive error handling without bare except clauses
- **Optional Dependencies**: Well-designed pattern for optional visualization libraries

## Audit Status: PASSED
**Audited by**: Claude (GAP Audit - batch_0012)
**Last Audit**: 2025-02-07T00:00:00Z
**Issues Found**: 0 critical violations
**Notes**: File follows all BASE_RULES. Well-designed optional dependency pattern.

---
*Auto-generated requirements updated after audit on 2025-02-07*
