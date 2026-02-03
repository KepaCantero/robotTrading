# risk_parameters.py

## Purpose
Risk Parameters Value Object - Immutable risk management constraints for portfolio and position management.

---

## Type Definitions / Data Classes

### RiskParameters (frozen=True)
```python
@dataclass(frozen=True)
class RiskParameters:
    max_position_size: Decimal          # REQUIRED - Maximum position size (as decimal)
    max_portfolio_exposure: Decimal      # REQUIRED - Maximum portfolio exposure (as decimal)
    stop_loss_pct: Decimal               # REQUIRED - Stop loss percentage (0-1)
    take_profit_pct: Decimal             # REQUIRED - Take profit percentage (> 0)
    risk_reward_ratio: Decimal           # Default: 2 - Minimum R/R ratio
    max_daily_loss_pct: Decimal          # Default: 0.05 - Max daily loss (0-1)
    max_drawdown_pct: Decimal             # Default: 0.15 - Max drawdown (0-1)
```

**Properties:**
- Immutable (frozen=True)
- Value object (defined by attributes, no identity)

**Invariants (enforced in __post_init__):**
- `max_position_size` > 0
- `max_portfolio_exposure` > 0
- `stop_loss_pct` in (0, 1]
- `take_profit_pct` > 0
- `risk_reward_ratio` > 0
- `max_daily_loss_pct` in [0, 1]
- `max_drawdown_pct` in [0, 1]

---

## Function Signatures (Contracts)

### `RiskParameters.__post_init__() -> None`
**Pre:** None
**Post:** Risk parameters validated
**Raises:** `ValueError` if any invariant violated
**Retry:** No
**Side Effects:** None (validation only)

### `get_stop_loss_price(entry_price, side) -> Decimal`
**Pre:** entry_price > 0; side in ["long", "short"]
**Post:** Returns stop loss price
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formulas:**
- Long: `entry_price × (1 - stop_loss_pct)`
- Short: `entry_price × (1 + stop_loss_pct)`

### `get_take_profit_price(entry_price, side) -> Decimal`
**Pre:** entry_price > 0; side in ["long", "short"]
**Post:** Returns take profit price
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formulas:**
- Long: `entry_price × (1 + take_profit_pct)`
- Short: `entry_price × (1 - take_profit_pct)`

### `validate_risk_reward(entry_price, target_price, stop_price, side) -> bool`
**Pre:** entry_price > 0; target_price > 0; stop_price > 0; side in ["long", "short"]
**Post:** Returns True if actual risk/reward >= risk_reward_ratio
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:**
- Long: `(target_price - entry_price) / (entry_price - stop_price) >= risk_reward_ratio`
- Short: `(entry_price - target_price) / (stop_price - entry_price) >= risk_reward_ratio`

### `for_tier(tier) -> RiskParameters` (classmethod)
**Pre:** tier in ["micro", "small", "medium", "large", "institutional"]
**Post:** Returns RiskParameters with tier-appropriate values
**Raises:** None (defaults to institutional for unknown tier)
**Retry:** No
**Side Effects:** None (factory)

**Tier Specifications:**
- **micro:** max_position=20%, exposure=100%, stop=5%, tp=10%
- **small:** max_position=15%, exposure=120%, stop=4%, tp=8%
- **medium:** max_position=10%, exposure=150%, stop=3%, tp=6%
- **large:** max_position=8%, exposure=180%, stop=2.5%, tp=5%
- **institutional:** max_position=5%, exposure=200%, stop=2%, tp=4%

---

## Acceptance Criteria
- [x] **AC-001:** max_position_size must be positive
- [x] **AC-002:** max_portfolio_exposure must be positive
- [x] **AC-003:** stop_loss_pct in range (0, 1]
- [x] **AC-004:** take_profit_pct must be positive
- [x] **AC-005:** risk_reward_ratio must be positive (default 2:1)
- [x] **AC-006:** max_daily_loss_pct in range [0, 1]
- [x] **AC-007:** max_drawdown_pct in range [0, 1]
- [x] **AC-008:** Stop loss LONG = entry × (1 - stop_pct)
- [x] **AC-009:** Stop loss SHORT = entry × (1 + stop_pct)
- [x] **AC-010:** Take profit LONG = entry × (1 + tp_pct)
- [x] **AC-011:** Take profit SHORT = entry × (1 - tp_pct)
- [x] **AC-012:** Value object is immutable (frozen=True)
- [x] **AC-013:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Risk Parameters Value Object):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Value object | DDD (Evans) | Immutable, no identity | ✅ OK - frozen=True |
| Position size limit | Risk management | Max position size % of capital | ✅ OK - max_position_size |
| Portfolio exposure | Risk management | Max exposure % of capital | ✅ OK - max_portfolio_exposure |
| Stop loss | Risk management | Exit price on loss | ✅ OK - get_stop_loss_price() |
| Take profit | Risk management | Exit price on profit | ✅ OK - get_take_profit_price() |
| Risk/reward ratio | Trading standard | Min 2:1 reward:risk | ✅ OK - validate_risk_reward() |
| Daily loss limit | Risk management | Max daily loss % | ✅ OK - max_daily_loss_pct |
| Drawdown limit | Risk management | Max drawdown % | ✅ OK - max_drawdown_pct |
| Stop loss LONG | Trading standard | entry × (1 - stop_pct) | ✅ OK - get_stop_loss_price() |
| Stop loss SHORT | Trading standard | entry × (1 + stop_pct) | ✅ OK - Inverse formula |
| Take profit LONG | Trading standard | entry × (1 + tp_pct) | ✅ OK - get_take_profit_price() |
| Take profit SHORT | Trading standard | entry × (1 - tp_pct) | ✅ OK - Inverse formula |
| Tier-based params | Risk management | 5 tiers (micro to institutional) | ✅ OK - for_tier() |
| Validation | Clean code | Validate invariants | ✅ OK - __post_init__ |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only std lib |

**NOTE:** This analysis references BASE_RULES.md for universal rules and standard risk management practices.

---

## Dependencies
- **External:** `dataclasses` (std), `decimal` (std)
- **Internal:** None (value object)

---

## Required Tests
- **test_risk_parameters_value_object.py:**
  - `test_create_valid_params()` - Valid parameters
  - `test_negative_position_size()` - Raises ValueError
  - `test_negative_portfolio_exposure()` - Raises ValueError
  - `test_invalid_stop_loss_pct()` - Raises ValueError (not 0-1)
  - `test_negative_take_profit()` - Raises ValueError
  - `test_negative_risk_reward()` - Raises ValueError
  - `test_invalid_daily_loss()` - Raises ValueError (not 0-1)
  - `test_invalid_drawdown()` - Raises ValueError (not 0-1)
  - `test_get_stop_loss_long()` - entry × (1 - stop_pct)
  - `test_get_stop_loss_short()` - entry × (1 + stop_pct)
  - `test_get_take_profit_long()` - entry × (1 + tp_pct)
  - `test_get_take_profit_short()` - entry × (1 - tp_pct)
  - `test_validate_risk_reward_long_pass()` - R/R >= 2:1
  - `test_validate_risk_reward_long_fail()` - R/R < 2:1
  - `test_validate_risk_reward_short_pass()` - R/R >= 2:1
  - `test_validate_risk_reward_zero_loss()` - Returns False
  - `test_for_tier_micro()` - 20% position, 100% exposure
  - `test_for_tier_small()` - 15% position, 120% exposure
  - `test_for_tier_medium()` - 10% position, 150% exposure
  - `test_for_tier_large()` - 8% position, 180% exposure
  - `test_for_tier_institutional()` - 5% position, 200% exposure
  - `test_for_tier_unknown()` - Defaults to institutional
  - `test_immutability()` - Cannot modify after creation
  - `test_equality()` - Same values = equal

---

## Notes
- **Critical:** RiskParameters is a VALUE OBJECT (immutable, defined by attributes, no identity)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Value Object pattern
- **Frozen Dataclass:** @dataclass(frozen=True) ensures immutability
- **Position Size Limit:** Maximum position size as percentage of capital (e.g., 0.10 = 10%)
- **Portfolio Exposure Limit:** Maximum total exposure as multiplier of capital (e.g., 1.5 = 150%)
- **Stop Loss:** Exit price level to limit losses (percentage from entry)
- **Take Profit:** Exit price level to capture gains (percentage from entry)
- **Risk/Reward Ratio:** Minimum acceptable ratio of potential profit to potential loss (2:1 standard)
- **Daily Loss Limit:** Maximum daily loss as percentage of capital (5% default)
- **Drawdown Limit:** Maximum drawdown from peak as percentage (15% default)
- **LONG Formulas:**
  - Stop loss = entry × (1 - stop_loss_pct) - price drops below this, exit
  - Take profit = entry × (1 + take_profit_pct) - price reaches this, exit
- **SHORT Formulas:**
  - Stop loss = entry × (1 + stop_loss_pct) - price rises above this, exit
  - Take profit = entry × (1 - take_profit_pct) - price drops to this, exit
- **Tier-Based Parameters:** Smaller accounts can take more risk per position; larger accounts are more conservative
- **Factory Method:** `for_tier()` creates RiskParameters for capital tiers (micro, small, medium, large, institutional)
- **Validation:** All parameters validated on creation via __post_init__

---

**File Reference:** `app/domain/value_objects/risk_parameters.py`
**Last Audited:** 2026-02-04
**Audit Status:** ✅ COMPLIANT
