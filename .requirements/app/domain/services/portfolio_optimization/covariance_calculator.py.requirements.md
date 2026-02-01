# covariance_calculator.py

## Purpose
Domain service for calculating covariance and correlation matrices for portfolio optimization. Supports sample covariance, shrinkage estimators (Ledoit-Wolf), and exponential-weighted covariance with PSD enforcement.

---

## Type Definitions / Data Classes

### CovarianceResult (dataclass)
```python
covariance_matrix: np.ndarray      # N x N covariance matrix
correlation_matrix: np.ndarray     # N x N correlation matrix
std_devs: np.ndarray               # Standard deviations (N,)
means: np.ndarray                  # Mean returns (N,)
symbols: List[str]                 # Asset symbols (N)
```

**Methods:**
- get_covariance(symbol1, symbol2) -> Decimal
- get_correlation(symbol1, symbol2) -> Decimal
- get_std_dev(symbol) -> Decimal

**Validation Rules:**
- covariance_matrix is positive semidefinite
- correlation_matrix has 1.0 on diagonal, values in [-1, 1]
- std_devs > 0 (all assets)
- len(symbols) == N (matrix dimension)

### CovarianceCalculator (class)
```python
_min_observations: int             # Minimum observations required (default: 252)
_shrinkage: Optional[float]        # Shrinkage intensity [0, 1] (default: None)
```

**Constants:**
- MIN_OBSERVATIONS = 252 (TRADING_DAYS from _validation)
- DEFAULT_EWMA_SPAN = 60 (~quarterly)
- DEFAULT_SHRINKAGE_INTENSITY = 0.1
- MIN_VARIANCE_THRESHOLD (from _validation)

---

## Function Signatures (Contracts)

### `CovarianceCalculator.__init__(min_observations, shrinkage)`
**Pre:** min_observations >= 2, shrinkage in [0, 1] or None
**Post:** Calculator initialized with configuration
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `calculate_sample_covariance(returns) -> CovarianceResult`
**Pre:** returns is dict symbol -> List[Decimal], at least 2 assets, min_observations per asset
**Post:** Returns CovarianceResult with sample covariance (ddof=1)
**Raises:** ValueError if insufficient data or assets
**Retry:** No
**Side Effects:** None

**Algorithm:**
1. Validate at least 2 assets
2. Sanitize returns (remove NaN, zero variance)
3. Calculate means
4. Calculate sample covariance: cov = (X - μ)'(X - μ) / (n - 1)
5. Sanitize covariance (remove NaN, enforce PSD)
6. Calculate correlation matrix

### `calculate_shrinkage_covariance(returns, shrinkage) -> CovarianceResult`
**Pre:** returns valid, shrinkage in [0, 1] or None
**Post:** Returns CovarianceResult with shrunk covariance
**Raises:** ValueError if insufficient data or invalid shrinkage
**Retry:** No
**Side Effects:** None

**Shrinkage Formula:**
- Σ_shrunk = (1 - λ) * Σ_sample + λ * Σ_structured
- Σ_structured uses constant correlation model
- λ = shrinkage intensity (0 = sample, 1 = structured)

**Ledoit-Wolf Shrinkage:**
- Structured estimator: constant correlation matrix
- Shrinkage decreases with more observations and assets
- Formula: λ ≈ n_assets / n_observations

### `calculate_exponential_covariance(returns, span) -> CovarianceResult`
**Pre:** returns valid, span > 0
**Post:** Returns CovarianceResult with EWMA covariance
**Raises:** ValueError if insufficient data or invalid span
**Retry:** No
**Side Effects:** None

**EWMA Formula:**
- α = 2 / (span + 1)
- weights[i] = (1 - α)^(n_obs - 1 - i)
- μ_weighted = Σ(weights[i] * returns[i])
- cov_weighted = Σ(weights[i] * (x[i] - μ) * (y[j] - μ))

**Adaptive Benefits:**
- More weight to recent observations
- Useful for time-varying correlations
- Default span = 60 (~quarterly)

### `get_positive_semidefinite_covariance(cov_matrix) -> np.ndarray`
**Pre:** cov_matrix is square matrix
**Post:** Returns PSD covariance matrix
**Raises:** None
**Retry:** No
**Side Effects:** None

**PSD Enforcement:**
- Eigenvalue decomposition: Σ = QΛQ'
- Set negative eigenvalues to zero: Λ* = max(Λ, 0)
- Reconstruct: Σ_psd = QΛ*Q'
- Ensures matrix is positive semidefinite

### `get_risk_contribution(weights, cov_matrix) -> np.ndarray`
**Pre:** weights sum to 1.0, cov_matrix is PSD
**Post:** Returns risk contribution for each asset
**Raises:** None
**Retry:** No
**Side Effects:** None (logs warning if volatility near zero)

**Formula:**
- σ_p = sqrt(w'Σw) (portfolio volatility)
- MC_i = (Σw)_i (marginal contribution)
- RC_i = w_i * MC_i / σ_p (component contribution)
- Σ(RC_i) = σ_p (sum to portfolio volatility)

### `get_effective_number_bets(weights, cov_matrix) -> float`
**Pre:** weights sum to 1.0, cov_matrix valid
**Post:** Returns effective number of uncorrelated bets
**Raises:** None
**Retry:** No
**Side Effects:** None

**Formula:**
- N* = (w'Σw) / σ²_avg
- Measures diversification
- Higher = more diversified
- N assets with correlation ρ: N* ≈ N / (1 + (N-1)ρ)

---

## Acceptance Criteria
- [ ] Sample covariance uses ddof=1 (unbiased estimator)
- [ ] Covariance matrix is positive semidefinite
- [ ] Correlation matrix has 1.0 on diagonal
- [ ] Correlation values in [-1, 1]
- [ ] Standard deviations > 0
- [ ] NaN values removed from returns
- [ ] Zero variance assets removed with warning
- [ ] Shrinkage combines sample and structured estimators
- [ ] EWMA gives more weight to recent observations
- [ ] Risk contributions sum to portfolio volatility
- [ ] Effective number of bets >= 1
- [ ] At least 2 assets required
- [ ] At least min_observations required
- [ ] All calculations use float (not Decimal) for numerical efficiency

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance matrix PSD validation | ✅ OK - Enforced in calculation |
| TRD-007 | BASE_RULES | Document TRADING_DAYS = 252 | ✅ OK - MIN_OBSERVATIONS = 252 |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - No infrastructure imports |
| TYP-001 | BASE_RULES | Type hints | ✅ OK - Full type coverage |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError for invalid inputs |
| LOG-004 | BASE_RULES | Log warnings | ✅ OK - Logs NaN, zero variance, PSD issues |
| LOG-003 | BASE_RULES | Appropriate log levels | ✅ OK - warning for issues, debug for info |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Only covariance calculations |

### Covariance Estimation Rules (Ledoit-Wolf, López de Prado)

| Rule ID | Rule | Priority | Status |
|---------|------|----------|--------|
| COV-001 | Covariance matrix must be positive semidefinite | **P0** | ✅ OK |
| COV-002 | Use unbiased estimator (ddof=1) for sample covariance | **P0** | ✅ OK |
| COV-003 | Remove NaN values from returns | **P0** | ✅ OK |
| COV-004 | Remove zero variance assets | **P1** | ✅ OK |
| COV-005 | Shrinkage reduces estimation error | **P1** | ✅ OK |
| COV-006 | EWMA adapts to recent data | **P2** | ✅ OK |
| COV-007 | Minimum 252 observations (1 year) | **P1** | ✅ OK |
| COV-008 | Correlation matrix diagonal = 1.0 | **P0** | ✅ OK |

---

## Dependencies
- **External:**
  - numpy (np) - for matrix operations
  - logging - for warnings
  - dataclasses, decimal, typing - for type hints
- **Internal:**
  - app.domain.services.portfolio_optimization._validation
    - TRADING_DAYS
    - is_positive_semidefinite
    - enforce_positive_semidefinite
    - MIN_VARIANCE_THRESHOLD

---

## Required Tests
- **test_covariance_calculator.py:**
  - **Success paths:**
    - test_calculate_sample_covariance_valid: Returns valid CovarianceResult
    - test_covariance_matrix_psd: Matrix is positive semidefinite
    - test_correlation_diagonal_one: Diagonal entries = 1.0
    - test_correlation_in_range: All correlations in [-1, 1]
    - test_standard_deviations_positive: All std devs > 0
    - test_shrinkage_covariance_combines_estimators: Shrunk between sample and structured
    - test_ewma_covariance_weights_recent: Recent observations have higher weight
    - test_get_covariance_by_symbol: Returns correct covariance
    - test_get_correlation_by_symbol: Returns correct correlation
    - test_get_std_dev_by_symbol: Returns correct std dev
    - test_risk_contribution_sum_to_volatility: Sum of RC = portfolio volatility
    - test_effective_number_bets_diversified: Uncorrelated assets have high N*
    - test_effective_number_bets_correlated: Correlated assets have low N*
  - **Error paths:**
    - test_insufficient_observations_raises: ValueError for < min_observations
    - test_insufficient_assets_raises: ValueError for < 2 assets
    - test_invalid_shrinkage_raises: ValueError for shrinkage not in [0, 1]
    - test_invalid_span_raises: ValueError for span <= 0
    - test_nan_returns_removed_with_warning: NaN returns skipped
    - test_zero_variance_removed_with_warning: Zero variance assets skipped
  - **Edge cases:**
    - test_perfect_correlation: Correlation = 1.0 handled
    - test_zero_correlation: Correlation = 0.0 handled
    - test_negative_correlation: Correlation = -1.0 handled
    - test_two_assets_minimum: Works with exactly 2 assets
    - test_shrinkage_zero_sample_only: shrinkage=0 returns sample covariance
    - test_shrinkage_one_structured_only: shrinkage=1 returns structured covariance
    - test_ewma_span_one_naive: span=1 gives equal weights
    - test_psd_enforcement_negative_eigenvalues: Negative eigenvalues set to zero
    - test_risk_contribution_zero_volatility: Handles zero volatility gracefully
    - test_effective_number_bets_zero_variance: Handles zero variance

---

## Notes
**Critical Implementation Details:**
- Sample covariance uses ddof=1 for unbiased estimation
- Covariance sanitized to ensure PSD (eigenvalue adjustment)
- NaN and zero variance assets removed with warnings
- Shrinkage combines sample covariance with structured estimator
- Ledoit-Wolf shrinkage: λ ≈ n_assets / n_observations
- EWMA uses exponential decay: α = 2 / (span + 1)
- Risk contribution measures component contribution to volatility
- Effective number of bets measures true diversification

**Mathematical Foundation:**
- Sample covariance: Σ = (X - μ)'(X - μ) / (n - 1)
- Correlation: ρ_ij = Σ_ij / (σ_i * σ_j)
- Shrinkage: Σ_shrunk = (1 - λ) * Σ_sample + λ * Σ_structured
- EWMA: weights decay exponentially with time
- Risk contribution: RC_i = w_i * (Σw)_i / σ_p

**Validation and Sanitization:**
- Minimum 252 observations (1 trading year)
- At least 2 valid assets after sanitization
- PSD enforcement via eigenvalue decomposition
- NaN replacement with zeros
- Zero variance detection and removal

**Usage Recommendations:**
- Use sample covariance for large datasets (n > 500)
- Use shrinkage for noisy datasets (n < 500)
- Use EWMA for time-varying correlations
- Always check PSD before optimization
- Monitor effective number of bets for diversification
