# multi_strategy_engine.py

## Purpose
Multi-strategy backtesting engine with capital allocation. Manages simultaneous backtests across multiple strategies with intelligent stock allocation and dynamic capital reallocation.

---

## Type Definitions / Data Classes

### MultiStrategyBacktester Class
```python
class MultiStrategyBacktester:
    allocation_manager: MultiStrategyAllocationManager  # REQUIRED - Manages capital allocation
    strategies: Dict[str, BaseStrategy]                 # REQUIRED - Strategy instances
    config_params: Dict                                 # REQUIRED - Common backtest parameters
    portfolio_config: PortfolioConfigManager            # REQUIRED - Sector filtering config
    enable_diagnostics: bool                            # OPTIONAL - Enable diagnostic logging
    early_abort_loss_pct: Decimal                       # OPTIONAL - Abort threshold (default: 20%)
    enable_dynamic_reallocation: bool                   # OPTIONAL - Enable dynamic rebalancing
    reallocation_frequency_days: int                    # OPTIONAL - Days between reallocations
    stock_allocator: StrategyStockAllocator             # REQUIRED - Intelligent stock assignment
    reallocation_engine: DynamicCapitalReallocationEngine | None  # Optional - Dynamic rebalancing
```

**Validation Rules:**
- `total_capital` must be positive Decimal
- `early_abort_loss_pct` must be between 0 and 1 (as Decimal)
- `reallocation_frequency_days` must be positive (default: 30)
- Stock allocation validation must pass for use_allocator=True

---

## Function Signatures (Contracts)

### `MultiStrategyBacktester.__init__(...) -> None`
**Pre:** allocation_manager and strategies must be valid, config_params must have required keys
**Post:** All components initialized, diagnostic logger created if enabled
**Raises:** ValueError for invalid allocation manager
**Retry:** ❌ No
**Side Effects:** Initializes allocators, engines, creates output directories

### `MultiStrategyBacktester.run_multi_strategy_backtest(quotes, start_date, end_date) -> Dict[str, Dict]`
**Pre:** quotes must contain market data for all symbols, dates must be valid range
**Post:** Returns consolidated dict with per_strategy and combined metrics
**Raises:** Value/Type/Key/Attribute/Index errors for invalid inputs (logged, continues)
**Retry:** ✅ Yes (individual strategy failures don't stop batch)
**Side Effects:** Runs backtests, generates signals, updates reallocation engine, saves diagnostic report

### `MultiStrategyBacktester._create_empty_result(strategy_name, initial_capital, start_date, end_date) -> BacktestResult`
**Pre:** All parameters must be valid
**Post:** Returns BacktestResult with zero metrics
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (creates object only)

### `MultiStrategyBacktester._consolidate_results(results_by_strategy, capital_allocations) -> Dict`
**Pre:** results_by_strategy must have BacktestResult for each strategy
**Post:** Returns dict with per_strategy, combined, allocation, results keys
**Raises:** None (uses defaults for missing values)
**Retry:** ❌ No
**Side Effects:** None (aggregation only)

### `MultiStrategyBacktester._calculate_weighted_sharpe(results_by_strategy, capital_allocations) -> float`
**Pre:** results must have sharpe_ratio, capital_allocations must match
**Post:** Returns capital-weighted average Sharpe ratio
**Raises:** None (returns 0.0 if no valid Sharpe ratios)
**Retry:** ❌ No
**Side Effects:** None (calculation only)

### `MultiStrategyBacktester._calculate_weighted_max_dd(results_by_strategy, capital_allocations) -> float`
**Pre:** results must have max_drawdown, capital_allocations must match
**Post:** Returns capital-weighted average max drawdown
**Raises:** None (returns 0.0 if no valid drawdowns)
**Retry:** ❌ No
**Side Effects:** None (calculation only)

### `MultiStrategyBacktester.get_allocation_summary() -> Dict[str, Any]`
**Pre:** allocation_manager must be initialized
**Post:** Returns dict with allocated_capital, weight, target_weight, min_weight, max_weight
**Raises:** None (uses defaults)
**Retry:** ❌ No
**Side Effects:** None (read-only)

### `MultiStrategyBacktester._filter_quotes_by_strategy(quotes, strategy_name) -> List[Quote]`
**Pre:** portfolio_config must be initialized
**Post:** Returns filtered quotes for strategy's allowed sectors
**Raises:** None (returns all quotes if no sectors configured)
**Retry:** ❌ No
**Side Effects:** None (filtering only)

### `MultiStrategyBacktester._convert_quotes_to_dataframe_dict(quotes) -> Dict[str, pd.DataFrame]`
**Pre:** quotes must be valid list of Quote objects
**Post:** Returns dict mapping symbol to DataFrame with OHLCV data
**Raises:** None (returns empty dict on errors)
**Retry:** ❌ No
**Side Effects:** None (transformation only)

### `MultiStrategyBacktester._filter_quotes_by_allocator(quotes, strategy_name) -> List[Quote]`
**Pre:** allocation_result must be populated from allocator
**Post:** Returns quotes filtered to assigned symbols
**Raises:** None (falls back to portfolio config filtering)
**Retry:** ❌ No
**Side Effects:** None (filtering only)

---

## Acceptance Criteria
- [ ] run_multi_strategy_backtest() uses StrategyStockAllocator for intelligent stock assignment
- [ ] run_multi_strategy_backtest() falls back to portfolio config if allocator fails
- [ ] Each strategy gets allocated capital from MultiStrategyAllocationManager
- [ ] Signals generated only for quotes filtered to strategy's assigned symbols
- [ ] Diagnostic logger tracks signal candidates, signal counts, errors
- [ ] Early abort triggers if loss > threshold in first 2 years
- [ ] Dynamic capital reallocation engine updates after each strategy backtest
- [ ] Consolidated results include per-strategy and combined metrics
- [ ] Combined metrics use capital-weighted averages
- [ ] Stock allocation validation errors are logged but don't crash
- [ ] Empty results (no signals) create BacktestResult with zero metrics
- [ ] Reallocation engine linked to SimpleBacktester for performance tracking
- [ ] All exceptions caught and logged without stopping batch
- [ ] Fallback to portfolio config when allocator unavailable
- [ ] Residual capital tracked in allocation results

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - Config from params |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - exc_info=True used |
| TYP-001 | BASE_RULES.md | 100% type coverage | ❌ GAP - Some methods lack type hints |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Orchestrator pattern |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Coordinates strategies |
| DP-004 | BASE_RULES.md | Dependency injection | ✅ OK - All dependencies injected |
| TRD-002 | BASE_RULES.md | Risk validation | ✅ OK - Risk envelope enabled |
| TRD-003 | BASE_RULES.md | Position limits | ✅ OK - Max position size enforced |
| TRD-004 | BASE_RULES.md | Audit trail logging | ⚠️ PARTIAL - Diagnostic logging present |
| QL-001 | BASE_RULES.md | Complexity < 10 | ❌ GAP - run_multi_strategy_backtest is 200+ lines |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** pandas, logging, decimal, datetime, collections
- **Internal:**
  - `app.backtesting.engine.SimpleBacktester`
  - `app.backtesting.models.BacktestConfig, BacktestResult`
  - `app.backtesting.signal_diagnostic_logger.SignalDiagnosticLogger`
  - `app.core.centralized_config.StockAllocationSettings`
  - `app.services.dynamic_capital_reallocation.DynamicCapitalReallocationEngine`
  - `app.services.multi_strategy_allocation.MultiStrategyAllocationManager`
  - `app.services.portfolio_config_manager.PortfolioConfigManager, get_portfolio_config_manager`
  - `app.services.strategy_stock_allocator.StrategyStockAllocator`
  - `app.strategies.base.BaseStrategy`
  - `app.models.market_data.Quote`

---

## Required Tests
- **tests/backtesting/test_multi_strategy_engine.py:**
  - Test __init__() initializes all components
  - Test __init__() creates diagnostic logger when enabled
  - Test __init__() initializes reallocation engine when enabled
  - Test run_multi_strategy_backtest() returns consolidated results
  - Test run_multi_strategy_backtest() uses StrategyStockAllocator
  - Test run_multi_strategy_backtest() falls back on allocator failure
  - Test run_multi_strategy_backtest() allocates capital per strategy
  - Test run_multi_strategy_backtest() generates signals per strategy
  - Test run_multi_strategy_backtest() filters quotes by allocator
  - Test run_multi_strategy_backtest() handles empty signals gracefully
  - Test run_multi_strategy_backtest() creates empty result when no signals
  - Test run_multi_strategy_backtest() performs early abort check
  - Test run_multi_strategy_backtest() saves diagnostic report
  - Test _consolidate_results() calculates weighted Sharpe correctly
  - Test _consolidate_results() calculates weighted max DD correctly
  - Test _consolidate_results() returns correct structure
  - Test _calculate_weighted_sharpe() returns correct weighted average
  - Test _calculate_weighted_max_dd() returns correct weighted average
  - Test get_allocation_summary() returns allocation details
  - Test _filter_quotes_by_strategy() filters to allowed sectors
  - Test _filter_quotes_by_strategy() returns all if no sectors
  - Test _convert_quotes_to_dataframe_dict() creates correct DataFrames
  - Test _convert_quotes_to_dataframe_dict() sorts by timestamp
  - Test _filter_quotes_by_allocator() filters to assigned symbols
  - Test _filter_quotes_by_allocator() includes pairs for pairs_trading
  - Test _filter_quotes_by_allocator() falls back to portfolio config
  - Test _create_empty_result() creates valid BacktestResult
  - Test reallocation engine updated after each strategy
  - Test exceptions logged but don't stop batch
  - Test all emoji log messages render correctly

---

## Notes
- Comprehensive logging with emoji indicators (📊, ✅, ❌, ⚠️)
- run_multi_strategy_backtest() is very long (200+ lines) - consider refactoring
- Dynamic capital reallocation engine linked to SimpleBacktester
- StrategyStockAllocator used for intelligent stock-to-strategy assignment
- Fallback mechanism when allocator fails (logs warning, uses portfolio config)
- Diagnostic logging tracks signal generation pipeline
- Early abort feature prevents running bad strategies too long
- Residual capital tracked but not reallocated in current implementation
- Reallocation engine updates after each strategy completes backtest
- Multi-strategy results include per-strategy and combined metrics
- Capital-weighted metrics used for combined Sharpe and max DD
- Quotes conversion to DataFrame format for allocator compatibility
- Pair trading strategy gets both tickers from assigned pairs
- Sample symbols logging for debugging (first 10)
- Comprehensive error handling with specific exception types
- Lines 299-311: Critical fixes commentary for SimpleBacktester integration
- Lines 338-350: Allocation summary logged with validation status
- Spanish comments in some error handling
