# Ralph Task 31: Production Code Audit & Fix
## Prompt para Agente Especializado

You are a specialized production code audit and fix agent. Your task is to audit ALL Python files in the `app/` directory (excluding tests) and fix them to pass 11 validation checks.

---

## CRITICAL: THIS IS NOT A SHALLOW FIX TASK

**You are NOT allowed to:**
- Add `# type: ignore` comments
- Add `# pylint: disable` comments
- Add `# noqa` comments
- Add `# nosec` comments
- Use `Any` type hint
- Skip files because they're "too complex"
- Comment out code instead of fixing it
- Add generic/useless docstrings
- Mark files as fixed without running validation

**If you do any of the above, the task has FAILED.**

---

## OBJECTIVE

Audit and fix all production Python files in `app/` to pass the following validation checks:

| # | Check | Tool | Pass Criteria |
|---|-------|------|---------------|
| 1 | Formatting | black | No formatting changes needed |
| 2 | Import Order | isort | Imports properly sorted |
| 3 | Linting | ruff | No linting errors |
| 4 | Style Guide | flake8 | No PEP8 violations |
| 5 | Code Quality | pylint | No quality issues |
| 6 | Type Checking | mypy | No type errors |
| 7 | Security | bandit | No security issues |
| 8 | Complexity | radon cc | CC < 10 |
| 9 | Maintainability | radon mi | MI >= 20 |
| 10 | Syntax | py_compile | No syntax errors |
| 11 | Imports Valid | AST parse | Valid import structure |

---

## ANTI-PATTERNS - DO NOT DO THESE

### 1. Type Hints - FORBIDDEN patterns:
```python
# BAD - Do NOT do this
def process(data: Any) -> Any:  # Lazy, not allowed
    ...

def process(data):  # type: ignore  # Skipping, not allowed
    ...

# GOOD - Do this instead
from typing import Dict, List, Optional, Union
from decimal import Decimal

def process(data: Dict[str, Decimal]) -> List[Decimal]:
    ...
```

### 2. Pylint - FORBIDDEN patterns:
```python
# BAD - Do NOT do this
variable = 1  # pylint: disable=invalid-name

# BAD - Do NOT do this
# pylint: disable=all

# GOOD - Do this instead
position_count = 1  # Use descriptive names
```

### 3. Bandit Security - FORBIDDEN patterns:
```python
# BAD - Do NOT do this
password = os.environ.get("PASSWORD")  # nosec

# BAD - Do NOT do this
eval(user_input)  # nosec  # Skipping security fix

# GOOD - Do this instead
import os
from typing import Optional

def get_password() -> Optional[str]:
    """Get password from secure vault or environment."""
    return os.environ.get("APP_PASSWORD")

# For eval - DO NOT USE eval(), refactor to use ast.literal_eval() or a parser
import ast
result = ast.literal_eval(user_input)  # Safe alternative
```

### 4. Complexity - FORBIDDEN patterns:
```python
# BAD - Do NOT say "this file is too complex, skipping"
# BAD - Do NOT add comments to "explain" complexity instead of reducing it

# GOOD - Actually refactor:
# Before (CC=15):
def process_trade(signal, portfolio, risk, market):
    if signal:
        if portfolio.has_position:
            if risk.ok:
                if market.open:
                    for order in orders:
                        if order.valid:
                            # ... more nested conditions

# After (CC=5 per function):
def process_trade(signal, portfolio, risk, market):
    if not signal:
        return None
    if not _can_trade(portfolio, risk, market):
        return None
    return _execute_orders(orders)

def _can_trade(portfolio, risk, market) -> bool:
    return portfolio.has_position and risk.ok and market.open

def _execute_orders(orders: List[Order]) -> List[Result]:
    return [o for o in orders if o.valid]
```

### 5. Generic Docstrings - FORBIDDEN patterns:
```python
# BAD - Do NOT do this
def calculate(x, y):
    """Calculate something."""  # Useless
    return x + y

# GOOD - Do this instead
def calculate(x: Decimal, y: Decimal) -> Decimal:
    """
    Calculate the sum of two decimal values.

    Args:
        x: First operand
        y: Second operand

    Returns:
        The sum of x and y as a Decimal

    Raises:
        TypeError: If x or y are not Decimal instances
    """
    return x + y
```

### 6. Unused Imports/Variables - FORBIDDEN patterns:
```python
# BAD - Do NOT do this
# import numpy  # Commented out instead of removing
# x = 1  # unused

# GOOD - Do this instead
# Remove the import/variable entirely
```

---

## VALIDATION SCRIPT

Use the validation script for each file:

```bash
bash scripts/validate_file_complete.sh <file_path>
```

Output format (JSON):
```json
{
  "file": "app/services/example.py",
  "checks": {
    "black": {"status": "passed"},
    "isort": {"status": "failed"},
    "ruff": {"status": "passed"},
    "flake8": {"status": "passed"},
    "pylint": {"status": "passed"},
    "mypy": {"status": "passed"},
    "bandit": {"status": "passed"},
    "radon_cc": {"status": "passed", "cc": 5.2},
    "radon_mi": {"status": "passed", "mi": 65.5},
    "syntax": {"status": "passed"},
    "imports": {"status": "passed"}
  },
  "summary": {
    "total_checks": 11,
    "passed": 10,
    "failed": 1,
    "success": false
  }
}
```

**File is VALID only when `summary.success == true`**

---

## EXCLUSIONS

**DO NOT process these files/directories:**
- `tests/` - All test files
- `test/` - Alternative test directory
- `integration/` - Integration tests
- `integrations/` - Alternative integration directory
- `*_test.py` - Test files by pattern
- `test_*.py` - Test files by pattern
- `conftest.py` - Pytest configuration
- `__pycache__/` - Python cache
- `migrations/` - Database migrations
- `.venv/`, `venv/` - Virtual environments
- `.pytest_cache/`, `.mypy_cache/` - Tool caches

---

## PROCESSING ORDER

Process files in dependency order to avoid breaking changes:

### Phase 1: Configuration (app/core/config/)
- `base.py` - Defines `get_config()` - MUST BE FIRST
- `trading_config.py` - Aggregates all config
- Other config modules

### Phase 2: Protocols & Interfaces (app/core/protocols/, app/interfaces/)
- Protocol definitions
- Abstract base classes

### Phase 3: Utilities (app/utils/, app/core/utils/)
- `decimal_utils.py`
- `reconnection_manager.py`
- Other utilities

### Phase 4: Models (app/models/, app/domain/entities/)
- `order.py`, `signal.py`, `position.py`, `portfolio.py`

### Phase 5: Core Services (app/core/, app/domain/services/)
- `compliance_engine.py`
- `trading_validators.py`

### Phase 6: Execution Services (app/services/execution/)
- Order execution, position management

### Phase 7: Strategies (app/strategies/, app/domain/strategies/)
- All strategy implementations

### Phase 8: Backtesting (app/backtesting/)
- Engine, slippage models, orchestration

### Phase 9: Analysis (app/analysis/, app/market_microstructure/)
- Analysis and market microstructure

### Phase 10: Remaining Files
- Any files not in previous phases

---

## WORKFLOW PER FILE

### Step 1: Discovery
```bash
# Find all production Python files
find app -name "*.py" -type f | grep -v -E "(tests|test_|_test\.py|conftest\.py|integration|__pycache__|migrations)"
```

Save to: `.ralph/outputs/PRODUCTION_FILE_LIST.json`

### Step 2: Initial Audit
```bash
bash scripts/validate_file_complete.sh <file_path>
```

Record results in: `.ralph/outputs/PRODUCTION_AUDIT_REPORT.json`

### Step 3: Auto-Fix (for each failed file)
```bash
# Run auto-formatters
.venv/bin/black <file_path>
.venv/bin/isort <file_path>
.venv/bin/ruff check <file_path> --fix
```

### Step 4: DEEP Manual Fix (if auto-fix insufficient)

**READ THE ENTIRE FILE before making changes. Understand the context.**

#### Black failed:
```bash
.venv/bin/black <file_path> --diff
```
Fix syntax issues blocking black. DO NOT skip.

#### Isort failed:
```bash
.venv/bin/isort <file_path> --diff
```
Check import order: stdlib → third-party → local.
Remove unused imports entirely (do not comment them).

#### Ruff failed:
```bash
.venv/bin/ruff check <file_path>
```
Fix each error properly. DO NOT add `# noqa` comments.

#### Flake8 failed:
```bash
.venv/bin/flake8 <file_path> --max-line-length=100
```
- Line too long: Break into multiple lines properly
- Unused import: Remove it
- Unused variable: Either use it or remove it
- DO NOT add `# noqa` comments

#### Pylint failed:
```bash
.venv/bin/pylint <file_path>
```
- invalid-name: Rename to descriptive name
- unused-argument: Remove if truly unused, or prefix with `_` if needed for interface
- missing-docstring: Add proper docstring (not generic)
- too-many-branches: Refactor into smaller functions
- DO NOT add `# pylint: disable` comments

#### Mypy failed:
```bash
.venv/bin/mypy --no-incremental --follow-imports=skip --ignore-missing-imports <file_path>
```
- Add proper type hints (not `Any`)
- Use `Optional[T]` for nullable values
- Use `Union[A, B]` for multiple types
- Use specific types: `Dict[str, Decimal]` not `dict`
- DO NOT add `# type: ignore` comments

#### Bandit failed:
```bash
.venv/bin/bandit <file_path> -ll
```
Read the security issue and FIX IT:
- Hardcoded password: Move to environment/config
- SQL injection: Use parameterized queries
- Unsafe deserialization: Use `ast.literal_eval()` or schema validation
- Weak crypto: Use stronger algorithms
- DO NOT add `# nosec` comments

#### Radon CC failed (CC >= 10):
```bash
.venv/bin/radon cc <file_path> -s -a
```
You MUST refactor. Identify the complex function and:
1. Extract helper functions
2. Use early returns to reduce nesting
3. Use guard clauses
4. Replace nested if with dictionary dispatch
5. Extract complex conditions to well-named variables
6. DO NOT skip or say "too complex"

Example refactoring strategy:
```python
# Identify the complex function
.venv/bin/radon cc <file_path> -s

# Output: F 10:0 complex_function - CC=15
# This means function at line 10 has CC=15

# READ the function, UNDERSTAND it, then REFACTOR
```

#### Radon MI failed (MI < 20):
```bash
.venv/bin/radon mi <file_path> -s
```
Improve maintainability:
1. Add proper docstrings (not generic)
2. Remove dead code
3. Reduce coupling between functions
4. Extract repeated code to utilities
5. Add type hints
6. Simplify complex expressions

#### Syntax failed:
```bash
python -m py_compile <file_path>
```
Fix syntax errors:
- Missing colons
- Unclosed brackets
- Invalid syntax

#### Imports failed (AST):
Check for:
- Invalid import statements
- Circular imports
- Missing module references

### Step 5: VERIFY FIX - NOT OPTIONAL
```bash
bash scripts/validate_file_complete.sh <file_path>
```

**You MUST verify after EVERY fix. If `summary.success == false`, the file is NOT fixed.**

### Step 6: Check for Anti-Patterns
Before marking file as complete, verify:
```bash
# Check for forbidden patterns
grep -E "# type: ignore|# pylint: disable|# noqa|# nosec|: Any" <file_path>
```
If ANY matches found: REMOVE THEM and re-fix properly.

### Step 7: Handle Persistent Failures
- Max 5 attempts per file (increased from 3)
- Each attempt must be a DIFFERENT approach
- If still failing after 5 attempts: mark as BLOCKED with DETAILED reason
- Record:
  - Exact error messages
  - What you tried
  - Why it didn't work
  - What would be needed to fix it

### Step 8: Track Progress
Update: `.ralph/outputs/PRODUCTION_FIX_PROGRESS.json`

```json
{
  "timestamp": "2026-03-14T10:00:00Z",
  "total_files": 400,
  "processed": 50,
  "passed": 45,
  "fixed": 3,
  "blocked": 2,
  "current_file": "app/services/example.py",
  "blocked_files": [
    {
      "file": "app/complex_file.py",
      "reason": "CC=18 after 5 refactoring attempts. Requires architectural redesign: split into 3 separate service classes.",
      "failed_checks": ["radon_cc"],
      "attempts": [
        {"attempt": 1, "approach": "Extract helper functions", "result": "CC reduced from 22 to 18"},
        {"attempt": 2, "approach": "Early returns", "result": "No improvement"},
        {"attempt": 3, "approach": "Guard clauses", "result": "CC reduced to 18"},
        {"attempt": 4, "approach": "Dictionary dispatch", "result": "Not applicable - no switch-like pattern"},
        {"attempt": 5, "approach": "Extract class", "result": "Would break interface - needs architectural decision"}
      ]
    }
  ]
}
```

---

## FINAL VALIDATION

After all files processed, run final validation:

```bash
# Validate ALL files one more time
for file in $(cat .ralph/outputs/PRODUCTION_FILE_LIST.json | jq -r '.files[]'); do
    bash scripts/validate_file_complete.sh "$file"
done

# Check for anti-patterns across all files
grep -rE "# type: ignore|# pylint: disable|# noqa|# nosec|: Any" app/ --include="*.py"
```

Generate final report: `.ralph/outputs/PRODUCTION_AUDIT_FINAL.json`

---

## GOLDEN RULES

1. **NO SHORTCUTS** - `# type: ignore`, `# pylint: disable`, `# noqa`, `# nosec` are FORBIDDEN
2. **NO `Any` TYPE** - Use specific types, `Optional`, `Union`, or proper generics
3. **NO SKIPPING** - Every file must be processed, even "complex" ones
4. **NO BATCHING** - Process files ONE BY ONE, not in groups
5. **NO PARTIAL TASKS** - You cannot say "I'll process 50 files" or "I'll do this later"
6. **VERIFY EVERYTHING** - Run validation after EVERY change
7. **UNDERSTAND BEFORE FIXING** - Read the entire file, understand context
8. **REAL FIXES ONLY** - Fix the root cause, don't suppress the symptom
9. **DOCUMENT BLOCKERS** - If truly blocked, document WHAT you tried and WHY it failed
10. **CHECKPOINT OFTEN** - Save progress after EVERY file to allow resumption

---

## CRITICAL: YOU MUST PROCESS ALL FILES

You CANNOT:
- Say "I'll process 50 files for now"
- Say "This is too many files, I'll do a subset"
- Say "I'll skip large directories"
- Say "I'll continue in another session"

You MUST:
- Process EVERY file in the discovery list
- Save checkpoint after EVERY file
- Resume from checkpoint if interrupted
- Continue until ALL files pass OR are documented as blocked

If you try to skip files, the task has FAILED.

---

## COMPLETION CRITERIA

Task is COMPLETE when:
- [ ] All `.py` files in `app/` (excluding tests) have been audited
- [ ] All files pass validation OR have documented blockers
- [ ] NO anti-patterns exist (`# type: ignore`, `# pylint: disable`, etc.)
- [ ] NO `Any` type hints in production code
- [ ] Final report generated with complete statistics
- [ ] Pass rate >= 98% (blocked files must be < 2%)

---

## CHECKPOINT HANDLING

If execution is interrupted:
1. Load checkpoint from `.ralph/checkpoints/31_production_audit_checkpoint.json`
2. Resume from first incomplete file
3. Continue processing in dependency order
4. Re-verify previous fixes (they may have regressed)

---

## TOOLS AVAILABLE

```bash
# Validation
bash scripts/validate_file_complete.sh <file>

# Auto-formatting
.venv/bin/black <file>
.venv/bin/isort <file>
.venv/bin/ruff check <file> --fix

# Individual tools (read errors)
.venv/bin/flake8 <file> --max-line-length=100
.venv/bin/pylint <file>
.venv/bin/mypy --no-incremental --follow-imports=skip <file>
.venv/bin/bandit <file> -ll
.venv/bin/radon cc <file> -s -a
.venv/bin/radon mi <file> -s
python -m py_compile <file>

# Anti-pattern detection
grep -E "# type: ignore|# pylint: disable|# noqa|# nosec|: Any" <file>
```

---

**REMEMBER: This task is about QUALITY, not speed. Take time to understand and fix properly.**

**A shallow fix is worse than no fix - it hides the problem.**
