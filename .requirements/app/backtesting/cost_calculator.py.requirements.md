# cost_calculator.py

## Purpose
Advanced cost calculator for backtesting with dynamic spreads, asset-type-specific commissions, market impact, and ADV-based slippage models.

---

## Type Definitions / Data Classes

### AssetType Enum
```python
class AssetType(str, Enum):
    EQUITY = "equity"      # REQUIRED
    CRYPTO = "crypto"      # REQUIRED
    FOREX = "forex"        # REQUIRED
    COMMODITY = "commodity" # REQUIRED
```

### CostCalculatorError Exception
```python
class CostCalculatorError(ValueError):
    """Raised when cost calculation parameters are invalid."""
```

### CostCalculator Class
```python
class CostCalculator:
    use_dynamic_costs: bool  # REQUIRED - Enable dynamic spread/slippage
    SPREAD_RANGES: Dict[AssetType, Tuple[Decimal, Decimal]]  # REQUIRED
    COMMISSION_RATES: Dict[AssetType, Decimal]  # REQUIRED
    SLIPPAGE_RANGES: Dict[AssetType, Tuple[Decimal, Decimal]]  # REQUIRED
```

**Validation Rules:**
- All Decimal inputs validated non-negative (or positive where required)
- Percentages must be 0-1 range (as decimals)
- ADV values > 0 for ADV-based calculations (0 triggers default fallback)

---

## Function Signatures (Contracts)

### `detect_asset_type(symbol: str) -> AssetType`
**Pre:** symbol is non-empty string
**Post:** Returns AssetType based on symbol pattern matching
**Raises:** None (defaults to EQUITY)
**Retry:** No
**Side Effects:** None

### `classify_market_cap(adv_value: Decimal) -> str`
**Pre:** adv_value is non-negative Decimal
**Post:** Returns "large_cap", "mid_cap", or "small_cap"
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_adv_based_slippage_bps(order_value: Decimal, adv_value: Decimal, vix: Optional[Decimal] = None, asset_type: AssetType = AssetType.EQUITY) -> Decimal`
**Pre:** order_value > 0; adv_value >= 0
**Post:** Returns slippage in basis points using ADV formula
**Raises:** CostCalculatorError if order_value <= 0
**Retry:** No
**Side Effects:** Logs slippage; VIX > 30 doubles slippage

### `calculate_spread(asset_type: AssetType, volatility: Optional[Decimal] = None, liquidity: Optional[Decimal] = None) -> Decimal`
**Pre:** asset_type is valid AssetType
**Post:** Returns spread percentage (0.0001-0.0005 range)
**Raises:** None
**Retry:** No
**Side Effects:** Adjusts spread based on volatility/liquidity if dynamic

### `calculate_commission(asset_type: AssetType, trade_value: Decimal) -> Decimal`
**Pre:** trade_value > 0; asset_type is valid
**Post:** Returns commission amount (min $1.00, quantized to 0.01)
**Raises:** CostCalculatorError if trade_value <= 0
**Retry:** No
**Side Effects:** None

### `calculate_total_cost(symbol: str, trade_value: Decimal, is_buy: bool, ...) -> Tuple[Decimal, Decimal]`
**Pre:** trade_value > 0; symbol is non-empty
**Post:** Returns (total_cost, execution_price_adjustment)
**Raises:** CostCalculatorError if inputs invalid
**Retry:** No
**Side Effects:** Logs detailed cost breakdown

### `_validate_positive_decimal(value: Decimal, name: str, allow_zero: bool = False) -> None`
**Pre:** value is Decimal
**Post:** Raises CostCalculatorError if validation fails
**Raises:** CostCalculatorError
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All cost calculations return Decimal quantized to 0.01 (cents)
- [ ] Commission minimum of $1.00 enforced
- [ ] ADV-based slippage uses formula: Base + (Order/ADV)^2 * 100 bps
- [ ] VIX > 30 doubles slippage
- [ ] Asset type detection covers major symbols
- [ ] All validation methods raise CostCalculatorError
- [ ] Zero/negative ADV returns default slippage (doesn't fail)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-006 | 13-trading-specific-rules.md | Include transaction costs | ✅ OK |
| BT-004 | 13-trading-specific-rules.md | Realistic costs | ✅ OK |
| SEC-007 | 28-security-and-secrets.md | Input validation | ✅ OK |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK |
| LOG-003 | 09-logging-observability.md | Appropriate log levels | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK |
| TST-005 | 06-testing.md | Coverage > 80% | ❌ GAP - No test file found |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** Decimal, Enum
- **Internal:** None

---

## Required Tests
- **tests/unit/backtesting/test_cost_calculator.py:**
  - Test asset type detection
  - Test market cap classification
  - Test ADV-based slippage calculation
  - Test VIX multiplier
  - Test spread calculation
  - Test commission calculation with minimum
  - Test market impact calculation
  - Test total cost breakdown
  - Test validation methods

---

## Notes
- **Req #9:** ADV-based slippage formula: Slippage_Bps = Base_Slippage + (Order_Size/ADV)^2 * Impact_Coefficient
- **Market Cap Thresholds:** Large Cap >= $1B daily volume; Small Cap <= $100M
