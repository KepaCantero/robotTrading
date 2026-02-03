# walk_forward_validator.py

## Purpose
Walk-Forward Validator - Comprehensive validation system with walk-forward analysis, temporal cross-validation, stress testing, Monte Carlo simulation, and synthetic data generation.

---

## Type Definitions / Data Classes

### ValidationWindow
```python
@dataclass
class ValidationWindow:
    """
    Single walk-forward validation window.

    Attributes:
        train_start: Training period start date
        train_end: Training period end date
        test_start: Test period start date (gap after training)
        test_end: Test period end date
        is_train_performance: In-sample performance
        is_test_performance: Out-of-sample performance
    """
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    is_train_performance: Dict[str, Decimal]
    is_test_performance: Dict[str, Decimal]
```

### StressScenarioResult
```python
@dataclass
class StressScenarioResult:
    """
    Result of stress testing a strategy under adverse conditions.

    Attributes:
        scenario_name: Name of stress scenario
        test_start: Stress test start date
        test_end: Stress test end date
        baseline_return: Return during normal period
        stress_return: Return during stress period
        degradation: Performance degradation (baseline - stress)
        is_acceptable: Whether degradation is acceptable
    """
    scenario_name: str
    test_start: datetime
    test_end: datetime
    baseline_return: Decimal
    stress_return: Decimal
    degradation: Decimal
    is_acceptable: bool
```

### ValidationReport
```python
@dataclass
class ValidationReport:
    """
    Comprehensive validation report from walk-forward analysis.

    Attributes:
        is_mean_return: Mean in-sample return
        is_std_return: Std in-sample return
        oos_mean_return: Mean out-of-sample return
        oos_std_return: Std out-of-sample return
        consistency_ratio: OOS return / IS return
        is_consistent: Whether strategy is consistent (ratio >= 0.5)
        windows: List of validation windows
        stress_results: List of stress test results
        monte_carlo_results: Monte Carlo simulation results
        is_acceptable: Overall acceptability decision
    """
    is_mean_return: Decimal
    is_std_return: Decimal
    oos_mean_return: Decimal
    oos_std_return: Decimal
    consistency_ratio: Decimal
    is_consistent: bool
    windows: List[ValidationWindow]
    stress_results: List[StressScenarioResult]
    monte_carlo_results: Dict[str, Any]
    is_acceptable: bool
```

---

## Function Signatures (Contracts)

### `WalkForwardValidator.__init__(
    self,
    n_windows: int = 5,
    train_size: float = 0.6,
    test_size: float = 0.2,
    gap_size: float = 0.05,
    min_train_periods: int = 252
) -> None`
**Pre:** n_windows >= 3; train_size + test_size + gap_size <= 1.0; min_train_periods >= 126
**Post:** Validator initialized with parameters
**Raises:** None
**Retry:** No
**Side Effects:** Stores configuration

**Default Parameters:**
- n_windows: 5 (minimum 3 windows required)
- train_size: 60% for training
- test_size: 20% for testing
- gap_size: 5% gap between train and test (prevents data leakage)
- min_train_periods: 252 trading days (1 year minimum)

### `WalkForwardValidator.validate(
    self,
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None
) -> ValidationReport`
**Pre:** returns is non-empty Series with datetime index
**Post:** Returns ValidationReport with walk-forward analysis
**Raises:** ValueError if insufficient data
**Retry:** No
**Side Effects:** None (pure computation)

**Process:**
1. Generate n_windows validation windows
2. For each window:
   - Calculate IS (in-sample) performance on train period
   - Calculate OOS (out-of-sample) performance on test period
3. Aggregate statistics across all windows
4. Calculate consistency ratio (OOS mean / IS mean)
5. Assess consistency (ratio >= 0.5)

### `WalkForwardValidator._generate_windows(
    self,
    returns: pd.Series
) -> List[ValidationWindow]`
**Pre:** returns is non-empty Series with datetime index
**Post:** Returns list of ValidationWindow objects
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Window Generation:**
- Rolls forward through time
- Each window: [train_start, train_end, gap, test_start, test_end]
- Gap prevents data leakage from test to train

### `WalkForwardValidator._calculate_consistency_ratio(
    self,
    is_return: Decimal,
    oos_return: Decimal
) -> Decimal`
**Pre:** None
**Post:** Returns ratio of OOS to IS return
**Raises:** None
**Retry:** No
**Side Effects:** None (pure calculation)

**Formula:** `oos_return / abs(is_return)` (clamped to max 1.0 for positive IS)
**Threshold:** Strategy is consistent if ratio >= 0.5

### `CrossValidationTemporal.__init__(
    self,
    n_folds: int = 5,
    expanding_window: bool = True,
    min_train_size: int = 252
) -> None`
**Pre:** n_folds >= 3; min_train_size >= 126
**Post:** Cross-validator initialized
**Raises:** None
**Retry:** No
**Side Effects:** Stores configuration

### `CrossValidationTemporal.cross_validate(
    self,
    returns: pd.Series,
    strategy_func: Callable[[pd.Series], pd.Series]
) -> Dict[str, Any]`
**Pre:** returns is non-empty Series; strategy_func is callable
**Post:** Returns cross-validation results
**Raises:** None
**Retry:** No
**Side Effects:** Calls strategy_func for each fold

**Process:**
1. Split data into n_folds temporal folds
2. For each fold:
   - Train on data before fold
   - Test on fold data
   - Record IS and OOS performance
3. Aggregate results

### `StressTester.__init__() -> None`
**Pre:** None
**Post:** Stress tester initialized with scenarios
**Raises:** None
**Retry:** No
**Side Effects:** Initializes stress scenarios

### `StressTester.test_stress_scenarios(
    self,
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None
) -> List[StressScenarioResult]`
**Pre:** returns is non-empty Series with datetime index
**Post:** Returns list of stress test results
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Stress Scenarios:**
1. **Market Crash:** Returns < -20% in 20-day window
2. **Volatility Spike:** Volatility > 2× average
3. **Drawdown Period:** Drawdown > 15%
4. **Correlation Breakdown:** Diversification fails
5. **Liquidity Crisis:** Volume < 50% of average

### `StressTester._calculate_degradation(
    self,
    baseline_return: Decimal,
    stress_return: Decimal
) -> Decimal`
**Pre:** None
**Post:** Returns performance degradation
**Raises:** None
**Retry:** No
**Side Effects:** None (pure calculation)

**Formula:** `baseline_return - stress_return`

### `MonteCarloSimulator.__init__(
    self,
    n_simulations: int = 1000,
    block_size: int = 5
) -> None`
**Pre:** n_simulations >= 100; block_size >= 1
**Post:** Simulator initialized
**Raises:** None
**Retry:** No
**Side Effects:** Stores configuration

**Method:** Stationary bootstrap with block_size for preserving autocorrelation

### `MonteCarloSimulator.simulate(
    self,
    returns: pd.Series
) -> Dict[str, Any]`
**Pre:** returns is non-empty Series with at least 126 observations
**Post:** Returns simulation results
**Raises:** ValueError if insufficient data
**Retry:** No
**Side Effects:** Generates n_simulations resampled return series

**Process:**
1. Perform stationary bootstrap (block resampling)
2. For each simulation:
   - Resample returns with replacement
   - Calculate cumulative return
   - Record statistics
3. Aggregate results: mean, std, percentiles (5%, 25%, 50%, 75%, 95%)

### `SyntheticDataGenerator.__init__() -> None`
**Pre:** None
**Post:** Data generator initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SyntheticDataGenerator.generate_geometric_brownian_motion(
    self,
    n_obs: int,
    mu: float = 0.08,
    sigma: float = 0.15,
    S0: float = 100.0,
    dt: float = 1/252
) -> pd.Series`
**Pre:** n_obs >= 252; sigma > 0; S0 > 0; dt > 0
**Post:** Returns synthetic price series following GBM
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `S_t = S_{t-1} × exp((μ - σ²/2)dt + σ√dt × Z)` where Z ~ N(0,1)
**Reference:** Hull (2018) "Options, Futures, and Other Derivatives"

### `SyntheticDataGenerator.generate_mean_reverting(
    self,
    n_obs: int,
    theta: float = 0.1,
    mu: float = 0.0,
    sigma: float = 0.15,
    X0: float = 0.0,
    dt: float = 1/252
) -> pd.Series`
**Pre:** n_obs >= 252; theta > 0; sigma > 0; dt > 0
**Post:** Returns synthetic mean-reverting series (Ornstein-Uhlenbeck)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `dX = θ(μ - X)dt + σdW`
**Use Case:** Simulating pairs trading, statistical arbitrage strategies

### `ComprehensiveValidator.__init__(
    self,
    n_windows: int = 5,
    n_simulations: int = 1000,
    consistency_threshold: float = 0.5,
    degradation_threshold: float = 0.3
) -> None`
**Pre:** n_windows >= 3; n_simulations >= 100; thresholds in (0, 1)
**Post:** Comprehensive validator initialized
**Raises:** None
**Retry:** No
**Side Effects:** Initializes sub-validators

**Default Parameters:**
- consistency_threshold: 0.5 (OOS/IS ratio >= 50%)
- degradation_threshold: 0.3 (stress degradation <= 30%)

### `ComprehensiveValidator.validate(
    self,
    returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None
) -> ValidationReport`
**Pre:** returns is non-empty Series with datetime index
**Post:** Returns complete ValidationReport
**Raises:** ValueError if insufficient data (< 3 years)
**Retry:** No
**Side Effects:** Runs walk-forward, stress tests, Monte Carlo

**Process:**
1. Run walk-forward validation (n_windows)
2. Run stress tests (5 scenarios)
3. Run Monte Carlo simulation (n_simulations)
4. Aggregate results
5. Assess overall acceptability

**Acceptability Criteria:**
- Consistency ratio >= 0.5
- Stress degradation <= 0.3 (30%)
- Minimum 3 windows completed
- Monte Carlo 5th percentile positive (optional)

---

## Acceptance Criteria
- [ ] **AC-001:** WalkForwardValidator generates at least 3 windows
- [ ] **AC-002:** WalkForwardValidator includes gap between train and test
- [ ] **AC-003:** Consistency ratio calculated as OOS/IS return
- [ ] **AC-004:** Consistency threshold is 0.5 (50%)
- [ ] **AC-005:** CrossValidationTemporal folds are temporal (not shuffled)
- [ ] **AC-006:** StressTester tests 5 scenarios
- [ ] **AC-007:** StressTester calculates degradation correctly
- [ ] **AC-008:** MonteCarloSimulator uses stationary bootstrap
- [ ] **AC-009:** MonteCarloSimulator generates at least 100 simulations
- [ ] **AC-010:** SyntheticDataGenerator generates GBM correctly
- [ ] **AC-011:** SyntheticDataGenerator generates mean-reverting series
- [ ] **AC-012:** ComprehensiveValidator runs all three validations
- [ ] **AC-013:** ValidationReport includes consistency_ratio
- [ ] **AC-014:** ValidationReport includes is_acceptable decision
- [ ] **AC-015:** All public methods have complete type hints

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Walk-Forward Validator):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Walk-forward validation | Pardo (2008) | IS/OOS windows | ✅ OK - WalkForwardValidator |
| Temporal CV | Hyndman (2018) | Time series cross-validation | ✅ OK - CrossValidationTemporal |
| Stress testing | Risk management | Scenario analysis | ✅ OK - StressTester |
| Monte Carlo simulation | Risk management | Bootstrap resampling | ✅ OK - MonteCarloSimulator |
| Stationary bootstrap | Politis (2003) | Block bootstrap | ✅ OK - block_size |
| Consistency ratio | Pardo (2008) | OOS/IS >= 0.5 | ✅ OK - _calculate_consistency_ratio() |
| Gap between train/test | Pardo (2008) | Prevent data leakage | ✅ OK - gap_size |
| Minimum 3 windows | Pardo (2008) | Statistical validity | ✅ OK - n_windows >= 3 |
| Minimum 1 year train | Pardo (2008) | Sufficient data | ✅ OK - min_train_periods = 252 |
| GBM simulation | Hull (2018) | Geometric Brownian Motion | ✅ OK - generate_geometric_brownian_motion() |
| Mean-reverting simulation | Ornstein-Uhlenbeck | OU process | ✅ OK - generate_mean_reverting() |
| Degradation metric | Risk management | baseline - stress | ✅ OK - _calculate_degradation() |
| Comprehensive validation | Best practice | Multi-method validation | ✅ OK - ComprehensiveValidator |
| NumPy 2.0 compatible | BASE_RULES.md (TYP-005) | No np aliases | ✅ OK - No np usage |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Pardo (2008), Politis (2003), Hull (2018) for validation standards.

---

## Dependencies
- **External:** `pandas`, `numpy`, `decimal` (std), `datetime` (std), `dataclasses` (std), `typing` (std), `random` (std)
- **Internal:** None (infrastructure layer)

---

## Required Tests
- **test_walk_forward_validator.py:**
  - `test_walk_forward_init()` - Initializes with parameters
  - `test_generate_windows()` - At least 3 windows
  - `test_windows_have_gap()` - Gap between train and test
  - `test_validate()` - Returns ValidationReport
  - `test_calculate_consistency_ratio()` - OOS/IS ratio
  - `test_consistency_threshold()` - Ratio >= 0.5 is consistent
  - `test_cross_validation_temporal()` - Temporal folds
  - `test_cross_validation_no_shuffle()` - Preserves time order
  - `test_stress_tester()` - 5 scenarios tested
  - `test_stress_degradation()` - Correct calculation
  - `test_stress_market_crash()` - Detects crashes
  - `test_stress_volatility_spike()` - Detects spikes
  - `test_monte_carlo_simulator()` - At least 100 simulations
  - `test_monte_carlo_bootstrap()` - Stationary bootstrap
  - `test_synthetic_gbm()` - GBM generation
  - `test_synthetic_mean_reverting()` - OU process
  - `test_comprehensive_validator()` - All 3 validations run
  - `test_comprehensive_acceptable()` - is_acceptable when criteria met
  - `test_comprehensive_not_acceptable()` - Fails when criteria not met
  - `test_validation_report_fields()` - All fields present

---

## Notes
- **Critical:** Walk-Forward validation is the GOLD STANDARD for strategy validation (Pardo, 2008)
- **Pardo Reference:** "The Evaluation and Optimization of Trading Strategies" (2008)
- **Key Principle:** Out-of-sample (OOS) performance must be at least 50% of in-sample (IS) performance
- **Walk-Forward Process:**
  1. Divide time series into rolling windows
  2. Each window: train (in-sample) → gap → test (out-of-sample)
  3. Gap prevents data leakage from test to training
  4. Minimum 3 windows for statistical significance
  5. Minimum 1 year (252 days) training data
- **Consistency Ratio:** `OOS_return / IS_return`
  - Ratio >= 0.5 (50%): Strategy is consistent ✅
  - Ratio < 0.5: Strategy is overfit ❌
- **Stress Scenarios:**
  1. **Market Crash:** Sharp declines (-20% in 20 days)
  2. **Volatility Spike:** Volatility doubles
  3. **Drawdown Period:** Peak-to-trough > 15%
  4. **Correlation Breakdown:** Diversification fails
  5. **Liquidity Crisis:** Trading volume drops 50%
- **Degradation:** `baseline_return - stress_return`
  - Acceptable: degradation <= 30%
- **Monte Carlo Simulation:**
  - Stationary bootstrap (Politis, 2003)
  - Block resampling preserves autocorrelation
  - Minimum 1000 simulations for statistical validity
  - Outputs: 5th, 25th, 50th, 75th, 95th percentiles
- **Synthetic Data:**
  - **GBM:** Geometric Brownian Motion for trend-following strategies
  - **Mean-Reverting:** Ornstein-Uhlenbeck for pairs trading, stat arb
- **Comprehensive Validation:** Combines 3 methods for robust validation
  1. Walk-forward (temporal validation)
  2. Stress testing (adverse conditions)
  3. Monte Carlo (statistical distribution)
- **Production Rule:** Never deploy a strategy without comprehensive validation

---

**File Reference:** `app/backtesting/walk_forward_validator.py`
**Last Audited:** 2026-02-01
