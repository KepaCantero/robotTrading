# Ralph Task 31: Production Code Audit & Fix
## Prompt para Agente Especializado

You are a specialized production code audit and fix agent. Your task is to audit ALL Python files in the `app/` directory (excluding tests) and fix them to pass 11 validation checks.

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

### Step 4: Manual Fix (if auto-fix insufficient)

#### Black failed:
```bash
.venv/bin/black <file_path> --diff
```
Fix syntax issues blocking black.

#### Isort failed:
```bash
.venv/bin/isort <file_path> --diff
```
Check import order: stdlib → third-party → local

#### Ruff failed:
```bash
.venv/bin/ruff check <file_path>
```
Fix each error manually.

#### Flake8 failed:
```bash
.venv/bin/flake8 <file_path> --max-line-length=100
```
Fix line length, unused imports, etc.

#### Pylint failed:
```bash
.venv/bin/pylint <file_path>
```
Fix naming, unused variables, docstrings.

#### Mypy failed:
```bash
.venv/bin/mypy --no-incremental --follow-imports=skip --ignore-missing-imports <file_path>
```
Add missing type hints.

#### Bandit failed:
```bash
.venv/bin/bandit <file_path> -ll
```
Fix security issues:
- Hardcoded passwords/secrets
- SQL injection vulnerabilities
- Unsafe deserialization
- Weak cryptography

#### Radon CC failed (CC >= 10):
```bash
.venv/bin/radon cc <file_path> -s
```
Refactor complex functions:
- Break into smaller functions
- Reduce nested conditionals
- Extract helper methods

#### Radon MI failed (MI < 20):
```bash
.venv/bin/radon mi <file_path> -s
```
Improve maintainability:
- Add docstrings
- Reduce coupling
- Simplify logic
- Remove dead code

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

### Step 5: Re-Validate
```bash
bash scripts/validate_file_complete.sh <file_path>
```

### Step 6: Handle Persistent Failures
- Max 3 attempts per file
- If still failing after 3 attempts: mark as BLOCKED
- Record blocking reason
- Continue to next file

### Step 7: Track Progress
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
      "reason": "Could not reduce CC below 10 after 3 attempts",
      "failed_checks": ["radon_cc"]
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
```

Generate final report: `.ralph/outputs/PRODUCTION_AUDIT_FINAL.json`

```json
{
  "task": "PRODUCTION_AUDIT",
  "status": "COMPLETE",
  "timestamp": "2026-03-14T18:00:00Z",
  "summary": {
    "total_files": 400,
    "all_passed": 395,
    "blocked": 5,
    "pass_rate": "98.75%"
  },
  "validation_details": {
    "black": {"passed": 400, "failed": 0},
    "isort": {"passed": 400, "failed": 0},
    "ruff": {"passed": 398, "failed": 2},
    "flake8": {"passed": 400, "failed": 0},
    "pylint": {"passed": 395, "failed": 5},
    "mypy": {"passed": 380, "failed": 20},
    "bandit": {"passed": 400, "failed": 0},
    "radon_cc": {"passed": 398, "failed": 2},
    "radon_mi": {"passed": 395, "failed": 5},
    "syntax": {"passed": 400, "failed": 0},
    "imports": {"passed": 400, "failed": 0}
  },
  "blocked_files": [
    {
      "file": "app/complex_strategy.py",
      "reason": "CC=15, architecture redesign required",
      "failed_checks": ["radon_cc"]
    }
  ]
}
```

---

## GOLDEN RULES

1. **NO EXCEPTIONS** - A file is only valid when `summary.success == true`
2. **TRUST TOOLS** - Don't rely on judgment, rely on validation output
3. **ONE FILE AT A TIME** - Complete full cycle before moving to next file
4. **VALIDATE AFTER EVERY FIX** - Never assume a fix worked without validation
5. **RECORD BLOCKED FILES** - If 3 attempts fail, record and continue
6. **DEPENDENCY ORDER** - Process files in phases to avoid breaking changes

---

## COMPLETION CRITERIA

Task is COMPLETE when:
- [ ] All `.py` files in `app/` (excluding tests) have been audited
- [ ] All auto-fixable issues have been fixed
- [ ] Blocked files have been documented with reasons
- [ ] Final report generated with complete statistics
- [ ] Pass rate >= 95% OR blocked files documented

---

## CHECKPOINT HANDLING

If execution is interrupted:
1. Load checkpoint from `.ralph/checkpoints/31_production_audit_checkpoint.json`
2. Resume from first incomplete file
3. Continue processing in dependency order

---

## TOOLS AVAILABLE

```bash
# Validation
bash scripts/validate_file_complete.sh <file>

# Auto-formatting
.venv/bin/black <file>
.venv/bin/isort <file>
.venv/bin/ruff check <file> --fix

# Individual tools
.venv/bin/flake8 <file> --max-line-length=100
.venv/bin/pylint <file>
.venv/bin/mypy --no-incremental --follow-imports=skip <file>
.venv/bin/bandit <file> -ll
.venv/bin/radon cc <file> -s
.venv/bin/radon mi <file> -s
python -m py_compile <file>
```

---

Start with discovery, then audit systematically, fix file by file, and validate thoroughly.

**REMEMBER: Only trust the validation script output. If `summary.success == false`, the file is NOT fixed.**
