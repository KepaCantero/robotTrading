# risk_configurator.py

## Purpose
Risk Configuration Service - Provides risk management configuration based on risk tolerance, implementing VaR, Expected Shortfall, and drawdown controls.

---

## Type Definitions / Data Classes

### RiskLimitType (str, Enum)
```python
class RiskLimitType(str, Enum):
    MAX_DRAWDOWN = "max_drawdown"              # Maximum drawdown limit
    MAX_VOLATILITY = "max_volatility"          # Maximum volatility limit
    VAR_LIMIT = "var_limit"                    # Value at Risk limit
    EXPECTED_SHORTFALL = "expected_shortfall"  # Expected Shortfall limit
    MAX_POSITION_SIZE = "max_position_size"    # Maximum single position
    MAX_LEVERAGE = "max_leverage"              # Maximum leverage ratio
    CONCENTRATION_LIMIT = "concentration_limit" # Concentration limit
```

### StressTestScenario (str, Enum)
```python
class StressTestScenario(str, Enum):
    MARKET_CRASH = "market_crash"              # -30% market drop
    VOLATILITY_SPIKE = "volatility_spike"      # 2x volatility
    SECTOR_ROTATION = "sector_rotation"        # Sector-specific moves
    LIQUIDITY_CRISIS = "liquidity_crisis"      # Wide bid-ask spreads
    CORRELATION_BREAKDOWN = "correlation_breakdown"  # Diversification fails
```

### RiskLimit
```python
@dataclass
class RiskLimit:
    limit_type: RiskLimitType                   # REQUIRED - Type of risk limit
    limit_value: Decimal                        # REQUIRED - Limit threshold
    current_value: Decimal                      # REQUIRED - Current metric value
    utilization: float                          # 0-1 - Percentage of limit used
    is_breached: bool                           # Whether limit is exceeded
    timestamp: datetime                         # When measurement was taken
```

### VaRResult
```python
@dataclass
class VaRResult:
    var_95: Decimal                             # VaR at 95% confidence
    var_99: Decimal                             # VaR at 99% confidence
    expected_shortfall_95: Decimal              # ES at 95% confidence
    expected_shortfall_99: Decimal              # ES at 99% confidence
    confidence_interval: Tuple[Decimal, Decimal] # 95% CI for VaR
    calculation_date: datetime                  # When VaR was calculated
```

### DrawdownMetrics
```python
@dataclass
class DrawdownMetrics:
    current_drawdown: Decimal                    # Current drawdown
    max_drawdown: Decimal                        # Maximum drawdown
    avg_drawdown: Decimal                        # Average drawdown
    drawdown_duration: int                       # Days in current drawdown
    max_drawdown_duration: int                   # Longest drawdown period
    recovery_factor: float                       # Months to recover from max DD
```

### RiskBudget
```python
@dataclass
class RiskBudget:
    total_risk_budget: Decimal                   # In volatility terms
    equity_risk: Decimal                         # Allocation to equities
    fixed_income_risk: Decimal                   # Allocation to fixed income
    alternative_risk: Decimal                    # Allocation to alternatives
    currency_risk: Decimal                       # Allocation to currency risk
    concentration_risk: Decimal                  # Allocation to concentration
```

---

## Function Signatures (Contracts) - RiskConfigurator

### `RiskConfigurator.__init__() -> None`
**Pre:** None
**Post:** RiskConfigurator initialized with empty risk limits and stress scenarios
**Raises:** None
**Retry:** No
**Side Effects:** Initializes stress scenarios

### `configure_risk_limits(risk_tolerance: str, capital: Decimal) -> Dict[RiskLimitType, Decimal]`
**Pre:** risk_tolerance in ["BAJO", "MEDIO", "ALTO"]; capital > 0
**Post:** Returns risk limits based on tolerance
**Raises:** None (defaults to ALTO for unknown tolerance)
**Retry:** No
**Side Effects:** None (pure factory)

**Risk Limits by Tolerance:**

| Tolerance | Max DD | Max Vol | VaR | ES | Position | Leverage | Concentration |
|-----------|--------|---------|-----|----|----|----------|---------------|
| BAJO | 15% | 20% | 5% | 7% | 5% | 1.0x | 20% |
| MEDIO | 25% | 30% | 8% | 12% | 10% | 1.5x | 30% |
| ALTO | 40% | 50% | 12% | 18% | 20% | 2.0x | 40% |

### `calculate_var(returns: np.ndarray, capital: Decimal, confidence_levels) -> VaRResult`
**Pre:** returns is array of daily returns; capital > 0
**Post:** Returns VaRResult with VaR and Expected Shortfall at confidence levels
**Raises:** None (returns zero VaRResult if insufficient data)
**Retry:** No
**Side Effects:** None (pure computation)

**Formulas:**
- VaR (historical): Sort returns, take percentile at (1 - confidence)
- Expected Shortfall: Mean of returns beyond VaR
- Confidence Interval: Bootstrap method (1000 samples)

**Reference:** Artzner et al. (1999) "Coherent Measures of Risk"

### `calculate_drawdown_metrics(equity_curve: np.ndarray) -> DrawdownMetrics`
**Pre:** equity_curve is array of portfolio values over time
**Post:** Returns DrawdownMetrics with various statistics
**Raises:** None (returns zero metrics if insufficient data)
**Retry:** No
**Side Effects:** None (pure computation)

**Formulas:**
- drawdown = (equity_curve - running_max) / running_max
- max_drawdown = min(drawdown)
- recovery_factor = abs(max_drawdown) × 12

### `check_risk_limits(current_values, risk_limits) -> List[RiskLimit]`
**Pre:** current_values and risk_limits have matching keys
**Post:** Returns list of RiskLimit objects with utilization and breach status
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Utilization Formula:** `utilization = current_value / limit_value` (clamped to max 1.0)
**Breach Condition:** `current_value > limit_value`

### `allocate_risk_budget(total_risk_budget, asset_class_volatilities, correlations) -> RiskBudget`
**Pre:** total_risk_budget > 0; volatilities > 0
**Post:** Returns RiskBudget with risk allocations
**Raises:** None (equal weights if total_inv_vol = 0)
**Retry:** No
**Side Effects:** None (pure computation)

**Method:** Inverse volatility weighting for risk parity allocation

### `run_stress_test(portfolio_value, portfolio_positions, scenario) -> Decimal`
**Pre:** portfolio_value > 0; portfolio_positions non-empty
**Post:** Returns estimated loss under stress scenario
**Raises:** None (returns 0 if scenario not found)
**Retry:** No
**Side Effects:** None (pure computation)

**Stress Scenarios:**
- **MARKET_CRASH:** -30% equities, +5% bonds, 2x vol
- **VOLATILITY_SPIKE:** 3x volatility
- **SECTOR_ROTATION:** Sector-specific moves
- **LIQUIDITY_CRISIS:** 5x bid-ask spreads, -15% equities
- **CORRELATION_BREAKDOWN:** All correlations → 0.9

---

## Acceptance Criteria
- [ ] **AC-001:** configure_risk_limits() returns correct limits for BAJO/MEDIO/ALTO
- [ ] **AC-002:** VaR calculated using historical simulation
- [ ] **AC-003:** Expected Shortfall calculated as mean beyond VaR
- [ ] **AC-004:** Confidence interval calculated via bootstrap
- [ ] **AC-005:** Drawdown metrics calculated from equity curve
- [ ] **AC-006:** Risk limits check shows utilization and breach status
- [ ] **AC-007:** Risk budget allocated using inverse volatility
- [ ] **AC-008:** Stress tests estimate losses under scenarios
- [ ] **AC-009:** All calculations handle edge cases (empty data, zero values)
- [ ] **AC-010:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Risk Configurator Service):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Service pattern | Clean Architecture | Application service | ✅ OK - RiskConfigurator |
| VaR calculation | Hull (2018) | Value at Risk | ✅ OK - calculate_var() |
| Expected Shortfall | Artzner (1999) | Coherent risk measure | ✅ OK - ES in VaRResult |
| Historical simulation | Risk management | Non-parametric VaR | ✅ OK - Sorted returns |
| Bootstrap CI | Statistics | Confidence interval | ✅ OK - _bootstrap_var_ci() |
| Drawdown metrics | Risk management | Peak-to-trough analysis | ✅ OK - calculate_drawdown_metrics() |
| Risk limits | Risk management | Threshold enforcement | ✅ OK - check_risk_limits() |
| Risk budget | Portfolio theory | Risk allocation | ✅ OK - allocate_risk_budget() |
| Inverse volatility | Risk parity | 1/vol weighting | ✅ OK - allocate_risk_budget() |
| Stress testing | Risk management | Scenario analysis | ✅ OK - run_stress_test() |
| Tolerance-based limits | Risk management | 3 tiers | ✅ OK - configure_risk_limits() |
| Coherent risk measures | Artzner (1999) | ES is coherent | ✅ OK - Expected Shortfall |
| NumPy 2.0 compatible | BASE_RULES.md (TYP-005) | No np aliases | ✅ OK - np.ndarray |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Hull (2018), Artzner (1999) for risk management standards.

---

## Dependencies
- **External:** `numpy`, `dataclasses` (std), `decimal` (std), `datetime` (std), `enum` (std), `typing` (std)
- **Internal:** None (application service)

---

## Required Tests
- **test_risk_configurator.py:**
  - `test_configure_risk_limits_bajo()` - Conservative limits
  - `test_configure_risk_limits_medio()` - Moderate limits
  - `test_configure_risk_limits_alto()` - Aggressive limits
  - `test_configure_risk_limits_unknown()` - Defaults to ALTO
  - `test_calculate_var_sufficient_data()` - Returns VaRResult
  - `test_calculate_var_insufficient_data()` - Returns zero VaRResult
  - `test_var_95_calculated()` - Correct 95% VaR
  - `test_var_99_calculated()` - Correct 99% VaR
  - `test_expected_shortfall_95_calculated()` - Average beyond VaR
  - `test_expected_shortfall_99_calculated()` - Average beyond VaR
  - `test_confidence_interval_calculated()` - Bootstrap CI
  - `test_calculate_drawdown_metrics()` - All metrics calculated
  - `test_drawdown_metrics_empty_data()` - Returns zero metrics
  - `test_current_drawdown()` - Last value
  - `test_max_drawdown()` - Minimum drawdown
  - `test_avg_drawdown()` - Average of drawdown periods
  - `test_drawdown_duration()` - Days in current DD
  - `test_max_drawdown_duration()` - Longest DD period
  - `test_recovery_factor()` - Months to recover
  - `test_check_risk_limits()` - Returns list of RiskLimit
  - `test_risk_limit_utilization()` - current / limit
  - `test_risk_limit_breached()` - current > limit
  - `test_allocate_risk_budget_inverse_vol()` - 1/vol weighting
  - `test_allocate_risk_budget_zero_total()` - Equal weights
  - `test_risk_budget_allocations()` - Risk per asset class
  - `test_run_stress_test_market_crash()` - -30% loss
  - `test_run_stress_test_volatility_spike()` - 3x vol
  - `test_run_stress_test_liquidity_crisis()` - 5x spreads
  - `test_run_stress_test_unknown_scenario()` - Returns 0
  - `test_stress_scenarios_initialized()` - 5 scenarios

---

## Notes
- **Critical:** RiskConfigurator is an APPLICATION SERVICE (Clean Architecture)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Application Service pattern
- **Service Pattern:** Orchestrates domain logic and calculations
- **Hull Reference:** "Risk Management and Financial Institutions" (2018) - VaR and risk metrics
- **Artzner Reference:** "Coherent Measures of Risk" (1999) - Expected Shortfall as coherent risk measure
- **VaR (Value at Risk):** Maximum expected loss at confidence level over time horizon
  - Historical simulation: Sort returns, take percentile
  - 95% VaR: 95% confident losses won't exceed this
  - 99% VaR: 99% confident losses won't exceed this
- **Expected Shortfall (ES):** Average loss beyond VaR (coherent risk measure)
  - Also called Conditional VaR (CVaR) or Average Value at Risk (AVaR)
  - Addresses VaR limitations by considering tail risk
- **Bootstrap Confidence Interval:** Resample returns 1000 times to estimate VaR uncertainty
- **Drawdown Metrics:**
  - Current: Current peak-to-trough decline
  - Max: Largest historical decline
  - Average: Mean of all drawdown periods
  - Duration: Days in current/longest drawdown
  - Recovery Factor: Months to recover from max DD
- **Risk Limits:** Thresholds for various risk metrics (DD, vol, VaR, position size, leverage)
- **Risk Budget:** Allocation of total risk budget across asset classes using inverse volatility
- **Stress Testing:** Scenario-based loss estimation (market crash, volatility spike, liquidity crisis)
- **Tolerance Tiers:**
  - BAJO (Low): Conservative - 15% max DD, no leverage, 5% max position
  - MEDIO (Medium): Moderate - 25% max DD, 1.5x leverage, 10% max position
  - ALTO (High): Aggressive - 40% max DD, 2x leverage, 20% max position
- **NumPy Usage:** Uses np.ndarray for efficient numerical computation
- **Edge Cases:** Handles insufficient data gracefully (returns zero metrics)

---

**File Reference:** `app/application/services/risk_configurator.py`
**Last Audited:** 2026-02-01
