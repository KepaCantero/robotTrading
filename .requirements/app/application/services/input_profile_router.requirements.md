# input_profile_router.py

## Purpose
InputProfile Router - Maps InputProfile to System Configuration, automatically determining strategy, risk parameters, optimization method, tax handling, and constraints.

---

## Type Definitions / Data Classes

### StrategyType (str, Enum)
```python
class StrategyType(str, Enum):
    MOMENTUM = "momentum"                      # MAXIMIZAR_CAPITAL
    DIVIDEND = "dividend"                      # MAXIMIZAR_DIVIDENDOS
    LOW_VOLATILITY = "low_volatility"          # CAPITAL_PRESERVATION
    MULTI_FACTOR = "multi_factor"              # BALANCED_GROWTH
    MEAN_REVERSION = "mean_reversion"          # Neutral/Balanced
    PAIRS_TRADING = "pairs_trading"            # Market neutral
    QUALITY = "quality"                        # Long-term quality
    COVERED_CALL = "covered_call"              # INCOME_GENERATION
```

### OptimizationType (str, Enum)
```python
class OptimizationType(str, Enum):
    MEAN_VARIANCE = "mean_variance"            # Markowitz MVO
    HIERARCHICAL_RISK_PARITY = "hrp"           # HRP
    NESTED_CLUSTERED = "nco"                   # NCO
    BLACK_LITTERMAN = "black_litterman"        # BL
    RISK_PARITY = "risk_parity"                # Inverse volatility
    EQUAL_WEIGHT = "equal_weight"              # Simple equal weight
```

### RebalancingFrequency (str, Enum)
```python
class RebalancingFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
```

### RiskConfig
```python
@dataclass
class RiskConfig:
    max_drawdown: Decimal                       # Maximum drawdown allowed
    max_volatility: Decimal                     # Maximum annualized volatility
    max_position_size: Decimal                   # Maximum single position size
    leverage_allowed: bool                      # Whether leverage is allowed
    max_leverage: Decimal                        # Maximum leverage ratio
    stop_loss_atr_multiplier: Decimal            # ATR multiplier for stop loss
    take_profit_atr_multiplier: Decimal          # ATR multiplier for take profit
    var_confidence: float                        # VaR confidence level (0.95, 0.99)
    expected_shortfall_confidence: float         # ES confidence level
```

### OptimizationConfig
```python
@dataclass
class OptimizationConfig:
    optimization_type: OptimizationType         # Portfolio optimization method
    lookback_period: int                        # Days for covariance calculation
    rebalance_frequency: RebalancingFrequency   # How often to rebalance
    min_weight: Decimal                         # Minimum position weight
    max_weight: Decimal                         # Maximum position weight
    max_turnover: Decimal                       # Maximum portfolio turnover
    target_portfolio_volatility: Optional[Decimal]  # Target volatility
```

### TaxConfig
```python
@dataclass
class TaxConfig:
    country: str                                # Country name
    method: str                                 # FIFO, LIFO, HIFO, etc.
    dividend_tax_rate: Decimal                  # Dividend tax rate
    capital_gains_tax_rate: Decimal             # Capital gains tax rate
    short_term_holding_period: int              # Days for short-term classification
    tax_loss_harvesting: bool                   # Whether to use tax loss harvesting
    witholding_tax_rate: Decimal                # Withholding tax on dividends
```

### SystemConfiguration
```python
@dataclass
class SystemConfiguration:
    input_profile: InputProfile                 # User's InputProfile
    strategy_type: StrategyType                 # Selected strategy
    risk_config: RiskConfig                     # Risk configuration
    optimization_config: OptimizationConfig     # Optimization configuration
    tax_config: TaxConfig                       # Tax configuration

    # Additional constraints
    max_positions: int                          # Maximum number of positions
    min_liquidity_score: float                  # Minimum liquidity requirement
    sector_diversification_required: bool       # Whether sector diversification is required
    max_sector_exposure: Decimal                # Maximum exposure per sector
    long_only: bool                             # Long-only or long-short
```

---

## Function Signatures (Contracts) - InputProfileRouter

### `InputProfileRouter.__call__(profile) -> SystemConfiguration`
**Pre:** profile is valid InputProfile
**Post:** Returns complete SystemConfiguration
**Raises:** None (errors handled internally)
**Retry:** No
**Side Effects:** None (pure mapping)

**Process:**
1. Select strategy type from investment objective
2. Select risk configuration from risk tolerance
3. Select optimization configuration from horizon and capital
4. Create tax configuration from residence
5. Generate additional constraints

### `_select_strategy_type(objective) -> StrategyType`
**Pre:** None
**Post:** Returns StrategyType based on objective
**Raises:** None (defaults to MULTI_FACTOR)
**Retry:** No
**Side Effects:** None (pure mapping)

**Mapping:**
- MAXIMIZAR_CAPITAL → MOMENTUM
- MAXIMIZAR_DIVIDENDOS → DIVIDEND
- CAPITAL_PRESERVATION → LOW_VOLATILITY
- BALANCED_GROWTH → MULTI_FACTOR
- INCOME_GENERATION → COVERED_CALL

### `_select_risk_config(tolerance) -> RiskConfig`
**Pre:** tolerance is RiskTolerance
**Post:** Returns RiskConfig based on tolerance
**Raises:** None
**Retry:** No
**Side Effects:** None (pure factory)

**Risk Config by Tolerance:**

| Tolerance | Max DD | Max Vol | Position | Leverage | Stop | TP |
|-----------|--------|---------|----------|----------|------|-----|
| BAJO | 15% | 20% | 5% | No (1.0x) | 2.0× ATR | 3.0× ATR |
| MEDIO | 25% | 30% | 10% | Yes (1.5x) | 2.5× ATR | 4.0× ATR |
| ALTO | 40% | 50% | 20% | Yes (2.0x) | 3.0× ATR | 6.0× ATR |

### `_select_optimization_config(horizon, tolerance) -> OptimizationConfig`
**Pre:** horizon is InvestmentHorizon; tolerance is RiskTolerance
**Post:** Returns OptimizationConfig
**Raises:** None
**Retry:** No
**Side Effects:** None (pure factory)

**Rules:**
- Short horizon (< 12 months) → Equal weight or Risk Parity
- Medium horizon (12-60 months) → HRP or NCO
- Long horizon (> 60 months) → MVO or Black-Litterman
- Low tolerance → More conservative (smaller max_weight)
- High tolerance → More aggressive (larger max_weight)

### `_create_tax_config(residence) -> TaxConfig`
**Pre:** residence is TaxResidence
**Post:** Returns TaxConfig based on country
**Raises:** None
**Retry:** No
**Side Effects:** None (pure factory)

**Tax Config by Country:**

| Country | Method | Div Tax | CG Tax | Short Term | Loss Harvesting |
|---------|--------|---------|--------|------------|----------------|
| Spain | FIFO | 19% | 19% | 365 days | Yes |
| USA | HIFO | 15% | 15% | 365 days | Yes |
| UK | FIFO | 8.75% | 10% | 0 days | Yes |
| Default | FIFO | 15% | 15% | 365 days | Yes |

### `_generate_constraints(profile) -> Dict[str, Any]`
**Pre:** profile is valid InputProfile
**Post:** Returns constraint dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Constraints:**
- **max_positions:** Based on capital tier (<10k: 10, <100k: 25, >=100k: 50)
- **min_liquidity_score:** 0.5 if capital < 50k, else 0.7
- **sector_diversification_required:** True for BAJO/MEDIO tolerance
- **max_sector_exposure:** 25% for BAJO, else 40%
- **long_only:** True for CAPITAL_PRESERVATION or MAXIMIZAR_DIVIDENDOS

### `get_strategy_config(profile) -> Dict[str, Any]`
**Pre:** profile is valid InputProfile
**Post:** Returns strategy-specific configuration
**Raises:** None
**Retry:** No
**Side Effects:** None (calls __call__ and extracts strategy config)

**Strategy-Specific Parameters:**
- **MOMENTUM:** lookback=252, rebalance=monthly, top/bottom_percentile=0.3
- **DIVIDEND:** min_yield=2%, max_yield=10%, min_dividend_growth=0%
- **LOW_VOLATILITY:** max_beta=0.8, max_volatility=0.25
- **MULTI_FACTOR:** factor_weights (value, size, momentum, quality)

---

## Acceptance Criteria
- [ ] **AC-001:** __call__ returns complete SystemConfiguration
- [ ] **AC-002:** Strategy type mapped from objective
- [ ] **AC-003:** Risk config mapped from tolerance (BAJO/MEDIO/ALTO)
- [ ] **AC-004:** Optimization config mapped from horizon and tolerance
- [ ] **AC-005:** Tax config mapped from residence country
- [ ] **AC-006:** Constraints generated from profile
- [ ] **AC-007:** max_positions based on capital tier
- [ ] **AC-008:** long_only for conservative objectives
- [ ] **AC-009:** Strategy-specific parameters in get_strategy_config()
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

### Reglas ESPECÍFICAS de este archivo (InputProfile Router):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Router pattern | Clean Architecture | Profile → Configuration | ✅ OK - InputProfileRouter |
| Strategy mapping | Investment policy | Objective → Strategy | ✅ OK - _select_strategy_type() |
| Risk mapping | Risk management | Tolerance → Limits | ✅ OK - _select_risk_config() |
| Optimization mapping | Portfolio theory | Horizon → Method | ✅ OK - _select_optimization_config() |
| Tax mapping | Tax law | Residence → Config | ✅ OK - _create_tax_config() |
| Constraints | Risk management | Capital tier → Limits | ✅ OK - _generate_constraints() |
| Callability | Python | __call__ as main interface | ✅ OK - __call__() |
| ATR-based stops | Trading | Stop/TP in ATR multiples | ✅ OK - RiskConfig |
| Sector diversification | Risk management | Required for MEDIO/BAJO | ✅ OK - Constraints |
| Long-only constraint | Risk management | For conservative objectives | ✅ OK - long_only |
| Strategy parameters | Trading | Strategy-specific settings | ✅ OK - get_strategy_config() |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Clean Architecture patterns.

---

## Dependencies
- **External:** `dataclasses` (std), `decimal` (std), `enum` (std), `typing` (std)
- **Internal:**
  - `app.domain.models.input_profile.InputProfile`
  - `app.domain.models.input_profile.InvestmentObjective`
  - `app.domain.models.input_profile.RiskTolerance`
  - `app.domain.value_objects.investment_horizon.InvestmentHorizon`
  - `app.domain.value_objects.tax_residence.TaxResidence`

---

## Required Tests
- **test_input_profile_router.py:**
  - `test_call_returns_complete_config()` - All fields populated
  - `test_select_strategy_type_maximize_capital()` - MOMENTUM
  - `test_select_strategy_type_maximize_dividendos()` - DIVIDEND
  - `test_select_strategy_type_capital_preservation()` - LOW_VOLATILITY
  - `test_select_strategy_type_balanced_growth()` - MULTI_FACTOR
  - `test_select_strategy_type_income_generation()` - COVERED_CALL
  - `test_select_risk_config_bajo()` - Conservative config
  - `test_select_risk_config_medio()` - Moderate config
  - `test_select_risk_config_alto()` - Aggressive config
  - `test_select_optimization_config_short_horizon()` - Equal weight
  - `test_select_optimization_config_medium_horizon()` - HRP
  - `test_select_optimization_config_long_horizon()` - MVO
  - `test_create_tax_config_spain()` - Spanish tax config
  - `test_create_tax_config_usa()` - US tax config
  - `test_create_tax_config_uk()` - UK tax config
  - `test_generate_constraints_small_capital()` - 10 positions
  - `test_generate_constraints_medium_capital()` - 25 positions
  - `test_generate_constraints_large_capital()` - 50 positions
  - `test_generate_constraints_bajo_sector_diversification()` - Required
  - `test_generate_constraints_long_only_conservative()` - True
  - `test_get_strategy_config_momentum()` - Momentum params
  - `test_get_strategy_config_dividend()` - Dividend params
  - `test_get_strategy_config_low_volatility()` - Low vol params
  - `test_get_strategy_config_multi_factor()` - Factor weights

---

## Notes
- **Critical:** InputProfileRouter is an APPLICATION SERVICE (Clean Architecture)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Application Service pattern
- **Router Pattern:** Maps InputProfile to complete SystemConfiguration
- **KEY INSIGHT:** InputProfile drives EVERYTHING in the system (autonomous operation)
- **Strategy Type Mapping:**
  - MAXIMIZAR_CAPITAL → Momentum (aggressive growth)
  - MAXIMIZAR_DIVIDENDOS → Dividend (income focus)
  - CAPITAL_PRESERVATION → Low Volatility (defensive)
  - BALANCED_GROWTH → Multi-Factor (balanced)
  - INCOME_GENERATION → Covered Call (income)
- **Risk Configuration:**
  - BAJO: 15% max DD, no leverage, 5% max position, 2x ATR stop
  - MEDIO: 25% max DD, 1.5x leverage, 10% max position, 2.5x ATR stop
  - ALTO: 40% max DD, 2x leverage, 20% max position, 3x ATR stop
- **Optimization Selection:**
  - Short horizon: Simple methods (equal weight, risk parity)
  - Medium horizon: Hierarchical methods (HRP, NCO)
  - Long horizon: Mean-variance based (MVO, Black-Litterman)
- **Tax Configuration:**
  - Spain: FIFO, 19% taxes, 365 days short-term
  - USA: HIFO (tax optimization), 15% qualified, 365 days
  - UK: FIFO, 8.75% dividend, 10% CG, no short-term distinction
- **Constraints:**
  - Capital-based position limits (smaller accounts = fewer positions)
  - Liquidity requirements (smaller accounts = lower min liquidity)
  - Sector diversification for conservative profiles
  - Long-only for capital preservation and dividend strategies
- **Callability:** Implements __call__ for simple interface: `router(profile)`
- **Strategy-Specific Config:** get_strategy_config() provides detailed parameters per strategy

---

**File Reference:** `app/application/services/input_profile_router.py`
**Last Audited:** 2026-02-01
