# pairs_trading.py

## Purpose
Pairs trading strategy using cointegration and correlation to trade mean reversion of price spreads between two related assets (e.g., AAPL-MSFT).

---

## Type Definitions / Data Classes

### No Pydantic models or dataclasses defined in this file.

---

## Function Signatures (Contracts)

### `__init__(config: Dict[str, Any]) -> None`
**Pre:** config contains pair_symbols list or strategy_config available via get_strategy_config
**Post:** Strategy initialized with cointegration_threshold, spread_threshold, min_correlation, hedge_ratio, price_history defaultdict(deque maxlen=300), trade limiting counters
**Raises:** FileNotFoundError, ValueError, KeyError, TypeError when loading YAML config (caught and handled)
**Retry:** No
**Side Effects:** Initializes price_history defaultdict for both symbols, loads config from centralized_config

### `generate_signals(market_data: Quote) -> List[Signal]`
**Pre:** market_data contains valid price data
**Post:** Returns list of signals for both symbols in pair when spread deviates significantly, may be empty
**Raises:** ValueError, KeyError, AttributeError, IndexError, TypeError (logged, returns empty list)
**Retry:** No
**Side Effects:** Updates price_history, checks daily trade limits, may reset trades_today counter

### `risk_check(signal: Signal, portfolio: Portfolio) -> bool`
**Pre:** signal has valid price, portfolio has valid positions and cash
**Post:** Returns True if signal passes exposure/cash/pair_exposure validation, False otherwise
**Raises:** ValueError, TypeError, KeyError, AttributeError, IndexError (logged, returns False)
**Retry:** No
**Side Effects:** Logs rejection reasons with detailed diagnostics

### `_calculate_spread(market_data: Quote) -> Decimal`
**Pre:** price_history has at least 2 values for both symbols
**Post:** Returns spread as decimal percentage using numpy linear regression for hedge ratio (beta)
**Raises:** None (handles division by zero)
**Retry:** No
**Side Effects:** Stores hedge_ratio in instance variable

### `_calculate_correlation(market_data: Quote) -> Decimal`
**Pre:** price_history has at least 2 values for both symbols
**Post:** Returns correlation coefficient (0-1) using numpy.corrcoef
**Raises:** None (handles NaN)
**Retry:** No
**Side Effects:** None

### `_calculate_cointegration_score(market_data: Quote) -> Decimal`
**Pre:** price_history has at least 60 values for both symbols
**Post:** Returns cointegration score (0-1) using scipy/numpy, recalculated every 30 days (cached)
**Raises:** ValueError, KeyError, AttributeError, IndexError, TypeError (logged, returns default 0.75)
**Retry:** No
**Side Effects:** Updates cached_cointegration_score, cached_hedge_ratio, last_cointegration_recalc_date

### `_create_pair_signals(market_data: Quote, spread: Decimal) -> List[Signal]`
**Pre:** market_data and spread valid
**Post:** Returns list of signals for one or both symbols based on spread direction
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_total_exposure(portfolio: Portfolio) -> Decimal`
**Pre:** portfolio valid
**Post:** Returns total exposure as percentage (invested_value / total_value)
**Raises:** None (handles division by zero)
**Retry:** No
**Side Effects:** None

### `_calculate_pair_exposure(portfolio: Portfolio) -> Decimal`
**Pre:** portfolio valid
**Post:** Returns pair exposure as percentage (pair_value / total_value)
**Raises:** None (handles division by zero)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] generate_signals only processes symbols in pair_symbols list
- [ ] generate_signals checks daily trade limit (max_trades_per_day)
- [ ] generate_signals resets trades_today counter when date changes
- [ ] Signals only generated when spread > spread_threshold AND correlation >= min_correlation AND cointegration >= cointegration_threshold
- [ ] _calculate_spread uses numpy linear regression for hedge ratio (beta)
- [ ] _calculate_correlation uses numpy.corrcoef for vectorized calculation
- [ ] _calculate_cointegration_score recalculates every 30 days (rolling window)
- [ ] Cointegration score cached between recalculations
- [ ] risk_check rejects when total_exposure > max_total_exposure (default 40%)
- [ ] risk_check rejects when pair_exposure > max_pair_exposure (default 20%)
- [ ] risk_check allows higher exposure (15%) for SELL with existing position
- [ ] Spread z-score and half-life filters applied when sufficient data
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
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK - defaultdict with lambda is intentional |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Only handles pairs trading logic |
| SOL-005 | 03-solid-principles.md | Dependency Inversion | ✅ OK - Depends on BaseStrategy abstraction |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK - All method names are clear |
| TRD-002 | 13-trading-specific | Risk validation before trading | ✅ OK - risk_check enforces exposure limits |
| TRD-003 | 13-trading-specific | Position limits enforced | ✅ OK - Uses max_position_size from config |
| BT-003 | 13-trading-specific | No look-ahead bias | ✅ OK - Only uses historical data from deques |
| LOG-003 | 09-logging-observability.md | Appropriate log levels | ⚠️ NOT APPLIED - Mixes DEBUG/INFO/WARNING |
| LOG-004 | 09-logging-observability.md | Error logging with stack traces | ✅ OK - All exceptions logged with exc_info=True |
| ARCH-001 | 05-architecture.md | Layered architecture | ✅ OK - In domain layer, no framework imports |
| PERF-001 | 19-high-performance-python.md | Use vectorized operations | ✅ OK - Uses numpy/scipy for all calculations |

**GAP Analysis:**
- **TYP-002**: Uses `typing.Optional` instead of modern `X | None` syntax. Valid but not modern preferred syntax.
- **LOG-003**: Inconsistent log levels - uses DEBUG for per-bar checks, INFO for periodic logs, WARNING for edge cases. This is appropriate for different scenarios.

---

## Dependencies
- **External:** logging, collections.defaultdict, collections.deque, decimal.Decimal, typing (Any, Dict, List), numpy (as np), scipy.stats
- **Internal:**
  - app.core.centralized_config (get_strategy_config, get_trading_threshold)
  - app.models.market_data.Quote
  - app.models.portfolio.Portfolio
  - app.models.signal (Signal, SignalSource, SignalStrength, SignalType)
  - .base.BaseStrategy

---

## Required Tests
- **tests/unit/strategies/test_pairs_trading_strategy.py:**
  - Test initialization with pair_symbols from config
  - Test initialization with fallback to ["AAPL", "MSFT"]
  - Test generate_symbols ignores symbols not in pair_symbols
  - Test generate_signals checks daily trade limit
  - Test generate_signals resets trades_today when date changes
  - Test generate_signals requires spread, correlation, cointegration thresholds
  - Test _calculate_spread uses numpy linear regression
  - Test _calculate_spread calculates hedge ratio (beta) correctly
  - Test _calculate_correlation uses numpy.corrcoef
  - Test _calculate_cointegration_score recalculates every 30 days
  - Test _calculate_cointegration_score caches result between recalculations
  - Test _calculate_cointegration_score handles insufficient data (< 60 days)
  - Test _create_pair_signals generates correct signals for spread direction
  - Test risk_check rejects when total_exposure > max_total_exposure
  - Test risk_check rejects when pair_exposure > max_pair_exposure
  - Test risk_check allows higher exposure for SELL with existing position
  - Test spread z-score and half-life filters when sufficient data
  - Test all exception paths return empty list / False with logging

---

## Notes
- Pairs trading requires TWO related assets (e.g., AAPL-MSFT, GLD-GDX)
- Uses cointegration (long-term equilibrium) + correlation (short-term relationship) for signal validation
- Spread calculation: spread = price2 - (beta * price1), where beta is hedge ratio from linear regression
- Rolling cointegration window: 250 days or available history (min 60 for reliability), recalculated every 30 days
- Trade frequency limiting: max_trades_per_day configurable (default varies)
- Very conservative: max 40% total exposure, 20% pair exposure
- Minimum edge filters: spread_z_score, half_life_days to avoid poor quality pairs
- Vectorized calculations using numpy/scipy for performance
- Extensive logging: DEBUG for per-bar checks, INFO every 10 calls, INFO when signals generated
- Spread threshold configured as percentage (e.g., 1.2 = 120%), converted to decimal for comparison
- Allows SELL signals even when pair exposure temporarily high (to close positions)
