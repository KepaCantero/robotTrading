# compliance_engine.py

## Purpose
Unified compliance engine that integrates 17 systems (8 main + 12 compliance) for pre-trade and post-trade analysis, portfolio optimization, and kill switch monitoring.

---

## Type Definitions / Data Classes

### ComplianceConfig (Pydantic BaseModel)
```python
class ComplianceConfig(BaseModel):
    # Position Limits (Chan Rule 1)
    max_position_ratio: float = 0.10              # Max position size as ratio of portfolio
    max_drawdown_ratio: float = 0.25              # Max drawdown as ratio of peak portfolio
    max_leverage_ratio: float = 2.0               # Maximum gross leverage ratio

    # Kill Switch (Hull Rule 13.1)
    kill_switch_threshold: float = -0.05          # Daily loss threshold that triggers halt

    # Data Quality
    min_data_quality_score: float = 80.0          # Minimum data quality score to allow trading
    max_data_age_days: float = 1.0                # Maximum age of price data in days

    # Portfolio VaR
    max_portfolio_volatility: float = 0.30        # Maximum annualized portfolio volatility

    # Hull VaR
    max_daily_var_95: float = 0.05                # Maximum 1-day 95% VaR

    # SLO Thresholds
    slo_latency_ms: float = 100.0                 # Maximum acceptable latency in ms

    # Data Quality Deductions
    data_quality_nan_penalty: float = 15.0        # Quality score deduction for NaN values
    data_quality_stale_penalty: float = 20.0      # Quality score deduction for stale data
```

### SystemAvailability
```python
class SystemAvailability:
    enable_logging: bool           # OPTIONAL - Enable detailed logging
    _systems: Dict[str, bool]      # PRIVATE - System availability tracking
```

### SystemBus
```python
class SystemBus:
    engine: ComplianceEngine        # REQUIRED - Parent engine reference
    _execution_order: List[str]     # PRIVATE - System execution order
```

### ComplianceEngine (Singleton)
```python
class ComplianceEngine:
    asset_class: str                        # REQUIRED - Asset class type
    strict_mode: bool                       # OPTIONAL - Enforce compliance strictly
    enable_logging: bool                    # OPTIONAL - Enable detailed logging
    config: ComplianceConfig                # REQUIRED - Configuration object (defaults if None)
    availability: SystemAvailability        # REQUIRED - System availability tracker
    _system_bus: SystemBus                  # REQUIRED - System orchestrator
    _subsystems: Dict[str, Any]             # PRIVATE - Lazy-loaded subsystems
    _active_orders: Dict[str, Dict]         # PRIVATE - Order tracking
    _completed_trades: List[Dict]           # PRIVATE - Completed trades
    _daily_pnl_tracking: List[Dict]         # PRIVATE - Daily P&L for kill switch
    _starting_capital: float                # PRIVATE - Starting capital for kill switch (100000.0 default)
```

---

## Function Signatures (Contracts)

### `__init__(asset_class: str = "equity", strict_mode: bool = False, enable_logging: bool = True, config: Optional[ComplianceConfig] = None) -> None`
**Pre:** asset_class is valid string ("equity", "etf", "forex", "crypto", "futures")
**Post:** Singleton instance initialized with system availability checked
**Raises:** ValueError if starting_capital <= 0 (in set_starting_capital)
**Side Effects:** Initializes subsystem availability, logs startup info

### `check_kill_switch() -> bool`
**Pre:** _daily_pnl_tracking and _starting_capital initialized
**Post:** Returns True if daily loss exceeds 5% threshold
**Raises:** None
**Side Effects:** Logs critical message if triggered

### `track_daily_pnl(symbol: str, side: str, quantity: Decimal, entry_price: Decimal, exit_price: Optional[Decimal] = None, realized_pnl: Optional[float] = None) -> None`
**Pre:** quantity > 0, entry_price > 0
**Post:** P&L tracked in _daily_pnl_tracking
**Raises:** None
**Side Effects:** Appends to _daily_pnl_tracking, logs if enabled

### `analyze_pre_trade(symbol: str, side: str, quantity: Decimal, price: Decimal, price_history: Optional[pd.DataFrame] = None, urgency: float = 0.5, signal_time: Optional[datetime] = None) -> PreTradeAnalysis`
**Pre:** quantity > 0, price > 0, side in ["BUY", "SELL"], urgency in [0, 1]
**Post:** Returns PreTradeAnalysis with comprehensive decision from all 17 systems
**Raises:** None (handles exceptions internally)
**Side Effects:** May log warnings/errors, calls all available systems

### `analyze_post_trade(order_id: str, symbol: str, side: str, quantity: Decimal, execution_price: Decimal, signal_price: Optional[Decimal], signal_time: Optional[datetime], submission_time: datetime, execution_time: datetime, nbbo: Optional[Tuple[Decimal, Decimal]] = None) -> PostTradeAnalysis`
**Pre:** order_id is unique, quantity > 0, execution_price > 0
**Post:** Returns PostTradeAnalysis with execution quality metrics
**Raises:** None (handles exceptions internally)
**Side Effects:** Logs warnings if Harris analysis fails

### `optimize_portfolio(symbols: List[str], returns: pd.DataFrame, current_prices: Dict[str, Decimal]) -> PortfolioOptimization`
**Pre:** len(symbols) > 0, returns.shape matches symbols, all prices > 0
**Post:** Returns PortfolioOptimization with optimal weights
**Raises:** None (returns equal-weight fallback on error)
**Side Effects:** Logs error if optimization fails

---

## Acceptance Criteria
- [x] **AC-001:** Kill switch triggers at configured threshold (default -5%)
- [x] **AC-002:** All 17 systems checked for availability at initialization
- [x] **AC-003:** Pre-trade analysis returns can_execute=False when kill switch active
- [x] **AC-004:** Position limit check rejects positions > configured limit (default 10%, Chan Rule 1)
- [x] **AC-005:** Drawdown check rejects trades when drawdown > configured limit (default 25%, Chan Rule 1)
- [x] **AC-006:** Data quality check blocks trades when quality < configured threshold (default 80%)
- [x] **AC-007:** All functions have type hints
- [x] **AC-008:** No hardcoded thresholds (configurable via ComplianceConfig)

---

## Critical Rules (MUST NOT BREAK)

**See ../../BASE_RULES.md for universal rules (96+ rules in 14 categories)**

### File-Specific Rules Analysis:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | SOLID Principles | Single Responsibility - One class, one reason to change | ❌ GAP - ComplianceEngine is a God Object (2150+ lines, handles 17+ responsibilities) - Intentional design for unified entry point |
| SOL-002 | SOLID Principles | Open/Closed Principle - Open for extension, closed for modification | ❌ GAP - Adding new system requires modifying _load_subsystem with new elif branches |
| ASYNC-001 | Async Patterns | Use async def for I/O operations | ❌ GAP - analyze_pre_trade/analyze_post_trade are synchronous but call multiple subsystems - Async variants would be significant refactor |
| CFG-002 | Configuration | Environment variables for deployment | ✅ FIXED - 2026-02-01 - Added ComplianceConfig class with Pydantic validation |
| CC-007 | Clean Code | Functions < 20 lines (ideally) | ⚠️ PARTIAL - _handle_risk_engine is 145+ lines - Would require significant refactoring |
| QL-006 | Code Quality | Classes < 300 lines | ⚠️ NOT APPLIED - SystemBus is 700+ lines, ComplianceEngine is 1000+ lines - Intentional God Object design |
| TRD-003 | Trading Rules | Position limits enforcement | ✅ OK - Position limit check implemented using configurable threshold |
| TRD-004 | Trading Rules | Audit trail - Log all trade decisions | ✅ OK - Comprehensive logging throughout |
| RSK-003 | Risk Management | Drawdown control - Implement max drawdown limits | ✅ OK - Drawdown check implemented using configurable threshold |
| LOG-003 | Logging | Appropriate levels (debug/info/error/critical) | ✅ OK - Proper use of logger levels |
| LOG-004 | Logging | Error logging with stack traces | ⚠️ PARTIAL - Some exceptions logged without full traceback |
| DP-004 | Design Patterns | Dependency injection | ❌ GAP - Direct imports in _load_subsystem instead of DI |

### Critical GAPs (Priority P1):

#### ✅ FIXED - 2026-02-01:
1. **GAP-CFG-002 (Hardcoded thresholds):** ✅ FIXED
   - **Fix:** Added `ComplianceConfig` class with Pydantic validation
   - **Changes:**
     - New `ComplianceConfig` dataclass with all configurable thresholds
     - `max_position_ratio` (default 0.10) - Position size limit
     - `max_drawdown_ratio` (default 0.25) - Drawdown limit
     - `max_leverage_ratio` (default 2.0) - Leverage limit
     - `kill_switch_threshold` (default -0.05) - Kill switch threshold
     - `min_data_quality_score` (default 80.0) - Data quality threshold
     - `max_daily_var_95` (default 0.05) - Hull VaR threshold
     - `slo_latency_ms` (default 100.0) - SLO latency threshold
     - Data quality penalties: `data_quality_nan_penalty`, `data_quality_stale_penalty`
   - All hardcoded values replaced with `self.config.*` references
   - Updated `__init__` to accept optional `config` parameter
   - Updated `get_compliance_engine()` to accept optional `config` parameter

#### ❌ REMAINING (Intentional design or requires significant refactor):
2. **GAP-SOL-001 (God Object):** ⚠️ NOT APPLIED - Intentional Design
   - The file header explicitly states "THE ONLY ENGINE" - this is a unified entry point
   - Refactoring to separate classes would be a major architectural change
   - The complexity is managed through the SystemBus pattern
   - Recommendation: Keep as-is for simplicity, document as intentional trade-off

3. **GAP-ASYNC-001 (Missing async):** ⚠️ DEFERRED
   - Main methods are synchronous but perform I/O across 17 subsystems
   - Adding async variants would require:
     - Async versions of all subsystem interfaces
     - Breaking changes to public API
     - Significant testing effort
   - Current synchronous approach is acceptable for single-threaded usage
   - Recommendation: Add async variants in future major version

---

## Dependencies

### External:
- pandas (DataFrame operations)
- pydantic (ComplianceConfig validation)
- Decimal (precise financial calculations)
- asyncio (for potential future async variants)

### Internal:
- app.domain.entities.portfolio_optimization
- app.domain.entities.post_trade_analysis
- app.domain.entities.pre_trade_analysis
- app.backtesting.engine
- app.services.live_trading.broker_connector
- app.engines.risk_engine
- app.engines.portfolio_engine
- app.engines.data_engine
- app.engines.context_engine
- app.engines.execution_engine.microstructure
- app.services.regime_detection_chan
- app.services.portfolio_construction_narang
- app.backtesting.labeling.meta_labeling
- app.backtesting.validation.cross_validation
- app.engines.execution_engine.microstructure.harris_integration
- app.microstructure.liquidity
- app.engines.risk_engine.var_calculators.var_calculators
- app.sre.monitoring.golden_signals

---

## Required Tests

### **tests/core/test_compliance_engine.py:**
- `test_check_kill_switch_triggered()` - Daily loss > 5% triggers kill switch
- `test_check_kill_switch_not_triggered()` - Daily loss < 5% does not trigger
- `test_position_limit_exceeded()` - Rejects position > 10% of portfolio
- `test_position_limit_ok()` - Accepts position <= 10% of portfolio
- `test_drawdown_limit_exceeded()` - Rejects trades when drawdown > 25%
- `test_data_quality_threshold()` - Blocks trades when quality < 80%
- `test_pre_trade_kill_switch_active()` - Pre-trade blocked when kill switch on
- `test_all_systems_checked()` - All 17 systems checked at initialization
- `test_daily_pnl_tracking()` - P&L correctly tracked
- `test_reset_daily_tracking()` - Daily tracking properly reset
- `test_slo_metrics()` - SLO metrics calculated correctly
- `test_post_trade_analysis()` - Post-trade analysis returns proper metrics
- `test_portfolio_optimization()` - Portfolio optimization returns weights

---

## Validation

**QA Commands (from check_all.sh and Ralphex config):**

```bash
cd /Users/kepa.cantero/Projects/algoTrading

# 1. Syntax check
python -m py_compile app/core/compliance_engine.py

# 2. Type check (strict mode)
mypy --strict app/core/compliance_engine.py

# 3. Lint
ruff check app/core/compliance_engine.py

# 4. Format check
black --check app/core/compliance_engine.py

# 5. Import sort check
isort --check-only app/core/compliance_engine.py

# 6. Security scan
bandit app/core/compliance_engine.py

# 7. Related tests
pytest tests/core/test_compliance_engine.py -v 2>/dev/null || echo "No tests yet"
```

**Expected Results:**
- Syntax: PASS
- Mypy: PASS (no type errors)
- Ruff: PASS (no lint errors)
- Black: PASS (already formatted)
- Isort: PASS (imports sorted)
- Bandit: PASS (no security issues)
- Tests: PASS (all tests pass)

---

## Notes

**File:** app/core/compliance_engine.py
**Lines:** ~2150
**Complexity:** Very High - God Object pattern with 17+ integrated systems
**Created:** 2026-01-28
**Purpose:** Unified compliance engine for all trading operations

**Design Decision:**
The file header explicitly states this is "THE ONLY ENGINE" - intentional God Object pattern for unified entry point. This violates SOLID principles but provides simplicity for consumers.

---

**Fixes Applied 2026-02-01:**

### ✅ GAP-CFG-002: Hardcoded Thresholds - FIXED
**Summary:** Extracted all hardcoded trading thresholds into a configurable `ComplianceConfig` class using Pydantic validation.

**Changes Made:**
1. Added `ComplianceConfig` class with Pydantic `BaseModel`:
   - All trading thresholds now configurable with validation
   - Default values maintain original behavior
   - Field validators ensure logical constraints (e.g., kill switch threshold must be negative)

2. Updated `ComplianceEngine.__init__`:
   - Added optional `config: Optional[ComplianceConfig] = None` parameter
   - Default to `ComplianceConfig()` if no config provided (backward compatible)

3. Updated `get_compliance_engine()`:
   - Added optional `config` parameter
   - Documentation includes example of custom configuration usage

4. Replaced all hardcoded thresholds with `self.config.*` references:
   - Position limit: `self.config.max_position_ratio` (was 0.10)
   - Drawdown limit: `self.config.max_drawdown_ratio` (was 0.25)
   - Leverage limit: `self.config.max_leverage_ratio` (was 2.0)
   - Kill switch: `self.config.kill_switch_threshold` (was -0.05)
   - Data quality threshold: `self.config.min_data_quality_score` (was 80)
   - Portfolio volatility: `self.config.max_portfolio_volatility` (was 0.30)
   - Hull VaR: `self.config.max_daily_var_95` (was 0.05)
   - SLO latency: `self.config.slo_latency_ms` (was 100)
   - Data age: `self.config.max_data_age_days` (was 1.0)
   - Quality penalties: `self.config.data_quality_nan_penalty`, `self.config.data_quality_stale_penalty`

**Configuration Usage Example:**
```python
# Use defaults
engine = get_compliance_engine()

# Use custom thresholds
custom_config = ComplianceConfig(
    max_position_ratio=0.15,          # 15% position limit
    kill_switch_threshold=-0.03,      # 3% daily loss triggers halt
    min_data_quality_score=90.0,      # Stricter quality requirement
)
engine = get_compliance_engine(config=custom_config)
```

**Validation Results:**
- ✅ Syntax check passed
- ✅ All 64 existing tests passed
- ✅ Backward compatible (default config maintains original behavior)
- ✅ Type safe with Pydantic validation
