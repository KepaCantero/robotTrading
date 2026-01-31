# denoise_correlation.py.requirements.md

## Purpose
Implements López de Prado's correlation matrix de-noising using Random Matrix Theory (RMT) to remove noise from correlation matrices for robust portfolio optimization.

---

## Type Definitions / Data Classes

### DenoisedResult Class
```python
@dataclass
class DenoisedResult:
    original_corr: np.ndarray         # REQUIRED - Original correlation matrix (N, N)
    denoised_corr: np.ndarray         # REQUIRED - De-noised correlation matrix (N, N)
    denoised_cov: np.ndarray          # OPTIONAL - De-noised covariance matrix (N, N), may be None
    eigenvalues: np.ndarray           # REQUIRED - Eigenvalues of original matrix (N,)
    denoised_eigenvalues: np.ndarray  # REQUIRED - Eigenvalues after de-noising (N,)
    symbols: List[str]                # REQUIRED - Asset symbols/tickers
```

**Validation Rules:**
- `original_corr`, `denoised_corr`, `eigenvalues`, `denoised_eigenvalues` must have same shape (N, N) or (N,)
- `denoised_cov` may be None if only correlation de-noising performed
- All eigenvalues must be real (not complex)
- Diagonal of correlation matrices must equal 1.0
- Matrices must be symmetric

**Property Methods:**
- `noise_ratio: float` - Ratio of noise eigenvalues to total eigenvalues (0 to 1)

---

## Function Signatures (Contracts)

### `CorrelationDenoiser.__init__(method: str, min_observation_ratio: float) -> None`
**Pre:** method must be "spectral", "shrinkage", or "constant_corr"; min_observation_ratio >= 2.0
**Post:** CorrelationDenoiser instance initialized with validated parameters
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** None

### `denoise_correlation(corr_matrix: np.ndarray, n_observations: int, symbols: Optional[List[str]]) -> DenoisedResult`
**Pre:** corr_matrix is symmetric (N, N) with diagonal = 1.0; n_observations >= min_observation_ratio
**Post:** Returns DenoisedResult with noise eigenvalues replaced by their average
**Raises:** ValueError if matrix invalid or observations insufficient
**Retry:** No
**Side Effects:** None (pure function)

### `denoise_correlation_with_std(cov_matrix: np.ndarray, n_observations: int, symbols: Optional[List[str]]) -> DenoisedResult`
**Pre:** cov_matrix is positive semi-definite (N, N); n_observations >= min_observation_ratio
**Post:** Returns DenoisedResult with denoised covariance matrix
**Raises:** ValueError if matrix invalid or cannot convert to correlation
**Retry:** No
**Side Effects:** None

### `_calculate_max_random_eigenvalue(q: float, n_assets: int) -> float`
**Pre:** q > 0 (T/n ratio), n_assets >= 2
**Post:** Returns maximum eigenvalue threshold for random component (Marchenko-Pastur)
**Raises:** ValueError if q <= 0
**Retry:** No
**Side Effects:** None

### `_calculate_min_random_eigenvalue(q: float) -> float`
**Pre:** q > 0
**Post:** Returns minimum eigenvalue threshold for random component
**Raises:** ValueError if q <= 0
**Retry:** No
**Side Effects:** None

### `fit_kde(eigenvalues: np.ndarray) -> Tuple[np.ndarray, np.ndarray]`
**Pre:** eigenvalues is 1D array with length >= 2
**Post:** Returns (eigenvalue_grid, pdf_values) for visualization
**Raises:** ImportError if scipy not available
**Retry:** No
**Side Effects:** None

### `get_number_of_signal_factors(corr_matrix: np.ndarray, n_observations: int) -> int`
**Pre:** corr_matrix is valid correlation matrix; n_observations > 0
**Post:** Returns count of eigenvalues above random threshold
**Raises:** ValueError if inputs invalid
**Retry:** No
**Side Effects:** None

### `shrink_to_constant_correlation(corr_matrix: np.ndarray, shrinkage: Optional[float]) -> np.ndarray`
**Pre:** corr_matrix is valid correlation matrix; shrinkage in [0, 1] if provided
**Post:** Returns shrunk correlation matrix (weighted average with constant correlation)
**Raises:** ValueError if matrix invalid
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-RMT-001: De-noised correlation matrix has diagonal elements exactly 1.0
- [ ] AC-RMT-002: De-noised correlation matrix is symmetric (difference < 1e-10)
- [ ] AC-RMT-003: Number of signal factors <= number of assets
- [ ] AC-RMT-004: Noise ratio in [0, 1] (0 = all signal, 1 = all noise)
- [ ] AC-RMT-005: Marchenko-Pastur lambda_max > 0 for valid q factor
- [ ] AC-RMT-006: All eigenvalues are real (not complex)
- [ ] AC-RMT-007: De-noised eigenvalues >= 0 (no negative eigenvalues)
- [ ] AC-RMT-008: shrink_to_constant_correlation preserves diagonal = 1.0

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Covariance matrix must be positive semi-definite | ✅ OK - _is_positive_semi_definite check |
| TRD-007 | BASE_RULES | Document TRADING_DAYS = 252 for annualization | ⚠️ NOT APPLIED - Not relevant (no annualization) |
| ARCH-004 | BASE_RULES | Functions < 20 lines (ideally) | ✅ OK - Most functions compact |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ❌ GAP - No logging in current implementation |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - Uses None for optional mutable |
| TST-005 | BASE_RULES | Coverage > 80% | ⚠️ NOT APPLIED - Tests not yet written |

### López de Prado RMT-Specific Rules:

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| RMT-001 | T/n ratio >= 2 for RMT validity | ✅ OK - min_observation_ratio=2.0 enforced |
| RMT-002 | Use Marchenko-Pastur law for eigenvalue threshold | ✅ OK - _calculate_max_random_eigenvalue |
| RMT-003 | Replace noise eigenvalues with their average | ✅ OK - Lines 118-121 |
| RMT-004 | Ensure diagonal = 1.0 after reconstruction | ✅ OK - Line 129 |
| RMT-005 | Symmetrize matrix after reconstruction | ✅ OK - Line 132 |
| RMT-006 | Signal eigenvalues > max_random_eigenvalue | ✅ OK - Line 114 |

---

## Dependencies
- **External:** numpy, scipy (optimize, spatial.distance)
- **Internal:** None (standalone domain service)

---

## Required Tests
- **tests/domain/services/portfolio_optimization/test_denoise_correlation.py:**
  - Test denoise_correlation with valid correlation matrix
  - Test denoise_correlation_with_std converts to/from covariance
  - Test Marchenko-Pastur eigenvalue threshold calculation
  - Test signal vs noise eigenvalue separation
  - Test that diagonal remains 1.0 after de-noising
  - Test that matrix remains symmetric after de-noising
  - Test with edge case: all eigenvalues are noise (q factor very small)
  - Test with edge case: all eigenvalues are signal (perfect correlation)
  - Test shrink_to_constant_correlation with various shrinkage values
  - Test get_number_of_signal_factors returns correct count
  - Test fit_kde returns valid PDF for visualization
  - Test error handling: invalid correlation matrix (non-symmetric)
  - Test error handling: insufficient observations (n < min_observation_ratio)
  - Test noise_ratio property calculation

---

## Notes
- López de Prado's RMT method is critical for robust portfolio optimization
- Marchenko-Pastur law requires T (observations) >= 2n (assets) for validity
- The q factor (T/n) controls the eigenvalue threshold; smaller q = stricter threshold
- De-noising is most beneficial when n_assets is large relative to n_observations
- Consider adding logging for production use (noise_ratio, signal_count, etc.)
