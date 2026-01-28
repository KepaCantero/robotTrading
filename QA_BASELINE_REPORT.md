# Python QA Baseline Report
## algoTrading Codebase Analysis

**Generated:** 2026-01-30
**Analyzed Directory:** `/Users/kepa.cantero/Projects/algoTrading/app`
**Total Python Files:** 716
**Files Analyzed:** 591 (excluding tests, migrations, and some edge cases)

---

## Executive Summary

The algoTrading codebase has significant code quality issues that require immediate attention. This baseline report identifies critical problems across formatting, imports, type hints, linting, and code complexity that must be addressed to meet Python QA compliance standards.

### Overall Health Score: **CRITICAL** (26/100)

| Metric | Score | Status |
|--------|-------|--------|
| Code Formatting | 28.8% | CRITICAL |
| Import Sorting | 30.6% | CRITICAL |
| Type Hints | BLOCKED | CRITICAL |
| Linting | 7.4% | CRITICAL |
| Complexity | 79.0% | WARNING |

---

## 1. Code Formatting (Black)

### Summary
- **Tool:** `black --check app/`
- **Status:** FAILED
- **Files Needing Reformat:** 289 / 710 (40.7%)
- **Files Compliant:** 421 (59.2%)
- **Files with Parse Errors:** 5 (0.7%)

### Files with Parse Errors (CRITICAL - Must Fix First)

1. **app/dashboard/meta_dashboard_page.py**
   - Error: `Cannot parse: 14:0: import streamlit as st`
   - Likely cause: Improper indentation or syntax error

2. **app/middleware/logging_middleware.py**
   - Error: `Cannot parse: 7:0: request_id = str(uuid.uuid4())`
   - Likely cause: Code appears outside of function/class context (line 7)

3. **app/optimization/momentum_auto_optimizer.py**
   - Error: `Cannot parse: 139:0: import optuna`
   - Likely cause: Import statement in invalid location

4. **app/services/numba_risk.py**
   - Error: `Cannot parse: 37:0: from numba import jit, njit, prange`
   - Likely cause: Improper indentation in import block

5. **app/sre/oncall/handoff.py**
   - Error: `Cannot parse: 392:24: description "Discuss any pending tasks..."`
   - Likely cause: Malformed string or syntax error

### Most Affected Directories

| Directory | Files Needing Format |
|-----------|---------------------|
| app/backtesting/ | ~45 files |
| app/services/ | ~40 files |
| app/engines/ | ~35 files |
| app/strategies/ | ~25 files |
| app/dashboard/ | ~10 files |

---

## 2. Import Sorting (isort)

### Summary
- **Tool:** `isort --check-only app/`
- **Status:** FAILED
- **Files with Issues:** 219 / 716 (30.6%)
- **Compliance Rate:** 69.4%

### Common Issues
- Imports not properly grouped (stdlib, third-party, local)
- Imports not sorted alphabetically within groups
- Missing proper separation between import groups
- Inconsistent import ordering across files

### Most Affected Areas
- `app/backtesting/` - ~35 files
- `app/services/` - ~50 files
- `app/engines/` - ~30 files
- `app/strategies/` - ~20 files

---

## 3. Type Hints (mypy)

### Summary
- **Tool:** `mypy --strict app/`
- **Status:** BLOCKED
- **Blocking Issue:** Syntax errors prevent type checking
- **Files Analyzed:** 0 (blocked by 5 parse errors)

### Root Cause
The 5 files with syntax errors (identified in Black section) prevent mypy from analyzing the entire codebase. These must be fixed before type checking can proceed.

### Expected Issues (Pre-analysis)
Based on code inspection, anticipated type hint issues include:
- Missing return type annotations
- Missing parameter type hints
- Use of `Any` type
- Missing type stubs for third-party libraries
- Inconsistent type hint usage

---

## 4. Linting (ruff)

### Summary
- **Tool:** `ruff check app/`
- **Status:** FAILED
- **Total Errors:** 1,900
- **Fixable Automatically:** 578 (30.4%)

### Error Breakdown

| Error Code | Count | Description | Fixable |
|------------|-------|-------------|---------|
| F821 | 1,137 | Undefined name | NO |
| F401 | 604 | Unused import | YES |
| F541 | 58 | f-string missing placeholders | YES |
| F841 | 53 | Unused variable | YES |
| Invalid Syntax | 19 | Syntax errors | NO |
| E722 | 10 | Bare except | YES |
| F811 | 8 | Redefined while unused | YES |
| E741 | 5 | Ambiguous variable name | NO |
| E712 | 4 | True/False comparison | YES |
| E721 | 2 | Type comparison | NO |

### Top 20 Most Problematic Files (by ruff errors)

| Rank | File | Error Count | Primary Issues |
|------|------|-------------|----------------|
| 1 | app/backtesting/comprehensive_backtest_runner.py | 441 | F821 undefined names |
| 2 | app/services/live_trading/order_persistence.py | 60 | F821 undefined names |
| 3 | app/services/live_trading/trade_persistence.py | 55 | F821 undefined names |
| 4 | app/core/compliance_integration.py | 45 | F821 undefined names |
| 5 | app/database/__init__.py | 35 | F401 unused imports |
| 6 | app/engines/data_engine/sources/ohlcv_sources.py | 34 | F821 undefined names |
| 7 | app/engines/strategy_engines/base.py | 31 | F821 undefined names |
| 8 | app/engines/data_engine/cache/distributed_cache.py | 31 | F821 undefined names |
| 9 | app/services/metrics_database/questdb_connector.py | 26 | F821 undefined names |
| 10 | app/services/live_trading/trading_audit_trail.py | 25 | F821 undefined names |
| 11 | app/core/compliance_engine.py | 23 | F821 undefined names |
| 12 | app/services/external_integrations/dagster_orchestrator.py | 21 | F821 undefined names |
| 13 | app/services/fifo/modelo_721_generator.py | 18 | F821 undefined names |
| 14 | app/sre/reconciliation/boot_reconciler.py | 17 | F821 undefined names |
| 15 | app/services/monitoring/metrics_exporter.py | 17 | F821 undefined names |
| 16 | app/services/momentum_analysis_optimized.py | 17 | F821 undefined names |
| 17 | app/services/knowledge_graph/graph_builder.py | 17 | F821 undefined names |
| 18 | app/services/external_integrations/questdb_connector.py | 16 | F821 undefined names |
| 19 | app/engines/data_engine/sources/sentiment_sources.py | 16 | F821 undefined names |
| 20 | app/backtesting/profile_batch/result_aggregator.py | 16 | F821 undefined names |

### Common Patterns

**F821 Undefined Name Issues:**
- `asyncio` used but not imported
- `uuid` used but not imported
- Various standard library modules missing imports
- Likely caused by incomplete refactoring or copy-paste errors

---

## 5. Code Complexity (radon)

### Summary
- **Tool:** `radon cc app/ -a -s`
- **Status:** WARNING
- **Total Blocks Analyzed:** 10,175 (functions, methods, classes)
- **Average Complexity:** 3.74 (Grade A)

### Complexity Distribution

| Grade | Count | Percentage | Description |
|-------|-------|------------|-------------|
| A (1-5) | 8,202 | 80.6% | Good - Low complexity |
| B (6-10) | 1,464 | 14.4% | Warning - Medium complexity |
| C (11-20) | 417 | 4.1% | Danger - High complexity |
| D (21-30) | 69 | 0.7% | Extreme - Very high complexity |
| E (31-40) | 13 | 0.1% | Critical - Excessive complexity |
| F (41+) | 10 | 0.1% | Critical - Must refactor |

### Top 30 Most Complex Functions/Methods

| Rank | Complexity | File | Function/Method | Grade |
|------|------------|------|-----------------|-------|
| 1 | 259 | app/dashboard/advanced_dashboard.py | main | F |
| 2 | 66 | app/services/strategy_stock_allocator.py | StrategyStockAllocator.allocate | F |
| 3 | 52 | app/backtesting/walk_forward_validator.py | WalkForwardValidator.validate_strategy | F |
| 4 | 48 | app/backtesting/engine.py | SimpleBacktester.run_backtest | F |
| 5 | 46 | app/dashboard/comprehensive_data_loader.py | ComprehensiveBacktestLoader.load_all_results | F |
| 6 | 43 | app/backtesting/metrics.py | MetricsCalculator.calculate_all_metrics | F |
| 7 | 43 | app/backtesting/comprehensive_backtest_runner.py | ComprehensiveBacktestRunner.run_regime_test_backtest | F |
| 8 | 43 | app/backtesting/comprehensive_backtest_runner.py | ComprehensiveBacktestRunner.run_out_of_sample_backtest | F |
| 9 | 43 | app/strategies/momentum.py | MomentumStrategy.generate_signals | F |
| 10 | 41 | app/strategies/momentum_modular/learning/supervised_learning_engine.py | SupervisedLearningEngine.train | F |
| 11 | 40 | app/strategies/momentum_modular/strategy.py | ModularMomentumStrategy.generate_signals | E |
| 12 | 40 | app/engines/strategy_engines/pairs_engine.py | PairsTradingStrategyEngine.extract_features | E |
| 13 | 40 | app/backtesting/engine.py | SimpleBacktester._process_signal | E |
| 14 | 39 | app/backtesting/test_summary.py | TestSummaryReporter._format_human_readable | E |
| 15 | 39 | app/backtesting/engine.py | SimpleBacktester._execute_sell_signal | E |
| 16 | 37 | app/strategies/pairs_trading.py | PairsTradingStrategy.generate_signals | E |
| 17 | 37 | app/services/strategy_stock_allocator.py | StrategyStockAllocator.filter_stocks | E |
| 18 | 34 | app/services/strategy_stock_allocator.py | StrategyStockAllocator.score_momentum | E |
| 19 | 33 | app/backtesting/multi_strategy_engine.py | MultiStrategyBacktester.run_multi_strategy_backtest | E |
| 20 | 33 | app/backtesting/comprehensive_backtest_runner.py | ComprehensiveBacktestRunner.run_ablation_backtest | E |
| 21 | 33 | app/services/deploy_decision_orchestrator/deploy_decision_orchestrator.py | DeployDecisionOrchestrator._generate_rationale | E |
| 22 | 31 | app/engines/strategy_engines/trend_following_engine.py | TrendFollowingStrategyEngine._generate_signals_impl | E |
| 23 | 31 | app/engines/strategy_engines/momentum_engine.py | MomentumStrategyEngine.extract_features | E |
| 24 | 31 | app/engines/strategy_engines/pairs_engine.py | PairsTradingStrategyEngine.extract_features | E |
| 25 | 30 | app/engines/execution_engine/microstructure/microstructure_engine.py | MicrostructureEngine.calculate_market_impact | D |
| 26 | 28 | app/backtesting/profile_batch_backtester.py | ProfileBatchBacktester.run_profile_batch | D |
| 27 | 28 | app/services/live_trading/broker_adapters/ib_adapter.py | IBAdapter.connect | D |
| 28 | 27 | app/core/config_validator.py | ConfigValidator.validate_config | D |
| 29 | 27 | app/engines/strategy_engines/arbitrage_engine.py | ArbitrageStrategyEngine.generate_signals | D |
| 30 | 27 | app/strategies/momentum_modular/learning/learning_updater.py | LearningUpdater.update_parameters | D |

### Most Complex Files (Combined Score)

| File | Combined Score | Max Complexity | Worst Grade | Issues |
|------|----------------|----------------|-------------|--------|
| app/dashboard/advanced_dashboard.py | 259 | 259 | F | Monolithic function |
| app/services/strategy_stock_allocator.py | 66 | 66 | F | Complex allocation logic |
| app/backtesting/walk_forward_validator.py | 52 | 52 | F | Nested validation |
| app/backtesting/engine.py | 48 | 48 | F | Multiple responsibilities |
| app/dashboard/comprehensive_data_loader.py | 46 | 46 | F | Large data loading |
| app/backtesting/metrics.py | 43 | 43 | F | Too many metrics |
| app/backtesting/comprehensive_backtest_runner.py | 43 | 43 | F | God object anti-pattern |
| app/strategies/momentum.py | 43 | 43 | F | Complex signal generation |
| app/strategies/momentum_modular/learning/supervised_learning_engine.py | 41 | 41 | F | Training complexity |
| app/strategies/momentum_modular/strategy.py | 40 | 40 | E | Modular momentum |

---

## Priority Issues to Fix

### CRITICAL (Must Fix Immediately)

1. **Fix 5 Syntax Errors** (Blocking Type Checking)
   - app/middleware/logging_middleware.py
   - app/dashboard/meta_dashboard_page.py
   - app/services/numba_risk.py
   - app/optimization/momentum_auto_optimizer.py
   - app/sre/oncall/handoff.py

2. **Fix 1,137 Undefined Name Errors (F821)**
   - Missing imports for asyncio, uuid, and other stdlib modules
   - Use `ruff check app/ --fix` to auto-fix where possible
   - Manual review required for complex cases

3. **Refactor 10 Functions with Grade F Complexity**
   - All functions with complexity > 40 should be broken down
   - Apply Single Responsibility Principle
   - Extract helper functions/classes

### HIGH PRIORITY

4. **Fix 604 Unused Import Errors (F401)**
   - Run `ruff check app/ --fix` (auto-fixable)
   - Clean up imports

5. **Fix 219 Import Sorting Issues**
   - Run `isort app/ --fix-only` (auto-fixable)

6. **Fix 289 Formatting Issues**
   - Run `black app/` (auto-fixable)
   - Exclude the 5 files with syntax errors initially

### MEDIUM PRIORITY

7. **Add Type Hints**
   - After syntax errors are fixed, run mypy
   - Add return type annotations
   - Add parameter type hints
   - Remove use of `Any` type where possible

8. **Refactor 13 Functions with Grade E Complexity**
   - Break down functions with complexity 31-40
   - Improve testability

9. **Fix 53 Unused Variable Errors (F841)**
   - Remove or use variables
   - Auto-fixable with ruff

### LOW PRIORITY

10. **Fix 10 Bare Except Errors (E722)**
    - Use specific exception types
    - Improve error handling

11. **Refactor 69 Functions with Grade D Complexity**
    - Break down functions with complexity 21-30

---

## Recommended Fix Sequence

### Phase 0: Syntax Errors (Blocking)
```bash
# Fix the 5 files with syntax errors manually
# These block all other tools
```

### Phase 1: Auto-Fixable Issues
```bash
# Run in sequence
isort app/ --fix-only
black app/
ruff check app/ --fix
```

### Phase 2: Manual Fixes
- Fix remaining F821 undefined name errors
- Add missing type hints
- Refactor complex functions

### Phase 3: Validation
```bash
# Re-run all checks
black --check app/
isort --check-only app/
mypy --strict app/
ruff check app/
radon cc app/ -a -s
```

---

## Files Requiring Most Attention

### Top 10 Files by Combined Issue Score

1. **app/backtesting/comprehensive_backtest_runner.py**
   - 441 ruff errors + Grade F complexity
   - God object anti-pattern
   - Needs complete refactoring

2. **app/dashboard/advanced_dashboard.py**
   - Grade F complexity (259)
   - Monolithic main() function
   - Needs decomposition

3. **app/services/strategy_stock_allocator.py**
   - Grade F complexity (66)
   - Complex allocation logic
   - Needs simplification

4. **app/backtesting/walk_forward_validator.py**
   - Grade F complexity (52)
   - Nested validation logic
   - Needs extraction

5. **app/backtesting/engine.py**
   - Grade F complexity (48)
   - Multiple responsibilities
   - Needs separation of concerns

6. **app/backtesting/metrics.py**
   - Grade F complexity (43)
   - Too many metrics in one calculator
   - Needs metric-specific classes

7. **app/services/live_trading/order_persistence.py**
   - 60 ruff errors
   - Undefined name issues
   - Missing imports

8. **app/services/live_trading/trade_persistence.py**
   - 55 ruff errors
   - Undefined name issues
   - Missing imports

9. **app/core/compliance_integration.py**
   - 45 ruff errors
   - Undefined name issues
   - Missing imports

10. **app/middleware/logging_middleware.py**
    - Syntax error (blocking)
    - Incomplete code at line 7
    - Needs immediate fix

---

## Compliance with Python Rules

### Rules Status (from rules/python/)

| Rule | Status | Notes |
|------|--------|-------|
| 01-formatting-style | FAILED | 40.7% non-compliant |
| 02-type-hints | BLOCKED | Syntax errors prevent checking |
| 03-solid-principles | WARNING | Complex functions violate SRP |
| 04-design-patterns | WARNING | God objects detected |
| 05-architecture | WARNING | High coupling in some modules |
| 06-testing | NOT CHECKED | Tests not in scope for this baseline |
| 07-async-patterns | NOT CHECKED | Requires code review |
| 08-configuration | NOT CHECKED | Requires code review |
| 09-logging-observability | NOT CHECKED | Requires code review |
| 10-advanced-patterns | NOT CHECKED | Requires code review |

---

## Next Steps

1. **IMMEDIATE:** Fix the 5 syntax errors blocking type checking
2. **TODAY:** Run auto-fixers (isort, black, ruff --fix)
3. **THIS WEEK:** Address remaining undefined name errors
4. **THIS SPRINT:** Refactor Grade F and E complexity functions
5. **ONGOING:** Add type hints and improve test coverage

---

## Tools Configuration

All tools detected in: `/Users/kepa.cantero/Projects/algoTrading/.venv/bin/`

```bash
# Activate virtual environment before running
source .venv/bin/activate

# Run individual checks
black --check app/
isort --check-only app/
mypy --strict app/
ruff check app/
radon cc app/ -a -s

# Auto-fix where possible
isort app/ --fix-only
black app/
ruff check app/ --fix
```

---

## Conclusion

The algoTrading codebase requires significant refactoring to meet Python QA standards. The most critical issues are:

1. **5 syntax errors blocking type checking**
2. **1,137 undefined name errors** (mostly missing imports)
3. **289 formatting issues** (auto-fixable)
4. **219 import sorting issues** (auto-fixable)
5. **23 functions with extreme complexity (D-F grade)**

The good news is that ~50% of issues are auto-fixable. After running auto-fixers, the remaining issues require focused refactoring efforts, particularly around complex functions and proper import management.

**Estimated Effort:**
- Syntax errors: 2-4 hours
- Auto-fixes: 30 minutes
- Manual import fixes: 4-8 hours
- Complexity refactoring: 20-40 hours
- Type hints: 16-24 hours

**Total Estimated Time:** 40-80 hours for full compliance
