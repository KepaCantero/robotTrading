# compliance_engine.py

## Purpose
UNIFIED compliance engine integrating 17 systems (8 main + 12 compliance rules) for pre-trade analysis, post-trade analysis, and portfolio optimization with kill switch protection.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses domain entities from `app.domain.entities`.

### SystemAvailability Class
```python
class SystemAvailability:
    enable_logging: bool           # REQUIRED - Enable detailed system check logging
    _systems: Dict[str, bool]      # INTERNAL - Availability status of 17 systems
```

### ReconnectionConfig Class
```python
@dataclass
class ReconnectionConfig:
    max_attempts: int = 10                      # REQUIRED - Maximum retry attempts
    base_delay_seconds: float = 1.0             # REQUIRED - Initial backoff delay
    max_delay_seconds: float = 60.0             # REQUIRED - Maximum backoff cap
    exponential_base: float = 2.0               # REQUIRED - Backoff multiplier
    jitter: bool = True                         # OPTIONAL - Add random jitter
    jitter_factor: float = 0.1                  # OPTIONAL - Jitter amount (±10%)
    on_attempt: Optional[Callable[[int], None]] = None      # Callback on each attempt
    on_success: Optional[Callable[[int], None]] = None      # Callback on success
    on_failure: Optional[Callable[[], None]] = None         # Callback on failure
    alert_after_attempts: int = 3               # Alert threshold
    alert_callback: Optional[Callable[[int], None]] = None  # Alert callback
```

### ReconnectionStats Class
```python
@dataclass
class ReconnectionStats:
    total_attempts: int = 0                     # Counter for total connection attempts
    successful_connections: int = 0             # Counter for successful connections
    failed_connections: int = 0                 # Counter for failed connections
    last_connection_time: Optional[datetime] = None  # Timestamp of last success
    last_failure_time: Optional[datetime] = None    # Timestamp of last failure
    current_backoff_seconds: float = 0.0        # Current backoff delay

    @property
    def success_rate(self) -> float:            # Calculated: successful / total_attempts
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

### `ReconnectionManager.calculate_backoff(attempt: int) -> float`
**Pre:** attempt >= 0
**Post:** Returns delay in seconds with exponential backoff and jitter
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Updates stats.current_backoff_seconds

### `ReconnectionManager.connect_with_backoff(connect_func: Callable[[], Any]) -> Optional[Any]`
**Pre:** connect_func is async callable
**Post:** Returns connection object if successful, None if all attempts fail
**Raises:** ❌ No (catches and logs all exceptions)
**Retry:** ✅ Yes - Up to max_attempts with exponential backoff
**Side Effects:** Updates stats, calls callbacks, logs each attempt

---

## Acceptance Criteria
- [ ] Kill switch triggers when daily loss exceeds 5% (Hull Rule 13.1)
- [ ] Kill switch blocks ALL trades when triggered
- [ ] Pre-trade analysis runs ALL 17 systems via SystemBus
- [ ] Position limit check: max 10% of portfolio per position (Chan Rule 1)
- [ ] Drawdown limit check: max 25% drawdown (Chan Rule 1)
- [ ] Leverage check: max 2.0x gross exposure
- [ ] Data quality check: minimum 80% quality score required
- [ ] Harris microstructure analysis provides venue/algorithm recommendations
- [ ] Post-trade analysis calculates implementation shortfall
- [ ] Portfolio optimization integrates Chan + Narang + Hull methods
- [ ] Singleton pattern ensures only one ComplianceEngine instance
- [ ] Lazy initialization of subsystems (not loaded until first use)
- [ ] Reconnection manager uses exponential backoff: 1s, 2s, 4s, 8s, ... max 60s
- [ ] Jitter prevents thundering herd on reconnection
- [ ] All exceptions in system handlers are caught and logged
- [ ] Daily P&L tracking includes win rate, avg win, avg loss statistics
- [ ] SLO metrics track latency violations (100ms threshold)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility | ❌ GAP - ComplianceEngine does too much (17 systems orchestration + kill switch + tracking) |
| SOL-005 | BASE_RULES.md | Dependency Inversion | ⚠️ PARTIAL - Some direct imports, should use Protocol |
| ASYNC-001 | BASE_RULES.md | Use async def | ⚠️ PARTIAL - connect_with_backoff is async, but most methods are sync |
| ASYNC-005 | BASE_RULES.md | Set timeouts for external calls | ❌ GAP - Only connect_with_backoff has timeout (30s) |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ⚠️ NOT ENFORCED - May log trade details |
| SEC-005 | BASE_RULES.md | Audit logging for all trading operations | ✅ OK - _completed_trades tracks all |
| TRD-002 | BASE_RULES.md | Validate orders before execution | ✅ OK - analyze_pre_trade validates |
| TRD-003 | BASE_RULES.md | Position limits enforcement | ✅ OK - 10% limit checked |
| RSK-003 | BASE_RULES.md | Drawdown control implementation | ✅ OK - 25% limit checked |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - All handlers catch exceptions |
| ARCH-001 | BASE_RULES.md | Layered architecture | ⚠️ PARTIAL - Domain entities imported, but some infra leakage |

### Trading-Specific Rules

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| TRD-KILL-001 | Kill switch at 5% daily loss (Hull 13.1) | ✅ OK |
| TRD-POS-001 | Max 10% portfolio per position (Chan Rule 1) | ✅ OK |
| TRD-DD-001 | Max 25% drawdown (Chan Rule 1) | ✅ OK |
| TRD-LEV-001 | Max 2.0x leverage | ✅ OK |
| TRD-DATA-001 | Min 80% data quality score | ✅ OK |
| TRD-AUDIT-001 | Log all trade decisions | ✅ OK |
| TRD-SLO-001 | 100ms latency threshold | ✅ OK |
| TRD-17SYS-001 | ALL 17 systems must execute | ✅ OK - SystemBus orchestrates |
| TRD-LAZY-001 | Lazy subsystem initialization | ✅ OK |

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
  - Test ReconnectionManager exponential backoff calculation
  - Test ReconnectionManager adds jitter to delay
  - Test ReconnectionManager respects max_delay cap
  - Test connect_with_backoff retries on failure
  - Test connect_with_backoff calls callbacks
  - Test connect_with_backoff returns None after max attempts
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
- **Synchronous Bottlenecks:** Most methods are synchronous. Pre-trade analysis blocks on 17 system calls. Consider async/await for production.
- **Error Resilience:** All system handlers catch exceptions. This prevents cascading failures but may hide issues. Monitor warning logs.
- **Lazy Initialization:** Subsystems loaded on first use. This speeds startup but may cause latency spikes on first call.
- **Hardcoded Thresholds:** 5% kill switch, 10% position limit, 25% drawdown, 2.0x leverage, 80% data quality. Make configurable via YAML.
- **Hull Rule 13.1:** Kill switch is critical safety mechanism. Test thoroughly in integration tests.
- **17 Systems Integration:** SystemBus is complex. Add integration tests for all system combinations.
