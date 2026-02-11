# Session Handoff - Task 22: Code Quality Refactor

_Updated: 2026-02-11_

## Git Context

- **Branch:** `develop`
- **HEAD:** 7cfc63c2: ralph compliance

## Current Task

**Task 22: Code Quality Refactor - Production-Ready**

### Objective
Process ALL files ONE AT A TIME, for EACH file:
1. **Find hardcoded values** → Fix (Decimal("0.XX"), 0.02, 0.05, 0.15, 2.0, Spain tax rates)
2. **Find manual calculations** → Fix with specialized libraries (numpy, pandas, scipy)
3. **Find incomplete functions** → Fix (raise NotImplementedError, pass # stub, TODO/FIXME)
4. **Find production issues** → Fix (anything preventing production-ready code)
5. **Audit against .requirements.md** → Fix violations
6. **Validate** → If fails, fix again, re-validate
7. **Next file**

NO scripts - Use Read/Edit/Grep tools directly.

### Progress This Session (2026-02-11)

#### Files Fixed (3 new files this session)

1. **`app/services/advanced_risk_manager.py`** - FIXED:
   - Added `_get_risk_config()` helper function
   - `TradeRiskLimiter`: 0.02 -> `_get_risk_config('max_risk_per_trade', 0.02)`
   - `RiskRewardValidator`: 3.0 -> `_get_risk_config('min_reward_ratio', 3.0)`
   - `StrategyExposureLimiter`: 0.50/0.30 -> `_get_risk_config()` for each strategy
   - `DrawdownMonitor`: 0.15 -> `_get_risk_config('max_drawdown_pct', 0.15)`
   - `AdvancedRiskManager`: Fixed broken `getattr(config.trading)` reference (line 405)

2. **`app/dashboard/data_loader.py`** - FIXED:
   - Implemented `_get_strategy_status()` - checks backtest results and paper trading logs
   - Implemented `_get_last_pnl()` - retrieves PnL from results or logs with regex parsing
   - Removed 2 TODO comments with complete implementations

3. **Verified Already Production-Ready**:
   - `app/services/risk_scaling/limit_adjuster.py` - uses `_get_config_limit()` helper
   - `app/portfolio/multi_asset/asset_class.py` - uses `_get_asset_config()` helper

### Inventory Status
- Total Python files: 882
- Files fixed this session: 3
- Files remaining with issues: ~82
- Most remaining issues are in config files (where defaults are acceptable)

### Key Findings
1. **Config file defaults are acceptable**: Values like `0.02` in `Field(default=0.02)` are configuration defaults, not business logic hardcoded values
2. **Base class NotImplementedError is acceptable**: `EventHandler` and `OrderEventHandler` raise `NotImplementedError` to enforce implementation - this is correct OOP pattern
3. **Mathematical fallbacks are acceptable**: `volatility = 0.02` when no data available is a reasonable default, not a business rule

### Next Priority Files
Based on audit, files that may still need attention:
1. `app/strategies/pairs_trading.py` - has some hardcoded values (already uses config for most)
2. `app/microstructure/liquidity.py` - has fallback defaults (mathematical, not business logic)
3. `app/core/compliance_engine.py` - already has `ComplianceConfig` class

### Config System Status
- Config system is comprehensive with most needed fields in `TradingThresholds`
- `SpainTaxConfig` available for Spain-specific tax rules
- Helper pattern: `_get_config_limit()`, `_get_asset_config()`, `_get_risk_config()`

## Completion Criteria

Task COMPLETE when FOR EACH FILE:
- [ ] Find hardcoded values → Fixed with getattr(config.trading, 'param', default)
- [ ] Find manual calculations → Fixed with numpy/pandas/scipy
- [ ] Find incomplete functions → Fixed (NotImplementedError, stubs, TODOs removed)
- [ ] Find production issues → Fixed
- [ ] Audit against .requirements.md → Violations fixed
- [ ] Validate → Grep returns 0 for all issues
- [ ] Next file

**Quality Gates:**
- grep Decimal("0\. → 0 results
- grep 0.02, 0.05, 0.15, 2.0 → 0 results (in business logic, not config defaults)
- grep raise NotImplementedError → 0 results (except base classes)
- grep "# TODO:" → 0 results (except service registry docs)
- grep "math.sqrt" → 0 results (should use np.std)

**Status**: NOT STARTED - Ready to run with Ralph Task 22

## Next Session

Continue systematic file-by-file review focusing on:
1. Business logic files with actual hardcoded values (not config defaults)
2. Remaining TODO/FIXME comments in production code
3. Verify all syntax compiles correctly

**Completion Promise:** `CODE_QUALITY_REFACTOR_COMPLETE`
