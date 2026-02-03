# Plan: Fix GAP Violations - Phase 2

## Overview
Systematic audit and fix of Python files in batches of 10, processing from lowest layer (fewer dependencies) to highest. Each file goes through: requirements check/creation → GAP analysis → fix violations → tests → code review → final audit.

## Context
- **Repository:** `/Users/kepa.cantero/Projects/algoTrading`
- **BASE_RULES:** `.requirements/BASE_RULES.md` (96+ universal rules)
- **File Requirements:** `.requirements/[PATH]/[FileName].requirements.md`
- **Script:** `scripts/list_files_for_audit.py`
- **Templates:** `.claude/templates/refactor/` and `.claude/templates/gap/`

## Validation Commands
```bash
# Syntax check
python -m py_compile {{FILE}}

# Type check (if available)
mypy --strict {{FILE}} || true

# Lint (if available)
ruff check {{FILE}} || true

# Format check (if available)
black --check {{FILE}} || true

# Run tests for specific file
pytest tests/$(dirname {{FILE}})/test_$(basename {{FILE}}) -v || true
```

---

### Task 1: Get first batch of files (Layer 10: Data Layer)
- [ ] Run script to get files in dependency order: `python scripts/list_files_for_audit.py --format text | head -20`
- [ ] Identify first 10 files from Layer 10 (app/database/*.py) that need audit
- [ ] Create a list with full paths for processing
- [ ] Store the file list in a temporary file: `echo "FILE_LIST" > /tmp/batch1_files.txt`

### Task 2: Process Batch 1 - File 1 (app/database/models.py)
- [ ] Check if requirements exist at `.requirements/app/database/models.py.requirements.md`
- [ ] If NO requirements: Read `.claude/templates/gap/REQUIREMENT_TEMPLATE.md` and create requirements document following the template structure
- [ ] If YES requirements exist: Read `.requirements/app/database/models.py.requirements.md`
- [ ] Read `.claude/templates/gap/GAP_ANALYSIS_OUTPUT.md` and analyze `app/database/models.py` against BASE_RULES and file-specific requirements
- [ ] Generate structured list of violations with Rule ID, line numbers, and descriptions
- [ ] If violations found: Read `.claude/templates/refactor/IMPLEMENTER_DATA.md` and fix violations in `app/database/models.py` using minimal changes
- [ ] Run validation commands for the file
- [ ] If test file exists at `tests/app/database/test_models.py`: update it; otherwise create new test file following `.claude/templates/refactor/TESTER_DATA.md`
- [ ] Run pytest for the specific test file
- [ ] Perform code review following `.claude/templates/refactor/CODE_REVIEWER_DATA.md` guidelines
- [ ] If all checks pass: Update requirements document with `## Audit Status: PASSED` and timestamp
- [ ] Commit changes with message: "GAP audit: app/database/models.py - PASSED"

### Task 3: Process Batch 1 - File 2 (app/database/repositories.py)
- [ ] Check if requirements exist at `.requirements/app/database/repositories.py.requirements.md`
- [ ] If NO requirements: Create requirements document using REQUIREMENT_TEMPLATE.md
- [ ] If YES: Read existing requirements
- [ ] Analyze file against BASE_RULES and file-specific requirements (GAP_ANALYSIS_OUTPUT.md pattern)
- [ ] Generate violations list
- [ ] Fix violations using IMPLEMENTER_DATA.md approach (minimal changes only)
- [ ] Run validation commands
- [ ] Create/update test file at `tests/app/database/test_repositories.py`
- [ ] Run pytest for specific test
- [ ] Code review using CODE_REVIEWER_DATA.md guidelines
- [ ] Update requirements with PASSED status and timestamp
- [ ] Commit changes: "GAP audit: app/database/repositories.py - PASSED"

### Task 4: Process remaining 8 files from Batch 1 (Layer 10)
- [ ] For each remaining file in Layer 10 (from script output):
  - [ ] Execute same workflow as Task 2-3 (requirements → analyze → fix → test → review → audit)
  - [ ] Files to process: check script output for complete list
  - [ ] Commit each file individually after PASSED status
- [ ] Verify all Layer 10 files have PASSED status
- [ ] Run full test suite for database layer: `pytest tests/app/database/ -v`

### Task 5: Get and process Batch 2 (Layer 9: Core Layer)
- [ ] Run script again: `python scripts/list_files_for_audit.py --format text`
- [ ] Identify files from Layer 9 (app/core/*.py)
- [ ] Process each file using same 6-step workflow:
  1. Check/create requirements
  2. GAP analysis against BASE_RULES + file requirements
  3. Fix violations (minimal changes)
  4. Create/update tests
  5. Code review
  6. Audit and mark PASSED
- [ ] Commit each file after PASSED
- [ ] Run layer test suite: `pytest tests/app/core/ -v`

### Task 6: Get and process Batch 3 (Layer 7: Domain Entities)
- [ ] Run script: `python scripts/list_files_for_audit.py --format text`
- [ ] Process app/domain/entities/*.py files
- [ ] Execute 6-step workflow for each file
- [ ] Commit individually
- [ ] Run layer tests: `pytest tests/app/domain/entities/ -v`

### Task 7: Get and process Batch 4 (Layer 6: Domain Services)
- [ ] Run script for remaining files
- [ ] Process app/domain/services/*.py and app/domain/strategies/*.py
- [ ] Execute 6-step workflow for each file
- [ ] Commit individually
- [ ] Run layer tests: `pytest tests/app/domain/ -v`

### Task 8: Get and process Batch 5 (Layer 8: Application)
- [ ] Run script for remaining files
- [ ] Process app/application/**/*.py files
- [ ] Execute 6-step workflow for each file
- [ ] Commit individually
- [ ] Run layer tests: `pytest tests/app/application/ -v`

### Task 9: Get and process Batch 6 (Layers 3-5: Backtesting)
- [ ] Run script for remaining files
- [ ] Process app/backtesting/**/*.py files
- [ ] Execute 6-step workflow for each file
- [ ] Commit individually
- [ ] Run layer tests: `pytest tests/app/backtesting/ -v`

### Task 10: Get and process Batch 7 (Layer 11 & 1: Analysis + Microstructure)
- [ ] Run script for remaining files
- [ ] Process app/analysis/**/*.py and app/market_microstructure/**/*.py
- [ ] Execute 6-step workflow for each file
- [ ] Commit individually
- [ ] Run layer tests for both: `pytest tests/app/analysis/ tests/app/market_microstructure/ -v`

### Task 11: Get and process Batch 8 (Layers 12-13: API & Middleware)
- [ ] Run script for remaining files
- [ ] Process app/api/*.py and app/middleware/*.py (highest layers)
- [ ] Execute 6-step workflow for each file
- [ ] Commit individually
- [ ] Run layer tests: `pytest tests/app/api/ tests/app/middleware/ -v`

### Task 12: Final validation and summary
- [ ] Run final script check: `python scripts/list_files_for_audit.py --format text`
- [ ] Verify all files show PASSED status
- [ ] Run complete test suite: `pytest tests/ -v --ignore=tests/test_*.py`
- [ ] Generate summary report:
  - Total files audited
  - Total violations fixed by category (LOG-*, TYP-*, CC-*, etc.)
  - Files with PASSED status
  - Test coverage statistics
- [ ] Create final commit: "GAP Phase 2 Complete - All files audited and PASSED"
- [ ] Move this plan to completed folder

---

## 6-Step Workflow Reference (for each file)

**Step 1: Requirements Check/Creation**
- Check: `.requirements/[PATH]/[FILE].requirements.md` exists?
- If NO: Use `.claude/templates/gap/REQUIREMENT_TEMPLATE.md` to create
- If YES: Read and proceed

**Step 2: GAP Analysis**
- Template: `.claude/templates/gap/GAP_ANALYSIS_OUTPUT.md`
- Inputs: Python file + BASE_RULES.md + file requirements
- Output: Violations list (Rule ID, line, description)

**Step 3: Fix Violations**
- Template: `.claude/templates/refactor/IMPLEMENTER_DATA.md`
- Action: Fix ONLY reported violations (minimal changes)
- Patterns: `.claude/templates/gap/GAP_FIX_PATTERNS.md`

**Step 4: Tests**
- Template: `.claude/templates/refactor/TESTER_DATA.md`
- Action: Create/update `tests/[PATH]/test_[FILE].py`
- Run: `pytest tests/[PATH]/test_[FILE].py -v`

**Step 5: Code Review**
- Template: `.claude/templates/refactor/CODE_REVIEWER_DATA.md`
- Check: All validation commands pass
- Verify: Requirements compliance

**Step 6: Final Audit**
- Template: `.claude/templates/refactor/AUDITOR_DATA.md`
- Update requirements with:
  ```markdown
  ## Audit Status: PASSED
  **Last Audit:** [UTC_TIMESTAMP]
  ```

---

## Excluded Files
- `tests/**/*.py` - Test files themselves
- `**/test_*.py` - Test files
- `**/__init__.py` - Package init (unless significant logic)
- `**/conftest.py` - Pytest config

## Layer Dependencies (Reference)
```
L12-L13: API & Middleware (highest)
    ↓
L8: Application
    ↓
L6: Domain Services + Strategies
    ↓
L7: Domain Entities
    ↓
L9: Core Layer
    ↓
L10: Data Layer (lowest - start here)

Parallel branches:
- L3-L5: Backtesting (depends on Domain)
- L11: Analysis (depends on Domain)
- L1: Microstructure (depends on Data)
```

---

**Created:** 2026-02-06
**Status:** READY
**Batch Size:** 10 files per layer
**Processing Order:** Bottom-up (L10→L9→L7→L6→L8→L3-5→L11+L1→L12-13)
