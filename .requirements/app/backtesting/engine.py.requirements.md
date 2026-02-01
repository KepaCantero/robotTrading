# engine.py

## Purpose
Core backtesting engine with historical data simulation, trade execution, liquidity validation, risk envelope validation, and performance metrics.

---

## Type Definitions / Data Classes

### SimpleBacktester Class
```python
class SimpleBacktester:
    config: BacktestConfig
    capital: Decimal
    positions: Dict[str, Decimal]
    trades: List[Trade]
    equity_curve: List[Tuple[datetime, Decimal]]
    max_drawdown: Decimal
    strategy: Optional[Any]
    enable_risk_envelope: bool
    risk_validator: Optional[RiskEnvelopeValidator]
    trading_validator: TradingValidator
    liquidity_validator: LiquidityValidator
    last_known_prices: Dict[str, Decimal]
```

**Validation Rules:**
- config.initial_capital must be positive
- max_position_size in (0, 1]
- All trades validated for profitability

---

## Function Signatures (Contracts)

### `get_price(md) -> Decimal`
**Pre:** md has 'close' or 'close_price' attribute
**Post:** Returns closing price as Decimal
**Raises:** AttributeError if no price attribute
**Retry:** No
**Side Effects:** None

### `SimpleBacktester.__init__(config, ...)`
**Pre:** config is valid BacktestConfig
**Post:** Initialize backtester with validators
**Raises:** None
**Retry:** No
**Side Effects:** Initializes validators, logs

### `run_backtest(market_data: List, signals: List[Signal], ...) -> BacktestResult`
**Pre:** market_data non-empty
**Post:** Returns BacktestResult with trades, performance, equity
**Raises:** ValueError if no market data
**Retry:** No
**Side Effects:** Processes all data, executes signals, closes positions

### `_process_signal(signal: Signal, market_data: Any)`
**Pre:** signal has metadata
**Post:** Executes or rejects signal after validation
**Raises:** None (errors logged)
**Retry:** No
**Side Effects:** Calls risk_check, validates envelope, executes

### `_execute_buy_signal(signal: Signal, market_data: Any)`
**Pre:** signal is BUY type
**Post:** Executes buy with liquidity validation
**Raises:** None
**Retry:** No
**Side Effects:** Validates liquidity, position size, stop-loss; updates capital

### `_execute_sell_signal(signal: Signal, market_data: Any)`
**Pre:** signal is SELL type
**Post:** Executes sell with P&L calculation
**Raises:** None
**Retry:** No
**Side Effects:** Calculates P&L, updates capital, closes trades

### `_validate_trade_profitability(signal: Signal, price: Decimal) -> bool`
**Pre:** price > 0
**Post:** Returns True if expected profit > 5x commission
**Raises:** None
**Retry:** No
**Side Effects:** Logs rejection if commission ratio > 1%

### `_check_exit_conditions(market_data: Any)`
**Pre:** market_data has price
**Post:** Closes positions if SL/TP triggered
**Raises:** None
**Retry:** No
**Side Effects:** Uses intraday high/low for triggers

### `_close_position(symbol: str, timestamp: datetime, reason: str, current_price: Decimal = None)`
**Pre:** symbol has open position
**Post:** Closes position with P&L
**Raises:** None
**Retry:** No
**Side Effects:** Calculates P&L, closes trades, updates capital

### `_calculate_sharpe_ratio() -> Optional[Decimal]`
**Pre:** At least 2 closed trades
**Post:** Returns annualized Sharpe ratio
**Raises:** None
**Retry:** No
**Side Effects:** Uses time-series returns

---

## Acceptance Criteria
- [ ] All signals validated for liquidity before execution
- [ ] Commission ratio check rejects trades where cost > 1% of position
- [ ] Expected profit must be > 5x round-trip commission
- [ ] SL/TP use intraday high/low prices
- [ ] Equity curve uses tracked prices
- [ ] Sharpe calculated from time-series returns
- [ ] Risk envelope validation enabled by default
- [ ] All trades logged with reason, commission, slippage
- [ ] Partial fills supported for large orders

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| BT-003 | 13-trading-specific-rules.md | No look-ahead bias | ✅ OK |
| BT-004 | 13-trading-specific-rules.md | Realistic costs | ✅ OK |
| TRD-002 | 13-trading-specific-rules.md | Risk validation | ✅ OK |
| TRD-003 | 13-trading-specific-rules.md | Position limits | ✅ OK |
| SEC-007 | 28-security-and-secrets.md | Input validation | ✅ OK |
| LOG-004 | 09-logging-observability.md | Error logging | ✅ OK |
| TYP-001 | 02-type-hints.md | Type coverage | ⚠️ PARTIAL |
| ARCH-004 | 05-architecture.md | Functions < 20 lines | ❌ GAP |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ❌ GAP |
| TST-005 | 06-testing.md | Coverage > 80% | ❌ GAP - No test file found |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** Decimal, uuid, logging, math, datetime
- **Internal:**
  - app.backtesting.liquidity_validator.LiquidityValidator
  - app.backtesting.models
  - app.core.trading_validators.TradingValidator
  - app.models.portfolio
  - app.models.signal
  - app.services.risk_envelope_validator.RiskEnvelopeValidator

---

## Required Tests
- **tests/unit/backtesting/test_engine.py:**
  - Test get_price helper
  - Test backtest initialization
  - Test run_backtest
  - Test signal matching
  - Test buy/sell execution
  - Test trade profitability validation
  - Test SL/TP triggering
  - Test equity curve updates
  - Test Sharpe calculation
  - Test risk envelope validation
  - Test liquidity validation
  - Test partial fills

---

## Notes
- **CRITICAL FIX #1:** Liquidity validation (reject >10% of volume)
- **CRITICAL FIX #2:** Profitability validation (profit > 5x commission)
- **CRITICAL FIX #3:** Position sizing adjusted for commission ratio
- **CRITICAL FIX:** Equity curve uses tracked prices
- **CRITICAL FIX:** Sharpe from time-series returns
- **Signal Matching:** ±1 day tolerance
- **Risk Envelope:** Enabled by default
