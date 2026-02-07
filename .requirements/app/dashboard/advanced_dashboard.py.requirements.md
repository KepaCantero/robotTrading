# Requirements: dashboard/advanced_dashboard.py

## Source File Analysis
- **File Path**: `app/dashboard/advanced_dashboard.py`
- **Lines of Code:** 2608
- **Status:** AUDITED - PASSED
- **Audit Date:** 2026-02-07
- **Batch:** 0090

## Purpose
Advanced Visual Dashboard for AlgoTrading Backtesting with Streamlit. Comprehensive web-based dashboard with design improvements, colorized indicators, and visual configuration. Provides Mission Control interface for quantitative trading with real-time backtest execution, results visualization, training analysis, and integration objectives tracking.

## Dependencies
### Internal
- `app.dashboard.comprehensive_data_loader`: ComprehensiveBacktestLoader
- `app.backtesting.comprehensive_backtest_runner`: ComprehensiveBacktestRunner (lazy loaded)
- `app.backtesting.successful_configs`: SuccessfulConfigManager

### External
- `streamlit`: Web dashboard framework (imported FIRST)
- `plotly`: Interactive visualizations (px, go, make_subplots)
- `pandas`: Data manipulation
- `yaml`: Configuration file parsing
- `pathlib`: File operations
- `typing`: Type hints
- `logging`: Logging
- `datetime`: Time handling
- `json`: JSON serialization

### Critical Initialization
Environment variables MUST be set BEFORE importing numpy/pandas/torch:
- `OMP_NUM_THREADS=1`: Prevent threading conflicts
- `OPENBLAS_NUM_THREADS=1`: Prevent threading conflicts
- `MKL_NUM_THREADS=1`: Prevent threading conflicts
- `KMP_DUPLICATE_LIB_OK=TRUE`: Allow duplicate libs
- `PYTORCH_ENABLE_MPS_FALLBACK=1`: PyTorch fallback
- `TF_CPP_MIN_LOG_LEVEL=2`: Reduce TensorFlow logging
- `CUDA_VISIBLE_DEVICES=""`: Disable CUDA

## Classes/Functions

### Configuration Functions
- `load_thresholds(config_path)`: Load metric thresholds from config
  - Default thresholds: sharpe (0.0, 0.8, 1.5), drawdown (15, 10, 5), winrate (0.4, 0.55, 0.65), return_pct (0, 10, 25)

- `get_metric_color(value, metric, thresholds)`: Get color and emoji for metric
  - Returns: (color_class, emoji)
  - Classes: excellent, good, warn, bad

- `render_metric_card(label, value, metric, thresholds, format_str)`: Render metric card with dynamic color

### Integration Test Objectives
- `get_integration_test_objectives()`: Define metric objectives for integration tests
  - max_drawdown: < 20%
  - sharpe_ratio: > 1.2
  - sortino_ratio: > 1.5
  - annualized_volatility: 10-15%
  - profit_factor: > 1.4
  - win_rate: 45-60%

- `evaluate_objective(metric_name, value, objectives)`: Evaluate if metric meets objective
- `evaluate_all_objectives(metrics, objectives)`: Evaluate all metrics against objectives
- `extract_strategy_config(result_row)`: Extract strategy configuration from result

### Main Function
- `main()`: Dashboard main entry point
  - Sets page config (MUST be first Streamlit call)
  - Configures environment variables
  - Initializes session state
  - Creates sidebar with configuration
  - Creates main content tabs
  - Handles test execution

### Dashboard Tabs

#### Tab 1: Dashboard Overview
- KPI cards with color coding
- Top performers display
- Performance distribution charts
- Learning engines status indicator

#### Tab 2: Individual Results
- Filter by test type
- Sort by metrics
- Limit results
- Display individual test details

#### Tab 3: Training Analysis
- Before/After training comparison
- Learning engine results with training data
- Metrics comparison charts
- Improvement percentages

#### Tab 4: Saved Configurations
- Save current configuration
- List saved configurations
- Filter by metrics
- Load saved config

#### Tab 5: Integration Objectives
- Display integration test objectives
- Evaluate strategies against objectives
- Show passing strategies
- Display detailed metrics

#### Tab 6: Comparison View
- Multi-select for comparison
- Metrics comparison chart
- Detailed comparison table

#### Tab 7: Load Results
- Load from directory
- Display available files

## Business Logic

### Dashboard Flow
1. Load existing results or show setup info
2. Display KPI cards with color coding
3. Show top performers
4. Display performance distributions
5. Allow filtering and sorting
6. Execute selected tests on demand

### Test Execution
1. Configure tests in sidebar
2. Select learning engines
3. Configure parameters
4. Click EXECUTE button
5. Load ComprehensiveBacktestRunner (lazy loading)
6. Run tests
7. Display results
8. Update dashboard

### Multi-Strategy Mode
- Select multiple strategies
- Enable dynamic capital reallocation
- Configure reallocation frequency
- Test strategy combinations

## Data Models

### Session State
```python
{
    "backtest_config": dict,
    "results_loaded": bool,
    "df_results": DataFrame,
    "execute_tests": bool,
    "selected_tests": list,
    "execution_params": dict
}
```

### Configuration Structure
```yaml
input:
  symbol: str
  start_date: date
  end_date: date
  initial_capital: float

learning_engines:
  supervised: {enabled: bool}
  deep: {enabled: bool}
  reinforcement: {enabled: bool}
  transformer: {enabled: bool}

backtests:
  baseline: {enabled: bool}
  learning_engines: {enabled: bool}
  monte_carlo: {enabled: bool}
  ...
```

## API Contracts

### Public Interface
```bash
# Run dashboard
streamlit run app/dashboard/advanced_dashboard.py

# Dashboard will be available at
# http://localhost:8501
```

## Error Handling

### Exception Handling Strategy
- Generic exception catch in main()
- Try-catch for data loader initialization
- Try-catch for config loading
- Try-catch for test execution
- All errors displayed to user

### Error Recovery
- Shows helpful messages on errors
- Suggests troubleshooting steps
- Continues operation when possible
- Fallback to minimal interface on critical error

## Performance Considerations
- Lazy loading of ComprehensiveBacktestRunner (prevents threading issues)
- Session state caching
- Vectorized operations where possible
- Efficient DataFrame operations
- Progress bars for long operations

### Thread Safety
- Environment variables set BEFORE imports
- Single-threaded BLAS/MKL operations
- PyTorch MPS fallback enabled
- Duplicate library handling

## Testing Strategy

### Unit Tests
1. Test threshold loading
2. Test metric color calculation
3. Test objective evaluation
4. Test config extraction
5. Test view rendering

### Integration Tests
1. Test dashboard initialization
2. Test test execution flow
3. Test result loading
4. Test configuration saving/loading
5. Test multi-strategy mode

### Edge Cases
1. No results available
2. Configuration file missing
3. Test execution failures
4. Learning engine failures
5. Missing data fields

## UI/UX Considerations

### Visual Design
- Gradient metric cards (bad, warn, good, excellent)
- Color-coded indicators
- Emoji status symbols
- Professional gradient headers

### User Experience
- Intuitive sidebar configuration
- Clear execution feedback
- Progress indicators
- Helpful error messages
- Responsive layout

### Configuration
- Threshold customization
- Strategy mode selection
- Learning engine selection
- Execution parameters
- Multi-strategy settings

## Security Considerations
- No hardcoded credentials
- Configurable paths
- No sensitive data in logs
- Input validation
- File path validation

## Compliance & Standards
- Type hints throughout
- Comprehensive docstrings
- Structured logging
- Proper exception handling
- Path operations using pathlib

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0090 GAP Audit)
**Batch:** 0090

### BASE_RULES Verification

✅ **SEC-001**: No hardcoded secrets detected
✅ **LOG-004**: Comprehensive error logging with context
✅ **LOG-005**: No sensitive data in logs (test metadata only)
✅ **LOG-006**: Structured logging
✅ **ERR-001**: Proper exception handling
✅ **ERR-002**: All exceptions logged with context
✅ **DAT-001**: Uses timezone-aware datetime
✅ **DAT-003**: Proper JSON serialization
✅ **UI-001**: Professional visual design
✅ **UI-002**: Color-coded indicators
✅ **UI-003**: Responsive layout
✅ **PERF-001**: Vectorized operations
✅ **PERF-002**: Lazy loading for performance
✅ **PERF-003**: Session state caching
✅ **THR-001**: Thread safety (environment variables)
✅ **THR-002**: Single-threaded BLAS operations

### Notes
- Well-documented with clear purpose
- Comprehensive dashboard implementation
- Proper thread safety for numerical libraries
- Production-ready with no P0 or P1 violations
- Professional UI design
- Excellent user experience

### Recommendations (Future Enhancements)
1. Add real-time data streaming
2. Implement user authentication
3. Add dashboard export functionality
4. Implement collaboration features
5. Add more visualization types
6. Implement custom dashboard layouts
7. Add mobile responsiveness

---
*Requirements updated: 2026-02-07*
*Audit completed: Batch 0090*
