# robustness_tester.py

## Purpose
Robustness Tester for Professional Backtesting - Analyzes strategy robustness through parameter sensitivity analysis (±20% variation), stability maps (3D surfaces showing parameter performance), and start date sensitivity (12 different start dates) to identify whether a strategy is genuinely robust or overfitted.

---

## Type Definitions / Data Classes

### ParameterSensitivityResult
```python
@dataclass
class ParameterSensitivityResult:
    """Result of parameter sensitivity analysis."""
    parameter_name: str
    base_value: Any
    tested_values: List[Any]
    returns: List[float]               # Return for each parameter value
    sharpe_ratios: List[float]         # Sharpe for each parameter value
    max_drawdowns: List[float]         # Max DD for each parameter value

    # Sensitivity metrics
    return_std: float                  # Std dev of returns (lower = more robust)
    return_range: float                # Max - Min return
    sharpe_std: float                  # Std dev of Sharpe ratios

    # Stability assessment
    is_stable: bool                   # True if variation within acceptable bounds
    stability_score: float             # 0-100 score
```

### StabilityMapPoint
```python
@dataclass
class StabilityMapPoint:
    """Single point on stability map (3D surface)."""
    param1_value: float
    param2_value: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
```

### StabilityMapResult
```python
@dataclass
class StabilityMapResult:
    """Result of stability map generation (3D surface)."""
    param1_name: str
    param2_name: str
    param1_range: Tuple[float, float]  # (min, max)
    param2_range: Tuple[float, float]  # (min, max)
    points: List[StabilityMapPoint]

    # Stability metrics
    has_plateau: bool                  # True if stable plateau exists
    plateau_size: float                # Size of stable region as % of total
    best_region: Dict[str, Any]        # Best performing region

    # Visualization data (for 3D plotting)
    mesh_x: np.ndarray
    mesh_y: np.ndarray
    mesh_z_return: np.ndarray
    mesh_z_sharpe: np.ndarray
```

### StartDateSensitivityResult
```python
@dataclass
class StartDateSensitivityResult:
    """Result of start date sensitivity analysis (Req #14)."""
    start_dates: List[datetime]
    returns: List[float]
    sharpe_ratios: List[float]
    max_drawdowns: List[float]

    # Sensitivity metrics
    return_variation: float            # Std dev of returns across start dates
    return_range_pct: float            # (Max - Min) / Avg as percentage
    sharpe_variation: float

    # Robustness assessment (Req #14)
    is_robust: bool                    # True if CAGR variation < 20%
    robustness_score: float            # 0-100 score
```

### RobustnessReport
```python
@dataclass
class RobustnessReport:
    """Complete robustness analysis report."""
    strategy_name: str
    timestamp: datetime
    parameter_sensitivity: List[ParameterSensitivityResult]
    stability_maps: List[StabilityMapResult]
    start_date_sensitivity: StartDateSensitivityResult

    # Overall assessment
    overall_robustness_score: float    # 0-100
    is_robust: bool
    warnings: List[str]
    recommendations: List[str]
```

### RobustnessTester
```python
class RobustnessTester:
    """
    Robustness Testing System (Req #14 - HIGH PRIORITY).

    Tests strategy robustness through:
    1. Parameter sensitivity analysis (±20% variation)
    2. Stability Maps (3D surfaces showing parameter performance)
    3. Start date sensitivity (12 different start dates)

    A robust strategy should:
    - Have low sensitivity to parameter changes
    - Show a stable plateau in performance (not a single peak)
    - Perform consistently across different start dates
    """
```

---

## Function Signatures (Contracts)

### `RobustnessTester.__init__(
    parameter_variation_pct: float = 0.20,
    min_stability_score: float = 60.0,
    max_return_variation: float = 0.20,
    n_start_dates: int = 12,
) -> None`
**Pre:** parameter_variation_pct in (0, 1); min_stability_score in [0, 100]; max_return_variation in (0, 1); n_start_dates >= 1
**Post:** Tester initialized
**Raises:** None
**Retry:** No
**Side Effects:** Stores configuration

**Defaults (Req #14):**
- parameter_variation_pct: 20% (±0.20)
- min_stability_score: 60%
- max_return_variation: 20% (0.20)
- n_start_dates: 12 start dates

### `RobustnessTester.analyze_parameter_sensitivity(
    parameter_name: str,
    base_value: Any,
    param_type: str,
    run_backtest_fn: callable,
    n_steps: int = 5,
) -> ParameterSensitivityResult`
**Pre:** parameter_name non-empty; base_value valid; param_type in ["int", "float", "decimal"]; run_backtest_fn callable
**Post:** Returns ParameterSensitivityResult with sensitivity metrics
**Raises:** None (errors logged, returns 0 values)
**Retry:** No
**Side Effects:** Calls run_backtest_fn for each parameter value

**Variation Range (Req #14):** Base value ±20%

**Stability Assessment:**
- is_stable: return_std < (mean(abs(returns)) × 0.3)
- stability_score: max(0, 100 - (return_std × 100))

### `RobustnessTester.generate_stability_map(
    param1_name: str,
    param1_range: Tuple[float, float],
    param2_name: str,
    param2_range: Tuple[float, float],
    run_backtest_fn: callable,
    n_points_per_dim: int = 10,
) -> StabilityMapResult`
**Pre:** param names non-empty; ranges valid (min < max); run_backtest_fn callable
**Post:** Returns StabilityMapResult with 3D surface data
**Raises:** None (errors logged, skipped)
**Retry:** No
**Side Effects:** Calls run_backtest_fn for each combination (n² total)

**Process:**
1. Create grid of parameter combinations
2. Run backtest for each combination
3. Generate mesh for 3D plotting (cubic interpolation)
4. Detect stable plateau (not single peak)
5. Find best performing region

**Stable Plateau Detection:** >20% of points within 90% of max return

### `RobustnessTester.analyze_start_date_sensitivity(
    quotes: List[Quote],
    signals: List[Any],
    config: BacktestConfig,
    start_date_base: datetime,
    end_date: datetime,
    run_backtest_fn: callable,
) -> StartDateSensitivityResult`
**Pre:** quotes and signals non-empty; dates valid; run_backtest_fn callable
**Post:** Returns StartDateSensitivityResult with sensitivity metrics
**Raises:** None (errors logged, skipped)
**Retry:** No
**Side Effects:** Filters data by period, calls run_backtest_fn

**Start Dates (Req #14):** 12 different start dates (monthly intervals)

**Robustness Assessment (Req #14):** is_robust = (return_range_pct < 20%)

**Return Range Formula:** `(max_return - min_return) / abs(avg_return) × 100`

### `RobustnessTester._detect_stable_plateau(points: List[StabilityMapPoint]) -> bool`
**Pre:** points list
**Post:** Returns True if stable plateau exists
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Detection:** >20% of points within 90% of max return

### `RobustnessTester._calculate_plateau_size(points: List[StabilityMapPoint]) -> float`
**Pre:** points non-empty
**Post:** Returns plateau size as percentage of total
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Formula:** `(points within 90% of max / total points) × 100`

### `RobustnessTester._find_best_region(points: List[StabilityMapPoint]) -> Dict[str, Any]`
**Pre:** points non-empty
**Post:** Returns best region statistics
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Best Region:** Top 10% of points by Sharpe ratio

**Output:**
```python
{
    'avg_sharpe': float,
    'avg_return': float,
    'param1_center': float,
    'param2_center': float,
    'param1_std': float,
    'param2_std': float
}
```

### `RobustnessTester.generate_robustness_report(
    strategy_name: str,
    parameter_sensitivity: List[ParameterSensitivityResult],
    stability_maps: List[StabilityMapResult],
    start_date_sensitivity: StartDateSensitivityResult,
) -> RobustnessReport`
**Pre:** strategy_name non-empty; lists valid
**Post:** Returns complete RobustnessReport
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Overall Score Calculation:**
- Parameter score: 40% weight
- Map score: 30% weight (100 if plateau exists, else 50)
- Date score: 30% weight

**Warnings Generated For:**
- Unstable parameters
- No stable plateau found
- High start date sensitivity

---

## Acceptance Criteria
- [ ] **AC-001:** Parameter variation is ±20% (Req #14)
- [ ] **AC-002:** analyze_parameter_sensitivity() tests at least 5 values
- [ ] **AC-003:** Parameter sensitivity calculates return_std
- [ ] **AC-004:** Parameter sensitivity calculates stability_score
- [ ] **AC-005:** generate_stability_map() creates 3D surface
- [ ] **AC-006:** Stability map detects stable plateau
- [ ] **AC-007:** Stability plateau is >20% of points near peak
- [ ] **AC-008:** analyze_start_date_sensitivity() tests 12 start dates (Req #14)
- [ ] **AC-009:** Start date robustness requires <20% variation (Req #14)
- [ ] **AC-010:** _detect_stable_plateau() checks 90% threshold
- [ ] **AC-011:** _find_best_region() uses top 10% by Sharpe
- [ ] **AC-012:** generate_robustness_report() calculates overall score
- [ ] **AC-013:** Warnings generated for unstable parameters
- [ ] **AC-014:** NumPy 2.0 compatible (no np aliases)
- [ ] **AC-015:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Robustness Tester):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Robustness testing | Pardo (2008) | Parameter sensitivity | ✅ OK - analyze_parameter_sensitivity() |
| ±20% variation | Req #14 | Parameter variation range | ✅ OK - parameter_variation_pct = 0.20 |
| 12 start dates | Req #14 | Start date sensitivity | ✅ OK - n_start_dates = 12 |
| <20% variation | Req #14 | Robustness threshold | ✅ OK - max_return_variation = 0.20 |
| Stability maps | 3D visualization | Parameter surface | ✅ OK - generate_stability_map() |
| Stable plateau | Robustness | Not single peak | ✅ OK - _detect_stable_plateau() |
| Cubic interpolation | Scipy | Smooth surface | ✅ OK - griddata(method='cubic') |
| 3D mesh data | Visualization | mesh_x, mesh_y, mesh_z | ✅ OK - StabilityMapResult |
| Best region | Robustness | Top 10% by Sharpe | ✅ OK - _find_best_region() |
| Overall score | Scoring | Weighted average | ✅ OK - 40%/30%/30% |
| Warnings | Clean code | Actionable alerts | ✅ OK - warnings list |
| Recommendations | Clean code | Improvement suggestions | ✅ OK - recommendations list |
| NumPy 2.0 compatible | BASE_RULES.md (TYP-005) | No np aliases | ✅ OK - np.ndarray |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Pardo (2008) for robustness testing standards.

---

## Dependencies
- **External:** `numpy`, `scipy`, `decimal` (std), `datetime` (std), `dataclasses` (std), `logging` (std), `typing` (std)
- **Internal:**
  - `app.backtesting.models.BacktestConfig`
  - `app.backtesting.models.BacktestResult`
  - `app.models.market_data.Quote`

---

## Required Tests
- **test_robustness_tester.py:**
  - `test_init()` - Initializes with defaults
  - `test_init_custom_params()` - Uses provided values
  - `test_analyze_parameter_sensitivity_int()` - Varies int by ±20%
  - `test_analyze_parameter_sensitivity_float()` - Varies float by ±20%
  - `test_analyze_parameter_sensitivity_decimal()` - Varies decimal by ±20%
  - `test_analyze_parameter_sensitivity_n_steps()` - Tests 5 values
  - `test_parameter_sensitivity_return_std()` - Calculates std dev
  - `test_parameter_sensitivity_stability_score()` - Returns 0-100
  - `test_parameter_sensitivity_is_stable()` - Checks variation threshold
  - `test_generate_stability_map()` - Creates 3D surface
  - `test_stability_map_mesh_data()` - Returns mesh_x, mesh_y, mesh_z
  - `test_detect_stable_plateau()` - True when >20% near peak
  - `test_calculate_plateau_size()` - Returns percentage
  - `test_find_best_region()` - Returns top 10% stats
  - `test_analyze_start_date_sensitivity()` - Tests 12 dates
  - `test_start_date_sensitivity_robust()` - <20% variation
  - `test_start_date_sensitivity_not_robust()` - >=20% variation
  - `test_start_date_return_range_pct()` - (max-min)/avg × 100
  - `test_generate_robustness_report()` - Returns complete report
  - `test_overall_score_calculation()` - 40%/30%/30% weights
  - `test_warnings_unstable_params()` - Warnings for unstable
  - `test_warnings_no_plateau()` - Warnings for no plateau
  - `test_warnings_start_date()` - Warnings for high sensitivity

---

## Notes
- **Critical:** Robustness testing is essential to identify overfitting (Req #14 - HIGH PRIORITY)
- **Pardo Reference:** "The Evaluation and Optimization of Trading Strategies" (2008) - Robustness testing
- **Parameter Sensitivity (Req #14):**
  - Varies each parameter by ±20%
  - Tests 5 values across range
  - Measures impact on returns, Sharpe, drawdown
  - Lower return_std = more robust
- **Stability Maps:**
  - 3D surface showing performance across 2 parameters
  - Robust strategies show stable plateau (not single peak)
  - Uses cubic interpolation for smooth surface
  - >20% of points near peak = stable plateau
- **Start Date Sensitivity (Req #14):**
  - Tests 12 different start dates (monthly intervals)
  - Robust if CAGR variation < 20%
  - High sensitivity = overfitting to specific period
- **Plateau Detection:**
  - Threshold: 90% of max return
  - Stable if >20% of points in plateau
  - Single peak = overfitting
- **Best Region:**
  - Top 10% of points by Sharpe ratio
  - Returns center and std of parameters
- **Overall Score:**
  - Parameter score: 40% weight
  - Map score: 30% weight (100 if plateau)
  - Date score: 30% weight
  - min_stability_score: 60% for "robust"
- **Warnings:**
  - Unstable parameters
  - No stable plateau
  - High start date sensitivity
- **Production Rule:** Never deploy a strategy without robustness testing

---

**File Reference:** `app/backtesting/robustness_tester.py`
**Last Audited:** 2026-02-01
