# order_flow.py

## Purpose
Order flow and information asymmetry analysis module implementing O'Hara's "Market Microstructure Theory" (Chapters 3-4) concepts for order flow modeling, informed trading detection, and adverse selection measurement.

---

## Type Definitions / Data Classes

### Order Class/DataClass
```python
@dataclass
class Order:
    order_id: str                        # REQUIRED - Unique order identifier
    timestamp: datetime                  # REQUIRED - Order submission time
    side: OrderSide                      # REQUIRED - Buy or sell enum
    order_type: OrderType                # REQUIRED - MARKET/LIMIT/STOP/ICEBERG enum
    price: Optional[Decimal]             # OPTIONAL - Limit price (None for market orders)
    size: Decimal                        # REQUIRED - Order quantity
    trader_type: Optional[TraderType]    # OPTIONAL - INFORMED/UNINFORMED/NOISE enum
```

**Validation Rules:**
- `size` must be positive (Decimal > 0)
- `price` (if provided) must be positive
- `order_id` must be non-empty string
- Enums auto-converted from strings in `__post_init__`

### OrderFlowSnapshot Class/DataClass
```python
@dataclass
class OrderFlowSnapshot:
    timestamp: datetime                  # REQUIRED - Snapshot time
    buy_volume: Decimal                  # REQUIRED - Total buy volume
    sell_volume: Decimal                 # REQUIRED - Total sell volume
    buy_count: int                       # REQUIRED - Number of buy orders
    sell_count: int                      # REQUIRED - Number of sell orders
    order_imbalance: Decimal             # COMPUTED - Net flow (-1 to +1), auto-calculated
```

**Validation Rules:**
- Volumes must be non-negative
- Counts must be non-negative
- `order_imbalance` = (buy_volume - sell_volume) / (buy_volume + sell_volume)
- Auto-calculated in `__post_init__`

### InformationAsymmetryMetrics Class/DataClass
```python
@dataclass
class InformationAsymmetryMetrics:
    timestamp: datetime                      # REQUIRED - Measurement time
    probability_of_informed_trading: float   # REQUIRED - PIN score (0-1)
    order_flow_toxicity: float              # REQUIRED - Toxicity score (0-1)
    informed_trader_intensity: float        # REQUIRED - Rate of informed trading
    information_asymmetry_index: float      # REQUIRED - Composite measure
    adverse_selection_risk: str             # REQUIRED - Risk level (LOW/MEDIUM/HIGH)
```

**Validation Rules:**
- All float scores must be between 0 and 1
- `adverse_selection_risk` must be valid risk level string

### OrderFlowForecast Class/DataClass
```python
@dataclass
class OrderFlowForecast:
    forecast_time: datetime                        # REQUIRED - Forecast target time
    expected_buy_volume: Decimal                  # REQUIRED - Expected buy volume
    expected_sell_volume: Decimal                 # REQUIRED - Expected sell volume
    expected_imbalance: Decimal                   # REQUIRED - Expected imbalance (-1 to +1)
    confidence_interval: Tuple[Decimal, Decimal]  # REQUIRED - (lower, upper) 95% CI
    forecast_method: str                          # REQUIRED - Method identifier
```

**Validation Rules:**
- Volumes must be non-negative
- `expected_imbalance` must be between -1 and +1
- `confidence_interval[0]` <= `expected_imbalance` <= `confidence_interval[1]`
- `forecast_method` must be one of: 'exponential_smoothing', 'linear_regression', etc.

---

## Function Signatures (Contracts)

### `OrderFlowAnalyzer.__init__(lookback_seconds: int = 300, alpha_threshold: float = 0.3) -> None`
**Pre:** lookback_seconds > 0, 0 <= alpha_threshold <= 1
**Post:** Analyzer initialized with empty order history
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `OrderFlowAnalyzer.add_order(order: Order) -> None`
**Pre:** order valid with required fields
**Post:** Order added to history, old orders pruned
**Raises:** ValueError if order invalid
**Retry:** No
**Side Effects:** Modifies _order_history list, prunes old orders

### `OrderFlowAnalyzer.calculate_order_imbalance(window_seconds: Optional[int] = None) -> Decimal`
**Pre:** window_seconds positive if provided
**Post:** Returns imbalance -1 to +1
**Raises:** Returns Decimal('0') if no orders
**Retry:** No
**Side Effects:** None

### `OrderFlowAnalyzer.estimate_order_flow_toxicity(recent_trades: pd.DataFrame, price_changes: pd.Series) -> float`
**Pre:** recent_trades has ['timestamp', 'side', 'size', 'price'], price_changes aligned
**Post:** Returns toxicity 0-1 (higher = more informed trading)
**Raises:** Returns 0.0 if insufficient data
**Retry:** No
**Side Effects:** None

### `OrderFlowAnalyzer.calculate_probability_of_informed_trading(order_snapshots: List[OrderFlowSnapshot], price_volatility: float) -> float`
**Pre:** order_snapshots length >= 10, price_volatility >= 0
**Post:** Returns PIN score 0-1
**Raises:** Returns 0.0 if insufficient snapshots
**Retry:** No
**Side Effects:** None

### `OrderFlowAnalyzer.detect_informed_trading(current_orders: List[Order], price_history: pd.DataFrame) -> Tuple[bool, float, str]`
**Pre:** current_orders not empty, price_history has 'close' column
**Post:** Returns (is_detected, confidence, explanation)
**Raises:** Returns (False, 0.0, "Insufficient data") on errors
**Retry:** No
**Side Effects:** None

### `OrderFlowAnalyzer.measure_adverse_selection_cost(executions: pd.DataFrame, subsequent_prices: pd.Series) -> Dict[str, float]`
**Pre:** executions has ['timestamp', 'side', 'price', 'size'], subsequent_prices aligned
**Post:** Returns {'avg_adverse_cost_bps', 'adverse_selection_rate', 'total_adverse_cost_usd'}
**Raises:** Returns zeros if DataFrames empty
**Retry:** No
**Side Effects:** None

### `OrderFlowAnalyzer.forecast_order_flow(forecast_horizon_seconds: int = 60, method: str = "exponential_smoothing") -> OrderFlowForecast`
**Pre:** forecast_horizon_seconds > 0, method valid
**Post:** Returns forecast with confidence interval
**Raises:** Returns neutral forecast if insufficient history
**Retry:** No
**Side Effects:** None

### `OrderFlowAnalyzer.calculate_information_content(orders: List[Order], market_price: Decimal) -> Dict[str, float]`
**Pre:** orders list not empty, market_price > 0
**Post:** Returns {'information_content', 'signal_to_noise_ratio', 'information_quality'}
**Raises:** Returns zeros if no orders
**Retry:** No
**Side Effects:** None

### `OrderFlowAnalyzer.generate_order_flow_report(current_orders: List[Order], price_history: pd.DataFrame) -> Dict`
**Pre:** current_orders not empty, price_history valid
**Post:** Returns comprehensive analysis dictionary
**Raises:** Returns partial report on errors
**Retry:** No
**Side Effects:** Adds orders to history via add_order()

### `OrderFlowSimulator.generate_order_flow(num_orders: int, base_price: float, price_impact: float = 0.001, spread_bps: float = 1.0) -> List[Order]`
**Pre:** num_orders > 0, base_price > 0
**Post:** Returns list of simulated orders with timestamps
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Uses np.random for stochastic generation

### `get_order_flow_analyzer(lookback_seconds: int = 300, alpha_threshold: float = 0.3) -> OrderFlowAnalyzer`
**Pre:** lookback_seconds > 0, 0 <= alpha_threshold <= 1
**Post:** Returns singleton instance
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Creates singleton if not exists

---

## Acceptance Criteria
- [ ] AC-OF-001: Order dataclass validates enum conversion in __post_init__
- [ ] AC-OF-002: OrderFlowSnapshot.order_imbalance auto-calculates correctly
- [ ] AC-OF-003: All probability scores clamped to [0, 1]
- [ ] AC-OF-004: Empty order history returns Decimal('0') imbalance
- [ ] AC-OF-005: PIN calculation handles edge case (alpha=0, epsilon=0)
- [ ] AC-OF-006: Order history pruning respects lookback_seconds * 2
- [ ] AC-OF-007: Forecast confidence interval contains expected_imbalance
- [ ] AC-OF-008: Adverse cost calculation handles buy/sell sides correctly
- [ ] AC-OF-009: Information quality classification thresholds documented
- [ ] AC-OF-010: Simulator creates orders with valid timestamps

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECIFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | 05-architecture.md | Domain layer has no framework dependencies | ✅ OK - Pure Python |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK - All functions typed |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Order flow analysis |
| LOG-001 | 09-logging-observability.md | Structured logging | ⚠️ NOT APPLIED - No logging |
| TRD-004 | Trading rules | Audit trail for order analysis | ⚠️ GAP - No audit logging |
| QL-001 | Code quality | Complexity < 10 | ✅ OK - Functions focused |
| CC-002 | Clean code | No duplication | ⚠️ GAP - _generate_recommendations similar across modules |
| FMT-007 | Formatting | No mutable defaults | ✅ OK - Uses None for optionals |
| SEC-007 | Security | Input validation for DataFrame columns | ⚠️ GAP - No column validation |
| TRD-002 | Trading rules | Validate order sizes > 0 | ✅ OK - Decimal validation |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** numpy, pandas (data processing)
- **Internal:** None (pure domain module)

---

## Required Tests
- **tests/microstructure/test_order_flow.py:**
  - Test Order dataclass enum conversion from strings
  - Test OrderFlowSnapshot.order_imbalance calculation
  - Test calculate_order_imbalance with window parameter
  - Test estimate_order_flow_toxicity correlation calculation
  - Test calculate_probability_of_informed_trading PIN formula
  - Test detect_informed_trading alignment detection
  - Test measure_adverse_selection_cost buy/sell logic
  - Test forecast_order_flow with all methods
  - Test calculate_information_content classification
  - Test generate_order_flow_report structure
  - Test OrderFlowSimulator order generation
  - Test order history pruning in add_order()
  - Test singleton behavior

---

## Notes
- Implements Easley et al. (1996) PIN (Probability of INformed Trading) model
- Order flow toxicity measures correlation between order flow and subsequent price changes
- Adverse selection cost: market maker losses from trading with informed traders
- Information asymmetry index combines PIN, toxicity, and intensity metrics
- Simulator generates orders with informed trader behavior based on O'Hara models
