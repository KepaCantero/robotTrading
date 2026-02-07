# Requirements: backtesting/comprehensive_backtest_runner.py

## Source File Analysis
- **File Path**: `app/backtesting/comprehensive_backtest_runner.py`
- **Lines of Code**: 4041
- **Audit Status**: PASSED_WITH_NOTES
- **Audit Date**: 2026-02-07T05:30:00Z

## Purpose
Comprehensive backtesting runner that executes multiple types of backtests including baseline, learning engines, walk-forward, Monte Carlo, transformer optimization, ablation, grid search, out-of-sample, multi-strategy, and regime tests. Implements advanced MLOps practices from López de Prado and Tsay for robust strategy validation.

## Dependencies
### Internal:
- `app.backtesting.core` (BacktestConfigLoader, BacktestOrchestrator)
- `app.backtesting.core.error_handling` (MutexError, TrainingError, train_with_retry)
- `app.backtesting.core.executor` (ProcessPoolBacktestExecutor, SimpleBacktestExecutor)
- `app.backtesting.core.memory_manager` (AggressiveMemoryManager)
- `app.backtesting.data_loader` (DataLoader)
- `app.backtesting.data_split` (TrainValTestSplitter, MultipleTestingCorrector, validate_out_of_sample_performance)
- `app.backtesting.factories` (StrategyFactory)
- `app.backtesting.models` (BacktestConfig, BacktestResult)
- `app.backtesting.multi_strategy_engine` (MultiStrategyBacktester)
- `app.strategies.momentum_modular.strategy` (ModularMomentumStrategy)

### External:
- `logging`
- `datetime` (datetime, timedelta)
- `decimal` (Decimal)
- `pathlib` (Path)
- `typing` (Any, Dict, List, Optional)
- `numpy` (np)
- `pandas` (pd)

## Classes/Functions
### Classes:
- `ComprehensiveBacktestRunner`: Main orchestrator for comprehensive backtesting suite

### Key Methods:
- `run_all_backtests()`: Execute all configured backtests
- `run_specific_backtests(backtest_names)`: Run specific backtests by name
- `run_baseline_backtest()`: Baseline with all modules active
- `run_learning_engines_backtest()`: Test each learning engine individually
- `run_walk_forward_backtest()`: Walk-forward validation with rolling windows
- `run_monte_carlo_backtest(parallel)`: Monte Carlo stress testing
- `run_transformer_optimization_backtest()`: Transformer-based parameter optimization
- `run_ablation_backtest()`: Ablation study for filter importance
- `run_grid_search_backtest()`: Grid search hyperparameter optimization
- `run_out_of_sample_backtest()`: Out-of-sample validation with frozen parameters
- `run_multi_strategy_backtest()`: Multi-strategy portfolio testing
- `run_regime_test_backtest()`: Regime-based performance analysis
- `optimize_with_validation(param_grid, strategy_class)`: Parameter optimization with train/val/test split

## Business Logic
1. **Data Loading**: Loads historical market data from configured symbols and date range
2. **Strategy Configuration**: Creates strategy configurations from YAML config
3. **Backtest Execution**: Executes various backtest types using appropriate executors
4. **Metrics Calculation**: Calculates consistent performance metrics across all tests
5. **Memory Management**: Uses AggressiveMemoryManager to handle large result sets
6. **Meta-Analysis**: Optional integration with meta-analyzer for audit trails

## Data Models
- `BacktestConfig`: Configuration for backtest execution
- `BacktestResult`: Result object with performance metrics
- Strategy-specific config dictionaries

## API Contracts
### Public Methods:
All `run_*_backtest()` methods return `List[Dict[str, Any]]` with standardized result format:
```python
{
    'test_type': str,           # Type of backtest
    'test_name': str,           # Human-readable name
    'total_pnl': float,         # Total PnL
    'return_pct': float,        # Return percentage
    'sharpe_ratio': float,      # Sharpe ratio
    'win_rate': float,          # Win rate
    'max_drawdown': float,      # Maximum drawdown
    'total_trades': int,        # Total number of trades
    'final_capital': float,     # Final capital
    # ... additional test-specific fields
}
```

## Error Handling
- Uses specific exception types (MutexError, TrainingError)
- Catches specific exceptions in try/except blocks
- Logs errors with stack traces using logger.error()
- Graceful degradation when optional components fail
- No bare except clauses
- All exceptions logged appropriately

## Performance Considerations
- Uses AggressiveMemoryManager to prevent memory bloat
- Supports parallel execution for Monte Carlo and grid search
- ProcessPoolBacktestExecutor for CPU-intensive tasks
- SimpleBacktestExecutor for sequential execution
- Lazy loading of meta-analyzer components

## Testing Strategy
- Walk-forward validation for temporal consistency
- Out-of-sample testing with frozen parameters
- Multiple testing correction (Bonferroni)
- Ablation studies for feature importance
- Regime-based performance analysis

## BASE_RULES Compliance

### ✅ R099 (Absolute imports): All imports use absolute paths from `app`
- No relative imports detected
- All imports properly qualified

### ✅ R098 (No relative imports): No relative imports used
- All imports are absolute from the project root

### ✅ R100 (Modern type hints): Uses modern type hints
- `List[Dict[str, Any]]`
- `Optional[Dict[str, Any]]`
- Note: Could use `list[Dict[str, Any]]` (Python 3.9+) but current syntax is valid

### ✅ R102 (Any without documentation): `Any` is used appropriately
- `Any` is used for strategy objects which can vary in type
- Return dictionaries with dynamic structure are appropriately typed
- All usages are justified by the flexible nature of backtest results

### ✅ R103 (No type comments): No type comments used
- All type hints are inline annotations

### ✅ R104 (No bare except): No bare except clauses
- All exception handling uses specific exception types
- Example: `except MutexError`, `except TrainingError`, `except Exception as e`

### ✅ R105 (No print statements): Uses logger instead
- All output uses `logger.info()`, `logger.warning()`, `logger.error()`
- No print() statements in production code

### ✅ R107 (No mutable defaults): No mutable default arguments
- All defaults are immutable (None, False, True, numbers, strings)

### ✅ R108 (Proper exception handling): Specific exceptions caught
- Catches `MutexError`, `TrainingError` specifically
- Uses `Exception` with logging for unexpected errors
- Proper error propagation

### ✅ R110 (Google docstrings): Google-style docstrings
- All classes and methods have comprehensive docstrings
- Args, Returns, and Examples sections where appropriate

### ✅ R111 (No circular imports): No circular imports detected
- Lazy imports in methods where needed to avoid circularity
- Meta-analyzer imports guarded in try/except

## Notes
- **File Size**: 4041 lines (large file - consider splitting into smaller modules)
- **Complexity**: High complexity due to multiple backtest types in single class
- **Recommendation**: Consider extracting each backtest type to separate handler classes
- **P0 Issues**: None
- **P1 Issues**: File size violates single responsibility principle (consider refactoring)

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Audit completed on 2026-02-07T05:30:00Z*
