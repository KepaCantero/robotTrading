# Task: Refactor Base Template

**This is the BASE TEMPLATE for all refactoring tasks. Specific refactoring tasks extend this template.**

---

## Template Extension Pattern

**All refactoring tasks MUST follow this structure:**

```markdown
# Task: Refactor [File] - [Title]

## Extends
- Base: `.claude/tasks/REFACTOR_BASE.md`
- Orchestrator: @agent-tech-lead-orchestrator

## Context Variables (Pre-filled)
- `{{PYTHON_FILE}}` = [actual file path]
- `{{VIOLATION_TYPE}}` = [DP-004, ARCH-001, etc.]
- `{{PATTERN}}` = [DI Container, Service Layer, etc.]
- `{{REQUIREMENTS_FILE}}` = [actual requirements path]
- `{{INSTRUCTIONS_FILE}}` = [this task file]

## Filled Templates (for each step)

### Step 1: Implementer
**Template:** `.tasks/templates/REFACTOR_IMPLEMENTER.md`
**Filled with:** All context variables above

### Step 2: Tester
**Template:** `.tasks/templates/REFACTOR_TESTER.md`
**Filled with:** Changes from Step 1

### Step 3: Code Reviewer
**Template:** `.tasks/templates/REFACTOR_CODE_REVIEWER.md`
**Filled with:** Changes from Step 1 + Test results

### Step 4: Auditor
**Template:** `.tasks/templates/REFACTOR_AUDITOR.md`
**Filled with:** All previous steps context
```

---

## Overview

Systematic refactoring workflow for architectural violations found during GAP audit. Follows the **same pattern as GAP audit workflow**: Implementer → Tester → Code Reviewer → Auditor.

## Context

```
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
BASE_RULES: .requirements/BASE_RULES.md
Templates: .tasks/templates/
```

---

## Specialist Agents

| Agent | Role | When Called |
|-------|------|-------------|
| @agent-tech-lead-orchestrator | Coordinator | Always - delegates to specialists |
| @agent-backend-developer | Implement refactoring | Implementation phase |
| @agent-python-testing-expert | Create/update tests | After implementation |
| @agent-code-reviewer | Review and QA | After tests created |
| @agent-code-auditor | Audit compliance | After code review |

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TECH LEAD ORCHESTRATOR                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. IMPLEMENTER (@agent-backend-developer)                         │   │
│  │     - Read current code                                             │   │
│  │     - Apply refactoring changes                                     │   │
│  │     - Follow specific task instructions                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  2. TESTER (@agent-python-testing-expert)                          │   │
│  │     - Create/update unit tests                                      │   │
│  │     - Test refactored code                                          │   │
│  │     - Ensure all tests pass                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  3. CODE REVIEWER (@agent-code-reviewer)                           │   │
│  │     - Run QA checks (syntax, type, lint, format)                   │   │
│  │     - Review code quality                                           │   │
│  │     - Validate BASE_RULES compliance                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  4. AUDITOR (@agent-code-auditor)                                  │   │
│  │     - Verify all violations fixed                                   │   │
│  │     - Update requirements document                                  │   │
│  │     - Mark as PASSED or FAILED                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  COMPLETE / RETRY                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Implementer (@agent-backend-developer)

### Context
**Specific Task:** [EXTENDS FROM CHILD TASK]

### Instructions

1. **Read Current Code**
   ```bash
   Read app/[PATH]/[FileName].py
   ```

2. **Read BASE_RULES.md**
   ```bash
   Read .requirements/BASE_RULES.md
   ```

3. **Apply Refactoring Changes**
   - Follow specific instructions from child task
   - Use Edit tool for all changes
   - Maintain existing functionality
   - Follow BASE_RULES patterns

4. **Verify Syntax**
   ```bash
   python -m py_compile app/[PATH]/[FileName].py
   ```

5. **Output Format**
   Return implementation summary with:
   - Changes made
   - Lines modified
   - Syntax verification status
   - Any issues encountered

---

## Step 2: Tester (@agent-python-testing-expert)

### Context
**Changes from Implementer:** [SUMMARY FROM STEP 1]

### Instructions

1. **Read Test File**
   ```bash
   Read tests/[PATH]/test_[FileName].py
   ```

2. **Create/Update Tests**
   - Test refactored functionality
   - Test new patterns (DI, service layer, etc.)
   - Ensure backward compatibility
   - Add edge case coverage

3. **Run Tests**
   ```bash
   cd /Users/kepa.cantero/Projects/algoTrading
   pytest tests/[PATH]/test_[FileName].py -v
   ```

4. **Output Format**
   Return test report with:
   - Tests created/updated
   - Test results (PASS/FAIL)
   - Coverage percentage
   - Any failing tests with details

---

## Step 3: Code Reviewer (@agent-code-reviewer)

### Context
**File:** app/[PATH]/[FileName].py
**Test File:** tests/[PATH]/test_[FileName].py
**Changes:** [SUMMARY FROM STEP 1]

### Instructions

1. **Gather Context**
   ```bash
   Read app/[PATH]/[FileName].py
   Read .requirements/[PATH]/[FileName].requirements.md
   Read .requirements/BASE_RULES.md
   ```

2. **Run QA Checks**

   ```bash
   cd /Users/kepa.cantero/Projects/algoTrading

   # 1. Syntax check
   python -m py_compile app/[PATH]/[FileName].py

   # 2. Type check (if mypy available)
   mypy --strict app/[PATH]/[FileName].py

   # 3. Lint (if ruff available)
   ruff check app/[PATH]/[FileName].py

   # 4. Format check (if black available)
   black --check app/[PATH]/[FileName].py

   # 5. Import sort (if isort available)
   isort --check-only app/[PATH]/[FileName].py

   # 6. Security scan (if bandit available)
   bandit app/[PATH]/[FileName].py

   # 7. Unit tests
   pytest tests/[PATH]/test_[FileName].py -v
   ```

3. **Code Review Analysis**

   Review against these categories:

   - **Correctness**: Logic is correct, edge cases handled
   - **Security**: No injection risks, input validation present
   - **Performance**: No obvious issues, appropriate patterns
   - **Maintainability**: Clear naming, focused functions, no duplication
   - **BASE_RULES Compliance**: Verify all relevant rules

4. **Output Format**

   Return code review report:

   ```markdown
   ## Code Review Complete

   **File:** app/[PATH]/[FileName].py
   **Status:** [APPROVED / NEEDS_CHANGES]

   **QA Checks Summary:**
   | Check | Status | Notes |
   |-------|--------|-------|
   | Syntax | ✅/❌ | |
   | Type Checking | ✅/❌/N/A | |
   | Linting | ✅/❌/N/A | |
   | Formatting | ✅/❌/N/A | |
   | Security | ✅/❌/N/A | |
   | Unit Tests | ✅/❌/N/A | |

   **Findings:**
   [Detailed findings by category]

   **Requirements Compliance:**
   [Verification of task-specific requirements]

   **Overall Assessment:**
   [Summary]

   **Issues Found:**
   [List any issues]

   **Next:** [Ready for audit OR Back to implementer]
   ```

---

## Step 4: Auditor (@agent-code-auditor)

### Context
**File:** app/[PATH]/[FileName].py
**Requirements:** .requirements/[PATH]/[FileName].requirements.md
**Code Review Status:** [FROM STEP 3]

### Instructions

1. **Read Requirements Document**
   ```bash
   Read .requirements/[PATH]/[FileName].requirements.md
   ```

2. **Read Current Code**
   ```bash
   Read app/[PATH]/[FileName].py
   ```

3. **Verify Refactoring Complete**

   For each violation from requirements document:
   - Check if refactoring addressed the issue
   - Verify BASE_RULES.md compliance
   - Document current status

4. **Update Requirements Document**

   Use Edit tool to update the requirements document:

   ```markdown
   ## Audit Status

   | Field | Value |
   |-------|-------|
   | **Last Audit Date** | [TIMESTAMP] |
   | **Audit Status** | [PASSED / FAILED] |
   | **Refactoring Completed** | [YES / NO] |
   | **Audited By** | @agent-code-auditor |

   **Refactoring Applied:**
   - [VIOLATION_ID]: Description (line N)
   ```

   **Get timestamp:**
   ```bash
   date -u +%Y-%m-%dT%H:%M:%SZ
   ```

5. **Output Format**

   Return audit report:

   ```markdown
   ## Audit Complete

   **File:** app/[PATH]/[FileName].py
   **Requirements:** .requirements/[PATH]/[FileName].requirements.md
   **Date:** [TIMESTAMP]
   **Status:** [PASS / FAIL]

   **Violations Audited:**
   | Rule | Source | Status | Evidence |
   |------|--------|--------|----------|
   | RULE-ID | BASE_RULES/File | ✅ FIXED | Line N: ... |

   **Summary:**
   - Total violations: N
   - Verified fixed: N
   - Remaining: N
   - New issues: N

   **Requirements Document:** [UPDATED / NOT UPDATED]

   **Audit Outcome:**
   - [ ] All violations fixed
   - [ ] No new violations introduced
   - [ ] Requirements document updated
   - [ ] Timestamp added

   **Next:** [Task complete OR Back to implementer]
   ```

---

## Complete or Retry

### If ALL checks pass:
- Mark task as **COMPLETED**
- Move to next file

### If ANY check fails:
- Document what failed
- **Retry from Step 1** (Implementer)

---

## Acceptance Criteria (Template)

Child tasks should specify their acceptance criteria:

- [ ] Refactoring changes applied
- [ ] All existing functionality preserved
- [ ] Syntax check passes
- [ ] Type check passes (if available)
- [ ] Lint check passes (if available)
- [ ** ] Tests pass (new or updated)
- [ ] Requirements document updated
- [ ] Audit Status: PASSED

---

## Parallelization

**Multiple refactoring tasks can run in parallel when:**

1. **Different files with no dependencies** → Run 2-4 tasks in parallel
2. **Same file, different steps** → Must run sequentially
3. **Different layers (no deps)** → Can run in parallel

**Execution Pattern:**
```python
# ✅ CORRECT - Parallel execution
Task(agent=backend-developer, "Refactor portfolio.py")
Task(agent=backend-developer, "Refactor signals.py")
Task(agent=backend-developer, "Refactor health.py")

# Then after all complete:
Task(agent=code-reviewer, "Review portfolio.py")
Task(agent=code-reviewer, "Review signals.py")
Task(agent=code-reviewer, "Review health.py")
```

---

## QA Commands Reference

```bash
# Syntax check (always available)
python -m py_compile app/[PATH]/[FileName].py

# Type check (if mypy installed)
mypy --strict app/[PATH]/[FileName].py

# Lint (if ruff installed)
ruff check app/[PATH]/[FileName].py

# Format check (if black installed)
black --check app/[PATH]/[FileName].py

# Tests
pytest tests/[PATH]/test_[FileName].py -v
```

---

## BASE_RULES Categories

When reviewing, verify compliance with relevant categories:

| Category | Rules | Check |
|----------|-------|-------|
| Architecture (ARCH) | Layering, DI, patterns | ✅ |
| Design Patterns (DP) | SOLID, GoF patterns | ✅ |
| Security (SEC) | Input validation, no secrets | ✅ |
| Testing (TEST) | Testability, coverage | ✅ |
| Performance (PERF) | No obvious issues | ✅ |
| Code Style (FMT, TYP) | Type hints, formatting | ✅ |

---

## Task Status Flow

Each task flows through these states:

1. **PLANNED** - Task created, awaiting execution
2. **IMPLEMENTING** - Backend developer applying changes
3. **TESTING** - Testing expert creating/updating tests
4. **REVIEWING** - Code reviewer running QA checks
5. **AUDITING** - Auditor verifying compliance
6. **COMPLETED** - All checks pass, requirements updated
7. **FAILED** - Validation failed → Retry from step 1

---

**Template Version:** 1.0
**Created:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
