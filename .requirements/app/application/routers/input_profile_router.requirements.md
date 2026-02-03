# input_profile_router.py

## Purpose
Input Profile Router - Maps InputProfile to strategies and configurations. Implements automatic strategy selection based on investment objective, addressing the gap between user inputs and system configuration.

---

## Type Definitions / Data Classes

### InputProfileRouter
```python
class InputProfileRouter:
    """Route InputProfile to appropriate strategies and risk configurations.

    This router implements the critical mapping from user inputs to system
    configuration, addressing Brecha #1: NO hay routing InputProfile -> Estrategia.

    The router follows SOLID principles:
    - SRP: Only responsible for routing/profile mapping
    - OCP: Can be extended with new strategies without modification
    - DIP: Depends on abstractions (domain models), not concrete implementations
    """
```

**Purpose:** Orchestrate mapping from user input to trading system configuration

---

## Function Signatures (Contracts)

### `InputProfileRouter.__call__(profile: InputProfile) -> SystemConfiguration`
**Pre:** profile is valid InputProfile
**Post:** Returns complete SystemConfiguration
**Raises:** ValueError if profile validation fails
**Retry:** No
**Side Effects:** Logs routing decisions

**Process Flow:**
1. Select strategy type via `_select_strategy_type()`
2. Select risk configuration via `_select_risk_config()`
3. Create tax configuration via `_create_tax_config()`
4. Calculate rebalancing frequency via `_calculate_rebalance_frequency()`
5. Build and return SystemConfiguration

**Outputs Logged:**
- strategy_type
- max_drawdown
- leverage_allowed

### `InputProfileRouter._select_strategy_type(objetivo: ObjectivoInversion) -> StrategyType`
**Pre:** objetivo is valid ObjectivoInversion
**Post:** Returns appropriate StrategyType
**Raises:** ValueError if objetivo not recognized
**Retry:** No
**Side Effects:** None (pure computation)

**Mapping Table (based on academic research):**

| objetivo_inversion | StrategyType | Reference Paper |
|-------------------|--------------|-----------------|
| MAXIMIZAR_CAPITAL | MOMENTUM | Gray & Vogel: Quantitative Momentum |
| MAXIMIZAR_DIVIDENDOS | DIVIDEND | Berkin & Swedroe: Factor-Based Investing |
| CAPITAL_PRESERVATION | LOW_VOLATILITY | Markowitz: Portfolio Selection |
| BALANCED_GROWTH | MULTI_FACTOR | Fama-French: Factor Models |
| INCOME_GENERATION | COVERED_CALL | Kissell: Portfolio Management |

### `InputProfileRouter._select_risk_config(tolerance: RiskTolerance) -> RiskConfig`
**Pre:** tolerance is valid RiskTolerance
**Post:** Returns RiskConfig with parameters
**Raises:** ValueError if tolerance not recognized
**Retry:** No
**Side Effects:** None (pure computation)

**Risk Configuration Mapping (based on John Hull principles):**

| RiskTolerance | Max Drawdown | Max Position | Leverage | Min Positions | Max Positions |
|---------------|--------------|--------------|----------|---------------|---------------|
| BAJO (Low) | 15% | 5% | No | 10 | 50 |
| MEDIO (Medium) | 25% | 10% | 1.5x | 5 | 40 |
| ALTO (High) | 40% | 20% | 2.0x | 3 | 30 |

**Additional Parameters:**
- var_confidence: 95% (all)
- max_sector_exposure: 25-40%
- stop_loss_atr_multiplier: 1.5-2.5
- max_portfolio_volatility: 12-25%

### `InputProfileRouter._create_tax_config(tax_residence: Optional[TaxResidence]) -> Optional[TaxConfig]`
**Pre:** tax_residence is valid or None
**Post:** Returns TaxConfig or None
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Behavior:**
- Returns None if tax_residence is None
- Extracts all tax parameters from TaxResidence
- Calculates `prefer_long_term` from rate comparison
- Sets `min_holding_period_days = 365` (standard 1 year)
- Sets `hedging_instruments = ["FX_FORWARDS", "CURRENCY_FUTURES"]`

**Output:** TaxConfig with 14+ parameters

### `InputProfileRouter._calculate_rebalance_frequency(horizon_months: int) -> int`
**Pre:** horizon_months >= 0
**Post:** Returns rebalancing frequency in days
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Frequency Mapping (based on Grinold & Kahn):**

| Horizon | Frequency | Days |
|---------|-----------|------|
| < 6 months | Weekly | 7 |
| 6-23 months | Bi-weekly | 14 |
| 24-59 months | Monthly | 30 |
| >= 60 months | Quarterly | 90 |

**Logic:** Longer horizons → less frequent rebalancing

### `InputProfileRouter.validate_configuration(
    profile: InputProfile,
    config: SystemConfiguration,
) -> tuple[bool, list[str]]`
**Pre:** profile and config are valid
**Post:** Returns (is_valid, warnings)
**Raises:** None
**Retry:** No
**Side Effects:** Logs warnings if invalid

**Validation Checks:**
1. CAPITAL_PRESERVATION + ALTO risk tolerance (contradictory)
2. CAPITAL_PRESERVATION + leverage allowed (not optimal)
3. Short horizon + frequent rebalancing (high transaction costs)
4. Small capital + high position minimum (over-fragmentation)

**Warnings:** List of consistency issue descriptions

**is_valid:** True if no warnings generated

---

## Acceptance Criteria
- [ ] **AC-001:** __call__() accepts InputProfile and returns SystemConfiguration
- [ ] **AC-002:** _select_strategy_type() maps MAXIMIZAR_CAPITAL to MOMENTUM
- [ ] **AC-003:** _select_strategy_type() maps MAXIMIZAR_DIVIDENDOS to DIVIDEND
- [ ] **AC-004:** _select_strategy_type() maps CAPITAL_PRESERVATION to LOW_VOLATILITY
- [ ] **AC-005:** _select_strategy_type() maps BALANCED_GROWTH to MULTI_FACTOR
- [ ] **AC-006:** _select_strategy_type() maps INCOME_GENERATION to COVERED_CALL
- [ ] **AC-007:** _select_risk_config() BAJO has 15% max_drawdown
- [ ] **AC-008:** _select_risk_config() MEDIO has 25% max_drawdown
- [ ] **AC-009:** _select_risk_config() ALTO has 40% max_drawdown
- [ ] **AC-010:** _select_risk_config() BAJO has no leverage
- [ ] **AC-011:** _select_risk_config() ALTO allows 2.0x leverage
- [ ] **AC-012:** _create_tax_config() returns None when tax_residence is None
- [ ] **AC-013:** _calculate_rebalance_frequency() returns 7 for <6 months
- [ ] **AC-014:** _calculate_rebalance_frequency() returns 90 for >=60 months
- [ ] **AC-015:** validate_configuration() detects CAPITAL_PRESERVATION + ALTO
- [ ] **AC-016:** validate_configuration() detects short horizon + frequent rebalancing
- [ ] **AC-017:** All public methods have complete type hints

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

### Reglas ESPECÍFICAS de este archivo (Input Profile Router):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Objective to strategy mapping | Gray & Vogel | Momentum for capital maximization | ✅ OK - _select_strategy_type() |
| Objective to strategy mapping | Berkin & Swedroe | Dividend for income | ✅ OK - _select_strategy_type() |
| Objective to strategy mapping | Markowitz | Low volatility for preservation | ✅ OK - _select_strategy_type() |
| Objective to strategy mapping | Fama-French | Multi-factor for balanced | ✅ OK - _select_strategy_type() |
| Risk to drawdown mapping | Hull | Risk-appropriate drawdown limits | ✅ OK - _select_risk_config() |
| Risk to leverage mapping | Hull | Conservative = no leverage | ✅ OK - _select_risk_config() |
| Position sizing | Hull | Risk-appropriate position limits | ✅ OK - _select_risk_config() |
| Rebalancing frequency | Grinold & Kahn | Horizon-based frequency | ✅ OK - _calculate_rebalance_frequency() |
| Validation | Clean code | Consistency checks | ✅ OK - validate_configuration() |
| SOLID principles | Clean Architecture | SRP, OCP, DIP | ✅ OK - Class design |
| Decimal precision | BASE_RULES.md (TYP-002) | Decimal for percentages | ✅ OK - Decimal types |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and academic papers for strategy selection.

---

## Dependencies
- **Internal:**
  - `app.core.models.input_profile.InputProfile`
  - `app.core.models.input_profile.ObjectivoInversion`
  - `app.core.models.input_profile.RiskTolerance`
  - `app.core.models.input_profile.TaxResidence`
  - `app.domain.models.risk_config.RiskConfig`
  - `app.domain.models.strategy_type.StrategyType`
  - `app.domain.models.system_configuration.SystemConfiguration`
  - `app.domain.models.tax_config.TaxConfig`
- **External:** None (std lib only: logging, decimal, typing)

---

## Required Tests
- **test_input_profile_router.py:**
  - `test_call_returns_system_configuration()` - Returns SystemConfiguration
  - `test_select_strategy_maximizar_capital()` - Returns MOMENTUM
  - `test_select_strategy_maximizar_dividendos()` - Returns DIVIDEND
  - `test_select_strategy_capital_preservation()` - Returns LOW_VOLATILITY
  - `test_select_strategy_balanced_growth()` - Returns MULTI_FACTOR
  - `test_select_strategy_income_generation()` - Returns COVERED_CALL
  - `test_select_strategy_unknown()` - Raises ValueError
  - `test_select_risk_bajo()` - 15% drawdown, no leverage
  - `test_select_risk_medio()` - 25% drawdown, 1.5x leverage
  - `test_select_risk_alto()` - 40% drawdown, 2.0x leverage
  - `test_select_risk_unknown()` - Raises ValueError
  - `test_create_tax_config_with_residence()` - Returns TaxConfig
  - `test_create_tax_config_none()` - Returns None
  - `test_rebalance_frequency_short()` - Returns 7 days
  - `test_rebalance_frequency_medium()` - Returns 14 days
  - `test_rebalance_frequency_long()` - Returns 30 days
  - `test_rebalance_frequency_very_long()` - Returns 90 days
  - `test_validate_preservation_high_risk()` - Generates warning
  - `test_validate_preservation_leverage()` - Generates warning
  - `test_validate_short_horizon_frequent()` - Generates warning
  - `test_validate_small_capital_positions()` - Generates warning
  - `test_validate_valid_config()` - Returns (True, [])

---

## Notes
- **Critical:** This router bridges user input to trading system configuration
- **Academic References:**
  - **Gray & Vogel:** Quantitative Momentum - Momentum strategies for capital appreciation
  - **Berkin & Swedroe:** Factor-Based Investing - Dividend and income strategies
  - **Markowitz:** Portfolio Selection - Low volatility for capital preservation
  - **Fama-French:** Factor Models - Multi-factor for balanced growth
  - **Kissell:** Portfolio Management - Covered calls for income generation
  - **John Hull:** Risk management principles for risk configuration
  - **Grinold & Kahn:** Active portfolio management for rebalancing
- **Strategy Selection Logic:**
  - MAXIMIZAR_CAPITAL → MOMENTUM (aggressive growth)
  - MAXIMIZAR_DIVIDENDOS → DIVIDEND (income focus)
  - CAPITAL_PRESERVATION → LOW_VOLATILITY (risk-averse)
  - BALANCED_GROWTH → MULTI_FACTOR (diversified)
  - INCOME_GENERATION → COVERED_CALL (enhanced yield)
- **Risk Configuration Logic:**
  - BAJO (Low): 15% drawdown, no leverage, 5% max position, 10-50 positions
  - MEDIO (Medium): 25% drawdown, 1.5x leverage, 10% max position, 5-40 positions
  - ALTO (High): 40% drawdown, 2.0x leverage, 20% max position, 3-30 positions
- **Rebalancing Frequency:**
  - Short-term (<6mo): Weekly (7 days)
  - Medium-term (6-23mo): Bi-weekly (14 days)
  - Long-term (24-59mo): Monthly (30 days)
  - Very long-term (>=60mo): Quarterly (90 days)
- **Validation Warnings:**
  - Contradictory objectives (CAPITAL_PRESERVATION + ALTO risk)
  - Leverage with preservation objectives
  - High transaction costs (short horizon + frequent rebalancing)
  - Over-fragmentation (small capital + many positions)
- **SOLID Principles:**
  - SRP: Single responsibility for routing only
  - OCP: Extensible for new strategies without modification
  - DIP: Depends on domain abstractions, not implementations
- **Production Rule:** Always validate configuration consistency before trading

---

**File Reference:** `app/application/routers/input_profile_router.py`
**Last Audited:** 2026-02-01
