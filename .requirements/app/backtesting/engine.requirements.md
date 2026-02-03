# engine.py

## Purpose
Core backtesting engine that simulates trading execution with configurable slippage, commission, risk management, and liquidity validation for strategy performance evaluation.

---

## Type Definitions / Data Classes

### BacktestConfig (Pydantic model from models.py)
```python
class BacktestConfig(BaseModel):
    initial_capital: Decimal           # REQUIRED - Starting capital for backtest
    commission_per_trade: Decimal      # REQUIRED - Fixed commission per trade
    slippage_percentage: Decimal       # REQUIRED - Slippage as percentage (e.g., 0.1 for 0.1%)
    max_position_size: Decimal         # REQUIRED - Maximum position size as % of capital
    stop_loss_percentage: Optional[Decimal] = None   # OPTIONAL - Stop loss % from entry
    take_profit_percentage: Optional[Decimal] = None # OPTIONAL - Take profit % from entry
    risk_free_rate: Decimal = Decimal("0.02")        # Default 2% annual
    strategy_name: Optional[str] = None
```

### Trade (from models.py)
```python
class Trade(BaseModel):
    trade_id: str                      # REQUIRED - UUID
    symbol: str                        # REQUIRED - Trading symbol
    side: Literal["buy", "sell"]       # REQUIRED - Trade direction
    quantity: Decimal                  # REQUIRED - Number of shares/contracts
    entry_price: Decimal               # REQUIRED - Entry execution price
    entry_time: datetime               # REQUIRED - Entry timestamp
    exit_price: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    status: TradeStatus                # OPEN or CLOSED
    pnl: Optional[Decimal] = None
    commission: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    reason: str = ""
```

### BacktestResult (from models.py)
```python
class BacktestResult(BaseModel):
    config: BacktestConfig
    trades: List[Trade]
    performance: Optional[PerformanceMetrics]
    equity_curve: List[Tuple[datetime, Decimal]]
    start_date: datetime
    end_date: datetime
    final_capital: Decimal
    total_return: Decimal
    annualized_return: Decimal
```

### PerformanceMetrics (from models.py)
```python
class PerformanceMetrics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal                   # 0-100 percentage
    total_pnl: Decimal
    total_pnl_percentage: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    net_profit: Decimal
    max_drawdown: Decimal               # Negative value or zero
    max_drawdown_percentage: Decimal    # Negative percentage
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    avg_win: Decimal
    avg_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    total_days: int
    avg_trade_duration: Decimal
```

**Validation Rules:**
- `max_drawdown` must be <= 0 (negative values represent losses)
- `win_rate` must be between 0-100
- All monetary fields use Decimal for precision
- Trade quantities must be > 0

---

## Function Signatures (Contracts)

### `__init__(config: BacktestConfig, diagnostic_logger=None, strategy=None, enable_risk_envelope: bool = True, ...)`
**Pre:** config is valid BacktestConfig with positive initial_capital
**Post:** SimpleBacktester initialized with capital, empty positions/trades, validators configured
**Raises:** ValueError if config invalid
**Retry:** No
**Side Effects:** Initializes LiquidityValidator, TradingValidator, RiskEnvelopeValidator

### `run_backtest(market_data: List, signals: List[Signal], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> BacktestResult`
**Pre:** market_data non-empty, signals sorted by timestamp
**Post:** Returns BacktestResult with trades, performance metrics, equity curve
**Raises:** ValueError if market_data empty after date filtering
**Retry:** No
**Side Effects:** Processes all signals, executes trades, updates equity curve

### `_process_signal(signal: Signal, market_data: Any) -> None`
**Pre:** signal valid, market_data has price data
**Post:** Signal processed (executed or rejected), trade added if executed
**Raises:** Logs errors but continues processing
**Retry:** No
**Side Effects:** May add trade to self.trades, update positions/capital

### `_execute_buy_signal(signal: Signal, market_data: Any) -> None`
**Pre:** Signal type is BUY, sufficient capital available
**Post:** Buy trade executed if all validations pass
**Raises:** ValueError on position size validation failure
**Retry:** No
**Side Effects:** Adds Trade to list, updates positions and capital

### `_execute_sell_signal(signal: Signal, market_data: Any) -> None`
**Pre:** Signal type is SELL, position exists for symbol
**Post:** Sell trade executed, position closed or reduced
**Raises:** Warning logged if no position exists
**Retry:** No
**Side Effects:** Adds Trade to list, updates positions and capital

### `_validate_trade_profitability(signal: Signal, price: Decimal) -> bool`
**Pre:** signal has take_profit_percentage configured
**Post:** Returns True if expected profit > 5x round-trip commission
**Raises:** None
**Retry:** No
**Side Effects:** May log rejection to diagnostic_logger

### `_calculate_position_size(signal: Signal, price: Decimal) -> Decimal`
**Pre:** signal valid, price > 0
**Post:** Returns position size >= 1 share
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_check_exit_conditions(market_data: Any) -> None`
**Pre:** market_data has OHLC data
**Post:** Stop loss or take profit triggered if price hit
**Raises:** None
**Retry:** No
**Side Effects:** May close positions via _close_position

### `_close_position(symbol: str, timestamp: datetime, reason: str, current_price: Optional[Decimal] = None) -> None`
**Pre:** Position exists for symbol
**Post:** Position fully closed, trade added with P&L
**Raises:** None
**Retry:** No
**Side Effects:** Adds sell Trade, updates positions and capital

### `_calculate_sharpe_ratio() -> Optional[Decimal]`
**Pre:** At least 2 closed trades with exit times
**Post:** Returns annualized Sharpe ratio or None
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Backtest processes all signals within date range correctly
- [ ] Buy signals validate liquidity before execution (HIGH PRIORITY #1)
- [ ] Sell signals validate liquidity before execution (HIGH PRIORITY #1)
- [ ] Stop loss triggers on intraday low (not just close)
- [ ] Take profit triggers on intraday high (not just close)
- [ ] Commission impact validated before trade execution
- [ ] Equity curve accurately tracks portfolio value including unrealized P&L
- [ ] Sharpe ratio calculated correctly from time-series returns
- [ ] Partial fills handled correctly (order reduced to 5% ADV)
- [ ] Market impact calculated and applied to execution price
- [ ] Position closing uses last known price for accurate P&L
- [ ] Risk envelope validation prevents over-exposure
- [ ] Risk check from strategy applied before signal execution
- [ ] Diagnostic logger records all rejections with reasons
- [ ] Learning engine integration registers trades correctly

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-001 | 01-formatting-style.md | Line length ≤ 100 characters | ✅ OK |
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| ARCH-001 | 05-architecture.md | Domain layer independent of frameworks | ✅ OK |
| ARCH-005 | 05-architecture.md | Early returns to avoid nesting | ⚠️ NOT APPLIED - Some deeply nested conditionals |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ⚠️ NOT APPLIED - run_backtest does too much (consider extracting) |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| LOG-005 | 09-logging-observability.md | Never log sensitive data (passwords/tokens) | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs comprehensive tests |
| SEC-005 | 28-security-and-secrets.md | Audit logging for all trading operations | ✅ OK |

**HIGH PRIORITY #1 - Liquidity Validation (Audit Finding):**
- ✅ LiquidityValidator initialized in __init__
- ✅ validate_order() called before _execute_buy_signal
- ✅ simulate_fill() used for realistic execution
- ✅ Partial fills handled (5% ADV limit)
- ✅ Market impact calculated and applied
- ✅ Orders >10% ADV rejected

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** logging, datetime, decimal, uuid, math, numpy, pandas, pydantic
- **Internal:**
  - app.backtesting.liquidity_validator.LiquidityValidator
  - app.backtesting.models (BacktestConfig, BacktestResult, PerformanceMetrics, Trade, TradeStatus)
  - app.core.trading_validators.TradingValidator
  - app.models.portfolio (Portfolio, Position, AssetClass)
  - app.models.signal (Signal, SignalType)
  - app.services.dynamic_capital_reallocation.DynamicCapitalReallocationEngine
  - app.services.risk_envelope_validator.RiskEnvelopeValidator

---

## Required Tests
- **test_backtest_engine.py:**
  - Success: Simple buy/sell with profit
  - Success: Stop loss trigger on intraday low
  - Success: Take profit trigger on intraday high
  - Success: Partial fill handling (order >5% ADV)
  - Success: Market impact calculation
  - Success: Commission impact validation (reject when commission >1% of position)
  - Error: Insufficient capital for position
  - Error: Liquidity rejection (>10% ADV)
  - Edge: Zero volume data (should reject)
  - Edge: Multiple signals same timestamp
  - Edge: Signal with no matching market data
  - Integration: Risk envelope validation
  - Integration: Strategy risk_check
  - Integration: Learning engine trade registration

---

## Notes
- CRITICAL: Equity curve uses last_known_prices dict for accurate unrealized P&L tracking
- HIGH PRIORITY #1: Liquidity validation addresses audit finding about unrealistic order execution
- PESSIMISTIC EXECUTION: When both SL and TP hit, stop-loss takes priority
- Commission can be percentage (from signal metadata) or fixed (from config)
- Sharpe ratio calculation fixed to use proper time-series returns (not cumulative capital ratios)
