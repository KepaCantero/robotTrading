# Template: Requirements Document for Python File

Use this template when creating requirements documents for Python files.

## Instructions

Copy this template and fill in all sections for the Python file being documented.

---

# [FileName].py

## Purpose
[Clear description of what this module/file does. Include business context if applicable.]

---

## Type Definitions / Data Classes

### [ClassName/Name] (dataclass/Pydantic/TypedDict)
```python
@dataclass  # or class(BaseModel) or TypedDict
class [ClassName]:
    field_name: FieldType  # REQUIRED/OPTIONAL - Description
    field_name2: FieldType  # REQUIRED/OPTIONAL - Description with default
```

**Validation Rules:**
- [List any validation rules]
- [Mention constraints like min/max values]

---

## Function Signatures (Contracts)

### `function_name(param1: Type, param2: Type) -> ReturnType`
**Pre:** [What must be true before calling]
**Post:** [What is true after calling]
**Raises:** [Exceptions that may be raised]
**Retry:** [Yes/No - Is it retryable?]
**Side Effects:** [What state changes occur]

---

## Acceptance Criteria
- [ ] [Specific, testable condition 1]
- [ ] [Specific, testable condition 2]
- [ ] [Edge case handled]
- [ ] [Error case handled]

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | YYYY-MM-DDTHH:MM:SSZ |
| **Audit Status** | NEEDS_AUDIT / PASSED / FAILED |
| **BASE_RULES Version** | Commit hash or date |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | X / Y total |

**Status meanings:**
- **NEEDS_AUDIT** - File needs to be audited (default for new files or files with changes)
- **PASSED** - All GAP violations fixed, audit passed
- **FAILED** - Audit found violations that need fixing

**When to update:**
- Set to `NEEDS_AUDIT` when file is modified
- Set to `PASSED` after successful audit with timestamp
- Set to `FAILED` if audit finds violations (with list of violations)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| RULE-ID | BASE_RULES | Brief description of rule | ✅ OK / ❌ GAP / ⚠️ NOT APPLIED / ⚠️ PARTIAL |

**Status meanings:**
- ✅ **OK** - Rule is followed correctly
- ❌ **GAP** - Rule is violated (NEEDS FIXING)
- ⚠️ **NOT APPLIED** - Rule doesn't apply (explain why in description)
- ⚠️ **PARTIAL** - Rule partially followed (explain what's missing)

---

## Dependencies
- **External:** [List external packages like numpy, pandas, fastapi]
- **Internal:** [List internal imports like app.domain.entities]

---

## Required Tests
- **tests/[PATH]/test_[FileName].py:**
  - Test [specific functionality]
  - Test [edge case]
  - Test [error condition]
  - Test [integration with X]

---

## Notes
[Known issues, design decisions, references, future improvements]

---

## Example: Filled Template

```markdown
# breadth_calculator.py

## Purpose
Calculate and analyze strategy breadth, which measures the number of independent betting opportunities per year, a critical component of the Fundamental Law of Active Management.

---

## Type Definitions / Data Classes

### BreadthMetrics Class/DataClass (imported from models.py)
```python
@dataclass
class BreadthMetrics:
    annual_breadth: Decimal              # REQUIRED - Total bets per year
    independence_factor: Decimal         # REQUIRED - Correlation adjustment [0, 1]
    effective_breadth: Decimal           # REQUIRED - annual_breadth × independence_factor
    notes: str = ""                      # OPTIONAL - Additional context
```

**Validation Rules:**
- All values must be non-negative
- independence_factor must be in [0, 1]
- effective_breadth = annual_breadth × independence_factor

---

## Function Signatures (Contracts)

### `calculate_breadth(n_assets: int, rebalance_frequency: str, asset_correlation: Optional[pd.DataFrame] = None) -> BreadthMetrics`
**Pre:** n_assets > 0; rebalance_frequency in PERIODS_PER_YEAR keys
**Post:** Returns BreadthMetrics with calculated breadth
**Raises:** ValueError if invalid frequency or n_assets
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Breadth calculation correctly multiplies periods_per_year × n_assets × independence_factor
- [ ] Independence factor uses upper triangle of correlation matrix (excludes diagonal)
- [ ] Invalid rebalance frequencies raise ValueError with list of valid options
- [ ] Correlation matrix validation checks for square shape
- [ ] Returns DataFrame inference handles both DatetimeIndex and numeric indices

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-01-15T10:30:00Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | a1b2c3d (2026-01-10) |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | 5 / 5 total |

**Notes:**
- All GAP violations fixed on 2026-01-15
- LOG-004 and TRD-007 marked as PARTIAL (acceptable)
- File marked as PASSED after audit

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate mathematical relationships | ✅ OK - Independence formula validated |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError with descriptive messages |
| LOG-004 | BASE_RULES | Error logging with stack traces | ⚠️ PARTIAL - No error logging found |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear variable and function names |
| PERF-002 | BASE_RULES | Use vectorized operations | ✅ OK - Uses pandas/numpy vectorized ops |
| TRD-007 | BASE_RULES | Document TRADING_DAYS | ⚠️ PARTIAL - Uses 365.25 and 252 hardcoded |

---

## Dependencies
- **External:** numpy, pandas, decimal, logging, typing
- **Internal:** app.analysis.fundamental_law.models.BreadthMetrics, app.core.decimal_utils.to_decimal

---

## Required Tests
- **tests/unit/analysis/test_breadth_calculator.py:**
  - Test calculate_breadth with weekly frequency (success)
  - Test calculate_breadth with invalid frequency (raises ValueError)
  - Test calculate_independence_factor with uncorrelated assets (returns ~1.0)
  - Test estimate_required_breadth (success)
  - Test estimate_required_breadth with zero IC (raises ValueError)

---

## Notes
- Reference: Grinold & Kahn (2000), "Active Portfolio Management", Chapter 9
- Independence factor formula: IF = 1 / (1 + avg_correlation × (n - 1))
- Periods per year: daily=252, weekly=52, biweekly=26, monthly=12, quarterly=4, annually=1
```

---

## Common Rule Patterns

When filling the "Critical Rules" table, use these patterns:

### Type Hints (TYP-001, TYP-003)
- ✅ OK if all functions have return types
- ❌ GAP if return types missing
- ⚠️ PARTIAL if some functions missing types
- Use specific types, not `Any` (justify if `Any` is necessary)

### Logging (LOG-001, LOG-004)
- ✅ OK if structured logging with keyword args
- ❌ GAP if using f-strings in logging
- ❌ GAP if error logging missing `exc_info=True`
- Example: `logger.info("Processing trade", symbol=symbol, qty=qty)`

### Error Handling (CC-006)
- ✅ OK if specific exceptions (ValueError, TypeError)
- ❌ GAP if catching generic `Exception`
- ❌ GAP if bare `except:`

### Trading Rules (TRD-001, TRD-005, TRD-007)
- ✅ OK if inputs validated
- ❌ GAP if no price/quantity validation
- ⚠️ NOT APPLIED if not trading-related

### Architecture (ARCH-004, ARCH-006)
- ✅ OK if functions < 20 lines
- ❌ GAP if functions > 50 lines
- ✅ OK if dataclass is frozen=True

---

## How to Use This Template

1. **Copy** this template
2. **Rename** to `[FileName].requirements.md`
3. **Read** the Python file
4. **Read** BASE_RULES.md
5. **Fill** all sections:
   - Extract classes and their fields
   - List all functions with signatures
   - Document pre/post conditions
   - Check each rule from BASE_RULES
   - Mark status as OK/GAP/NOT APPLIED/PARTIAL
6. **Save** to `.requirements/[PATH]/[FileName].requirements.md`
