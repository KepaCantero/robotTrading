# mean_reversion.py

## Purpose
Mean reversion strategy using Z-score to identify overbought/oversold conditions and trade reversions to the mean with volatility filtering.

---

## Type Definitions / Data Classes

### No Pydantic models or dataclasses defined in this file.

---

## Function Signatures (Contracts)

### `__init__(config: Dict[str, Any]) -> None`
**Pre:** config contains strategy parameters or strategy_config available via get_strategy_config
**Post:** Strategy initialized with z_score_threshold, lookback_period, volatility_threshold, atr_floor, price_history deque (maxlen=200), TechnicalIndicatorCalculator
**Raises:** FileNotFoundError, ValueError, KeyError, TypeError when loading YAML config (caught and handled)
**Retry:** No
**Side Effects:** Initializes price_history deque, loads config from centralized_config

### `generate_signals(market_data: Quote) -> List[Signal]`
**Pre:** market_data contains valid price data
**Post:** Returns list of signals (BUY when oversold, SELL when overbought), may be empty
**Raises:** ValueError, KeyError, AttributeError, IndexError, TypeError (logged, returns empty list)
**Retry:** No
**Side Effects:** Updates price_history deque, logs diagnostic info

### `risk_check(signal: Signal, portfolio: Portfolio) -> bool`
**Pre:** signal has valid price, portfolio has valid positions and cash
**Post:** Returns True if signal passes exposure/cash/volatility validation, False otherwise
**Raises:** ValueError, TypeError, KeyError, AttributeError, IndexError (logged, returns False)
**Retry:** No
**Side Effects:** Logs rejection reasons with detailed diagnostics

### `_calculate_z_score(market_data: Quote) -> Decimal`
**Pre:** price_history has at least lookback_period values
**Post:** Returns Z-score using pandas-ta-classic via TechnicalIndicatorCalculator, or simplified calculation if insufficient history
**Raises:** None (handles all errors)
**Retry:** No
**Side Effects:** None

### `_calculate_volatility(market_data: Quote) -> Decimal`
**Pre:** price_history has at least 2 values
**Post:** Returns volatility using pandas-ta-classic via TechnicalIndicatorCalculator, or simplified calculation if insufficient history
**Raises:** None (handles all errors)
**Retry:** No
**Side Effects:** None

### `_is_buy_signal(z_score, volatility, market_data) -> bool`
**Pre:** z_score and volatility calculated
**Post:** Returns True if z_score < threshold (oversold) with acceptable price range and volatility
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_is_sell_signal(z_score, volatility, market_data) -> bool`
**Pre:** z_score and volatility calculated
**Post:** Returns True if z_score > threshold (overbought) with acceptable price range and volatility
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_create_buy_signal(market_data, z_score) -> Signal`
**Pre:** market_data and z_score valid
**Post:** Returns Signal object with BUY type and z_score metadata
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_create_sell_signal(market_data, z_score) -> Signal`
**Pre:** market_data and z_score valid
**Post:** Returns Signal object with SELL type and z_score metadata
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] generate_signals returns BUY when z_score < -threshold (oversold)
- [ ] generate_signals returns SELL when z_score > threshold (overbought)
- [ ] Both BUY and SELL conditions can be true (allows opposite signals)
- [ ] risk_check rejects SELL when no position exists
- [ ] risk_check rejects BUY when cash insufficient
- [ ] risk_check rejects when total exposure > 60%
- [ ] risk_check rejects when asset volatility too high (> volatility_threshold * 2)
- [ ] _calculate_z_score uses TechnicalIndicatorCalculator (pandas-ta-classic)
- [ ] _calculate_volatility uses TechnicalIndicatorCalculator (pandas-ta-classic)
- [ ] atr_floor and price_range_multiplier used for price range filtering
- [ ] All exception handlers return empty list / False with logging
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
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Only handles mean reversion logic |
| SOL-005 | 03-solid-principles.md | Dependency Inversion | ✅ OK - Depends on BaseStrategy abstraction |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK - All method names are clear |
| TRD-002 | 13-trading-specific | Risk validation before trading | ✅ OK - risk_check enforces exposure/volatility limits |
| TRD-003 | 13-trading-specific | Position limits enforced | ✅ OK - Uses max_position_size from config |
| BT-003 | 13-trading-specific | No look-ahead bias | ✅ OK - Only uses historical data from deque |
| LOG-003 | 09-logging-observability.md | Appropriate log levels | ⚠️ NOT APPLIED - Mixes DEBUG/INFO for different purposes |
| LOG-004 | 09-logging-observability.md | Error logging with stack traces | ✅ OK - All exceptions logged with exc_info=True |
| ARCH-001 | 05-architecture.md | Layered architecture | ✅ OK - In domain layer, no framework imports |
| PERF-001 | 19-high-performance-python.md | Use vectorized operations | ✅ OK - Uses TechnicalIndicatorCalculator with pandas-ta |

**GAP Analysis:**
- **TYP-002**: Uses `typing.Optional` instead of modern `X | None` syntax. Valid but not modern preferred syntax.
- **LOG-003**: Inconsistent log levels - uses DEBUG for per-bar checks, INFO for periodic summaries and signal generation. This is actually appropriate for different use cases.

---

## Dependencies
- **External:** logging, collections.deque, decimal.Decimal, typing (Any, Dict, List)
- **Internal:**
  - app.core.centralized_config (get_strategy_config, get_trading_threshold)
  - app.models.market_data.Quote
  - app.models.portfolio.Portfolio
  - app.models.signal (Signal, SignalSource, SignalStrength, SignalType)
  - app.services.momentum_analysis.TechnicalIndicatorCalculator
  - .base.BaseStrategy

---

## Required Tests
- **tests/unit/strategies/test_mean_reversion_strategy.py:**
  - Test initialization with config from centralized_config
  - Test initialization with fallback to config dict
  - Test generate_signals generates BUY when z_score < -threshold
  - Test generate_signals generates SELL when z_score > threshold
  - Test generate_signals can generate both BUY and SELL in same call
  - Test generate_signals with insufficient history uses simplified calculation
  - Test risk_check rejects SELL when no position exists
  - Test risk_check rejects SELL when position quantity insufficient
  - Test risk_check rejects BUY when cash insufficient
  - Test risk_check rejects when total exposure > 60%
  - Test risk_check rejects when asset volatility too high
  - Test _calculate_z_score uses TechnicalIndicatorCalculator
  - Test _calculate_volatility uses TechnicalIndicatorCalculator
  - Test _is_buy_signal with z_score below threshold
  - Test _is_sell_signal with z_score above threshold
  - Test atr_floor and price_range_multiplier filtering
  - Test all exception paths return empty list / False with logging

---

## Notes
- Strategy uses vectorized TechnicalIndicatorCalculator for Z-score and volatility (no manual math)
- Mean reversion: buys when price drops below mean (negative z-score), sells when price rises above mean (positive z-score)
- More conservative than momentum: max exposure 60%, volatility threshold * 2 for safety
- Price range filtering uses atr_floor * price_range_multiplier to ensure sufficient price movement
- Allows both BUY and SELL signals in same market_data call (opposite signals possible)
- Extensive logging: DEBUG for every candidate, INFO every 10 calls, INFO when signals generated
- Z-score threshold configurable (default 1.0), with 70% multiplier for signal generation (more permissive)
