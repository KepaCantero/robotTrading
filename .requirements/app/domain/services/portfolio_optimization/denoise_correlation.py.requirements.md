# denoise_correlation.py

## Purpose
Implements López de Prado's correlation matrix de-noising using Random Matrix Theory (RMT) to remove noise from correlation matrices per "Machine Learning for Asset Managers" (2019).

---

## Type Definitions / Data Classes

### DenoisedResult (dataclass)
```python
original_corr: np.ndarray                # Original correlation matrix (N, N)
denoised_corr: np.ndarray                # De-noised correlation matrix (N, N)
denoised_cov: Optional[np.ndarray]       # De-noised covariance matrix (N, N)
eigenvalues: np.ndarray                  # Eigenvalues of original matrix (N,)
denoised_eigenvalues: np.ndarray         # Eigenvalues after de-noising (N,)
symbols: List[str]                       # Asset symbols/tickers
```

**Properties:**
- noise_ratio: Ratio of noise eigenvalues to signal eigenvalues

### CorrelationDenoiser (class)
```python
_method: str                             # De-noising method
_min_obs_ratio: float                    # Minimum T/n ratio for RMT validity
```

**Methods:**
- denoise_correlation()
- denoise_correlation_with_std()
- fit_kde()
- get_number_of_signal_factors()
- shrink_to_constant_correlation()

---

## Function Signatures (Contracts)

### `CorrelationDenoiser.__init__(method, min_observation_ratio)`
**Pre:** method in ['spectral', 'shrinkage', 'constant_corr'], min_observation_ratio >= 2.0
**Post:** Denoiser initialized with validated parameters
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `denoise_correlation(corr_matrix, n_observations, symbols) -> DenoisedResult`
**Pre:** corr_matrix is (N, N) square, n_observations >= min_obs_ratio * N
**Post:** Returns DenoisedResult with de-noised correlation matrix
**Raises:** ValueError if matrix invalid or observations insufficient
**Retry:** No
**Side Effects:** Logs de-noising process

### `denoise_correlation_with_std(cov_matrix, n_observations, symbols) -> DenoisedResult`
**Pre:** cov_matrix is (N, N) PSD, no zero-variance assets
**Post:** Returns DenoisedResult with de-noised covariance matrix
**Raises:** ValueError if matrix invalid or has zero variance
**Retry:** No
**Side Effects:** Logs de-noising process

### `_calculate_max_random_eigenvalue(q, n_assets) -> float`
**Pre:** q > 0 (T/n ratio), n_assets > 0
**Post:** Returns Marchenko-Pastur upper bound: σ * (1 + 1/√q)²
**Raises:** None
**Retry:** No
**Side Effects:** None

### `fit_kde(eigenvalues) -> Tuple[NDArray, NDArray]`
**Pre:** eigenvalues length >= 2
**Post:** Returns (eigenvalue_grid, pdf_values) for visualization
**Raises:** ValueError if insufficient eigenvalues, ImportError if scipy unavailable
**Retry:** No
**Side Effects:** None

### `get_number_of_signal_factors(corr_matrix, n_observations) -> int`
**Pre:** corr_matrix is (N, N) square
**Post:** Returns count of eigenvalues > max_random_eigenvalue
**Raises:** ValueError if matrix not square
**Retry:** No
**Side Effects:** None

### `shrink_to_constant_correlation(corr_matrix, shrinkage) -> NDArray`
**Pre:** corr_matrix is (N, N)
**Post:** Returns shrunk correlation matrix
**Raises:** ValueError if shrinkage not in [0, 1]
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] RMT validity check: T/n >= 2.0 (DEFAULT_MIN_OBSERVATION_RATIO)
- [ ] Marchenko-Pastur upper bound: λ_max = σ * (1 + 1/√q)²
- [ ] Signal eigenvalues: λ > λ_max
- [ ] Noise eigenvalues replaced with average: λ_noise = mean(λ_noise)
- [ ] De-noised matrix reconstructed: E' = V * diag(λ') * V.T
- [ ] Diagonal set to exactly 1.0 for correlation matrix
- [ ] Result is symmetric: (M + M.T) / 2
- [ ] Result is PSD: diagonal >= 1.0
- [ ] Complex eigenvalues handled (use real parts)
- [ ] Covariance de-noising preserves standard deviations
- [ ] Shrinkage to constant correlation available
- [ ] KDE fitting for visualization
- [ ] Signal factor counting
- [ ] Structured logging (LOG-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance PSD validation | ✅ OK - Assumes PSD input, ensures PSD output |
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - No infrastructure imports |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - All steps logged with context |
| TYP-001 | BASE_RULES | Type hints | ✅ OK - Full type coverage |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Each method has single purpose |
| CC-007 | BASE_RULES | Small functions | ✅ OK - Most methods < 30 lines |

---

## Dependencies
- **External:** numpy, scipy (optimize, spatial, stats), logging
- **Internal:** app.domain.services.portfolio_optimization._validation

---

## Required Tests
- **test_denoise_correlation.py:**
  - Correlation to distance conversion
  - Max random eigenvalue calculation (Marchenko-Pastur)
  - Min random eigenvalue calculation
  - Signal vs noise eigenvalue separation
  - Noise eigenvalue replacement with average
  - De-noised matrix reconstruction
  - Diagonal set to 1.0
  - Symmetry enforcement
  - PSD enforcement
  - Complex eigenvalue handling
  - Covariance de-noising with std preservation
  - Zero variance asset detection
  - Insufficient observations error
  - KDE fitting
  - Signal factor counting
  - Constant correlation shrinkage
  - DenoisedResult.noise_ratio property
  - Configuration validation

---

## Notes
RMT de-noising separates signal from noise by identifying eigenvalues that exceed theoretical random matrix bounds (Marchenko-Pastur law). Critical for robust portfolio optimization when N (assets) approaches T (observations).
