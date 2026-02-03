# Wrapper: Code Reviewer

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator, pass this entire context to review code and run QA checks deterministically.

---

## Agent to Delegate

**@agent-tech-lead-orchestrator** - Will coordinate the workflow and delegate to appropriate specialist agents.

---

## Context for Tech Lead Orchestrator

### Repository Information
```
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
BASE_RULES: .requirements/BASE_RULES.md (96+ rules)
```

### Task
Review code for: `{{PYTHON_FILE}}`

### Required Resources
```
Python File: {{PYTHON_FILE}}
Requirements: {{REQUIREMENTS_FILE}}
Test File: {{TEST_FILE}}
Changes: {{CHANGES_SUMMARY}}
BASE_RULES: .requirements/BASE_RULES.md
Fix Patterns: .tasks/templates/GAP_FIX_PATTERNS.md
```

### Specialist Agent to Call
@agent-code-reviewer (for code review and QA checks)

---

## Deterministic Instructions for @agent-code-reviewer

### Step 1: Gather Context

```bash
# Read the source file
Read {{PYTHON_FILE}}

# Read requirements to understand what GAPs were fixed
Read {{REQUIREMENTS_FILE}}

# Get current date for report
date -u +%Y-%m-%dT%H:%M:%SZ
```

### Step 2: Run QA Checks

Execute these checks in order:

```bash
cd /Users/kepa.cantero/Projects/algoTrading

# 1. Syntax check (always available)
python -m py_compile {{PYTHON_FILE}}

# 2. Type check (if mypy available)
mypy --strict {{PYTHON_FILE}}

# 3. Lint (if ruff available)
ruff check {{PYTHON_FILE}}

# 4. Format check (if black available)
black --check {{PYTHON_FILE}}

# 5. Import sort (if isort available)
isort --check-only {{PYTHON_FILE}}

# 6. Security scan (if bandit available)
bandit {{PYTHON_FILE}}

# 7. Unit tests
pytest {{TEST_FILE}} -v
```

For each check, record:
- Status: PASS/FAIL/N/A
- Output: Any errors or warnings

### Step 3: Code Review Analysis

Review the code against these categories:

#### Correctness
- Logic is correct
- Edge cases handled
- No off-by-one errors
- No race conditions (if async)

#### Security
- No SQL injection risk
- No XSS risk (if web)
- Input validation present
- Secrets not hardcoded
- Error messages don't leak info

#### Performance
- No obvious performance issues
- Appropriate data structures
- No unnecessary loops
- Caching if appropriate

#### Maintainability
- Clear variable names
- Appropriate comments
- Functions are focused
- No code duplication

#### BASE_RULES Compliance
Verify:
- TYP-001: Type hints present
- LOG-001: Structured logging
- LOG-004: Exception stack traces
- CC-006: Specific exception handling
- TRD-005: Price validation
- SEC-007: Input validation

### Step 4: Requirements Compliance

From requirements document, extract "Critical Rules" table.
Verify each GAP violation marked as ❌ GAP is now fixed.

For each GAP:
- Locate the fix in the code
- Verify fix follows GAP_FIX_PATTERNS.md
- Document line number of fix

### Step 5: Generate Report

Use the report format below.

---

## Required Output Format

@agent-code-reviewer must return:

```markdown
## Code Review Complete

**File:** {{PYTHON_FILE}}
**Date:** {{DATE}}
**Status:** [APPROVED / NEEDS_CHANGES]

**QA Checks Summary:**
| Check | Status | Notes |
|-------|--------|-------|
| Syntax | ✅/❌ | |
| Type Checking (mypy) | ✅/❌/N/A | |
| Linting (ruff) | ✅/❌/N/A | |
| Formatting (black) | ✅/❌/N/A | |
| Import Sort (isort) | ✅/❌/N/A | |
| Security (bandit) | ✅/❌/N/A | |
| Unit Tests | ✅/❌/N/A | |

**Code Review Findings:**

### Correctness
{{FINDINGS}}

### Security
{{FINDINGS}}

### Performance
{{FINDINGS}}

### Maintainability
{{FINDINGS}}

### BASE_RULES Compliance
{{FINDINGS}}

**Requirements Compliance:**
{{GAP_STATUS_TABLE}}

**Overall Assessment:**
{{SUMMARY}}

**Issues Found:**
{{ISSUES_LIST}}

**Recommendations:**
{{RECOMMENDATIONS}}

**Next:** [Ready for audit OR Back to implementer]
```

---

## Severity Levels

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| **Critical** | Security issue, crash risk, data loss | Must fix before approval |
| **High** | Breaking change, significant bug | Must fix before approval |
| **Medium** | Code quality, minor bug | Should fix, can defer |
| **Low** | Style, minor improvement | Optional |

---

## Approval Criteria

**APPROVED if:**
- [ ] Syntax check: PASS
- [ ] All tests: PASS
- [ ] No Critical issues
- [ ] No High issues
- [ ] All GAP violations verified fixed

**NEEDS_CHANGES if:**
- [ ] Any check: FAIL
- [ ] Critical OR High issues found
- [ ] Any GAP violation not fixed

---

## Quality Checklist

- [ ] All QA checks executed
- [ ] Code reviewed against all categories
- [ ] BASE_RULES compliance verified
- [ ] Requirements compliance verified
- [ ] Line numbers documented for issues
- [ ] Constructive feedback provided
- [ ] Clear approval/decision

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
**Specialist:** @agent-code-reviewer
