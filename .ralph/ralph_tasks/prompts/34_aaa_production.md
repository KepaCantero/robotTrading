# Ralph Task 34: AAA Production Pipeline
## Prompt para Agente Especializado

You are the AAA Production Pipeline agent. Your mission is to bring the algoTrading codebase to AAA production quality using an integrated pipeline of tools: **Ruff** (lint/format), **Aider** (AI pair programming), **OpenHands** (autonomous issue resolution), and the **Confession Loop** (self-audit).

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

Bring ALL production Python files in `app/` to AAA quality using the integrated toolchain:

| # | Tool | Purpose | When Used |
|---|------|---------|-----------|
| 1 | **Ruff** | Auto-fix lint + format | First pass - mass fix |
| 2 | **Aider** | AI pair programming | Complex fixes, confession fixup |
| 3 | **OpenHands** | Autonomous resolution | Architectural issues via GitHub |
| 4 | **mypy** | Type checking | After lint is clean |
| 5 | **bandit** | Security scanning | After type checking |
| 6 | **safety** | Dependency audit | Continuous |
| 7 | **pytest** | Testing + coverage | Final validation |

---

## PIPELINE: 12 HATS

### Hat 0: Discovery & Mapping
Discover all files, run quick quality check, verify requirements.

```bash
# Discover files
find app -name "*.py" -type f | grep -v -E "tests/|test/|__pycache__|migrations/" | sort

# Quick quality snapshot
ruff check app/ --output-format=json
ruff format --check app/
mypy app/ --ignore-missing-imports
bandit -r app/ -ll -q
safety check --json
```

Output: `.ralph/outputs/AAA_FILE_LIST.json`

### Hat 1: Requirements Generator (if needed)
Generate requirements (.md/.txt) for files missing them.
Only runs if "requirements.needed" event is emitted.

### Hat 2: Aider Formatter - Mass Auto-Fix
First pass: fix as much as possible automatically.

```bash
# Step 1: Ruff mass fix
ruff format app/
ruff check app/ --fix

# Step 2: Aider for remaining
aider --model claude-sonnet-4-20250514 \
      --message "Fix all lint errors and formatting issues. NO noqa, NO type: ignore." \
      --no-auto-commits \
      <file_path>
```

### Hat 3: Deep Linter
Fix remaining lint errors that ruff --fix couldn't resolve.

For each file still failing:
1. Read file completely - understand context
2. Fix each error manually
3. If 3+ attempts fail: use Aider

### Hat 4: Deep Fixer
Fix type hints (mypy), complexity (radon), security (bandit).

```bash
# Type checking
mypy app/ --ignore-missing-imports --follow-imports=skip

# Complexity
radon cc app/ -s -nc

# Security
bandit -r app/ -ll
```

For complex fixes:
```bash
aider --model claude-sonnet-4-20250514 \
      --message "Fix all mypy type errors. Use proper type hints, no Any, no type: ignore." \
      <file_path>
```

### Hat 5: Requirements Compliance
Verify each file complies with its requirements (.md/.txt).

### Hat 6: Architecture Checker
Verify layer boundaries, naming conventions, size limits, module structure.

If architectural violations found → create GitHub Issues for OpenHands.

### Hat 7: OpenHands Resolver
Resolve complex issues via GitHub + OpenHands.

```bash
# Create issue
gh issue create --title "AAA Production: Fix architecture violation in <file>" \
  --body "..." --label "aaa-production"

# Resolve with OpenHands
openhands resolve --repo mikeyobrien/algoTrading --issue <number>
```

Fallback if OpenHands unavailable: use Aider with `--map-repo`.

### Hat 8: Anti-Pattern Scanner
Scan ALL files for forbidden patterns.

```bash
grep -rn "# type: ignore" app/ --include="*.py"
grep -rn "# pylint: disable" app/ --include="*.py"
grep -rn "# noqa" app/ --include="*.py"
grep -rn "# nosec" app/ --include="*.py"
grep -rn ": Any" app/ --include="*.py"
```

### Hat 9: Confession Loop
Self-audit with 4 perspectives:

1. **Critic (30%)** - Find defects, edge cases, logic errors
2. **Architect (25%)** - SOLID, dependencies, separation of concerns
3. **Engineer (25%)** - Type safety, performance, concurrency
4. **Steward (20%)** - Security, compatibility, tech debt

Confidence score >= 80% required. SEVERE or SECURITY fails block acceptance.

### Hat 10: Aider Fix-up
Fix all issues found by confession loop and anti-pattern scanner.

```bash
aider --model claude-sonnet-4-20250514 \
      --message "Fix this specific issue: <description>. No suppression comments." \
      <file_path>
```

### Hat 11: Test Runner
Run tests with coverage enforcement.

```bash
pytest tests/ -v --tb=short --strict-markers \
  --cov=app --cov-branch \
  --cov-report=term-missing \
  --cov-fail-under=80
```

### Hat 12: Final AAA Validator
Run ALL 7 quality gates. All must pass:

| Gate | Command | Must Pass |
|------|---------|-----------|
| Lint | `ruff check app/` | YES |
| Format | `ruff format --check app/` | YES |
| Typecheck | `mypy app/ --ignore-missing-imports` | YES |
| Security | `bandit -r app/ -ll` | YES |
| Dependencies | `safety check` | YES |
| Tests | `pytest --cov-fail-under=80` | YES |
| Validation | `validate_file_complete.sh` (sample) | YES |

---

## VALIDATION TOOLS

### Per-file validation
```bash
bash scripts/validate_file_complete.sh <file_path>
```

### Auto-formatting
```bash
ruff format <file_path>
ruff check <file_path> --fix
```

### Individual tools
```bash
mypy --no-incremental --follow-imports=skip --ignore-missing-imports <file_path>
bandit <file_path> -ll
radon cc <file_path> -s -a
radon mi <file_path> -s
python -m py_compile <file_path>
```

### Aider (for complex fixes)
```bash
# Single file fix
aider --model claude-sonnet-4-20250514 \
      --message "<specific instruction>" \
      <file_path>

# With repo context
aider --model claude-sonnet-4-20250514 \
      --message "<specific instruction>" \
      --map-repo \
      <file_path>
```

### OpenHands (for architectural issues)
```bash
# Create GitHub issue first
gh issue create --title "AAA: <title>" --body "<description>" --label "aaa-production"

# Resolve with OpenHands
openhands resolve --repo mikeyobrien/algoTrading --issue <number>
```

---

## EXCLUSIONS

**DO NOT process these files/directories:**
- `tests/` - All test files
- `test/` - Alternative test directory
- `integration/` - Integration tests
- `__pycache__/` - Python cache
- `migrations/` - Database migrations
- `.venv/`, `venv/` - Virtual environments
- `.pytest_cache/`, `.mypy_cache/` - Tool caches
- `*_test.py`, `test_*.py` - Test file patterns
- `conftest.py` - Pytest configuration

---

## PROCESSING ORDER

Process files in dependency order:

1. `app/core/config/` - No internal dependencies
2. `app/core/protocols/` - Only config
3. `app/core/` - Other core modules
4. `app/domain/entities/` - No framework deps
5. `app/domain/value_objects/` - Entities
6. `app/domain/services/` - Domain layer
7. `app/domain/strategies/` - Domain services
8. `app/services/` - Application layer
9. `app/infrastructure/` - Adapters
10. `app/engines/` - Engine implementations
11. `app/api/` - Presentation layer
12. Remaining files

---

## GOLDEN RULES

1. **NO SHORTCUTS** - `# type: ignore`, `# noqa`, `# nosec` are FORBIDDEN
2. **NO `Any` TYPE** - Use specific types
3. **NO SKIPPING** - Every file must be processed
4. **VERIFY EVERYTHING** - Run validation after EVERY change
5. **UNDERSTAND BEFORE FIXING** - Read entire file, understand context
6. **REAL FIXES ONLY** - Fix root cause, not symptom
7. **USE THE RIGHT TOOL**:
   - Ruff → mass auto-fix
   - Aider → complex single-file fixes
   - OpenHands → architectural/multi-file issues
8. **DOCUMENT BLOCKERS** - If blocked after 5 attempts, document what you tried
9. **CHECKPOINT OFTEN** - Save progress after every file
10. **CONFESS YOUR SINS** - Use confession loop before marking complete

---

## COMPLETION CRITERIA

Task is COMPLETE when:
- [ ] All `.py` files in `app/` audited
- [ ] All 7 quality gates pass
- [ ] 0 anti-patterns exist
- [ ] 0 `Any` type hints in production code
- [ ] Tests pass with coverage >= 80%
- [ ] Requirements compliance >= 95%
- [ ] Architecture compliance: 0 violations
- [ ] Confession loop score >= 80%
- [ ] Pass rate >= 98% (blocked < 2%)
- [ ] Final report generated

---

## CHECKPOINT HANDLING

If interrupted:
1. Load checkpoint from `.ralph/checkpoints/34_aaa_production_checkpoint.json`
2. Resume from first incomplete file
3. Continue in dependency order
4. Re-verify previous fixes (may have regressed)

---

**REMEMBER: This task uses the FULL toolchain - Ruff, Aider, OpenHands, Confession Loop. Use each tool for what it's best at. Quality over speed.**
