# Ralph Task 35: Fix Pytest - Unit Tests Green
## Prompt para Agente Especializado

You are the Fix Pytest Unit Tests agent. A massive refactoring has happened in the production codebase. The tests are **completely broken**. Your mission is to **rewrite the unit tests from scratch** based on the current API, make them all pass, and achieve >= 80% coverage — **without touching any production code**.

---

## ⛔ ABSOLUTE RULES

**You are NOT allowed to:**
- Modify ANY file under `app/` (production code)
- Modify ANY file under `tests/integration/`
- Add `@pytest.mark.skip` or `pytest.xfail`
- Comment out tests
- Use `# type: ignore` in test files
- Use `try/except pass` to silence errors
- Delete tests to make the suite pass

**If you modify `app/` code, the task has FAILED.**

---

## 🔄 STRATEGY: REWRITE > FIX

After a massive refactoring, most tests are broken beyond repair. **Rewriting is faster and safer than fixing.**

**Decision criteria for each test file:**
- **REWRITE** (most files): Test has collection error (won't compile) OR 3+ failures OR structural/API changes
- **FIX_MINOR** (rare exception): Test has only 1-2 simple import path errors, rest is fine
- **DELETE**: Test targets a module that no longer exists after the refactor

**Rewriting means:**
1. Clear the entire test file content
2. Read the source file in `app/` (READ ONLY)
3. Understand the CURRENT API (classes, methods, signatures, exceptions)
4. Write fresh tests based on the CURRENT API
5. Mock all external dependencies
6. Each test < 1 second, no real connections

---

## SCOPE: ONLY tests/unit/

This task is **exclusively** about `tests/unit/`. Integration tests are **read-only**.

---

## PRINCIPLES: FAST AND MINIMAL

Every test must be:
- **< 1 second** to execute
- **No real connections** (no DBs, brokers, APIs, network)
- **No large data files**
- **No sleeps, waits, or timeouts**
- **Mock everything external** with `unittest.mock.MagicMock` / `patch`
- **Minimal fixtures** — only what the assert needs

---

## KNOWN REFACTORING CHANGES

- `app/domain/services/execution/*` → `app/infrastructure/execution/*`
- Many other modules likely moved/renamed/removed during the refactor

---

## PIPELINE: 6 HATS

### Hat 0: Unit Test Discovery & Classification
Diagnose `tests/unit/` and classify each file as REWRITE / FIX_MINOR / OK.

```bash
python -m pytest tests/unit/ --collect-only -q 2>&1 | tee .ralph/outputs/unit_collection.txt
python -m pytest tests/unit/ -v --tb=short --no-header 2>&1 | tee .ralph/outputs/unit_run_full.txt
```

Output: `.ralph/outputs/UNIT_TEST_DIAGNOSIS.json`
```json
{
  "total_test_files": 0,
  "rewrite": ["tests/unit/path/test_broken.py"],
  "fix_minor": ["tests/unit/path/test_almost_ok.py"],
  "ok": ["tests/unit/path/test_good.py"],
  "source_files_without_tests": ["app/path/module.py"]
}
```

### Hat 1: Test Rewriter (tests/unit/ ONLY)
**REWRITE** all broken test files from scratch. **DO NOT modify `app/`.**

For each file classified as REWRITE:
1. Clear the test file content
2. Find the source file: `find app -name "<module>.py" -type f`
3. Read the source (READ ONLY) to understand the CURRENT API
4. Write fresh tests:
   - Import from the NEW module path
   - Mock all external dependencies
   - Test the current API signatures
   - Each test < 1 second

For FIX_MINOR files: just update the import paths.

Template for rewritten tests:
```python
"""Tests for <module>."""
import pytest
from unittest.mock import MagicMock, patch

from app.infrastructure.execution.module import ClassName


@pytest.fixture
def instance():
    """Minimal fixture - mock everything external."""
    with patch("app.infrastructure.execution.module.ExternalDep"):
        return ClassName()


class TestClassName:
    def test_init(self, instance):
        assert instance is not None

    def test_method_happy_path(self, instance):
        with patch.object(instance, "_call", return_value=MagicMock(status="ok")):
            result = instance.public_method()
        assert result is not None

    def test_error(self, instance):
        with patch.object(instance, "_call", side_effect=ValueError):
            with pytest.raises(ValueError):
                instance.public_method()
```

If a source module was deleted in the refactor → DELETE the test file.

### Hat 2: Rewrite Validator
Verify rewritten tests pass. Fix any edge cases.

```bash
python -m pytest tests/unit/ -v --tb=long --no-header 2>&1 | tee .ralph/outputs/unit_validation.txt
```

For any remaining failures:
1. Read error + test file + source file
2. Fix the test only
3. If can't fix after 2 attempts → rewrite that test file again
4. If source module doesn't exist → delete the test

### Hat 3: Coverage Analyzer
```bash
python -m pytest tests/unit/ --cov=app --cov-branch \
  --cov-report=term-missing \
  --cov-report=json:.ralph/outputs/coverage.json \
  -q --no-header
```

Prioritize by coverage impact:
1. Large files with 0% coverage
2. `app/domain/`, `app/services/`, `app/infrastructure/`, `app/engines/`

### Hat 4: Unit Test Writer
Generate **fast, minimal** unit tests for uncovered modules. **DO NOT modify `app/`.**

Same rewrite principles: read source, understand current API, mock everything, < 1s per test.

### Hat 5: Final Validator
```bash
python -m pytest tests/unit/ -v --tb=short --strict-markers \
  --cov=app --cov-branch \
  --cov-report=term-missing \
  --cov-report=json:.ralph/outputs/coverage_final.json \
  --cov-report=html:htmlcov \
  --cov-report=xml:coverage.xml \
  --cov-fail-under=80
```

**Verify no production code was touched:**
```bash
git diff --name-only app/ 2>/dev/null
# MUST be empty
```

---

## IMPORTANT NOTES

1. **`python -m pytest`** — always, not bare `pytest`
2. **Python 3.9** — no newer features
3. **pytest-asyncio**: `asyncio_mode = "auto"`
4. **Work dir**: `/Users/kepa.cantero/Projects/algoTrading`

---

## COMPLETION CRITERIA

1. `pytest tests/unit/ --collect-only` → 0 errors
2. `pytest tests/unit/` → exit code 0
3. `pytest tests/unit/ --cov-fail-under=80` → exit code 0
4. `git diff --name-only app/` → empty

Emit: `PYTEST_GREEN_COMPLETE`
