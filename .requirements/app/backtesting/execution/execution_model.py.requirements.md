# execution_model.py

## Purpose
Comprehensive execution model that coordinates transaction costs, slippage, market impact (Almgren-Chriss), order fill simulation, and partial fills for realistic backtesting.

---

## Type Definitions / Data Classes

### ExecutionConfig DataClass
```python
@dataclass
class ExecutionConfig:
    cost_config: CostConfig                          # REQUIRED - Transaction cost configuration
    slippage_config: SlippageConfig                  # REQUIRED - Slippage model configuration
    impact_config: ImpactConfig                      # REQUIRED - Market impact configuration
    max_participation_rate: Decimal = Decimal("0.10") # REQUIRED - Max % of ADV (default 10%)
    allow_partial_fills: bool = True                 # REQUIRED - Allow partial fills
    min_fill_pct: Decimal = Decimal("0.0")           # REQUIRED - Min fill percentage
    enable_logging: bool = True                      # REQUIRED - Enable execution logging
```

**Validation Rules:**
- `max_participation_rate` must be between 0 and 1 (represents percentage)
- `min_fill_pct` must be between 0 and 100
- All cost/slippage/impact configs must be valid

### RealisticExecutionModel Class
```python
class RealisticExecutionModel:
    config: ExecutionConfig                          # REQUIRED - Execution configuration
    cost_calculator: TransactionCostCalculator       # REQUIRED - Computes transaction costs
    slippage_model: SlippageModel                    # REQUIRED - Estimates slippage
    impact_model: MarketImpactModel                  # REQUIRED - Calculates market impact
    fill_simulator: OrderFillSimulator               # REQUIRED - Simulates order fills
    summary: ExecutionSummary                        # REQUIRED - Tracks execution statistics
```

**Validation Rules:**
- All calculator/model/simulator components must be initialized
- `config` must be valid or default ExecutionConfig used

---

## Function Signatures (Contracts)

### `ExecutionConfig.to_simulator_config() -> SimulatorConfig`
**Pre:** ExecutionConfig is properly initialized
**Post:** Returns SimulatorConfig with FillConstraints created from instance fields
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure conversion)

### `RealisticExecutionModel.__init__(config: Optional[ExecutionConfig] = None) -> None`
**Pre:** config is None or valid ExecutionConfig
**Post:** Instance initialized with all components and default config if not provided
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Initializes calculator, models, simulator, and summary

### `async execute_order(order: Order, market_snapshot: MarketSnapshot) -> ExecutionResult`
**Pre:** order is valid Order, market_snapshot has current market data
**Post:** Returns ExecutionResult with fill details, costs, and status
**Raises:** ValueError if order parameters invalid
**Retry:** ❌ No
**Side Effects:** Updates summary, logs execution if enabled

**ExecutionResult Fields:**
- order: Order executed
- fills: List[FillResult] (empty if rejected)
- total_filled_shares: int (0 if rejected)
- avg_fill_price: Decimal (0 if rejected)
- total_commission: Decimal
- total_slippage_bps: Decimal
- total_market_impact_bps: Decimal
- total_cost: Decimal
- first_fill_time: datetime | None
- last_fill_time: datetime | None
- is_fully_filled: bool
- is_partial_fill: bool
- is_rejected: bool
- cost_breakdown: CostBreakdown
- execution_summary: str
- warnings: List[str]

### `async execute_orders_batch(orders: List[Order], market_snapshots: Dict[str, MarketSnapshot]) -> List[ExecutionResult]`
**Pre:** orders is non-empty, market_snapshots contains data for all order symbols
**Post:** Returns list of ExecutionResult for each order (skips orders without market data)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs warning for symbols without market data, executes each order

### `get_execution_summary() -> ExecutionSummary`
**Pre:** None
**Post:** Returns current ExecutionSummary with aggregated statistics
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `reset_summary() -> None`
**Pre:** None
**Post:** summary is reset to new empty ExecutionSummary
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Resets summary state

### `estimate_execution_cost(symbol: str, side: str, shares: int, price: Decimal, adv: Decimal, volatility: Optional[Decimal] = None) -> Dict[str, Decimal]`
**Pre:** symbol is non-empty, side in ["buy", "sell"], shares > 0, price > 0, adv > 0, volatility >= 0
**Post:** Returns dict with estimated costs without full simulation
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (estimation only)

**Cost Dictionary Keys:**
- commission: Decimal
- regulatory_fees: Decimal
- slippage_cost: Decimal
- market_impact_cost: Decimal
- total_cost: Decimal
- total_cost_bps: Decimal
- estimated_fill_price: Decimal

### `validate_order_feasibility(order: Order, market_snapshot: MarketSnapshot) -> Tuple[bool, List[str]]`
**Pre:** order is valid Order, market_snapshot has current market data
**Post:** Returns (is_feasible, list_of_warnings)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (validation only)

**Feasibility Checks:**
- Market is open (is_market_open)
- No trading halt (is_trading_halt)
- Participation rate within limits
- Fill probability estimation (> 0 for feasible)

---

## Acceptance Criteria
- [ ] All functions have complete type hints (TYP-001)
- [ ] ExecutionConfig has all required fields with proper defaults
- [ ] ExecutionConfig.to_simulator_config() creates valid SimulatorConfig
- [ ] RealisticExecutionModel initializes all components correctly
- [ ] execute_order() returns valid ExecutionResult for filled orders
- [ ] execute_order() returns ExecutionResult with is_rejected=True for rejected orders
- [ ] execute_order() returns ExecutionResult with is_partial_fill=True for partial fills
- [ ] execute_order() calculates cost_breakdown correctly for partial fills
- [ ] execute_order() updates summary after each execution
- [ ] execute_order() logs when enable_logging=True
- [ ] execute_orders_batch() executes all orders with valid market data
- [ ] execute_orders_batch() skips and logs warning for orders without market data
- [ ] get_execution_summary() returns aggregated statistics
- [ ] reset_summary() creates new empty summary
- [ ] estimate_execution_cost() returns all required cost fields
- [ ] estimate_execution_cost() uses simplified spread assumption (2 bps)
- [ ] validate_order_feasibility() returns False when market closed
- [ ] validate_order_feasibility() returns False when trading halt
- [ ] validate_order_feasibility() warns on high participation rate
- [ ] validate_order_feasibility() warns on low fill probability
- [ ] All async methods properly use await
- [ ] Decimal precision maintained throughout calculations

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-001 | 01-formatting-style.md | Line length ≤ 100 | ✅ OK |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK |
| TYP-002 | 02-type-hints.md | Modern syntax (X \| None) | ✅ OK |
| ASYNC-001 | 07-async-patterns.md | Use async def | ✅ OK - execute_order, execute_orders_batch |
| ASYNC-002 | 07-async-patterns.md | Await async calls | ✅ OK - Awaits fill_simulator.simulate_fill |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Coordinates execution components |
| SOL-005 | 03-solid-principles.md | Dependency Injection | ✅ OK - Components injected via config |
| ARCH-001 | 05-architecture.md | Layered architecture | ✅ OK - Infrastructure layer |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK - Raises ValueError for invalid orders |
| LOG-003 | 09-logging-observability.md | Appropriate levels | ✅ OK - info for normal, warning for skipped |
| LOG-005 | 09-logging-observability.md | No sensitive data | ✅ OK |
| EXE-001 | BASE_RULES.md | Order validation | ✅ OK - validate_order_feasibility |
| EXE-002 | BASE_RULES.md | Execution timing | ✅ OK - Async execution |
| EXE-003 | BASE_RULES.md | Market impact | ✅ OK - Almgren-Chriss model |
| BT-004 | BASE_RULES.md | Realistic costs | ✅ OK - Transaction costs, slippage, impact |

---

## Dependencies
- **External:** `logging`, `dataclasses`, `datetime`, `decimal`, `typing`
- **Internal:**
  - `app.backtesting.execution.market_impact.ImpactConfig, MarketImpactModel`
  - `app.backtesting.execution.models.*` (CostBreakdown, ExecutionResult, ExecutionSummary, FillResult, MarketSnapshot, Order, OrderSide, OrderType)
  - `app.backtesting.execution.order_fill_simulator.FillConstraints, OrderFillSimulator, SimulatorConfig`
  - `app.backtesting.execution.slippage_model.SlippageConfig, SlippageModel`
  - `app.backtesting.execution.transaction_cost.CostConfig, TransactionCostCalculator`

---

## Required Tests
- **tests/unit/backtesting/execution/test_execution_model.py:**
  - Test ExecutionConfig creation with defaults
  - Test ExecutionConfig.to_simulator_config() conversion
  - Test RealisticExecutionModel initialization
  - Test RealisticExecutionModel initialization with default config
  - Test execute_order() with fully filled order
  - Test execute_order() with partially filled order
  - Test execute_order() with rejected order
  - Test execute_order() cost_breakdown scaling for partial fills
  - Test execute_order() updates summary
  - Test execute_order() logging when enabled/disabled
  - Test execute_orders_batch() with all valid orders
  - Test execute_orders_batch() skips orders without market data
  - Test execute_orders_batch() logs warnings for missing data
  - Test get_execution_summary() returns correct statistics
  - Test reset_summary() clears summary
  - Test estimate_execution_cost() returns all required fields
  - Test estimate_execution_cost() calculates correct totals
  - Test validate_order_feasibility() with open market
  - Test validate_order_feasibility() with closed market
  - Test validate_order_feasibility() with trading halt
  - Test validate_order_feasibility() warns on high participation rate
  - Test validate_order_feasibility() warns on low fill probability
  - Test Decimal precision maintained in calculations
  - Integration test with all execution components

---

## Notes
- This is the main orchestration class for realistic execution simulation
- Coordinates multiple execution components (cost, slippage, impact, fill simulator)
- Implements Almgren-Chriss market impact model
- Typical all-in costs: 5-10 bps (large cap), 10-25 bps (mid cap), 25-50+ bps (small cap)
- All methods are async except for utility methods
- Cost breakdown includes commission, SEC fee, FINRA TAF, exchange fees, slippage, market impact
- Properly handles partial fills and order rejections
- Maintains execution summary for batch operations
- Participation rate limits prevent unrealistic large orders
