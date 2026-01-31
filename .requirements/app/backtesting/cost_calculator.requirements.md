# cost_calculator.py

## Purpose
Advanced Cost Calculator for Backtesting - Calculates realistic trading costs including dynamic spreads (0.01-0.03% for stocks), commission by asset type (0.01-0.05%), market impact and slippage (0.02-0.1%), and ADV-based slippage model (Req #9).

---

## Type Definitions / Data Classes

### AssetType (str, Enum)
```python
class AssetType(str, Enum):
    EQUITY = "equity"        # Stocks/ETFs
    CRYPTO = "crypto"        # Cryptocurrencies
    FOREX = "forex"          # Currency pairs
    COMMODITY = "commodity"  # Commodities/futures
```

### CostCalculatorError(ValueError)
```python
class CostCalculatorError(ValueError):
    """Raised when cost calculation parameters are invalid."""
```

### CostCalculator
```python
class CostCalculator:
    """
    Advanced cost calculator for backtesting (TASK-CST-1, CST-2, Req #9).

    Provides realistic cost modeling with:
    - Dynamic spreads (0.01-0.03% for stocks)
    - Asset-type-specific commissions (0.01-0.05%)
    - Market impact and slippage (0.02-0.1%)
    - Total cost per trade calculation
    - ADV-based slippage model (Req #9): Slippage = Base + (Order_Size/ADV)^2 * Coef
    - Volatility multiplier (Req #9): VIX > 30 = slippage x2
    """
```

**Class Constants:**

| Constant | Value | Description |
|----------|-------|-------------|
| SPREAD_RANGES | Dict by AssetType | Min/max spreads (0.01-0.03% for equity) |
| COMMISSION_RATES | Dict by AssetType | Commission rates (0.01% for equity) |
| SLIPPAGE_RANGES | Dict by AssetType | Min/max slippage (0.02-0.1% for equity) |
| LARGE_CAP_BASE_SLIPPAGE_BPS | 3.5 | 2-5 bps average for large caps |
| SMALL_CAP_BASE_SLIPPAGE_BPS | 17.5 | 10-25 bps average for small caps |
| IMPACT_COEFFICIENT | 100 | Multiplier for ADV impact |
| VIX_HIGH_VOLATILITY_THRESHOLD | 30 | VIX > 30 triggers high vol |
| VOLATILITY_MULTIPLIER_HIGH | 2 | 2x slippage in high vol |
| LARGE_CAP_MIN_VOLUME | $1B | Minimum daily volume for large cap |
| SMALL_CAP_MAX_VOLUME | $100M | Maximum daily volume for small cap |

---

## Function Signatures (Contracts)

### `CostCalculator.__init__(use_dynamic_costs: bool = True) -> None`
**Pre:** None
**Post:** Calculator initialized
**Raises:** None
**Retry:** No
**Side Effects:** Stores use_dynamic_costs flag

### `CostCalculator._validate_positive_decimal(value: Decimal, name: str, allow_zero: bool = False) -> None`
**Pre:** value is Decimal
**Post:** Raises CostCalculatorError if invalid
**Raises:** CostCalculatorError if value < 0 (or <= 0 if not allow_zero)
**Retry:** No
**Side Effects:** None (pure validation)

### `CostCalculator._validate_percentage(value: Optional[Decimal], name: str, max_value: Decimal = Decimal("1")) -> None`
**Pre:** value is Decimal or None
**Post:** Raises CostCalculatorError if invalid
**Raises:** CostCalculatorError if value < 0 or > max_value
**Retry:** No
**Side Effects:** None (pure validation)

### `CostCalculator.detect_asset_type(symbol: str) -> AssetType`
**Pre:** symbol is non-empty string
**Post:** Returns detected AssetType
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Detection Rules:**
- **Crypto:** Contains BTC, ETH, USDT, USDC, BNB, ADA, DOGE, XRP
- **Forex:** Contains USD, EUR, GBP, JPY, CHF, AUD, CAD, NZD (max 6 chars)
- **Commodity:** Contains GLD, SLV, OIL, CL, GC, SI, NG
- **Default:** EQUITY

### `CostCalculator.classify_market_cap(adv_value: Decimal) -> str`
**Pre:** adv_value >= 0
**Post:** Returns "large_cap", "small_cap", or "mid_cap"
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Classification:**
- **large_cap:** adv_value >= $1B daily volume
- **small_cap:** adv_value <= $100M daily volume
- **mid_cap:** Between small and large

### `CostCalculator.calculate_adv_based_slippage_bps(
    order_value: Decimal,
    adv_value: Decimal,
    vix: Optional[Decimal] = None,
    asset_type: AssetType = AssetType.EQUITY,
) -> Decimal`
**Pre:** order_value > 0; adv_value >= 0
**Post:** Returns slippage in basis points
**Raises:** CostCalculatorError if order_value <= 0
**Retry:** No
**Side Effects:** None (pure computation)

**Formula (Req #9):** `Slippage_Bps = Base_Slippage + (Order_Size / ADV)^2 × Impact_Coefficient`

**Base Slippage by Market Cap:**
- large_cap: 3.5 bps (2-5 bps average)
- small_cap: 17.5 bps (10-25 bps average)
- mid_cap: 10.5 bps (interpolated)

**Volatility Multiplier (Req #9):** If VIX > 30, slippage × 2

### `CostCalculator.calculate_adv_based_slippage(
    asset_type: AssetType,
    trade_value: Decimal,
    adv_value: Decimal,
    order_size_pct: Optional[Decimal] = None,
    volatility: Optional[Decimal] = None,
    vix: Optional[Decimal] = None,
) -> Decimal`
**Pre:** trade_value > 0; adv_value >= 0
**Post:** Returns slippage amount in dollars
**Raises:** CostCalculatorError if invalid
**Retry:** No
**Side Effects:** None (pure computation)

**Process:** Calculate BPS using ADV model, convert to dollar amount

### `CostCalculator.calculate_spread(
    asset_type: AssetType,
    volatility: Optional[Decimal] = None,
    liquidity: Optional[Decimal] = None,
) -> Decimal`
**Pre:** asset_type is valid AssetType
**Post:** Returns spread as percentage (e.g., 0.0002 for 0.02%)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Spread Ranges by Asset Type:**
- EQUITY: 0.01-0.03%
- CRYPTO: 0.05-0.2%
- FOREX: 0.01-0.05%
- COMMODITY: 0.02-0.05%

**Dynamic Adjustments:**
- Higher volatility → wider spread (up to 3x)
- Low liquidity (< $1M) → 1.5x spread

### `CostCalculator.calculate_commission(asset_type: AssetType, trade_value: Decimal) -> Decimal`
**Pre:** asset_type valid; trade_value > 0
**Post:** Returns commission amount (minimum $1)
**Raises:** CostCalculatorError if trade_value <= 0
**Retry:** No
**Side Effects:** None (pure computation)

**Commission Rates by Asset Type:**
- EQUITY: 0.01% (typical online broker)
- CRYPTO: 0.1%
- FOREX: 0.02%
- COMMODITY: 0.02%

**Minimum:** $1 per trade

### `CostCalculator.calculate_slippage(
    asset_type: AssetType,
    trade_value: Decimal,
    order_size_pct: Optional[Decimal] = None,
    volatility: Optional[Decimal] = None,
) -> Decimal`
**Pre:** asset_type valid; trade_value > 0; order_size_pct in [0, 1]
**Post:** Returns slippage amount in dollars
**Raises:** CostCalculatorError if invalid
**Retry:** No
**Side Effects:** None (pure computation)

**Slippage Ranges by Asset Type:**
- EQUITY: 0.02-0.1%
- CRYPTO: 0.05-0.2%
- FOREX: 0.01-0.03%
- COMMODITY: 0.03-0.1%

**Dynamic Adjustments:**
- Larger orders → more slippage (up to 6x)
- Higher volatility → more slippage (up to 3x)

### `CostCalculator.calculate_market_impact(
    trade_value: Decimal,
    order_size_pct: Optional[Decimal] = None,
) -> Decimal`
**Pre:** trade_value > 0; order_size_pct in [0, 1]
**Post:** Returns market impact amount
**Raises:** CostCalculatorError if invalid
**Retry:** No
**Side Effects:** None (pure computation)

**Base:** 0.01% (MARKET_IMPACT_BASE)
**Multiplier:** `1 + (order_size_pct × 3)` (up to 4x)

### `CostCalculator.calculate_total_cost(
    symbol: str,
    trade_value: Decimal,
    is_buy: bool,
    volatility: Optional[Decimal] = None,
    liquidity: Optional[Decimal] = None,
    order_size_pct: Optional[Decimal] = None,
) -> Tuple[Decimal, Decimal]`
**Pre:** symbol non-empty; trade_value > 0
**Post:** Returns (total_cost, execution_price_adjustment)
**Raises:** CostCalculatorError if invalid
**Retry:** No
**Side Effects:** None (pure computation)

**Total Cost Components:**
1. Commission (fixed percentage)
2. Slippage (dynamic based on conditions)
3. Market impact (size-dependent)

**Execution Price Adjustment:**
- **Buy:** +spread (pay ask price)
- **Sell:** -spread (receive bid price)

**Total Cost Range (TASK-CST-2):** 0.02-0.1% additional

### `CostCalculator.apply_execution_costs(
    base_price: Decimal,
    symbol: str,
    is_buy: bool,
    volatility: Optional[Decimal] = None,
    liquidity: Optional[Decimal] = None,
) -> Decimal`
**Pre:** base_price > 0; symbol non-empty
**Post:** Returns adjusted execution price
**Raises:** CostCalculatorError if base_price <= 0
**Retry:** No
**Side Effects:** None (pure computation)

**Adjustment:**
- **Buy:** `base_price × (1 + spread)`
- **Sell:** `base_price × (1 - spread)`

---

## Acceptance Criteria
- [ ] **AC-001:** AssetType has EQUITY, CRYPTO, FOREX, COMMODITY values
- [ ] **AC-002:** detect_asset_type() correctly identifies crypto symbols
- [ ] **AC-003:** detect_asset_type() correctly identifies forex pairs
- [ ] **AC-004:** classify_market_cap() returns large_cap for >= $1B
- [ ] **AC-005:** classify_market_cap() returns small_cap for <= $100M
- [ ] **AC-006:** calculate_adv_based_slippage_bps() implements Req #9 formula
- [ ] **AC-007:** Large cap base slippage is 2-5 bps (3.5 average)
- [ ] **AC-008:** Small cap base slippage is 10-25 bps (17.5 average)
- [ ] **AC-009:** VIX > 30 doubles slippage (volatility multiplier)
- [ ] **AC-010:** calculate_spread() returns 0.01-0.03% for equity
- [ ] **AC-011:** calculate_commission() returns 0.01% for equity
- [ ] **AC-012:** calculate_slippage() returns 0.02-0.1% for equity
- [ ] **AC-013:** calculate_total_cost() returns 0.02-0.1% additional cost
- [ ] **AC-014:** apply_execution_costs() adjusts price for spread
- [ ] **AC-015:** Validation raises CostCalculatorError for invalid inputs
- [ ] **AC-016:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Cost Calculator):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Dynamic spreads | Backtesting standard | 0.01-0.03% for stocks | ✅ OK - SPREAD_RANGES |
| Commission by asset | Backtesting standard | 0.01-0.1% | ✅ OK - COMMISSION_RATES |
| Slippage modeling | Backtesting standard | 0.02-0.1% | ✅ OK - SLIPPAGE_RANGES |
| Market impact | Almgren-Chriss | Size-dependent | ✅ OK - calculate_market_impact() |
| ADV-based slippage | Req #9 | Base + (Size/ADV)^2 × Coef | ✅ OK - calculate_adv_based_slippage_bps() |
| Large cap slippage | Req #9 | 2-5 bps | ✅ OK - LARGE_CAP_BASE_SLIPPAGE_BPS |
| Small cap slippage | Req #9 | 10-25 bps | ✅ OK - SMALL_CAP_BASE_SLIPPAGE_BPS |
| Volatility multiplier | Req #9 | VIX > 30 = 2x | ✅ OK - VOLATILITY_MULTIPLIER_HIGH |
| Asset type detection | Clean code | Symbol parsing | ✅ OK - detect_asset_type() |
| Validation | Clean code | Input validation | ✅ OK - _validate_*() |
| Custom exception | Clean code | CostCalculatorError | ✅ OK - Exception class |
| Decimal precision | BASE_RULES.md (TYP-002) | Decimal for money | ✅ OK - Decimal types |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Almgren-Chriss (2004) for market impact modeling.

---

## Dependencies
- **External:** `decimal` (std), `enum` (std), `logging` (std), `typing` (std)
- **Internal:** None (infrastructure layer)

---

## Required Tests
- **test_cost_calculator.py:**
  - `test_init_with_dynamic_costs()` - Stores flag
  - `test_validate_positive_decimal_valid()` - Passes validation
  - `test_validate_positive_decimal_negative()` - Raises CostCalculatorError
  - `test_validate_positive_decimal_zero()` - Raises if not allow_zero
  - `test_validate_percentage()` - Validates 0-1 range
  - `test_detect_asset_type_equity()` - Returns EQUITY for stocks
  - `test_detect_asset_type_crypto()` - Returns CRYPTO for BTC/ETH
  - `test_detect_asset_type_forex()` - Returns FOREX for USD/EUR
  - `test_detect_asset_type_commodity()` - Returns COMMODITY for GLD/OIL
  - `test_classify_market_cap_large()` - Returns large_cap for >= $1B
  - `test_classify_market_cap_small()` - Returns small_cap for <= $100M
  - `test_classify_market_cap_mid()` - Returns mid_cap between
  - `test_calculate_adv_based_slippage_bps_large_cap()` - 3.5 bps base
  - `test_calculate_adv_based_slippage_bps_small_cap()` - 17.5 bps base
  - `test_calculate_adv_based_slippage_bps_mid_cap()` - 10.5 bps base
  - `test_calculate_adv_based_slippage_bps_impact()` - ADV impact applies
  - `test_calculate_adv_based_slippage_bps_vix_high()` - Doubles when VIX > 30
  - `test_calculate_adv_based_slippage_bps_zero_adv()` - Uses default
  - `test_calculate_spread_equity()` - Returns 0.01-0.03%
  - `test_calculate_spread_volatility()` - Increases with vol
  - `test_calculate_spread_liquidity()` - Wider for low liquidity
  - `test_calculate_commission_equity()` - Returns 0.01%
  - `test_calculate_commission_minimum()` - Returns $1 minimum
  - `test_calculate_slippage_equity()` - Returns 0.02-0.1%
  - `test_calculate_slippage_dynamic()` - Adjusts for size/vol
  - `test_calculate_market_impact()` - Increases with order size
  - `test_calculate_total_cost()` - Returns sum of all costs
  - `test_calculate_total_cost_range()` - 0.02-0.1% of trade value
  - `test_apply_execution_costs_buy()` - Increases price by spread
  - `test_apply_execution_costs_sell()` - Decreases price by spread

---

## Notes
- **Critical:** Realistic cost modeling is essential for accurate backtesting
- **Almgren-Chriss Reference:** "Optimal Execution of Portfolio Transactions" (2004) - Market impact modeling
- **Spread Ranges:** Dynamic bid-ask spreads by asset type
  - EQUITY: 0.01-0.03% (1-3 bps)
  - CRYPTO: 0.05-0.2% (wider due to fragmentation)
  - FOREX: 0.01-0.05% (tight spreads in major pairs)
  - COMMODITY: 0.02-0.05%
- **Commission Rates:** Per-trade costs
  - EQUITY: 0.01% ($1 per $10K trade)
  - CRYPTO: 0.1% (higher due to exchange fees)
  - FOREX: 0.02% (spread-based pricing)
  - COMMODITY: 0.02% (futures commission)
- **Slippage Ranges:** Price movement during order execution
  - EQUITY: 0.02-0.1% (2-10 bps)
  - CRYPTO: 0.05-0.2% (high volatility)
  - FOREX: 0.01-0.03% (liquid market)
  - COMMODITY: 0.03-0.1%
- **ADV-Based Slippage Model (Req #9):**
  - Formula: `Slippage_Bps = Base_Slippage + (Order_Size / ADV)^2 × Impact_Coefficient`
  - Large Cap: 2-5 bps base (3.5 average)
  - Small Cap: 10-25 bps base (17.5 average)
  - Impact Coefficient: 100
  - VIX > 30: 2x slippage multiplier
- **Market Impact:** Price impact from order size
  - Base: 0.01%
  - Multiplier: 1 + (order_size_pct × 3)
  - Large orders move the market
- **Total Cost Range:** 0.02-0.1% additional cost per trade
  - Commission: Fixed percentage
  - Slippage: Dynamic based on conditions
  - Market Impact: Size-dependent
- **Execution Price Adjustment:**
  - Buy: Pay ask (higher price)
  - Sell: Receive bid (lower price)
  - Always worse for trader (realistic)
- **Production Rule:** Always use realistic costs in production backtesting

---

**File Reference:** `app/backtesting/cost_calculator.py`
**Last Audited:** 2026-02-01
