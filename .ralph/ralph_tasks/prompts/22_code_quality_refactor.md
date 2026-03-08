# Ralph Task 22: Code Quality Refactor - Production-Ready
## Prompt para Agente Especializado

You are a specialized code quality refactoring agent for PRODUCTION-READY code. Your task is to review and fix ALL Python files in the `app/` directory to ensure:

1. **Centralized Modular Config**: All configurable parameters use the centralized config system
2. **No Hardcoded Values**: No magic numbers hardcoded in code
3. **Specialized Libraries**: Use numpy/pandas/scipy for calculations instead of manual implementations
4. **PRODUCTION-READY ONLY**: No incomplete implementations, no TODOs, no stubs, no placeholders

---

## VERSION 9.0 - WORKFLOW PER FILE

**ARCHITECTURE - FILE BY FILE:**

```
FOR EACH FILE:
┌─────────────────────────────────────────────────────────────────┐
│  File 1: app/services/example.py                               │
│                                                                  │
│  1. AUDIT   → Grep: "0\.02|0\.05|0\.15" in file                  │
│  2. READ    → Read file to understand context                   │
│  3. FIX     → Edit: Replace with getattr(config.trading, ...)   │
│  4. VALIDATE→ Grep: Verify no hardcoded values remain          │
│  ✓ Complete → Move to next file                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  File 2: app/strategies/pairs_trading.py                       │
│  1. AUDIT → 2. READ → 3. FIX → 4. VALIDATE → ✓ Complete       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                           ... (426 files)
```

**CRITICAL - WORKFLOW PER FILE:**
- **ONE file at a time** - Complete full cycle before next file
- **NO bulk operations** - Don't audit all, then fix all
- **Audit → Fix → Validate** per file
- **Track progress** - Report every 10 files

---

## CURRENT AUDIT RESULTS (2026-02-10)

**Claude direct audit using Grep:**

Total problems identified: **426+ files with hardcoded values**

### Breakdown by pattern:
- **0.02 (R1 Kelly 2%)**: 120 files
- **0.05 (5% thresholds)**: 169 files
- **0.1 (10% thresholds)**: 160 files
- **0.15 (R2 Drawdown)**: 102 files
- **0.19 (Spain IRPF)**: 9 files
- **0.21 (Spain IRPF)**: 5 files
- **0.23 (Spain IRPF)**: 3 files
- **2.0 (R4 R:R ratio)**: Found in strategy files

### Breakdown by type:
- **Trading Rule Violations (R1-R29)**: 179 issues
  - R1 (Kelly 2% max): 119 violations - hardcoded 0.02 should use config
  - R2 (Drawdown 15%): 41 violations - hardcoded 0.15/0.25 should use config
  - R4 (R:R 2:1): 49 violations - hardcoded 2.0 should use config
- **Spain Tax Violations**: 33 issues
  - IRPF rates (0.19, 0.21, 0.23) should use config.spain_tax
  - Dividendos UE, Modelo 720 violations
- **NotImplementedError**: 8 issues (mainly in tomasini_event_queue.py)
- **TODO comments**: 2 issues

### Files with most issues:
1. app/application/services/input_profile_router.py (8 issues)
2. app/services/risk_management_chan.py (6 issues)
3. app/services/risk_scaling/limit_adjuster.py (6 issues)
4. app/portfolio/multi_asset/asset_class.py (6 issues)
5. app/strategies/pairs_trading.py (5 issues)

---

## TRADING RULES (from rules/trading/)

### R1: Kelly Criterion + 2% max position size
- **Rule**: Validate order value <= 2% of available cash
- **Implementation**: Use `getattr(config.trading, 'max_risk_per_trade', 0.02)`
- **Reference**: rules/trading/:210-222

### R2: Drawdown 15% stop trading
- **Rule**: Stop trading when drawdown >= 15%
- **Implementation**: Use `getattr(config.compliance, 'max_drawdown_pct', 0.15)`
- **Reference**: rules/trading/:224-233

### R4: Risk-Reward 2:1 minimum
- **Rule**: Validate RR ratio >= 2.0 before trade
- **Implementation**: Use `getattr(config.trading, 'min_rr_ratio', 2.0)`
- **Reference**: rules/trading/:235-250

---

## SPAIN TAX RULES (from rules/trading/)

### IRPF Progresivo (19/21/23%)
- Use `getattr(config.spain_tax, 'irpf_rate_19', 0.19)`
- Use `getattr(config.spain_tax, 'irpf_rate_21', 0.21)`
- Use `getattr(config.spain_tax, 'irpf_rate_23', 0.23)`

### Dividendos UE (0% withholding)
- Use `getattr(config.spain_tax, 'eu_dividend_withholding_pct', 0.0)`

### Modelo 720 (>€50k extranjeros)
- Use `getattr(config.spain_tax, 'modelo_720_threshold_eur', 50000)`

---

## CONTEXT

### Modular Config Architecture

The project has a modular configuration system in `app/core/config/`:

- `base.py` - Environment, SettingsBase, get_config()
- `signal_risk.py` - SignalThresholds, RiskManagementThresholds, CircuitBreakerThresholds
- `position_sizing.py` - PositionSizingThresholds, PortfolioAllocationThresholds
- `technical_indicators.py` - TechnicalIndicatorThresholds, WindowSizes
- `infrastructure.py` - DatabaseConfig, RedisConfig, APIConfig
- `compliance.py` - ComplianceConfig
- `trading_config.py` - CentralizedConfig, TradingThresholds (main aggregated config)

### Correct Usage Pattern

```python
from app.core.config.base import get_config

config = get_config()
# For trading thresholds
value = Decimal(str(getattr(config.trading, 'parameter_name', default_value)))
# For compliance
compliance_value = getattr(config.compliance, 'parameter_name', default_value)
```

### What Should Be Configured

**MUST use config:**
- Percentage thresholds (0.05, 0.02, 0.15, etc.)
- Risk limits (drawdown, exposure, position sizing)
- Time intervals (check_interval_seconds, etc.)
- Multipliers and factors
- Default values for fallback scenarios

**ACCEPTABLE as hardcoded:**
- Mathematical constants (0, 1, -1, 2, etc.)
- Conversion factors (100 for %, 10000 for bps)
- Array indices (-1 for last)
- Loop ranges (for i in range(10))

### Production-Ready Requirements

**CRITICAL**: Every fix must be production-ready. Do NOT leave:
- `TODO` comments
- `FIXME` comments
- Placeholder implementations
- Stub methods with `pass`
- Incomplete error handling
- Missing type hints
- Missing docstrings on public functions

---

## PHASE 1: INVENTORY - Dependency-Aware Ordering

**CRITICAL:** Files MUST be processed in dependency order to avoid breaking changes.

### Processing Order (10 Phases)

Files are categorized and processed in this specific order:

1. **Phase 1: Configuration Files** (`app/core/config/`)
   - `base.py` - Defines `get_config()` - MUST BE FIRST
   - `trading_config.py` - Aggregates all config - SECOND
   - Other config modules (signal_risk, position_sizing, etc.)
   - **Reason:** All other files depend on `get_config()`

2. **Phase 2: Interfaces and Protocols** (`app/core/protocols/`, `app/interfaces/`)
   - Protocol definitions
   - Abstract base classes
   - **Reason:** Implementations depend on protocols being defined first

3. **Phase 3: Base Utilities** (`app/core/utils/`, `app/utils/`)
   - `decimal_utils.py`
   - `reconnection_manager.py`
   - `centralized_config.py`
   - **Reason:** Foundational utilities with minimal dependencies

4. **Phase 4: Models and Entities** (`app/models/`, `app/domain/entities/`)
   - `order.py`, `signal.py`, `position.py`, `portfolio.py`
   - **Reason:** Services depend on models, not vice versa

5. **Phase 5: Core Services** (`app/core/`, `app/domain/services/`)
   - `compliance_engine.py`
   - `trading_validators.py`
   - Portfolio services, position sizing, signal evaluation
   - **Reason:** Foundational for trading logic

6. **Phase 6: Execution Services** (`app/services/execution/`, `signal_execution_engine.py`)
   - Order execution, position management
   - **Reason:** Depends on core services (compliance, position sizing)

7. **Phase 7: Trading Strategies** (`app/strategies/`, `app/domain/strategies/`)
   - All strategy implementations (momentum, pairs trading, etc.)
   - **Reason:** Strategies depend on all services above

8. **Phase 8: Backtesting** (`app/backtesting/`)
   - `engine.py`, slippage models, backtest orchestration
   - **Reason:** Depends on strategies and compliance engine

9. **Phase 9: Analysis** (`app/analysis/`, `app/market_microstructure/`)
   - Fundamental law analysis, OFI, market microstructure
   - **Reason:** Analysis depends on backtesting results

10. **Phase 10: Remaining Files**
    - Any files not caught by previous phases
    - **Reason:** Catch-all for edge cases

### Inventory Process

1. List all `.py` files in `app/` directory (excluding tests)
2. Categorize files into one of 10 phases based on path
3. Sort files alphabetically within each phase
4. Generate ordered file list: `.ralph/outputs/files_list.txt`
5. Generate phase summary: `.ralph/outputs/files_by_phase.json`

```json
{
  "total_files": 400,
  "phases": {
    "phase_1_config": {
      "priority": 1,
      "count": 7,
      "files": ["app/core/config/base.py", "app/core/config/trading_config.py", ...]
    },
    "phase_2_interfaces": {
      "priority": 2,
      "count": 3,
      "files": ["app/core/protocols/trading.py", ...]
    },
    ...
  },
  "timestamp": "2026-02-10T10:00:00Z"
}
```

---

## PHASE 2: AUDIT

For each file, audit for:

### 2.1 Hardcoded Values Detection

Search patterns:
- `Decimal("0.XX")` - Hardcoded decimal thresholds
- `0.XX` in numeric context - Hardcoded float thresholds
- `"value"` in numeric comparisons

Examples of BAD code:
```python
# BAD
if exposure_pct > Decimal("0.35"):  # Hardcoded!
    urgency = "immediate"

# BAD
volatility_threshold = 0.02  # Hardcoded!

# BAD
max_drawdown = 0.15  # Hardcoded!
```

### 2.2 Manual Calculation Detection

Search for:
- Manual standard deviation: `sqrt(sum((x - mean)**2) / n)`
- Manual correlation: `sum((x - mean_x)*(y - mean_y)) / ...`
- Manual percentiles: `sorted_values[int(len * 0.5)]`
- Manual variance: `sum((x - mean)**2) / len`
- Manual moving averages: `for loops with rolling sums`

Examples of BAD code:
```python
# BAD - Manual std
mean = sum(values) / len(values)
variance = sum((x - mean)**2 for x in values) / len(values)
std = sqrt(variance)

# GOOD - Use numpy
import numpy as np
std = np.std(values)

# BAD - Manual percentile
sorted_vals = sorted(values)
median = sorted_vals[int(len(values) * 0.5)]

# GOOD - Use numpy
median = np.percentile(values, 50)

# BAD - Manual moving average
ma_values = []
for i in range(len(prices) - window + 1):
    ma_values.append(sum(prices[i:i+window]) / window)

# GOOD - Use pandas
import pandas as pd
ma_values = pd.Series(prices).rolling(window).mean()
```

### 2.3 Incomplete Implementation Detection

Search for:
- `TODO`, `FIXME`, `XXX`, `HACK` comments
- `pass` statements with placeholder comments
- `raise NotImplementedError`
- Stub methods without real implementation

Examples of UNACCEPTABLE code:
```python
# UNACCEPTABLE - TODO comment
def calculate_risk(self):
    # TODO: Implement risk calculation
    pass

# UNACCEPTABLE - NotImplementedError
def validate_position(self, position):
    raise NotImplementedError("Position validation not implemented")

# UNACCEPTABLE - Stub with placeholder
def process_signal(self, signal):
    pass  # Placeholder

# PRODUCTION-READY - Complete implementation
def calculate_risk(self) -> Decimal:
    """
    Calculate portfolio risk using VaR methodology.

    Returns:
        Decimal: Risk amount in portfolio currency
    """
    try:
        config = get_config()
        var_limit_pct = Decimal(str(getattr(
            config.trading, 'var_max_limit_pct', 0.02
        )))
        portfolio_value = self._get_portfolio_value()
        return portfolio_value * var_limit_pct
    except (ValueError, AttributeError, KeyError) as e:
        logger.error(f"Error calculating risk: {e}")
        return Decimal("0")
```

### 2.4 Config Usage Audit

Check:
- Does file import `get_config`?
- Are numeric thresholds using `getattr(config.trading, ...)`?
- Are config fields missing from `trading_config.py`?
- Are type hints present on all functions?
- Are docstrings present on public functions?

Generate audit findings:

```json
{
  "file": "app/services/signal_execution_engine.py",
  "issues": [
    {
      "type": "hardcoded_value",
      "line": 150,
      "code": "if exposure > Decimal('0.35'):",
      "severity": "HIGH",
      "suggestion": "Use config.trading.currency_urgency_immediate"
    },
    {
      "type": "manual_calculation",
      "line": 200,
      "code": "std = math.sqrt(sum(...))",
      "severity": "MEDIUM",
      "suggestion": "Use np.std()"
    },
    {
      "type": "incomplete_implementation",
      "line": 75,
      "code": "raise NotImplementedError",
      "severity": "HIGH",
      "suggestion": "Implement the functionality properly"
    },
    {
      "type": "missing_type_hints",
      "line": 100,
      "code": "def process_signal(signal):",
      "severity": "MEDIUM",
      "suggestion": "Add return type hint -> SignalResult"
    }
  ]
}
```

---

## PHASE 3: FIX

For EACH file with issues:

### 3.1 Add Missing Config Fields

If a hardcoded value needs config, add to `app/core/config/trading_config.py`:

```python
# In TradingThresholds class
parameter_name: float = Field(
    default=0.05,  # The hardcoded value
    ge=0.0, le=1.0,
    description="Clear description of what this parameter does"
)
```

**Naming conventions:**
- Use descriptive names: `max_drawdown_pct` not `md`
- Include units in name if applicable: `_pct`, `_bps`, `_seconds`
- Group related parameters with common prefix

### 3.2 Fix Hardcoded Values

Replace hardcoded with config:

```python
# BEFORE
if exposure_pct > Decimal("0.35"):
    urgency = "immediate"

# AFTER
config = get_config()
urgency_immediate = Decimal(str(getattr(
    config.trading, 'currency_urgency_immediate', 0.35
)))
if exposure_pct > urgency_immediate:
    urgency = "immediate"
```

### 3.3 Refactor Manual Calculations

Replace with library functions:

```python
# BEFORE
def calculate_std(values):
    """Calculate standard deviation."""
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean)**2 for x in values) / len(values))

# AFTER - Production-ready
import numpy as np
from typing import List, Union
from decimal import Decimal

def calculate_std(values: List[Union[float, Decimal]]) -> float:
    """
    Calculate standard deviation using numpy.

    Args:
        values: List of numeric values

    Returns:
        float: Standard deviation of the values

    Raises:
        ValueError: If values list is empty
    """
    if not values:
        raise ValueError("Cannot calculate std of empty list")

    try:
        return float(np.std(values))
    except (TypeError, ValueError) as e:
        raise ValueError(f"Error calculating std: {e}") from e
```

For calculations with existing imports:
- Already have numpy/pandas: Use them directly
- Don't have imports: Add imports and use library functions

### 3.4 Complete Incomplete Implementations

For every TODO/FIXME/stub found:

1. **If functionality is needed**: Implement it properly with:
   - Complete logic (no placeholders)
   - Type hints on all parameters and return
   - Docstring explaining purpose
   - Error handling with try-except
   - Logging for errors

2. **If functionality is NOT needed**: Remove the code entirely

```python
# EXAMPLE 1: Implement properly
# BEFORE:
def validate_order(self, order):
    # TODO: Add validation
    pass

# AFTER:
def validate_order(self, order: Order) -> ValidationResult:
    """
    Validate order before execution.

    Args:
        order: Order to validate

    Returns:
        ValidationResult with pass/fail status
    """
    try:
        config = get_config()
        min_order_size = Decimal(str(getattr(
            config.trading, 'min_order_size', 0.01
        )))

        if order.quantity < min_order_size:
            return ValidationResult(
                passed=False,
                message=f"Order size {order.quantity} below minimum {min_order_size}"
            )

        return ValidationResult(passed=True, message="Order valid")

    except (ValueError, AttributeError) as e:
        logger.error(f"Error validating order: {e}")
        return ValidationResult(passed=False, message=f"Validation error: {e}")
```

### 3.5 Fix Files One by One - In Dependency Order

**CRITICAL:** Process files in the exact order from Phase 1 inventory (10 phases).

**Do NOT skip phases or process out of order.**

For each file (in dependency order):
1. Read the file completely
2. Identify all issues from audit
3. Add missing config fields to `trading_config.py` (if in Phase 1, add directly; if in later phases, ensure field exists)
4. Fix hardcoded values using config pattern
5. Refactor manual calculations to use libraries
6. Complete/remove incomplete implementations
7. Add missing type hints
8. Add missing docstrings
9. Add error handling where missing
10. Verify fixes don't break logic
11. Run syntax check
12. Mark file as fixed in tracking report
13. **Only after ALL files in a phase are complete, move to next phase**

---

## PHASE 4: VALIDATE

After fixing all files:

### 4.1 Hardcoded Value Check

Run comprehensive grep:
```bash
# Find remaining hardcoded decimals
grep -r 'Decimal("0\.[0-9]\+")' app/ --include="*.py" | grep -v test

# Find remaining hardcoded floats (avoiding version numbers)
grep -rn '\b0\.[0-9]\+\b' app/ --include="*.py" | grep -v test | grep -v ".pyc" | grep -v "version" | grep -v "python [0-9]"
```

### 4.2 Incomplete Implementation Check

```bash
# Check for TODO/FIXME comments
grep -rn "TODO\|FIXME\|XXX\|HACK" app/ --include="*.py" | grep -v test

# Check for stub implementations
grep -rn "pass.*#.*\(stub\|placeholder\|not implemented\)" app/ --include="*.py"

# Check for NotImplementedError
grep -rn "raise NotImplementedError" app/ --include="*.py" | grep -v test
```

### 4.3 Config Usage Check

Verify:
- All numeric thresholds use `getattr(config.trading, ...)`
- Fallback defaults match original hardcoded values
- No direct numeric comparisons without config

### 4.4 Library Usage Check

Verify:
- No manual std/correlation/percentile/variance calculations
- `import numpy as np` where calculations exist
- `import pandas as pd` where time series/dataframes exist
- Using vectorized operations instead of loops

### 4.5 Type Hints Check

```bash
# Verify type hints with pyright or mypy
python -m pyright app/**/*.py
```

### 4.6 Generate Final Report

```json
{
  "task": "CODE_QUALITY_REFACTOR",
  "status": "COMPLETE",
  "summary": {
    "total_files": 400,
    "files_with_issues": 87,
    "files_fixed": 87,
    "config_fields_added": 156,
    "hardcoded_values_fixed": 312,
    "calculations_refactored": 34,
    "incomplete_implementations_removed": 23
  },
  "production_ready": true,
  "validation_results": {
    "hardcoded_decimals_found": 0,
    "hardcoded_floats_found": 0,
    "incomplete_implementations_found": 0,
    "missing_type_hints": 0,
    "missing_docstrings": 0
  },
  "changes_by_file": [
    {
      "file": "app/services/currency_hedging_engine.py",
      "hardcoded_fixed": 12,
      "config_fields_added": ["currency_urgency_immediate", "currency_default_correlation"],
      "calculations_refactored": 1,
      "incomplete_removed": 0,
      "production_ready": true
    },
    ...
  ],
  "timestamp": "2026-02-10T18:00:00Z"
}
```

---

## PRODUCTION-READY CHECKLIST

Each file MUST pass ALL these checks before being marked as complete:

- [ ] No hardcoded Decimal("0.XX") values
- [ ] No hardcoded 0.XX float thresholds
- [ ] All numeric thresholds use `getattr(config.trading, ...)` with defaults
- [ ] No manual calculations (std, corr, percentile, variance, MA)
- [ ] All calculations use numpy/pandas/scipy
- [ ] No TODO/FIXME/XXX/HACK comments
- [ ] No `raise NotImplementedError`
- [ ] No stub methods with `pass`
- [ ] All functions have return type hints
- [ ] All public functions have docstrings
- [ ] All functions have error handling (try-except or documented raises)
- [ ] Config fields added to trading_config.py for all parameters
- [ ] Code follows PEP 8 style guidelines
- [ ] No syntax errors (verified with python -m py_compile)

---

## IMPORTANT NOTES

1. **Backward Compatibility**: Always use `getattr()` with defaults
   ```python
   value = getattr(config.trading, 'parameter_name', default_value)
   ```

2. **Type Consistency**: Convert config values to proper types
   ```python
   # For Decimal
   value = Decimal(str(getattr(config.trading, 'param', 0.05)))

   # For float
   value = float(getattr(config.trading, 'param', 0.05))
   ```

3. **File by File**: Process one file at a time to ensure quality

4. **Tests**: Skip test files, only fix production code

5. **Documentation**: Add clear Field descriptions for new config fields

6. **Error Handling**: All functions must have try-except or documented raises

7. **Type Hints**: All functions must have parameter and return type hints

8. **Docstrings**: All public functions must have Google-style docstrings

---

## CHECKPOINT HANDLING

If execution is interrupted:
1. Load last checkpoint to see progress
2. Resume from first incomplete file
3. Update tracking report as files are fixed
4. Save checkpoint after each file

Checkpoint structure:
```json
{
  "files_audited": ["app/services/file1.py", ...],
  "files_fixed": ["app/services/file1.py", ...],
  "config_fields_added": {
    "app/services/file1.py": ["param1", "param2"]
  },
  "current_file": "app/services/file2.py",
  "incomplete_removed": 15
}
```

---

## COMPLETION CRITERIA

Task is COMPLETE when:
- [ ] All `.py` files in `app/` (excluding tests) have been audited
- [ ] No hardcoded Decimal("0.XX") values remain
- [ ] No hardcoded 0.XX float thresholds remain
- [ ] All numeric thresholds use config with getattr()
- [ ] All manual calculations use numpy/pandas/scipy
- [ ] No TODO/FIXME/incomplete implementations remain
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] All functions have proper error handling
- [ ] Final report generated with all changes documented
- [ ] Config fields added for all hardcoded values found
- [ ] All validation checks pass (grep, pyright, etc.)

---

Start with inventory, then audit systematically, fix file by file with production-ready code, and validate thoroughly.

REMEMBER: **Production-ready means COMPLETE implementation, NOT placeholders or TODOs.**
