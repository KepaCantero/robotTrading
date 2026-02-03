# carver_robust_rules.py

## Purpose
Implements Robert Carver's Robust Rules Strategy following his "Systematic Trading" methodology. Uses simple, robust trading rules with fixed timestamp execution, handcrafted portfolio weights, and decay factors for smooth transitions.

---

## Type Definitions / Data Classes

No custom dataclasses defined - uses imports from app.models.*

---

## Function Signatures (Contracts)

### `CarverRobustRulesStrategy.__init__(config: Dict[str, Any])`
**Pre:** config contains required parameters
**Post:** Strategy initialized with configuration
**Raises:** ValueError if invalid configuration
**Retry:** No
**Side Effects:** Initializes deques for price history

### `CarverRobustRulesStrategy.generate_signals(market_data: Quote) -> List[Signal]`
**Pre:** market_data contains valid price fields
**Post:** Returns list of trading signals (empty if no signal)
**Raises:** Logs exceptions, returns empty list
**Retry:** No
**Side Effects:** Updates price history deques

### `CarverRobustRulesStrategy._should_execute_at_fixed_timestamp() -> bool`
**Pre:** None
**Post:** Returns True if at fixed execution time
**Raises:** None (logs warnings for invalid formats)
**Retry:** No
**Side Effects:** Updates last_execution_time and last_execution_date

### `CarverRobustRulesStrategy._calculate_volatility(prices_list: List[float]) -> float`
**Pre:** prices_list length >= 2
**Post:** Returns annualized volatility
**Raises:** None (returns default 0.02)
**Retry:** No
**Side Effects:** None

### `CarverRobustRulesStrategy._get_handcrafted_weight(symbol: str, volatility: float) -> float`
**Pre:** volatility >= 0
**Post:** Returns weight for position sizing [0, 1]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `CarverRobustRulesStrategy._apply_decay_factor(current_weight: float, previous_weight: Optional[float]) -> float`
**Pre:** current_weight in [0, 1]
**Post:** Returns decayed weight
**Raises:** None
**Retry:** No
**Side Effects:** None

### `CarverRobustRulesStrategy.risk_check(signal: Signal, portfolio: Portfolio) -> bool`
**Pre:** portfolio is valid
**Post:** Returns True if signal passes risk checks
**Raises:** None (logs errors, returns False)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Fixed timestamp execution only triggers at specified times (09:30, 16:00)
- [ ] Moving average calculation uses correct lookback period
- [ ] Volatility calculation annualizes using sqrt(252)
- [ ] Handcrafted weights scale inversely with volatility
- [ ] Decay factor smooths position transitions
- [ ] Risk checks validate position size and cash availability
- [ ] Market data validation checks symbol, price, volume
- [ ] Execution only occurs once per day per timestamp

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent-python-expert (via Tech Lead Orchestrator) |
| **GAPs Fixed** | 0 / ? total |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-001 | BASE_RULES | Structured logging | ✅ FIXED - Changed to structured logging (lines 177, 182, 204, 216, 228) |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ OK - Uses exc_info=True (lines 234, 520) |
| CC-006 | BASE_RULES | Explicit error handling | ✅ FIXED - Uses specific exceptions (line 231, 519) |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ FIXED - Added -> Signal return type |
| TRD-002 | BASE_RULES | Risk validation | ✅ OK - Position and cash validation |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - All decisions logged |
| SEC-007 | BASE_RULES | Input validation | ✅ OK - Market data validation |
| ARCH-004 | BASE_RULES | Small functions (<20 lines) | ⚠️ PARTIAL - Some functions >20 lines |

---

## Dependencies
- **External:** logging, collections, datetime, decimal, typing
- **Internal:** 
  - app.core.centralized_config (get_strategy_config, get_trading_threshold)
  - app.models.market_data.Quote
  - app.models.portfolio.Portfolio
  - app.models.signal (Signal, SignalSource, SignalStrength, SignalType)
  - app.services.momentum_analysis.TechnicalIndicatorCalculator
  - app.services.scheduling.market_scheduler (MarketScheduler, MarketType)
  - .base.BaseStrategy

---

## Required Tests
- **tests/strategies/test_carver_robust_rules.py:**
  - Test generate_signals with buy condition (price > MA)
  - Test generate_signals with sell condition (price < MA)
  - Test fixed timestamp execution at correct time
  - Test fixed timestamp execution skips non-execution times
  - Test volatility calculation with sufficient data
  - Test volatility calculation with insufficient data
  - Test handcrafted weight calculation with predefined weight
  - Test handcrafted weight calculation based on volatility
  - Test decay factor application with previous weight
  - Test decay factor without previous weight
  - Test risk_check passes for valid BUY signal
  - Test risk_check rejects SELL without position
  - Test risk_check rejects BUY with insufficient cash

---

## Notes
- Reference: Robert Carver "Systematic Trading"
- Fixed timestamp execution reduces "timing luck"
- Handcrafted weights based on instrument risk characteristics
- Volatility target: 15% annualized by default
- Instrument diversification limit: 40% by default
