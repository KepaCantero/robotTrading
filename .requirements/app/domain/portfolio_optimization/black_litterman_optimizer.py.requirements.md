# black_litterman_optimizer.py

## Purpose
Implements Black-Litterman portfolio optimization combining market equilibrium returns with investor views to produce stable, intuitive portfolio allocations per Black & Litterman (1992).

---

## Type Definitions / Data Classes

### InvestorView (frozen dataclass)
```python
view_type: ViewType              # REQUIRED - Type of view (ABSOLUTE or RELATIVE)
assets: list[int]                # REQUIRED - Indices of assets involved in the view
pick_vector: NDArray[np.float64] # REQUIRED - Picking vector P mapping view to assets
expected_return: float           # REQUIRED - Expected return Q for the view (annualized)
confidence: float                # REQUIRED - Confidence level 0.0 to 1.0 (exclusive)
id: str | None = None            # OPTIONAL - Identifier for the view
```

**Validation Rules:**
- confidence must be in (0, 1) exclusive - partial certainty representation
- pick_vector must match n_assets length
- ABSOLUTE views: pick_vector should sum to 1.0
- RELATIVE views: pick_vector should sum to 0.0

### BlackLittermanConfig (dataclass)
```python
tau: float = 0.05                # Uncertainty parameter for equilibrium returns
risk_aversion: float = 3.0       # Risk aversion coefficient
use_shrinkage: bool = True       # Apply Ledoit-Wolf shrinkage
lookback_days: int = 252         # Days for covariance calculation (Rule 66)
risk_free_rate: float = 0.02     # Risk-free rate for Sharpe calculation
max_position: float = 0.20       # Maximum weight per asset (Rule 70)
omega_method: str = "idzorek"    # Method for Ω calculation
```

**Validation Rules:**
- tau > 0
- risk_aversion > 0
- lookback_days >= 252 (Rule 66)
- max_position in (0, 1] (Rule 70)
- omega_method in ['idzorek', 'proportional', 'diagonal']

### BlackLittermanResult (frozen dataclass)
```python
weights: NDArray[np.float64]              # Optimal portfolio weights (N,)
equilibrium_returns: NDArray[np.float64]  # Market equilibrium returns Π (N,)
bl_returns: NDArray[np.float64]           # Combined expected returns E[R] (N,)
views: list[InvestorView]                 # Investor views used
posterior_covariance: NDArray[np.float64] # Posterior covariance (N, N)
expected_return: float                    # Portfolio expected return
expected_risk: float                      # Portfolio expected risk
sharpe_ratio: float                       # Portfolio Sharpe ratio
view_impact: NDArray[np.float64] | None   # Impact of each view on returns
success: bool = True                      # Whether optimization succeeded
message: str = "Optimization successful"  # Status message
```

---

## Function Signatures (Contracts)

### `EquilibriumReturns.from_market_caps(cov_matrix, market_caps, risk_aversion) -> NDArray[np.float64]`
**Pre:** cov_matrix is (N, N) PSD, market_caps positive, risk_aversion > 0
**Post:** Returns equilibrium returns Π = λ * Σ * w_market (N,)
**Raises:** ValueError if market_caps invalid
**Retry:** No
**Side Effects:** None (pure calculation)

### `ViewMatrix.build_pick_matrix(views, n_assets) -> NDArray[np.float64]`
**Pre:** views non-empty, pick_vector lengths match n_assets
**Post:** Returns pick matrix P of shape (K, N) where K = len(views)
**Raises:** ValueError if views empty or length mismatch
**Retry:** No
**Side Effects:** None

### `ViewMatrix.build_omega_matrix(P, cov_matrix, views, tau, method) -> NDArray[np.float64]`
**Pre:** P is (K, N), cov_matrix is (N, N) PSD, views non-empty, tau > 0
**Post:** Returns diagonal uncertainty matrix Ω (K, K)
**Raises:** ValueError if method unknown
**Retry:** No
**Side Effects:** None

### `BlackLittermanOptimizer.optimize(returns, market_caps, market_weights, views) -> BlackLittermanResult`
**Pre:** returns is (T, N) with T >= 252, either market_caps or market_weights provided
**Post:** Returns BlackLittermanResult with optimal weights and metrics
**Raises:** ValueError if insufficient data or invalid inputs
**Retry:** No
**Side Effects:** Logs optimization steps and results

---

## Acceptance Criteria
- [ ] Equilibrium returns calculated from market caps/weights: Π = λ * Σ * w_market
- [ ] Pick matrix P built correctly for absolute (sum=1) and relative (sum=0) views
- [ ] Omega matrix Ω calculated using Idzorek method with confidence levels
- [ ] BL returns combined: E[R] = M^(-1) * [(τΣ)^(-1)Π + P'Ω^(-1)Q]
- [ ] Covariance matrix uses 252-day lookback (Rule 66)
- [ ] Max position constraint enforced (Rule 70): w[i] <= 0.20
- [ ] Ledoit-Wolf shrinkage applied when use_shrinkage=True (Rule 74)
- [ ] Posterior covariance is positive semi-definite
- [ ] Weights sum to 1.0 within tolerance (Rule 69)
- [ ] All weights non-negative (long-only constraint, Rule 68)
- [ ] Exception handling returns equal weights fallback on failure
- [ ] Structured logging for all optimization steps (LOG-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance matrix PSD validation | ✅ OK - _ensure_psd() clips negative eigenvalues |
| TRD-003 | BASE_RULES | Position limits (max 20%) | ✅ OK - max_position constraint enforced |
| TRD-007 | BASE_RULES | Annualization uses TRADING_DAYS=252 | ✅ OK - lookback_days=252, returns annualized |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - No infrastructure imports |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - All key steps logged with context |
| TYP-001 | BASE_RULES | Type hints on all functions | ✅ OK - Full type coverage with NDArray |

---

## Dependencies
- **External:** numpy, scipy, sklearn (LedoitWolf), logging, dataclasses, enum
- **Internal:** None (domain layer has no internal dependencies)

---

## Required Tests
- **test_black_litterman_optimizer.py:**
  - Equilibrium returns calculation from market caps
  - Equilibrium returns from market weights
  - Pick matrix construction for absolute views
  - Pick matrix construction for relative views
  - Omega matrix calculation with Idzorek method
  - Omega matrix with proportional method
  - Omega matrix with diagonal method
  - BL returns combination with no views (returns equilibrium)
  - BL returns combination with absolute views
  - BL returns combination with relative views
  - Complete optimization pipeline
  - Covariance PSD enforcement
  - Ledoit-Wolf shrinkage application
  - Max position constraint enforcement
  - Weight sum constraint validation
  - Fallback to equal weights on optimization failure
  - View impact calculation
  - InvestorView validation (confidence bounds)
  - Configuration validation

---

## Notes
Black-Litterman addresses mean-variance instability by starting from market equilibrium and combining with investor views using Bayesian framework. Key is confidence parameter tau controlling view uncertainty.
