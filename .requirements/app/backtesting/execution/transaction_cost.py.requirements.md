# transaction_cost.py

## Purpose
Realistic US equity transaction cost calculation including per-share commission, SEC fees, FINRA TAF, exchange fees, and tiered commission structures.

---

## Type Definitions / Data Classes

### FeeType Enum
```python
class FeeType(str, Enum):
    SEC_FEE = "sec_fee"              # REQUIRED - SEC Section 31 fee on sells
    FINRA_TAF = "finra_taf"          # REQUIRED - FINRA Trading Activity Fee
    EXCHANGE_FEE = "exchange_fee"    # REQUIRED - Exchange fees (NYSE/NASDAQ)
    PLATFORM_FEE = "platform_fee"    # REQUIRED - Platform/broker fees
```

**Validation Rules:**
- Used for identifying fee types in configuration
- Must match keys in US_EQUITY_FEES dict

### CommissionType Enum
```python
class CommissionType(str, Enum):
    FIXED_PER_SHARE = "fixed_per_share"    # REQUIRED - Fixed amount per share
    TIERED = "tiered"                      # REQUIRED - Tiered based on volume
    PERCENTAGE = "percentage"              # REQUIRED - Percentage of trade value
    HYBRID = "hybrid"                      # REQUIRED - Combination with minimum
```

**Validation Rules:**
- Determines commission calculation method
- Must be valid CommissionType value

### FeeConfig Class
```python
@dataclass
class FeeConfig:
    fee_type: FeeType                              # REQUIRED - Type of fee
    rate: Decimal                                  # REQUIRED - Fee rate (gte 0)
    min_fee: Optional[Decimal] = None              # OPTIONAL - Minimum fee (gte 0 if set)
    max_fee: Optional[Decimal] = None              # OPTIONAL - Maximum fee (gte 0 if set)
    applies_to_buy: bool = False                   # OPTIONAL - Whether fee applies to buy orders
    applies_to_sell: bool = True                   # OPTIONAL - Whether fee applies to sell orders
    description: str = ""                          # OPTIONAL - Human-readable description
```

**Validation Rules:**
- `rate` must be non-negative
- `min_fee` and `max_fee` (if set) must be non-negative
- At least one of `applies_to_buy` or `applies_to_sell` must be True

### CommissionTier Class
```python
@dataclass
class CommissionTier:
    min_shares: int                    # REQUIRED - Minimum shares for this tier (gt 0)
    max_shares: Optional[int]          # OPTIONAL - Maximum shares for this tier (gte min_shares if set)
    rate: Decimal                      # REQUIRED - Commission rate per share (gt 0)
    min_commission: Decimal            # REQUIRED - Minimum commission for this tier (gte 0)
```

**Validation Rules:**
- `min_shares` must be positive
- `max_shares` (if set) must be >= `min_shares`
- `rate` must be positive
- `min_commission` must be non-negative

### TransactionCost Class
```python
@dataclass
class TransactionCost:
    commission: Decimal                      # REQUIRED - Broker commission (gte 0)
    sec_fee: Decimal                         # REQUIRED - SEC fee (gte 0)
    finra_taf: Decimal                       # REQUIRED - FINRA Trading Activity Fee (gte 0)
    exchange_fee: Decimal                    # REQUIRED - Exchange fees (gte 0)
    platform_fee: Decimal                    # REQUIRED - Platform/broker fees (gte 0)
    total_cost: Decimal                      # REQUIRED - Sum of all costs (gte 0)
    fee_details: Dict[str, Decimal]          # OPTIONAL - Detailed breakdown (default empty)
```

**Validation Rules:**
- All cost fields must be non-negative
- `total_cost` must equal sum of all individual costs
- `fee_details` provides transparency into cost breakdown

### CostConfig Class
```python
@dataclass
class CostConfig:
    commission_per_share: Decimal = Decimal("0.005")                # OPTIONAL - Per-share rate (gte 0)
    min_commission: Decimal = Decimal("1.0")                        # OPTIONAL - Minimum per trade (gte 0)
    max_commission: Optional[Decimal] = None                        # OPTIONAL - Maximum per trade (gte 0 if set)
    commission_type: CommissionType = CommissionType.FIXED_PER_SHARE # OPTIONAL - Commission structure
    commission_tiers: List[CommissionTier]                          # OPTIONAL - Tiers for tiered commission
    use_sec_fee: bool = True                                        # OPTIONAL - Apply SEC fee
    use_finra_taf: bool = True                                     # OPTIONAL - Apply FINRA TAF
    use_exchange_fees: bool = True                                  # OPTIONAL - Apply exchange fees
    custom_fees: Dict[str, FeeConfig]                               # OPTIONAL - Custom fee configurations
```

**Validation Rules:**
- `commission_per_share` must be non-negative
- `min_commission` and `max_commission` (if set) must be non-negative
- `commission_tiers` must be valid if `commission_type` is TIERED

---

## Function Signatures (Contracts)

### `TransactionCostCalculator.__init__(config: Optional[CostConfig] = None) -> None`
**Pre:** config is None or valid CostConfig
**Post:** Calculator initialized with config or defaults
**Raises:** None
**Retry:** No
**Side Effects:** Initializes fee lookup dict

### `TransactionCostCalculator.calculate_commission(shares: int, price: Decimal) -> Decimal`
**Pre:** shares > 0, price > 0
**Post:** Returns commission amount (gte min_commission, lte max_commission if set)
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator._calculate_tiered_commission(shares: int) -> Decimal`
**Pre:** shares > 0, commission_tiers is non-empty list
**Post:** Returns commission based on tiered structure
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator.calculate_sec_fee(shares: int, price: Decimal) -> Decimal`
**Pre:** shares > 0, price > 0
**Post:** Returns SEC fee (0.01 to 5.95) or 0
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator.calculate_finra_taf(shares: int) -> Decimal`
**Pre:** shares > 0
**Post:** Returns FINRA TAF amount (gte 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator.calculate_exchange_fee(shares: int, exchange: Optional[str] = None) -> Decimal`
**Pre:** shares > 0, exchange is None or valid exchange code
**Post:** Returns exchange fee amount (gte 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator.calculate_platform_fee(shares: int, price: Decimal) -> Decimal`
**Pre:** shares > 0, price > 0
**Post:** Returns platform fee amount (gte 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator.calculate_cost(symbol: str, side: str, shares: int, price: Decimal, exchange: Optional[str] = None) -> TransactionCost`
**Pre:** shares > 0, price > 0, side in ['buy', 'sell']
**Post:** Returns TransactionCost with complete breakdown
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator.estimate_cost_range(symbol: str, side: str, shares: int, price_min: Decimal, price_max: Decimal) -> Tuple[TransactionCost, TransactionCost]`
**Pre:** shares > 0, price_min > 0, price_max > 0, price_min <= price_max
**Post:** Returns (min_cost, max_cost) tuple
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator.get_cost_as_bps(cost: TransactionCost, trade_value: Decimal) -> Decimal`
**Pre:** cost is valid, trade_value > 0
**Post:** Returns cost in basis points (gte 0)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `TransactionCostCalculator.get_effective_cost(symbol: str, side: str, shares: int, price: Decimal, exchange: Optional[str] = None) -> Decimal`
**Pre:** shares > 0, price > 0, side in ['buy', 'sell']
**Post:** Returns effective cost per share (gte 0)
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All commission calculations respect min_commission
- [ ] All commission calculations respect max_commission if set
- [ ] SEC fee is only applied to sell orders
- [ ] SEC fee is capped at $5.95 per transaction
- [ ] SEC fee minimum is $0.01
- [ ] FINRA TAF is applied to both buy and sell orders
- [ ] Exchange fees use correct rate for exchange code
- [ ] Platform fees respect min/max from config
- [ ] Tiered commission correctly applies tier rates
- [ ] Total cost equals sum of all components
- [ ] All type hints are present and accurate
- [ ] All Decimal operations use proper quantization

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError for invalid inputs |
| TRD-006 | BASE_RULES | Transaction costs in backtesting | ✅ OK - Complete fee structure |
| LOG-004 | BASE_RULES | Error logging | ⚠️ NOT APPLIED - No logging on errors |
| ARCH-006 | BASE_RULES | Value objects immutable | ❌ GAP - dataclass not frozen |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - field_default_factory used |

---

## Dependencies
- **External:** logging, decimal, enum
- **Internal:** None

---

## Required Tests
- **tests/unit/backtesting/execution/test_transaction_cost.py:**
  - Test fixed per-share commission calculation
  - Test percentage commission calculation
  - Test tiered commission calculation
  - Test hybrid commission with minimum
  - Test SEC fee calculation for sell orders
  - Test SEC fee returns 0 for buy orders
  - Test SEC fee cap at $5.95
  - Test SEC fee minimum at $0.01
  - Test FINRA TAF calculation
  - Test exchange fee calculation for NYSE
  - Test exchange fee calculation for NASDAQ
  - Test platform fee with min/max
  - Test complete cost calculation for buy order
  - Test complete cost calculation for sell order
  - Test cost range estimation
  - Test cost as basis points calculation
  - Test effective cost per share calculation
  - Test error handling for invalid inputs (negative shares, zero price, invalid side)

---

## Notes
- US Equity regulatory fees as of 2024:
  - SEC Section 31 fee: $0.0000078 per dollar sold (capped at $5.95)
  - FINRA TAF: $0.000145 per share traded
  - Exchange fees: ~$0.003 per share (varies by exchange)
- Commission structure supports multiple types: fixed per-share, percentage, tiered, hybrid
- All costs properly quantized to 2 decimal places (cents)
