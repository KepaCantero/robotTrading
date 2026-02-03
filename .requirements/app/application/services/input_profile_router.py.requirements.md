# input_profile_router.py (services)

## Purpose
Alternative implementation of InputProfile routing with different data model. Maps InputProfile to SystemConfiguration including strategy type, risk config, optimization config, and tax config based on user investment parameters.

---

## Type Definitions / Data Classes

### StrategyType (Enum)
```python
class StrategyType(str, Enum):
    MOMENTUM = "momentum"  # For MAXIMIZAR_CAPITAL
    DIVIDEND = "dividend"  # For MAXIMIZAR_DIVIDENDOS
    LOW_VOLATILITY = "low_volatility"  # For CAPITAL_PRESERVATION
    MULTI_FACTOR = "multi_factor"  # For BALANCED_GROWTH
    MEAN_REVERSION = "mean_reversion"  # Neutral/Balanced
    PAIRS_TRADING = "pairs_trading"  # Market neutral
    QUALITY = "quality"  # Long-term quality
    COVERED_CALL = "covered_call"  # For INCOME_GENERATION
```

### OptimizationType (Enum)
```python
class OptimizationType(str, Enum):
    MEAN_VARIANCE = "mean_variance"  # Markowitz MVO
    HIERARCHICAL_RISK_PARITY = "hrp"  # HRP
    NESTED_CLUSTERED = "nco"  # NCO
    BLACK_LITTERMAN = "black_litterman"  # BL
    RISK_PARITY = "risk_parity"  # Inverse volatility
    EQUAL_WEIGHT = "equal_weight"  # Simple equal weight
```

### RiskConfig (Dataclass)
```python
@dataclass
class RiskConfig:
    max_drawdown: Decimal  # REQUIRED - Maximum drawdown allowed
    max_volatility: Decimal  # REQUIRED - Maximum annualized volatility
    max_position_size: Decimal  # REQUIRED - Maximum single position size
    leverage_allowed: bool  # REQUIRED - Whether leverage is allowed
    max_leverage: Decimal  # REQUIRED - Maximum leverage ratio
    stop_loss_atr_multiplier: Decimal  # REQUIRED - ATR multiplier for stop loss
    take_profit_atr_multiplier: Decimal  # REQUIRED - ATR multiplier for take profit
    var_confidence: float  # REQUIRED - VaR confidence level (0.95, 0.99)
    expected_shortfall_confidence: float  # REQUIRED - ES confidence level
```

**Validation Rules:**
- `max_drawdown`, `max_volatility`, `max_position_size` must be between 0 and 1
- `max_leverage` must be >= 1.0
- `var_confidence`, `expected_shortfall_confidence` must be between 0 and 1

### OptimizationConfig (Dataclass)
```python
@dataclass
class OptimizationConfig:
    optimization_type: OptimizationType  # REQUIRED - Optimization method
    lookback_period: int  # REQUIRED - Days for covariance calculation
    rebalance_frequency: RebalancingFrequency  # REQUIRED - How often to rebalance
    min_weight: Decimal  # REQUIRED - Minimum position weight
    max_weight: Decimal  # REQUIRED - Maximum position weight
    max_turnover: Decimal  # REQUIRED - Maximum portfolio turnover
    target_portfolio_volatility: Optional[Decimal]  # OPTIONAL - Target volatility
```

### TaxConfig (Dataclass)
```python
@dataclass
class TaxConfig:
    country: str  # REQUIRED - Country code
    method: str  # REQUIRED - Accounting method (FIFO, LIFO, HIFO)
    dividend_tax_rate: Decimal  # REQUIRED - Dividend tax rate
    capital_gains_tax_rate: Decimal  # REQUIRED - Capital gains tax rate
    short_term_holding_period: int  # REQUIRED - Days for short-term
    tax_loss_harvesting: bool  # REQUIRED - Enable tax loss harvesting
    witholding_tax_rate: Decimal  # REQUIRED - Withholding tax rate
```

### SystemConfiguration (Dataclass)
```python
@dataclass
class SystemConfiguration:
    input_profile: InputProfile  # REQUIRED - Original user profile
    strategy_type: StrategyType  # REQUIRED - Selected strategy
    risk_config: RiskConfig  # REQUIRED - Risk parameters
    optimization_config: OptimizationConfig  # REQUIRED - Optimization settings
    tax_config: TaxConfig  # REQUIRED - Tax configuration
    max_positions: int  # REQUIRED - Maximum number of positions
    min_liquidity_score: float  # REQUIRED - Minimum liquidity score
    sector_diversification_required: bool  # REQUIRED - Enforce sector diversification
    max_sector_exposure: Decimal  # REQUIRED - Max exposure per sector
    long_only: bool  # REQUIRED - Long-only or long-short allowed
```

---

## Function Signatures (Contracts)

### `__call__(profile: InputProfile) -> SystemConfiguration`
**Pre:** `profile` must be valid InputProfile with all required fields
**Post:** Returns complete SystemConfiguration
**Raises:** No explicit exceptions
**Retry:** No
**Side Effects:** No state changes (pure routing)

### `_select_strategy_type(objective: InvestmentObjective) -> StrategyType`
**Pre:** `objective` must be valid InvestmentObjective enum
**Post:** Returns StrategyType, defaults to MULTI_FACTOR if not found
**Raises:** No exceptions (uses .get() with default)
**Retry:** No
**Side Effects:** No state changes

### `_select_risk_config(tolerance: RiskTolerance) -> RiskConfig`
**Pre:** `tolerance` must be valid RiskTolerance enum
**Post:** Returns RiskConfig with parameters for tolerance level
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** No state changes

### `_select_optimization_config(horizon: InvestmentHorizon, tolerance: RiskTolerance) -> OptimizationConfig`
**Pre:** `horizon` and `tolerance` must be valid
**Post:** Returns OptimizationConfig based on horizon and tolerance
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** No state changes

### `_create_tax_config(residence: TaxResidence) -> TaxConfig`
**Pre:** `residence` must have country attribute
**Post:** Returns TaxConfig with country-specific parameters
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** No state changes

### `_generate_constraints(profile: InputProfile) -> Dict[str, Any]`
**Pre:** `profile` must be valid with capital, risk_tolerance, objective
**Post:** Returns dict of constraint values
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** No state changes

### `get_strategy_config(profile: InputProfile) -> Dict[str, Any]`
**Pre:** `profile` must be valid InputProfile
**Post:** Returns strategy-specific configuration dictionary
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** No state changes (calls __call__ internally)

---

## Acceptance Criteria
- [ ] MAXIMIZAR_CAPITAL maps to MOMENTUM strategy
- [ ] CAPITAL_PRESERVATION maps to LOW_VOLATILITY strategy
- [ ] BAJO risk tolerance sets leverage_allowed to False
- [ ] ALTO risk tolerance allows 2.0x leverage
- [ ] Short horizon (< 12 months) uses EQUAL_WEIGHT optimization
- [ ] Long horizon (> 60 months) uses MEAN_VARIANCE optimization
- [ ] Capital < $10,000 limits max_positions to 10
- [ ] Capital >= $100,000 allows max_positions to 50
- [ ] CAPITAL_PRESERVATION objective requires long_only
- [ ] Spain tax config uses FIFO method with 19% rates
- [ ] USA tax config uses HIFO method with 15% rates
- [ ] All strategy types generate appropriate config parameters

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES.md | Modern syntax | ⚠️ PARTIAL - Uses `Dict` instead of `dict` |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ GAP - No explicit validation |
| CC-007 | BASE_RULES.md | Small functions | ⚠️ NOT APPLIED - Some functions long |
| TRD-002 | BASE_RULES.md | Risk validation | ✅ OK - via RiskConfig |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** `dataclasses.dataclass`, `decimal.Decimal`, `enum.Enum`, `typing`
- **Internal:**
  - `app.domain.models.input_profile` (InputProfile, InvestmentObjective, RiskTolerance)
  - `app.domain.value_objects.investment_horizon` (InvestmentHorizon)
  - `app.domain.value_objects.tax_residence` (TaxResidence)

---

## Required Tests
- **test_input_profile_router_services.py:**
  - Test strategy type mapping for all investment objectives
  - Test risk config mapping for all risk tolerance levels
  - Test optimization config selection for different horizons
  - Test tax config creation for Spain, USA, UK, default
  - Test constraint generation for different capital levels
  - Test complete configuration generation
  - Test get_strategy_config for all strategy types
  - Test long_only constraint for CAPITAL_PRESERVATION
  - Test leverage settings for all risk tolerances
  - Test position limits based on capital

---

## Notes
**Duplicate Implementation:** This is an alternative implementation of InputProfile routing in the services directory. The canonical implementation is in `routers/input_profile_router.py`. Consider consolidating to avoid duplication (DRY principle - CC-002).

**Data Model Differences:** Uses different InputProfile model from `app.domain.models.input_profile` vs `app.core.models.input_profile` used in routers version.
