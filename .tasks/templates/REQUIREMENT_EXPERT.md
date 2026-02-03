# Wrapper: Requirement Expert

**This template is a CONTEXT WRAPPER for @agent-tech-lead-orchestrator**

When calling @agent-tech-lead-orchestrator, pass this entire context to create requirements documents deterministically.

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
```

### Task
Create requirements document for: `{{PYTHON_FILE}}`

### Required Resources
```
BASE_RULES: .requirements/BASE_RULES.md (96+ rules)
Template: .tasks/templates/REQUIREMENT_TEMPLATE.md
Output: .requirements/{{PYTHON_PATH}}.requirements.md
```

### Specialist Agent to Call
@agent-python-expert (for creating requirements documents)

---

## Deterministic Instructions for @agent-python-expert

### Step 1: Gather Information (Use Scripts)

```bash
# Get file statistics
wc -l {{PYTHON_FILE}}

# Count elements
grep -c "^class " {{PYTHON_FILE}} || echo "0"
grep -c "^def " {{PYTHON_FILE}} || echo "0"
grep -c "^import " {{PYTHON_FILE}}
grep -c "^from " {{PYTHON_FILE}}

# Get current timestamp for Audit Status
date -u +%Y-%m-%dT%H:%M:%SZ
```

### Step 2: Read Required Files (In Order)

1. `.tasks/templates/REQUIREMENT_TEMPLATE.md` - Template structure
2. `.requirements/BASE_RULES.md` - 96+ universal rules
3. `{{PYTHON_FILE}}` - The Python file to document

### Step 3: Extract from Python File

**Document these elements:**

1. **Module Purpose** - From docstring at top of file
2. **Classes** - Each class with:
   - Class name
   - Docstring
   - All fields with types (Mapped[type], Optional[type], etc.)
   - Default values
   - Validation (CheckConstraints, etc.)
3. **Functions** - Each function with:
   - Signature with types
   - Parameters and return types
   - Docstring (if any)
4. **Dependencies** - External packages and internal imports

### Step 4: Check GAP Violations

**Look for these patterns:**
- `datetime.utcnow()` → FMT-007 (deprecated)
- `except Exception:` → CC-006
- `logger.*f"` → LOG-001
- Missing `-> Type` → TYP-001
- `: Any` without justification → TYP-003

### Step 5: Create Requirements Document

**Using `.tasks/templates/REQUIREMENT_TEMPLATE.md`, create:**

```markdown
# [FileName].py

## Purpose
[From module docstring]

---

## Type Definitions / Data Classes
[One section per class]

## Function Signatures (Contracts)
[One section per function]

## Acceptance Criteria
[Testable conditions]

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | [CURRENT_TIMESTAMP] |
| **Audit Status** | NEEDS_AUDIT |
| **BASE_RULES Version** | TBD |
| **Audited By** | @agent-python-expert |
| **GAPs Fixed** | 0 / X total |

---

## Critical Rules (MUST NOT BREAK)

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
[Fill with GAP violations found]

---

## Dependencies
[External and Internal]

## Required Tests
[Test file location and cases]

## Notes
[Known issues, design decisions]
```

### Step 6: Save Document

```bash
# Create directory if needed
mkdir -p .requirements/{{PATH_DIR}}

# Write file
# Save to: .requirements/{{PYTHON_PATH}}.requirements.md
```

---

## Required Output Format

@agent-python-expert must return:

```markdown
## Requirements Document Created

**File:** {{PYTHON_FILE}}
**Requirements:** .requirements/{{PYTHON_PATH}}.requirements.md

**Summary:**
- Classes documented: X
- Functions documented: Y
- GAP violations found: Z
- Priority: P0=A P1=B P2=C P3=D

**GAP Violations:**
- [List of violations]

**File saved to:** .requirements/{{PYTHON_PATH}}.requirements.md
```

---

## Quality Checklist

The requirements document MUST have:
- [ ] All sections from template filled
- [ ] All classes documented
- [ ] All functions documented
- [ ] GAP violations listed in Critical Rules table
- [ ] Audit Status with current timestamp
- [ ] Dependencies listed
- [ ] Required Tests specified
- [ ] File saved to correct location

---

## Common GAP Patterns to Document

| Pattern | Rule | Lines to Check |
|---------|------|----------------|
| `datetime.utcnow()` | FMT-007 | All datetime defaults |
| `except Exception:` | CC-006 | All except blocks |
| `logger.*f"` | LOG-001 | All logger calls |
| Missing `-> Type` | TYP-001 | All def statements |
| `: Any` | TYP-003 | All type hints |
| Price > 0 check | TRD-005 | Price-related functions |
| Hardcoded secrets | SEC-001 | String literals |
| Functions > 20 lines | ARCH-004 | All def blocks |

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
