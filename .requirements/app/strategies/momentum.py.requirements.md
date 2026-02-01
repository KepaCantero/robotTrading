# momentum.py

## Purpose
Momentum trading strategy using RSI, EMA, volume, ROC, and ATR indicators to identify trend continuation opportunities with proper risk management.

---

## Type Definitions / Data Classes

### No Pydantic models or dataclasses defined in this file.

---

## Function Signatures (Contracts)

### `__init__(config: Dict[str, Any]) -> None`
**Pre:** config contains strategy parameters or strategy_config is available via get_strategy_config
**Post:** Strategy initialized with RSI, EMA, ATR thresholds, technical indicator history deques (maxlen=200), and TechnicalIndicatorCalculator
**Raises:** FileNotFoundError, ValueError, KeyError, TypeError when loading YAML config (caught and handled)
**Retry:** No
**Side Effects:** Initializes multiple deque collections for price history, loads config from centralized_config

### `generate_signals(market_data: Quote) -> List[Signal]`
**Pre:** market_data contains valid price/volume data
**Post:** Returns list of processed signals (after scoring engine), may be empty if cooldown active or filters fail
**Raises:** ValueError, KeyError, AttributeError, IndexError, TypeError (logged, returns empty list)
**Retry:** No
**Side Effects:** Updates price/volume history deques, processes signals through SignalScoringEngine

### `risk_check(signal: Signal, portfolio: Portfolio) -> bool`
**Pre:** signal has valid price, portfolio has valid positions and cash
**Post:** Returns True if signal passes exposure/cash/position validation, False otherwise
**Raises:** ValueError, TypeError, KeyError, AttributeError, IndexError (logged, returns False)
**Retry:** No
**Side Effects:** Logs rejection reasons with detailed diagnostics

### `_calculate_volume_ratio(market_data: Quote) -> Decimal`
**Pre:** market_data has valid volume
**Post:** Returns volume ratio vs 20-period average, or 1 if insufficient history
**Raises:** None (handles division by zero)
**Retry:** No
**Side Effects:** None

### `_passes_atr_filter(current_price: Optional[Decimal]) -> bool`
**Pre:** ATR history has at least one value if filter enabled
**Post:** Returns True if ATR > threshold (relative or absolute), or True if filter disabled
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_is_buy_signal(rsi, ema, volume_ratio, roc, obv_trend, market_data) -> bool`
**Pre:** All indicators calculated and valid
**Post:** Returns True if RSI in momentum zone (40-70) with bullish confirmations, or if RSI recovering from oversold with strong volume
**Raises:** None
**Retry:** No
**Side Effects:** Logs rejections with diagnostic info

### `_is_sell_signal(rsi, ema, volume_ratio, roc, obv_trend, market_data) -> bool`
**Pre:** All indicators calculated and valid
**Post:** Returns True if RSI overbought (>55) with bearish confirmations
**Raises:** None
**Retry:** No
**Side Effects:** Logs rejections with diagnostic info

### `_create_buy_signal(market_data, rsi, ema, volume_ratio, roc, atr) -> Signal`
**Pre:** All parameters valid
**Post:** Returns Signal object with BUY type and complete metadata
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_create_sell_signal(market_data, rsi, ema, volume_ratio, roc, atr) -> Signal`
**Pre:** All parameters valid
**Post:** Returns Signal object with SELL type and complete metadata
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] generate_signals returns BUY only when RSI < 70 (never buy overbought)
- [ ] generate_signals returns SELL only when RSI > 30 (never sell oversold)
- [ ] Cooldown mechanism prevents signals within cooldown_bars of last signal
- [ ] ATR volatility filter rejects signals when volatility too low
- [ ] Stochastic RSI filter reduces false signals when enabled
- [ ] risk_check rejects BUY when insufficient cash
- [ ] risk_check rejects SELL when no position exists
- [ ] risk_check rejects signals when total exposure > max_exposure
- [ ] All signals processed through SignalScoringEngine
- [ ] TechnicalIndicatorCalculator used for all indicator calculations (no manual math)
- [ ] Type hints present on all methods (100% coverage)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage on all functions | ✅ OK - All methods have type hints |
| TYP-002 | 02-type-hints.md | Use modern syntax (X \| None) | ❌ GAP - Uses typing.Optional instead of X \| None |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK - No mutable defaults in __init__ |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Only handles momentum signal generation |
| SOL-005 | 03-solid-principles.md | Dependency Inversion | ✅ OK - Depends on BaseStrategy abstraction |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK - All method names are clear |
| TRD-002 | 13-trading-specific | Risk validation before trading | ✅ OK - risk_check enforces exposure/cash limits |
| TRD-003 | 13-trading-specific | Position limits enforced | ✅ OK - Uses max_position_size from config |
| BT-003 | 13-trading-specific | No look-ahead bias | ✅ OK - Only uses historical data from deques |
| LOG-003 | 09-logging-observability.md | Appropriate log levels | ❌ GAP - Mixes DEBUG/INFO for similar diagnostics |
| LOG-004 | 09-logging-observability.md | Error logging with stack traces | ✅ OK - All exceptions logged with exc_info=True |
| ARCH-001 | 05-architecture.md | Layered architecture | ✅ OK - In domain layer, no framework imports |
| PERF-001 | 19-high-performance-python.md | Use vectorized operations | ✅ OK - Uses TechnicalIndicatorCalculator with numpy/pandas |

**GAP Analysis:**
- **TYP-002**: Uses `typing.Optional` instead of modern `X | None` syntax. This is valid Python but not the modern preferred syntax.
- **LOG-003**: Inconsistent use of DEBUG vs INFO for diagnostics. Some diagnostic info logged at DEBUG, others at INFO. Should be consistent.

---

## Dependencies
- **External:** logging, collections.deque, decimal.Decimal, typing (Any, Dict, List, Optional)
- **Internal:**
  - app.core.centralized_config (get_strategy_config, get_trading_threshold)
  - app.models.market_data.Quote
  - app.models.portfolio.Portfolio
  - app.models.signal (Signal, SignalSource, SignalStrength, SignalType)
  - app.services.momentum_analysis.TechnicalIndicatorCalculator
  - app.services.signal_scoring_engine.get_signal_scoring_engine
  - .base.BaseStrategy

---

## Required Tests
- **tests/unit/strategies/test_momentum_strategy.py:**
  - Test initialization with config from centralized_config
  - Test initialization with fallback to config dict
  - Test generate_signals with insufficient history (returns empty)
  - Test generate_signals generates BUY when RSI in momentum zone (40-70)
  - Test generate_signals NEVER generates BUY when RSI > 70
  - Test generate_signals generates SELL when RSI > 55 with bearish signals
  - Test generate_signals NEVER generates SELL when RSI < 30
  - Test cooldown mechanism prevents duplicate signals
  - Test ATR filter rejects low volatility signals
  - Test Stochastic RSI filter reduces signals when enabled
  - Test risk_check rejects BUY when cash insufficient
  - Test risk_check rejects SELL when no position exists
  - Test risk_check rejects when exposure > max_exposure
  - Test signals processed through SignalScoringEngine
  - Test _calculate_volume_ratio with insufficient history returns 1
  - Test _passes_atr_filter with relative ATR calculation
  - Test all exception paths return empty list / False with logging

---

## Notes
- Strategy uses vectorized TechnicalIndicatorCalculator for all indicator math (no manual calculations)
- Implements cooldown mechanism (default 5 bars) to prevent signal spam
- ATR volatility filter can use relative ATR (% of price) or absolute ATR
- Stochastic RSI filter is optional and configurable
- Signal Scoring Engine processes all raw signals before return
- Extensive logging for diagnostics: DEBUG for per-bar checks, INFO for signal generation
- Momentum strategy: buys on trend continuation (RSI 40-70, price > EMA), NOT on oversold reversals
- SELL only when RSI overbought (>55) with bearish confirmation, NOT when RSI oversold
