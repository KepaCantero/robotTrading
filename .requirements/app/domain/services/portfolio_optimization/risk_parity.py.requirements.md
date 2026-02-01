# risk_parity.py

## Purpose
Implements Risk Parity portfolio optimization equalizing risk contribution across assets, with support for inverse volatility, equal weight, and diversified risk parity methods.

---

## Type Definitions / Data Classes

### RiskParityResult (dataclass)
```python
weights: np.ndarray                  # Risk parity weights (N,)
risk_contributions: np.ndarray       # Risk contribution of each asset (N,)
risk_budget: np.ndarray              # Target risk budget (N,) - usually equal
symbols: List[str]                   # Asset symbols
converged: bool                      # Whether optimization converged

@property
def weights_dict(self) -> Dict[str, float]:  # Get weights as dictionary
    return {symbol: float(weight) for symbol, weight in zip(self.symbols, self.weights)}

@property
def risk_parity_error(self) -> float:  # Std dev of risk contributions
    return float(np.std(self.risk_contributions))
```

**Validation Rules:**
- weights must sum to 1.0
- All weights must be non-negative (if min_weight >= 0)
- risk_contributions must sum to portfolio risk

---

## Function Signatures (Contracts)

### `RiskParityOptimizer.__init__(risk_free_rate, min_weight, max_weight)`
**Pre:** 0 <= min_weight <= max_weight <= 1.0
**Post:** Risk parity optimizer initialized
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `optimize(cov_matrix, symbols, risk_budget) -> RiskParityResult`
**Pre:** cov_matrix is (N, N) PSD, risk_budget optional (defaults to equal)
**Post:** Returns RiskParityResult with optimal weights
**Raises:** ValueError if covariance validation fails
**Retry:** No
**Side Effects:** Logs optimization convergence

### `inverse_volatility(cov_matrix, symbols) -> RiskParityResult`
**Pre:** cov_matrix is (N, N)
**Post:** Returns RiskParityResult with inverse volatility weights
**Raises:** ValueError if all assets have zero variance
**Retry:** No
**Side Effects:** None

### `equal_weight(cov_matrix, symbols) -> RiskParityResult`
**Pre:** cov_matrix is (N, N) square
**Post:** Returns RiskParityResult with equal weights
**Raises:** ValueError if covariance invalid
**Retry:** No
**Side Effects:** None

### `diversified_risk_parity(cov_matrix, symbols, kappa) -> RiskParityResult`
**Pre:** cov_matrix is (N, N) PSD, kappa > 0
**Post:** Returns RiskParityResult with DRP weights (diversification penalty)
**Raises:** ValueError if covariance validation fails
**Retry:** No
**Side Effects:** Logs optimization result

### `get_diversification_ratio(weights, cov_matrix) -> float`
**Pre:** weights sum to 1.0, cov_matrix is (N, N)
**Post:** Returns diversification ratio DR = (Σ w_i σ_i) / σ_p
**Raises:** None (returns 1.0 if portfolio_vol = 0)
**Retry:** No
**Side Effects:** None

### `cluster_based_risk_parity(cov_matrix, cluster_labels, symbols) -> np.ndarray`
**Pre:** cov_matrix is (N, N), cluster_labels length = N
**Post:** Returns CBRP weights with inter and intra-cluster allocation
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** Logs warnings for invalid clusters

---

## Acceptance Criteria
- [ ] Covariance matrix validated as PSD before optimization
- [ ] Risk contributions equalized: RC_i = w_i * (Σw)_i / σ_p = constant
- [ ] Weights sum to 1.0 (Rule 69)
- [ ] Long-only constraint enforced (Rule 68): w[i] >= 0
- [ ] Max position constraint enforced (Rule 70): w[i] <= max_weight
- [ ] Inverse volatility: w_i ∝ 1/σ_i
- [ ] Diversified risk parity adds entropy penalty: -kappa * Σ w_i * log(w_i)
- [ ] Zero variance assets handled with MIN_VARIANCE_THRESHOLD
- [ ] Optimization convergence tracked
- [ ] Cluster-based risk parity implemented
- [ ] Diversification ratio calculated
- [ ] Exception handling with structured logging

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance PSD validation | ✅ OK - validate_covariance_matrix() called |
| TRD-003 | BASE_RULES | Position limits enforced | ✅ OK - min_weight, max_weight bounds |
| TRD-007 | BASE_RULES | TRADING_DAYS=252 | ⚠️ NOT APPLIED - Risk parity works on any timescale |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - Only numpy/scipy imports |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - All key steps logged |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ OK - log_optimization_failure() used |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - Full type hints |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Separate methods for each strategy |

---

## Dependencies
- **External:** numpy, scipy (minimize), logging
- **Internal:** app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_risk_parity.py:**
  - Risk parity optimization with equal risk budget
  - Risk parity optimization with custom risk budget
  - Inverse volatility weights
  - Equal weight benchmark
  - Diversified risk parity with entropy penalty
  - Risk contribution calculation
  - Risk parity error (std dev of contributions)
  - Zero variance asset handling
  - Covariance sanitization
  - Max position constraint enforcement
  - Min position constraint enforcement
  - Diversification ratio calculation
  - Cluster-based risk parity
  - Cluster variance calculation
  - Inter-cluster risk parity allocation
  - Intra-cluster risk parity allocation
  - Exception handling with fallback

---

## Notes
Risk Parity equalizes risk contributions, not weights. Uses scipy.optimize.minimize with SLSQP. Convergence critical for quality - check converged flag. Diversification ratio > 1 indicates diversification benefit.
