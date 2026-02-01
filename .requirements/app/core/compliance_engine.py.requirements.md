# compliance_engine.py

## Purpose
UNIFIED compliance engine integrating 17 systems (8 main + 12 compliance rules) for pre-trade analysis, post-trade analysis, and portfolio optimization with kill switch protection.

## ASYNC-005 Timeout Handling
**Status:** ✅ RESOLVED - Timeouts delegated to subsystems

ComplianceEngine is a **synchronous façade** that orchestrates 17 subsystems but makes no direct external calls (network, file I/O, database). All I/O operations are delegated to subsystems which handle their own timeouts:

- **HarrisIntegrator**: Handles its own timeouts for market data calls
- **AlphaModel**: Computational only (no external I/O)
- **RegimeDetector**: Computational only (no external I/O)
- **Other subsystems**: Each handles its own timeouts as appropriate

When async refactoring is implemented (ASYNC-001), timeout parameters will be added at the façade level.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses domain entities from `app.domain.entities`.

### SystemAvailability Class
```python
class SystemAvailability:
    enable_logging: bool           # REQUIRED - Enable detailed system check logging
    _systems: Dict[str, bool]      # INTERNAL - Availability status of 17 systems
```

### ComplianceConfig Class (Pydantic BaseModel)
```python
class ComplianceConfig:
    max_position_ratio: float = 0.10           # Max position size as ratio of portfolio (Chan Rule 1)
    max_drawdown_ratio: float = 0.25           # Max drawdown ratio (Chan Rule 1)
    max_leverage_ratio: float = 2.0            # Max gross leverage ratio
    kill_switch_threshold: float = -0.05       # Daily loss threshold (Hull Rule 13.1)
    min_data_quality_score: float = 80.0       # Minimum data quality score
    max_data_age_days: float = 1.0             # Maximum age of price data in days
    max_portfolio_volatility: float = 0.30     # Maximum annualized portfolio volatility
    max_daily_var_95: float = 0.05             # Maximum 1-day 95% VaR
    slo_latency_ms: float = 100.0              # Maximum acceptable latency in milliseconds
    data_quality_nan_penalty: float = 15.0     # Quality score deduction for NaN values
    data_quality_stale_penalty: float = 20.0   # Quality score deduction for stale data
```

### ComplianceEngine Class (Singleton)
```python
class ComplianceEngine:
    asset_class: str                            # REQUIRED - "equity", "etf", "forex", "crypto", "futures"
    strict_mode: bool                           # REQUIRED - Enforce all checks strictly
    enable_logging: bool                        # REQUIRED - Enable detailed logging
    availability: SystemAvailability            # COMPOSED - System availability tracker
    _subsystems: Dict[str, Any]                 # INTERNAL - Lazy-loaded subsystems
    _system_bus: SystemBus                      # COMPOSED - Orchestrator for 17 systems
    _active_orders: Dict[str, Dict[str, Any]]   # INTERNAL - Pending order tracking
    _completed_trades: List[Dict[str, Any]]     # INTERNAL - Executed trade tracking
    _daily_pnl_tracking: List[Dict[str, Any]]   # INTERNAL - Kill switch P&L tracking
    _starting_capital: float = 100000.0         # Hull Rule 13.1 - Starting capital reference
```

---

## Function Signatures (Contracts)

### `ComplianceEngine.__new__(cls) -> ComplianceEngine`
**Pre:** None
**Post:** Returns singleton instance (only one instance ever created)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Sets cls._instance if first call

### `ComplianceEngine.analyze_pre_trade(symbol: str, side: str, quantity: Decimal, price: Decimal, price_history: Optional[pd.DataFrame], urgency: float, signal_time: Optional[datetime]) -> PreTradeAnalysis`
**Pre:** symbol is valid trading symbol, side is "BUY" or "SELL", quantity > 0, price > 0
**Post:** Returns PreTradeAnalysis with can_execute flag, confidence score, and reasons from all 17 systems
**Raises:** ❌ No (returns analysis with can_execute=False on errors)
**Retry:** ❌ No
**Side Effects:** Checks kill switch, runs all 17 systems via SystemBus

### `ComplianceEngine.analyze_post_trade(order_id: str, symbol: str, side: str, quantity: Decimal, execution_price: Decimal, signal_price: Optional[Decimal], signal_time: Optional[datetime], submission_time: datetime, execution_time: datetime, nbbo: Optional[Tuple[Decimal, Decimal]]) -> PostTradeAnalysis`
**Pre:** order_id is unique, submission_time < execution_time
**Post:** Returns PostTradeAnalysis with latency, implementation shortfall, market impact
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `ComplianceEngine.optimize_portfolio(symbols: List[str], returns: pd.DataFrame, current_prices: Dict[str, Decimal]) -> PortfolioOptimization`
**Pre:** symbols length equals returns columns, all prices > 0
**Post:** Returns PortfolioOptimization with optimal weights, expected return/risk, Sharpe ratio
**Raises:** ❌ No (returns equal weights on error)
**Retry:** ❌ No
**Side Effects:** None

### `ComplianceEngine.check_kill_switch() -> bool`
**Pre:** None
**Post:** Returns True if daily loss > 5% of starting capital (Hull Rule 13.1)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs critical message if triggered

### `ComplianceEngine.track_daily_pnl(symbol: str, side: str, quantity: Decimal, entry_price: Decimal, exit_price: Optional[Decimal], realized_pnl: Optional[float]) -> None`
**Pre:** quantity > 0, entry_price > 0
**Post:** Appends P&L record to _daily_pnl_tracking
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Updates _daily_pnl_tracking, logs if enable_logging=True

### `ComplianceEngine.reset_daily_tracking(new_starting_capital: Optional[float]) -> None`
**Pre:** new_starting_capital must be > 0 if provided
**Post:** Clears _daily_pnl_tracking, optionally updates _starting_capital
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Clears tracking list, logs previous day summary

### `ComplianceEngine.set_starting_capital(capital: float) -> None`
**Pre:** capital > 0
**Post:** Updates _starting_capital
**Raises:** ValueError if capital <= 0
**Retry:** ❌ No
**Side Effects:** Logs capital change

---

## Acceptance Criteria
- [ ] Kill switch triggers when daily loss exceeds configured threshold (Hull Rule 13.1)
- [ ] Kill switch blocks ALL trades when triggered
- [ ] Pre-trade analysis runs ALL 17 systems via SystemBus
- [ ] Position limit check: max configured ratio of portfolio per position (default 10%, Chan Rule 1)
- [ ] Drawdown limit check: max configured ratio drawdown (default 25%, Chan Rule 1)
- [ ] Leverage check: max configured leverage ratio (default 2.0x)
- [ ] Data quality check: minimum configured quality score (default 80%)
- [ ] Harris microstructure analysis provides venue/algorithm recommendations
- [ ] Post-trade analysis calculates implementation shortfall
- [ ] Portfolio optimization integrates Chan + Narang + Hull methods
- [ ] Singleton pattern ensures only one ComplianceEngine instance
- [ ] Lazy initialization of subsystems (not loaded until first use)
- [ ] All exceptions in system handlers are caught and logged
- [ ] Daily P&L tracking includes win rate, avg win, avg loss statistics
- [ ] SLO metrics track latency violations (configured threshold, default 100ms)
- [ ] Timeout handling is delegated to subsystems (ASYNC-005 resolved)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility | ⚠️ NOT APPLIED - Façade pattern for unified entry point (see GAP analysis) |
| SOL-002 | BASE_RULES.md | Open/Closed Principle | ⚠️ DEFERRED - Requires plugin architecture (see GAP analysis) |
| SOL-005 | BASE_RULES.md | Dependency Inversion | ⚠️ PARTIAL - Some direct imports, should use Protocol |
| ASYNC-001 | BASE_RULES.md | Use async def | ⚠️ DEFERRED - Sync methods acceptable for single-threaded (see GAP analysis) |
| ASYNC-005 | BASE_RULES.md | Set timeouts for external calls | ✅ OK - Timeouts delegated to subsystems (see GAP analysis) |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ⚠️ NOT ENFORCED - May log trade details |
| SEC-005 | BASE_RULES.md | Audit logging for all trading operations | ✅ OK - _completed_trades tracks all |
| TRD-002 | BASE_RULES.md | Validate orders before execution | ✅ OK - analyze_pre_trade validates |
| TRD-003 | BASE_RULES.md | Position limits enforcement | ✅ OK - 10% limit checked |
| RSK-003 | BASE_RULES.md | Drawdown control implementation | ✅ OK - 25% limit checked |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - All handlers catch exceptions |
| ARCH-001 | BASE_RULES.md | Layered architecture | ⚠️ PARTIAL - Domain entities imported, but some infra leakage |
| DP-004 | BASE_RULES.md | Dependency injection | ⚠️ DEFERRED - Direct imports instead of DI (see GAP analysis) |

### Trading-Specific Rules

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| TRD-KILL-001 | Kill switch at configurable daily loss (default -5%, Hull 13.1) | ✅ OK - ComplianceConfig.kill_switch_threshold |
| TRD-POS-001 | Max configurable position ratio (default 10%, Chan Rule 1) | ✅ OK - ComplianceConfig.max_position_ratio |
| TRD-DD-001 | Max configurable drawdown (default 25%, Chan Rule 1) | ✅ OK - ComplianceConfig.max_drawdown_ratio |
| TRD-LEV-001 | Max configurable leverage (default 2.0x) | ✅ OK - ComplianceConfig.max_leverage_ratio |
| TRD-DATA-001 | Min configurable data quality (default 80%) | ✅ OK - ComplianceConfig.min_data_quality_score |
| TRD-AUDIT-001 | Log all trade decisions | ✅ OK |
| TRD-SLO-001 | Configurable latency threshold (default 100ms) | ✅ OK - ComplianceConfig.slo_latency_ms |
| TRD-TIMEOUT-001 | Timeouts delegated to subsystems | ✅ OK - ASYNC-005 resolved |
| TRD-17SYS-001 | ALL 17 systems must execute | ✅ OK - SystemBus orchestrates |
| TRD-LAZY-001 | Lazy subsystem initialization | ✅ OK |

---

## GAP Analysis - Remaining Architectural Issues

### Summary of Remaining GAPs

| GAP ID | Rule | Status | Category | Impact |
|--------|------|--------|----------|--------|
| SOL-001 | Single Responsibility | ⚠️ NOT APPLIED | Intentional Design | LOW |
| SOL-002 | Open/Closed Principle | ⚠️ DEFERRED | Requires Plugin Architecture | MEDIUM |
| ASYNC-001 | Missing Async Variants | ⚠️ DEFERRED | Significant Refactor | MEDIUM |
| ASYNC-005 | Timeouts for External Calls | ✅ RESOLVED | Delegated to Subsystems | NONE |
| DP-004 | Dependency Injection | ⚠️ DEFERRED | Architecture Change | LOW |

### Detailed GAP Analysis

#### GAP-SOL-001: God Object (Single Responsibility Principle)

**Status:** ⚠️ NOT APPLIED - Intentional Design Decision

**Rationale:**
- The file header explicitly states "THE ONLY ENGINE" - this is a unified entry point
- ComplianceEngine is designed as a **Façade pattern** providing a single, simplified interface to a complex subsystem
- The file header (lines 1-30) explicitly documents this as "THE ONLY ENGINE" - intentional architectural decision
- Refactoring to separate classes would be a **major architectural change** affecting all consumers
- The complexity is managed through the **SystemBus pattern** which orchestrates the 17 systems
- This is a documented trade-off: simplicity of API vs. pure SOLID adherence

**Impact:** LOW - The design is intentional and documented

**Recommendation:** Keep as-is. The God Object pattern is acceptable here as it's a **Façade**, not a violation. The SystemBus class handles the orchestration complexity.

**Reference:** Lines 1-30 in compliance_engine.py document this design decision

---

#### GAP-SOL-002: Open/Closed Principle

**Status:** ⚠️ DEFERRED - Requires Plugin Architecture

**Current State:** Adding new system requires modifying `_load_subsystem` with new `elif` branches (lines 1608-1749)

**Rationale:**
- Current implementation uses explicit `if/elif` chains for subsystem loading
- Proper fix would require a **plugin registration system** or **dependency injection container**
- This is a significant refactoring that would affect the lazy initialization pattern
- The 17 systems are relatively stable (not frequently added/removed)

**Impact:** MEDIUM - New systems require code modification, but systems are stable

**Recommendation:** DEFER to future major version. Implement a plugin registry:
```python
# Future design:
subsystem_registry = {
    "risk_engine": lambda: RiskEngine(),
    "portfolio_engine": lambda: PortfolioEngine(),
    # ...
}
```

**Estimated Effort:** 2-3 days (design + implementation + testing)

---

#### GAP-ASYNC-001: Missing Async Variants

**Status:** ⚠️ DEFERRED - Significant Refactor

**Current State:** Main methods (`analyze_pre_trade`, `analyze_post_trade`) are synchronous but perform I/O across 17 subsystems

**Rationale:**
- Adding async variants would require **breaking changes to public API**
- All 17 subsystem interfaces would need async versions
- Significant testing effort for all integration points
- Current synchronous approach is acceptable for **single-threaded usage**
- The SystemBus orchestration would need complete redesign for async/await

**Impact:** MEDIUM - Performance bottleneck only under high concurrency

**Recommendation:** DEFER to v2.0. Add async variants as separate methods:
```python
# Future API:
async def analyze_pre_trade_async(...) -> PreTradeAnalysis:
    # asyncio.gather for parallel system execution
```

**Estimated Effort:** 3-5 days (async variants + comprehensive testing)

---

#### GAP-ASYNC-005: Timeouts for External Calls

**Status:** ✅ RESOLVED - Delegated to Subsystems

**Current State:** ComplianceEngine makes no direct external calls. All I/O operations are delegated to subsystems which handle their own timeouts.

**Rationale:**
- ComplianceEngine is a **synchronous façade** pattern - it orchestrates but doesn't execute I/O
- No direct network calls, file I/O, or database operations in ComplianceEngine
- All external operations are delegated to 17 subsystems:
  - `_handle_harris`: HarrisIntegrator.pre_trade_check() - handles its own timeouts
  - `_handle_narang`: AlphaModel.generate_alpha() - computational, no network I/O
  - `_handle_ernest_chan`: RegimeDetector.detect_regimes() - computational, no network I/O
  - `_handle_hull`: calculate_var() - pure computation
  - Portfolio optimization: optimizer.optimize() - pure computation
- Each subsystem is responsible for its own timeout handling
- When ASYNC-001 is implemented (async variants), timeouts can be added at the façade level using `asyncio.wait_for()`

**Impact:** NONE - Current architecture is correct for synchronous façade pattern

**Documentation Added:**
- Timeout responsibility clarified in subsystem handler documentation
- When async refactoring occurs (ASYNC-001), add `timeout` parameter to main methods:
```python
# Future async design:
async def analyze_pre_trade_async(
    ...,
    timeout: float = 30.0
) -> PreTradeAnalysis:
    return await asyncio.wait_for(
        self._system_bus.execute_pre_trade_analysis_async(...),
        timeout=timeout
    )
```

**Recommendation:** Keep as-is. Each subsystem handles its own timeouts. When implementing async variants (ASYNC-001), add timeout parameters at the façade level.

---

#### GAP-DP-004: Dependency Injection

**Status:** ⚠️ DEFERRED - Architecture Change Required

**Current State:** Direct imports in `_load_subsystem` instead of dependency injection (lines 1616-1738)

**Rationale:**
- Current implementation uses lazy loading with direct imports
- Proper DI would require a **DI container** (e.g., dependency-injector, pins)
- The singleton pattern makes DI more complex
- Would break backward compatibility with existing consumers

**Impact:** LOW - Tight coupling exists, but systems are stable

**Recommendation:** DEFER to v2.0. Implement DI container:
```python
# Future design:
class ComplianceEngine:
    def __init__(self, container: DIContainer):
        self._container = container

    def _get_subsystem(self, name: str):
        return self._container.get(name)
```

**Estimated Effort:** 2-3 days (DI container + refactoring + testing)

---

## Dependencies
- **External:** `pandas` (DataFrame operations), `Decimal` (precise financial calculations)
- **Internal:**
  - `app.domain.entities.portfolio_optimization.PortfolioOptimization`
  - `app.domain.entities.post_trade_analysis.PostTradeAnalysis`
  - `app.domain.entities.pre_trade_analysis.PreTradeAnalysis`
  - `app.core.timezone_utils.utc_now`
- **Standard Library:** `datetime`, `decimal.Decimal`, `logging`, `pathlib.Path`, `typing`, `dataclasses`, `asyncio`, `random`

---

## Required Tests
- **tests/core/test_compliance_engine.py:**
  - Test singleton pattern returns same instance
  - Test kill switch triggers at -5% daily return
  - Test kill switch blocks trade when triggered
  - Test position limit check (10% of portfolio)
  - Test position limit exceeded sets can_execute=False
  - Test drawdown limit check (25% from peak)
  - Test drawdown exceeded sets can_execute=False
  - Test leverage ratio calculation (gross exposure / capital)
  - Test leverage > 2.0x sets can_execute=False
  - Test data quality score calculation
  - Test data quality < 80% sets can_execute=False
  - Test track_daily_pnl records P&L correctly
  - Test reset_daily_tracking clears list
  - Test set_starting_capital updates value
  - Test set_starting_capital raises ValueError for <= 0
  - Test get_daily_pnl_summary returns correct statistics
  - Test analyze_pre_trade calls all 17 systems
  - Test analyze_pre_trade respects kill switch
  - Test analyze_post_trade calculates latency
  - Test analyze_post_trade calculates implementation shortfall
  - Test optimize_portfolio returns equal weights on error
  - Test SystemBus executes systems in correct order
  - Test SystemBus handles critical failures
  - Test SystemAvailability checks all 17 systems
  - Test lazy initialization of subsystems
  - Test ComplianceConfig validation (negative kill switch threshold)
  - Test configurable thresholds are used in checks
  - Edge case: Zero starting capital
  - Edge case: Empty price history
  - Edge case: NaN values in price history
  - Security: No sensitive data in logs (passwords, API keys)

---

## Notes
- **GOD OBJECT WARNING:** ComplianceEngine violates SRP (orchestration + validation + tracking + kill switch). Consider splitting into:
  1. `ComplianceEngine` (orchestration only)
  2. `KillSwitchManager` (P&L tracking and kill switch logic)
  3. `TradeTracker` (SLO tracking and audit trail)
- **Synchronous Bottlenecks:** Most methods are synchronous. Pre-trade analysis blocks on 17 system calls. Consider async/await for production (ASYNC-001).
- **Timeout Handling (ASYNC-005):** ComplianceEngine is a synchronous façade with no direct external calls. All timeout handling is delegated to subsystems. When async variants are implemented, timeout parameters will be added at the façade level.
- **Error Resilience:** All system handlers catch exceptions. This prevents cascading failures but may hide issues. Monitor warning logs.
- **Lazy Initialization:** Subsystems loaded on first use. This speeds startup but may cause latency spikes on first call.
- **Configurable Thresholds:** All trading thresholds are now configurable via ComplianceConfig (GAP-CFG-002 resolved). Defaults: 5% kill switch, 10% position limit, 25% drawdown, 2.0x leverage, 80% data quality.
- **Hull Rule 13.1:** Kill switch is critical safety mechanism. Test thoroughly in integration tests.
- **17 Systems Integration:** SystemBus is complex. Add integration tests for all system combinations.
