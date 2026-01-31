# models.py

## Purpose
Market microstructure models module implementing foundational models from Maureen O'Hara's "Market Microstructure Theory" including Glosten-Milgrom (1985), Kyle (1985), Roll (1984), and Stoll (2000) for understanding information incorporation into prices.

---

## Type Definitions / Data Classes

### ModelParameters Class/DataClass
```python
@dataclass
class ModelParameters:
    alpha: float    # REQUIRED - Probability of information event (0-1)
    delta: float    # REQUIRED - Probability of bad news given event (0-1)
    mu: float       # REQUIRED - Informed trader arrival rate
    epsilon: float  # REQUIRED - Uninformed trader arrival rate (buy = sell)
    sigma: float    # REQUIRED - Informed trader order size
```

**Validation Rules:**
- `alpha` must be between 0 and 1
- `delta` must be between 0 and 1
- `mu`, `epsilon`, `sigma` must be positive

### GlostenMilgromResult Class/DataClass
```python
@dataclass
class GlostenMilgromResult:
    timestamp: datetime                      # REQUIRED - Calculation time
    bid_price: Decimal                       # REQUIRED - Equilibrium bid price
    ask_price: Decimal                       # REQUIRED - Equilibrium ask price
    spread_bps: float                        # REQUIRED - Spread in basis points
    adverse_selection_component: float       # REQUIRED - Portion of spread due to adverse selection (0-1)
    informed_trading_probability: float      # REQUIRED - Probability current trade is informed (0-1)
```

**Validation Rules:**
- `bid_price` < `ask_price` (strict inequality)
- `spread_bps` >= 0
- Component values between 0 and 1

### KyleModelResult Class/DataClass
```python
@dataclass
class KyleModelResult:
    timestamp: datetime                      # REQUIRED - Calculation time
    market_depth_lambda: float               # REQUIRED - Market depth parameter (price impact per unit)
    expected_informed_profit: float          # REQUIRED - Expected profit of informed trader
    optimal_order_size: float                # REQUIRED - Optimal order size for informed trader
    price_impact: float                      # REQUIRED - Expected price impact
    information_revelation: float            # REQUIRED - How much information revealed (0-1)
```

**Validation Rules:**
- `market_depth_lambda` > 0 (higher = less depth)
- `expected_informed_profit` >= 0
- `information_revelation` between 0 and 1

### OrderFlowImpactResult Class/DataClass
```python
@dataclass
class OrderFlowImpactResult:
    timestamp: datetime                      # REQUIRED - Calculation time
    immediate_impact: float                  # REQUIRED - Immediate price impact in bps
    permanent_impact: float                  # REQUIRED - Long-run price impact in bps
    impact_decay: float                      # REQUIRED - Decay rate of temporary impact (0-1)
    information_content: float               # REQUIRED - Information content of order flow (0-1)
    adjustment_speed: float                  # REQUIRED - Speed of price adjustment
```

**Validation Rules:**
- `immediate_impact` >= `permanent_impact` (temporary adds to permanent)
- Decay and content between 0 and 1

### RollSpreadResult Class/DataClass
```python
@dataclass
class RollSpreadResult:
    timestamp: datetime                      # REQUIRED - Calculation time
    estimated_spread_bps: float              # REQUIRED - Estimated effective spread
    covariance: float                        # REQUIRED - First-order serial covariance
    spread_std_error: float                  # REQUIRED - Standard error of spread estimate
    is_significant: bool                     # REQUIRED - Whether spread statistically significant
```

**Validation Rules:**
- `estimated_spread_bps` >= 0
- `covariance` <= 0 (negative covariance indicates bid-ask bounce)
- `spread_std_error` >= 0

### StollDecompositionResult Class/DataClass
```python
@dataclass
class StollDecompositionResult:
    timestamp: datetime                      # REQUIRED - Calculation time
    total_spread_bps: float                  # REQUIRED - Total observed spread
    order_processing_bps: float              # REQUIRED - Fixed cost component
    inventory_holding_bps: float             # REQUIRED - Inventory risk component
    adverse_selection_bps: float             # REQUIRED - Information asymmetry component
    component_weights: Dict[str, float]      # REQUIRED - Weight of each component (sums to 1.0)
```

**Validation Rules:**
- All spread values >= 0
- Components sum to `total_spread_bps` (within tolerance)
- `component_weights` values sum to 1.0

---

## Function Signatures (Contracts)

### `GlostenMilgromModel.__init__(initial_value: float = 100.0, alpha: float = 0.2, delta: float = 0.5, mu: float = 0.1, epsilon: float = 0.5) -> None`
**Pre:** initial_value > 0, 0 <= alpha, delta <= 1, mu, epsilon > 0
**Post:** Model initialized with parameters
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `GlostenMilgromModel.calculate_equilibrium_spread() -> Tuple[float, float]`
**Pre:** Model initialized with valid parameters
**Post:** Returns (bid_price, ask_price) where bid < ask
**Raises:** Returns equal prices if no informed traders
**Retry:** No
**Side Effects:** None

### `GlostenMilgromModel.simulate_trade_sequence(num_trades: int, information_event: Optional[InformationEvent] = None) -> pd.DataFrame`
**Pre:** num_trades > 0
**Post:** Returns DataFrame with trade simulation columns
**Raises:** ValueError if num_trades <= 0
**Retry:** No
**Side Effects:** Uses np.random for stochastic simulation

### `GlostenMilgromModel.calculate_spread_components() -> Dict[str, float]`
**Pre:** Model initialized
**Post:** Returns {'total_spread', 'adverse_selection_pct', 'order_processing_pct', 'inventory_holding_pct'}
**Raises:** Returns zeros if spread = 0
**Retry:** No
**Side Effects:** None

### `KyleModel.__init__(V0: float = 100.0, Sigma0: float = 25.0, Sigma_u: float = 100.0) -> None`
**Pre:** V0 > 0, Sigma0 > 0, Sigma_u > 0
**Post:** Model initialized with lambda = sqrt(Sigma0) / sqrt(Sigma_u)
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `KyleModel.calculate_market_depth() -> float`
**Pre:** Model initialized
**Post:** Returns lambda parameter (price impact per unit)
**Raises:** Returns calculated lambda
**Retry:** No
**Side Effects:** None

### `KyleModel.calculate_optimal_informed_trading(true_value: float) -> KyleModelResult`
**Pre:** true_value > 0
**Post:** Returns result with optimal order = (true_value - V0) / (2*lambda)
**Raises:** Returns result even if true_value equals V0
**Retry:** No
**Side Effects:** None

### `KyleModel.simulate_kyle_equilibrium(num_periods: int = 10) -> pd.DataFrame`
**Pre:** num_periods > 0
**Post:** Returns DataFrame with simulation results
**Raises:** ValueError if num_periods <= 0
**Retry:** No
**Side Effects:** Uses np.random for stochastic simulation

### `MadhavanRichardsonModel.__init__(price_impact: float = 0.001, decay_rate: float = 0.5) -> None`
**Pre:** price_impact > 0, 0 <= decay_rate <= 1
**Post:** Model initialized
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `MadhavanRichardsonModel.estimate_order_flow_impact(order_flow: pd.Series, price_changes: pd.Series) -> OrderFlowImpactResult`
**Pre:** Series aligned, min length >= 10
**Post:** Returns impact estimates from regression
**Raises:** Returns zeros if insufficient data
**Retry:** No
**Side Effects:** None

### `RollSpreadEstimator.estimate_spread(price_series: pd.Series) -> RollSpreadResult`
**Pre:** price_series length >= 10
**Post:** Returns spread estimate from serial covariance
**Raises:** Returns zero spread if covariance >= 0
**Retry:** No
**Side Effects:** None

### `StollSpreadDecomposer.decompose_spread(observed_spread_bps: float, price_variance: float, order_flow_imbalance: float, volume: float, volatility: float) -> StollDecompositionResult`
**Pre:** observed_spread_bps > 0, all floats valid
**Post:** Returns components that sum to total spread
**Raises:** Returns equal split if calculation fails
**Retry:** No
**Side Effects:** None

### `MicrostructureModelComparator.analyze_market(price_history: pd.DataFrame, order_flow: Optional[pd.Series] = None) -> Dict`
**Pre:** price_history has 'close' column, 'volume' optional
**Post:** Returns dictionary with all model results
**Raises:** Returns partial results on errors
**Retry:** No
**Side Effects:** None

### `get_glosten_milgrom_model(...) -> GlostenMilgromModel`
**Pre:** All parameters positive and within valid ranges
**Post:** Returns singleton instance
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Creates singleton if not exists

---

## Acceptance Criteria
- [ ] AC-MOD-001: All result dataclasses have to_dict() methods
- [ ] AC-MOD-002: Probability parameters (alpha, delta) clamped to [0, 1]
- [ ] AC-MOD-003: Bid price strictly less than ask price in GM model
- [ ] AC-MOD-004: Kyle lambda calculation: sqrt(Sigma0) / sqrt(Sigma_u)
- [ ] AC-MOD-005: Roll spread: 2*sqrt(-covariance) only if covariance < 0
- [ ] AC-MOD-006: Stoll components sum to total within 0.01% tolerance
- [ ] AC-MOD-007: Simulations use np.random for reproducibility (seed option)
- [ ] AC-MOD-008: InformationEvent enum has exactly 3 values: NONE, GOOD, BAD
- [ ] AC-MOD-009: All model parameters validated in __init__
- [ ] AC-MOD-010: Singleton functions return same instance on repeated calls

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECIFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | 05-architecture.md | Domain layer has no framework dependencies | ✅ OK - Pure Python |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK - All functions typed |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Each model focused |
| LOG-001 | 09-logging-observability.md | Structured logging | ⚠️ NOT APPLIED - No logging |
| TRD-001 | Trading rules | Validate model parameters | ✅ OK - Parameter validation |
| QL-001 | Code quality | Complexity < 10 | ✅ OK - Models are simple |
| CC-002 | Clean code | No duplication | ⚠️ GAP - Similar to_dict() across dataclasses |
| FMT-007 | Formatting | No mutable defaults | ✅ OK - Uses None for optionals |
| SEC-007 | Security | Input validation for Series/DataFrames | ⚠️ GAP - No validation |
| TRD-007 | Trading rules | Document trading days = 252 | ⚠️ NOT APPLIED - No annualization |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** numpy, pandas (computations)
- **Internal:** None (pure domain module)

---

## Required Tests
- **tests/microstructure/test_models.py:**
  - Test GlostenMilgromModel equilibrium spread calculation
  - Test GM model simulation with all InformationEvent types
  - Test GM spread components (100% adverse selection in basic model)
  - Test KyleModel market depth lambda calculation
  - Test Kyle optimal trading: x = (v - V0) / (2*lambda)
  - Test Kyle equilibrium simulation returns expected columns
  - Test MadhavanRichardsonModel order flow impact regression
  - Test RollSpreadEstimator with positive/negative covariance
  - Test StollSpreadDecomposer component normalization
  - Test MicrostructureModelComparator analyze_market output
  - Test all singleton functions return same instance
  - Test parameter validation in model constructors
  - Test to_dict() methods produce serializable output

---

## Notes
- Glosten-Milgrom (1985): Sequential trade model with adverse selection
- Kyle (1985): Strategic informed trading with market depth lambda
- Roll (1984): Spread estimation from serial covariance: s = 2*sqrt(-cov)
- Stoll (2000): Spread decomposition into 3 components (order processing, inventory, adverse selection)
- Madhavan-Richardson-Rooms (1997): Order flow impact with permanent/temporary components
- All models implement foundational microstructure theory from O'Hara (1995)
- Singleton pattern for model instances to avoid repeated initialization
