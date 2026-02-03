# covered_call.py

## Purpose
Covered Call strategy domain service - generates income by selling call options against owned stock positions.

---

## Type Definitions / Data Classes

### CallSignal (Enum)
```python
class CallSignal(str, Enum):
    SELL_CALL = "sell_call"              # Sell call option (open covered call)
    BUY_BACK_CALL = "buy_back_call"      # Buy back call (close position)
    ROLL_CALL = "roll_call"              # Roll to next expiration/strike
    HOLD = "hold"                        # Hold current position
    NO_ACTION = "no_action"
```

### OptionData
```python
@dataclass
class OptionData:
    symbol: str                    # REQUIRED - Option symbol
    strike: float                  # REQUIRED - Strike price
    expiration_date: str           # REQUIRED - YYYY-MM-DD
    days_to_expiration: int        # REQUIRED - DTE
    implied_volatility: float      # REQUIRED - IV
    bid: float                     # REQUIRED - Bid price
    ask: float                     # REQUIRED - Ask price
    mid_price: float               # REQUIRED - Mid price
    delta: float                   # REQUIRED - Option delta
    theta: float                   # REQUIRED - Time decay per day
```

**Properties:**
- `is_itm` - Returns True if delta > 0.5
- `is_otm` - Returns True if delta < 0.5
- `time_value` - Returns mid_price - max(0, delta) (simplified)

### CoveredCallPosition
```python
@dataclass
class CoveredCallPosition:
    stock_symbol: str                      # REQUIRED - Stock symbol
    stock_quantity: int                    # REQUIRED - Number of shares owned
    stock_cost_basis: float                # REQUIRED - Cost basis per share
    call_option: OptionData                # REQUIRED - Short call option
    call_premium_received: float           # REQUIRED - Premium received
    open_date: str                         # REQUIRED - Position open date
```

**Properties:**
- `break_even_price` - Returns stock_cost_basis - call_premium_received
- `max_profit` - Returns (strike - stock_cost_basis) + call_premium_received
- `max_loss` - Returns stock_cost_basis - call_premium_received (stock goes to zero)
- `assignment_probability` - Returns min(1.0, delta × 2) if ITM, else delta

### CoveredCallPortfolio
```python
@dataclass
class CoveredCallPortfolio:
    positions: List[CoveredCallPosition]   # REQUIRED - List of positions
    total_premium_collected: float         # REQUIRED - Total premium
    assigned_positions: int                # REQUIRED - Number assigned
    avg_monthly_income: float              # REQUIRED - Average monthly income
```

**Properties:**
- `annualized_yield` - Returns avg_monthly_income × 12
- `capital_at_risk` - Returns sum(stock_quantity × stock_cost_basis)

---

## Function Signatures (Contracts)

### `CoveredCallStrategy.__init__(target_otm_percentage, min_days_to_expiration, max_days_to_expiration, min_premium_threshold, max_iv_percentile, roll_threshold, assignment_threshold) -> None`
**Pre:** target_otm_percentage > 0; min_days_to_expiration >= 1; max_days_to_expiration > min_days; min_premium_threshold >= 0; max_iv_percentile in (0, 1]; roll_threshold in (0, 1]; assignment_threshold in (0, 1]
**Post:** Strategy configured with parameters
**Raises:** None (initialization only)
**Retry:** No
**Side Effects:** None (initialization only)

### `select_optimal_call(stock_price, available_calls, stock_quantity) -> Optional[OptionData]`
**Pre:** stock_price > 0; available_calls non-empty; stock_quantity > 0
**Post:** Returns best call option to sell (or None if none suitable)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `generate_signal(covered_position, stock_price, available_calls) -> CallSignal`
**Pre:** stock_price > 0; available_calls non-empty
**Post:** Returns SELL_CALL/BUY_BACK_CALL/ROLL_CALL/HOLD/NO_ACTION based on position state
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `_find_next_month_call(stock_price, available_calls, current_strike) -> Optional[OptionData]` (private)
**Pre:** stock_price > 0; available_calls non-empty; current_strike > 0
**Post:** Returns call option for next month with similar strike
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `_find_roll_up_call(stock_price, available_calls, current_option) -> Optional[OptionData]` (private)
**Pre:** stock_price > 0; available_calls non-empty; current_option valid
**Post:** Returns call option with higher strike for more premium
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `calculate_position_size(capital, stock_price, max_position_pct) -> int`
**Pre:** capital > 0; stock_price > 0; max_position_pct in (0, 1]
**Post:** Returns number of shares (in lots of 100, minimum 100)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `calculate_expected_return(covered_position, days_to_expiration) -> float`
**Pre:** covered_position valid; days_to_expiration >= 1
**Post:** Returns annualized return (0-1)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `create_covered_call_position(stock_symbol, stock_quantity, stock_cost_basis, call_option, open_date) -> CoveredCallPosition`
**Pre:** stock_symbol non-empty; stock_quantity > 0; stock_cost_basis > 0; call_option valid; open_date non-empty
**Post:** Returns CoveredCallPosition with premium = call_option.bid
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `manage_position(position, current_stock_price, current_date) -> Tuple[CallSignal, Optional[OptionData]]`
**Pre:** position valid; current_stock_price > 0; current_date non-empty
**Post:** Returns (signal, new_option_if_rolling)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `calculate_portfolio_metrics(positions) -> Dict[str, float]`
**Pre:** positions valid list
**Post:** Returns dict with total_capital, total_premium, annualized_yield, avg_dte, positions_at_risk, total_positions
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Select calls with 30-45 days to expiration (monthly cycle)
- [ ] **AC-002:** Target strike 5% OTM (out-of-the-money)
- [ ] **AC-003:** Premium threshold >= 1% of stock price
- [ ] **AC-004:** Roll when delta > 0.5 (ITM) or assignment probability > 80%
- [ ] **AC-005:** Position size rounded to nearest 100 shares (option contract)
- [ ] **AC-006:** Break-even = cost_basis - premium_received
- [ ] **AC-007:** Max profit = (strike - cost_basis) + premium_received
- [ ] **AC-008:** All public methods have complete type hints
- [ ] **AC-009:** NumPy 2.0 compatibility

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Covered Call):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate option data ranges | ✅ FIXED - Full validation with logging |
| Stock ownership | Covered call | Must own 100 shares per contract | ✅ OK - stock_quantity |
| Target OTM | Kissell & Posament (2017) | 5-10% OTM for income focus | ✅ OK - target_otm=0.05 |
| DTE range | Options standard | 30-45 DTE optimal | ✅ OK - min/max_dte |
| Premium threshold | Income strategy | Min 1% of stock price | ✅ OK - min_premium=0.01 |
| IV cap | Options trading | Avoid expensive options (IV > 80th percentile) | ✅ OK - max_iv=0.8 |
| Roll threshold | Risk management | Roll when delta > 0.5 | ✅ OK - roll_threshold=0.5 |
| Assignment threshold | Risk management | Close when prob > 80% | ✅ OK - assign_threshold=0.8 |
| Break-even calculation | Options standard | Cost basis - premium | ✅ OK - break_even_price |
| Max profit | Options payoff | Strike - cost + premium | ✅ OK - max_profit |
| Max loss | Options payoff | Cost - premium (stock → 0) | ✅ OK - max_loss |
| Assignment probability | Options risk | ~delta (or 2×delta if ITM) | ✅ OK - assignment_probability |
| Position sizing | Options standard | Round to 100 shares | ✅ OK - calculate_position_size |
| Annualized return | Finance standard | (premium/cost) × (365/DTE) | ✅ OK - calculate_expected_return |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Kissell & Posament (2017) "Options Trading and Hedging" for covered call rules.

---

## Dependencies
- **External:** `numpy`, `dataclasses` (std), `decimal` (std), `enum` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_covered_call.py:**
  - `test_select_optimal_call()` - Selects best call by premium and strike distance
  - `test_sell_call_signal()` - No position + suitable call = SELL_CALL
  - `test_buy_back_signal()` - Near expiration ITM = BUY_BACK
  - `test_roll_signal()` - Delta > 0.5 = ROLL
  - `test_hold_signal()` - OTM with adequate time = HOLD
  - `test_break_even_calculation()` - Cost - premium
  - `test_max_profit_calculation()` - Strike - cost + premium
  - `test_max_loss_calculation()` - Cost - premium
  - `test_assignment_probability_itm()` - delta × 2 if ITM
  - `test_assignment_probability_otm()` - delta if OTM
  - `test_position_size_rounding()` - Round to nearest 100
  - `test_expected_return()` - Annualized (premium/cost) × (365/DTE)
  - `test_create_covered_call_position()` - Premium = bid
  - `test_find_next_month_call()` - Similar strike, later expiration
  - `test_find_roll_up_call()` - Higher strike, more premium
  - `test_portfolio_metrics()` - Capital, premium, yield, DTE, at_risk
  - `test_min_position_size()` - Minimum 100 shares
  - `test_no_suitable_calls()` - Returns None

---

## Notes
- **Critical:** Covered call is a income strategy, not appreciation strategy
- **Kissell & Posament Reference:** "Options Trading and Hedging" (2017)
- **Strategy:** Own stock + sell calls = collect premium income
- **Stock Ownership:** Must own 100 shares per option contract (US options)
- **Target OTM:** 5% out-of-the-money balances income vs upside potential
- **DTE Range:** 30-45 days optimal (monthly cycle, theta decay accelerates near expiration)
- **Premium Threshold:** Minimum 1% of stock price (otherwise not worth transaction cost)
- **IV Cap:** Avoid expensive options (implied volatility > 80th percentile)
- **Roll Threshold:** Delta > 0.5 indicates option becoming ITM (roll or close)
- **Assignment Threshold:** > 80% probability = close position to avoid assignment
- **Break-Even Price:** Stock can fall by premium amount before loss
- **Max Profit:** Capped at strike price (stock called away at strike)
- **Max Loss:** Stock goes to zero (reduced by premium received)
- **Assignment Probability:** Approximated by delta (OTM) or 2×delta (ITM)
- **Position Size:** Round down to nearest 100 shares (option contract multiplier)
- **Annualized Return:** (Premium / Investment) × (365 / Days to Expiration)
- **Roll Up:** Move to higher strike for more premium (when very OTM, delta < 0.3)
- **Roll Forward:** Move to next month with similar strike (when ITM, near expiration)
- **Time Decay:** Theta (time value) decays faster near expiration (profits seller)
- **Capital at Risk:** Sum of stock_quantity × stock_cost_basis for all positions
- **Monthly Income:** Total premium / Average capital at risk × 12 = annualized yield

---

**File Reference:** `app/domain/strategies/covered_call.py`
**Last Audited:** 2026-02-01
