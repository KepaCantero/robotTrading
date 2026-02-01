# robust_backtester.py

## Purpose
Main backtesting engine for 25+ year historical simulations with memory-efficient chunking, checkpointing, survivorship bias correction, corporate actions handling, and dividend reinvestment.

---

## Type Definitions / Data Classes

### RobustBacktestConfig
```python
@dataclass
class RobustBacktestConfig:
    initial_capital: Decimal                 # REQUIRED - Starting capital for backtest (must be > 0)
    start_date: date                         # REQUIRED - Backtest start date (must be before end_date)
    end_date: date                           # REQUIRED - Backtest end date (must be after start_date)
    commission_per_trade: Decimal            # REQUIRED - Commission per trade (fixed or percentage)
    slippage_bps: Decimal                    # REQUIRED - Slippage in basis points
    risk_free_rate: Decimal                  # REQUIRED - Risk-free rate for Sharpe ratio calculation
    enable_survivorship_correction: bool     # REQUIRED - Enable survivorship bias correction
    enable_dividend_reinvestment: bool       # REQUIRED - Enable dividend reinvestment (DRIP)
    enable_checkpointing: bool               # REQUIRED - Enable checkpoint/resume functionality
    checkpoint_dir: Optional[Path]           # OPTIONAL - Directory to save checkpoints (defaults to ./checkpoints)
    checkpoint_frequency: int                # REQUIRED - Checkpoint frequency in days (default: 365)
    chunk_size_days: int                     # REQUIRED - Process data in chunks (default: 365 days)
    progress_callback: Optional[Callable]    # OPTIONAL - Callback for progress updates
    pit_data_path: Optional[Path]            # OPTIONAL - Path to point-in-time database
    pit_cache_size_mb: int                   # REQUIRED - PIT cache size in MB (default: 100)
    enable_look_ahead_validation: bool       # REQUIRED - Enable automatic look-ahead bias validation
    validation_strict_mode: bool             # REQUIRED - Whether validation failures block execution
    drip_config: DripConfig                  # REQUIRED - DRIP configuration
```

**Validation Rules:**
- `end_date` must be after `start_date` (validated in `__post_init__`)
- `initial_capital` must be positive (validated in `__post_init__`)
- `checkpoint_dir` defaults to `./checkpoints` if None
- All Decimal fields preserve monetary precision

### RobustBacktestResult
```python
@dataclass
class RobustBacktestResult:
    config: RobustBacktestConfig                     # REQUIRED - Configuration used for backtest
    performance: PerformanceMetrics                  # REQUIRED - Comprehensive performance metrics
    equity_curve: List[Tuple[date, Decimal]]        # REQUIRED - Full equity curve (date -> capital)
    trades: List[Dict[str, Any]]                    # REQUIRED - List of all trades executed
    yearly_breakdown: List[Any]                      # REQUIRED - Year-by-year performance breakdown
    rolling_metrics: Any                             # OPTIONAL - Rolling metrics over different windows
    survivorship_adjustment: Optional[SurvivorshipFreeResult]  # OPTIONAL - Survivorship bias info
    dividend_tracker: Any                           # OPTIONAL - Dividend tracking information
    checkpoints_used: int                           # REQUIRED - Number of checkpoints loaded/resumed from
    total_duration_seconds: float                   # REQUIRED - Total backtest execution time
```

---

## Function Signatures (Contracts)

### `__init__(config: RobustBacktestConfig) -> None`
**Pre:** config must be valid (end_date > start_date, initial_capital > 0)
**Post:** Backtester initialized with all components and checkpoint directory created
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** Creates checkpoint directory if enabled

### `async def run_backtest(strategy: Any, market_data: Union[pd.DataFrame, List[Any]], signals: Optional[List[Any]] = None, resume_from_checkpoint: bool = False) -> RobustBacktestResult`
**Pre:** market_data must contain OHLCV data with datetime index; strategy must have generate_signals() if signals is None
**Post:** Returns RobustBacktestResult with complete backtest results
**Raises:** ValueError if look-ahead validation fails and validation_strict_mode=True
**Retry:** No
**Side Effects:** Saves checkpoints if enabled; updates performance tracker; modifies internal state (_capital, _positions, _trades)

### `async def _process_backtest_chunks(strategy: Any, market_data: pd.DataFrame, signals: Optional[List[Any]]) -> None`
**Pre:** market_data must have datetime or date index
**Post:** Processes all chunks and updates internal state
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Updates _capital, _positions, _trades; saves checkpoints periodically; calls progress_callback

### `async def _process_chunk(strategy: Any, chunk: pd.DataFrame, signals: Optional[List[Any]]) -> None`
**Pre:** chunk must be a valid DataFrame with market data
**Post:** Processes all rows in chunk
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Updates _capital, _positions, _cost_basis, _trades; processes corporate actions

### `async def _process_signal(signal: Any, market_data: pd.Series) -> None`
**Pre:** signal must have symbol, signal_type, and optionally price
**Post:** Executes buy or sell order
**Raises:** No explicit exceptions raised (logs warning and returns on error)
**Retry:** No
**Side Effects:** Updates _capital, _positions, _cost_basis, _trades

### `def _execute_buy(symbol: str, price: Decimal, signal: Any) -> None`
**Pre:** price must be positive; _capital must be sufficient for trade
**Post:** Buys shares (10% of capital by default) and updates position
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Decrements _capital; increments _positions[symbol]; updates _cost_basis[symbol]; appends to _trades

### `def _execute_sell(symbol: str, price: Decimal, signal: Any) -> None`
**Pre:** symbol must be in _positions with positive quantity
**Post:** Sells all shares of symbol and calculates P&L
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Increments _capital; sets _positions[symbol] to 0; clears _cost_basis[symbol]; appends to _trades with P&L

### `def _save_checkpoint(is_final: bool = False) -> None`
**Pre:** enable_checkpointing must be True; checkpoint_dir must exist
**Post:** Checkpoint saved to file
**Raises:** OSError if file write fails
**Retry:** No
**Side Effects:** Creates checkpoint file on disk

### `def _load_latest_checkpoint() -> bool`
**Pre:** checkpoint_dir must exist
**Post:** Restores state from latest checkpoint if found
**Raises:** No explicit exceptions raised (logs error and returns False)
**Retry:** No
**Side Effects:** Updates _current_date, _capital, _positions, _cost_basis

### `def load_corporate_actions_from_csv(filepath: str) -> int`
**Pre:** filepath must exist and be readable CSV
**Post:** Corporate actions loaded from CSV
**Raises:** No explicit exceptions raised (logs error and returns 0)
**Retry:** No
**Side Effects:** Populates corporate_action_handler with actions

### `def load_delisted_database(filepath: str) -> int`
**Pre:** filepath must exist and be readable CSV
**Post:** Delisted stocks loaded from database
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Populates survivorship_adjuster with delisted stocks

### `def _validate_backtest_data(signals: Union[List[Any], pd.DataFrame], market_data: pd.DataFrame) -> ValidationResult`
**Pre:** signals must be convertible to DataFrame; market_data must have datetime index
**Post:** Returns ValidationResult with look-ahead bias analysis
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Logs validation report

---

## Acceptance Criteria
- [ ] RobustBacktestConfig validates that end_date > start_date
- [ ] RobustBacktestConfig validates that initial_capital > 0
- [ ] run_backtest() raises ValueError when look-ahead validation fails in strict mode
- [ ] run_backtest() creates checkpoint directory if enabled
- [ ] _execute_buy() uses Decimal arithmetic for all monetary calculations
- [ ] _execute_sell() calculates P&L using stored cost basis
- [ ] _save_checkpoint() serializes checkpoint state to pickle file
- [ ] _load_latest_checkpoint() restores state from most recent checkpoint
- [ ] _process_backtest_chunks() calls progress_callback for each chunk
- [ ] All trade records include timestamp, symbol, side, shares, price, commission
- [ ] Checkpoint files are named with date (checkpoint_YYYYMMDD.pkl)
- [ ] Cost basis is tracked per-symbol using weighted average

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage for all functions | ✅ OK - All public methods have type hints |
| TYP-002 | BASE_RULES.md | Modern syntax (X \| None) | ✅ OK - Uses Optional[T] correctly |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ OK - Uses logging module with context |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ✅ OK - Exception handlers log errors |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses field(default_factory=list/dict) |
| FMT-008 | BASE_RULES.md | Context managers for resources | ✅ OK - Uses 'with' for file operations |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - LookAheadValidator prevents future data usage |
| BT-004 | BASE_RULES.md | Realistic costs (commission, slippage) | ✅ OK - Configurable commission_per_trade and slippage_bps |
| BT-005 | BASE_RULES.md | Multiple period testing | ✅ OK - Supports 25+ year backtests with chunking |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ NOT APPLIED - Some methods catch Exception broadly |
| TRD-004 | BASE_RULES.md | Audit trail for trades | ✅ OK - All trades recorded in _trades list |
| ARCH-004 | BASE_RULES.md | Small functions (< 20 lines) | ❌ GAP - Some methods exceed 20 lines (e.g., run_backtest ~90 lines) |
| QL-001 | BASE_RULES.md | Complexity < 10 per function | ⚠️ NOT APPLIED - Not measured with radon |
| QL-007 | BASE_RULES.md | Max 7 parameters per function | ❌ GAP - run_backtest has 4 parameters (OK), but _process_chunk has 4 (OK) |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets in code |
| DP-004 | BASE_RULES.md | Dependency injection | ✅ OK - Components injected via constructor |

**GAP Analysis:**
1. **ARCH-004 (Small functions):** Some methods like `run_backtest` (~90 lines) and `_process_backtest_chunks` (~60 lines) are longer than ideal. However, these are orchestrator methods with complex logic that would be difficult to split without harming readability. This is a moderate priority gap.

2. **CC-006 (Explicit error handling):** Several methods catch broad `Exception` without re-raising. While this provides robustness, it may hide unexpected errors. Consider logging more specific exception types.

---

## Dependencies
- **External:** pandas, numpy, pickle (standard lib), dataclasses (standard lib), decimal (standard lib), pathlib (standard lib), typing (standard lib), logging (standard lib)
- **Internal:**
  - `.corporate_actions.CorporateActionHandler`
  - `.corporate_actions.PositionAdjustment`
  - `.dividend_handler.DividendHandler`
  - `.dividend_handler.DripConfig`
  - `.look_ahead_validator.LookAheadValidator`
  - `.look_ahead_validator.ValidationResult`
  - `.models` (BacktestCheckpoint, CorporateAction, DelistedReturnData, ProgressUpdate, StockSplit)
  - `.performance_tracker.PerformanceMetrics`
  - `.performance_tracker.PerformanceTracker`
  - `.pit_database.PITDatabaseClient`
  - `.survivorship_adjuster.SurvivorshipAdjuster`
  - `.survivorship_adjuster.SurvivorshipFreeResult`
  - `..point_in_time_database.PointInTimeDatabase`

---

## Required Tests
- **tests/unit/backtesting/robust_engine/test_robust_backtester.py:**
  - Test RobustBacktestConfig validation (end_date > start_date, initial_capital > 0)
  - Test run_backtest with valid market data and signals
  - Test run_backtest raises ValueError on look-ahead validation failure (strict mode)
  - Test run_backtest resumes from checkpoint when resume_from_checkpoint=True
  - Test _execute_buy with sufficient capital
  - Test _execute_buy with insufficient capital (shares = 0)
  - Test _execute_sell with existing position
  - Test _execute_sell with no position (does nothing)
  - Test cost basis tracking for multiple buys of same symbol
  - Test P&L calculation in _execute_sell
  - Test _save_checkpoint creates file with correct name
  - Test _load_latest_checkpoint restores state correctly
  - Test _process_backtest_chunks calls progress_callback
  - Test _process_backtest_chunks saves checkpoints periodically
  - Test checkpoint directory creation on initialization
  - Test Decimal precision maintained in all monetary calculations
  - Test trade records contain all required fields
  - Test load_corporate_actions_from_csv with valid CSV
  - Test load_corporate_actions_from_csv with invalid CSV (returns 0)
  - Test load_delisted_database with valid CSV
  - Test integration with CorporateActionHandler
  - Test integration with DividendHandler
  - Test integration with SurvivorshipAdjuster
  - Test integration with LookAheadValidator

---

## Notes
- This is the orchestrator for the entire robust backtesting system (FASE 5.1 from AUDIT_PLAN_COMPLETO)
- Uses Decimal type for all monetary calculations to preserve precision
- Checkpointing is critical for 25+ year backtests to avoid losing progress
- The async pattern is used for future extensibility (e.g., async I/O for data loading)
