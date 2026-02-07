# Requirements: services/expensive_module_gate.py

**See ../../BASE_RULES.md for universal rules**

## Source File Analysis
- **File Path**: `app/services/expensive_module_gate.py`
- **Lines of Code**: 410
- **Purpose**: Prevents expensive computational modules on small accounts (cost optimization)
- **Status**: PRODUCTION READY

## Module Purpose
Prevents initialization of computationally expensive modules on small accounts where their cost exceeds the value they generate. Enforces minimum capital thresholds and provides cost-benefit analysis for:
- DeepLearningEngine, TransformerEngine, ReinforcementLearningEngine
- MultiTaskLearningEngine, TransferLearning, HyperparameterOptimizer
- Feature Importance Analysis

## Dependencies
### Internal
- None (standalone service)

### External
- `decimal.Decimal`: Precise financial calculations
- `enum.Enum`: ExpenseLevelEnum classification
- `logging`: Standard logging
- `typing.Dict`, `typing.Tuple`: Type hints

## Classes and Functions

### Classes/Enums
- **`ExpenseLevelEnum` (str, Enum)**: Cost classification
  - CHEAP (<0.1% of capital/month)
  - MODERATE (0.1-0.5% of capital/month)
  - EXPENSIVE (0.5-2% of capital/month)
  - VERY_EXPENSIVE (>2% of capital/month)

- **`ExpensiveModuleGate`**: Module gatekeeping logic
  - Static methods for module enablement decisions
  - MODULES dict with module definitions (7 modules)
  - Capital tier classification

### Key Methods (Static)
- **`should_enable_module(module_name, capital, expected_monthly_alpha, enforce_strict_cost_ratio)`**:
  Returns (enabled: bool, analysis: Dict) - Main decision logic

- **`get_enabled_modules(capital, expected_monthly_alpha, enforce_strict_cost_ratio)`**:
  Returns (enabled_modules: Dict, analysis: Dict) - Batch evaluation

- **`get_recommended_modules(capital)`**:
  Returns Dict[module_name -> bool] - Capital tier recommendations

- **`get_total_expensive_module_cost(capital, enabled_modules)`**:
  Returns Decimal - Total monthly cost calculation

- **`log_module_decision(module_name, capital, analysis, account_id)`**:
  Returns str - Audit logging

- **`get_cost_summary(capital, enabled_modules, expected_monthly_alpha)`**:
  Returns Dict - Cost metrics and recommendations

- **`_get_capital_tier(capital)`**:
  Returns str - "micro" (<$15k), "small" ($15k-$50k), "medium" ($50k-$250k), "large" (>$250k)

## Business Logic

### Decision Flow
1. Validate capital > 0
2. Check if module exists in registry
3. Enforce minimum capital threshold OR cost-benefit ratio (<30% of alpha)
4. Return enabled/disabled with detailed analysis

### Capital Tiers
- **micro** (<$15k): All expensive modules DISABLED
- **small** ($15k-$50k): Most modules DISABLED
- **medium** ($50k-$250k): Moderate and some expensive enabled
- **large** (>$250k): All modules enabled

### Module Definitions
Each module has:
- expense_level: CHEAP/MODERATE/EXPENSIVE/VERY_EXPENSIVE
- monthly_cost_pct: Decimal percentage of capital
- min_capital: Minimum viable capital threshold
- description: What the module does
- benefits: Value proposition
- fallback: Simpler alternative module

## Data Models
- Module definition dict (MODULES class attribute)
- Analysis dict: enabled, reason, recommendation, cost_estimate_monthly, cost_ratio, capital_tier

## API Contracts
```python
@staticmethod
def should_enable_module(
    module_name: str,
    capital: Decimal,
    expected_monthly_alpha: Decimal = Decimal("100"),
    enforce_strict_cost_ratio: bool = False,
) -> Tuple[bool, Dict]
```

## Error Handling
- Input validation (capital must be positive)
- Graceful handling of unknown modules (returns "NOT_FOUND")
- Division by zero protection (cost_ratio calculation)

## Performance Considerations
- O(1) lookups for module decisions
- O(n) for batch evaluation (n = number of modules)
- No external API calls (pure computation)

## Testing Strategy
- Unit: Test capital tier thresholds
- Unit: Test module enablement logic
- Unit: Test cost calculation accuracy
- Edge: Zero/negative capital
- Edge: Unknown module names

## Economics & Rationale
Expensive modules require significant infrastructure:
- GPU/CPU time for model training
- Memory for model storage
- Storage for model artifacts
- Development and maintenance overhead

Better to use simple, deterministic strategies on small accounts and upgrade modules only when capital and trading volume increase.

## BASE_RULES Compliance

### Critical Rules (P0)
- ✅ **CC-003 (KISS)**: Simple, straightforward decision logic
- ✅ **CC-006 (CC-007)**: Small functions, explicit error handling
- ✅ **CFG-002**: No hardcoded configuration (uses parameters)

### Code Quality (QL-001, QL-005)
- ✅ Functions under 40 lines
- ✅ Clear, descriptive names
- ✅ Minimal complexity (if-else logic only)

### Type Hints (TYP-001, TYP-002)
- ✅ All functions have type hints
- ✅ Modern syntax (Tuple[bool, Dict])
- ✅ Return types clearly specified

### Logging (LOG-001, LOG-003)
- ✅ Structured logging with context
- ✅ Appropriate levels (info/warning)
- ✅ Audit trail via log_module_decision()

## Audit Status

**Status:** PASSED
**Date:** 2026-02-07
**Auditor:** Claude Code (Batch 0070-0071-0072 GAP Audit)
**GAPs Found:** 0 critical, 0 high priority
**Risk Level:** LOW - Configuration logic with no external dependencies

### Verification Results
- All BASE_RULES verified
- No P0/P1 violations
- Code is production-ready
- Proper economic justification documented
- Capital tier thresholds are reasonable for trading costs

### Notes
- Module definitions could be externalized to config (future enhancement)
- Cost percentages are estimates and should be validated against actual infrastructure costs
- Fallback module recommendations are valuable for degraded mode operation
- Logging provides good audit trail for cost optimization decisions

---
*Updated: 2026-02-07*
*Batch: 0070*
