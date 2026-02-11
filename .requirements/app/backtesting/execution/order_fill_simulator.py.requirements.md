# order_fill_simulator.py

## Purpose
Realistic order fill simulator combining transaction costs, slippage, market impact, partial fills, and order rejection for backtesting execution.

---

## Type Definitions / Data Classes

### FillConstraints Class
```python
@dataclass
class FillConstraints:
    max_participation_rate: Decimal = Decimal("0.10")    # OPTIONAL - Maximum % of ADV (gt 0, lte 1)
    max_slippage_bps: Decimal = Decimal("50")            # OPTIONAL - Maximum slippage (gte 0)
    max_market_impact_bps: Decimal = Decimal("100")      # OPTIONAL - Maximum market impact (gte 0)
    min_fill_pct: Decimal = Decimal("0.0")               # OPTIONAL - Minimum fill percentage (gte 0, lte 1)
    allow_partial_fills: bool = True                     # OPTIONAL - Whether partial fills allowed
```

**Validation Rules:**
- `max_participation_rate` must be between 0 and 1
- All bps fields must be non-negative
- `min_fill_pct` must be between 0 and 1

### SimulatorConfig Class
```python
@dataclass
class SimulatorConfig:
    cost_config: CostConfig = field(default_factory=CostConfig)                          # OPTIONAL
    slippage_config: SlippageConfig = field(default_factory=SlippageConfig)             # OPTIONAL
    impact_config: ImpactConfig = field(default_factory=ImpactConfig)                    # OPTIONAL
    fill_constraints: FillConstraints = field(default_factory=FillConstraints)           # OPTIONAL
    rejection_threshold_adv_pct: Decimal = Decimal("0.25")                               # OPTIONAL - Reject > 25% ADV (gt 0, lte 1)
    liquidity_warning_threshold: Decimal = Decimal("0.15")                                # OPTIONAL - Warn > 15% ADV (gt 0, lte 1)
```

**Validation Rules:**
- All threshold percentages must be between 0 and 1
- rejection_threshold must be > liquidity_warning_threshold

---

## Function Signatures (Contracts)

### `OrderFillSimulator.__init__(cost_calculator: Optional[TransactionCostCalculator] = None, slippage_model: Optional[SlippageModel] = None, impact_model: Optional[MarketImpactModel] = None, config: Optional[SimulatorConfig] = None) -> None`
**Pre:** All optional params are None or valid instances
**Post:** OrderFillSimulator initialized with provided or default components
**Raises:** None
**Retry:** No
**Side Effects:** None

### `OrderFillSimulator.simulate_fill(order: Order, market_snapshot: MarketSnapshot) -> FillResult`
**Pre:** order.validate() passes, market_snapshot has valid data
**Post:** Returns FillResult with execution details or rejection reason
**Raises:** ValueError if order or market data invalid
**Retry:** No
**Side Effects:** None (pure simulation)

### `OrderFillSimulator.simulate_fill_sequence(order: Order, market_snapshots: List[MarketSnapshot]) -> List[FillResult]`
**Pre:** order.validate() passes, market_snapshots is non-empty list
**Post:** Returns list of FillResult objects for each time period
**Raises:** None
**Retry:** No
**Side Effects:** None

### `OrderFillSimulator.estimate_fill_probability(order: Order, market_snapshot: MarketSnapshot) -> float`
**Pre:** order is valid, market_snapshot has valid data
**Post:** Returns fill probability between 0 and 1
**Raises:** None
**Retry:** No
**Side Effects:** None

### `OrderFillSimulator.get_cost_breakdown(order: Order, market_snapshot: MarketSnapshot) -> Dict[str, Decimal]`
**Pre:** order is valid, market_snapshot has valid data
**Post:** Returns dictionary with all cost components
**Raises:** None
**Retry:** No
**Side Effects:** None

### `OrderFillSimulator._create_rejected_result(order: Order, reason: FillReason, message: str) -> FillResult`
**Pre:** order is valid, reason is valid FillReason, message is non-empty string
**Post:** Returns FillResult with filled=False and reason set
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Orders exceeding rejection_threshold_adv_pct are rejected
- [ ] Partial fills respect max_participation_rate
- [ ] Orders violating min_fill_pct are rejected
- [ ] Slippage exceeding max_slippage_bps triggers rejection or partial fill
- [ ] Market impact exceeding max_market_impact_bps triggers rejection or partial fill
- [ ] Market closed orders return MARKET_CLOSED rejection
- [ ] Trading halt orders return MARKET_CLOSED rejection
- [ ] Fill costs are properly scaled for partial fills
- [ ] All async functions are properly marked with async def
- [ ] All type hints are present and accurate

---

## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-05T00:00:00Z |
| **Auditor** | Claude Code (Ralphex Audit v2.0) |
| **GAPs Found** | 1 P0, 0 P1, 1 P2, 0 P3 |
| **Notes** | Missing error logging for order rejections. Otherwise solid implementation. |

## GAP Details

### P0 (Critical) - 1 gap

#### GAP-P0-001: Missing Error Logging for Order Rejections (LOG-004 violation)
**Rule:** LOG-004 from BASE_RULES.md - "Error logging: Log exceptions with stack traces"
**Current State:** Order rejections only logged in warnings list, not in error logs
**Impact:** Production debugging - rejected orders not properly tracked in audit trail
**Location:** Lines 170-182, 229-234, 248-254, 291-295 (all `_create_rejected_result` calls)
**Evidence:**
```python
if not market_snapshot.is_market_open:
    return self._create_rejected_result(
        order,
        FillReason.MARKET_CLOSED,
        "Market is closed",
    )
# No logger.error() call before returning rejected result
```
**Acceptance Criteria:**
- [ ] Add `logger.error()` before each `_create_rejected_result()` call
- [ ] Include order_id, symbol, side, quantity, reason in error logs
- [ ] Add structured logging for audit trail

### P2 (Medium) - 1 gap

#### GAP-P2-001: Missing fee_details in Partial Fill Reconstruction (TRD-006 partial violation)
**Rule:** TRD-006 from BASE_RULES.md - "Transaction costs: Include costs in backtesting"
**Current State:** Partial fill TransactionCost reconstruction missing fee_details
**Impact:** Cost breakdown incomplete for partial fills
**Location:** Lines 300-307
**Evidence:**
```python
transaction_cost = TransactionCost(
    commission=transaction_cost.commission * fill_ratio,
    sec_fee=transaction_cost.sec_fee * fill_ratio,
    finra_taf=transaction_cost.finra_taf * fill_ratio,
    exchange_fee=transaction_cost.exchange_fee * fill_ratio,
    platform_fee=transaction_cost.platform_fee * fill_ratio,
    total_cost=transaction_cost.total_cost * fill_ratio,
)  # Missing: fee_details parameter
```
**Acceptance Criteria:**
- [ ] Add `fee_details=transaction_cost.fee_details` to TransactionCost constructor
- [ ] Scale fee_details values by fill_ratio
- [ ] Add test for partial fill cost breakdown

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule ID | Source | Requirement | Current Status | Gap ID |
|---------|--------|-------------|----------------|---------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK | |
| ASYNC-001 | BASE_RULES | Use async def | ✅ FIXED - Removed unnecessary async | |
| ASYNC-002 | BASE_RULES | Await async calls | ✅ FIXED - No async calls needed | |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError for invalid inputs | |
| EXE-001 | BASE_RULES | Order validation | ✅ OK - Calls order.validate() | |
| EXE-002 | BASE_RULES | Execution timing | ⚠️ NOT APPLIED - Simulation only | |
| LOG-004 | BASE_RULES | Error logging | ❌ GAP | GAP-P0-001 |
| DP-004 | BASE_RULES | Dependency injection | ✅ OK - All models injected via constructor | |
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ FIXED - Config dataclasses frozen=True |
| TRD-006 | BASE_RULES | Transaction costs | ⚠️ PARTIAL | GAP-P2-001 |

---

## Dependencies
- **External:** logging, decimal, datetime, enum
- **Internal:**
  - .market_impact.MarketImpact, MarketImpactModel, ImpactConfig
  - .models.Order, FillResult, MarketSnapshot, OrderSide, OrderStatus, OrderType, TimeOfDay, FillReason
  - .slippage_model.SlippageConfig, SlippageEstimate, SlippageModel
  - .transaction_cost.CostConfig, TransactionCost, TransactionCostCalculator

---

## Required Tests
- **tests/unit/backtesting/execution/test_order_fill_simulator.py:**
  - Test full fill scenario
  - Test partial fill due to participation rate limit
  - Test rejection due to exceeding ADV threshold
  - Test rejection due to market closed
  - Test rejection due to trading halt
  - Test rejection due to slippage exceeding maximum
  - Test rejection due to market impact exceeding maximum
  - Test rejection due to minimum fill requirement not met
  - Test cost breakdown calculation
  - Test fill probability estimation
  - Test fill sequence across multiple time periods
  - Test warning generation for large orders
  - Test proper scaling of costs for partial fills
  - Test error logging for all rejection scenarios

---

## Notes
- Simulator combines three execution cost models: transaction costs, slippage, and market impact
- Implements realistic order rejection based on liquidity constraints
- Supports partial fills with proper cost scaling
- Proper dependency injection via constructor
- **CRITICAL:** GAP-P0-001 must be fixed for production audit trail
