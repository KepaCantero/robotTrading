# Wrapper: Auditor (Requirements Compliance Auditor)

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator, pass this entire context to audit requirements compliance and update documents deterministically.

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
Requirements Location: .requirements/
BASE_RULES: .requirements/BASE_RULES.md (96+ rules)
```

### Task
Audit requirements compliance for: `{{PYTHON_FILE}}`

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
- All rules marked as ❌ GAP (should be fixed)
- All rules marked as ⚠️ PARTIAL (should verify completion)
- Any rules marked as ✅ FIXED (verify still fixed)

### Step 2: Read Current Code

```bash
Read {{PYTHON_FILE}}
```

### Step 3: Verify Each GAP Violation

For each rule in requirements document:

#### From BASE_RULES.md (Universal Rules)
1. Read the rule definition from BASE_RULES.md
2. Verify the code follows the rule
3. Check against GAP_FIX_PATTERNS.md for expected pattern

#### From File-Specific Requirements
1. Check the specific requirement
2. Verify the implementation matches
3. Document any discrepancies

**Verification Patterns:**

**LOG-001: Structured Logging**
```python
# ✅ GOOD
logger.info("Processing trade", symbol=symbol, quantity=quantity)

# ❌ BAD
logger.info(f"Processing trade: {symbol}")
```

**LOG-004: Exception Stack Traces**
```python
# ✅ GOOD
except ValueError as e:
    logger.error("Invalid input", error=str(e), exc_info=True)

# ❌ BAD
except ValueError as e:
    logger.error("Invalid input", error=str(e))
```

**CC-006: Explicit Error Handling**
```python
# ✅ GOOD
except ValueError as e:
    # Handle
except ValidationError as e:
    # Handle

# ❌ BAD
except Exception as e:
    # Handle everything
```

**TYP-001: Return Types**
```python
# ✅ GOOD
def process(x) -> int:

# ❌ BAD
def process(x):
```

**FMT-007: DateTime Deprecated**
```python
# ❌ BAD
default=datetime.utcnow

# ✅ GOOD
default=lambda: datetime.now(timezone.utc)
```

### Step 4: Update Requirements Document

For each verified FIXED GAP, update the status table:

**Before:**
```markdown
| LOG-001 | BASE_RULES | Structured logging | ❌ GAP - Uses f-string |
```

**After:**
```markdown
| LOG-001 | BASE_RULES | Structured logging | ✅ FIXED - 2026-02-02T14:30:00Z - Line 45: Replaced with logger.info("Processing", symbol=symbol) |
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
| **BASE_RULES Version** | main@$(git rev-parse --short HEAD) |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | X / Y total |

**Fixes Applied:**
- RULE-ID: Description (line N)
```

**If audit FAILED:**
```markdown
## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-02T14:30:00Z |
| **Audit Status** | FAILED |
| **BASE_RULES Version** | main@$(git rev-parse --short HEAD) |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | X / Y total |

**Remaining Issues:**
- RULE-ID: Still violating at line N
- RULE-ID: Partial implementation

**Fixed:**
- RULE-ID: Description (line N)
```

**If first audit (NEEDS_AUDIT):**
```markdown
## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-02T14:30:00Z |
| **Audit Status** | NEEDS_AUDIT |
| **BASE_RULES Version** | main@$(git rev-parse --short HEAD) |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | 0 / Y total |

**Issues Found:**
- RULE-ID: Description (line N)
```

### Step 6: Update Requirements File

Use Edit tool to update:
1. Critical Rules table (change ❌ GAP to ✅ FIXED)
2. Audit Status section (add/update timestamp and status)
3. Notes section (add fixes applied)

---

## Required Output Format

@agent-code-auditor must return:

```markdown
## Audit Complete

**File:** {{PYTHON_FILE}}
**Requirements:** {{REQUIREMENTS_FILE}}
**Date:** {{TIMESTAMP}}
**Status:** [PASS / FAIL]

**GAP Violations Audited:**
| Rule | Source | Status | Evidence |
|------|--------|--------|----------|
| LOG-001 | BASE_RULES | ✅ FIXED | Line 45: logger.info("...", symbol=symbol) |
| LOG-004 | BASE_RULES | ✅ FIXED | Line 67: exc_info=True added |
| CC-006 | BASE_RULES | ❌ REMAINING | Line 89: Still using generic Exception |

**Summary:**
- Total GAPs: {{N}}
- Verified fixed: {{N}}
- Remaining: {{N}}
- New issues: {{N}}

**Requirements Document:** [UPDATED / NOT UPDATED]

**Audit Outcome:**
- [ ] All GAP violations fixed
- [ ] No new GAP violations introduced
- [ ] Requirements document updated
- [ ] Timestamp added

**Next:** [Task complete OR Back to implementer]
```

---

## Pass/Fail Criteria

**PASS if ALL:**
- [ ] All GAP violations from requirements are verified fixed
- [ ] No new GAP violations introduced
- [ ] Requirements document updated with ✅ FIXED
- [ ] Audit Status section updated with PASSED
- [ ] ISO 8601 timestamp added

**FAIL if ANY:**
- [ ] Any GAP violation remains unfixed
- [ ] New GAP violations introduced
- [ ] Requirements document not updated
- [ ] Timestamp not added

---

## Quality Checklist

- [ ] All GAP violations verified
- [ ] Line numbers documented for fixes
- [ ] BASE_RULES.md checked for each rule
- [ ] GAP_FIX_PATTERNS.md used as reference
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

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
**Specialist:** @agent-code-auditor
