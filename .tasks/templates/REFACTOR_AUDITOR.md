# Wrapper: Refactor Auditor (Requirements Compliance Auditor)

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator for refactoring audit, pass this entire context.

---

## Agent to Delegate

**@agent-tech-lead-orchestrator** - Will coordinate the workflow and delegate to @agent-code-auditor.

---

## Context for Tech Lead Orchestrator

### Repository Information
```
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
Requirements Location: .requirements/
BASE_RULES: .requirements/BASE_RULES.md
```

### Task
Audit refactoring compliance for: `{{PYTHON_FILE}}`
Refactoring Type: `{{VIOLATION_TYPE}}`
Code Review Status: `{{CODE_REVIEW_STATUS}}`

### Required Resources
```
Python File: {{PYTHON_FILE}}
Requirements: {{REQUIREMENTS_FILE}}
BASE_RULES: .requirements/BASE_RULES.md
Verification Checklist: .tasks/templates/GAP_FIX_PATTERNS.md
```

### Specialist Agent to Call
@agent-code-auditor (for requirements compliance audit)

---

## Deterministic Instructions for @agent-code-auditor

### Step 1: Read Requirements Document

```bash
Read {{REQUIREMENTS_FILE}}
```

Extract from the "Critical Rules (MUST NOT BREAK)" section:
- All rules marked as ❌ GAP (should be fixed by refactoring)
- Refactoring-specific violations (DP-004, ARCH-001, etc.)
- Any rules marked as ⚠️ PARTIAL (should verify complete)

### Step 2: Read Current Code

```bash
Read {{PYTHON_FILE}}
```

### Step 3: Verify Refactoring Complete

For each violation from requirements document:

#### **DP-004: Dependency Injection Violations**

**Checklist:**
```python
# ✅ FIXED - DI Container pattern present
from app.core.di_container import DIContainer

_di_container = DIContainer()

def get_service() -> ServiceType:
    return _di_container.get_service()

# ❌ STILL VIOLATED - Direct instantiation remains
service = Service()  # This should be gone
```

**Verification:**
1. DI Container class exists
2. No direct `Service()` instantiation in API layer
3. All services use `Depends(get_service)`
4. Singleton pattern correctly implemented

#### **ARCH-001: Layering Violations**

**Checklist:**
```python
# ✅ FIXED - Service layer used
from app.infrastructure.health.service import DatabaseHealthChecker

def get_checker() -> DatabaseHealthChecker:
    return DatabaseHealthChecker(config)

# ❌ STILL VIOLATED - Database logic in API layer
import sqlite3
conn = sqlite3.connect(path)  # This should be gone
```

**Verification:**
1. No `sqlite3` or other DB imports in API layer
2. Service class exists in `app/infrastructure/`
3. API layer only calls service methods
4. No business logic in API layer

### Step 4: Update Requirements Document

For each verified FIXED violation, update the status table:

**Before:**
```markdown
| DP-004 | BASE_RULES | Dependency Injection | ❌ GAP - Direct instantiation at line 43 |
```

**After:**
```markdown
| DP-004 | BASE_RULES | Dependency Injection | ✅ FIXED - 2026-02-02T14:30:00Z - Line 43: Replaced with DI container pattern |
```

### Step 5: Update Audit Status with Timestamp

**Get current timestamp:**
```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

**Update Audit Status section:**

**If audit PASSED:**
```markdown
## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-02T14:30:00Z |
| **Audit Status** | PASSED |
| **Refactoring Type** | DP-004 / ARCH-001 |
| **Refactoring Completed** | YES |
| **BASE_RULES Version** | main@$(git rev-parse --short HEAD) |
| **Audited By** | @agent-code-auditor |

**Refactoring Applied:**
- RULE-ID: Description (line N)
- RULE-ID: Description (line N)

**Files Modified:**
- {{PYTHON_FILE}}: [changes summary]
- [NEW_FILE]: [if applicable]
```

**If audit FAILED:**
```markdown
## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-02T14:30:00Z |
| **Audit Status** | FAILED |
| **Refactoring Type** | DP-004 / ARCH-001 |
| **Refactoring Completed** | PARTIAL |
| **BASE_RULES Version** | main@$(git rev-parse --short HEAD) |
| **Audited By** | @agent-code-auditor |

**Remaining Issues:**
- RULE-ID: Still violating at line N
- RULE-ID: Partial implementation

**Fixed:**
- RULE-ID: Description (line N)
```

### Step 6: Update Requirements File

Use Edit tool to update:
1. Critical Rules table (change ❌ GAP to ✅ FIXED)
2. Audit Status section (add/update timestamp and status)
3. Notes section (add refactoring applied)

---

## Required Output Format

@agent-code-auditor must return:

```markdown
## Refactoring Audit Complete

**File:** {{PYTHON_FILE}}
**Requirements:** {{REQUIREMENTS_FILE}}
**Date:** {{TIMESTAMP}}
**Refactoring Type:** {{VIOLATION_TYPE}}
**Status:** [PASS / FAIL]

**Violations Audited:**
| Rule | Source | Status | Evidence |
|------|--------|--------|----------|
| DP-004 | BASE_RULES | ✅ FIXED | Line 43: DI container implemented |
| ARCH-001 | BASE_RULES | ✅ FIXED | Line 87: Database logic moved to service layer |

**Summary:**
- Total violations: {{N}}
- Verified fixed: {{N}}
- Remaining: {{N}}
- New issues: {{N}}

**Refactoring Verification:**

**DP-004 (Dependency Injection):**
- [ ] DI Container exists: ✅/❌
- [ ] No direct instantiation: ✅/❌
- [ ] Depends() used correctly: ✅/❌
- [ ] Singleton pattern: ✅/❌

**ARCH-001 (Layering):**
- [ ] No DB imports in API: ✅/❌
- [ ] Service class exists: ✅/❌
- [ ] API delegates to service: ✅/❌
- [ ] No business logic in API: ✅/❌

**Requirements Document:** [UPDATED / NOT UPDATED]

**Audit Outcome:**
- [ ] All violations fixed
- [ ] No new violations introduced
- [ ] Requirements document updated
- [ ] Timestamp added
- [ ] Refactoring pattern verified

**Next:** [Task complete OR Back to implementer]
```

---

## Pass/Fail Criteria

**PASS if ALL:**
- [ ] All refactoring violations are fixed
- [ ] No new violations introduced
- [ ] Requirements document updated with ✅ FIXED
- [ ] Audit Status section updated with PASSED
- [ ] ISO 8601 timestamp added
- [ ] Refactoring pattern correctly implemented

**FAIL if ANY:**
- [ ] Any refactoring violation remains
- [ ] New violations introduced
- [ ] Requirements document not updated
- [ ] Timestamp not added
- [ ] Refactoring pattern not correctly applied

---

## Quality Checklist

- [ ] All refactoring violations verified
- [ ] Line numbers documented for fixes
- [ ] BASE_RULES.md checked for each rule
- [ ] Refactoring pattern verified
- [ ] Requirements document updated
- [ ] Audit Status updated with timestamp
- [ ] Fixes documented with dates
- [ ] New violations documented (if any)

---

## Timestamp Format

**ISO 8601 UTC:** `YYYY-MM-DDTHH:MM:SSZ`

Examples:
- `2026-02-02T14:30:00Z`
- `2026-02-02T08:15:30Z`

Get timestamp:
```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

---

## Refactoring Pattern Verification

### DP-004 Verification

```python
# Check these elements are present:
1. DI Container class exists
2. get_SERVICE() function exists
3. Depends(get_SERVICE) used in endpoints
4. No direct Service() instantiation
5. Singleton pattern (__new__ or similar)
```

### ARCH-001 Verification

```python
# Check these elements are present:
1. Service class in app/infrastructure/ or similar
2. API imports service from infrastructure
3. No direct database/framework imports in API
4. All logic delegated to service
5. Clean separation of concerns
```

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
**Specialist:** @agent-code-auditor
