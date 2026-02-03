# Wrapper: Refactor Code Reviewer

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator for refactoring code review, pass this entire context.

---

## Agent to Delegate

**@agent-tech-lead-orchestrator** - Will coordinate the workflow and delegate to @agent-code-reviewer.

---

## Context for Tech Lead Orchestrator

### Repository Information
```
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
BASE_RULES: .requirements/BASE_RULES.md
```

### Task
Review refactored code for: `{{PYTHON_FILE}}`
Refactoring Type: `{{VIOLATION_TYPE}}`
Changes: `{{CHANGES_SUMMARY}}`

### Required Resources
```
Python File: {{PYTHON_FILE}}
Requirements: {{REQUIREMENTS_FILE}}
Test File: {{TEST_FILE}}
Changes Summary: {{CHANGES_SUMMARY}}
BASE_RULES: .requirements/BASE_RULES.md
```

### Specialist Agent to Call
@agent-code-reviewer (for code review and QA checks)

---

## Deterministic Instructions for @agent-code-reviewer

### Step 1: Gather Context

```bash
# Read the refactored source file
Read {{PYTHON_FILE}}

# Read requirements to understand what was fixed
Read {{REQUIREMENTS_FILE}}

# Read BASE_RULES for verification
Read .requirements/BASE_RULES.md

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

Review the refactored code against these categories:

#### **Correctness**
- Refactoring preserves original behavior
- No logic errors introduced
- Edge cases handled correctly
- No race conditions (if async/threaded)

#### **Architecture**
- DP-004: Dependency Injection properly implemented
- ARCH-001: Layering violations resolved
- Clean architecture principles followed
- Framework dependencies isolated

#### **Security**
- No new security vulnerabilities
- Input validation maintained
- No hardcoded secrets
- Error messages don't leak info

#### **Performance**
- No performance regression
- Appropriate patterns (singleton, lazy loading)
- No memory leaks
- Efficient initialization

#### **Maintainability**
- Clear variable/function names
- Appropriate comments
- Functions are focused
- No code duplication
- Follows DRY principle

#### **BASE_RULES Compliance**
Verify refactoring-specific rules:
- DP-004: Dependency Injection used
- ARCH-001: Proper layering
- SOL-001: Single Responsibility
- SOL-002: Open/Closed Principle
- SOL-005: Dependency Inversion

### Step 4: Refactoring Pattern Verification

**For DI Container refactoring, verify:**

```python
# ✅ Correct Pattern
class DIContainer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_service(self) -> ServiceType:
        if 'service' not in self._services:
            self._services['service'] = Service()
        return self._services['service']

# Usage in API
def get_service() -> ServiceType:
    return _di_container.get_service()

@router.get("/endpoint")
async def endpoint(
    service: ServiceType = Depends(get_service)
):
    # Use service
```

**For Service Layer extraction, verify:**

```python
# ✅ Correct Pattern
# app/infrastructure/health/service.py
class DatabaseHealthChecker:
    def __init__(self, config: Config) -> None:
        self.config = config

    def check_health(self) -> HealthResult:
        # Implementation

# app/api/health.py
from app.infrastructure.health.service import DatabaseHealthChecker

def get_db_checker() -> DatabaseHealthChecker:
    return DatabaseHealthChecker(config=settings)
```

### Step 5: Generate Report

Use the report format below.

---

## Required Output Format

@agent-code-reviewer must return:

```markdown
## Code Review Complete

**File:** {{PYTHON_FILE}}
**Refactoring Type:** {{VIOLATION_TYPE}}
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

### Architecture
{{FINDINGS - DP-004/ARCH-001 verification}}

### Security
{{FINDINGS}}

### Performance
{{FINDINGS}}

### Maintainability
{{FINDINGS}}

### BASE_RULES Compliance
{{VERIFICATION OF REFACTORING RULES}}

**Refactoring Pattern Verification:**
{{PATTERN_VERIFICATION}}

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
| **Critical** | Breaking change, functionality loss | Must fix before approval |
| **High** | Architecture violation, significant bug | Must fix before approval |
| **Medium** | Code quality, minor improvement | Should fix, can defer |
| **Low** | Style, minor optimization | Optional |

---

## Approval Criteria

**APPROVED if:**
- [ ] Syntax check: PASS
- [ ] All tests: PASS
- [ ] No Critical issues
- [ ] No High issues
- [ ] Refactoring pattern correctly implemented
- [ ] BASE_RULES compliance verified

**NEEDS_CHANGES if:**
- [ ] Any check: FAIL
- [ ] Critical OR High issues found
- [ ] Refactoring pattern not correctly applied
- [ ] BASE_RULES violations remain

---

## Quality Checklist

- [ ] All QA checks executed
- [ ] Code reviewed against all categories
- [ ] Refactoring pattern verified
- [ ] BASE_RULES compliance verified
- [ ] Breaking changes identified
- [ ] Constructive feedback provided
- [ ] Clear approval/decision

---

## Common Review Patterns

### DI Container Review Checklist

```markdown
**DI Container Review:**
- [ ] Container implements singleton pattern correctly
- [ ] Services use lazy initialization
- [ ] Thread safety considered (if applicable)
- [ ] Generic registration methods available
- [ ] Type hints present and correct
- [ ] API file uses Depends() correctly
- [ ] No direct instantiation remaining
```

### Service Layer Review Checklist

```markdown
**Service Layer Review:**
- [ ] Service class in correct location (infrastructure/)
- [ ] No database/framework code in API layer
- [ ] Service has clear interface
- [ ] Configuration passed via constructor
- [ ] Error handling appropriate
- [ ] Type hints present
- [ ] Testable design
```

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
**Specialist:** @agent-code-reviewer
