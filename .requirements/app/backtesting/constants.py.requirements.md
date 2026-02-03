# constants.py

## Purpose
Centralized configuration for all backtesting constants, replacing magic numbers across capital_scale_analyzer.py, execution_engine.py, and related modules with type-safe, documented dataclasses.

---

## Type Definitions / Data Classes

### CapitalScaleConstants (Dataclass)
```python
@dataclass
class CapitalScaleConstants:
    # Capital levels for multi-scale analysis
    DEFAULT_CAPITAL_LEVELS: List[Decimal] = [
        Decimal("1000"),   # Micro account
        Decimal("5000"),   # Small account
        Decimal("10000"),  # Medium account
        Decimal("50000"),  # Pro account
        Decimal("100000"), # Fund account
    ]

    # ADV (Average Daily Volume) limits
    ADV_LIMIT_PCT_DEFAULT: Decimal = Decimal("0.02")              # 2% ADV rule
    ADV_FILL_RATIO_REJECT_THRESHOLD: Decimal = Decimal("0.5")     # Reject if fill < 50%

    # Commission impact thresholds
    COMMISSION_IMPACT_WARNING_THRESHOLD: Decimal = Decimal("0.15")    # 15% - trigger warning
    COMMISSION_IMPACT_CRITICAL_THRESHOLD: Decimal = Decimal("0.20")   # 20% - reject strategy
    COMMISSION_IMPACT_OPTIMAL_THRESHOLD: Decimal = Decimal("0.15")    # 15% - optimal capital selection

    # Alpha degradation
    ALPHA_DEGRADATION_THRESHOLD: Decimal = Decimal("0.50")            # 50% degradation max acceptable

    # Commission models by capital level
    COMMISSION_MODELS: Dict[Decimal, Dict[str, Any]] = {
        Decimal("1000"): {
            "type": "fixed",
            "cost": Decimal("5.0"),
            "description": "Micro account - high fixed fees"
        },
        Decimal("5000"): {
            "type": "fixed",
            "cost": Decimal("3.0"),
            "description": "Small account - reduced fixed fees"
        },
        Decimal("10000"): {
            "type": "hybrid",
            "min_cost": Decimal("1.0"),
            "rate": Decimal("0.001"),
            "description": "Medium account - hybrid structure"
        },
        Decimal("50000"): {
            "type": "tiered",
            "brackets": [...],
            "description": "Pro account - tiered pricing"
        },
        Decimal("100000"): {
            "type": "tiered",
            "brackets": [...],
            "description": "Fund account - institutional pricing"
        }
    }

    # Scalability score weights (max 100 points total)
    SCALABILITY_ALPHA_DEGRADATION_MAX_POINTS: Decimal = Decimal("40")  # Alpha degradation score
    SCALABILITY_COMMISSION_MAX_POINTS: Decimal = Decimal("30")          # Commission impact score
    SCALABILITY_STABILITY_MAX_POINTS: Decimal = Decimal("30")           # Win rate stability score

    # Commission impact score thresholds
    COMMISSION_IMPACT_EXCELLENT_THRESHOLD: Decimal = Decimal("0.10")   # < 10% = excellent
    COMMISSION_IMPACT_GOOD_THRESHOLD: Decimal = Decimal("0.15")        # < 15% = good
    COMMISSION_IMPACT_POOR_THRESHOLD: Decimal = Decimal("0.15")        # >= 15% = poor

    # Win rate stability
    WIN_RATE_STABILITY_PENALTY_FACTOR: Decimal = Decimal("100")        # Multiplier for std dev penalty
```

**Validation Rules:**
- All Decimal values must be created with string constructor for precision
- Capital levels must be ascending order
- Commission thresholds: warning < critical
- Score weights must sum to 100
- ADV limit must be positive decimal < 1.0

### ExecutionEngineConstants (Dataclass)
```python
@dataclass
class ExecutionEngineConstants:
    # Slippage settings (in basis points)
    BASE_SLIPPAGE_BPS: Decimal = Decimal("5")              # 5 bps base slippage
    OPTIMISTIC_SLIPPAGE_BPS: Decimal = Decimal("2")        # 2 bps for optimistic mode
    STOP_SLIPPAGE_MULTIPLIER: Decimal = Decimal("2")       # 2x slippage on stops

    # Volatility multiplier
    VOLATILITY_MULTIPLIER: Decimal = Decimal("2")          # 2x slippage for high volatility

    # Execution timing
    ENABLE_NEXT_DAY_EXECUTION: bool = True                 # Signal at close t, execute at open t+1
```

**Validation Rules:**
- Slippage must be positive Decimal values
- Multipliers must be >= 1.0
- Base slippage > optimistic slippage

### BacktestingConstants (Dataclass)
```python
@dataclass
class BacktestingConstants:
    capital_scale: CapitalScaleConstants = field(default_factory=CapitalScaleConstants)
    execution: ExecutionEngineConstants = field(default_factory=ExecutionEngineConstants)
```

---

## Function Signatures (Contracts)

### `get_default_capital_levels() -> List[Decimal]`
**Pre:** None
**Post:** Returns copy of DEFAULT_CAPITAL_LEVELS list (prevents mutation)
**Raises:** No
**Retry:** No
**Side Effects:** None (pure function, returns copy)

### `get_commission_models() -> Dict[Decimal, Dict[str, Any]]`
**Pre:** None
**Post:** Returns copy of COMMISSION_MODELS dict (prevents mutation)
**Raises:** No
**Retry:** No
**Side Effects:** None (pure function, returns copy)

### `get_base_slippage_bps() -> Decimal`
**Pre:** None
**Post:** Returns BASE_SLIPPAGE_BPS value
**Raises:** No
**Retry:** No
**Side Effects:** None

### `get_adv_limit_pct() -> Decimal`
**Pre:** None
**Post:** Returns ADV_LIMIT_PCT_DEFAULT value
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-CON-001: All Decimal values use string constructor for precision
- [ ] AC-CON-002: Capital levels are in ascending order (1000, 5000, 10000, 50000, 100000)
- [ ] AC-CON-003: Commission model brackets are valid (volume_max ascending)
- [ ] AC-CON-004: Score weights sum to 100 (40 + 30 + 30)
- [ ] AC-CON-005: Singleton instance BACKTESTING_CONSTANTS is immutable
- [ ] AC-CON-006: Convenience functions return copies (prevent mutation)
- [ ] AC-CON-007: All thresholds are documented with units (%, bps, Decimal)
- [ ] AC-CON-008: Commission models have all required fields (type, cost/rate, description)

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

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | BASE_RULES | No mutable defaults - use field_factory | ✅ OK |
| TYP-001 | BASE_RULES | Type hints on all class attributes | ✅ OK |
| ARCH-006 | BASE_RULES | Value objects immutable - use @dataclass | ✅ OK (no frozen=True but uses factory) |
| CC-003 | BASE_RULES | KISS - simple dataclass constants | ✅ OK |
| CFG-003 | BASE_RULES | Configuration validation | ⚠️ PARTIAL - No validators on dataclasses |
| TRD-006 | BASE_RULES | Transaction costs included in models | ✅ OK |

### Trading-Specific Rules

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| BT-004 | BASE_RULES | Realistic costs - slippage and commissions defined | ✅ OK |
| TRD-006 | BASE_RULES | Transaction costs model by capital level | ✅ OK |
| EXE-002 | BASE_RULES | Execution timing - next day execution flag | ✅ OK |

**NOTE:** This analysis considers all 96 rules from BASE_RULES.md

---

## Dependencies
- **External:** None (only stdlib: dataclasses, decimal, typing)
- **Internal:** None (constants module has no internal dependencies)

---

## Required Tests
- **tests/backtesting/test_constants.py:**
  - Test BACKTESTING_CONSTANTS singleton is accessible
  - Test DEFAULT_CAPITAL_LEVELS contains all 5 levels in ascending order
  - Test COMMISSION_MODELS has entries for all 5 capital levels
  - Test COMMISSION_MODELS structure is valid (type, cost/rate, description)
  - Test commission thresholds: warning < critical
  - Test score weights sum to 100
  - Test slippage values are positive Decimals
  - Test get_default_capital_levels returns copy (mutation doesn't affect original)
  - Test get_commission_models returns copy (mutation doesn't affect original)
  - Test get_base_slippage_bps returns correct value
  - Test get_adv_limit_pct returns correct value
  - Test ADV limit is 2% (0.02 Decimal)
  - Test alpha degradation threshold is 50% (0.50 Decimal)
  - Test commission impact thresholds follow: excellent < good = poor
  - Test execution engine constants have valid values
  - Test ENABLE_NEXT_DAY_EXECUTION is True

---

## Notes
Replaces magic numbers scattered across backtesting modules. Uses dataclass factory pattern to prevent mutable default arguments. All Decimal values use string constructor for financial precision. Singleton pattern via module-level BACKTESTING_CONSTANTS instance.
