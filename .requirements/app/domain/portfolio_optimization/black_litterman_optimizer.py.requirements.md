# black_litterman_optimizer.py.requirements.md

## Purpose
Implements Black-Litterman portfolio optimization combining market equilibrium returns with investor views for robust, intuitive portfolio allocations.

---

## Type Definitions / Data Classes

### ViewType Enum
```python
class ViewType(str, Enum):
    ABSOLUTE = "absolute"  # "Asset A will return X%"
    RELATIVE = "relative"  # "Asset A will outperform Asset B by X%"
```

### InvestorView DataClass
```python
@dataclass(frozen=True)
class InvestorView:
    view_type: ViewType              # REQUIRED - Type of view (ABSOLUTE or RELATIVE)
    assets: list[int]                # REQUIRED - Indices of assets involved in view
    pick_vector: NDArray[np.float64] # REQUIRED - Picking vector P mapping view to assets (N,)
    expected_return: float           # REQUIRED - Expected return Q for the view (annualized)
    confidence: float                # REQUIRED - Confidence level (0, 1) exclusive
    id: str | None                   # OPTIONAL - View identifier
```

**Validation Rules:**
- confidence must be in (0, 1) - strictly between, not inclusive
- For ABSOLUTE views: pick_vector.sum() ≈ 1.0
- For RELATIVE views: pick_vector.sum() ≈ 0.0
- len(pick_vector) must equal total number of assets in universe
- expected_return is annualized (e.g., 0.08 for 8%)

### BlackLittermanConfig DataClass
```python
@dataclass
class BlackLittermanConfig:
    tau: float                       # REQUIRED - Uncertainty parameter, default 0.05, must be > 0
    risk_aversion: float             # REQUIRED - Risk aversion coefficient λ, default 3.0, > 0
    use_shrinkage: bool              # REQUIRED - Use Ledoit-Wolf shrinkage (Rule 74), default True
    lookback_days: int               # REQUIRED - Days for covariance (Rule 66), default 252, >= 252
    risk_free_rate: float            # REQUIRED - Risk-free rate for Sharpe, default 0.02
    max_position: float              # REQUIRED - Max weight per asset (Rule 70), default 0.20, (0, 1]
    omega_method: str                # REQUIRED - Method for Ω calculation: 'idzorek', 'proportional', 'diagonal'
```

**Validation Rules:**
- tau > 0 (uncertainty parameter must be positive)
- risk_aversion > 0 (typically 2.0 to 4.0)
- lookback_days >= 252 (Rule 66)
- max_position in (0, 1] (Rule 70)
- omega_method in ['idzorek', 'proportional', 'diagonal']

### BlackLittermanResult DataClass
```python
@dataclass(frozen=True)
class BlackLittermanResult:
    weights: NDArray[np.float64]              # REQUIRED - Optimal portfolio weights (N,)
    equilibrium_returns: NDArray[np.float64]  # REQUIRED - Market equilibrium returns Π (N,)
    bl_returns: NDArray[np.float64]           # REQUIRED - BL combined returns E[R] (N,)
    views: list[InvestorView]                 # REQUIRED - Investor views used
    posterior_covariance: NDArray[np.float64] # REQUIRED - Posterior covariance (N, N)
    expected_return: float                    # REQUIRED - Portfolio expected return
    expected_risk: float                      # REQUIRED - Portfolio expected risk
    sharpe_ratio: float                       # REQUIRED - Portfolio Sharpe ratio
    view_impact: NDArray[np.float64] | None   # OPTIONAL - Impact of each view on returns
    success: bool                             # REQUIRED - Whether optimization succeeded
    message: str                              # REQUIRED - Status message
```

**Property Methods:**
- `weights_dict: dict[str, float]` - Convert weights to dictionary
- `get_view_summary() -> list[dict]` - Get summary of views and impacts

---

## Function Signatures (Contracts)

### `EquilibriumReturns.from_market_caps(cov_matrix, market_caps, risk_aversion) -> NDArray[np.float64]`
**Pre:** cov_matrix is valid (N, N), market_caps positive (N,), risk_aversion > 0
**Post:** Returns equilibrium returns Π = λ * Σ * w_market (N,)
**Raises:** None
**Retry:** No
**Side Effects:** Logs equilibrium return statistics

### `EquilibriumReturns.from_weights(cov_matrix, market_weights, risk_aversion) -> NDArray[np.float64]`
**Pre:** cov_matrix valid (N, N), market_weights sum to 1.0, risk_aversion > 0
**Post:** Returns equilibrium returns Π (N,)
**Raises:** ValueError if weights don't sum to 1
**Retry:** No
**Side Effects:** None

### `ViewMatrix.build_pick_matrix(views: list[InvestorView], n_assets: int) -> NDArray[np.float64]`
**Pre:** views is non-empty, n_assets >= len(views)
**Post:** Returns pick matrix P (K, N) where K = len(views)
**Raises:** ValueError if views empty or pick_vector length mismatch
**Retry:** No
**Side Effects:** Logs matrix dimensions

### `ViewMatrix.build_q_vector(views: list[InvestorView]) -> NDArray[np.float64]`
**Pre:** views is non-empty
**Post:** Returns Q vector (K,) of expected returns
**Raises:** ValueError if views empty
**Retry:** No
**Side Effects:** Logs Q statistics

### `ViewMatrix.build_omega_matrix(P, cov_matrix, views, tau, method) -> NDArray[np.float64]`
**Pre:** P is (K, N), cov_matrix (N, N), views length K, tau > 0, method valid
**Post:** Returns uncertainty matrix Ω (K, K) diagonal
**Raises:** ValueError if method invalid
**Retry:** No
**Side Effects:** Logs Ω diagonal mean

### `BlackLittermanOptimizer.__init__(config: BlackLittermanConfig | None) -> None`
**Pre:** config is None or valid BlackLittermanConfig
**Post:** Optimizer initialized with config or defaults
**Raises:** ValueError if config validation fails
**Retry:** No
**Side Effects:** Logs initialization parameters

### `calculate_covariance_matrix(returns, use_shrinkage: bool | None) -> NDArray[np.float64]`
**Pre:** returns is 2D (T, N) with T >= lookback_days (Rule 66)
**Post:** Returns covariance matrix (N, N) annualized with optional shrinkage
**Raises:** ValueError if insufficient data
**Retry:** No
**Side Effects:** Ensures PSD, logs parameters

### `calculate_equilibrium_returns(cov_matrix, market_caps, market_weights) -> NDArray[np.float64]`
**Pre:** cov_matrix valid, exactly one of market_caps or market_weights provided
**Post:** Returns equilibrium returns Π (N,)
**Raises:** ValueError if neither or both provided
**Retry:** No
**Side Effects:** Delegates to EquilibriumReturns static methods

### `calculate_bl_returns(equilibrium_returns, cov_matrix, views) -> tuple[NDArray, NDArray]`
**Pre:** equilibrium_returns (N,), cov_matrix (N, N) PSD, views may be empty
**Post:** Returns (bl_returns, posterior_covariance) from BL formula
**Raises:** None
**Retry:** No
**Side Effects:** Implements core BL: E[R] = M^(-1) * [(τΣ)^(-1)Π + P'Ω^(-1)Q]

### `optimize(returns, market_caps, market_weights, views) -> BlackLittermanResult`
**Pre:** returns 2D (T, N), market_caps or weights provided, views validated
**Post:** Returns BlackLittermanResult with optimal weights and metrics
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** Full BL pipeline, returns equal weights on failure

### `compute_black_litterman_weights(returns, market_caps, views, tau, risk_aversion, max_position) -> NDArray[np.float64]`
**Pre:** returns 2D (T, N), market_caps positive, views non-empty, tau > 0, risk_aversion > 0
**Post:** Returns optimal weights (N,)
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** Creates config, optimizer, and calls optimize

---

## Acceptance Criteria
- [ ] AC-BL-001: Equilibrium returns formula: Π = λ * Σ * w_market
- [ ] AC-BL-002: Pick matrix P has shape (K, N) where K = number of views
- [ ] AC-BL-003: Q vector has length K = number of views
- [ ] AC-BL-004: Ω (omega) matrix is diagonal (K, K)
- [ ] AC-BL-005: Confidence in (0, 1) exclusive for InvestorView
- [ ] AC-BL-006: tau > 0 (uncertainty parameter)
- [ ] AC-BL-007: risk_aversion > 0 (typically 2.0 to 4.0)
- [ ] AC-BL-008: lookback_days >= 252 (Rule 66)
- [ ] AC-BL-009: max_position in (0, 1] (Rule 70)
- [ ] AC-BL-010: Covariance uses Ledoit-Wolf shrinkage (Rule 74)
- [ ] AC-BL-011: Weights sum to 1.0
- [ ] AC-BL-012: All weights >= 0 (long-only)
- [ ] AC-BL-013: BL returns formula: E[R] = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1) * [(τΣ)^(-1)Π + P'Ω^(-1)Q]
- [ ] AC-BL-014: ABSOLUTE view pick_vector sums to ~1.0
- [ ] AC-BL-015: RELATIVE view pick_vector sums to ~0.0

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance must be positive semi-definite | ✅ OK - _ensure_psd method |
| TRD-003 | BASE_RULES | Enforce max position size | ✅ OK - max_position constraint (Rule 70) |
| TRD-007 | BASE_RULES | Document TRADING_DAYS = 252 | ✅ OK - lookback_days=252 default |
| ARCH-004 | BASE_RULES | Functions < 20 lines | ❌ GAP - Some functions exceed (optimize: 80+ lines) |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - Modern type hints throughout |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ❌ GAP - Generic error logging |
| TST-005 | BASE_RULES | Coverage > 80% | ⚠️ NOT APPLIED - Tests not yet written |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Separate classes for each concern |
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Focused, minimal interfaces |

### Black-Litterman Specific Rules (from paper):

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| BL-001 | Combine equilibrium returns with investor views | ✅ OK - Core BL formula |
| BL-002 | Use tau (uncertainty parameter) for scaling | ✅ OK - tau_Sigma calculation |
| BL-003 | Calculate equilibrium from market caps or weights | ✅ OK - from_market_caps, from_weights |
| BL-004 | Build P (pick) and Q (view) matrices | ✅ OK - ViewMatrix class |
| BL-005 | Calculate Ω (uncertainty) matrix | ✅ OK - build_omega_matrix with 3 methods |
| BL-006 | Support absolute and relative views | ✅ OK - ViewType enum + InvestorView |
| BL-007 | Use confidence levels for view uncertainty | ✅ OK - Idzorek method in omega calculation |
| BL-008 | Apply Ledoit-Wolf shrinkage (Rule 74) | ✅ OK - _shrink_covariance |
| BL-009 | Enforce max position constraint (Rule 70) | ✅ OK - bounds in max_sharpe_weights |
| BL-010 | 252-day lookback for covariance (Rule 66) | ✅ OK - lookback_days=252 |

---

## Dependencies
- **External:** numpy, scipy (optimize), sklearn (covariance: LedoitWolf - optional)
- **Internal:** None (standalone domain module)

---

## Required Tests
- **tests/domain/portfolio_optimization/test_black_litterman_optimizer.py:**

#### InvestorView Tests:
- Test InvestorView creation with valid absolute view
- Test InvestorView creation with valid relative view
- Test InvestorView validation: confidence must be in (0, 1) exclusive
- Test InvestorView validation: absolute view pick vector sums to 1
- Test InvestorView validation: relative view pick vector sums to 0
- Test InvestorView with optional id field

#### BlackLittermanConfig Tests:
- Test config creation with valid parameters
- Test config validation: tau > 0
- Test config validation: risk_aversion > 0
- Test config validation: lookback_days >= 252
- Test config validation: max_position in (0, 1]
- Test config validation: omega_method valid values

#### EquilibriumReturns Tests:
- Test from_market_caps with valid inputs
- Test from_market_caps formula: Π = λ * Σ * w_market
- Test from_weights with valid inputs
- Test from_weights validates sum to 1.0
- Test from_weights raises ValueError if sum != 1

#### ViewMatrix Tests:
- Test build_pick_matrix with absolute views
- Test build_pick_matrix with relative views
- Test build_pick_matrix raises error if views empty
- Test build_pick_matrix raises error if length mismatch
- Test build_q_vector with valid views
- Test build_q_vector raises error if views empty
- Test build_omega_matrix with idzorek method
- Test build_omega_matrix with proportional method
- Test build_omega_matrix with diagonal method
- Test build_omega_matrix raises error if method invalid
- Test Ω matrix is diagonal

#### BlackLittermanOptimizer Tests:
- Test initialization with default config
- Test initialization with custom config
- Test calculate_covariance_matrix with shrinkage
- Test calculate_covariance_matrix without shrinkage
- Test calculate_covariance_matrix validates lookback_days
- Test calculate_equilibrium_returns with market_caps
- Test calculate_equilibrium_returns with market_weights
- Test calculate_equilibrium_returns raises error if neither provided
- Test calculate_bl_returns with empty views (returns equilibrium)
- Test calculate_bl_returns with valid views
- Test BL returns formula correctness
- Test optimize with market_caps and views
- Test optimize with market_weights and views
- Test optimize returns valid weights (sum to 1, non-negative)
- Test optimize enforces max_position constraint
- Test optimize failure returns equal weights fallback
- Test compute_black_litterman_weights convenience function
- Test BlackLittermanResult properties
- Test get_view_summary returns correct structure
- Test posterior_covariance is positive semi-definite

#### Edge Cases:
- Test with 2 assets only
- Test with no views (pure equilibrium)
- Test with many views (K > N)
- Test with conflicting views
- Test with high confidence views (approaching 1.0)
- Test with low confidence views (approaching 0.0)

---

## Notes
- Black-Litterman (1992) addresses the "garbage in, garbage out" problem of traditional MVO
- By starting from market equilibrium (what the market collectively believes), BL returns are more stable
- Investor views are expressed as deviations from equilibrium, not absolute predictions
- The tau parameter controls uncertainty in the prior (equilibrium): smaller = more confidence
- The Idzorek method for Ω allows intuitive confidence levels (0-100%) for each view
- BL portfolios are more intuitive and don't require extreme positions like traditional MVO
- The implementation follows the Walters (2014) formulation for clarity
- Consider adding view performance tracking to assess view quality over time
- Could add support for view timing (expiration dates for views)
- The tau=0.05 default is standard but could be calibrated for specific markets
